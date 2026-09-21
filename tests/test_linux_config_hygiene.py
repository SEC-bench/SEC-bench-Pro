from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness"))

import common  # noqa: E402


class LinuxConfigHygieneTests(unittest.TestCase):
    def test_runtime_config_omits_build_only_kernel_config_paths(self) -> None:
        config = common.build_linux_secb_config(
            {
                "kernel": {
                    "build_commit": "deadbeef",
                    "defconfig_base": "x86_64_defconfig",
                    "kconfig_additions_file": "config/secret.additions",
                    "config_full_file": "config/secret.config",
                }
            }
        )

        kernel = config["kernel"]
        self.assertIsInstance(kernel, dict)
        self.assertEqual(kernel["build_commit"], "deadbeef")
        self.assertNotIn("kconfig_additions_file", kernel)
        self.assertNotIn("config_full_file", kernel)

    def test_evaluation_setup_removes_legacy_config_inputs(self) -> None:
        with (
            patch.object(common, "run_step") as run_step,
            patch.object(common, "_ensure_linux_process_tools"),
            patch.object(common, "_prepare_linux_secb_runtime"),
        ):
            common.setup_linux_evaluation_container(
                "container-id",
                secb_config_content=None,
            )

        commands = {
            call.args[0]: call.args[3]
            for call in run_step.call_args_list
        }
        command = commands["Sanitize Linux eval container"]
        self.assertIn("rm -rf /config", command)
        self.assertIn(".kernel.kconfig_additions_file", command)
        self.assertIn(".kernel.config_full_file", command)

    def test_all_leaf_builds_reuse_the_resolved_dot_config(self) -> None:
        scripts = sorted((ROOT / "projects" / "linux").glob("CVE-*/build.sh"))
        self.assertEqual(len(scripts), 137)

        for script in scripts:
            with self.subTest(script=script.parent.name):
                source = script.read_text(encoding="utf-8")
                reuse_guard = 'if [ -s "$KDIR/.config" ]; then'
                self.assertIn(reuse_guard, source)
                self.assertIn('log "reusing existing kernel .config"', source)
                self.assertIn("make olddefconfig", source)

                # Build-only inputs may initialize a fresh image, but cannot
                # replace the retained config during evaluator rebuilds.
                if 'make "$DEFCONFIG"' in source:
                    initializer_call = "        initialize_kernel_config\n"
                    self.assertLess(
                        source.index(reuse_guard),
                        source.index(initializer_call, source.index(reuse_guard)),
                    )
                if 'cp -f "$CONFIG_FULL" "$KDIR/.config"' in source:
                    self.assertLess(
                        source.index(reuse_guard),
                        source.index('cp -f "$CONFIG_FULL" "$KDIR/.config"'),
                    )

    def test_image_sanitizer_requires_dot_config_and_removes_build_inputs(self) -> None:
        source = (ROOT / "base" / "linux" / "sanitize-git").read_text(
            encoding="utf-8"
        )

        self.assertIn('if [ ! -s "$repo/.config" ]; then', source)
        self.assertIn('if [ ! -s "$verification_binary" ]; then', source)
        self.assertIn("verification binary not found", source)
        self.assertIn("rm -rf /config", source)
        self.assertIn("del(.kernel.kconfig_additions_file", source)
        self.assertIn(".kernel.config_full_file", source)

    def test_image_sanitizer_rejects_a_missing_verification_binary(self) -> None:
        sanitizer = ROOT / "base" / "linux" / "sanitize-git"
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            repo = temp / "linux"
            repo.mkdir()
            (repo / ".config").write_text("CONFIG_TEST=y\n", encoding="utf-8")
            config = temp / "config.json"
            missing = temp / "missing-bzImage"
            config.write_text(
                json.dumps({"verification_binary": str(missing)}) + "\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [str(sanitizer), str(repo)],
                capture_output=True,
                text=True,
                env={**os.environ, "SECB_CONFIG": str(config)},
                timeout=10,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("verification binary not found", result.stderr)

    def test_every_leaf_image_runs_the_sanitizer_after_config_copy(self) -> None:
        linux_dir = ROOT / "projects" / "linux"
        vulnerable = sorted(linux_dir.glob("CVE-*/Dockerfile"))
        fixed = sorted(linux_dir.glob("CVE-*/Dockerfile.fixed"))
        self.assertEqual(len(vulnerable), 137)
        self.assertEqual(len(fixed), 137)

        dockerfiles = [
            *vulnerable,
            *fixed,
            ROOT / "base" / "linux" / "Dockerfile.latest",
        ]
        sanitizer = "RUN secb-sanitize-git /src/linux"
        for dockerfile in dockerfiles:
            with self.subTest(dockerfile=dockerfile):
                source = dockerfile.read_text(encoding="utf-8")
                self.assertIn(sanitizer, source)
                if "COPY config/" in source:
                    self.assertLess(source.index("COPY config/"), source.rindex(sanitizer))


if __name__ == "__main__":
    unittest.main()
