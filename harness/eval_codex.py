"""Evaluation harness for OpenAI Codex agent inside Docker containers.

Usage::

    uv run harness/eval_codex.py harness/configs/codex/v8/baseline_gpt-5.4.toml
    python3 harness/eval_codex.py harness/configs/codex/sm/baseline_gpt-5.4.toml --no-tui

The script:

1.  Loads a TOML config describing model, instances, timeout, etc.
2.  For each benchmark instance: starts a privileged container,
    configures Codex auth, runs the agent, collects artifacts
    (Codex sessions, audit files, tracking database), and tears down.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import common
from common import (
    ACOV_PYTHON_AUDIT_ENV_SH,
    ACOV_SHIM_DIR,
    ACOV_SOCKET_PATH,
    BOLD,
    acov_db_container_path,
    acov_event_log_container_path,
    bash_codex_native_and_acov_path,
    CYAN,
    DIM,
    NC,
    SCRIPT_DIR,
    YELLOW,
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
    load_config,
    resolve_instances,
    resolve_path,
    run_eval_loop,
    run_step,
    setup_acov,
    setup_linux_evaluation_container,
    is_timeout_exit_code,
    step_err,
    step_ok,
    step_run,
    step_warn,
    warn,
    write_timeout_marker,
)

# ---------------------------------------------------------------------------
# Codex-specific environment variables
# ---------------------------------------------------------------------------

_CODEX_FORWARDED_ENV_VARS = ("OPENAI_API_KEY",)


# ---------------------------------------------------------------------------
# Codex artifact helpers
# ---------------------------------------------------------------------------


def _inspect_codex_sessions(sessions_dest: Path) -> tuple[int, Path | None]:
    """Return ``(jsonl_count, first_invalid_file)`` for copied Codex sessions."""
    session_count = 0
    for session_file in sorted(sessions_dest.rglob("*.jsonl")):
        session_count += 1
        try:
            with session_file.open("r", encoding="utf-8") as fh:
                for line in fh:
                    if line.strip():
                        json.loads(line)
                        break
                else:
                    return session_count, session_file
        except (OSError, json.JSONDecodeError):
            return session_count, session_file
    return session_count, None


def _write_codex_session_manifest(
    sessions_dest: Path,
    instance_outdir: Path,
) -> tuple[int, Path | None]:
    """Record the selected Codex session without duplicating session JSONL."""
    session_files = sorted(
        sessions_dest.rglob("*.jsonl"),
        key=lambda path: (path.stat().st_mtime, str(path)),
        reverse=True,
    )
    if not session_files:
        return 0, None

    latest = session_files[0]
    event_count = 0
    with latest.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.strip():
                event_count += 1

    manifest = {
        "source": str(latest.relative_to(instance_outdir)),
        "events": event_count,
        "sessions": len(session_files),
    }
    (instance_outdir / "codex_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return event_count, latest


# ---------------------------------------------------------------------------
# Per-instance runner
# ---------------------------------------------------------------------------


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
    """Run the full evaluation lifecycle for one benchmark instance.

    1.  Start a privileged detached container.
    2.  Configure Codex auth, tracking, protocol files, skills.
    3.  Run the Codex agent with the rendered prompt.
    4.  Collect all artifacts.
    5.  Tear down the container.

    Returns the agent process exit code (0 = success).
    """
    model = config["model"]
    timeout_secs: int = config["timeout"]
    tracking: str = config.get("tracking", "beads")
    project: str = config.get("project", "")

    # Codex-specific config
    codex_cli: str = config.get("codex_cli", "codex")
    approval_mode: str = config.get("approval_mode", "full-auto")
    sandbox: str = config.get("sandbox", "danger-full-access")
    json_output: bool = config.get("json_output", False)
    copy_host_auth: bool = config.get("copy_host_auth", False)
    reasoning_effort: str = config["reasoning_effort"]

    container_name = f"codex-eval-{instance_id}-{int(datetime.now().timestamp())}"

    common._emit(f"\n{CYAN}{BOLD}>>> Instance: {instance_id} <<<{NC}")
    info(f"Image: {image_name}")
    info(f"Work dir: {work_dir}")

    # -- Ensure Docker image is available ----------------------------------
    rc = subprocess.run(
        ["docker", "image", "inspect", image_name],
        capture_output=True,
    ).returncode
    if rc != 0:
        info(f"Pulling Docker image: {image_name}")
        subprocess.run(["docker", "pull", image_name], check=True)
    else:
        info(f"Docker image found locally: {image_name}")

    # -- Start detached container (--privileged for Codex) -----------------
    env_args = build_env_args(_CODEX_FORWARDED_ENV_VARS)
    info(f"Starting container: {container_name}")
    result = subprocess.run(
        [
            "docker",
            "run",
            "--detach",
            "--name",
            container_name,
            "--privileged",
            *env_args,
            image_name,
            "bash",
            "-c",
            "sleep infinity",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    container_id = result.stdout.strip()
    info(f"Container started: {container_id[:12]}")
    common._active_containers.add(container_name)

    agent_exit = 1

    # -- Cleanup closure ---------------------------------------------------
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
        # ==================================================================
        # Setup steps
        # ==================================================================

        # 1. Configure Codex auth.json
        host_auth = Path.home() / ".codex" / "auth.json"
        if copy_host_auth and host_auth.is_file():
            step_run("Copy host auth.json to container")
            docker_exec(container_id, "mkdir -p /root/.codex/", 10)
            if docker_copy_to(
                container_id,
                str(host_auth),
                "/root/.codex/auth.json",
            ):
                step_ok("Copy host auth.json to container")
            else:
                step_warn(f"Copy host auth.json to container  {DIM}copy failed{NC}")
        else:
            run_step(
                "Update Codex auth.json with OPENAI_API_KEY",
                container_id,
                30,
                (
                    'python3 -c "'
                    "import json, os, pathlib; "
                    'p = pathlib.Path(\\"/root/.codex/auth.json\\"); '
                    "p.parent.mkdir(parents=True, exist_ok=True); "
                    "cfg = json.loads(p.read_text()) if p.exists() else {}; "
                    'cfg[\\"OPENAI_API_KEY\\"] = os.environ.get(\\"OPENAI_API_KEY\\", \\"\\"); '
                    "p.write_text(json.dumps(cfg, indent=2))"
                    '"'
                ),
            )

        step_run("Write Codex config")
        docker_exec(container_id, "mkdir -p /root/.codex/", 10)
        codex_config_content = (
            f"model = {json.dumps(model)}\n"
            f"model_reasoning_effort = {json.dumps(reasoning_effort)}\n"
        )
        (instance_outdir / "config.toml").write_text(
            codex_config_content,
            encoding="utf-8",
        )
        if docker_pipe_stdin(container_id, codex_config_content, "/root/.codex/config.toml"):
            step_ok("Write Codex config")
        else:
            step_warn(f"Write Codex config  {DIM}copy failed{NC}")

        # 2. Tracking-specific initialization
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

        # 3. Remove existing AGENTS.md, copy eval protocol
        run_step(
            "Remove AGENTS.md",
            container_id,
            30,
            f"rm -f {work_dir}/AGENTS.md",
        )

        if agents_md_content is not None:
            step_run("Copy eval AGENTS.md")
            if docker_pipe_stdin(container_id, agents_md_content, f"{work_dir}/AGENTS.md"):
                step_ok("Copy eval AGENTS.md")
            else:
                step_warn(f"Copy eval AGENTS.md  {DIM}copy failed{NC}")

        if common.is_linux_project(project):
            setup_linux_evaluation_container(
                container_id,
                secb_config_content=linux_secb_config_content,
                instance_dir=linux_instance_dir,
            )

        # 4. Copy skill files to .agents/skills/
        if skill_directory and skill_directory.is_dir():
            step_run("Copy skill files")
            docker_exec(
                container_id,
                f"mkdir -p {work_dir}/.agents/skills",
                30,
            )
            src = str(skill_directory) + "/."
            if docker_copy_to(container_id, src, f"{work_dir}/.agents/skills/"):
                skill_count = sum(1 for _ in skill_directory.rglob("SKILL.md"))
                step_ok(
                    f"Copy skill files  "
                    f"{DIM}({skill_count} skills to .agents/skills/){NC}"
                )
            else:
                step_warn(f"Copy skill files  {DIM}copy failed{NC}")

        # 5. Initialize git repo (Codex requires a git repo)
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

        # ==================================================================
        # Run Codex agent
        # ==================================================================
        if common.INTERRUPTED:
            return 130

        # Write prompt into the container
        prompt_container_path = f"/tmp/codex-eval-prompt-{instance_id}.txt"
        docker_pipe_stdin(container_id, prompt, prompt_container_path)

        # Source nvm first so ``npm root -g`` works for Codex path resolution.
        nvm_setup = (
            'export NVM_DIR="$HOME/.nvm" && '
            '[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" 2>/dev/null; '
        )

        # acov: native Codex binary + PATH (shims before bundled rg). See
        # ``bash_codex_native_and_acov_path`` docstring.
        if tracking == "acov":
            path_export = (
                ACOV_PYTHON_AUDIT_ENV_SH
                + bash_codex_native_and_acov_path(
                    shim_dir=ACOV_SHIM_DIR,
                    codex_cli_fallback=codex_cli,
                )
                + f'export ACOV_DB="{acov_db_container_path(work_dir)}" && '
                f'export ACOV_EVENT_LOG="{acov_event_log_container_path(work_dir)}" && '
                f'export ACOV_SOCKET="{ACOV_SOCKET_PATH}" && '
                f'export ACOV_PROJECT_ROOT="{work_dir}" && '
                f'export ACOV_SHIM_DIR="{ACOV_SHIM_DIR}" && '
            )
            codex_invoker = '"${CODEX_EXE:-$CODEX_CLI_FALLBACK}"'
        else:
            path_export = 'export PATH="$HOME/.local/bin:$HOME/.cargo/bin:/usr/local/bin:$PATH" && '
            codex_invoker = codex_cli

        # Build the codex CLI command
        # Approval policy is a top-level Codex option in current CLI versions,
        # while sandbox remains accepted on `codex exec`.
        approval_flag = "-a never " if approval_mode == "full-auto" else f"-a {approval_mode} "

        codex_cmd = (
            f"{nvm_setup}"
            f"{path_export}"
            "export TERM=xterm-256color && "
            "export COLORTERM=truecolor && "
            "export FORCE_COLOR=1 && "
            "export RUST_LOG='codex_core::session=off' && "
            f"cd {work_dir} && "
            f"{codex_invoker} "
            f"{approval_flag}"
            "exec "
            f"-s {sandbox} "
        )

        # Optional JSON output
        if json_output:
            codex_cmd += "--json "

        codex_cmd += f'"$(cat {prompt_container_path})"'

        common._emit(
            f"  {YELLOW}\u25c9{NC} Run Codex agent  "
            f"{DIM}(timeout={timeout_secs}s, model={model}){NC}"
        )
        info("Agent output:")
        common._emit(f"{DIM}{'─' * 64}{NC}")

        agent_stdout_file = instance_outdir / "agent_stdout.txt"

        agent_exit = docker_exec_streaming(
            container_id,
            codex_cmd,
            timeout_secs,
            agent_stdout_file,
            agent_type="codex",
        )

        common._emit(f"{DIM}{'─' * 64}{NC}")

        if agent_exit == 0:
            step_ok(f"Run Codex agent  {DIM}exit 0{NC}")
        else:
            step_err(f"Run Codex agent  {DIM}exit {agent_exit}{NC}")
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

        # ==================================================================
        # Collect artifacts (skip entirely when interrupted)
        # ==================================================================
        if common.INTERRUPTED:
            return agent_exit

        # -- Codex sessions (trajectories) ---------------------------------
        step_run("Collect Codex sessions")
        rc, stdout, _ = docker_exec(
            container_id,
            "[ -d ~/.codex/sessions ] && echo yes || echo no",
            30,
        )
        if stdout.strip().rstrip("\r") == "yes":
            sessions_dest = instance_outdir / "codex_sessions"
            sessions_dest.mkdir(parents=True, exist_ok=True)
            if docker_copy_from(
                container_id,
                "/root/.codex/sessions/.",
                str(sessions_dest) + "/",
            ):
                session_count, invalid_session = _inspect_codex_sessions(sessions_dest)
                if invalid_session is not None:
                    rel_invalid = invalid_session.relative_to(sessions_dest)
                    step_warn(
                        f"Collect Codex sessions  {DIM}"
                        f"invalid jsonl: {rel_invalid}{NC}"
                    )
                elif session_count == 0:
                    step_warn(f"Collect Codex sessions  {DIM}no jsonl files{NC}")
                else:
                    step_ok(
                        f"Collect Codex sessions  {DIM}"
                        f"({session_count} valid jsonl files){NC}"
                    )
                    step_run("Write Codex session manifest")
                    event_count, latest_session = _write_codex_session_manifest(
                        sessions_dest,
                        instance_outdir,
                    )
                    if latest_session is None:
                        step_warn(f"Write Codex session manifest  {DIM}not found{NC}")
                    else:
                        rel_latest = latest_session.relative_to(sessions_dest)
                        step_ok(
                            f"Write Codex session manifest  {DIM}"
                            f"{rel_latest} ({event_count} events){NC}"
                        )
            else:
                step_warn(f"Collect Codex sessions  {DIM}copy failed{NC}")
        else:
            step_warn(f"Collect Codex sessions  {DIM}not found{NC}")

        # -- Audit artifacts -----------------------------------------------
        collect_audit_artifacts(container_id, work_dir, instance_outdir)

        # -- Tracking database (beads or acov) -----------------------------
        if tracking == "beads":
            collect_beads_artifacts(container_id, work_dir, instance_outdir)
        elif tracking == "acov":
            collect_acov_artifacts(container_id, instance_outdir, work_dir)

        # -- Result files --------------------------------------------------
        collect_result_files(container_id, work_dir, instance_outdir)

    finally:
        _cleanup_container()

    return agent_exit


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate Codex agent inside Docker containers",
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

    # -- Load config -------------------------------------------------------
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

    # -- Resolve all paths from config -------------------------------------
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
    if "json_output" in config and not isinstance(config["json_output"], bool):
        error("Invalid json_output. Must be true or false.")
        return 1

    reasoning_effort = config.get("reasoning_effort", "high")
    if not isinstance(reasoning_effort, str) or not reasoning_effort.strip():
        error("Invalid reasoning_effort. Must be a non-empty string.")
        return 1
    config["reasoning_effort"] = reasoning_effort

    # Optional fields
    skill_directory: Path | None = None
    if config.get("skill_directory"):
        skill_directory = resolve_path(SCRIPT_DIR, config["skill_directory"])

    agents_md: Path | None = None
    if config.get("agents_md"):
        agents_md = resolve_path(SCRIPT_DIR, config["agents_md"])

    # acov-specific fields
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

    # -- Validate prompt template ------------------------------------------
    if not prompt_template_path.is_file():
        error(f"Prompt template not found: {prompt_template_path}")
        return 1

    # -- Docker preflight --------------------------------------------------
    try:
        docker_preflight()
    except RuntimeError as exc:
        error(str(exc))
        return 1

    # -- Create run output directory ---------------------------------------
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_outdir = outdir / timestamp
    run_outdir.mkdir(parents=True, exist_ok=True)

    info(f"Output directory: {run_outdir}")
    info(f"Model: {model}")
    info(f"Tracking: {tracking}")
    info(f"Timeout: {timeout_secs}s")
    info(f"Reasoning effort: {config['reasoning_effort']}")
    info(f"Approval mode: {config.get('approval_mode', 'full-auto')}")
    info(f"Sandbox: {config.get('sandbox', 'danger-full-access')}")
    info(f"JSON output: {str(config.get('json_output', False)).lower()}")
    if skill_directory:
        info(f"Skill directory: {skill_directory}")
    if agents_md:
        info(f"Agents MD: {agents_md}")
    if acov_path:
        info(f"acov path: {acov_path}")
        if acov_subsystems:
            info(f"acov subsystems: {acov_subsystems}")
    info(f"Instances: {' '.join(instances)}")

    # -- Main instance loop ------------------------------------------------
    return run_eval_loop(
        instances=instances,
        images_dir=images_dir,
        run_outdir=run_outdir,
        prompt_template_path=prompt_template_path,
        config=config,
        agent_label=f"codex/{model}",
        run_instance_fn=run_instance,
        use_tui=not args.no_tui,
        agents_md=agents_md,
        skill_directory=skill_directory,
        acov_path=acov_path,
        acov_subsystems=acov_subsystems,
    )


if __name__ == "__main__":
    sys.exit(main())
