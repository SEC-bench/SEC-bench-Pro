#!/usr/bin/env python3
"""Check that a Linux CVE's PoC is mitigated in the fixed Docker image.

Fixed-image counterpart to ``crash_check.sh``.  Runs ``secb repro`` against the
conventional fixed image tag (``hwiwonlee/linux.x86_64.fixed:<CVE>``) up to
``--attempts`` times.  For newer audit-style images that carry
``/run/secb/config.json`` instead of a baked ``/poc`` tree, each attempt starts
a temporary container, copies the host-side PoC bundle into ``/src/linux/audit``,
runs ``secb build``, then runs ``secb repro``.  Each attempt's serial log is
re-classified host-side using the same KASAN/KFENCE/UBSAN/PANIC ladder that
``crash_check.sh`` uses; the in-container ``secb.sh`` verdict line is
intentionally ignored so the oracle stays decoupled from any per-leaf drift.

A run passes only when every attempt classifies as ``NO_CRASH_DETECTED``.  If
any attempt produces a verdict, the script fails with one of:

  * ``REPRODUCED:<TYPE>``    - matches ``meta.error_type`` (patch regression
                                on the intended bug).
  * ``UNBLOCKED_CRASH:<TYPE>`` - matches some *other* KASAN/KFENCE/UBSAN/PANIC
                                bucket (unrelated kernel crash on the fixed
                                kernel — also a fail).

The checker is deliberately self-contained because Linux verdicts are a
single regex match over the kernel serial log.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_FIXED_REPO = "hwiwonlee/linux.x86_64.fixed"
DEFAULT_ATTEMPTS = 3
DEFAULT_TIMEOUT = 600  # kernel boot + repro upper bound (cf. meta.qemu.timeout_repro_sec)


# Host-side verdict ladder.  Order matters — first regex to match wins, exactly
# as in linux/crash_check.sh and linux/CVE-*/secb.sh.  Plain WARNINGs are
# deliberately not in the ladder (sanity WARN_ONs added by fix patches would
# otherwise be mis-classified as regressions on the fixed kernel).
TS = r"\[ *[0-9.]+\]"
VERDICT_LADDER: list[tuple[str, re.Pattern[str]]] = [
    ("KASAN_UAF",          re.compile(rf"{TS} BUG: KASAN: (slab-)?use-after-free")),
    ("KASAN_OOB",          re.compile(rf"{TS} BUG: KASAN: slab-out-of-bounds")),
    ("KASAN_OOB",          re.compile(rf"{TS} BUG: KASAN: (global|stack|vmalloc)-out-of-bounds")),
    ("KASAN_DOUBLE_FREE",  re.compile(rf"{TS} BUG: KASAN: double-free")),
    ("KASAN_INVALID_FREE", re.compile(rf"{TS} BUG: KASAN: invalid-free")),
    ("KASAN_NULL_DEREF",   re.compile(rf"{TS} BUG: KASAN: null-ptr-deref")),
    ("KASAN_GPF",          re.compile(rf"{TS} general protection fault.*KASAN")),
    ("KFENCE",             re.compile(rf"{TS} KFENCE: ")),
    ("UBSAN",              re.compile(rf"{TS} UBSAN: ")),
]
PANIC_RE = re.compile(rf"{TS} Kernel panic - not syncing")
PANIC_ON_WARN_RE = re.compile(r"panic_on_warn set")


def classify_serial_log(output: str, selfcheck_regex: str | None) -> str | None:
    """Return one of the verdict strings, or ``None`` for no crash."""
    for verdict, pattern in VERDICT_LADDER:
        if pattern.search(output):
            return verdict
    if PANIC_RE.search(output) and not PANIC_ON_WARN_RE.search(output):
        return "PANIC"
    if selfcheck_regex:
        try:
            if re.search(selfcheck_regex, output):
                return "POC_SELFCHECK"
        except re.error:
            pass
    return None


def classify_fixed_output(output: str, expected_type: str, selfcheck_regex: str | None) -> tuple[str, bool]:
    """Return ``(classification, ok)``. ``ok`` is True when the fixed kernel
    blocked the PoC (i.e. NO_CRASH_DETECTED)."""
    actual = classify_serial_log(output, selfcheck_regex)
    if actual is None:
        return "NO_CRASH_DETECTED", True
    if expected_type and actual == expected_type:
        return f"REPRODUCED:{actual}", False
    return f"UNBLOCKED_CRASH:{actual}", False


def image_exists(image: str) -> bool:
    proc = subprocess.run(
        ["docker", "image", "inspect", image],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc.returncode == 0


def image_uses_runtime_config(image: str) -> bool:
    proc = subprocess.run(
        ["docker", "run", "--rm", image, "sh", "-c", "test -r /run/secb/config.json"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc.returncode == 0


def prepare_poc_bundle(instance_dir: Path, tmp_dir: Path) -> Path:
    audit_dir = tmp_dir / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)

    poc_dir = instance_dir / "poc"
    if poc_dir.is_dir():
        for item in poc_dir.iterdir():
            dest = audit_dir / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)

    for support_name in ("poc.sh", "compile.sh"):
        src = instance_dir / support_name
        dest = audit_dir / support_name
        if src.is_file() and not dest.exists():
            shutil.copy2(src, dest)

    if not any(audit_dir.iterdir()):
        raise FileNotFoundError(
            f"no PoC files found under {poc_dir} or root support files"
        )
    return audit_dir


def docker_capture(
    cmd: list[str],
    timeout: int | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)


def timeout_output(exc: subprocess.TimeoutExpired) -> str:
    stdout = exc.stdout if isinstance(exc.stdout, str) else ""
    stderr = exc.stderr if isinstance(exc.stderr, str) else ""
    return stdout + stderr


def run_direct_attempt(
    instance_id: str,
    image: str,
    attempt: int,
    timeout: int,
) -> tuple[int | None, bool, str, bool]:
    name = f"secb-patch-{instance_id}-{attempt}-{uuid.uuid4().hex[:8]}"
    cmd = [
        "docker",
        "run",
        "--name",
        name,
        "--rm",
        "--privileged",
        image,
        "/usr/local/bin/secb",
        "repro",
    ]
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
        return proc.returncode, False, (proc.stdout or "") + (proc.stderr or ""), False
    except subprocess.TimeoutExpired as exc:
        subprocess.run(
            ["docker", "rm", "-f", name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return None, True, timeout_output(exc), False


def run_audit_attempt(
    instance_id: str,
    image: str,
    poc_bundle: Path,
    attempt: int,
    timeout: int,
) -> tuple[int | None, bool, str, bool]:
    name = f"secb-patch-{instance_id}-{attempt}-{uuid.uuid4().hex[:8]}"
    try:
        start = docker_capture(
            [
                "docker",
                "run",
                "--detach",
                "--name",
                name,
                "--privileged",
                image,
                "bash",
                "-lc",
                "sleep infinity",
            ],
            timeout=60,
        )
        if start.returncode != 0:
            output = (start.stdout or "") + (start.stderr or "")
            return start.returncode, False, output, True

        prep = docker_capture(
            [
                "docker",
                "exec",
                name,
                "bash",
                "-lc",
                "mkdir -p /src/linux/audit /out /tmp/secb && chmod 1777 /out /tmp/secb",
            ],
            timeout=60,
        )
        if prep.returncode != 0:
            output = (prep.stdout or "") + (prep.stderr or "")
            return prep.returncode, False, output, True

        cp_proc = docker_capture(
            ["docker", "cp", f"{poc_bundle}/.", f"{name}:/src/linux/audit/"],
            timeout=60,
        )
        if cp_proc.returncode != 0:
            output = (cp_proc.stdout or "") + (cp_proc.stderr or "")
            return cp_proc.returncode, False, output, True

        try:
            build = docker_capture(
                [
                    "docker",
                    "exec",
                    name,
                    "bash",
                    "-lc",
                    "cd /src/linux && rm -rf /tmp/secb/poc /out/initramfs.cpio.gz && /usr/local/bin/secb build",
                ],
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            return None, True, timeout_output(exc), True

        build_output = (build.stdout or "") + (build.stderr or "")
        if build.returncode != 0:
            return build.returncode, False, build_output, True

        try:
            repro = docker_capture(
                ["docker", "exec", name, "bash", "-lc", "/usr/local/bin/secb repro"],
                timeout=timeout,
            )
            output = build_output + (repro.stdout or "") + (repro.stderr or "")
            return repro.returncode, False, output, False
        except subprocess.TimeoutExpired as exc:
            return None, True, build_output + timeout_output(exc), False
    finally:
        subprocess.run(
            ["docker", "rm", "-f", name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def output_tail(output: str, lines: int = 80) -> str:
    return "\n".join(output.splitlines()[-lines:])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a Linux CVE PoC against the fixed image and verify mitigation."
    )
    parser.add_argument("issue_id", help="Linux instance id (CVE-YYYY-NNNNN)")
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
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)

    args = build_parser().parse_args(argv)
    instance_id = args.issue_id
    instance_dir = ROOT / instance_id
    if not instance_dir.is_dir():
        print(f"ERROR: Instance directory not found: {instance_dir}", file=sys.stderr)
        return 2

    meta_path = instance_dir / "meta.json"
    if not meta_path.is_file():
        print(f"ERROR: Missing meta.json: {meta_path}", file=sys.stderr)
        return 2

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    expected_type = meta.get("error_type") or ""
    selfcheck_regex = (
        (meta.get("verdict") or {}).get("selfcheck_regex")
        if isinstance(meta.get("verdict"), dict)
        else None
    )
    fixed_image = f"{args.fixed_repo}:{instance_id}"

    print(f"* Target: {instance_dir}")
    print(f"* Run Command: secb repro (expected mitigation; expected error_type={expected_type or 'unset'})")
    print(f"* Fixed Image Name: {fixed_image}")
    print(f"* Attempts: {args.attempts}")

    if not image_exists(fixed_image):
        print(f"ERROR: Fixed image '{fixed_image}' not found.", file=sys.stderr)
        print(
            f"Build it using {instance_dir / 'Dockerfile.fixed'} or linux/build_fixed_images.sh.",
            file=sys.stderr,
        )
        return 2

    use_audit_poc = image_uses_runtime_config(fixed_image)
    if use_audit_poc:
        print("* PoC mode: host audit bundle copied to /src/linux/audit before repro")
    else:
        print("* PoC mode: image-baked rootfs")

    with tempfile.TemporaryDirectory(prefix=f"secb-patch-{instance_id}-") as tmp:
        tmp_dir = Path(tmp)
        poc_bundle = None
        if use_audit_poc:
            try:
                poc_bundle = prepare_poc_bundle(instance_dir, tmp_dir)
            except FileNotFoundError as exc:
                print(f"ERROR: {exc}", file=sys.stderr)
                return 2

        for attempt in range(1, args.attempts + 1):
            print(f"=== Fixed attempt {attempt}/{args.attempts} ===")
            if use_audit_poc:
                assert poc_bundle is not None
                returncode, timed_out, output, harness_error = run_audit_attempt(
                    instance_id, fixed_image, poc_bundle, attempt, args.timeout
                )
            else:
                returncode, timed_out, output, harness_error = run_direct_attempt(
                    instance_id, fixed_image, attempt, args.timeout
                )
            output_file = tmp_dir / f"attempt-{attempt}.output"
            output_file.write_text(output, encoding="utf-8", errors="replace")
            if harness_error:
                exit_text = "timeout" if timed_out else str(returncode)
                print(f"exit={exit_text} classification=HARNESS_ERROR")
                print("--- output tail ---", file=sys.stderr)
                print(output_tail(output), file=sys.stderr)
                return 2

            classification, ok = classify_fixed_output(
                output, expected_type, selfcheck_regex
            )
            exit_text = "timeout" if timed_out else str(returncode)
            print(f"exit={exit_text} classification={classification}")

            if not ok:
                if classification.startswith("REPRODUCED:"):
                    print(
                        "FAILED: PoC reproduced the original vulnerability on fixed image.",
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
