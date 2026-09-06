from __future__ import annotations

import re
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LINUX_PROJECTS = ROOT / "projects" / "linux"


def _run_instructions(source: str) -> list[str]:
    lines = source.splitlines()
    instructions: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not re.match(r"^RUN(?:\s|$)", line):
            index += 1
            continue
        instruction = line
        while instruction.rstrip().endswith("\\"):
            index += 1
            if index >= len(lines):
                break
            instruction += "\n" + lines[index]
        instructions.append(instruction)
        index += 1
    return instructions


class LinuxBuildParallelismTests(unittest.TestCase):
    def test_every_leaf_accepts_the_shared_kbuild_jobs_argument(self) -> None:
        vulnerable = sorted(LINUX_PROJECTS.glob("CVE-*/Dockerfile"))
        fixed = sorted(LINUX_PROJECTS.glob("CVE-*/Dockerfile.fixed"))
        self.assertEqual(len(vulnerable), 137)
        self.assertEqual(len(fixed), 137)

        defaults: dict[str, Counter[str | None]] = {
            "vulnerable": Counter(),
            "fixed": Counter(),
        }
        for kind, paths in (("vulnerable", vulnerable), ("fixed", fixed)):
            for path in paths:
                source = path.read_text(encoding="utf-8")
                declarations = re.findall(
                    r"^ARG KBUILD_JOBS(?:=([^\s#]+))?$", source, re.MULTILINE
                )
                self.assertEqual(
                    len(declarations),
                    1,
                    f"{path} must declare ARG KBUILD_JOBS exactly once",
                )
                defaults[kind][declarations[0] or None] += 1
                self.assertNotRegex(source, r"(?m)^ARG KJOBS(?:=|\s|$)")

                for instruction in _run_instructions(source):
                    self.assertNotRegex(
                        instruction,
                        r"\bKBUILD_JOBS=64(?:\s|$)",
                        f"{path} hardcodes build parallelism in a RUN instruction",
                    )

        self.assertEqual(defaults["vulnerable"], Counter({None: 89, "16": 47, "4": 1}))
        self.assertEqual(defaults["fixed"], Counter({None: 89, "64": 48}))

    def test_linux_builder_passes_only_the_canonical_argument_name(self) -> None:
        source = (LINUX_PROJECTS / "build_images.py").read_text(encoding="utf-8")
        self.assertEqual(source.count('build_args["KBUILD_JOBS"]'), 1)
        self.assertNotIn('build_args["KJOBS"]', source)

    def test_direct_base_fixed_leaves_stage_the_runtime_config(self) -> None:
        direct_base: set[str] = set()
        for path in sorted(LINUX_PROJECTS.glob("CVE-*/Dockerfile.fixed")):
            source = path.read_text(encoding="utf-8")
            if "FROM hwiwonlee/linux.base:latest" not in source:
                continue
            direct_base.add(path.parent.name)
            self.assertIn("mkdir -p /run/secb /out /tmp/secb", source, str(path))
            self.assertIn(
                "COPY secb_config.json /run/secb/config.json", source, str(path)
            )

        self.assertEqual(direct_base, {"CVE-2023-54125", "CVE-2024-50211"})


if __name__ == "__main__":
    unittest.main()
