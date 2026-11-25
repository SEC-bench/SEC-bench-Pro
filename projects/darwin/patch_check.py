#!/usr/bin/env python3
"""patch_check.py - fixed-kernel oracle for darwin-bench.

Boot a task's custom-fixed image (the from-source kernel with the upstream fix
from patches/ applied on top of patches-pre/) run the PoC, and assert the crash
is gone. Exit contract mirrors SEC-bench-Pro's projects/linux/patch_check.py:

    0  the fix mitigates the PoC         (verdict NO_CRASH_DETECTED)
    1  the fixed kernel still crashes    (verdict CONFIRMED:<type>)
    2  harness error                     (no image, no variant, docker failure)

    projects/darwin/patch_check.py CVE-2026-28897
    projects/darwin/patch_check.py CVE-2026-28897 --build > output.custom-fixed.txt

crash_check.sh does the booting and classification; patch_check runs its
one-shot transcript and reads the verdict (its last verdict line). The fixed
image is produced by build_images.py --mode custom-fixed (pass --build to run it
first). The transcript goes to stdout (so `> output.custom-fixed.txt` works);
notes go to stderr.

The oracle only has signal where the paired custom-development (vulnerable) build
produces a CONFIRMED crash on the open-source kernel. For a bug caught only by a
toolchain feature the Linux build lacks (e.g. -fbounds-safety), both the vuln and
the fixed build read NO_CRASH, so a pass here is not evidence of mitigation.
"""
import argparse
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
CRASH_CHECK = HERE / "crash_check.sh"
BUILD_IMAGES = HERE / "build_images.py"


def die(msg):
    print("patch_check: error: " + msg, file=sys.stderr)
    raise SystemExit(2)


def image_exists(tag):
    return subprocess.run(["docker", "image", "inspect", tag],
                          stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL).returncode == 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("instance")
    ap.add_argument("--variant", default="custom-fixed",
                    help="the fixed variant to boot (default custom-fixed)")
    ap.add_argument("--build", action="store_true",
                    help="run build_images.py --mode <variant> --instances <instance> first")
    args = ap.parse_args()

    inst = args.instance
    d = HERE / inst
    if not (d / "meta.json").is_file():
        die(f"no task {inst} (missing {d / 'meta.json'})")
    meta = json.loads((d / "meta.json").read_text())
    if args.variant not in meta.get("variants", []):
        die(f"{inst} has no {args.variant} variant (variants: {', '.join(meta.get('variants', []))})")

    if args.build:
        print(f"patch_check: building {inst} {args.variant} ...", file=sys.stderr)
        if subprocess.run([sys.executable, str(BUILD_IMAGES),
                           "--mode", args.variant, "--instances", inst]).returncode != 0:
            die(f"build_images.py --mode {args.variant} failed")

    tag = f"darwin-bench/{inst.lower()}:{args.variant}"
    if not image_exists(tag):
        die(f"image {tag} not found; build it first: "
            f"projects/darwin/build_images.py --mode {args.variant} --instances {inst} (or pass --build)")

    # One-shot transcript via crash_check.sh; stdout = transcript + verdict line.
    proc = subprocess.run([str(CRASH_CHECK), inst, args.variant],
                          stdout=subprocess.PIPE, text=True)
    sys.stdout.write(proc.stdout)

    verdict = ""
    for line in proc.stdout.splitlines():
        line = line.strip()
        if line.startswith("CONFIRMED:") or line == "NO_CRASH_DETECTED":
            verdict = line
    if not verdict:
        die("no verdict line in the crash_check.sh transcript")

    if verdict == "NO_CRASH_DETECTED":
        print(f"patch_check: mitigated ({inst} {args.variant}: {verdict})", file=sys.stderr)
        return 0
    print(f"patch_check: NOT mitigated ({inst} {args.variant}: {verdict})", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
