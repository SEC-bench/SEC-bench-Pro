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
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

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

REPO_ROOT = Path(__file__).resolve().parents[2]
LINUX_DIR = Path(__file__).resolve().parent
BASE_DIR = REPO_ROOT / "base" / "linux"

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
    dockerfile: Path | None = None,
    build_args: dict[str, str] | None = None,
    no_cache: bool = False,
    log_file: Path | None = None,
    skip_existing: bool = False,
    secrets: list[str] | None = None,
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

    cmd = ["docker", "build", "-t", tag]
    if dockerfile:
        cmd += ["-f", str(dockerfile)]
    if no_cache:
        cmd.append("--no-cache")
    for k, v in (build_args or {}).items():
        cmd += ["--build-arg", f"{k}={v}"]
    for s in secrets or []:
        cmd += ["--secret", s]
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
) -> bool:
    task_id = None
    if progress:
        task_id = progress.add_task("base image", total=1)

    log("building base image: hwiwonlee/linux.base:latest", progress)
    tag = f"{IMAGE_REPOS['base']}:latest"
    build_args = {}
    if args.kbuild_jobs:
        build_args["KBUILD_JOBS"] = str(args.kbuild_jobs)

    # Context is the repo root so the Dockerfile can COPY the vendored MCP
    # (mcps/linux) alongside base/linux/*. A repo-root .dockerignore keeps the
    # sent context lean. No gh token / secret needed anymore.
    log_file = log_dir / "base.log"
    tag, ok, elapsed = build_image(
        tag=tag,
        context=REPO_ROOT,
        dockerfile=BASE_DIR / "Dockerfile",
        build_args=build_args,
        no_cache=args.no_cache,
        log_file=log_file,
        skip_existing=args.skip_existing,
    )
    if progress and task_id is not None:
        progress.advance(task_id)

    if ok:
        log(f"base ok ({elapsed:.0f}s)", progress)
    else:
        log(f"base FAILED — see {log_file}", progress)
    return ok


def build_instances_parallel(
    mode: str,
    instances: list[str],
    args: argparse.Namespace,
    log_dir: Path,
    progress: Progress | None = None,
) -> list[str]:
    """Build vuln/fixed/latest images in parallel. Returns list of failed instance IDs."""
    repo = IMAGE_REPOS[mode]
    failed: list[str] = []
    task_id = None
    if progress:
        task_id = progress.add_task(f"{mode} images", total=len(instances))

    def _build_one(cve: str) -> tuple[str, bool, float, Path]:
        tag = f"{repo}:{cve}"
        cve_dir = LINUX_DIR / cve
        log_file = log_dir / f"{mode}_{cve}.log"

        build_args: dict[str, str] = {}
        if args.kbuild_jobs:
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
            dockerfile=dockerfile,
            build_args=build_args,
            no_cache=args.no_cache,
            log_file=log_file,
            skip_existing=args.skip_existing,
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
        default="origin/master",
        help="Git ref for latest images (default: origin/master).",
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

    instances = args.instances or discover_instances()
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
    total_start = time.monotonic()

    progress = None if args.no_progress else make_progress()

    def _run() -> None:
        log(f"instances: {len(instances)}", progress)
        log(f"modes: {', '.join(modes)}", progress)
        log(f"parallel: {args.parallel}", progress)
        if args.kbuild_jobs:
            log(f"kbuild jobs: {args.kbuild_jobs}", progress)
        log(f"logs: {log_dir}", progress)

        for mode in modes:
            if mode == "base":
                if not build_base(args, log_dir, progress):
                    all_failed["base"] = ["linux.base"]
                continue

            eligible = filter_instances(instances, mode)
            if not eligible:
                log(f"[{mode}] no eligible instances, skipping", progress)
                continue

            log(f"[{mode}] building {len(eligible)} image(s)", progress)
            failed = build_instances_parallel(mode, eligible, args, log_dir, progress)
            if failed:
                all_failed[mode] = failed

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
