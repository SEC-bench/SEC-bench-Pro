from __future__ import annotations

import re
import shlex
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCKERFILES = {
    "v8": ROOT / "base" / "v8" / "Dockerfile",
    "v8-latest": ROOT / "base" / "v8" / "Dockerfile.latest",
    "sm": ROOT / "base" / "sm" / "Dockerfile",
    "linux": ROOT / "base" / "linux" / "Dockerfile",
}

COMMON_TOOLS = {
    "addr2line",
    "bwrap",
    "curl",
    "envsubst",
    "file",
    "gawk",
    "gdb",
    "git",
    "jq",
    "killall",
    "less",
    "locale",
    "ltrace",
    "make",
    "pip3",
    "pkg-config",
    "ps",
    "python3",
    "rg",
    "rsync",
    "secb-sanitize-git",
    "setpriv",
    "socat",
    "sqlite3",
    "strace",
    "unshare",
    "valgrind",
    "vim",
    "xxd",
    "xz",
}

COMMON_APT_PACKAGES = {
    "binutils",
    "bubblewrap",
    "ca-certificates",
    "curl",
    "file",
    "gawk",
    "gdb",
    "gettext-base",
    "git",
    "jq",
    "less",
    "locales",
    "ltrace",
    "make",
    "pkg-config",
    "procps",
    "psmisc",
    "python3",
    "python3-pip",
    "python3-venv",
    "ripgrep",
    "rsync",
    "socat",
    "sqlite3",
    "strace",
    "util-linux",
    "valgrind",
    "vim",
    "xxd",
    "xz-utils",
}


class BaseDockerfileContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sources = {
            name: path.read_text(encoding="utf-8")
            for name, path in DOCKERFILES.items()
        }

    @staticmethod
    def _apt_packages(source: str) -> set[str]:
        logical_lines: list[str] = []
        current = ""
        for raw_line in source.splitlines():
            line = raw_line.strip()
            current = f"{current} {line}".strip()
            if line.endswith("\\"):
                current = current[:-1].rstrip()
            else:
                logical_lines.append(current)
                current = ""

        packages: set[str] = set()
        install_pattern = re.compile(
            r"apt-get(?:\s+-o\s+\S+)*\s+install\s+"
            r"(?:--?[A-Za-z0-9-]+\s+)*(?P<packages>.*?)(?=\s+&&|$)"
        )
        for instruction in logical_lines:
            for match in install_pattern.finditer(instruction):
                packages.update(shlex.split(match.group("packages")))
        return packages

    def test_common_apt_packages_are_installed(self) -> None:
        for name, source in self.sources.items():
            installed = self._apt_packages(source)
            self.assertTrue(
                COMMON_APT_PACKAGES <= installed,
                f"{name} is missing apt packages "
                f"{sorted(COMMON_APT_PACKAGES - installed)}",
            )

    def test_common_runtime_tool_smoke_is_identical(self) -> None:
        declared: dict[str, set[str]] = {}
        pattern = re.compile(
            r"for tool in \\\n(?P<tools>.*?)\s+do \\\n\s*command -v",
            re.DOTALL,
        )
        for name, source in self.sources.items():
            match = pattern.search(source)
            self.assertIsNotNone(match, f"{name} has no runtime tool smoke loop")
            assert match is not None
            declared[name] = {
                tool.rstrip(";")
                for tool in match.group("tools").replace("\\", "").split()
            }
            self.assertTrue(
                COMMON_TOOLS <= declared[name],
                f"{name} is missing {sorted(COMMON_TOOLS - declared[name])}",
            )

        reference = declared["v8"]
        for name, tools in declared.items():
            self.assertEqual(tools, reference, f"{name} runtime tool contract differs")

    def test_node_and_uv_are_consistent_and_pinned(self) -> None:
        uv_images = set()
        uv_pattern = re.compile(
            r"COPY --from=(ghcr[.]io/astral-sh/uv:[^\s]+) /uv /uvx /bin/"
        )
        for name, source in self.sources.items():
            self.assertIn("https://deb.nodesource.com/setup_24.x", source, name)
            self.assertNotIn("setup_current.x", source, name)
            match = uv_pattern.search(source)
            self.assertIsNotNone(match, f"{name} has no pinned uv image")
            assert match is not None
            uv_image = match.group(1)
            self.assertRegex(uv_image, r":[0-9]+[.][0-9]+[.][0-9]+@sha256:[0-9a-f]{64}$")
            uv_images.add(uv_image)
        self.assertEqual(len(uv_images), 1)

    def test_agents_default_to_latest_and_record_versions(self) -> None:
        required = (
            "ARG CODEX_VERSION=latest",
            "ARG OPENCODE_VERSION=latest",
            "ARG CLAUDE_CODE_VERSION=latest",
            "ARG AGENT_CACHE_BUST=manual",
            '"@openai/codex@${CODEX_VERSION}"',
            '"opencode-ai@${OPENCODE_VERSION}"',
            'bash /tmp/claude-install.sh "${CLAUDE_CODE_VERSION}"',
            "ln -sf /root/.local/bin/claude /usr/local/bin/claude",
            "bash -lc 'command -v codex >/dev/null && command -v opencode >/dev/null && command -v claude >/dev/null'",
            ': "agent-cache-bust=${AGENT_CACHE_BUST}"',
            "DISABLE_AUTOUPDATER=1",
            "OPENCODE_DISABLE_AUTOUPDATE=1",
            "codex --version",
            "opencode --version",
            "claude --version",
            "> /etc/secb-agent-versions",
        )
        for name, source in self.sources.items():
            for text in required:
                self.assertIn(text, source, f"{name} is missing {text}")

    def test_agent_layer_follows_expensive_target_layers(self) -> None:
        expensive_markers = {
            "v8": 'git -C "$SRC/v8" fetch',
            "v8-latest": "ninja -j\"$jobs\" -C out/x64.release d8",
            "sm": "./mach bootstrap --application-choice=js",
            "linux": "uv pip install --system /opt/secb-mcps/linux",
        }
        for name, source in self.sources.items():
            self.assertLess(
                source.index(expensive_markers[name]),
                source.index("ARG AGENT_CACHE_BUST=manual"),
                f"{name} agent refresh invalidates an expensive target layer",
            )

    def test_parent_images_are_digest_pinned(self) -> None:
        for name, source in self.sources.items():
            first_instruction = next(
                line for line in source.splitlines() if line.startswith("FROM ")
            )
            self.assertRegex(first_instruction, r"@sha256:[0-9a-f]{64}$", name)


if __name__ == "__main__":
    unittest.main()
