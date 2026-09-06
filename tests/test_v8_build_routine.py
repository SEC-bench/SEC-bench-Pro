from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VULN_BUILD_SCRIPT = ROOT / "projects" / "v8" / "build_images.sh"
FIXED_BUILD_SCRIPT = ROOT / "projects" / "v8" / "build_fixed_images.sh"
BASE_HELPER = ROOT / "projects" / "v8" / "base_compat.sh"


class V8BuildRoutineTests(unittest.TestCase):
    def _fake_environment(
        self,
        temp: Path,
        *,
        base_state: str,
        leaf_present: bool = False,
        vulnerable_state: str = "missing",
        rebuild_compatible: bool = True,
    ) -> tuple[dict[str, str], Path]:
        docker_log = temp / "docker.log"
        base_present = temp / "base-present"
        compatible = temp / "base-compatible"
        leaf_marker = temp / "leaf-present"
        vulnerable_present = temp / "vulnerable-present"
        vulnerable_marker = temp / "vulnerable-marker"
        vulnerable_lineage = temp / "vulnerable-lineage"
        if base_state in {"incompatible", "compatible"}:
            base_present.touch()
        if base_state == "compatible":
            compatible.touch()
        if leaf_present:
            leaf_marker.touch()
        if vulnerable_state in {"stale", "current", "marker-only", "lineage-only"}:
            vulnerable_present.touch()
        if vulnerable_state in {"current", "marker-only"}:
            vulnerable_marker.touch()
        if vulnerable_state in {"current", "lineage-only"}:
            vulnerable_lineage.touch()

        docker = temp / "docker"
        docker.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env bash
                set -eu
                printf '%s\n' "$*" >> "$DOCKER_LOG"
                if [[ "$1 $2" == "image inspect" ]]; then
                    tag="${@: -1}"
                    case "$tag" in
                        hwiwonlee/v8.base:latest) [[ -f "$BASE_PRESENT" ]] ;;
                        hwiwonlee/v8.x86_64.fixed:*) [[ -f "$LEAF_PRESENT" ]] ;;
                        hwiwonlee/v8.x86_64:*) [[ -f "$VULNERABLE_PRESENT" ]] ;;
                        *) exit 1 ;;
                    esac
                    if [[ "${3:-}" == "--format" ]]; then
                        case "${4:-}" in
                            '{{.Id}}')
                                printf 'sha256:%064d\n' 0
                                ;;
                            *Config.Labels*)
                                if [[ "$tag" == hwiwonlee/v8.x86_64:* ]] && \
                                    [[ -f "$VULNERABLE_MARKER" ]]; then
                                    printf 'sha256:%064d\n' 0
                                else
                                    printf '<no value>\n'
                                fi
                                ;;
                            *RootFS.Layers*)
                                if [[ "$tag" == "hwiwonlee/v8.base:latest" ]]; then
                                    printf '%s\n' '["sha256:base"]'
                                elif [[ -f "$VULNERABLE_LINEAGE" ]]; then
                                    printf '%s\n' '["sha256:base","sha256:leaf"]'
                                else
                                    printf '%s\n' '["sha256:old-base","sha256:leaf"]'
                                fi
                                ;;
                        esac
                    fi
                    exit
                fi
                if [[ "$1" == "run" ]]; then
                    [[ -f "$BASE_COMPATIBLE" ]]
                    exit
                fi
                if [[ "$1" == "build" && "$*" == *"hwiwonlee/v8.base:latest"* ]]; then
                    touch "$BASE_PRESENT"
                    if [[ "$MAKE_COMPATIBLE" == "1" ]]; then
                        touch "$BASE_COMPATIBLE"
                    fi
                elif [[ "$1" == "build" && "$*" == *"hwiwonlee/v8.x86_64:"* ]]; then
                    touch "$VULNERABLE_PRESENT" "$VULNERABLE_MARKER" "$VULNERABLE_LINEAGE"
                elif [[ "$1" == "build" && "$*" == *"hwiwonlee/v8.x86_64.fixed:"* ]]; then
                    touch "$LEAF_PRESENT"
                fi
                exit 0
                """
            ),
            encoding="utf-8",
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
            ),
            encoding="utf-8",
        )
        curl.chmod(0o755)

        env = os.environ.copy()
        env.update(
            {
                "PATH": f"{temp}:{env['PATH']}",
                "DOCKER_LOG": str(docker_log),
                "BASE_PRESENT": str(base_present),
                "BASE_COMPATIBLE": str(compatible),
                "LEAF_PRESENT": str(leaf_marker),
                "VULNERABLE_PRESENT": str(vulnerable_present),
                "VULNERABLE_MARKER": str(vulnerable_marker),
                "VULNERABLE_LINEAGE": str(vulnerable_lineage),
                "MAKE_COMPATIBLE": "1" if rebuild_compatible else "0",
            }
        )
        return env, docker_log

    def _run_vulnerable(
        self,
        *,
        base_state: str,
        force: bool = False,
        rebuild_compatible: bool = True,
        selected_id: str = "350292240",
    ) -> tuple[subprocess.CompletedProcess[str], list[str]]:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            env, docker_log = self._fake_environment(
                temp,
                base_state=base_state,
                rebuild_compatible=rebuild_compatible,
            )
            selection = temp / "instances.txt"
            selection.write_text(f"{selected_id}\n", encoding="utf-8")
            args = [str(VULN_BUILD_SCRIPT)]
            if force:
                args.append("--rebuild-base")
            args.extend(["-f", str(selection)])
            result = subprocess.run(
                args,
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=15,
            )
            calls = docker_log.read_text().splitlines() if docker_log.exists() else []
            return result, calls

    def _temporary_fixed_tree(self, temp: Path, *, direct_base: bool) -> Path:
        project_dir = temp / "repo" / "projects" / "v8"
        base_dir = temp / "repo" / "base" / "v8"
        instance_dir = project_dir / "example"
        (instance_dir / "patches").mkdir(parents=True)
        base_dir.mkdir(parents=True)
        shutil.copy2(FIXED_BUILD_SCRIPT, project_dir / "build_fixed_images.sh")
        shutil.copy2(VULN_BUILD_SCRIPT, project_dir / "build_images.sh")
        shutil.copy2(BASE_HELPER, project_dir / "base_compat.sh")
        shutil.copy2(ROOT / "base" / "build_base_images.sh", temp / "repo" / "base" / "build_base_images.sh")
        shutil.copy2(ROOT / "base" / "v8" / "gclient-wrapper", base_dir / "gclient-wrapper")
        (instance_dir / "patches" / "0001-fix.patch").write_text(
            "non-empty patch fixture\n", encoding="utf-8"
        )
        parent = (
            "hwiwonlee/v8.base:latest"
            if direct_base
            else "hwiwonlee/v8.x86_64:example"
        )
        (instance_dir / "Dockerfile.fixed").write_text(
            f"FROM {parent}\nRUN true\n", encoding="utf-8"
        )
        (instance_dir / "Dockerfile").write_text(
            "FROM hwiwonlee/v8.base:latest\nRUN true\n", encoding="utf-8"
        )
        return project_dir / "build_fixed_images.sh"

    def _run_fixed(
        self,
        *,
        base_state: str,
        direct_base: bool,
        force: bool = False,
        skip_existing: bool = False,
        vulnerable_state: str = "missing",
    ) -> tuple[subprocess.CompletedProcess[str], list[str]]:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            script = self._temporary_fixed_tree(temp, direct_base=direct_base)
            env, docker_log = self._fake_environment(
                temp,
                base_state=base_state,
                leaf_present=skip_existing,
                vulnerable_state=vulnerable_state,
            )
            args = [str(script)]
            if force:
                args.append("-b")
            if skip_existing:
                args.append("--skip-existing")
            args.append("example")
            result = subprocess.run(
                args,
                cwd=temp / "repo",
                env=env,
                capture_output=True,
                text=True,
                timeout=15,
            )
            calls = docker_log.read_text().splitlines() if docker_log.exists() else []
            return result, calls

    def test_vulnerable_builder_rebuilds_missing_or_incompatible_base_first(self) -> None:
        for base_state in ("missing", "incompatible"):
            with self.subTest(base_state=base_state):
                result, calls = self._run_vulnerable(base_state=base_state)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                base_build = next(
                    index
                    for index, call in enumerate(calls)
                    if call.startswith("build -t hwiwonlee/v8.base:latest ")
                )
                leaf_build = next(
                    index
                    for index, call in enumerate(calls)
                    if call.startswith("build -t hwiwonlee/v8.x86_64:350292240 ")
                )
                self.assertLess(base_build, leaf_build)
                self.assertTrue(calls[base_build].endswith("/base/v8"))

    def test_vulnerable_builder_reuses_compatible_base_unless_forced(self) -> None:
        result, calls = self._run_vulnerable(base_state="compatible")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(
            any(
                call.startswith("build -t hwiwonlee/v8.base:latest ")
                for call in calls
            )
        )

        result, calls = self._run_vulnerable(
            base_state="compatible", force=True
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        base_call = next(
            call
            for call in calls
            if call.startswith("build -t hwiwonlee/v8.base:latest ")
        )
        self.assertIn("CODEX_VERSION=9.8.7", base_call)
        self.assertIn("OPENCODE_VERSION=8.7.6", base_call)
        self.assertIn("CLAUDE_CODE_VERSION=7.6.5", base_call)
        self.assertIn("AGENT_CACHE_BUST=", base_call)

    def test_builder_stops_if_rebuilt_base_still_fails_the_contract(self) -> None:
        result, calls = self._run_vulnerable(
            base_state="incompatible", rebuild_compatible=False
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("failed to build a compatible", result.stderr)
        self.assertFalse(
            any("hwiwonlee/v8.x86_64:350292240" in call for call in calls)
        )

    def test_vulnerable_builder_rejects_an_unknown_requested_id(self) -> None:
        result, calls = self._run_vulnerable(
            base_state="compatible", selected_id="not-a-real-instance"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requested instance directory not found", result.stderr)
        self.assertEqual(calls, [])

    def test_fixed_builder_rebuilds_base_before_direct_base_leaf(self) -> None:
        result, calls = self._run_fixed(
            base_state="incompatible", direct_base=True
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        base_build = next(
            index
            for index, call in enumerate(calls)
            if call.startswith("build -t hwiwonlee/v8.base:latest ")
        )
        leaf_build = next(
            index
            for index, call in enumerate(calls)
            if "build -f " in call and "v8.x86_64.fixed:example" in call
        )
        self.assertLess(base_build, leaf_build)

    def test_fixed_builder_repairs_stale_or_missing_vulnerable_parent(self) -> None:
        for state in ("missing", "stale", "marker-only", "lineage-only"):
            with self.subTest(state=state):
                result, calls = self._run_fixed(
                    base_state="compatible",
                    direct_base=False,
                    vulnerable_state=state,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                parent_build = next(
                    index
                    for index, call in enumerate(calls)
                    if call.startswith("build -t hwiwonlee/v8.x86_64:example ")
                )
                fixed_build = next(
                    index
                    for index, call in enumerate(calls)
                    if "v8.x86_64.fixed:example" in call
                )
                self.assertLess(parent_build, fixed_build)
                self.assertIn("org.secbench.base-image-id=sha256:", calls[parent_build])

    def test_fixed_builder_reuses_current_vulnerable_parent(self) -> None:
        result, calls = self._run_fixed(
            base_state="compatible",
            direct_base=False,
            vulnerable_state="current",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(
            any(
                call.startswith("build -t hwiwonlee/v8.x86_64:example ")
                for call in calls
            )
        )

        result, calls = self._run_fixed(
            base_state="missing", direct_base=True, skip_existing=True
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(
            any(
                call.startswith("build -t hwiwonlee/v8.base:latest ")
                for call in calls
            )
        )

    def test_fixed_builder_discovers_all_tracked_fixed_definitions(self) -> None:
        definitions = sorted((ROOT / "projects" / "v8").glob("*/Dockerfile.fixed"))
        self.assertEqual(len(definitions), 103)
        for definition in definitions:
            patches = list((definition.parent / "patches").glob("*.patch"))
            self.assertTrue(patches, definition.parent.name)
            self.assertTrue(
                any(patch.stat().st_size > 0 for patch in patches),
                definition.parent.name,
            )
        direct_base_definitions = [
            path
            for path in definitions
            if any(
                line.strip() == "FROM hwiwonlee/v8.base:latest"
                for line in path.read_text(encoding="utf-8").splitlines()
            )
        ]
        self.assertEqual(len(direct_base_definitions), 14)
        for path in direct_base_definitions:
            self.assertIn("gclient sync", path.read_text(encoding="utf-8"))
        source = FIXED_BUILD_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("-name Dockerfile.fixed", source)
        self.assertNotIn("missing fix.json", source)
        self.assertNotIn("-name fix.json", source)

    def test_compatibility_probe_covers_bounded_gclient_and_runtime(self) -> None:
        probe = BASE_HELPER.read_text(encoding="utf-8")
        for expected in (
            "/etc/secb-agent-versions",
            "/opt/depot_tools/gclient.unbounded",
            "sha256sum /opt/depot_tools/gclient",
            "GCLIENT_JOBS",
            "GCLIENT_SYNC_TIMEOUT_SEC",
            "python3",
            "timeout",
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
            self.assertIn(expected, probe)


if __name__ == "__main__":
    unittest.main()
