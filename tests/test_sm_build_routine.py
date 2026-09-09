from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = ROOT / "projects" / "sm" / "build_images.sh"
FIXED_BUILD_SCRIPT = ROOT / "projects" / "sm" / "build_fixed_images.sh"


class SpiderMonkeyBuildRoutineTests(unittest.TestCase):
    def _run_build(
        self,
        *,
        base_state: str,
        force: bool = False,
        fixed: bool = False,
        fixed_tag_present: bool = False,
        skip_existing: bool = False,
        base_build_succeeds: bool = True,
        base_repairs: bool = True,
        expect_success: bool = True,
    ) -> list[str]:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            docker_log = temp / "docker.log"
            docker_log.touch()
            image_present = temp / "image-present"
            sanitizer_present = temp / "sanitizer-present"
            tooling_present = temp / "tooling-present"
            rust_version = temp / "rust-version"
            if base_state in {
                "sanitizer_missing",
                "rust_1_98",
                "old_tooling",
                "compatible",
            }:
                image_present.touch()
            if base_state in {"rust_1_98", "old_tooling", "compatible"}:
                sanitizer_present.touch()
            if base_state == "rust_1_98":
                rust_version.write_text("1.98.0\n")
            elif base_state in {"old_tooling", "compatible"}:
                rust_version.write_text("1.95.0\n")
            if base_state == "compatible":
                tooling_present.touch()

            docker = temp / "docker"
            docker.write_text(
                textwrap.dedent(
                    """\
                    #!/usr/bin/env bash
                    set -eu
                    printf '%s\\n' "$*" >> "$DOCKER_LOG"
                    if [[ "$1 $2" == "image inspect" ]]; then
                        if [[ "$*" == *"hwiwonlee/sm.x86_64.fixed:"* ]]; then
                            [[ "$FIXED_TAG_PRESENT" == "1" ]]
                        else
                            [[ -f "$IMAGE_PRESENT" ]]
                        fi
                        exit
                    fi
                    if [[ "$1" == "run" ]]; then
                        [[ -f "$SANITIZER_PRESENT" ]]
                        [[ "$(cat "$RUST_VERSION_FILE")" == "1.95.0" ]]
                        [[ -f "$TOOLING_PRESENT" ]]
                        exit
                    fi
                    if [[ "$1" == "build" && "$*" == *"hwiwonlee/sm.base:latest"* ]]; then
                        [[ "$BASE_BUILD_SUCCEEDS" == "1" ]] || exit 1
                        if [[ "$BASE_REPAIRS" == "1" ]]; then
                            touch "$IMAGE_PRESENT" "$SANITIZER_PRESENT" "$TOOLING_PRESENT"
                            printf '1.95.0\n' > "$RUST_VERSION_FILE"
                        fi
                    fi
                    exit 0
                    """
                )
            )
            docker.chmod(0o755)

            curl = temp / "curl"
            curl.write_text(
                textwrap.dedent(
                    """\
                    #!/usr/bin/env bash
                    set -eu
                    url="${@: -1}"
                    case "$url" in
                        *'@openai%2Fcodex/latest') printf '%s\n' '{"version":"9.8.7"}' ;;
                        *'opencode-ai/latest') printf '%s\n' '{"version":"8.7.6"}' ;;
                        *'claude-code-releases/latest') printf '%s\n' '7.6.5' ;;
                        *) exit 1 ;;
                    esac
                    """
                )
            )
            curl.chmod(0o755)

            build_script = BUILD_SCRIPT
            if fixed:
                sandbox_root = temp / "repo"
                sandbox_sm = sandbox_root / "projects" / "sm"
                sandbox_base = sandbox_root / "base"
                instance = sandbox_sm / "1880719"
                (instance / "patches").mkdir(parents=True)
                sandbox_base.mkdir(parents=True)
                build_script = sandbox_sm / "build_fixed_images.sh"
                shutil.copy2(FIXED_BUILD_SCRIPT, build_script)
                shutil.copy2(ROOT / "base" / "build_base_images.sh", sandbox_base)
                (instance / "Dockerfile.fixed").write_text(
                    "FROM hwiwonlee/sm.base:latest\n", encoding="utf-8"
                )
                (instance / "patches" / "0001-fix.patch").write_text(
                    "test patch\n", encoding="utf-8"
                )

            env = os.environ.copy()
            env.update(
                {
                    "PATH": f"{temp}:{env['PATH']}",
                    "DOCKER_LOG": str(docker_log),
                    "IMAGE_PRESENT": str(image_present),
                    "SANITIZER_PRESENT": str(sanitizer_present),
                    "TOOLING_PRESENT": str(tooling_present),
                    "RUST_VERSION_FILE": str(rust_version),
                    "BASE_BUILD_SUCCEEDS": "1" if base_build_succeeds else "0",
                    "BASE_REPAIRS": "1" if base_repairs else "0",
                    "FIXED_TAG_PRESENT": "1" if fixed_tag_present else "0",
                }
            )
            args = [str(build_script)]
            if force:
                args.append("-b")
            if skip_existing:
                args.append("--skip-existing")
            args.append("1880719")
            result = subprocess.run(
                args,
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if expect_success:
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            else:
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            return docker_log.read_text().splitlines()

    def test_missing_or_incompatible_base_is_built_before_leaf(self) -> None:
        for base_state in (
            "missing",
            "sanitizer_missing",
            "rust_1_98",
            "old_tooling",
        ):
            with self.subTest(base_state=base_state):
                calls = self._run_build(base_state=base_state)
                base_build = next(
                    index
                    for index, call in enumerate(calls)
                    if call.startswith("build -t hwiwonlee/sm.base:latest ")
                )
                leaf_build = next(
                    index
                    for index, call in enumerate(calls)
                    if call.startswith("build -t hwiwonlee/sm.x86_64:1880719 ")
                )
                self.assertLess(base_build, leaf_build)
                self.assertTrue(calls[base_build].endswith("/base/sm"))

    def test_compatible_base_is_reused_unless_rebuild_is_requested(self) -> None:
        reused_calls = self._run_build(base_state="compatible")
        self.assertFalse(
            any("hwiwonlee/sm.base:latest" in call for call in reused_calls if call.startswith("build "))
        )

        rebuilt_calls = self._run_build(base_state="compatible", force=True)
        base_call = next(
            call
            for call in rebuilt_calls
            if call.startswith("build -t hwiwonlee/sm.base:latest ")
        )
        self.assertIn("CODEX_VERSION=9.8.7", base_call)
        self.assertIn("OPENCODE_VERSION=8.7.6", base_call)
        self.assertIn("CLAUDE_CODE_VERSION=7.6.5", base_call)
        self.assertIn("AGENT_CACHE_BUST=", base_call)

    def test_fixed_builder_rebuilds_incompatible_base_before_leaf(self) -> None:
        for base_state in (
            "missing",
            "sanitizer_missing",
            "rust_1_98",
            "old_tooling",
        ):
            with self.subTest(base_state=base_state):
                calls = self._run_build(base_state=base_state, fixed=True)
                base_build = next(
                    index
                    for index, call in enumerate(calls)
                    if call.startswith("build -t hwiwonlee/sm.base:latest ")
                )
                leaf_build = next(
                    index
                    for index, call in enumerate(calls)
                    if "-t hwiwonlee/sm.x86_64.fixed:1880719 " in call
                )
                self.assertLess(base_build, leaf_build)

    def test_fixed_builder_reuses_compatible_base(self) -> None:
        reused_calls = self._run_build(base_state="compatible", fixed=True)
        self.assertFalse(
            any(
                "hwiwonlee/sm.base:latest" in call
                for call in reused_calls
                if call.startswith("build ")
            )
        )
        self.assertEqual(
            sum(
                "-t hwiwonlee/sm.x86_64.fixed:1880719 " in call
                for call in reused_calls
                if call.startswith("build ")
            ),
            1,
        )

    def test_fixed_builder_stops_when_canonical_base_remains_incompatible(self) -> None:
        cases = (
            {"base_build_succeeds": False},
            {"base_repairs": False},
        )
        for case in cases:
            with self.subTest(case=case):
                calls = self._run_build(
                    base_state="missing",
                    fixed=True,
                    expect_success=False,
                    **case,
                )
                self.assertTrue(
                    any(
                        call.startswith("build -t hwiwonlee/sm.base:latest ")
                        for call in calls
                    )
                )
                self.assertFalse(
                    any("hwiwonlee/sm.x86_64.fixed:" in call for call in calls)
                )

    def test_fixed_builder_skips_existing_leaf_without_requiring_base(self) -> None:
        calls = self._run_build(
            base_state="missing",
            fixed=True,
            fixed_tag_present=True,
            skip_existing=True,
        )
        self.assertFalse(any("hwiwonlee/sm.base:latest" in call for call in calls))
        self.assertFalse(
            any(
                "hwiwonlee/sm.x86_64.fixed:1880719" in call
                for call in calls
                if call.startswith("build ")
            )
        )

    def test_fixed_builder_requires_base_when_skip_existing_leaf_is_pending(self) -> None:
        calls = self._run_build(
            base_state="missing",
            fixed=True,
            fixed_tag_present=False,
            skip_existing=True,
        )
        base_build = next(
            index
            for index, call in enumerate(calls)
            if call.startswith("build -t hwiwonlee/sm.base:latest ")
        )
        leaf_build = next(
            index
            for index, call in enumerate(calls)
            if "-t hwiwonlee/sm.x86_64.fixed:1880719 " in call
        )
        self.assertLess(base_build, leaf_build)

    def test_compatibility_probe_covers_the_runtime_contract(self) -> None:
        normalized_probes = []
        for build_script in (BUILD_SCRIPT, FIXED_BUILD_SCRIPT):
            probe = build_script.read_text(encoding="utf-8")
            match = re.search(
                r"base_is_compatible\(\) \{\n(?P<body>.*?)\n\}",
                probe,
                re.DOTALL,
            )
            self.assertIsNotNone(match, str(build_script))
            normalized_probes.append(" ".join(match.group("body").split()))
            for expected in (
                "/usr/local/bin/secb-sanitize-git",
                "/etc/secb-agent-versions",
                "rustc 1[.]95[.]0",
                "cbindgen 0[.]28[.]0",
                "bwrap",
                "socat",
                "setpriv",
                "unshare",
                "gdb",
                "strace",
                "ltrace",
                "valgrind",
                "rg",
                "jq",
                "xxd",
                "codex",
                "opencode",
                "claude",
            ):
                self.assertIn(expected, probe, str(build_script))
        self.assertEqual(normalized_probes[0], normalized_probes[1])

    def test_canonical_base_pins_the_compatible_rust_toolchain(self) -> None:
        dockerfile = (ROOT / "base" / "sm" / "Dockerfile").read_text(
            encoding="utf-8"
        )
        self.assertIn("ARG RUST_VERSION=1.95.0", dockerfile)
        self.assertIn('--default-toolchain "${RUST_VERSION}"', dockerfile)
        self.assertNotIn("--default-toolchain stable", dockerfile)

    def test_all_fixed_leaves_depend_on_the_probed_canonical_base(self) -> None:
        dockerfiles = sorted((ROOT / "projects" / "sm").glob("*/Dockerfile.fixed"))
        self.assertEqual(len(dockerfiles), 104)
        for dockerfile in dockerfiles:
            first_from = next(
                line for line in dockerfile.read_text(encoding="utf-8").splitlines()
                if line.startswith("FROM ")
            )
            self.assertEqual(first_from, "FROM hwiwonlee/sm.base:latest", str(dockerfile))


if __name__ == "__main__":
    unittest.main()
