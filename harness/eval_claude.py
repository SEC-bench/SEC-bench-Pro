"""Evaluation harness for Claude Code agent inside Docker containers.

Usage::

    uv run harness/eval_claude.py harness/configs/claude/v8/baseline_sonnet-4.6.toml
    python3 harness/eval_claude.py harness/configs/claude/sm/baseline_sonnet-4.6.toml --no-tui

The script:

1.  Loads a TOML config describing model, instances, timeout, etc.
2.  For each benchmark instance: starts a container, configures
    Claude Code, runs the agent, collects artifacts (Claude projects,
    audit files, tracking database), and tears down.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import common
from common import (
    ACOV_PYTHON_AUDIT_ENV_SH,
    ACOV_SHIM_DIR,
    ACOV_SOCKET_PATH,
    BOLD,
    CYAN,
    DIM,
    NC,
    SCRIPT_DIR,
    YELLOW,
    acov_db_container_path,
    acov_event_log_container_path,
    build_env_args,
    collect_acov_artifacts,
    collect_audit_artifacts,
    collect_beads_artifacts,
    collect_result_files,
    docker_copy_from,
    docker_copy_to,
    docker_exec,
    docker_exec_streaming,
    docker_pipe_stdin,
    docker_preflight,
    error,
    info,
    is_timeout_exit_code,
    load_config,
    resolve_instances,
    resolve_path,
    run_eval_loop,
    run_step,
    setup_acov,
    setup_linux_evaluation_container,
    step_err,
    step_ok,
    step_run,
    step_warn,
    warn,
    write_timeout_marker,
)


@dataclass(frozen=True)
class ClaudeProviderSettings:
    forwarded_env_vars: tuple[str, ...]
    use_bare: bool
    required_host_env_var: str | None = None


_CLAUDE_PROVIDER_SETTINGS: dict[str, ClaudeProviderSettings] = {
    "bedrock": ClaudeProviderSettings(
        forwarded_env_vars=(
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_SESSION_TOKEN",
            "AWS_REGION_NAME",
            "CLAUDE_CODE_USE_BEDROCK",
        ),
        use_bare=False,
    ),
    "anthropic": ClaudeProviderSettings(
        forwarded_env_vars=("ANTHROPIC_API_KEY",),
        use_bare=True,
        required_host_env_var="ANTHROPIC_API_KEY",
    ),
}

_CLAUDE_EXTRA_ENV = {
    "IS_SANDBOX": "1",
}


def _write_claude_project_manifest(
    projects_dest: Path,
    instance_outdir: Path,
) -> tuple[int, Path | None, int]:
    """Record the selected Claude project JSONL without duplicating it."""
    project_files = sorted(
        projects_dest.rglob("*.jsonl"),
        key=lambda path: (path.stat().st_mtime, str(path)),
        reverse=True,
    )
    if not project_files:
        return 0, None, 0

    latest = project_files[0]
    event_count = 0
    with latest.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.strip():
                event_count += 1

    manifest = {
        "source": str(latest.relative_to(instance_outdir)),
        "events": event_count,
        "projects": len(project_files),
    }
    (instance_outdir / "claude_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return event_count, latest, len(project_files)


def run_instance(
    *,
    instance_id: str,
    image_name: str,
    work_dir: str,
    instance_outdir: Path,
    prompt: str,
    config: dict,
    agents_md_content: str | None,
    linux_secb_config_content: str | None,
    linux_instance_dir: Path | None,
    skill_directory: Path | None,
    acov_path: Path | None,
    acov_subsystems: str | None,
) -> int:
    """Run the full evaluation lifecycle for one benchmark instance."""
    model = config["model"]
    timeout_secs: int = config["timeout"]
    tracking: str = config.get("tracking", "beads")
    project: str = config.get("project", "")
    provider: str = config.get("provider", "bedrock")
    provider_settings = _CLAUDE_PROVIDER_SETTINGS[provider]

    claude_cli: str = config.get("claude_cli", "claude")
    max_budget_usd: float | None = config.get("max_budget_usd")
    allowed_tools: list[str] = config.get(
        "allowed_tools",
        ["Bash", "Read", "Write", "Edit", "Glob", "Grep"],
    )
    output_format: str = config.get("output_format", "stream-json")
    permission_mode: str | None = config.get("permission_mode")
    system_prompt: str | None = config.get("system_prompt")
    reasoning_effort: str = config["reasoning_effort"]
    privileged: bool = config.get("privileged", common.is_linux_project(project))

    container_name = f"claude-eval-{instance_id}-{int(datetime.now().timestamp())}"

    common._emit(f"\n{CYAN}{BOLD}>>> Instance: {instance_id} <<<{NC}")
    info(f"Image: {image_name}")
    info(f"Work dir: {work_dir}")

    rc = subprocess.run(
        ["docker", "image", "inspect", image_name],
        capture_output=True,
    ).returncode
    if rc != 0:
        info(f"Pulling Docker image: {image_name}")
        subprocess.run(["docker", "pull", image_name], check=True)
    else:
        info(f"Docker image found locally: {image_name}")

    env_args = build_env_args(
        provider_settings.forwarded_env_vars,
        extra_env=_CLAUDE_EXTRA_ENV,
    )
    required_host_env_var = provider_settings.required_host_env_var
    if required_host_env_var and not os.environ.get(required_host_env_var):
        warn(
            f"{required_host_env_var} is unset on the host; Claude Code may fail "
            f"to authenticate with provider={provider}."
        )

    info(f"Starting container: {container_name}")
    docker_run_cmd = [
        "docker",
        "run",
        "--detach",
        "--name",
        container_name,
    ]
    if privileged:
        docker_run_cmd.append("--privileged")
    docker_run_cmd.extend(
        [
            *env_args,
            image_name,
            "bash",
            "-c",
            "sleep infinity",
        ]
    )
    result = subprocess.run(
        docker_run_cmd,
        capture_output=True,
        text=True,
        check=True,
    )
    container_id = result.stdout.strip()
    info(f"Container started: {container_id[:12]}")
    common._active_containers.add(container_name)

    agent_exit = 1

    def _cleanup_container() -> None:
        if container_name not in common._active_containers:
            return
        if not common.INTERRUPTED:
            info("Fixing file ownership before cleanup...")
            try:
                subprocess.run(
                    [
                        "docker",
                        "exec",
                        container_id,
                        "bash",
                        "-c",
                        f"chown -R {os.getuid()}:{os.getgid()} /tmp 2>/dev/null || true",
                    ],
                    capture_output=True,
                    timeout=30,
                )
            except subprocess.TimeoutExpired:
                warn("Ownership fix timed out -- skipping")
        info(f"Removing container: {container_name}")
        try:
            subprocess.run(
                ["docker", "rm", "-f", container_name],
                capture_output=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            warn(f"docker rm -f timed out for {container_name}")
        common._active_containers.discard(container_name)
        info("Container removed.")

    try:
        if tracking == "beads":
            run_step(
                "Beads initialization (sqlite backend)",
                container_id,
                300,
                (
                    'export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH" && '
                    f"cd {work_dir} && bd init --backend sqlite"
                ),
            )
        elif tracking == "acov":
            setup_acov(
                container_id=container_id,
                work_dir=work_dir,
                acov_path=acov_path,
                acov_subsystems=acov_subsystems,
            )

        run_step(
            "Remove CLAUDE.md",
            container_id,
            30,
            f"rm -f {work_dir}/CLAUDE.md",
        )

        if agents_md_content is not None:
            step_run("Copy eval CLAUDE.md")
            if docker_pipe_stdin(container_id, agents_md_content, f"{work_dir}/CLAUDE.md"):
                step_ok("Copy eval CLAUDE.md")
            else:
                step_warn(f"Copy eval CLAUDE.md  {DIM}copy failed{NC}")

        if common.is_linux_project(project):
            setup_linux_evaluation_container(
                container_id,
                secb_config_content=linux_secb_config_content,
                instance_dir=linux_instance_dir,
            )

        step_run("Write Claude settings")
        docker_exec(container_id, "mkdir -p /root/.claude", 30)
        settings_content = json.dumps(
            {
                "model": model,
                "effortLevel": reasoning_effort,
            },
            indent=2,
        ) + "\n"
        (instance_outdir / "settings.json").write_text(settings_content, encoding="utf-8")
        if docker_pipe_stdin(container_id, settings_content, "/root/.claude/settings.json"):
            step_ok("Write Claude settings")
        else:
            step_warn(f"Write Claude settings  {DIM}copy failed{NC}")

        if skill_directory and skill_directory.is_dir():
            step_run("Copy skill files")
            docker_exec(
                container_id,
                f"mkdir -p {work_dir}/.claude/skills",
                30,
            )
            src = str(skill_directory) + "/."
            if docker_copy_to(container_id, src, f"{work_dir}/.claude/skills/"):
                skill_count = sum(1 for _ in skill_directory.rglob("SKILL.md"))
                step_ok(
                    f"Copy skill files  "
                    f"{DIM}({skill_count} skills to .claude/skills/){NC}"
                )
            else:
                step_warn(f"Copy skill files  {DIM}copy failed{NC}")

        run_step(
            "Initialize git repo",
            container_id,
            60,
            (
                f"cd {work_dir} && "
                "(git rev-parse --is-inside-work-tree 2>/dev/null || "
                "(git init && git add -A && git commit -m 'Initial commit' --allow-empty))"
            ),
        )

        if common.INTERRUPTED:
            return 130

        prompt_container_path = f"/tmp/claude-eval-prompt-{instance_id}.txt"
        docker_pipe_stdin(container_id, prompt, prompt_container_path)

        if tracking == "acov":
            path_export = (
                ACOV_PYTHON_AUDIT_ENV_SH
                + f'export PATH="{ACOV_SHIM_DIR}:$HOME/.local/bin:$HOME/.cargo/bin:/usr/local/bin:$PATH" && '
                + f'export ACOV_DB="{acov_db_container_path(work_dir)}" && '
                + f'export ACOV_EVENT_LOG="{acov_event_log_container_path(work_dir)}" && '
                + f'export ACOV_SOCKET="{ACOV_SOCKET_PATH}" && '
                + f'export ACOV_PROJECT_ROOT="{work_dir}" && '
                + f'export ACOV_SHIM_DIR="{ACOV_SHIM_DIR}" && '
            )
        else:
            path_export = (
                'export PATH="$HOME/.local/bin:$HOME/.cargo/bin:/usr/local/bin:$PATH" && '
            )

        nvm_setup = (
            'export NVM_DIR="$HOME/.nvm" && '
            '[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" 2>/dev/null; '
        )

        claude_cmd_parts = [shlex.quote(claude_cli)]
        if provider_settings.use_bare:
            claude_cmd_parts.append("--bare")
        claude_cmd_parts.extend(
            [
                '-p "$(cat ' + shlex.quote(prompt_container_path) + ')"',
                "--model",
                shlex.quote(model),
                "--output-format",
                shlex.quote(output_format),
                "--verbose",
                "--dangerously-skip-permissions",
            ]
        )
        if provider_settings.use_bare and agents_md_content is not None:
            claude_cmd_parts.extend(
                [
                    "--append-system-prompt-file",
                    shlex.quote(f"{work_dir}/CLAUDE.md"),
                ]
            )

        if allowed_tools:
            claude_cmd_parts.extend(
                ["--allowedTools", shlex.quote(",".join(allowed_tools))]
            )

        if max_budget_usd is not None:
            claude_cmd_parts.extend(
                ["--max-budget-usd", shlex.quote(str(max_budget_usd))]
            )

        if permission_mode:
            claude_cmd_parts.extend(["--permission-mode", shlex.quote(permission_mode)])

        if system_prompt:
            claude_cmd_parts.extend(
                ["--append-system-prompt", shlex.quote(system_prompt)]
            )

        claude_cmd = (
            f"{path_export}"
            f"{nvm_setup}"
            "export TERM=xterm-256color && "
            "export COLORTERM=truecolor && "
            "export FORCE_COLOR=1 && "
            f"cd {shlex.quote(work_dir)} && "
            + " ".join(claude_cmd_parts)
        )

        common._emit(
            f"  {YELLOW}\u25c9{NC} Run Claude Code agent  "
            f"{DIM}(timeout={timeout_secs}s, model={model}){NC}"
        )
        info("Agent output:")
        common._emit(f"{DIM}{'─' * 64}{NC}")

        agent_stdout_file = instance_outdir / "agent_stdout.txt"
        agent_exit = docker_exec_streaming(
            container_id,
            claude_cmd,
            timeout_secs,
            agent_stdout_file,
            agent_type="claude",
        )

        common._emit(f"{DIM}{'─' * 64}{NC}")

        if agent_exit == 0:
            step_ok(f"Run Claude Code agent  {DIM}exit 0{NC}")
        else:
            step_err(f"Run Claude Code agent  {DIM}exit {agent_exit}{NC}")
            if is_timeout_exit_code(agent_exit):
                marker_path = write_timeout_marker(
                    instance_outdir,
                    timeout_secs,
                    agent_exit,
                )
                step_warn(
                    f"Record timeout marker  {DIM}{marker_path.name} "
                    f"(timeout={timeout_secs}s){NC}"
                )

        if common.INTERRUPTED:
            return agent_exit

        step_run("Collect Claude projects")
        _rc, stdout, _stderr = docker_exec(
            container_id,
            "[ -d ~/.claude/projects ] && echo yes || echo no",
            30,
        )
        if stdout.strip().rstrip("\r") == "yes":
            projects_dest = instance_outdir / "claude_projects"
            projects_dest.mkdir(parents=True, exist_ok=True)
            if docker_copy_from(
                container_id,
                "/root/.claude/projects/.",
                str(projects_dest) + "/",
            ):
                event_count, latest_project, project_count = (
                    _write_claude_project_manifest(projects_dest, instance_outdir)
                )
                step_ok(
                    f"Collect Claude projects  "
                    f"{DIM}({project_count} project jsonl files){NC}"
                )
                if latest_project is None:
                    step_warn(f"Write Claude project manifest  {DIM}not found{NC}")
                else:
                    rel_latest = latest_project.relative_to(projects_dest)
                    step_ok(
                        f"Write Claude project manifest  {DIM}"
                        f"{rel_latest} ({event_count} events){NC}"
                    )
            else:
                step_warn(f"Collect Claude projects  {DIM}copy failed{NC}")
        else:
            step_warn(f"Collect Claude projects  {DIM}not found{NC}")

        collect_audit_artifacts(container_id, work_dir, instance_outdir)

        if tracking == "beads":
            collect_beads_artifacts(container_id, work_dir, instance_outdir)
        elif tracking == "acov":
            collect_acov_artifacts(container_id, instance_outdir, work_dir)

        collect_result_files(container_id, work_dir, instance_outdir)

    finally:
        _cleanup_container()

    return agent_exit


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate Claude Code agent inside Docker containers",
    )
    parser.add_argument(
        "config",
        type=Path,
        help="Path to TOML config file",
    )
    parser.add_argument(
        "--no-tui",
        action="store_true",
        default=False,
        help="Disable the Rich progress bar (plain output only).",
    )
    args = parser.parse_args()

    config_path = args.config.resolve()
    if not config_path.is_file():
        error(f"Config file not found: {config_path}")
        return 1

    info(f"Loading config: {config_path}")
    try:
        config = load_config(config_path)
    except ValueError as exc:
        error(str(exc))
        return 1

    model = config["model"]
    timeout_secs: int = config["timeout"]
    outdir = resolve_path(SCRIPT_DIR, config["outdir"])
    prompt_template_path = resolve_path(SCRIPT_DIR, config["prompt_template"])
    images_dir = resolve_path(SCRIPT_DIR, config["images_dir"])
    try:
        instances = resolve_instances(config, images_dir)
    except ValueError as exc:
        error(str(exc))
        return 1

    tracking: str = config.get("tracking", "beads")
    provider = config.get("provider", "bedrock")
    if provider not in _CLAUDE_PROVIDER_SETTINGS:
        error(
            f"Invalid provider '{provider}'. Must be one of: "
            f"{', '.join(sorted(_CLAUDE_PROVIDER_SETTINGS))}."
        )
        return 1
    config.setdefault("provider", provider)

    reasoning_effort = config.get("reasoning_effort", "high")
    if not isinstance(reasoning_effort, str) or not reasoning_effort.strip():
        error("Invalid reasoning_effort. Must be a non-empty string.")
        return 1
    config["reasoning_effort"] = reasoning_effort

    if "privileged" in config and not isinstance(config["privileged"], bool):
        error("Invalid privileged. Must be true or false.")
        return 1
    config["privileged"] = config.get(
        "privileged",
        common.is_linux_project(config.get("project", "")),
    )

    skill_directory: Path | None = None
    if config.get("skill_directory"):
        skill_directory = resolve_path(SCRIPT_DIR, config["skill_directory"])

    agents_md: Path | None = None
    if config.get("agents_md"):
        agents_md = resolve_path(SCRIPT_DIR, config["agents_md"])

    acov_path: Path | None = None
    acov_subsystems: str | None = config.get("acov_subsystems")
    if tracking == "acov":
        acov_path = resolve_path(SCRIPT_DIR, config["acov_path"])
        if not acov_path.is_dir():
            error(f"acov project not found: {acov_path}")
            return 1
        ac_bin = acov_path / "target" / "release" / "ac"
        shim_bin = acov_path / "target" / "release" / "acov-shim"
        if not ac_bin.is_file() or not shim_bin.is_file():
            error(
                f"acov binaries not found at {acov_path / 'target/release/'}. "
                "Build first: cd acov && cargo build --release"
            )
            return 1

    if not prompt_template_path.is_file():
        error(f"Prompt template not found: {prompt_template_path}")
        return 1

    try:
        docker_preflight()
    except RuntimeError as exc:
        error(str(exc))
        return 1

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_outdir = outdir / timestamp
    run_outdir.mkdir(parents=True, exist_ok=True)

    info(f"Output directory: {run_outdir}")
    info(f"Model: {model}")
    info(f"Provider: {provider}")
    info(f"Tracking: {tracking}")
    info(f"Timeout: {timeout_secs}s")
    info(f"Output format: {config.get('output_format', 'stream-json')}")
    info(f"Reasoning effort: {config['reasoning_effort']}")
    if config.get("privileged", False):
        info("Docker privileged mode: true")
    if skill_directory:
        info(f"Skill directory: {skill_directory}")
    if agents_md:
        info(f"Agents MD: {agents_md}")
    if acov_path:
        info(f"acov path: {acov_path}")
        if acov_subsystems:
            info(f"acov subsystems: {acov_subsystems}")
    if config.get("max_budget_usd") is not None:
        info(f"Max budget: ${config['max_budget_usd']}")
    if config.get("permission_mode"):
        info(f"Permission mode: {config['permission_mode']}")
    info(f"Instances: {' '.join(instances)}")

    return run_eval_loop(
        instances=instances,
        images_dir=images_dir,
        run_outdir=run_outdir,
        prompt_template_path=prompt_template_path,
        config=config,
        agent_label=f"claude/{model}",
        run_instance_fn=run_instance,
        use_tui=not args.no_tui,
        agents_md=agents_md,
        agents_md_artifact_name="CLAUDE.md",
        skill_directory=skill_directory,
        acov_path=acov_path,
        acov_subsystems=acov_subsystems,
    )


if __name__ == "__main__":
    sys.exit(main())
