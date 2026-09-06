from __future__ import annotations

import re
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LINUX_PROJECTS = ROOT / "projects" / "linux"
DOCKERFILE = ROOT / "base" / "linux" / "Dockerfile"
MANIFEST = ROOT / "base" / "linux" / "required-commits.txt"
FETCH_SCRIPT = ROOT / "base" / "linux" / "fetch-required-commits"
FULL_SHA = re.compile(r"[0-9a-f]{40}")
DEFAULT_REMOTE = "https://github.com/torvalds/linux.git"
TORVALDS_REMOTES = {
    DEFAULT_REMOTE,
    "https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git",
}
DIRECT_BASE_FIXED = {
    "CVE-2023-54125": "FIX_COMMIT",
    "CVE-2024-50211": "FIX_PARENT_COMMIT",
}
LEAF_BASE_PACKAGES = {
    "gcc-multilib",
    "libc6-dev-i386",
    "locales",
    "pkg-config",
    "ripgrep",
}


class LinuxBaseCommitTests(unittest.TestCase):
    def test_fetch_helper_does_not_fetch_an_existing_object(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            repository = temp / "repository"
            subprocess.run(
                ["git", "init", "-q", str(repository)], check=True
            )
            subprocess.run(
                ["git", "-C", str(repository), "config", "user.name", "test"],
                check=True,
            )
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(repository),
                    "config",
                    "user.email",
                    "test@example.invalid",
                ],
                check=True,
            )
            (repository / "file").write_text("test\n", encoding="ascii")
            subprocess.run(
                ["git", "-C", str(repository), "add", "file"], check=True
            )
            subprocess.run(
                ["git", "-C", str(repository), "commit", "-qm", "test"],
                check=True,
            )
            commit = subprocess.run(
                ["git", "-C", str(repository), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            manifest = temp / "manifest"
            manifest.write_text(
                f"{commit} https://example.invalid/unreachable.git\n",
                encoding="ascii",
            )

            subprocess.run(
                [str(FETCH_SCRIPT), str(repository), str(manifest)], check=True
            )
            required_ref = subprocess.run(
                [
                    "git",
                    "-C",
                    str(repository),
                    "rev-parse",
                    f"refs/secb-required/{commit}",
                ],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            self.assertEqual(required_ref, commit)

    def test_manifest_exactly_matches_task_build_commits(self) -> None:
        declared: dict[str, str] = {}
        paths = sorted(LINUX_PROJECTS.glob("CVE-*/Dockerfile")) + sorted(
            LINUX_PROJECTS.glob("CVE-*/Dockerfile.fixed")
        )
        self.assertTrue(paths)

        for path in paths:
            source = path.read_text(encoding="utf-8")
            remotes = re.findall(r"^ARG SYZBOT_TREE=([^\s#]+)$", source, re.MULTILINE)
            self.assertLessEqual(len(remotes), 1, str(path))
            remote = remotes[0] if remotes else DEFAULT_REMOTE
            for value in re.findall(
                r"^ARG BUILD_COMMIT=([^\s#]+)$", source, re.MULTILINE
            ):
                self.assertRegex(value, rf"^{FULL_SHA.pattern}$", str(path))
                if value in declared:
                    self.assertEqual(declared[value], remote, str(path))
                declared[value] = remote

        lines = MANIFEST.read_text(encoding="ascii").splitlines()
        self.assertTrue(lines)
        self.assertEqual(lines, sorted(set(lines)))
        manifest: dict[str, str] = {}
        for line in lines:
            fields = line.split()
            self.assertEqual(len(fields), 2, line)
            commit, remote = fields
            self.assertRegex(commit, rf"^{FULL_SHA.pattern}$")
            self.assertTrue(remote.startswith("https://"), line)
            self.assertNotIn(commit, manifest)
            manifest[commit] = remote
        self.assertEqual(manifest, declared)

    def test_base_fetches_only_clone_missing_commits_with_network_guards(self) -> None:
        source = DOCKERFILE.read_text(encoding="utf-8")
        fetch_script = FETCH_SCRIPT.read_text(encoding="utf-8")

        clone = source.index("clone --bare https://github.com/torvalds/linux.git")
        manifest_copy = source.index(
            "COPY base/linux/required-commits.txt /base/required-commits.txt"
        )
        fetch_script_copy = source.index(
            "COPY base/linux/fetch-required-commits "
            "/usr/local/bin/secb-fetch-required-linux-commits"
        )
        missing_check = fetch_script.index(
            'if ! git -C "$repository" cat-file -e "${commit}^{commit}"'
        )
        fetch = fetch_script.index(
            '-C "$repository" fetch --no-tags --depth=1 "$remote" "$commit"'
        )
        required_fetch = source.index(
            "timeout --kill-after=30s 1800s secb-fetch-required-linux-commits"
        )

        self.assertLess(manifest_copy, fetch_script_copy)
        self.assertLess(fetch_script_copy, clone)
        self.assertLess(clone, required_fetch)
        self.assertNotIn("\nRUN ", source[clone:required_fetch])
        self.assertLess(missing_check, fetch)
        self.assertIn("while read -r commit remote extra", fetch_script)
        self.assertIn('test -z "${extra:-}"', fetch_script)
        self.assertIn(
            'git -C "$repository" update-ref "refs/secb-required/${commit}" "$commit"',
            fetch_script,
        )
        self.assertIn("timeout --kill-after=30s 1800s", source)
        self.assertIn("timeout --kill-after=30s 3600s", source)
        self.assertIn("http.lowSpeedLimit=1024", source)
        self.assertIn("http.lowSpeedTime=60", source)
        self.assertIn("timeout --kill-after=30s 600s", fetch_script)
        self.assertIn("http.lowSpeedLimit=1024", fetch_script)
        self.assertIn("http.lowSpeedTime=60", fetch_script)

    def test_all_vulnerable_leaves_guard_the_fallback_fetch(self) -> None:
        external: list[Path] = []
        paths = sorted(LINUX_PROJECTS.glob("CVE-*/Dockerfile"))
        self.assertEqual(len(paths), 137)
        for path in paths:
            source = path.read_text(encoding="utf-8")
            remotes = re.findall(r"^ARG SYZBOT_TREE=([^\s#]+)$", source, re.MULTILINE)
            self.assertLessEqual(len(remotes), 1, str(path))
            remote = '"${SYZBOT_TREE}"' if remotes else "origin"
            commit_check = (
                'git -C /src/linux.git cat-file -e "${BUILD_COMMIT}^{commit}"'
            )
            missing_check = source.index(
                f"if ! {commit_check} 2>/dev/null"
            )
            fetch = source.index(
                '-C /src/linux.git fetch --no-tags --depth=1 '
                f'{remote} "${{BUILD_COMMIT}}"'
            )
            final_check = source.index(commit_check, fetch)
            worktree = source.index(
                'git -C /src/linux.git worktree add --detach '
                '/src/linux "${BUILD_COMMIT}"'
            )
            self.assertLess(missing_check, fetch, str(path))
            self.assertLess(fetch, final_check, str(path))
            self.assertLess(final_check, worktree, str(path))
            self.assertEqual(source.count(commit_check), 2, str(path))
            self.assertEqual(source.count("timeout --kill-after=30s 600s"), 1, str(path))
            self.assertIn("http.lowSpeedLimit=1024", source, str(path))
            self.assertIn("http.lowSpeedTime=60", source, str(path))
            self.assertNotIn(
                'fetch origin "${BUILD_COMMIT}" || true', source, str(path)
            )
            if remotes and remotes[0] not in TORVALDS_REMOTES:
                external.append(path)

        self.assertEqual(
            {path.parent.name for path in external},
            {
                "CVE-2021-47478",
                "CVE-2022-48714",
                "CVE-2022-48847",
                "CVE-2024-56650",
                "CVE-2025-40349",
                "CVE-2026-31513",
            },
        )

    def test_cached_leaf_commit_skips_the_fallback_fetch(self) -> None:
        path = LINUX_PROJECTS / "CVE-2024-49903" / "Dockerfile"
        source = path.read_text(encoding="utf-8")
        start = source.index("RUN set -eux;")
        command = source[start + len("RUN ") : source.index("\n\n", start)]
        command = command.replace("\\\n", "\n")

        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            source_repository = temp / "source"
            bare_repository = temp / "linux.git"
            worktree = temp / "linux"
            subprocess.run(["git", "init", "-q", str(source_repository)], check=True)
            subprocess.run(
                ["git", "-C", str(source_repository), "config", "user.name", "test"],
                check=True,
            )
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(source_repository),
                    "config",
                    "user.email",
                    "test@example.invalid",
                ],
                check=True,
            )
            (source_repository / "file").write_text("cached\n", encoding="ascii")
            subprocess.run(
                ["git", "-C", str(source_repository), "add", "file"], check=True
            )
            subprocess.run(
                ["git", "-C", str(source_repository), "commit", "-qm", "cached"],
                check=True,
            )
            commit = subprocess.run(
                ["git", "-C", str(source_repository), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            subprocess.run(
                [
                    "git",
                    "clone",
                    "-q",
                    "--bare",
                    str(source_repository),
                    str(bare_repository),
                ],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(bare_repository), "remote", "remove", "origin"],
                check=True,
            )

            command = command.replace("/src/linux.git", str(bare_repository))
            command = command.replace("/src/linux", str(worktree))
            subprocess.run(
                ["bash", "-c", command],
                check=True,
                capture_output=True,
                env={"PATH": "/usr/bin:/bin", "BUILD_COMMIT": commit},
            )
            checked_out = subprocess.run(
                ["git", "-C", str(worktree), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            self.assertEqual(checked_out, commit)

    def test_direct_base_fixed_leaves_guard_the_actual_checkout_parent(self) -> None:
        fixed_paths = sorted(LINUX_PROJECTS.glob("CVE-*/Dockerfile.fixed"))
        direct_base = {
            path.parent.name: path
            for path in fixed_paths
            if re.search(
                r"^FROM hwiwonlee/linux\.base:latest$",
                path.read_text(encoding="utf-8"),
                re.MULTILINE,
            )
        }
        self.assertEqual(set(direct_base), set(DIRECT_BASE_FIXED))

        for cve, variable in DIRECT_BASE_FIXED.items():
            path = direct_base[cve]
            source = path.read_text(encoding="utf-8")
            checkout_commit = f'${{{variable}}}^1^{{commit}}'
            commit_check = f'git -C /src/linux.git cat-file -e "{checkout_commit}"'
            missing_check = source.index(f"if ! {commit_check} 2>/dev/null")
            fetch = source.index(
                '-C /src/linux.git fetch --no-tags --depth=20 '
                f'"${{SYZBOT_TREE}}" "${{{variable}}}"'
            )
            final_check = source.index(commit_check, fetch)
            worktree = source.index(
                'git -C /src/linux.git worktree add --detach '
                f'/src/linux "${{{variable}}}^"'
            )
            self.assertLess(missing_check, fetch, str(path))
            self.assertLess(fetch, final_check, str(path))
            self.assertLess(final_check, worktree, str(path))
            self.assertEqual(source.count(commit_check), 2, str(path))
            self.assertEqual(source.count("timeout --kill-after=30s 600s"), 1, str(path))
            self.assertIn("http.lowSpeedLimit=1024", source, str(path))
            self.assertIn("http.lowSpeedTime=60", source, str(path))

        inherited = set(fixed_paths) - set(direct_base.values())
        self.assertEqual(len(inherited), 135)
        for path in inherited:
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("/src/linux.git fetch", source, str(path))
            self.assertNotIn("/src/linux.git worktree add", source, str(path))

    def test_leaf_images_reuse_base_packages_and_locale(self) -> None:
        base_source = DOCKERFILE.read_text(encoding="utf-8")
        install_start = base_source.index(
            "apt-get -o Acquire::Retries=5 install -y --no-install-recommends"
        )
        install_end = base_source.index(
            "&& rm -rf /var/lib/apt/lists/*", install_start
        )
        base_install = base_source[install_start:install_end]
        for package in LEAF_BASE_PACKAGES:
            self.assertRegex(
                base_install,
                rf"(?<![A-Za-z0-9-]){re.escape(package)}(?![A-Za-z0-9-])",
            )
        self.assertIn("locale-gen en_US.UTF-8", base_source)
        self.assertIn("ENV LANG=en_US.UTF-8", base_source)
        self.assertIn("ENV LC_ALL=en_US.UTF-8", base_source)

        paths = sorted(LINUX_PROJECTS.glob("CVE-*/Dockerfile")) + [
            LINUX_PROJECTS / cve / "Dockerfile.fixed"
            for cve in sorted(DIRECT_BASE_FIXED)
        ]
        self.assertEqual(len(paths), 139)
        for path in paths:
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("RUN apt-get update", source, str(path))
            self.assertNotIn("ENV LANG=C.UTF-8", source, str(path))
            self.assertNotIn("ENV LC_ALL=C.UTF-8", source, str(path))
            self.assertIn("ENV LANG=en_US.UTF-8", source, str(path))
            self.assertIn("ENV LC_ALL=en_US.UTF-8", source, str(path))


if __name__ == "__main__":
    unittest.main()
