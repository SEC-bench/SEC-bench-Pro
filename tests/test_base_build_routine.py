from __future__ import annotations

import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = ROOT / "base" / "build_base_images.sh"


class BaseBuildRoutineTests(unittest.TestCase):
    def _run(
        self,
        *targets: str,
        codex_version: str = "9.8.7",
        opencode_version: str = "8.7.6",
        claude_version: str = "7.6.5",
        cache_bust: str | None = "shared-test-key",
    ) -> tuple[subprocess.CompletedProcess[str], list[str], list[str]]:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            docker_log = temp / "docker.log"
            curl_log = temp / "curl.log"

            docker = temp / "docker"
            docker.write_text(
                textwrap.dedent(
                    """\
                    #!/usr/bin/env bash
                    set -eu
                    printf '%s\n' "$*" >> "$DOCKER_LOG"
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
                    printf '%s\n' "$url" >> "$CURL_LOG"
                    case "$url" in
                        *'@openai%2Fcodex/latest')
                            printf '{"version":"%s"}\n' "$FAKE_CODEX_VERSION"
                            ;;
                        *'opencode-ai/latest')
                            printf '{"version":"%s"}\n' "$FAKE_OPENCODE_VERSION"
                            ;;
                        *'claude-code-releases/latest')
                            printf '%s\n' "$FAKE_CLAUDE_VERSION"
                            ;;
                        *) exit 1 ;;
                    esac
                    """
                )
            )
            curl.chmod(0o755)

            env = os.environ.copy()
            env.update(
                {
                    "PATH": f"{temp}:{env['PATH']}",
                    "DOCKER_LOG": str(docker_log),
                    "CURL_LOG": str(curl_log),
                    "FAKE_CODEX_VERSION": codex_version,
                    "FAKE_OPENCODE_VERSION": opencode_version,
                    "FAKE_CLAUDE_VERSION": claude_version,
                }
            )
            if cache_bust is None:
                env.pop("AGENT_CACHE_BUST", None)
            else:
                env["AGENT_CACHE_BUST"] = cache_bust

            result = subprocess.run(
                [str(BUILD_SCRIPT), *targets],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=10,
            )
            docker_calls = (
                docker_log.read_text().splitlines() if docker_log.exists() else []
            )
            curl_calls = curl_log.read_text().splitlines() if curl_log.exists() else []
            return result, docker_calls, curl_calls

    def test_default_build_uses_one_version_set_and_cache_key(self) -> None:
        result, docker_calls, curl_calls = self._run()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(
            set(curl_calls),
            {
                "https://registry.npmjs.org/@openai%2Fcodex/latest",
                "https://registry.npmjs.org/opencode-ai/latest",
                "https://downloads.claude.ai/claude-code-releases/latest",
            },
        )
        self.assertEqual(len(docker_calls), 3)

        expected_tags = (
            "hwiwonlee/v8.base:latest",
            "hwiwonlee/sm.base:latest",
            "hwiwonlee/linux.base:latest",
        )
        for call, tag in zip(docker_calls, expected_tags, strict=True):
            self.assertTrue(call.startswith(f"build -t {tag} "), call)
            self.assertIn("CODEX_VERSION=9.8.7", call)
            self.assertIn("OPENCODE_VERSION=8.7.6", call)
            self.assertIn("CLAUDE_CODE_VERSION=7.6.5", call)
            self.assertIn("AGENT_CACHE_BUST=shared-test-key", call)

        self.assertTrue(docker_calls[0].endswith(str(ROOT / "base" / "v8")))
        self.assertTrue(docker_calls[1].endswith(str(ROOT / "base" / "sm")))
        self.assertIn(f"-f {ROOT / 'base' / 'linux' / 'Dockerfile'}", docker_calls[2])
        self.assertTrue(docker_calls[2].endswith(str(ROOT)))

    def test_selected_targets_preserve_requested_order(self) -> None:
        result, docker_calls, _ = self._run("linux", "sm")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(docker_calls), 2)
        self.assertIn("hwiwonlee/linux.base:latest", docker_calls[0])
        self.assertIn("hwiwonlee/sm.base:latest", docker_calls[1])

    def test_platform_and_no_cache_are_forwarded_to_docker(self) -> None:
        result, docker_calls, _ = self._run(
            "linux", "--platform", "linux/amd64", "--no-cache"
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(docker_calls), 1)
        self.assertIn("--platform linux/amd64", docker_calls[0])
        self.assertIn("--no-cache", docker_calls[0])
        self.assertIn("CODEX_VERSION=9.8.7", docker_calls[0])
        self.assertIn("OPENCODE_VERSION=8.7.6", docker_calls[0])
        self.assertIn("CLAUDE_CODE_VERSION=7.6.5", docker_calls[0])

    def test_invalid_target_fails_before_network_or_build(self) -> None:
        result, docker_calls, curl_calls = self._run("chromium")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown target", result.stderr)
        self.assertEqual(docker_calls, [])
        self.assertEqual(curl_calls, [])

    def test_invalid_resolved_version_stops_before_build(self) -> None:
        result, docker_calls, curl_calls = self._run(
            "sm", codex_version="latest"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Codex returned an invalid version", result.stderr)
        self.assertEqual(docker_calls, [])
        self.assertEqual(len(curl_calls), 3)

    def test_generated_cache_key_is_nonempty(self) -> None:
        result, docker_calls, _ = self._run("v8", cache_bust=None)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertRegex(docker_calls[0], r"AGENT_CACHE_BUST=[^ ]+")

if __name__ == "__main__":
    unittest.main()
