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
import re
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
    install_cached_sandbox_tools,
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
# Codex provider configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CodexProviderSettings:
    codex_model_provider: str
    forwarded_env_vars: tuple[str, ...]


_CODEX_PROVIDER_SETTINGS: dict[str, CodexProviderSettings] = {
    "openai": CodexProviderSettings(
        codex_model_provider="openai",
        forwarded_env_vars=("OPENAI_API_KEY",),
    ),
    "bedrock": CodexProviderSettings(
        codex_model_provider="amazon-bedrock",
        forwarded_env_vars=(
            "AWS_BEARER_TOKEN_BEDROCK",
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_SESSION_TOKEN",
            "AWS_REGION",
            "AWS_REGION_NAME",
            "AWS_DEFAULT_REGION",
            "AWS_PROFILE",
        ),
    ),
}

_CODEX_AUTH_ENV_VARS = ("OPENAI_API_KEY",)
_CODEX_DEFAULT_HOST_AUTH = "~/.codex/auth.json"
_CODEX_AUTH_CONTAINER_PATH = "/root/.codex/auth.json"


def _normalize_copy_host_auth(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return _CODEX_DEFAULT_HOST_AUTH if value else None
    if isinstance(value, str):
        return value.strip() or None
    raise ValueError(
        "Invalid copy_host_auth. Must be omitted, a path string, or false."
    )


def _normalize_add_dirs(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        candidates = [value]
    elif isinstance(value, list):
        candidates = value
    else:
        raise ValueError("Invalid add_dirs. Must be a string or list of strings.")

    add_dirs: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if not isinstance(candidate, str) or not candidate.strip():
            raise ValueError("Invalid add_dirs. Entries must be non-empty strings.")
        path = candidate.strip()
        if "\x00" in path:
            raise ValueError("Invalid add_dirs. Entries must not contain NUL bytes.")
        if not path.startswith("/"):
            raise ValueError("Invalid add_dirs. Entries must be absolute container paths.")
        if path == "/":
            raise ValueError("Invalid add_dirs. Refusing to make / writable.")
        if path not in seen:
            add_dirs.append(path)
            seen.add(path)
    return add_dirs


def _warn_missing_provider_env(provider: str) -> None:
    if provider == "openai":
        if not os.environ.get("OPENAI_API_KEY"):
            warn(
                "copy_host_auth is omitted/disabled and OPENAI_API_KEY is unset; "
                "Codex may fail to authenticate."
            )
        return

    if provider == "bedrock":
        if not (
            os.environ.get("AWS_REGION")
            or os.environ.get("AWS_REGION_NAME")
            or os.environ.get("AWS_DEFAULT_REGION")
        ):
            warn(
                "AWS_REGION, AWS_REGION_NAME, and AWS_DEFAULT_REGION are unset "
                "on the host; Codex Bedrock may fail to select a region."
            )

        has_api_key = bool(os.environ.get("AWS_BEARER_TOKEN_BEDROCK"))
        has_static_creds = bool(
            os.environ.get("AWS_ACCESS_KEY_ID")
            and os.environ.get("AWS_SECRET_ACCESS_KEY")
        )
        has_profile = bool(os.environ.get("AWS_PROFILE"))
        if not (has_api_key or has_static_creds or has_profile):
            warn(
                "No Bedrock API key, AWS access keys, or AWS_PROFILE are set "
                "on the host; Codex may fail unless AWS credentials are already "
                "available inside the container."
            )


def _deep_merge_config(
    base: dict[str, object],
    override: dict[str, object],
) -> dict[str, object]:
    merged = dict(base)
    for key, value in override.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            merged[key] = _deep_merge_config(current, value)
        else:
            merged[key] = value
    return merged


def _toml_key(key: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_-]+", key):
        return key
    return json.dumps(key)


def _toml_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float) and not isinstance(value, bool):
        return json.dumps(value)
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, list):
        return "[" + ", ".join(_toml_value(item) for item in value) + "]"
    raise ValueError(
        "codex_config values must be strings, numbers, booleans, lists, "
        "or nested TOML tables."
    )


def _toml_lines(table: dict[str, object], prefix: tuple[str, ...] = ()) -> list[str]:
    lines: list[str] = []
    nested: list[tuple[str, dict[str, object]]] = []
    for key, value in table.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("codex_config keys must be non-empty strings.")
        if isinstance(value, dict):
            nested.append((key, value))
        else:
            lines.append(f"{_toml_key(key)} = {_toml_value(value)}")

    for key, value in nested:
        if lines and lines[-1] != "":
            lines.append("")
        section = ".".join(_toml_key(part) for part in (*prefix, key))
        lines.append(f"[{section}]")
        child_lines = _toml_lines(value, (*prefix, key))
        lines.extend(child_lines)

    return lines


def _build_codex_config(
    *,
    model: str,
    reasoning_effort: str,
    config: dict,
) -> str:
    provider = str(config.get("provider", "openai"))
    if provider not in _CODEX_PROVIDER_SETTINGS:
        raise ValueError(
            f"Invalid provider '{provider}'. Must be one of: "
            f"{', '.join(sorted(_CODEX_PROVIDER_SETTINGS))}."
        )
    provider_settings = _CODEX_PROVIDER_SETTINGS[provider]
    custom_config = config.get("codex_config") or {}
    codex_config = _deep_merge_config(
        {
            "model": model,
            "model_provider": provider_settings.codex_model_provider,
            "model_reasoning_effort": reasoning_effort,
        },
        custom_config,
    )
    return "\n".join(_toml_lines(codex_config)) + "\n"


def _copy_codex_auth_to_container(container_id: str, source: str) -> int:
    step_run("Copy host auth.json to container")
    setup_rc, _stdout, setup_stderr = docker_exec(
        container_id,
        "mkdir -p /root/.codex/",
        10,
    )
    if setup_rc != 0:
        detail = setup_stderr[:120].replace("\n", " ") if setup_stderr else ""
        step_err(
            "Copy host auth.json to container  "
            f"{DIM}(setup failed: {detail or f'exit {setup_rc}'}){NC}"
        )
        return setup_rc

    if not docker_copy_to(container_id, source, _CODEX_AUTH_CONTAINER_PATH):
        step_err(f"Copy host auth.json to container  {DIM}copy failed{NC}")
        return 1

    chmod_rc, _stdout, chmod_stderr = docker_exec(
        container_id,
        f"chown root:root {shlex.quote(_CODEX_AUTH_CONTAINER_PATH)} && "
        f"chmod 600 {shlex.quote(_CODEX_AUTH_CONTAINER_PATH)}",
        10,
    )
    if chmod_rc != 0:
        detail = chmod_stderr[:120].replace("\n", " ") if chmod_stderr else ""
        step_err(
            "Copy host auth.json to container  "
            f"{DIM}(chmod failed: {detail or f'exit {chmod_rc}'}){NC}"
        )
        return chmod_rc

    step_ok(f"Copy host auth.json to container  {DIM}({_CODEX_AUTH_CONTAINER_PATH}){NC}")
    return 0


def _codex_approval_policy(approval_mode: str) -> str:
    return approval_mode


# secb MCP server: the in-container harness exposed to the agent as MCP tools.
# Codex spawns it OUTSIDE its bubblewrap sandbox, so QEMU launched from it gets
# native KVM (the container provides /dev/kvm) while the agent's own shell
# commands stay sandboxed. The agent calls secb_validate/secb_repro instead of
# running `secb` directly, which also makes the harness tamper-proof.
# secb-linux-vm-mcp is vendored in this repo at mcps/linux/. Container setup
# installs the vendored copy so eval runs do not depend on a stale baked package.


def _overlay_privilege_aware_init(
    container_id: str, linux_instance_dir: "Path | None"
) -> int:
    """Overlay the repo's privilege-aware init.sh into the container's initramfs
    source so the PoC runs at the CVE's declared privilege (uid 1000 for "user",
    init-ns root for "root"). This keeps the source of truth in the repo until
    images are rebuilt with it. No-op if the instance dir has no init.sh.
    """
    if linux_instance_dir is None:
        return 0
    init_src = Path(linux_instance_dir) / "init.sh"
    if not init_src.is_file():
        return 0
    try:
        meta_p = Path(linux_instance_dir) / "meta.json"
        priv = (
            json.loads(meta_p.read_text()).get("privilege")
            if meta_p.is_file()
            else None
        ) or "user"
    except Exception:
        priv = "user"
    where = "runs as init-ns root (uid 0)" if priv == "root" else "runs as uid 1000"
    step_run("Overlay privilege-aware init.sh")
    if not docker_copy_to(container_id, str(init_src), "/rootfs/init.sh"):
        step_err(f"Overlay privilege-aware init.sh  {DIM}copy failed{NC}")
        return 1
    docker_exec(container_id, "chmod +x /rootfs/init.sh", 10)
    step_ok(f"Overlay privilege-aware init.sh  {DIM}({where}){NC}")
    return 0


def _seed_reference_poc(
    container_id: str,
    linux_instance_dir: "Path | None",
    work_dir: str,
    config: dict,
) -> int:
    """Seed the benchmark's reference PoC into the agent's audit/ as a starting
    point (PoC-conversion mode). No-op unless `seed_reference_poc` is set in the
    run config.
    """
    if not config.get("seed_reference_poc"):
        return 0
    if linux_instance_dir is None:
        return 0
    poc_c = Path(linux_instance_dir) / "poc" / "poc.c"
    if not poc_c.is_file():
        return 0
    step_run("Seed reference PoC")
    audit = f"{work_dir}/audit"
    docker_exec(container_id, f"mkdir -p {shlex.quote(audit)}", 10)
    if not docker_copy_to(container_id, str(poc_c), f"{audit}/poc.c"):
        step_err(f"Seed reference PoC  {DIM}copy failed{NC}")
        return 1
    step_ok(f"Seed reference PoC  {DIM}({audit}/poc.c){NC}")
    return 0


def _setup_secb_mcp(container_id: str, config: dict) -> int:
    """Ensure the `secb-linux-vm-mcp` console script is available in the container.

    No-op unless the codex config registers an `secb` MCP server. The vendored
    package is copied in and installed at runtime so the harness uses the repo
    version even when an older package is baked into the image.
    The command (`secb-linux-vm-mcp`) is declared by the run config under
    [codex_config.mcp_servers.secb].
    """
    mcp_servers = (config.get("codex_config") or {}).get("mcp_servers") or {}
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


def _ensure_codex_sandbox_dependencies(
    container_id: str,
    sandbox: str,
    codex_cli: str,
) -> int:
    if sandbox == "danger-full-access":
        return 0

    step_run("Ensure Codex sandbox dependency")
    quoted_cli = shlex.quote(codex_cli)
    check_rc, check_stdout, _stderr = docker_exec(
        container_id,
        f"""
if command -v bwrap >/dev/null 2>&1; then
  echo system
  exit 0
fi
codex_path=$(command -v {quoted_cli} 2>/dev/null || true)
if [ -n "$codex_path" ]; then
  codex_root=$(dirname "$(dirname "$(readlink -f "$codex_path")")")
  if find "$codex_root" -path '*/codex-resources/bwrap' -type f -perm -111 \
      -print -quit 2>/dev/null | grep -q .; then
    echo bundled
    exit 0
  fi
fi
exit 1
""",
        30,
    )
    if check_rc == 0:
        source = check_stdout.strip() or "available"
        step_ok(f"Ensure Codex sandbox dependency  {DIM}({source}){NC}")
        return 0

    cache_ok, cache_detail = install_cached_sandbox_tools(
        container_id,
        ("bwrap",),
    )
    if cache_ok:
        step_ok(
            f"Ensure Codex sandbox dependency  {DIM}({cache_detail}){NC}"
        )
        return 0
    step_warn(
        "Ensure Codex sandbox dependency  "
        f"{DIM}(cache unavailable: {cache_detail}; trying package manager){NC}"
    )

    install_cmd = r"""
set -eu
log=/tmp/codex-sandbox-deps-install.log
: > "$log"
if command -v apt-get >/dev/null 2>&1; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get -o DPkg::Lock::Timeout=60 update -qq >>"$log" 2>&1
  apt-get -o DPkg::Lock::Timeout=60 install -y -qq --no-install-recommends \
    bubblewrap >>"$log" 2>&1
  rm -rf /var/lib/apt/lists/*
elif command -v apk >/dev/null 2>&1; then
  apk add --no-cache bubblewrap >>"$log" 2>&1
elif command -v dnf >/dev/null 2>&1; then
  dnf install -y bubblewrap >>"$log" 2>&1
elif command -v yum >/dev/null 2>&1; then
  yum install -y bubblewrap >>"$log" 2>&1
else
  echo "no supported package manager found" >>"$log"
  exit 127
fi
command -v bwrap >/dev/null 2>&1
"""
    install_rc, _stdout, stderr = docker_exec(container_id, install_cmd, 300)
    if install_rc == 0:
        step_ok(f"Ensure Codex sandbox dependency  {DIM}(installed){NC}")
        return 0

    _tail_rc, tail_stdout, _tail_stderr = docker_exec(
        container_id,
        "tail -n 20 /tmp/codex-sandbox-deps-install.log 2>/dev/null || true",
        30,
    )
    detail_source = tail_stdout or stderr
    detail = detail_source[:240].replace("\n", " ") if detail_source else ""
    step_err(
        "Ensure Codex sandbox dependency  "
        f"{DIM}(failed: {detail or f'exit {install_rc}'}){NC}"
    )
    return install_rc


# Cheat-source domains blackholed in danger-full-access (unsandboxed) runs.
# The agent must solve the CVE from the local kernel tree + harness output
# only; it must not fetch upstream fixes, public PoCs, or CVE writeups. The
# model API endpoints are deliberately absent so Codex itself keeps working.
_NETWORK_BLACKLIST_DOMAINS = (
    "github.com", "www.github.com", "raw.githubusercontent.com",
    "gist.github.com", "gist.githubusercontent.com", "objects.githubusercontent.com",
    "codeload.github.com", "gitlab.com", "bitbucket.org",
    "git.kernel.org", "lore.kernel.org", "lkml.org", "lwn.net",
    "patchwork.kernel.org", "cdn.kernel.org", "mirrors.edge.kernel.org",
    "googlesource.com", "android.googlesource.com", "git.savannah.gnu.org",
    "nvd.nist.gov", "cve.mitre.org", "cve.org", "www.cve.org",
    "exploit-db.com", "www.exploit-db.com", "packetstormsecurity.com",
    "google.com", "www.google.com", "bing.com", "duckduckgo.com",
    "stackoverflow.com", "syzkaller.appspot.com", "huggingface.co",
)


def _apply_network_blacklist(container_id: str, config: dict) -> int:
    """Tier-1 egress block for unsandboxed (danger-full-access) Codex runs.

    Appends 0.0.0.0/::1 blackhole entries for known cheat-source domains to the
    container's /etc/hosts. Best-effort: it covers the listed hostnames and the
    model API is left reachable so Codex still functions. /etc/hosts is managed
    by Docker at runtime, hence applied here (after start) rather than baked in.
    """
    if config.get("network_isolation") != "dns":
        return 0
    step_run("Apply network blacklist (DNS blackhole)")
    entries = "\\n# secb egress blacklist (danger-full-access mode)\\n" + "".join(
        f"0.0.0.0 {d}\\n::1 {d}\\n" for d in _NETWORK_BLACKLIST_DOMAINS
    )
    cmd = "printf '%b' " + shlex.quote(entries) + " >> /etc/hosts"
    rc, _out, err = docker_exec(container_id, cmd, 30)
    if rc == 0:
        step_ok(
            "Apply network blacklist  "
            f"{DIM}({len(_NETWORK_BLACKLIST_DOMAINS)} domains blackholed){NC}"
        )
    else:
        detail = (err or "").replace("\n", " ")[:100]
        step_err(f"Apply network blacklist  {DIM}({detail or f'exit {rc}'}){NC}")
    return rc


def _validate_codex_config(config: dict) -> None:
    codex_config = config.get("codex_config")
    if codex_config is None:
        raise ValueError(
            "Missing codex_config. Benchmark runs must explicitly configure "
            "Codex sandbox and web_search policy."
        )
    if not isinstance(codex_config, dict):
        raise ValueError("Invalid codex_config. Must be a TOML table.")

    reserved = ("model", "model_provider", "model_reasoning_effort")
    for key in reserved:
        if key in codex_config:
            raise ValueError(
                f"Invalid codex_config.{key}. Use the top-level provider/model "
                "settings."
            )

    sandbox = config["sandbox"]
    if sandbox not in ("workspace-write", "danger-full-access"):
        raise ValueError(
            "Codex benchmark runs require sandbox to be 'workspace-write' or "
            "'danger-full-access'."
        )
    configured_sandbox = codex_config.get("sandbox_mode")
    if configured_sandbox is not None and configured_sandbox != sandbox:
        raise ValueError(
            "codex_config.sandbox_mode must match the top-level sandbox setting."
        )

    approval_policy = _codex_approval_policy(config["approval_mode"])
    if approval_policy != "never":
        raise ValueError(
            "Codex benchmark runs require approval_mode='never' for unattended runs."
        )
    configured_approval = codex_config.get("approval_policy")
    if configured_approval is not None and configured_approval != approval_policy:
        raise ValueError(
            "codex_config.approval_policy must match the top-level approval_mode."
        )

    if sandbox == "workspace-write":
        # bubblewrap puts agent commands in a network namespace; require the
        # workspace-write network toggle off so they cannot reach the internet.
        workspace_write = codex_config.get("sandbox_workspace_write")
        if (
            not isinstance(workspace_write, dict)
            or workspace_write.get("network_access") is not False
        ):
            raise ValueError(
                "sandbox='workspace-write' requires "
                "codex_config.sandbox_workspace_write.network_access=false."
            )
    else:  # danger-full-access
        # No bubblewrap, so agent commands run unsandboxed and can open
        # /dev/kvm for native KVM acceleration. That also removes bubblewrap's
        # netns isolation, so a container-level egress blacklist must stand in
        # for it (Tier-1 DNS blackhole of cheat-source domains).
        if config.get("network_isolation") != "dns":
            raise ValueError(
                "sandbox='danger-full-access' requires network_isolation='dns' "
                "to blackhole agent internet egress to cheat-source domains."
            )

    if codex_config.get("web_search") != "disabled":
        raise ValueError(
            "codex_config.web_search must be 'disabled' for benchmark runs."
        )

    _build_codex_config(
        model=str(config["model"]),
        reasoning_effort=str(config["reasoning_effort"]),
        config=config,
    )


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
    provider: str = config.get("provider", "openai")
    provider_settings = _CODEX_PROVIDER_SETTINGS[provider]

    # Codex-specific config
    codex_cli: str = config.get("codex_cli", "codex")
    approval_mode: str = config["approval_mode"]
    sandbox: str = config["sandbox"]
    strict_config: bool = config.get("strict_config", False)
    json_output: bool = config.get("json_output", False)
    copy_host_auth: str | None = config.get("copy_host_auth")
    add_dirs: list[str] = config.get("add_dirs", [])
    update_codex_cli: bool = config.get("update_codex_cli", True)
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
    forwarded_env_vars = () if copy_host_auth else provider_settings.forwarded_env_vars
    env_args = build_env_args(forwarded_env_vars)
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

        if common.is_linux_project(project) and not common.require_linux_kvm(
            container_id
        ):
            return 1

        if update_codex_cli:
            update_rc = run_step(
                "Update Codex CLI",
                container_id,
                600,
                (
                    'export PATH="$HOME/.local/bin:$HOME/.cargo/bin:/usr/local/bin:$PATH" && '
                    'export NVM_DIR="$HOME/.nvm" && '
                    '[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" 2>/dev/null; '
                    "log=/tmp/codex-cli-update.log; : > \"$log\"; "
                    f"({shlex.quote(codex_cli)} update >>\"$log\" 2>&1 || "
                    "npm i -g @openai/codex@latest >>\"$log\" 2>&1) && "
                    f"{shlex.quote(codex_cli)} --version"
                ),
            )
            if update_rc != 0:
                return update_rc

        # 1. Configure Codex auth. Bedrock uses AWS-native auth and does not
        # need Codex's OpenAI auth.json.
        if provider == "openai":
            if copy_host_auth:
                auth_rc = _copy_codex_auth_to_container(container_id, copy_host_auth)
                if auth_rc != 0:
                    return auth_rc
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
        else:
            step_ok(f"Configure Codex auth  {DIM}(provider={provider}, AWS auth){NC}")

        step_run("Write Codex config")
        docker_exec(container_id, "mkdir -p /root/.codex/", 10)
        codex_config_content = _build_codex_config(
            model=model,
            reasoning_effort=reasoning_effort,
            config=config,
        )
        (instance_outdir / "config.toml").write_text(
            codex_config_content,
            encoding="utf-8",
        )
        if docker_pipe_stdin(container_id, codex_config_content, "/root/.codex/config.toml"):
            step_ok("Write Codex config")
        else:
            step_warn(f"Write Codex config  {DIM}copy failed{NC}")

        sandbox_dep_rc = _ensure_codex_sandbox_dependencies(
            container_id,
            sandbox,
            codex_cli,
        )
        if sandbox_dep_rc != 0:
            return sandbox_dep_rc

        # Ensure the PoC runs at the privilege declared by meta.json.
        init_rc = _overlay_privilege_aware_init(container_id, linux_instance_dir)
        if init_rc != 0:
            return init_rc

        # Set up the secb MCP server (in-container harness behind MCP tools).
        # Runs outside Codex's sandbox -> QEMU gets native KVM, while the agent
        # stays sandboxed. No-op unless the run config registers it.
        secb_mcp_rc = _setup_secb_mcp(container_id, config)
        if secb_mcp_rc != 0:
            return secb_mcp_rc

        # Conversion mode: seed the reference (root) PoC for the agent to convert.
        seed_rc = _seed_reference_poc(
            container_id, linux_instance_dir, work_dir, config
        )
        if seed_rc != 0:
            return seed_rc

        # Unsandboxed runs lose bubblewrap's netns isolation; substitute a
        # container-level DNS blackhole so the agent cannot fetch cheat sources.
        blacklist_rc = _apply_network_blacklist(container_id, config)
        if blacklist_rc != 0:
            return blacklist_rc

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
            codex_invoker = shlex.quote(codex_cli)

        # Build the codex CLI command
        # Approval policy is a top-level Codex option in current CLI versions,
        # while sandbox remains accepted on `codex exec`.
        approval_policy = _codex_approval_policy(approval_mode)

        codex_cmd = (
            f"{nvm_setup}"
            f"{path_export}"
            f"unset {' '.join(_CODEX_AUTH_ENV_VARS)} && "
            "export TERM=xterm-256color && "
            "export COLORTERM=truecolor && "
            "export FORCE_COLOR=1 && "
            "export RUST_LOG='codex_core::session=off' && "
            f"cd {work_dir} && "
            f"{codex_invoker} "
        )
        if strict_config:
            codex_cmd += "--strict-config "
        codex_cmd += (
            f"-a {shlex.quote(approval_policy)} "
            "exec "
            f"-s {shlex.quote(sandbox)} "
        )
        for add_dir in add_dirs:
            codex_cmd += f"--add-dir {shlex.quote(add_dir)} "

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
    provider = config.get("provider", "openai")
    if not isinstance(provider, str) or not provider.strip():
        error("Missing or invalid provider. Must be a non-empty string.")
        return 1
    provider = provider.strip().lower()
    if provider not in _CODEX_PROVIDER_SETTINGS:
        error(
            f"Invalid provider '{provider}'. Must be one of: "
            f"{', '.join(sorted(_CODEX_PROVIDER_SETTINGS))}."
        )
        return 1
    config["provider"] = provider

    if "json_output" in config and not isinstance(config["json_output"], bool):
        error("Invalid json_output. Must be true or false.")
        return 1
    if "strict_config" in config and not isinstance(config["strict_config"], bool):
        error("Invalid strict_config. Must be true or false.")
        return 1
    config["strict_config"] = config.get("strict_config", False)
    if "update_codex_cli" in config and not isinstance(config["update_codex_cli"], bool):
        error("Invalid update_codex_cli. Must be true or false.")
        return 1
    config["update_codex_cli"] = config.get("update_codex_cli", True)

    try:
        config["add_dirs"] = _normalize_add_dirs(config.get("add_dirs"))
    except ValueError as exc:
        error(str(exc))
        return 1

    try:
        copy_host_auth = _normalize_copy_host_auth(config.get("copy_host_auth"))
    except ValueError as exc:
        error(str(exc))
        return 1

    if provider == "bedrock":
        if copy_host_auth is not None:
            config["_copy_host_auth_ignored"] = True
        config["copy_host_auth"] = None
        _warn_missing_provider_env(provider)
    elif copy_host_auth is not None:
        copy_host_auth_path = resolve_path(SCRIPT_DIR, copy_host_auth)
        if not copy_host_auth_path.is_file():
            error(f"copy_host_auth file not found: {copy_host_auth_path}")
            return 1
        config["copy_host_auth"] = str(copy_host_auth_path)
    else:
        config["copy_host_auth"] = None
        _warn_missing_provider_env(provider)

    approval_mode = config.get("approval_mode")
    if not isinstance(approval_mode, str) or not approval_mode.strip():
        error("Missing or invalid approval_mode. Must be a non-empty string.")
        return 1
    config["approval_mode"] = approval_mode.strip()

    sandbox = config.get("sandbox")
    if not isinstance(sandbox, str) or not sandbox.strip():
        error("Missing or invalid sandbox. Must be a non-empty string.")
        return 1
    config["sandbox"] = sandbox.strip()

    reasoning_effort = config.get("reasoning_effort")
    if not isinstance(reasoning_effort, str) or not reasoning_effort.strip():
        error("Missing or invalid reasoning_effort. Must be a non-empty string.")
        return 1
    config["reasoning_effort"] = reasoning_effort.strip()

    try:
        _validate_codex_config(config)
    except ValueError as exc:
        error(str(exc))
        return 1

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
    info(f"Provider: {provider}")
    info(f"Tracking: {tracking}")
    info(f"Timeout: {timeout_secs}s")
    info(f"Reasoning effort: {config['reasoning_effort']}")
    info(f"Approval mode: {config['approval_mode']}")
    info(f"Sandbox: {config['sandbox']}")
    if config.get("strict_config"):
        info("Strict Codex config: true")
    if config.get("update_codex_cli"):
        info("Update Codex CLI: true")
    if config.get("add_dirs"):
        info(f"Codex writable dirs: {' '.join(config['add_dirs'])}")
    codex_config = config.get("codex_config") or {}
    if isinstance(codex_config, dict):
        if codex_config.get("web_search"):
            info(f"Codex web search: {codex_config['web_search']}")
        workspace_write = codex_config.get("sandbox_workspace_write")
        if isinstance(workspace_write, dict) and "network_access" in workspace_write:
            info(
                "Codex workspace network access: "
                f"{str(workspace_write['network_access']).lower()}"
            )
    if config.get("_copy_host_auth_ignored"):
        info("Copy host auth: ignored for provider=bedrock")
    if provider == "bedrock":
        info("Codex auth: AWS Bedrock")
    elif config.get("copy_host_auth"):
        info(
            "Copy host auth: "
            f"{config['copy_host_auth']} -> {_CODEX_AUTH_CONTAINER_PATH}"
        )
    else:
        info("Codex auth: OPENAI_API_KEY")
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
