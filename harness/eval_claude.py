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
    install_cached_sandbox_tools,
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
    settings_env: tuple[tuple[str, object], ...] = ()
    default_reasoning_effort: str | None = None


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
    "glm": ClaudeProviderSettings(
        forwarded_env_vars=("ANTHROPIC_AUTH_TOKEN",),
        # Bare mode accepts ANTHROPIC_API_KEY only; Z.AI uses the auth token.
        use_bare=False,
        required_host_env_var="ANTHROPIC_AUTH_TOKEN",
        settings_env=(
            ("ANTHROPIC_BASE_URL", "https://api.z.ai/api/anthropic"),
            ("ANTHROPIC_DEFAULT_HAIKU_MODEL", "glm-4.7"),
            ("CLAUDE_CODE_AUTO_COMPACT_WINDOW", "1000000"),
            ("CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC", 1),
            ("API_TIMEOUT_MS", "3000000"),
        ),
        default_reasoning_effort="max",
    ),
}

_CLAUDE_EXTRA_ENV = {
    "IS_SANDBOX": "1",
}

_CLAUDE_AUTH_CONTAINER_PATH = "/root/.claude/.credentials.json"
_CLAUDE_JSON_CONTAINER_PATH = "/root/.claude.json"
_CLAUDE_AUTH_ENV_VARS = (
    "CLAUDE_CODE_USE_BEDROCK",
    "CLAUDE_CODE_USE_VERTEX",
    "CLAUDE_CODE_USE_FOUNDRY",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_API_KEY",
    "CLAUDE_CODE_OAUTH_TOKEN",
)
_CLAUDE_EVAL_SETTINGS_CONTAINER_PATH = "/tmp/claude-eval-settings.json"
_CLAUDE_EVAL_MCP_CONFIG_CONTAINER_PATH = "/tmp/claude-eval-mcp.json"


def _claude_container_security_args(
    *,
    privileged: bool,
    claude_sandbox: bool,
) -> list[str]:
    if privileged:
        return ["--privileged"]
    if claude_sandbox:
        # Claude's weaker nested sandbox creates its own user namespace. The
        # outer profiles must permit those syscalls, but no added capability is
        # needed by the evaluation container itself.
        return [
            "--security-opt",
            "apparmor=unconfined",
            "--security-opt",
            "seccomp=unconfined",
        ]
    return []


def _copy_required_file_to_container(
    *,
    container_id: str,
    label: str,
    source: str,
    destination: str,
    setup_cmd: str | None = None,
    timeout_secs: int = 30,
) -> int:
    step_run(label)
    if setup_cmd is not None:
        setup_rc, _stdout, setup_stderr = docker_exec(
            container_id,
            setup_cmd,
            timeout_secs,
        )
        if setup_rc != 0:
            detail = (
                setup_stderr[:120].replace("\n", " ") if setup_stderr else ""
            )
            step_err(
                f"{label}  {DIM}(setup failed: {detail or f'exit {setup_rc}'}){NC}"
            )
            return setup_rc

    if not docker_copy_to(container_id, source, destination):
        step_err(f"{label}  {DIM}copy failed{NC}")
        return 1

    chmod_rc, _stdout, chmod_stderr = docker_exec(
        container_id,
        f"chown root:root {shlex.quote(destination)} && "
        f"chmod 600 {shlex.quote(destination)}",
        timeout_secs,
    )
    if chmod_rc != 0:
        detail = chmod_stderr[:120].replace("\n", " ") if chmod_stderr else ""
        step_err(
            f"{label}  {DIM}(chmod failed: {detail or f'exit {chmod_rc}'}){NC}"
        )
        return chmod_rc

    step_ok(f"{label}  {DIM}({destination}){NC}")
    return 0


def _ensure_claude_sandbox_dependencies(container_id: str) -> int:
    """Install Claude Code's Linux sandbox helpers when an image is missing them."""
    step_run("Ensure Claude sandbox dependencies")
    check_cmd = "command -v bwrap >/dev/null 2>&1 && command -v socat >/dev/null 2>&1"
    check_rc, _stdout, _stderr = docker_exec(container_id, check_cmd, 30)
    if check_rc == 0:
        step_ok("Ensure Claude sandbox dependencies")
        return 0

    cache_ok, cache_detail = install_cached_sandbox_tools(
        container_id,
        ("bwrap", "socat"),
    )
    if cache_ok:
        step_ok(
            "Ensure Claude sandbox dependencies  "
            f"{DIM}({cache_detail}){NC}"
        )
        return 0
    step_warn(
        "Ensure Claude sandbox dependencies  "
        f"{DIM}(cache unavailable: {cache_detail}; trying package manager){NC}"
    )

    install_cmd = r"""
set -eu
log=/tmp/claude-sandbox-deps-install.log
: > "$log"
if command -v apt-get >/dev/null 2>&1; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get -o DPkg::Lock::Timeout=60 update -qq >>"$log" 2>&1
  apt-get -o DPkg::Lock::Timeout=60 install -y -qq --no-install-recommends \
    bubblewrap socat >>"$log" 2>&1
  rm -rf /var/lib/apt/lists/*
elif command -v apk >/dev/null 2>&1; then
  apk add --no-cache bubblewrap socat >>"$log" 2>&1
elif command -v dnf >/dev/null 2>&1; then
  dnf install -y bubblewrap socat >>"$log" 2>&1
elif command -v yum >/dev/null 2>&1; then
  yum install -y bubblewrap socat >>"$log" 2>&1
else
  echo "no supported package manager found" >>"$log"
  exit 127
fi
command -v bwrap >/dev/null 2>&1
command -v socat >/dev/null 2>&1
"""
    install_rc, _stdout, stderr = docker_exec(container_id, install_cmd, 300)
    if install_rc == 0:
        step_ok(f"Ensure Claude sandbox dependencies  {DIM}(installed){NC}")
        return 0

    _tail_rc, tail_stdout, _tail_stderr = docker_exec(
        container_id,
        "tail -n 20 /tmp/claude-sandbox-deps-install.log 2>/dev/null || true",
        30,
    )
    detail_source = tail_stdout or stderr
    detail = detail_source[:240].replace("\n", " ") if detail_source else ""
    step_err(
        "Ensure Claude sandbox dependencies  "
        f"{DIM}(failed: {detail or f'exit {install_rc}'}){NC}"
    )
    return install_rc


def _deep_merge_settings(
    base: dict[str, object],
    override: dict[str, object],
) -> dict[str, object]:
    """Merge Claude settings dictionaries without mutating either input."""
    merged = dict(base)
    for key, value in override.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            merged[key] = _deep_merge_settings(current, value)
        else:
            merged[key] = value
    return merged


def _build_claude_settings(config: dict) -> dict[str, object]:
    provider = config.get("provider", "bedrock")
    provider_settings = _CLAUDE_PROVIDER_SETTINGS[provider]
    defaults: dict[str, object] = {}
    if config.get("claude_sandbox", False):
        # The evaluator itself runs in Docker. Claude's documented nested mode
        # avoids a second user/PID namespace layer that Docker may reject.
        defaults["sandbox"] = {"enableWeakerNestedSandbox": True}
    if provider_settings.settings_env:
        provider_env = dict(provider_settings.settings_env)
        if provider == "glm":
            model = config["model"]
            provider_env["ANTHROPIC_DEFAULT_SONNET_MODEL"] = model
            provider_env["ANTHROPIC_DEFAULT_OPUS_MODEL"] = model
        defaults["env"] = provider_env

    custom_settings = config.get("claude_settings") or {}
    return _deep_merge_settings(defaults, custom_settings)


def _normalize_tool_entries(value: object, key: str) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else None
    if isinstance(value, list):
        normalized: list[str] = []
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise ValueError(f"Invalid {key}. Entries must be non-empty strings.")
            normalized.append(item.strip())
        return normalized
    raise ValueError(f"Invalid {key}. Must be a string or list of strings.")


def _tool_arg(entries: list[str] | None) -> str | None:
    return ",".join(entries) if entries else None


def _normalize_tool_arg(value: object, key: str) -> str | None:
    return _tool_arg(_normalize_tool_entries(value, key))


def _builtin_tool_entries(entries: list[str] | None) -> list[str] | None:
    if not entries:
        return None
    return [entry for entry in entries if not entry.startswith("mcp__")]


def _normalize_claude_mcp_servers(value: object) -> dict[str, object]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("Invalid mcp_servers. Must be a TOML table.")

    normalized: dict[str, object] = {}
    for name, server_config in value.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Invalid mcp_servers. Server names must be non-empty strings.")
        if not isinstance(server_config, dict):
            raise ValueError(f"Invalid mcp_servers.{name}. Must be a TOML table.")

        server_type = server_config.get("type", "stdio")
        if not isinstance(server_type, str) or not server_type.strip():
            raise ValueError(f"Invalid mcp_servers.{name}.type. Must be a string.")
        server_type = server_type.strip()

        if server_type != "stdio":
            raise ValueError(
                f"Invalid mcp_servers.{name}.type. Only 'stdio' is supported "
                "for in-container benchmark MCP servers."
            )

        command = server_config.get("command")
        if not isinstance(command, str) or not command.strip():
            raise ValueError(
                f"Invalid mcp_servers.{name}.command. Must be a non-empty string."
            )

        server: dict[str, object] = {
            "type": "stdio",
            "command": command.strip(),
        }

        args = server_config.get("args")
        if args is not None:
            if not isinstance(args, list) or not all(
                isinstance(item, str) and item.strip() for item in args
            ):
                raise ValueError(
                    f"Invalid mcp_servers.{name}.args. Must be a list of strings."
                )
            server["args"] = [item.strip() for item in args]

        env = server_config.get("env")
        if env is not None:
            if not isinstance(env, dict) or not all(
                isinstance(key, str)
                and key.strip()
                and isinstance(val, str)
                for key, val in env.items()
            ):
                raise ValueError(
                    f"Invalid mcp_servers.{name}.env. Must be a string map."
                )
            server["env"] = {key.strip(): val for key, val in env.items()}

        normalized[name.strip()] = server

    return normalized


def _build_claude_mcp_config(config: dict) -> dict[str, object]:
    mcp_servers = config.get("mcp_servers") or {}
    return {"mcpServers": mcp_servers}


def _setup_secb_mcp(container_id: str, config: dict) -> int:
    """Install the vendored `secb-linux-vm-mcp` package in the container."""
    mcp_servers = config.get("mcp_servers") or {}
    if "secb" not in mcp_servers:
        return 0

    step_run("Set up secb MCP server")
    mcps_src = Path(__file__).resolve().parent.parent / "mcps" / "linux"
    if not mcps_src.is_dir():
        step_err(f"Set up secb MCP server  {DIM}vendored mcps/linux not found{NC}")
        return 1
    if not docker_copy_to(container_id, str(mcps_src), "/opt/secb-mcps/linux"):
        step_err(f"Set up secb MCP server  {DIM}copy failed{NC}")
        return 1
    install_rc, _stdout, install_stderr = docker_exec(
        container_id,
        "(uv pip install --system /opt/secb-mcps/linux "
        "|| python3 -m pip install --break-system-packages /opt/secb-mcps/linux)",
        900,
    )
    if install_rc != 0:
        detail = install_stderr[:160].replace("\n", " ") if install_stderr else ""
        step_err(f"Set up secb MCP server  {DIM}install failed: {detail}{NC}")
        return install_rc
    step_ok(f"Set up secb MCP server  {DIM}(installed from vendored mcps/){NC}")
    return 0


def _validate_claude_sandbox_config(config: dict) -> None:
    if not config.get("claude_sandbox", False):
        return

    if config.get("dangerously_skip_permissions", False):
        raise ValueError(
            "dangerously_skip_permissions=true conflicts with claude_sandbox=true."
        )
    if config.get("permission_mode") == "bypassPermissions":
        raise ValueError(
            "permission_mode='bypassPermissions' conflicts with claude_sandbox=true."
        )

    settings = _build_claude_settings(config)
    sandbox = settings.get("sandbox")
    if not isinstance(sandbox, dict):
        raise ValueError("claude_sandbox=true requires a sandbox settings object.")
    if sandbox.get("enabled") is not True:
        raise ValueError("claude_sandbox=true requires sandbox.enabled=true.")
    if sandbox.get("failIfUnavailable") is not True:
        raise ValueError("claude_sandbox=true requires sandbox.failIfUnavailable=true.")
    if sandbox.get("allowUnsandboxedCommands") is not False:
        raise ValueError(
            "claude_sandbox=true requires sandbox.allowUnsandboxedCommands=false."
        )
    network = sandbox.get("network")
    denied_domains = (
        network.get("deniedDomains")
        if isinstance(network, dict)
        else None
    )
    if not isinstance(denied_domains, list) or "*" not in denied_domains:
        raise ValueError(
            "claude_sandbox=true requires sandbox.network.deniedDomains to include '*'."
        )


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
    tools_arg: str | None = config.get("tools_arg")
    allowed_tools_arg: str | None = config.get("allowed_tools_arg")
    disallowed_tools_arg: str | None = config.get("disallowed_tools_arg")
    mcp_config_arg: str | None = config.get("mcp_config_arg")
    output_format: str = config.get("output_format", "stream-json")
    permission_mode: str | None = config.get("permission_mode")
    system_prompt: str | None = config.get("system_prompt")
    reasoning_effort: str = config["reasoning_effort"]
    privileged: bool = config.get("privileged", common.is_linux_project(project))
    copy_host_auth: str | None = config.get("copy_host_auth")
    copy_host_claude_json: str | None = config.get("copy_host_claude_json")
    update_claude_cli: bool = config.get("update_claude_cli", False)
    dangerously_skip_permissions: bool = config["dangerously_skip_permissions"]
    claude_sandbox: bool = config.get("claude_sandbox", False)
    strict_mcp_config: bool = config.get("strict_mcp_config", False)
    use_bare = provider_settings.use_bare and copy_host_auth is None

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

    forwarded_env_vars = () if copy_host_auth else provider_settings.forwarded_env_vars
    extra_env = dict(_CLAUDE_EXTRA_ENV)
    if copy_host_auth:
        extra_env.update({var: "" for var in _CLAUDE_AUTH_ENV_VARS})
    env_args = build_env_args(forwarded_env_vars, extra_env=extra_env)
    required_host_env_var = provider_settings.required_host_env_var
    if (
        not copy_host_auth
        and required_host_env_var
        and not os.environ.get(required_host_env_var)
    ):
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
        *_claude_container_security_args(
            privileged=privileged,
            claude_sandbox=claude_sandbox,
        ),
    ]
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
        if update_claude_cli:
            update_rc = run_step(
                "Update Claude CLI",
                container_id,
                300,
                (
                    'export PATH="$HOME/.local/bin:$HOME/.cargo/bin:/usr/local/bin:$PATH" && '
                    f"{shlex.quote(claude_cli)} update && "
                    f"{shlex.quote(claude_cli)} --version"
                ),
            )
            if update_rc != 0:
                return update_rc

        if copy_host_auth:
            auth_rc = _copy_required_file_to_container(
                container_id=container_id,
                label="Copy host auth to container",
                source=copy_host_auth,
                destination=_CLAUDE_AUTH_CONTAINER_PATH,
                setup_cmd="mkdir -p /root/.claude",
            )
            if auth_rc != 0:
                return auth_rc

        if copy_host_claude_json:
            claude_json_rc = _copy_required_file_to_container(
                container_id=container_id,
                label="Copy host .claude.json to container",
                source=copy_host_claude_json,
                destination=_CLAUDE_JSON_CONTAINER_PATH,
            )
            if claude_json_rc != 0:
                return claude_json_rc

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

        secb_mcp_rc = _setup_secb_mcp(container_id, config)
        if secb_mcp_rc != 0:
            return secb_mcp_rc

        step_run("Write Claude settings")
        docker_exec(container_id, "mkdir -p /root/.claude", 30)
        settings = _build_claude_settings(config)
        settings_content = json.dumps(
            settings,
            indent=2,
            sort_keys=True,
        ) + "\n"
        (instance_outdir / "settings.json").write_text(settings_content, encoding="utf-8")
        settings_written = docker_pipe_stdin(
            container_id,
            settings_content,
            _CLAUDE_EVAL_SETTINGS_CONTAINER_PATH,
        )
        if settings_written:
            step_ok("Write Claude settings")
        else:
            step_warn(f"Write Claude settings  {DIM}copy failed{NC}")
            if claude_sandbox:
                return 1

        if mcp_config_arg:
            step_run("Write Claude MCP config")
            mcp_config_content = json.dumps(
                _build_claude_mcp_config(config),
                indent=2,
                sort_keys=True,
            ) + "\n"
            (instance_outdir / "mcp.json").write_text(
                mcp_config_content,
                encoding="utf-8",
            )
            if docker_pipe_stdin(
                container_id,
                mcp_config_content,
                mcp_config_arg,
            ):
                step_ok("Write Claude MCP config")
            else:
                step_warn(f"Write Claude MCP config  {DIM}copy failed{NC}")
                return 1

        if claude_sandbox:
            sandbox_dep_rc = _ensure_claude_sandbox_dependencies(container_id)
            if sandbox_dep_rc != 0:
                return sandbox_dep_rc

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
        effort_env = (
            "export CLAUDE_CODE_EFFORT_LEVEL="
            f"{shlex.quote(reasoning_effort)} && "
        )
        auth_env_reset = ""
        if copy_host_auth:
            auth_env_reset = f"unset {' '.join(_CLAUDE_AUTH_ENV_VARS)} && "

        claude_cmd_parts = [shlex.quote(claude_cli)]
        if use_bare:
            claude_cmd_parts.append("--bare")
        claude_cmd_parts.extend(
            [
                '-p "$(cat ' + shlex.quote(prompt_container_path) + ')"',
                "--model",
                shlex.quote(model),
                "--effort",
                shlex.quote(reasoning_effort),
                "--output-format",
                shlex.quote(output_format),
                "--verbose",
                "--settings",
                shlex.quote(_CLAUDE_EVAL_SETTINGS_CONTAINER_PATH),
            ]
        )
        if dangerously_skip_permissions:
            claude_cmd_parts.append("--dangerously-skip-permissions")

        if strict_mcp_config:
            claude_cmd_parts.append("--strict-mcp-config")

        if mcp_config_arg:
            claude_cmd_parts.extend(["--mcp-config", shlex.quote(mcp_config_arg)])

        if use_bare and agents_md_content is not None:
            claude_cmd_parts.extend(
                [
                    "--append-system-prompt-file",
                    shlex.quote(f"{work_dir}/CLAUDE.md"),
                ]
            )

        if tools_arg is not None:
            claude_cmd_parts.extend(["--tools", shlex.quote(tools_arg)])

        if allowed_tools_arg is not None:
            claude_cmd_parts.extend(["--allowedTools", shlex.quote(allowed_tools_arg)])

        if disallowed_tools_arg is not None:
            claude_cmd_parts.extend(
                ["--disallowedTools", shlex.quote(disallowed_tools_arg)]
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
            f"{auth_env_reset}"
            f"{effort_env}"
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
    provider_settings = _CLAUDE_PROVIDER_SETTINGS[provider]

    model = config.get("model")
    if not isinstance(model, str) or not model.strip():
        error("Missing or invalid model. Must be a non-empty string.")
        return 1
    model = model.strip()
    config["model"] = model

    reasoning_effort = config.get(
        "reasoning_effort",
        provider_settings.default_reasoning_effort,
    )
    if not isinstance(reasoning_effort, str) or not reasoning_effort.strip():
        error("Missing or invalid reasoning_effort. Must be a non-empty string.")
        return 1
    reasoning_effort = reasoning_effort.strip()
    config["reasoning_effort"] = reasoning_effort

    if "claude_sandbox" in config and not isinstance(config["claude_sandbox"], bool):
        error("Invalid claude_sandbox. Must be true or false.")
        return 1
    config["claude_sandbox"] = config.get("claude_sandbox", False)

    if "claude_settings" in config:
        if not isinstance(config["claude_settings"], dict):
            error("Invalid claude_settings. Must be a TOML table.")
            return 1
        try:
            json.dumps(config["claude_settings"])
        except TypeError as exc:
            error(f"Invalid claude_settings. Must be JSON-serializable: {exc}")
            return 1

    if "strict_mcp_config" in config and not isinstance(
        config["strict_mcp_config"],
        bool,
    ):
        error("Invalid strict_mcp_config. Must be true or false.")
        return 1
    config["strict_mcp_config"] = config.get(
        "strict_mcp_config",
        False,
    )

    try:
        config["mcp_servers"] = _normalize_claude_mcp_servers(
            config.get("mcp_servers"),
        )
    except ValueError as exc:
        error(str(exc))
        return 1
    config["mcp_config_arg"] = (
        _CLAUDE_EVAL_MCP_CONFIG_CONTAINER_PATH
        if config["mcp_servers"]
        else None
    )
    if config["mcp_servers"] and not config["strict_mcp_config"]:
        error("mcp_servers requires strict_mcp_config=true for benchmark runs.")
        return 1

    if "dangerously_skip_permissions" in config and not isinstance(
        config["dangerously_skip_permissions"],
        bool,
    ):
        error("Invalid dangerously_skip_permissions. Must be true or false.")
        return 1
    config["dangerously_skip_permissions"] = config.get(
        "dangerously_skip_permissions",
        False,
    )

    try:
        allowed_tools_source = config.get("allowed_tools")
        allowed_tool_entries = _normalize_tool_entries(
            allowed_tools_source,
            "allowed_tools",
        )
        allowed_tools_arg = _tool_arg(allowed_tool_entries)
        config["allowed_tools_arg"] = allowed_tools_arg or None

        tools_source = config.get("tools")
        tools_arg = _normalize_tool_arg(tools_source, "tools")
        if tools_arg is None and allowed_tool_entries:
            # Eval configs maintain one tool list. Use it both as Claude's
            # built-in tool whitelist and as the auto-approval list.
            # MCP tools are controlled by --mcp-config/--strict-mcp-config.
            tools_arg = _tool_arg(_builtin_tool_entries(allowed_tool_entries))
        config["tools_arg"] = tools_arg

        disallowed_tools_source = config.get("disallowed_tools")
        disallowed_tools_arg = _normalize_tool_arg(
            disallowed_tools_source,
            "disallowed_tools",
        )
        config["disallowed_tools_arg"] = disallowed_tools_arg or None
    except ValueError as exc:
        error(str(exc))
        return 1

    if config["mcp_servers"]:
        for server_name in config["mcp_servers"]:
            prefix = f"mcp__{server_name}__"
            wildcard = f"{prefix}*"
            if not allowed_tool_entries or not any(
                entry == wildcard or entry.startswith(prefix)
                for entry in allowed_tool_entries
            ):
                error(
                    f"mcp_servers.{server_name} requires an allowed_tools entry "
                    f"like '{wildcard}'."
                )
                return 1

    try:
        _validate_claude_sandbox_config(config)
    except ValueError as exc:
        error(str(exc))
        return 1

    copy_host_auth = config.get("copy_host_auth")
    if copy_host_auth is not None:
        if provider == "glm":
            error(
                "provider='glm' requires ANTHROPIC_AUTH_TOKEN and does not support "
                "copy_host_auth."
            )
            return 1
        if not isinstance(copy_host_auth, str) or not copy_host_auth.strip():
            error("Invalid copy_host_auth. Must be a non-empty path string.")
            return 1
        copy_host_auth_path = resolve_path(SCRIPT_DIR, copy_host_auth.strip())
        if not copy_host_auth_path.is_file():
            error(f"copy_host_auth file not found: {copy_host_auth_path}")
            return 1
        config["copy_host_auth"] = str(copy_host_auth_path)

    copy_host_claude_json = config.get("copy_host_claude_json")
    if copy_host_claude_json is not None:
        if copy_host_auth is None:
            error("copy_host_claude_json requires copy_host_auth.")
            return 1
        if (
            not isinstance(copy_host_claude_json, str)
            or not copy_host_claude_json.strip()
        ):
            error("Invalid copy_host_claude_json. Must be a non-empty path string.")
            return 1
        copy_host_claude_json_path = resolve_path(
            SCRIPT_DIR,
            copy_host_claude_json.strip(),
        )
        if not copy_host_claude_json_path.is_file():
            error(
                "copy_host_claude_json file not found: "
                f"{copy_host_claude_json_path}"
            )
            return 1
        config["copy_host_claude_json"] = str(copy_host_claude_json_path)

    if "update_claude_cli" in config and not isinstance(
        config["update_claude_cli"],
        bool,
    ):
        error("Invalid update_claude_cli. Must be true or false.")
        return 1
    config["update_claude_cli"] = config.get("update_claude_cli", False)

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
    if config.get("claude_sandbox"):
        info("Claude Bash sandbox: enabled (network denied)")
    info(f"Claude tools: {config.get('tools_arg') or '(none)'}")
    if config.get("allowed_tools_arg"):
        info(f"Claude auto-allowed tools: {config['allowed_tools_arg']}")
    if config.get("disallowed_tools_arg"):
        info(f"Claude disallowed tools: {config['disallowed_tools_arg']}")
    if config.get("mcp_servers"):
        info(f"Claude MCP servers: {', '.join(sorted(config['mcp_servers']))}")
    if config.get("strict_mcp_config"):
        info("Strict MCP config: true")
    if config.get("dangerously_skip_permissions"):
        info("Dangerously skip permissions: true")
    if config.get("privileged", False):
        info("Docker privileged mode: true")
    if config.get("copy_host_auth"):
        info(
            "Copy host auth: "
            f"{config['copy_host_auth']} -> {_CLAUDE_AUTH_CONTAINER_PATH}"
        )
    if config.get("copy_host_claude_json"):
        info(
            "Copy host .claude.json: "
            f"{config['copy_host_claude_json']} -> {_CLAUDE_JSON_CONTAINER_PATH}"
        )
    if config["update_claude_cli"]:
        info("Update Claude CLI: true")
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
