from __future__ import annotations

import os
import subprocess
import sys
import textwrap
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness"))

import common  # noqa: E402


class ActiveContainerRegistryTests(unittest.TestCase):
    def test_registry_api_tracks_container_lifecycle(self) -> None:
        name = f"registry-test-{uuid.uuid4().hex}"
        self.addCleanup(common.unregister_active_container, name)

        self.assertFalse(common.is_active_container(name))
        common.register_active_container(name)
        self.assertTrue(common.is_active_container(name))
        common.unregister_active_container(name)
        self.assertFalse(common.is_active_container(name))

    def test_sigint_cleanup_can_reenter_registry_lock(self) -> None:
        """A signal during a registry operation must not deadlock cleanup."""
        script = textwrap.dedent(
            """
            import signal
            import subprocess
            from unittest.mock import patch

            import common

            name = "signal-reentry-test"
            common.INTERRUPTED = False
            common.register_active_container(name)
            removed = subprocess.CompletedProcess(
                ["docker", "rm", "-f", "-v", name], 0, "", ""
            )
            common._active_containers_lock.acquire()
            try:
                with patch.object(common.subprocess, "run", return_value=removed):
                    common._on_sigint(signal.SIGINT, None)
            finally:
                common._active_containers_lock.release()
            if common.is_active_container(name):
                raise SystemExit("signal cleanup left the container registered")
            """
        )
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "harness")
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            timeout=5,
            env=env,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_confirmed_removal_and_already_absent_unregister(self) -> None:
        cases = (
            (
                subprocess.CompletedProcess(
                    ["docker", "rm", "-f", "container"], 0, "container\n", ""
                ),
                "Container removed.",
            ),
            (
                subprocess.CompletedProcess(
                    ["docker", "rm", "-f", "container"],
                    1,
                    "",
                    "Error response from daemon: No such container: container\n",
                ),
                "Container already absent.",
            ),
        )
        for result, final_message in cases:
            with self.subTest(final_message=final_message):
                name = f"removal-success-{uuid.uuid4().hex}"
                common.register_active_container(name)
                self.addCleanup(common.unregister_active_container, name)
                infos: list[str] = []
                warnings: list[str] = []

                with patch.object(common.subprocess, "run", return_value=result):
                    removed = common.remove_registered_container(
                        name, info_fn=infos.append, warn_fn=warnings.append
                    )

                self.assertTrue(removed)
                self.assertFalse(common.is_active_container(name))
                self.assertEqual(infos[-1], final_message)
                self.assertEqual(warnings, [])

    def test_failed_removal_stays_registered_for_exit_cleanup(self) -> None:
        failures = (
            subprocess.CompletedProcess(
                ["docker", "rm", "-f", "container"],
                7,
                "",
                "daemon unavailable\n",
            ),
            subprocess.TimeoutExpired(["docker", "rm", "-f", "container"], 30),
            OSError("docker executable unavailable"),
        )
        for failure in failures:
            with self.subTest(failure=type(failure).__name__):
                name = f"removal-failure-{uuid.uuid4().hex}"
                common.register_active_container(name)
                self.addCleanup(common.unregister_active_container, name)
                infos: list[str] = []
                warnings: list[str] = []

                kwargs = (
                    {"return_value": failure}
                    if isinstance(failure, subprocess.CompletedProcess)
                    else {"side_effect": failure}
                )
                with patch.object(common.subprocess, "run", **kwargs):
                    removed = common.remove_registered_container(
                        name, info_fn=infos.append, warn_fn=warnings.append
                    )

                self.assertFalse(removed)
                self.assertTrue(common.is_active_container(name))
                self.assertEqual(infos, [f"Removing container: {name}"])
                self.assertEqual(len(warnings), 1)
                self.assertIn("remains registered for exit cleanup", warnings[0])
                self.assertNotIn("Container removed.", infos)

    def test_all_evaluators_use_the_shared_removal_helper(self) -> None:
        for filename in ("eval_codex.py", "eval_claude.py", "eval_opencode.py"):
            with self.subTest(filename=filename):
                source = (ROOT / "harness" / filename).read_text(encoding="utf-8")
                self.assertIn("common.remove_registered_container(", source)
                self.assertNotIn("common._active_containers", source)


if __name__ == "__main__":
    unittest.main()
