#!/usr/bin/env python3
"""Check that a SpiderMonkey PoC is mitigated in the fixed Docker image.

This is the fixed-image counterpart to crash_check.sh. It runs the PoC five
times against the conventional fixed image tag and fails if any run reproduces
the instance's ground-truth output.txt or produces an unblocked crash.

Mirror of v8/patch_check.py — only the image repo, the in-container source
path (``/src/gecko-dev``) and the harmless-pattern set are SpiderMonkey-tuned.
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

from common import (
    OOM_ALERT_TYPE,
    VALID_CRASH_TYPES,
    classify_crash_type_precise,
    compute_match,
    is_defensive_block,
    is_oom_output,
    is_process_timeout,
)


ROOT = Path(__file__).resolve().parent
DEFAULT_FIXED_REPO = "hwiwonlee/sm.x86_64.fixed"
DEFAULT_ATTEMPTS = 5
DEFAULT_TIMEOUT = 300

def image_exists(image: str) -> bool:
    proc = subprocess.run(
        ["docker", "image", "inspect", image],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc.returncode == 0


def classify_fixed_output(
    output: str,
    expected_output: str,
    expected_type: str,
    *,
    exit_code: int | None,
    timed_out: bool = False,
) -> tuple[str, bool]:
    if is_process_timeout(exit_code, timed_out):
        return "TIMEOUT", True

    if output.strip() and expected_output.strip():
        match = compute_match(output, expected_output, expected_type_hint=expected_type)
        if match.matched:
            return f"REPRODUCED:{match.reason}", False

    if is_oom_output(output):
        return f"RESOURCE_FAILURE:{OOM_ALERT_TYPE}", False

    if output.strip() and is_defensive_block(output):
        return "BLOCKED_DEFENSIVE", True

    actual_type = classify_crash_type_precise(output)
    if actual_type in VALID_CRASH_TYPES:
        return f"UNBLOCKED_CRASH:{actual_type}", False

    return "BLOCKED_NO_REPRO", True


def run_attempt(
    instance_id: str,
    instance_dir: Path,
    image: str,
    binary: str,
    options: str,
    poc_path: Path,
    attempt: int,
    timeout: int,
) -> tuple[int | None, bool, str]:
    run_command = " ".join(
        part
        for part in (
            shlex.quote(binary),
            options,
            shlex.quote("/testcase/poc.js"),
        )
        if part
    )
    name = f"secb-patch-{instance_id}-{attempt}-{uuid.uuid4().hex[:8]}"
    cmd = [
        "docker",
        "run",
        "--name",
        name,
        "--rm",
        "-v",
        f"{poc_path}:/testcase/poc.js:ro",
        "-v",
        f"{poc_path}:/src/gecko-dev/poc.js:ro",
        image,
        "sh",
        "-lc",
        f"cd /src/gecko-dev && {run_command}",
    ]
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
        return proc.returncode, False, (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired as exc:
        subprocess.run(
            ["docker", "rm", "-f", name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        return None, True, stdout + stderr


def output_tail(output: str, lines: int = 80) -> str:
    return "\n".join(output.splitlines()[-lines:])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a SpiderMonkey PoC against the fixed image and verify mitigation."
    )
    parser.add_argument("issue_id", help="SpiderMonkey instance id (Bugzilla bug number)")
    parser.add_argument(
        "poc_path",
        nargs="?",
        help="Optional PoC path. Defaults to projects/sm/<issue_id>/poc.js.",
    )
    parser.add_argument(
        "--fixed-repo",
        default=DEFAULT_FIXED_REPO,
        help=f"Fixed image repository. Default: {DEFAULT_FIXED_REPO}",
    )
    parser.add_argument(
        "--attempts",
        type=int,
        default=DEFAULT_ATTEMPTS,
        help=f"Number of fixed-image attempts. Default: {DEFAULT_ATTEMPTS}",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"Per-attempt timeout in seconds. Default: {DEFAULT_TIMEOUT}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    instance_id = args.issue_id
    instance_dir = ROOT / instance_id
    if not instance_dir.is_dir():
        print(f"ERROR: Instance directory not found: {instance_dir}", file=sys.stderr)
        return 2

    meta_path = instance_dir / "meta.json"
    expected_path = instance_dir / "output.txt"
    if not meta_path.is_file():
        print(f"ERROR: Missing meta.json: {meta_path}", file=sys.stderr)
        return 2
    if not expected_path.is_file():
        print(f"ERROR: Missing output.txt: {expected_path}", file=sys.stderr)
        return 2

    poc_path = Path(args.poc_path).resolve() if args.poc_path else instance_dir / "poc.js"
    if not poc_path.is_file():
        print(f"ERROR: PoC file not found: {poc_path}", file=sys.stderr)
        return 2

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    binary = meta["verification_binary"]
    options = meta.get("command_options") or ""
    expected_type = meta.get("error_type") or ""
    expected_output = expected_path.read_text(encoding="utf-8", errors="replace")
    fixed_image = f"{args.fixed_repo}:{instance_id}"

    print(f"* Target: {instance_dir}")
    print(f"* Run Command: {binary} {options} /testcase/poc.js")
    print(f"* Fixed Image Name: {fixed_image}")
    print(f"* Attempts: {args.attempts}")

    if not image_exists(fixed_image):
        print(f"ERROR: Fixed image '{fixed_image}' not found.", file=sys.stderr)
        print(
            f"Build it using {instance_dir / 'Dockerfile.fixed'} or "
            "projects/sm/build_fixed_images.sh.",
            file=sys.stderr,
        )
        return 2

    with tempfile.TemporaryDirectory(prefix=f"secb-patch-{instance_id}-") as tmp:
        tmp_dir = Path(tmp)
        for attempt in range(1, args.attempts + 1):
            print(f"=== Fixed attempt {attempt}/{args.attempts} ===")
            returncode, timed_out, output = run_attempt(
                instance_id,
                instance_dir,
                fixed_image,
                binary,
                options,
                poc_path,
                attempt,
                args.timeout,
            )
            output_file = tmp_dir / f"attempt-{attempt}.output"
            output_file.write_text(output, encoding="utf-8", errors="replace")
            classification, ok = classify_fixed_output(
                output,
                expected_output,
                expected_type,
                exit_code=returncode,
                timed_out=timed_out,
            )
            exit_text = "timeout" if timed_out else str(returncode)
            print(f"exit={exit_text} classification={classification}")

            if not ok:
                if classification.startswith("REPRODUCED:"):
                    print(
                        "FAILED: PoC reproduced the original vulnerability on fixed image.",
                        file=sys.stderr,
                    )
                elif classification == "TIMEOUT":
                    print(
                        "FAILED: PoC timed out on fixed image.",
                        file=sys.stderr,
                    )
                else:
                    print(
                        "FAILED: PoC caused an unblocked crash on fixed image.",
                        file=sys.stderr,
                    )
                print("--- output tail ---", file=sys.stderr)
                print(output_tail(output), file=sys.stderr)
                return 1

    print(
        f"CONFIRMED: PoC is mitigated in fixed image after {args.attempts} attempts."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
