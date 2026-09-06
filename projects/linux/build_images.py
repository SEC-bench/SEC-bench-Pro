#!/usr/bin/env python3
"""Build Docker images for the Linux kernel benchmark.

Supports building base, vulnerable, fixed, and latest images with parallel
execution and per-instance logging.

Examples:
    # Build everything (base first, then vuln+fixed+latest in parallel)
    python projects/linux/build_images.py --mode all -j 4

    # Build only vulnerable images for two CVEs
    python projects/linux/build_images.py --mode vuln --instances CVE-2022-0185 CVE-2021-22555

    # Build latest images with a specific kernel ref
    python projects/linux/build_images.py --mode latest --linux-ref v6.15 -j 8

    # Rebuild base image with no cache
    python projects/linux/build_images.py --mode base --no-cache
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

try:
    from rich.progress import (
        BarColumn,
        MofNCompleteColumn,
        Progress,
        SpinnerColumn,
        TextColumn,
        TimeElapsedColumn,
        TimeRemainingColumn,
    )
    from rich.text import Text
except ModuleNotFoundError as exc:
    if exc.name is None or not (exc.name == "rich" or exc.name.startswith("rich.")):
        raise
    RICH_AVAILABLE = False
else:
    RICH_AVAILABLE = True

REPO_ROOT = Path(__file__).resolve().parents[2]
LINUX_DIR = Path(__file__).resolve().parent
BASE_DIR = REPO_ROOT / "base" / "linux"
BASE_BUILDER = REPO_ROOT / "base" / "build_base_images.sh"
DEFAULT_LINUX_REF = "d2c9a99135da931377240942d44f3dea104cedb8"
BASE_IMAGE = "hwiwonlee/linux.base:latest"
BASE_LINEAGE_LABEL = "org.secbench.base-image-id"
REQUIRED_COMMITS_MANIFEST = BASE_DIR / "required-commits.txt"
BASE_COMPATIBILITY_TIMEOUT_SEC = 60
LINUX_BASE_REQUIRED_TOOLS = (
    "addr2line",
    "bwrap",
    "curl",
    "file",
    "gawk",
    "gdb",
    "envsubst",
    "git",
    "jq",
    "less",
    "locale",
    "ltrace",
    "make",
    "pkg-config",
    "ps",
    "killall",
    "python3",
    "pip3",
    "rg",
    "rsync",
    "socat",
    "sqlite3",
    "strace",
    "setpriv",
    "unshare",
    "valgrind",
    "vim",
    "xxd",
    "xz",
    "secb-sanitize-git",
    "codex",
    "opencode",
    "claude",
)

IMAGE_REPOS = {
    "base": "hwiwonlee/linux.base",
    "vuln": "hwiwonlee/linux.x86_64",
    "fixed": "hwiwonlee/linux.x86_64.fixed",
    "latest": "hwiwonlee/linux.x86_64.latest",
}


def ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_progress() -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TextColumn("elapsed"),
        TimeElapsedColumn(),
        TextColumn("eta"),
        TimeRemainingColumn(),
    )


def log(msg: str, progress: Progress | None = None) -> None:
    line = f"[{ts()}] {msg}"
    if progress:
        progress.console.print(Text(line))
    else:
        print(line, flush=True)


def discover_instances() -> list[str]:
    return sorted(
        d.name for d in LINUX_DIR.iterdir()
        if d.is_dir() and d.name.startswith("CVE-")
    )


def build_image(
    tag: str,
    context: Path,
    platform: str,
    dockerfile: Path | None = None,
    build_args: dict[str, str] | None = None,
    no_cache: bool = False,
    log_file: Path | None = None,
    skip_existing: bool = False,
    secrets: list[str] | None = None,
    labels: dict[str, str] | None = None,
) -> tuple[str, bool, float]:
    """Run a single docker build. Returns (tag, success, duration_seconds)."""
    if skip_existing:
        check = subprocess.run(
            ["docker", "image", "inspect", tag],
            capture_output=True,
        )
        if check.returncode == 0:
            if log_file:
                log_file.write_text(f"SKIPPED existing {tag}\n")
            return tag, True, 0.0

    cmd = ["docker", "build", "--platform", platform, "-t", tag]
    if dockerfile:
        cmd += ["-f", str(dockerfile)]
    if no_cache:
        cmd.append("--no-cache")
    for k, v in (build_args or {}).items():
        cmd += ["--build-arg", f"{k}={v}"]
    for s in secrets or []:
        cmd += ["--secret", s]
    for key, value in (labels or {}).items():
        cmd += ["--label", f"{key}={value}"]
    cmd.append(str(context))

    start = time.monotonic()
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env={**os.environ, "DOCKER_BUILDKIT": "1"},
    )
    elapsed = time.monotonic() - start

    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        log_file.write_bytes(result.stdout)

    return tag, result.returncode == 0, elapsed


def build_base(
    args: argparse.Namespace,
    log_dir: Path,
    progress: Progress | None = None,
    *,
    force_rebuild: bool = False,
) -> bool:
    task_id = None
    if progress:
        task_id = progress.add_task("base image", total=1)

    log(f"building base image: {BASE_IMAGE}", progress)
    log_file = log_dir / "base.log"
    if args.skip_existing and not force_rebuild and image_exists(BASE_IMAGE):
        log_file.parent.mkdir(parents=True, exist_ok=True)
        log_file.write_text(f"SKIPPED existing {BASE_IMAGE}\n")
        ok = True
        elapsed = 0.0
    else:
        cmd = [str(BASE_BUILDER), "--platform", args.platform]
        if args.no_cache:
            cmd.append("--no-cache")
        cmd.append("linux")

        start = time.monotonic()
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env={**os.environ, "DOCKER_BUILDKIT": "1"},
        )
        elapsed = time.monotonic() - start
        log_file.parent.mkdir(parents=True, exist_ok=True)
        log_file.write_bytes(result.stdout)
        ok = result.returncode == 0

    if progress and task_id is not None:
        progress.advance(task_id)

    if ok:
        log(f"base ok ({elapsed:.0f}s)", progress)
    else:
        log(f"base FAILED — see {log_file}", progress)
    return ok


def image_exists(tag: str) -> bool:
    """Return whether a local image tag exists."""
    try:
        result = subprocess.run(
            ["docker", "image", "inspect", tag],
            capture_output=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def image_id(tag: str) -> str | None:
    """Resolve one local tag to an immutable image ID."""
    try:
        result = subprocess.run(
            ["docker", "image", "inspect", "--format", "{{.Id}}", tag],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    candidate = result.stdout.strip()
    if result.returncode != 0 or not re.fullmatch(r"sha256:[0-9a-f]{64}", candidate):
        return None
    return candidate


def image_has_current_base_lineage(tag: str) -> bool:
    """Verify both the recorded base ID and immutable rootfs ancestry."""
    try:
        result = subprocess.run(
            ["docker", "image", "inspect", BASE_IMAGE, tag],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=30,
        )
        records = json.loads(result.stdout) if result.returncode == 0 else []
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return False
    if not isinstance(records, list) or len(records) != 2:
        return False
    base, image = records
    if not isinstance(base, dict) or not isinstance(image, dict):
        return False
    base_id = base.get("Id")
    if not isinstance(base_id, str) or not re.fullmatch(
        r"sha256:[0-9a-f]{64}", base_id
    ):
        return False
    base_rootfs = base.get("RootFS")
    image_config = image.get("Config")
    image_rootfs = image.get("RootFS")
    if (
        not isinstance(base_rootfs, dict)
        or not isinstance(image_config, dict)
        or not isinstance(image_rootfs, dict)
    ):
        return False
    labels = image_config.get("Labels") or {}
    if not isinstance(labels, dict) or labels.get(BASE_LINEAGE_LABEL) != base_id:
        return False
    base_layers = base_rootfs.get("Layers")
    image_layers = image_rootfs.get("Layers")
    return bool(
        isinstance(base_layers, list)
        and base_layers
        and isinstance(image_layers, list)
        and image_layers[: len(base_layers)] == base_layers
    )


def pending_instance_builds(
    mode: str,
    instances: list[str],
    *,
    skip_existing: bool,
) -> list[str]:
    """Return leaves that will reach docker build for this invocation."""
    if not skip_existing:
        return list(instances)
    repo = IMAGE_REPOS[mode]
    return [
        cve for cve in instances if not image_exists(f"{repo}:{cve}")
    ]


def fixed_dockerfile_uses_canonical_base(cve: str) -> bool:
    """Return whether one fixed leaf directly inherits linux.base."""
    dockerfile = LINUX_DIR / cve / "Dockerfile.fixed"
    try:
        source = dockerfile.read_text(encoding="utf-8")
    except OSError:
        return False
    match = re.search(r"^\s*FROM\s+(\S+)", source, flags=re.MULTILINE)
    return match is not None and match.group(1) == BASE_IMAGE


def fixed_dockerfile_vulnerable_parent(cve: str) -> str | None:
    """Return the exact paired vulnerable parent, or None for other parents."""
    dockerfile = LINUX_DIR / cve / "Dockerfile.fixed"
    try:
        source = dockerfile.read_text(encoding="utf-8")
    except OSError:
        return None
    match = re.search(r"^\s*FROM\s+(\S+)", source, flags=re.MULTILINE)
    if match is None:
        return None
    expected = f"{IMAGE_REPOS['vuln']}:{cve}"
    return expected if match.group(1) == expected else None


def mode_has_pending_base_dependency(
    mode: str,
    instances: list[str],
    *,
    skip_existing: bool,
) -> bool:
    """Return whether a pending leaf needs the canonical base contract."""
    pending = pending_instance_builds(
        mode,
        instances,
        skip_existing=skip_existing,
    )
    if mode in {"vuln", "latest"}:
        return bool(pending)
    if mode == "fixed":
        # A vulnerable-parent fixed leaf also needs the canonical base so its
        # immutable lineage can be checked and repaired before the fixed build.
        return bool(pending)
    return False


def linux_base_is_compatible(platform: str) -> bool:
    """Check the local canonical base against the current host contract."""
    try:
        manifest_sha256 = hashlib.sha256(
            REQUIRED_COMMITS_MANIFEST.read_bytes()
        ).hexdigest()
    except OSError:
        return False

    if not image_exists(BASE_IMAGE):
        return False

    tools = " ".join(LINUX_BASE_REQUIRED_TOOLS)
    probe = f"""set -eu
test -s /base/required-commits.txt
test \"$(sha256sum /base/required-commits.txt | awk '{{print $1}}')\" = \"$1\"
test -s /etc/secb-agent-versions
test -d /src/linux.git
test \"$(git --git-dir=/src/linux.git rev-parse --is-bare-repository)\" = true
while read -r commit _remote; do
    test -n \"$commit\" || continue
    git --git-dir=/src/linux.git cat-file -e \"$commit^{{commit}}\"
done < /base/required-commits.txt
for tool in {tools}; do
    command -v \"$tool\" >/dev/null
done
command -v secb-linux-vm-mcp >/dev/null
python3 -c 'import fastmcp, secb_linux_vm_mcp'
"""
    try:
        result = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "--platform",
                platform,
                "--network",
                "none",
                "--read-only",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--env",
                "PYTHONDONTWRITEBYTECODE=1",
                "--entrypoint",
                "/bin/sh",
                BASE_IMAGE,
                "-c",
                probe,
                "sh",
                manifest_sha256,
            ],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=BASE_COMPATIBILITY_TIMEOUT_SEC,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def ensure_compatible_linux_base(
    args: argparse.Namespace,
    log_dir: Path,
    progress: Progress | None = None,
) -> bool:
    """Rebuild an absent/stale standalone-mode base and verify the result."""
    if linux_base_is_compatible(args.platform):
        log(f"using compatible base image: {BASE_IMAGE}", progress)
        return True

    log(
        f"base image is missing the current manifest/runtime contract; "
        f"rebuilding {BASE_IMAGE}",
        progress,
    )
    if not build_base(args, log_dir, progress, force_rebuild=True):
        return False
    if not linux_base_is_compatible(args.platform):
        log(f"rebuilt base is still incompatible: {BASE_IMAGE}", progress)
        return False
    return True


def build_instances_parallel(
    mode: str,
    instances: list[str],
    args: argparse.Namespace,
    log_dir: Path,
    progress: Progress | None = None,
) -> list[str]:
    """Build vuln/fixed/latest images in parallel. Returns list of failed instance IDs."""
    repo = IMAGE_REPOS[mode]
    if mode == "vuln" and args.skip_existing:
        pending = pending_instance_builds(
            mode, instances, skip_existing=True
        )
        if not pending:
            log(f"[{mode}] all selected images already exist, skipping", progress)
            return []
    failed: list[str] = []
    task_id = None
    if progress:
        task_id = progress.add_task(f"{mode} images", total=len(instances))

    vulnerable_base_id = image_id(BASE_IMAGE) if mode == "vuln" else None
    if mode == "vuln" and vulnerable_base_id is None:
        log(f"[{mode}] cannot resolve immutable base ID for {BASE_IMAGE}", progress)
        return list(instances)

    def _build_one(cve: str) -> tuple[str, bool, float, Path]:
        tag = f"{repo}:{cve}"
        cve_dir = LINUX_DIR / cve
        log_file = log_dir / f"{mode}_{cve}.log"

        build_args: dict[str, str] = {}
        if args.kbuild_jobs is not None:
            build_args["KBUILD_JOBS"] = str(args.kbuild_jobs)

        if mode == "vuln":
            dockerfile = cve_dir / "Dockerfile"
        elif mode == "fixed":
            dockerfile = cve_dir / "Dockerfile.fixed"
        elif mode == "latest":
            dockerfile = BASE_DIR / "Dockerfile.latest"
            build_args["LINUX_REF"] = args.linux_ref
            if args.linux_ref.startswith("origin/"):
                build_args["LINUX_REF_CACHE_BUST"] = datetime.now(timezone.utc).strftime(
                    "%Y%m%dT%H%M%SZ"
                )
        else:
            raise ValueError(f"unknown mode: {mode}")

        if not dockerfile.exists():
            log_file.write_text(f"SKIPPED — {dockerfile.name} not found\n")
            return cve, False, 0.0, log_file

        _, ok, elapsed = build_image(
            tag=tag,
            context=cve_dir,
            platform=args.platform,
            dockerfile=dockerfile,
            build_args=build_args,
            no_cache=args.no_cache,
            log_file=log_file,
            skip_existing=args.skip_existing,
            labels=(
                {BASE_LINEAGE_LABEL: vulnerable_base_id}
                if mode == "vuln" and vulnerable_base_id is not None
                else None
            ),
        )
        return cve, ok, elapsed, log_file

    # For latest mode, warm the shared Docker cache with the first instance.
    start_idx = 0
    if mode == "latest" and len(instances) > 1 and args.parallel > 1:
        first = instances[0]
        log(f"[{mode}] warming cache with {first}", progress)
        cve, ok, elapsed, lf = _build_one(first)
        if progress and task_id is not None:
            progress.advance(task_id)
        if ok:
            log(f"[{mode}] {cve} ok ({elapsed:.0f}s)", progress)
        else:
            log(f"[{mode}] {cve} FAILED — see {lf}", progress)
            failed.append(cve)
        start_idx = 1

    remaining = instances[start_idx:]
    if not remaining:
        return failed

    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
        futures = {pool.submit(_build_one, cve): cve for cve in remaining}
        for future in as_completed(futures):
            cve, ok, elapsed, lf = future.result()
            if progress and task_id is not None:
                progress.advance(task_id)
            if ok:
                log(f"[{mode}] {cve} ok ({elapsed:.0f}s)", progress)
            else:
                log(f"[{mode}] {cve} FAILED — see {lf}", progress)
                failed.append(cve)

    return failed


def filter_instances(instances: list[str], mode: str) -> list[str]:
    """Filter instances that have the required Dockerfile for the given mode."""
    filtered = []
    for cve in instances:
        cve_dir = LINUX_DIR / cve
        if mode == "vuln" and (cve_dir / "Dockerfile").exists():
            filtered.append(cve)
        elif mode == "fixed" and (cve_dir / "Dockerfile.fixed").exists():
            filtered.append(cve)
        elif mode == "latest":
            # Latest uses base/linux/Dockerfile.latest with per-CVE context
            if (cve_dir / "secb_config.json").exists():
                filtered.append(cve)
        else:
            filtered.append(cve)
    return filtered


def unknown_requested_instances(instances: list[str]) -> list[str]:
    """Return explicit IDs that are not benchmark instance directories."""
    return sorted(
        {
            cve
            for cve in instances
            if not re.fullmatch(r"CVE-[A-Za-z0-9._-]+", cve)
            or not (LINUX_DIR / cve).is_dir()
        }
    )


def repair_fixed_vulnerable_parents(
    instances: list[str],
    args: argparse.Namespace,
    log_dir: Path,
    progress: Progress | None = None,
) -> list[str]:
    """Rebuild stale/missing vulnerable parents needed by pending fixed leaves."""
    pending = set(
        pending_instance_builds(
            "fixed", instances, skip_existing=args.skip_existing
        )
    )
    dependent: list[tuple[str, str]] = []
    failures: list[str] = []
    for cve in instances:
        if cve not in pending:
            continue
        if fixed_dockerfile_uses_canonical_base(cve):
            continue
        parent = fixed_dockerfile_vulnerable_parent(cve)
        if parent is None:
            log(
                f"[fixed] {cve} has an unsupported or mismatched parent image",
                progress,
            )
            failures.append(cve)
            continue
        dependent.append((cve, parent))

    stale = [cve for cve, parent in dependent if not image_has_current_base_lineage(parent)]
    if stale:
        log(
            f"[fixed] rebuilding {len(stale)} stale or missing vulnerable "
            "parent image(s)",
            progress,
        )
        parent_args = argparse.Namespace(**vars(args))
        parent_args.skip_existing = False
        rebuild_failures = build_instances_parallel(
            "vuln", stale, parent_args, log_dir, progress
        )
        failures.extend(rebuild_failures)

    failed = set(failures)
    for cve, parent in dependent:
        if cve in failed:
            continue
        if not image_has_current_base_lineage(parent):
            log(
                f"[fixed] {cve} vulnerable parent does not inherit the current "
                f"{BASE_IMAGE}",
                progress,
            )
            failures.append(cve)
            failed.add(cve)
    if args.push:
        for cve in stale:
            if cve in failed:
                continue
            tag = f"{IMAGE_REPOS['vuln']}:{cve}"
            log(f"[vuln] pushing repaired parent {tag}", progress)
            subprocess.run(
                ["docker", "push", tag],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build Linux kernel benchmark Docker images.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--mode",
        choices=["all", "base", "vuln", "fixed", "latest"],
        default="all",
        help="Which image type(s) to build (default: all).",
    )
    parser.add_argument(
        "--instances",
        nargs="+",
        metavar="CVE",
        help="Specific CVE IDs to build. Default: all discovered instances.",
    )
    parser.add_argument(
        "-j", "--parallel",
        type=int,
        default=1,
        help="Number of parallel docker builds (default: 1).",
    )
    parser.add_argument(
        "--kbuild-jobs",
        type=int,
        default=None,
        help="KBUILD_JOBS passed to kernel builds.",
    )
    parser.add_argument(
        "--linux-ref",
        default=DEFAULT_LINUX_REF,
        help=f"Git ref for latest images (default: {DEFAULT_LINUX_REF}).",
    )
    parser.add_argument(
        "--platform",
        default="linux/amd64",
        help="Docker target platform (default: linux/amd64).",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Pass --no-cache to docker build.",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip images already present locally.",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push images after successful build.",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable the rich progress bar.",
    )
    args = parser.parse_args()

    if args.parallel < 1:
        parser.error("--parallel must be >= 1")
    if args.kbuild_jobs is not None and args.kbuild_jobs < 1:
        parser.error("--kbuild-jobs must be >= 1")

    if args.instances is not None:
        unknown = unknown_requested_instances(args.instances)
        if unknown:
            log(f"unknown requested instance(s): {', '.join(unknown)}")
            return 1
        instances = list(dict.fromkeys(args.instances))
    else:
        instances = discover_instances()
    if not instances:
        log("no instances found")
        return 1

    modes: list[str] = []
    if args.mode == "all":
        modes = ["base", "vuln", "fixed", "latest"]
    else:
        modes = [args.mode]

    log_dir = LINUX_DIR / "build_logs" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_dir.mkdir(parents=True, exist_ok=True)

    all_failed: dict[str, list[str]] = {}
    failed_vulnerable: set[str] = set()
    total_start = time.monotonic()

    progress = None if args.no_progress or not RICH_AVAILABLE else make_progress()
    if not args.no_progress and not RICH_AVAILABLE:
        log("rich is unavailable; continuing without the progress bar")

    def _run() -> None:
        log(f"instances: {len(instances)}", progress)
        log(f"modes: {', '.join(modes)}", progress)
        log(f"parallel: {args.parallel}", progress)
        log(f"platform: {args.platform}", progress)
        if args.kbuild_jobs is not None:
            log(f"kbuild jobs: {args.kbuild_jobs}", progress)
        log(f"logs: {log_dir}", progress)

        for mode in modes:
            if mode == "base":
                if not build_base(args, log_dir, progress):
                    all_failed["base"] = ["linux.base"]
                    if len(modes) > 1:
                        log("base failed; skipping dependent image builds", progress)
                        return
                if args.mode == "all":
                    has_pending_dependency = any(
                        mode_has_pending_base_dependency(
                            dependent_mode,
                            filter_instances(instances, dependent_mode),
                            skip_existing=args.skip_existing,
                        )
                        for dependent_mode in ("vuln", "fixed", "latest")
                    )
                    if has_pending_dependency and not ensure_compatible_linux_base(
                        args, log_dir, progress
                    ):
                        all_failed["base"] = ["linux.base"]
                        log(
                            "base compatibility check failed; skipping dependent "
                            "image builds",
                            progress,
                        )
                        return
                continue

            eligible = filter_instances(instances, mode)
            if mode == "fixed" and failed_vulnerable:
                blocked = [
                    cve
                    for cve in eligible
                    if cve in failed_vulnerable
                    and fixed_dockerfile_vulnerable_parent(cve) is not None
                ]
                if blocked:
                    log(
                        f"[fixed] skipping {len(blocked)} image(s) whose paired "
                        "vulnerable image failed to build",
                        progress,
                    )
                    blocked_set = set(blocked)
                    eligible = [cve for cve in eligible if cve not in blocked_set]
            if not eligible:
                log(f"[{mode}] no eligible instances, skipping", progress)
                continue

            # `all` already runs the established base phase first. Standalone
            # leaf modes need an equivalent guard when at least one selected
            # tag will be built. Fixed leaves require the base either directly
            # or through a verified paired vulnerable image.
            if args.mode not in {"all", "base"}:
                requires_base = mode_has_pending_base_dependency(
                    mode,
                    eligible,
                    skip_existing=args.skip_existing,
                )
                if requires_base and not ensure_compatible_linux_base(
                    args, log_dir, progress
                ):
                    all_failed["base"] = ["linux.base"]
                    log(
                        "base compatibility check failed; skipping dependent "
                        f"{mode} image builds",
                        progress,
                    )
                    return

            if mode == "fixed":
                parent_failures = repair_fixed_vulnerable_parents(
                    eligible, args, log_dir, progress
                )
                if parent_failures:
                    prior = all_failed.setdefault("vuln", [])
                    prior.extend(cve for cve in parent_failures if cve not in prior)
                    failed_set = set(parent_failures)
                    eligible = [cve for cve in eligible if cve not in failed_set]
                    if not eligible:
                        log(
                            "[fixed] no image has a verified current vulnerable parent",
                            progress,
                        )
                        continue

            log(f"[{mode}] building {len(eligible)} image(s)", progress)
            failed = build_instances_parallel(mode, eligible, args, log_dir, progress)
            if failed:
                all_failed[mode] = failed
                if mode == "vuln":
                    failed_vulnerable.update(failed)

            # Push successful images
            if args.push:
                repo = IMAGE_REPOS[mode]
                succeeded = [c for c in eligible if c not in failed]
                for cve in succeeded:
                    tag = f"{repo}:{cve}"
                    log(f"[{mode}] pushing {tag}", progress)
                    subprocess.run(
                        ["docker", "push", tag],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )

    if progress:
        with progress:
            _run()
    else:
        _run()

    total_elapsed = time.monotonic() - total_start
    log(f"done in {total_elapsed:.0f}s", progress)

    if all_failed:
        log("FAILURES:", progress)
        for mode, cves in all_failed.items():
            for cve in cves:
                log(f"  [{mode}] {cve}", progress)
        log(f"logs: {log_dir}", progress)
        return 1

    log("all builds succeeded", progress)
    return 0


if __name__ == "__main__":
    sys.exit(main())
