"""Evaluation harness for OpenCode agent inside Docker containers.

Usage::

    uv run harness/eval_opencode.py harness/configs/opencode/v8/config.example.toml
    python3 harness/eval_opencode.py harness/configs/opencode/sm/config.example.toml --no-tui

The script:

1.  Loads a TOML config describing model, API provider, instances, timeout, etc.
2.  For each benchmark instance: starts a container, configures OpenCode,
    runs the agent, collects compact trajectory/session artifacts, audit files,
    tracking databases, result files, and tears down.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

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
from router.render import format_line as format_agent_line


@dataclass(frozen=True)
class OpenCodeProviderSettings:
    model_prefix: str
    forwarded_env_vars: tuple[str, ...]
    required_env_vars: tuple[str, ...] = ()
    requires_region: bool = False


_OPENCODE_PROVIDER_SETTINGS: dict[str, OpenCodeProviderSettings] = {
    "opencode": OpenCodeProviderSettings(
        model_prefix="opencode/",
        forwarded_env_vars=(),
    ),
    "openrouter": OpenCodeProviderSettings(
        model_prefix="openrouter/",
        forwarded_env_vars=("OPENROUTER_API_KEY",),
        required_env_vars=("OPENROUTER_API_KEY",),
    ),
    "moonshot": OpenCodeProviderSettings(
        model_prefix="moonshotai/",
        forwarded_env_vars=("MOONSHOT_API_KEY",),
        required_env_vars=("MOONSHOT_API_KEY",),
    ),
    "moonshot-cn": OpenCodeProviderSettings(
        model_prefix="moonshotai-cn/",
        forwarded_env_vars=("MOONSHOT_API_KEY",),
        required_env_vars=("MOONSHOT_API_KEY",),
    ),
    "openai": OpenCodeProviderSettings(
        model_prefix="openai/",
        forwarded_env_vars=("OPENAI_API_KEY",),
        required_env_vars=("OPENAI_API_KEY",),
    ),
    "nvidia": OpenCodeProviderSettings(
        model_prefix="nvidia/",
        forwarded_env_vars=("NVIDIA_API_KEY",),
        required_env_vars=("NVIDIA_API_KEY",),
    ),
    "bedrock": OpenCodeProviderSettings(
        model_prefix="amazon-bedrock/",
        forwarded_env_vars=(
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_SESSION_TOKEN",
            "AWS_REGION",
            "AWS_REGION_NAME",
            "AWS_DEFAULT_REGION",
        ),
        required_env_vars=("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"),
        requires_region=True,
    ),
}

_OPENCODE_EXTRA_ENV = {
    "IS_SANDBOX": "1",
}

_DEFAULT_AGENT_NAME = "opencode"
_DEFAULT_PERMISSION_CONFIG: dict[str, Any] = {
    "*": "deny",
    # Built-in tools from https://opencode.ai/docs/tools/#built-in.
    "bash": "allow",
    "edit": "allow",
    "read": {
        "*": "allow",
        "*.env": "deny",
        "*.env.*": "deny",
        "*.env.example": "allow",
    },
    "grep": "allow",
    "glob": "allow",
    "list": "allow",
    "lsp": "allow",
    "skill": "allow",
    "todowrite": "allow",
    "webfetch": "deny",
    "websearch": "deny",
    "question": "deny",
    # Permission safety guards documented separately from built-in tools.
    "doom_loop": "allow",
    "external_directory": "allow",
    "task": "allow",
    # OpenCode exposes MCP tools with the server name as the prefix, e.g.
    # secb_validate/secb_build/secb_repro for the Linux PoC harness.
    "secb_*": "allow",
}
_OPENCODE_ARTIFACT_MODES = {"compact", "debug"}
_OPENCODE_DB_CONTAINER_PATH = "/root/.local/share/opencode/opencode.db"
_OPENCODE_NETWORK_SANDBOX_SHELL = "/usr/local/bin/opencode-network-sandbox-shell"
_OPENCODE_NETWORK_SANDBOX_BACKEND = "/run/opencode-network-sandbox-backend"
_OPENCODE_NETWORK_SANDBOX_STATUS = "/tmp/opencode-shell-sandbox.status"

_OPENCODE_NETWORK_SANDBOX_SHELL_SCRIPT = r"""#!/usr/bin/env bash
set -euo pipefail

real_shell="${OPENCODE_SANDBOX_REAL_SHELL:-}"
if [ -z "$real_shell" ]; then
  if [ -x /bin/bash ]; then
    real_shell=/bin/bash
  else
    real_shell=/bin/sh
  fi
fi
if [ ! -x "$real_shell" ]; then
  echo "opencode shell sandbox: shell is not executable: $real_shell" >&2
  exit 126
fi

backend="$(cat /run/opencode-network-sandbox-backend 2>/dev/null || true)"
payload='
if command -v ip >/dev/null 2>&1; then
  ip link set lo up 2>/dev/null || true
fi
if ! command -v setpriv >/dev/null 2>&1; then
  echo "opencode shell sandbox: setpriv unavailable" >&2
  exit 126
fi
exec setpriv --no-new-privs --bounding-set=-all \
  --inh-caps=-all --ambient-caps=-all \
  --securebits=+noroot,+noroot_locked -- "$@"
'
case "$backend" in
  unshare)
    exec unshare --net --fork -- \
      /bin/sh -c "$payload" opencode-network-sandbox "$real_shell" "$@"
    ;;
  bwrap)
    exec bwrap --unshare-net --dev-bind / / --proc /proc -- \
      /bin/sh -c "$payload" opencode-network-sandbox "$real_shell" "$@"
    ;;
  *)
    echo "opencode shell sandbox: backend unavailable" >&2
    exit 126
    ;;
esac
"""

_OPENCODE_NETWORK_SANDBOX_BACKEND_SCRIPT = r"""
set -eu
mkdir -p /run
rm -f /run/opencode-network-sandbox-backend
if command -v unshare >/dev/null 2>&1 && \
    command -v setpriv >/dev/null 2>&1 && \
    unshare --net --fork -- \
      /bin/sh -c 'exit 0' >/dev/null 2>&1; then
  printf 'unshare\n' >/run/opencode-network-sandbox-backend
  exit 0
fi
if command -v bwrap >/dev/null 2>&1 && \
    command -v setpriv >/dev/null 2>&1 && \
    bwrap --unshare-net --dev-bind / / --proc /proc -- \
      /bin/sh -c 'exit 0' >/dev/null 2>&1; then
  printf 'bwrap\n' >/run/opencode-network-sandbox-backend
  exit 0
fi
exit 1
"""

_OPENCODE_REASONING_TAIL_SCRIPT = r"""
import json
import sqlite3
import sys
from pathlib import Path

db_path = Path(sys.argv[1])
session_id = sys.argv[2]
if not db_path.exists():
    raise SystemExit(0)

try:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=0.1)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, time_created, data FROM part "
        "WHERE session_id = ? ORDER BY time_created, id",
        (session_id,),
    ).fetchall()
except sqlite3.Error:
    raise SystemExit(0)
finally:
    try:
        conn.close()
    except NameError:
        pass

for row in rows:
    try:
        data = json.loads(row["data"])
    except (TypeError, json.JSONDecodeError):
        continue
    if data.get("type") != "reasoning":
        continue
    text = data.get("text")
    if not isinstance(text, str) or not text.strip():
        continue
    print(json.dumps({
        "id": row["id"],
        "time_created": row["time_created"],
        "text": text,
    }, ensure_ascii=False))
"""


def _warn_missing_provider_env(api: str) -> None:
    settings = _OPENCODE_PROVIDER_SETTINGS[api]
    for key in settings.required_env_vars:
        if not os.environ.get(key):
            warn(
                f"{key} is unset on the host; OpenCode may fail to "
                f"authenticate with api={api}."
            )
    if settings.requires_region and not (
        os.environ.get("AWS_REGION")
        or os.environ.get("AWS_REGION_NAME")
        or os.environ.get("AWS_DEFAULT_REGION")
    ):
        warn(
            "AWS_REGION, AWS_REGION_NAME, and AWS_DEFAULT_REGION are unset "
            "on the host; OpenCode Bedrock may fail to select a region."
        )


def _model_ref(api: str, model: str) -> str:
    prefix = _OPENCODE_PROVIDER_SETTINGS[api].model_prefix
    if model.startswith(prefix):
        return model
    return f"{prefix}{model}"


def _provider_id_from_model_ref(model_ref: str) -> str:
    return model_ref.split("/", 1)[0]


def _deep_merge_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if (
            isinstance(value, dict)
            and isinstance(merged.get(key), dict)
        ):
            merged[key] = _deep_merge_dict(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _validate_permission_rule(value: Any, path: str) -> None:
    if isinstance(value, str):
        if value not in {"allow", "ask", "deny"}:
            raise ValueError(
                f"Invalid {path}. Must be 'allow', 'ask', or 'deny'."
            )
        return
    if isinstance(value, dict):
        for key, nested in value.items():
            if not isinstance(key, str) or not key.strip():
                raise ValueError(f"Invalid {path}. Permission keys must be strings.")
            _validate_permission_rule(nested, f"{path}.{key}")
        return
    raise ValueError(f"Invalid {path}. Must be a string or TOML table.")


def _normalize_permission_config(value: Any) -> Any:
    permission = copy.deepcopy(value)
    _validate_permission_rule(permission, "permission")
    return permission


def _normalize_opencode_mcp_servers(value: object) -> dict[str, object]:
    if value in (None, False):
        return {}
    if not isinstance(value, dict):
        raise ValueError("Invalid mcp. Must be a TOML table.")

    normalized: dict[str, object] = {}
    for name, server in value.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Invalid mcp. Server names must be non-empty strings.")
        if not isinstance(server, dict):
            raise ValueError(f"Invalid mcp.{name}. Must be a TOML table.")

        server_type = server.get("type")
        if server_type != "local":
            raise ValueError(
                f"Invalid mcp.{name}.type. Only 'local' MCP servers are "
                "supported for benchmark runs."
            )

        command = server.get("command")
        if (
            not isinstance(command, list)
            or not command
            or any(not isinstance(item, str) or not item.strip() for item in command)
        ):
            raise ValueError(
                f"Invalid mcp.{name}.command. OpenCode local MCP command must "
                "be a non-empty list of strings."
            )

        normalized_server: dict[str, object] = {
            "type": "local",
            "command": list(command),
        }

        if "cwd" in server:
            cwd = server["cwd"]
            if not isinstance(cwd, str) or not cwd.strip():
                raise ValueError(f"Invalid mcp.{name}.cwd. Must be a string.")
            normalized_server["cwd"] = cwd

        if "environment" in server:
            environment = server["environment"]
            if (
                not isinstance(environment, dict)
                or any(
                    not isinstance(key, str) or not isinstance(val, str)
                    for key, val in environment.items()
                )
            ):
                raise ValueError(
                    f"Invalid mcp.{name}.environment. Must be a string map."
                )
            normalized_server["environment"] = dict(environment)

        if "enabled" in server:
            enabled = server["enabled"]
            if not isinstance(enabled, bool):
                raise ValueError(f"Invalid mcp.{name}.enabled. Must be a boolean.")
            normalized_server["enabled"] = enabled

        if "timeout" in server:
            timeout = server["timeout"]
            if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
                raise ValueError(f"Invalid mcp.{name}.timeout. Must be a number.")
            normalized_server["timeout"] = timeout

        normalized[name] = normalized_server
    return normalized


def _permission_allows_mcp_server(permission_config: Any, server_name: str) -> bool:
    if permission_config == "allow":
        return True
    if not isinstance(permission_config, dict):
        return False

    explicit_keys = (
        f"{server_name}_*",
        f"{server_name}*",
    )
    for key in explicit_keys:
        if permission_config.get(key) == "allow":
            return True
    return permission_config.get("*") == "allow"


def _setup_secb_mcp(container_id: str, config: dict) -> int:
    """Install the vendored `secb-linux-vm-mcp` package in the container."""
    mcp_servers = config.get("mcp") or {}
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


def _ensure_opencode_shell_network_sandbox(container_id: str) -> int:
    """Install and verify the shell wrapper used for OpenCode bash tool calls."""
    step_run("Ensure OpenCode shell network sandbox")
    setup_rc, _stdout, setup_stderr = docker_exec(
        container_id,
        _OPENCODE_NETWORK_SANDBOX_BACKEND_SCRIPT,
        30,
    )

    if setup_rc != 0:
        install_cmd = r"""
set -eu
log=/tmp/opencode-shell-sandbox-install.log
: > "$log"
if command -v apt-get >/dev/null 2>&1; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get -o DPkg::Lock::Timeout=60 update -qq >>"$log" 2>&1
  apt-get -o DPkg::Lock::Timeout=60 install -y -qq --no-install-recommends \
    util-linux bubblewrap >>"$log" 2>&1
  rm -rf /var/lib/apt/lists/*
elif command -v apk >/dev/null 2>&1; then
  apk add --no-cache util-linux bubblewrap >>"$log" 2>&1
elif command -v dnf >/dev/null 2>&1; then
  dnf install -y util-linux bubblewrap >>"$log" 2>&1
elif command -v yum >/dev/null 2>&1; then
  yum install -y util-linux bubblewrap >>"$log" 2>&1
else
  echo "no supported package manager found" >>"$log"
  exit 127
fi
command -v setpriv >/dev/null 2>&1
command -v unshare >/dev/null 2>&1 || command -v bwrap >/dev/null 2>&1
"""
        install_rc, _stdout, install_stderr = docker_exec(
            container_id,
            install_cmd,
            300,
        )
        if install_rc != 0:
            _tail_rc, tail_stdout, _tail_stderr = docker_exec(
                container_id,
                "tail -n 20 /tmp/opencode-shell-sandbox-install.log 2>/dev/null || true",
                30,
            )
            detail_source = tail_stdout or install_stderr
            detail = detail_source[:240].replace("\n", " ") if detail_source else ""
            step_err(
                "Ensure OpenCode shell network sandbox  "
                f"{DIM}(dependency failed: {detail or f'exit {install_rc}'}){NC}"
            )
            return install_rc

        setup_rc, _stdout, setup_stderr = docker_exec(
            container_id,
            _OPENCODE_NETWORK_SANDBOX_BACKEND_SCRIPT,
            30,
        )

    if setup_rc != 0:
        detail = setup_stderr[:240].replace("\n", " ") if setup_stderr else ""
        step_err(
            "Ensure OpenCode shell network sandbox  "
            f"{DIM}(backend unavailable: {detail or f'exit {setup_rc}'}){NC}"
        )
        return setup_rc

    mkdir_rc, _stdout, mkdir_stderr = docker_exec(
        container_id,
        "mkdir -p /usr/local/bin",
        10,
    )
    if mkdir_rc != 0:
        detail = mkdir_stderr[:120].replace("\n", " ") if mkdir_stderr else ""
        step_err(
            "Ensure OpenCode shell network sandbox  "
            f"{DIM}(setup failed: {detail or f'exit {mkdir_rc}'}){NC}"
        )
        return mkdir_rc

    if not docker_pipe_stdin(
        container_id,
        _OPENCODE_NETWORK_SANDBOX_SHELL_SCRIPT,
        _OPENCODE_NETWORK_SANDBOX_SHELL,
    ):
        step_err(f"Ensure OpenCode shell network sandbox  {DIM}(copy failed){NC}")
        return 1

    chmod_rc, _stdout, chmod_stderr = docker_exec(
        container_id,
        f"chmod 755 {shlex.quote(_OPENCODE_NETWORK_SANDBOX_SHELL)}",
        10,
    )
    if chmod_rc != 0:
        detail = chmod_stderr[:120].replace("\n", " ") if chmod_stderr else ""
        step_err(
            "Ensure OpenCode shell network sandbox  "
            f"{DIM}(chmod failed: {detail or f'exit {chmod_rc}'}){NC}"
        )
        return chmod_rc

    smoke_cmd = (
        f"{shlex.quote(_OPENCODE_NETWORK_SANDBOX_SHELL)} -c "
        + shlex.quote(
            "echo ok >/tmp/opencode-shell-sandbox.ok && "
            "if awk 'NR > 1 && $2 == \"00000000\" { found = 1 } "
            "END { exit found ? 0 : 1 }' /proc/net/route; then "
            "  echo default route still visible >&2; exit 1; "
            "fi && "
            "grep -Eq '^CapEff:[[:space:]]+0+$' /proc/self/status && "
            "test \"$(readlink /proc/1/ns/net)\" != "
            "\"$(readlink /proc/self/ns/net)\""
        )
    )
    smoke_rc, _stdout, smoke_stderr = docker_exec(container_id, smoke_cmd, 30)
    if smoke_rc != 0:
        detail = smoke_stderr[:240].replace("\n", " ") if smoke_stderr else ""
        step_err(
            "Ensure OpenCode shell network sandbox  "
            f"{DIM}(smoke failed: {detail or f'exit {smoke_rc}'}){NC}"
        )
        return smoke_rc

    rc, backend, _stderr = docker_exec(
        container_id,
        f"cat {shlex.quote(_OPENCODE_NETWORK_SANDBOX_BACKEND)}",
        10,
    )
    backend = backend.strip() if rc == 0 else ""
    status_cmd = (
        "printf '%s\n' "
        + shlex.quote(f"enabled=true\nbackend={backend}\nshell={_OPENCODE_NETWORK_SANDBOX_SHELL}")
        + f" > {shlex.quote(_OPENCODE_NETWORK_SANDBOX_STATUS)}"
    )
    docker_exec(container_id, status_cmd, 10)

    suffix = f" ({backend})" if backend else ""
    step_ok(f"Ensure OpenCode shell network sandbox  {DIM}{suffix}{NC}")
    return 0


def _build_opencode_config(
    *,
    agent_name: str,
    model_ref: str,
    variant: str | None,
    agent_options: dict[str, Any] | None,
    agents_md_content: str | None,
    skill_container_dir: str | None,
    permission_config: Any,
    steps: int | None,
    mcp_config: dict[str, object] | None,
    shell_path: str | None,
    config_overrides: dict[str, Any] | None,
) -> dict[str, Any]:
    agent_config: dict[str, Any] = {
        "description": "SEC-bench Pro evaluation agent",
        "mode": "primary",
        "model": model_ref,
    }
    if permission_config is not None:
        config_permission = copy.deepcopy(permission_config)
    else:
        config_permission = None
    if variant:
        agent_config["variant"] = variant
    if agent_options:
        agent_config.update(copy.deepcopy(agent_options))
    if agents_md_content:
        agent_config["prompt"] = agents_md_content
    if steps is not None:
        agent_config["steps"] = steps

    config: dict[str, Any] = {
        "$schema": "https://opencode.ai/config.json",
        # Disable OpenCode's per-edit git snapshots. In benchmark containers the
        # worktrees are large and snapshotting on every edit overloads disk/CPU
        # without adding value, since the harness collects worktree diffs itself.
        "snapshot": False,
        "autoupdate": False,
        "default_agent": agent_name,
        "agent": {
            agent_name: agent_config,
        },
    }
    if skill_container_dir:
        config["skills"] = {
            "paths": [skill_container_dir],
        }

    if config_overrides:
        config = _deep_merge_dict(config, config_overrides)
    if mcp_config:
        config["mcp"] = copy.deepcopy(mcp_config)
    if config_permission is not None:
        config["permission"] = config_permission
    if shell_path:
        config["shell"] = shell_path
    return config


def _container_path_exists(
    container_id: str,
    path: str,
    test_flag: str,
    timeout_secs: int = 30,
) -> bool:
    _rc, stdout, _stderr = docker_exec(
        container_id,
        f"[ {test_flag} {shlex.quote(path)} ] && echo yes || echo no",
        timeout_secs,
    )
    return stdout.strip().rstrip("\r") == "yes"


def _copy_container_dir(
    *,
    container_id: str,
    label: str,
    src: str,
    dest: Path,
) -> None:
    step_run(label)
    if not _container_path_exists(container_id, src, "-d"):
        step_warn(f"{label}  {DIM}not found{NC}")
        return
    dest.mkdir(parents=True, exist_ok=True)
    if docker_copy_from(container_id, f"{src}/.", str(dest) + "/"):
        file_count = sum(1 for p in dest.rglob("*") if p.is_file())
        step_ok(f"{label}  {DIM}({file_count} files){NC}")
    else:
        step_warn(f"{label}  {DIM}copy failed{NC}")


def _collect_opencode_database(container_id: str, instance_outdir: Path) -> None:
    step_run("Collect OpenCode database")
    db_dir = instance_outdir / "opencode_db"
    db_dir.mkdir(parents=True, exist_ok=True)

    db_src = "/root/.local/share/opencode/opencode.db"
    copied = False
    for suffix in ("", "-wal", "-shm"):
        src = f"{db_src}{suffix}"
        dest = db_dir / f"opencode.db{suffix}"
        if docker_copy_from(container_id, src, str(dest)) and suffix == "":
            copied = True

    if copied and (db_dir / "opencode.db").is_file():
        db_size = (db_dir / "opencode.db").stat().st_size
        step_ok(f"Collect OpenCode database  {DIM}({db_size // 1024} KB){NC}")
    else:
        step_warn(f"Collect OpenCode database  {DIM}not found{NC}")


def _path_file_count(path: Path) -> int:
    return sum(1 for p in path.rglob("*") if p.is_file())


def _path_size_bytes(path: Path) -> int:
    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            total += item.stat().st_size
    return total


def _format_bytes(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"


class _OpenCodeReasoningTailer:
    """Recover reasoning events from OpenCode's DB when stdout omits them."""

    def __init__(
        self,
        *,
        container_id: str,
        db_path: str = _OPENCODE_DB_CONTAINER_PATH,
    ) -> None:
        self.container_id = container_id
        self.db_path = db_path
        self.session_ids: set[str] = set()
        self.seen_part_ids: set[str] = set()
        self.disabled = False
        self.last_poll = 0.0

    def __call__(self, line: str) -> list[str]:
        event = self._parse_event(line)
        if event is None:
            return []

        session_id = self._session_id(event)
        if session_id:
            self.session_ids.add(session_id)

        if self._is_reasoning_event(event):
            part_id = self._part_id(event)
            if part_id:
                self.seen_part_ids.add(part_id)
            return []

        event_type = str(event.get("type") or "")
        if event_type not in {
            "step-start",
            "step_start",
            "tool_use",
            "tool",
            "step-finish",
            "step_finish",
            "text",
            "done",
        }:
            return []

        if event_type in {"step-start", "step_start"}:
            # Step-start can arrive before OpenCode commits the reasoning part.
            # Poll there opportunistically, but avoid tight loops if the CLI
            # emits several progress events together.
            now = time.monotonic()
            if now - self.last_poll < 0.15:
                return []
            self.last_poll = now
        return self.flush()

    def flush(self) -> list[str]:
        if self.disabled or not self.session_ids:
            return []
        rendered: list[str] = []
        for session_id in sorted(self.session_ids):
            rendered.extend(self._poll_session(session_id))
        return rendered

    @staticmethod
    def _parse_event(line: str) -> dict[str, Any] | None:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            return None
        return event if isinstance(event, dict) else None

    @staticmethod
    def _event_part(event: dict[str, Any]) -> dict[str, Any]:
        part = event.get("part")
        return part if isinstance(part, dict) else {}

    def _session_id(self, event: dict[str, Any]) -> str | None:
        part = self._event_part(event)
        value = (
            event.get("sessionID")
            or event.get("session_id")
            or part.get("sessionID")
            or part.get("session_id")
        )
        return str(value) if value else None

    def _part_id(self, event: dict[str, Any]) -> str | None:
        part = self._event_part(event)
        value = part.get("id") or event.get("partID") or event.get("part_id")
        return str(value) if value else None

    def _is_reasoning_event(self, event: dict[str, Any]) -> bool:
        part = self._event_part(event)
        return event.get("type") == "reasoning" or part.get("type") == "reasoning"

    def _poll_session(self, session_id: str) -> list[str]:
        cmd = (
            f"if [ ! -f {shlex.quote(self.db_path)} ]; then exit 0; fi; "
            "if command -v python3 >/dev/null 2>&1; then py=python3; "
            "elif command -v python >/dev/null 2>&1; then py=python; "
            "else exit 127; fi; "
            f'"$py" -c {shlex.quote(_OPENCODE_REASONING_TAIL_SCRIPT)} '
            f"{shlex.quote(self.db_path)} {shlex.quote(session_id)}"
        )
        try:
            result = subprocess.run(
                ["docker", "exec", self.container_id, "bash", "-c", cmd],
                capture_output=True,
                text=True,
                timeout=3,
            )
        except subprocess.TimeoutExpired:
            return []
        if result.returncode == 127:
            self.disabled = True
            return []
        if result.returncode != 0:
            return []

        rendered: list[str] = []
        for raw in (result.stdout or "").splitlines():
            try:
                row = json.loads(raw)
            except json.JSONDecodeError:
                continue
            part_id = str(row.get("id") or "")
            text = row.get("text")
            if not part_id or part_id in self.seen_part_ids:
                continue
            if not isinstance(text, str) or not text.strip():
                continue
            self.seen_part_ids.add(part_id)
            synthetic = {
                "type": "reasoning",
                "sessionID": session_id,
                "part": {
                    "id": part_id,
                    "sessionID": session_id,
                    "type": "reasoning",
                    "text": text,
                },
            }
            formatted = format_agent_line(
                "opencode",
                json.dumps(synthetic, ensure_ascii=False),
            )
            if formatted:
                rendered.append(formatted)
        return rendered


_OPENCODE_TRAJECTORY_EXPORTER = r"""
import json
import sqlite3
import sys
from pathlib import Path


def _decode_jsonish(value):
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped or stripped[0] not in "[{":
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value


def _row_dict(row):
    return {key: _decode_jsonish(row[key]) for key in row.keys()}


def _table_exists(conn, name):
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone()
    return row is not None


def _fetch_all(conn, query, args=()):
    return [_row_dict(row) for row in conn.execute(query, args).fetchall()]


def main():
    db_path = Path(sys.argv[1])
    work_dir = sys.argv[2]
    out_dir = Path(sys.argv[3])
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "db_path": str(db_path),
        "work_dir": work_dir,
        "session_ids": [],
        "sessions": 0,
        "messages": 0,
        "parts": 0,
        "reasoning_parts": 0,
        "reasoning_chars": 0,
        "todos": 0,
    }

    if not db_path.exists():
        print(json.dumps({**manifest, "error": "database_not_found"}))
        return 2

    uri = f"file:{db_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        required = ("session", "message", "part")
        missing = [name for name in required if not _table_exists(conn, name)]
        if missing:
            print(json.dumps({**manifest, "error": "missing_tables", "tables": missing}))
            return 2

        work_dirs = [work_dir, work_dir.rstrip("/")]
        try:
            work_dirs.append(str(Path(work_dir).resolve()))
        except OSError:
            pass
        work_dirs = list(dict.fromkeys(value for value in work_dirs if value))
        placeholders = ",".join("?" for _ in work_dirs)
        sessions = _fetch_all(
            conn,
            f"SELECT * FROM session WHERE directory IN ({placeholders}) ORDER BY time_created",
            tuple(work_dirs),
        )
        if not sessions:
            print(json.dumps({**manifest, "error": "session_not_found"}))
            return 3

        trajectory_dir = out_dir / "trajectory"
        reasoning_dir = out_dir / "reasoning"
        trajectory_dir.mkdir(parents=True, exist_ok=True)
        reasoning_dir.mkdir(parents=True, exist_ok=True)
        manifest["sessions"] = len(sessions)

        for session in sessions:
            sid = session["id"]
            manifest["session_ids"].append(sid)
            messages = _fetch_all(
                conn,
                "SELECT * FROM message WHERE session_id = ? ORDER BY time_created",
                (sid,),
            )
            parts = _fetch_all(
                conn,
                "SELECT * FROM part WHERE session_id = ? ORDER BY time_created",
                (sid,),
            )
            todos = []
            if _table_exists(conn, "todo"):
                todos = _fetch_all(
                    conn,
                    "SELECT * FROM todo WHERE session_id = ? ORDER BY position",
                    (sid,),
                )

            project = None
            if session.get("project_id") and _table_exists(conn, "project"):
                row = conn.execute(
                    "SELECT * FROM project WHERE id = ?",
                    (session["project_id"],),
                ).fetchone()
                if row is not None:
                    project = _row_dict(row)

            payload = {
                "session": session,
                "project": project,
                "messages": messages,
                "parts": parts,
                "todos": todos,
            }
            with open(trajectory_dir / f"{sid}.json", "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2, ensure_ascii=False)
                fh.write("\n")

            reasoning_chunks = []
            for part in parts:
                data = part.get("data")
                if not isinstance(data, dict) or data.get("type") != "reasoning":
                    continue
                text = data.get("text")
                if not isinstance(text, str) or not text.strip():
                    continue
                manifest["reasoning_parts"] += 1
                manifest["reasoning_chars"] += len(text)
                reasoning_chunks.append(
                    {
                        "part_id": part.get("id"),
                        "message_id": part.get("message_id"),
                        "time_created": part.get("time_created"),
                        "text": text,
                    }
                )

            if reasoning_chunks:
                with open(reasoning_dir / f"{sid}.md", "w", encoding="utf-8") as fh:
                    fh.write(f"# OpenCode Reasoning: {sid}\n\n")
                    for index, item in enumerate(reasoning_chunks, 1):
                        fh.write(f"## Reasoning {index}\n\n")
                        if item.get("message_id"):
                            fh.write(f"- message_id: `{item['message_id']}`\n")
                        if item.get("part_id"):
                            fh.write(f"- part_id: `{item['part_id']}`\n")
                        if item.get("time_created"):
                            fh.write(f"- time_created: `{item['time_created']}`\n")
                        fh.write("\n")
                        fh.write(item["text"].rstrip())
                        fh.write("\n\n")

            manifest["messages"] += len(messages)
            manifest["parts"] += len(parts)
            manifest["todos"] += len(todos)

        with open(out_dir / "manifest.json", "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2)
            fh.write("\n")
        print(json.dumps(manifest))
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
"""


_OPENCODE_SESSION_BUNDLE_EXPORTER = r"""
import json
import shutil
import sqlite3
import sys
from pathlib import Path


def _dir_size(path):
    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            total += item.stat().st_size
    return total


def _copy_file(src, dest):
    if not src.is_file():
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return True


def _copy_tree(src, dest):
    if not src.is_dir():
        return False
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dest)
    return True


def _backup_sqlite(src, dest):
    if not src.is_file():
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    source = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
    target = sqlite3.connect(str(dest))
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()
    return True


def main():
    db_path = Path(sys.argv[1])
    work_dir = Path(sys.argv[2])
    out_dir = Path(sys.argv[3])
    try:
        session_ids = json.loads(sys.argv[4]) if len(sys.argv) > 4 else []
    except json.JSONDecodeError:
        session_ids = []

    if out_dir.exists():
        shutil.rmtree(out_dir)

    local_share = out_dir / "local_share" / "opencode"
    project = out_dir / "project"
    local_share.mkdir(parents=True, exist_ok=True)
    project.mkdir(parents=True, exist_ok=True)

    contains = {
        "database": False,
        "storage": False,
        "tool_output": False,
        "project_config": False,
        "project_skills": False,
        "agents_md": False,
    }
    errors = []

    try:
        contains["database"] = _backup_sqlite(db_path, local_share / "opencode.db")
    except Exception as exc:
        errors.append(f"database: {type(exc).__name__}: {exc}")

    data_home = db_path.parent
    contains["storage"] = _copy_tree(
        data_home / "storage",
        local_share / "storage",
    )
    contains["tool_output"] = _copy_tree(
        data_home / "tool-output",
        local_share / "tool-output",
    )

    contains["project_config"] = _copy_file(
        work_dir / "opencode.json",
        project / "opencode.json",
    )
    if not contains["project_config"]:
        contains["project_config"] = _copy_file(
            work_dir / ".opencode" / "opencode.json",
            project / "opencode.json",
        )
    contains["project_skills"] = _copy_tree(
        work_dir / ".opencode" / "skills",
        project / ".opencode" / "skills",
    )
    contains["agents_md"] = _copy_file(
        work_dir / "AGENTS.md",
        project / "AGENTS.md",
    )

    (out_dir / "work_dir.txt").write_text(str(work_dir) + "\n", encoding="utf-8")
    (out_dir / "session_ids.txt").write_text(
        "\n".join(session_ids) + ("\n" if session_ids else ""),
        encoding="utf-8",
    )

    restore = '''#!/bin/sh
set -eu

bundle_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
work_dir="${1:-/src/v8}"

mkdir -p /root/.local/share/opencode "$work_dir/.opencode"
cp -a "$bundle_dir/local_share/opencode/." /root/.local/share/opencode/
if [ -f "$bundle_dir/project/opencode.json" ]; then
  cp "$bundle_dir/project/opencode.json" "$work_dir/opencode.json"
fi
if [ -d "$bundle_dir/project/.opencode" ]; then
  cp -a "$bundle_dir/project/.opencode/." "$work_dir/.opencode/"
fi
if [ -f "$bundle_dir/project/AGENTS.md" ]; then
  cp "$bundle_dir/project/AGENTS.md" "$work_dir/AGENTS.md"
fi
'''
    restore_path = out_dir / "restore.sh"
    restore_path.write_text(restore, encoding="utf-8")
    restore_path.chmod(0o755)

    readme = '''OpenCode continuation bundle

Copy this directory into a stopped or fresh benchmark container, then run:

  sh /path/to/opencode_session/restore.sh /src/v8

The bundle restores /root/.local/share/opencode, project opencode.json, and
optional .opencode skills needed for OpenCode to see the saved session. It intentionally
does not include OpenCode logs, snapshots, or project node_modules.
'''
    (out_dir / "README.txt").write_text(readme, encoding="utf-8")

    manifest = {
        "work_dir": str(work_dir),
        "session_ids": session_ids,
        "contains": contains,
        "bytes": _dir_size(out_dir),
        "errors": errors,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest))
    return 0 if contains["database"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
"""


def _collect_opencode_session_bundle(
    container_id: str,
    work_dir: str,
    instance_outdir: Path,
    instance_id: str,
    session_ids: list[str] | None,
) -> None:
    step_run("Collect OpenCode session bundle")
    exporter_path = f"/tmp/opencode-session-bundle-{instance_id}.py"
    bundle_dir = f"/tmp/opencode-session-bundle-{instance_id}"
    if not docker_pipe_stdin(
        container_id,
        _OPENCODE_SESSION_BUNDLE_EXPORTER,
        exporter_path,
    ):
        step_warn(f"Collect OpenCode session bundle  {DIM}exporter copy failed{NC}")
        return

    rc, stdout, stderr = docker_exec(
        container_id,
        (
            f"python3 {shlex.quote(exporter_path)} "
            "/root/.local/share/opencode/opencode.db "
            f"{shlex.quote(work_dir)} "
            f"{shlex.quote(bundle_dir)} "
            f"{shlex.quote(json.dumps(session_ids or []))}"
        ),
        120,
    )

    manifest: dict[str, Any] = {}
    if stdout.strip():
        try:
            manifest = json.loads(stdout.strip().splitlines()[-1])
        except json.JSONDecodeError:
            manifest = {}

    if rc != 0:
        reason = (
            "; ".join(manifest.get("errors", []))
            or (stderr.strip()[:120] if stderr else f"exit {rc}")
        )
        step_warn(f"Collect OpenCode session bundle  {DIM}{reason}{NC}")
        return

    dest = instance_outdir / "opencode_session"
    dest.mkdir(parents=True, exist_ok=True)
    if docker_copy_from(container_id, f"{bundle_dir}/.", str(dest) + "/"):
        size = _format_bytes(_path_size_bytes(dest))
        file_count = _path_file_count(dest)
        step_ok(
            f"Collect OpenCode session bundle  "
            f"{DIM}({file_count} files, {size}){NC}"
        )
    else:
        step_warn(f"Collect OpenCode session bundle  {DIM}copy failed{NC}")


def collect_opencode_artifacts(
    container_id: str,
    work_dir: str,
    instance_outdir: Path,
    instance_id: str,
    artifact_mode: str,
) -> None:
    """Collect OpenCode trajectory and compact continuation data."""
    step_run("Collect OpenCode trajectory")
    exporter_path = f"/tmp/opencode-export-{instance_id}.py"
    export_dir = f"/tmp/opencode-export-{instance_id}"
    manifest: dict[str, Any] = {}
    if not docker_pipe_stdin(container_id, _OPENCODE_TRAJECTORY_EXPORTER, exporter_path):
        step_warn(f"Collect OpenCode trajectory  {DIM}exporter copy failed{NC}")
    else:
        rc, stdout, stderr = docker_exec(
            container_id,
            (
                f"rm -rf {shlex.quote(export_dir)} && "
                f"python3 {shlex.quote(exporter_path)} "
                "/root/.local/share/opencode/opencode.db "
                f"{shlex.quote(work_dir)} "
                f"{shlex.quote(export_dir)}"
            ),
            120,
        )
        if stdout.strip():
            try:
                manifest = json.loads(stdout.strip().splitlines()[-1])
            except json.JSONDecodeError:
                manifest = {}

        if rc == 0:
            trajectory_dest = instance_outdir / "trajectory"
            trajectory_dest.mkdir(parents=True, exist_ok=True)
            if docker_copy_from(
                container_id,
                f"{export_dir}/trajectory/.",
                str(trajectory_dest) + "/",
            ):
                count = sum(1 for _ in trajectory_dest.glob("*.json"))
                step_ok(
                    f"Collect OpenCode trajectory  "
                    f"{DIM}({count} sessions, {manifest.get('messages', '?')} "
                    f"messages, {manifest.get('reasoning_parts', 0)} reasoning){NC}"
                )
            else:
                step_warn(f"Collect OpenCode trajectory  {DIM}copy failed{NC}")

            reasoning_dest = instance_outdir / "reasoning"
            reasoning_dest.mkdir(parents=True, exist_ok=True)
            if docker_copy_from(
                container_id,
                f"{export_dir}/reasoning/.",
                str(reasoning_dest) + "/",
            ):
                reasoning_count = sum(1 for _ in reasoning_dest.glob("*.md"))
                if reasoning_count:
                    step_ok(
                        f"Collect OpenCode reasoning  "
                        f"{DIM}({reasoning_count} files, "
                        f"{manifest.get('reasoning_chars', 0)} chars){NC}"
                    )
                else:
                    step_warn(f"Collect OpenCode reasoning  {DIM}none found{NC}")
            else:
                step_warn(f"Collect OpenCode reasoning  {DIM}copy failed{NC}")

            manifest_dest = instance_outdir / "opencode_manifest.json"
            docker_copy_from(
                container_id,
                f"{export_dir}/manifest.json",
                str(manifest_dest),
            )
        else:
            reason = manifest.get("error") or (stderr.strip()[:120] if stderr else f"exit {rc}")
            step_warn(f"Collect OpenCode trajectory  {DIM}{reason}{NC}")

    _collect_opencode_session_bundle(
        container_id=container_id,
        work_dir=work_dir,
        instance_outdir=instance_outdir,
        instance_id=instance_id,
        session_ids=manifest.get("session_ids") if manifest else None,
    )

    if artifact_mode != "debug":
        return

    _collect_opencode_database(container_id, instance_outdir)
    _copy_container_dir(
        container_id=container_id,
        label="Collect OpenCode storage",
        src="/root/.local/share/opencode/storage",
        dest=instance_outdir / "opencode_storage",
    )
    _copy_container_dir(
        container_id=container_id,
        label="Collect OpenCode logs",
        src="/root/.local/share/opencode/log",
        dest=instance_outdir / "opencode_logs",
    )
    _copy_container_dir(
        container_id=container_id,
        label="Collect OpenCode tool output",
        src="/root/.local/share/opencode/tool-output",
        dest=instance_outdir / "opencode_tool_output",
    )
    _copy_container_dir(
        container_id=container_id,
        label="Collect OpenCode snapshots",
        src="/root/.local/share/opencode/snapshot",
        dest=instance_outdir / "opencode_snapshot",
    )
    _copy_container_dir(
        container_id=container_id,
        label="Collect OpenCode project config",
        src=f"{work_dir.rstrip('/')}/.opencode",
        dest=instance_outdir / "opencode_project_config",
    )


def collect_worktree_artifacts(
    container_id: str,
    work_dir: str,
    instance_outdir: Path,
) -> None:
    """Collect git status and diffs to help reproduce agent-side edits."""
    step_run("Collect worktree state")
    out_base = "/tmp/opencode-worktree"
    rc, _stdout, stderr = docker_exec(
        container_id,
        (
            f"rm -rf {out_base} && mkdir -p {out_base} && "
            f"cd {shlex.quote(work_dir)} && "
            f"git status --short > {out_base}/status.txt 2>&1 && "
            f"git diff --binary > {out_base}/worktree.diff 2>&1 && "
            f"git diff --cached --binary > {out_base}/index.diff 2>&1"
        ),
        60,
    )
    if rc != 0:
        detail = stderr[:120].replace("\n", " ") if stderr else f"exit {rc}"
        step_warn(f"Collect worktree state  {DIM}{detail}{NC}")
        return

    dest = instance_outdir / "worktree"
    dest.mkdir(parents=True, exist_ok=True)
    if docker_copy_from(container_id, f"{out_base}/.", str(dest) + "/"):
        step_ok("Collect worktree state")
    else:
        step_warn(f"Collect worktree state  {DIM}copy failed{NC}")


def collect_shell_network_sandbox_artifact(
    container_id: str,
    instance_outdir: Path,
) -> None:
    if not _container_path_exists(
        container_id,
        _OPENCODE_NETWORK_SANDBOX_STATUS,
        "-f",
    ):
        return
    dest = instance_outdir / "opencode_shell_sandbox.txt"
    if not docker_copy_from(
        container_id,
        _OPENCODE_NETWORK_SANDBOX_STATUS,
        str(dest),
    ):
        step_warn(f"Collect OpenCode shell sandbox status  {DIM}copy failed{NC}")


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

    api: str = config["api"]
    provider_settings = _OPENCODE_PROVIDER_SETTINGS[api]
    model_ref = _model_ref(api, model)

    opencode_cli: str = config.get("opencode_cli", "opencode")
    output_format: str = config.get("output_format", "json")
    variant: str | None = config.get("variant")
    agent_options: dict[str, Any] | None = config.get("agent_options")
    agent_name: str = config.get("agent_name", _DEFAULT_AGENT_NAME)
    permission_config = config.get("permission", _DEFAULT_PERMISSION_CONFIG)
    steps: int | None = config.get("steps")
    config_overrides: dict[str, Any] | None = config.get("opencode_config")
    mcp_config: dict[str, object] | None = config.get("mcp") or None
    artifact_mode: str = config.get("opencode_artifacts", "compact")
    privileged: bool = config.get("privileged", common.is_linux_project(project))
    refresh_models: bool = config.get("refresh_models", True)
    update_opencode_cli: bool = config.get("update_opencode_cli", False)
    opencode_update_method: str = config.get("opencode_update_method", "npm")
    pure: bool = config.get("pure", True)
    shell_network_sandbox: bool = config.get("shell_network_sandbox", False)

    container_name = f"opencode-eval-{instance_id}-{int(datetime.now().timestamp())}"

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
        extra_env=_OPENCODE_EXTRA_ENV,
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
    elif shell_network_sandbox:
        docker_run_cmd.extend(
            [
                "--cap-add=SYS_ADMIN",
                "--cap-add=NET_ADMIN",
                "--security-opt",
                "seccomp=unconfined",
                "--security-opt",
                "apparmor=unconfined",
            ]
        )
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
        opencode_path_export = (
            'export PATH="$HOME/.opencode/bin:$HOME/.local/bin:'
            '$HOME/.cargo/bin:/usr/local/bin:$PATH" && '
            'export NVM_DIR="$HOME/.nvm" && '
            'if [ -s "$NVM_DIR/nvm.sh" ]; then '
            '. "$NVM_DIR/nvm.sh" 2>/dev/null || true; fi && '
        )
        rc = run_step(
            "Check OpenCode CLI",
            container_id,
            30,
            f"{opencode_path_export}command -v {shlex.quote(opencode_cli)}",
        )
        if rc != 0:
            return 127

        if update_opencode_cli:
            rc = run_step(
                "Update OpenCode CLI",
                container_id,
                600,
                (
                    f"{opencode_path_export}"
                    f"{shlex.quote(opencode_cli)} upgrade "
                    f"--method {shlex.quote(opencode_update_method)} && "
                    f"{shlex.quote(opencode_cli)} --version"
                ),
            )
            if rc != 0:
                return rc

        if tracking == "beads":
            run_step(
                "Beads initialization (sqlite backend)",
                container_id,
                300,
                (
                    'export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH" && '
                    f"cd {shlex.quote(work_dir)} && bd init --backend sqlite"
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
            "Remove AGENTS.md",
            container_id,
            30,
            f"rm -f {shlex.quote(work_dir.rstrip('/') + '/AGENTS.md')}",
        )

        if agents_md_content is not None:
            step_run("Copy eval AGENTS.md")
            if docker_pipe_stdin(
                container_id,
                agents_md_content,
                f"{work_dir.rstrip('/')}/AGENTS.md",
            ):
                step_ok("Copy eval AGENTS.md")
            else:
                step_warn(f"Copy eval AGENTS.md  {DIM}copy failed{NC}")

        if common.is_linux_project(project):
            setup_linux_evaluation_container(
                container_id,
                secb_config_content=linux_secb_config_content,
                instance_dir=linux_instance_dir,
            )
            secb_mcp_rc = _setup_secb_mcp(container_id, config)
            if secb_mcp_rc != 0:
                return secb_mcp_rc

        if shell_network_sandbox:
            sandbox_rc = _ensure_opencode_shell_network_sandbox(container_id)
            if sandbox_rc != 0:
                return sandbox_rc

        skill_container_dir: str | None = None
        if skill_directory and skill_directory.is_dir():
            skill_container_dir = f"{work_dir.rstrip('/')}/.opencode/skills"
            step_run("Copy skill files")
            docker_exec(
                container_id,
                f"mkdir -p {shlex.quote(skill_container_dir)}",
                30,
            )
            src = str(skill_directory) + "/."
            if docker_copy_to(container_id, src, f"{skill_container_dir}/"):
                skill_count = sum(1 for _ in skill_directory.rglob("SKILL.md"))
                step_ok(
                    f"Copy skill files  "
                    f"{DIM}({skill_count} skills to .opencode/skills/){NC}"
                )
            else:
                step_warn(f"Copy skill files  {DIM}copy failed{NC}")

        step_run("Write OpenCode config")
        opencode_project_config = f"{work_dir.rstrip('/')}/opencode.json"
        opencode_config = _build_opencode_config(
            agent_name=agent_name,
            model_ref=model_ref,
            variant=variant,
            agent_options=agent_options,
            agents_md_content=agents_md_content,
            skill_container_dir=skill_container_dir,
            permission_config=permission_config,
            steps=steps,
            mcp_config=mcp_config,
            shell_path=(
                _OPENCODE_NETWORK_SANDBOX_SHELL
                if shell_network_sandbox
                else None
            ),
            config_overrides=config_overrides,
        )
        opencode_config_content = json.dumps(opencode_config, indent=2) + "\n"
        (instance_outdir / "opencode.json").write_text(
            opencode_config_content,
            encoding="utf-8",
        )
        if docker_pipe_stdin(
            container_id,
            opencode_config_content,
            opencode_project_config,
        ):
            step_ok("Write OpenCode config")
        else:
            step_warn(f"Write OpenCode config  {DIM}copy failed{NC}")

        if refresh_models:
            provider_id = _provider_id_from_model_ref(model_ref)
            run_step(
                "Refresh OpenCode model registry",
                container_id,
                180,
                (
                    f"{opencode_path_export}"
                    f"cd {shlex.quote(work_dir)} && "
                    f"{shlex.quote(opencode_cli)} models "
                    f"{shlex.quote(provider_id)} --refresh >/tmp/opencode-models-refresh.log 2>&1"
                ),
            )

        # run_step(
        #     "Initialize git repo",
        #     container_id,
        #     60,
        #     (
        #         f"cd {shlex.quote(work_dir)} && "
        #         "(git rev-parse --is-inside-work-tree 2>/dev/null || "
        #         "(git init && git add -A && "
        #         "git -c user.email=secbench@example.invalid "
        #         "-c user.name=SEC-bench "
        #         "commit -m 'Initial commit' --allow-empty))"
        #     ),
        # )

        if common.INTERRUPTED:
            return 130

        prompt_container_path = f"/tmp/opencode-eval-prompt-{instance_id}.txt"
        docker_pipe_stdin(container_id, prompt, prompt_container_path)

        if tracking == "acov":
            path_export = (
                ACOV_PYTHON_AUDIT_ENV_SH
                + f'export PATH="{ACOV_SHIM_DIR}:$HOME/.opencode/bin:$HOME/.local/bin:$HOME/.cargo/bin:/usr/local/bin:$PATH" && '
                + 'export NVM_DIR="$HOME/.nvm" && '
                + 'if [ -s "$NVM_DIR/nvm.sh" ]; then . "$NVM_DIR/nvm.sh" 2>/dev/null || true; fi && '
                + f'export ACOV_DB="{acov_db_container_path(work_dir)}" && '
                + f'export ACOV_EVENT_LOG="{acov_event_log_container_path(work_dir)}" && '
                + f'export ACOV_SOCKET="{ACOV_SOCKET_PATH}" && '
                + f'export ACOV_PROJECT_ROOT="{work_dir}" && '
                + f'export ACOV_SHIM_DIR="{ACOV_SHIM_DIR}" && '
            )
        else:
            path_export = opencode_path_export

        aws_region_export = (
            'if [ -z "${AWS_REGION:-}" ]; then '
            'export AWS_REGION="${AWS_REGION_NAME:-${AWS_DEFAULT_REGION:-}}"; '
            "fi && "
        )

        opencode_cmd_parts = [
            shlex.quote(opencode_cli),
            *(["--pure"] if pure else []),
            "run",
            "--format",
            shlex.quote(output_format),
            "--agent",
            shlex.quote(agent_name),
        ]
        opencode_cmd_parts.append(
            '"$(cat ' + shlex.quote(prompt_container_path) + ')"'
        )

        opencode_cmd = (
            f"{path_export}"
            f"{aws_region_export}"
            "export TERM=xterm-256color && "
            "export COLORTERM=truecolor && "
            "export FORCE_COLOR=1 && "
            "export OPENCODE_DISABLE_AUTOUPDATE=1 && "
            "export OPENCODE_DISABLE_DEFAULT_PLUGINS=1 && "
            "unset OPENCODE_ENABLE_EXA && "
            f"cd {shlex.quote(work_dir)} && "
            + " ".join(opencode_cmd_parts)
        )

        common._emit(
            f"  {YELLOW}\u25c9{NC} Run OpenCode agent  "
            f"{DIM}(timeout={timeout_secs}s, model={model_ref}){NC}"
        )
        info("Agent output:")
        common._emit(f"{DIM}{'─' * 64}{NC}")

        agent_stdout_file = instance_outdir / "agent_stdout.txt"
        reasoning_tailer = _OpenCodeReasoningTailer(container_id=container_id)
        agent_exit = docker_exec_streaming(
            container_id,
            opencode_cmd,
            timeout_secs,
            agent_stdout_file,
            agent_type="opencode",
            line_hook=reasoning_tailer,
        )
        for formatted in reasoning_tailer.flush():
            common._emit(formatted)

        common._emit(f"{DIM}{'─' * 64}{NC}")

        if agent_exit == 0:
            step_ok(f"Run OpenCode agent  {DIM}exit 0{NC}")
        else:
            step_err(f"Run OpenCode agent  {DIM}exit {agent_exit}{NC}")
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

        collect_opencode_artifacts(
            container_id,
            work_dir,
            instance_outdir,
            instance_id,
            artifact_mode,
        )
        collect_worktree_artifacts(container_id, work_dir, instance_outdir)
        collect_shell_network_sandbox_artifact(container_id, instance_outdir)
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
        description="Evaluate OpenCode agent inside Docker containers",
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
    api = config.get("api", "openrouter")
    if api not in _OPENCODE_PROVIDER_SETTINGS:
        error(
            f"Invalid api '{api}'. Must be one of: "
            f"{', '.join(sorted(_OPENCODE_PROVIDER_SETTINGS))}."
        )
        return 1
    config["api"] = api
    _warn_missing_provider_env(api)

    variant = config.get("variant")
    if variant in ("", None, False):
        variant = None
    elif not isinstance(variant, str) or not variant.strip():
        error("Invalid variant. Must be a non-empty string.")
        return 1
    config["variant"] = variant

    reasoning_effort = config.get("reasoning_effort")
    if reasoning_effort in ("", None, False):
        reasoning_effort = None
    elif not isinstance(reasoning_effort, str) or not reasoning_effort.strip():
        error("Invalid reasoning_effort. Must be a non-empty string.")
        return 1
    config["reasoning_effort"] = reasoning_effort

    agent_options: dict[str, Any] = {}
    for options_key in ("agent_options", "model_options", "opencode_agent_options"):
        if options_key not in config:
            continue
        value = config[options_key]
        if not isinstance(value, dict):
            error(f"Invalid {options_key}. Must be a TOML table when set.")
            return 1
        agent_options = _deep_merge_dict(agent_options, value)
    if reasoning_effort:
        if (
            "reasoningEffort" in agent_options
            and agent_options["reasoningEffort"] != reasoning_effort
        ):
            warn(
                "Both reasoning_effort and agent_options.reasoningEffort are set; "
                "using agent_options.reasoningEffort."
            )
        else:
            agent_options["reasoningEffort"] = reasoning_effort
    config["agent_options"] = agent_options or None

    artifact_mode = config.get("opencode_artifacts", "compact")
    if (
        not isinstance(artifact_mode, str)
        or artifact_mode not in _OPENCODE_ARTIFACT_MODES
    ):
        error(
            "Invalid opencode_artifacts. Must be one of: "
            f"{', '.join(sorted(_OPENCODE_ARTIFACT_MODES))}."
        )
        return 1
    config["opencode_artifacts"] = artifact_mode

    for bool_key in (
        "privileged",
        "refresh_models",
        "update_opencode_cli",
        "pure",
        "shell_network_sandbox",
    ):
        if bool_key in config and not isinstance(config[bool_key], bool):
            error(f"Invalid {bool_key}. Must be true or false.")
            return 1
    config["privileged"] = config.get(
        "privileged",
        common.is_linux_project(config.get("project", "")),
    )
    config["refresh_models"] = config.get("refresh_models", True)
    config["update_opencode_cli"] = config.get("update_opencode_cli", False)
    config["pure"] = config.get("pure", True)
    config["shell_network_sandbox"] = config.get("shell_network_sandbox", False)

    opencode_update_method = config.get("opencode_update_method", "npm")
    if (
        not isinstance(opencode_update_method, str)
        or opencode_update_method not in {"curl", "npm", "pnpm", "bun", "brew"}
    ):
        error(
            "Invalid opencode_update_method. Must be one of: "
            "curl, npm, pnpm, bun, brew."
        )
        return 1
    config["opencode_update_method"] = opencode_update_method

    if "network_isolation" in config:
        warn(
            "network_isolation is deprecated for OpenCode and ignored; "
            "shell_network_sandbox=true isolates bash tool calls without "
            "domain heuristics."
        )

    if "steps" in config and not isinstance(config["steps"], int):
        error("Invalid steps. Must be an integer when set.")
        return 1

    if "opencode_config" in config and not isinstance(config["opencode_config"], dict):
        error("Invalid opencode_config. Must be a TOML table when set.")
        return 1

    try:
        config["permission"] = _normalize_permission_config(
            config.get("permission", _DEFAULT_PERMISSION_CONFIG),
        )
    except ValueError as exc:
        error(str(exc))
        return 1

    try:
        config["mcp"] = _normalize_opencode_mcp_servers(config.get("mcp"))
    except ValueError as exc:
        error(str(exc))
        return 1

    if config["mcp"]:
        for server_name in config["mcp"]:
            if not _permission_allows_mcp_server(config["permission"], server_name):
                error(
                    f"mcp.{server_name} requires a permission entry like "
                    f"'{server_name}_* = \"allow\"'."
                )
                return 1

    if (
        config["shell_network_sandbox"]
        and isinstance(config.get("opencode_config"), dict)
        and "shell" in config["opencode_config"]
    ):
        warn(
            "opencode_config.shell is ignored because "
            "shell_network_sandbox=true."
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
    info(f"API: {api}")
    info(f"OpenCode model ref: {_model_ref(api, model)}")
    info(f"Tracking: {tracking}")
    info(f"Timeout: {timeout_secs}s")
    if variant:
        info(f"Variant: {variant}")
    if config.get("reasoning_effort"):
        info(f"Reasoning effort option: {config['reasoning_effort']}")
    if config.get("agent_options"):
        info(
            "Agent provider options: "
            + ", ".join(sorted(config["agent_options"].keys()))
        )
    info(f"OpenCode artifacts: {config.get('opencode_artifacts', 'compact')}")
    info(f"Output format: {config.get('output_format', 'json')}")
    if config.get("refresh_models", True):
        info("Refresh OpenCode models: true")
    else:
        info("Refresh OpenCode models: false")
    if config.get("update_opencode_cli"):
        info(
            "Update OpenCode CLI: true "
            f"(method={config['opencode_update_method']})"
        )
    else:
        info("Update OpenCode CLI: false")
    info(f"OpenCode pure mode: {str(config.get('pure', True)).lower()}")
    if config.get("shell_network_sandbox", False):
        info("OpenCode shell network sandbox: enabled")
    else:
        info("OpenCode shell network sandbox: disabled")
    if config.get("mcp"):
        info(f"OpenCode MCP servers: {', '.join(sorted(config['mcp']))}")
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
    info(f"Instances: {' '.join(instances)}")

    return run_eval_loop(
        instances=instances,
        images_dir=images_dir,
        run_outdir=run_outdir,
        prompt_template_path=prompt_template_path,
        config=config,
        agent_label=f"opencode/{model}",
        run_instance_fn=run_instance,
        use_tui=not args.no_tui,
        agents_md=agents_md,
        skill_directory=skill_directory,
        acov_path=acov_path,
        acov_subsystems=acov_subsystems,
    )


if __name__ == "__main__":
    sys.exit(main())
