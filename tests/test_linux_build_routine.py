from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
BUILD_IMAGES = ROOT / "projects" / "linux" / "build_images.py"


def _load_build_images_module():
    """Load the builder without requiring Rich in the unit-test environment."""
    rich = types.ModuleType("rich")
    progress = types.ModuleType("rich.progress")
    text = types.ModuleType("rich.text")
    for name in (
        "BarColumn",
        "MofNCompleteColumn",
        "Progress",
        "SpinnerColumn",
        "TextColumn",
        "TimeElapsedColumn",
        "TimeRemainingColumn",
    ):
        setattr(progress, name, type(name, (), {}))
    text.Text = str

    spec = importlib.util.spec_from_file_location("linux_build_images_test", BUILD_IMAGES)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    with patch.dict(
        sys.modules,
        {"rich": rich, "rich.progress": progress, "rich.text": text},
    ):
        spec.loader.exec_module(module)
    return module


class LinuxBuildRoutineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.builder = _load_build_images_module()

    def test_help_works_without_optional_rich_dependency(self) -> None:
        result = subprocess.run(
            [sys.executable, "-S", str(BUILD_IMAGES), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Build Linux kernel benchmark Docker images", result.stdout)

    def test_failed_vulnerable_parent_is_excluded_from_fixed_builds(self) -> None:
        calls: list[tuple[str, tuple[str, ...]]] = []

        def build_instances(mode, instances, *_args, **_kwargs):
            calls.append((mode, tuple(instances)))
            return ["CVE-bad"] if mode == "vuln" else []

        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch.object(self.builder, "LINUX_DIR", Path(temp_dir)),
            patch.object(
                self.builder, "unknown_requested_instances", return_value=[]
            ),
            patch.object(self.builder, "build_base", return_value=True),
            patch.object(
                self.builder,
                "ensure_compatible_linux_base",
                return_value=True,
            ),
            patch.object(
                self.builder, "filter_instances", side_effect=lambda items, _mode: list(items)
            ),
            patch.object(
                self.builder,
                "fixed_dockerfile_vulnerable_parent",
                side_effect=lambda cve: f"hwiwonlee/linux.x86_64:{cve}",
            ),
            patch.object(
                self.builder, "build_instances_parallel", side_effect=build_instances
            ),
            patch.object(
                self.builder, "repair_fixed_vulnerable_parents", return_value=[]
            ),
            patch.object(self.builder, "log"),
            patch.object(
                sys,
                "argv",
                [
                    str(BUILD_IMAGES),
                    "--mode",
                    "all",
                    "--instances",
                    "CVE-good",
                    "CVE-bad",
                    "--no-progress",
                ],
            ),
        ):
            result = self.builder.main()

        self.assertEqual(result, 1)
        self.assertEqual(
            calls,
            [
                ("vuln", ("CVE-good", "CVE-bad")),
                ("fixed", ("CVE-good",)),
                ("latest", ("CVE-good", "CVE-bad")),
            ],
        )

    def test_failed_vulnerable_build_blocks_only_paired_parent_fixed(self) -> None:
        calls: list[tuple[str, tuple[str, ...]]] = []

        def build_instances(mode, instances, *_args, **_kwargs):
            calls.append((mode, tuple(instances)))
            return list(instances) if mode == "vuln" else []

        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch.object(self.builder, "LINUX_DIR", Path(temp_dir)),
            patch.object(
                self.builder, "unknown_requested_instances", return_value=[]
            ),
            patch.object(self.builder, "build_base", return_value=True),
            patch.object(
                self.builder, "ensure_compatible_linux_base", return_value=True
            ),
            patch.object(
                self.builder,
                "filter_instances",
                side_effect=lambda items, _mode: list(items),
            ),
            patch.object(
                self.builder,
                "fixed_dockerfile_vulnerable_parent",
                side_effect=lambda cve: (
                    "hwiwonlee/linux.x86_64:CVE-paired"
                    if cve == "CVE-paired"
                    else None
                ),
            ),
            patch.object(
                self.builder, "build_instances_parallel", side_effect=build_instances
            ),
            patch.object(
                self.builder, "repair_fixed_vulnerable_parents", return_value=[]
            ),
            patch.object(self.builder, "log"),
            patch.object(
                sys,
                "argv",
                [
                    str(BUILD_IMAGES),
                    "--mode",
                    "all",
                    "--instances",
                    "CVE-direct",
                    "CVE-paired",
                    "--no-progress",
                ],
            ),
        ):
            result = self.builder.main()

        self.assertEqual(result, 1)
        self.assertIn(("fixed", ("CVE-direct",)), calls)

    def test_kbuild_jobs_must_be_positive(self) -> None:
        for value in ("0", "-1"):
            with (
                self.subTest(value=value),
                patch.object(
                    sys,
                    "argv",
                    [
                        str(BUILD_IMAGES),
                        "--mode",
                        "base",
                        "--instances",
                        "CVE-test",
                        "--kbuild-jobs",
                        value,
                        "--no-progress",
                    ],
                ),
                patch("sys.stderr", new_callable=io.StringIO),
                patch.object(self.builder, "build_base") as build_base,
            ):
                with self.assertRaises(SystemExit) as raised:
                    self.builder.main()
                self.assertEqual(raised.exception.code, 2)
                build_base.assert_not_called()

    def _run_standalone_mode(
        self,
        mode: str,
        *,
        pending: list[str],
        fixed_uses_base: bool = False,
        base_ok: bool = True,
        skip_existing: bool = False,
    ) -> tuple[int, list[str]]:
        events: list[str] = []
        argv = [
            str(BUILD_IMAGES),
            "--mode",
            mode,
            "--instances",
            "CVE-test",
            "--no-progress",
        ]
        if skip_existing:
            argv.insert(-1, "--skip-existing")

        def ensure_base(*_args, **_kwargs):
            events.append("base")
            return base_ok

        def build_instances(built_mode, built_instances, *_args, **_kwargs):
            events.append(f"{built_mode}:{','.join(built_instances)}")
            return []

        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch.object(self.builder, "LINUX_DIR", Path(temp_dir)),
            patch.object(
                self.builder, "unknown_requested_instances", return_value=[]
            ),
            patch.object(
                self.builder,
                "filter_instances",
                return_value=["CVE-test"],
            ),
            patch.object(
                self.builder,
                "pending_instance_builds",
                return_value=pending,
            ),
            patch.object(
                self.builder,
                "fixed_dockerfile_uses_canonical_base",
                return_value=fixed_uses_base,
            ),
            patch.object(
                self.builder,
                "ensure_compatible_linux_base",
                side_effect=ensure_base,
            ),
            patch.object(
                self.builder,
                "build_instances_parallel",
                side_effect=build_instances,
            ),
            patch.object(
                self.builder, "repair_fixed_vulnerable_parents", return_value=[]
            ),
            patch.object(self.builder, "log"),
            patch.object(sys, "argv", argv),
        ):
            result = self.builder.main()
        return result, events

    def test_standalone_vulnerable_and_latest_require_base_before_leaf(self) -> None:
        for mode in ("vuln", "latest"):
            with self.subTest(mode=mode):
                result, events = self._run_standalone_mode(
                    mode, pending=["CVE-test"]
                )
                self.assertEqual(result, 0)
                self.assertEqual(events, ["base", f"{mode}:CVE-test"])

    def test_all_checks_compatible_base_before_dependent_leaves(self) -> None:
        events: list[str] = []

        def build_base(*_args, **_kwargs):
            events.append("base-phase")
            return True

        def ensure_base(*_args, **_kwargs):
            events.append("base-contract")
            return True

        def build_instances(mode, *_args, **_kwargs):
            events.append(mode)
            return []

        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch.object(self.builder, "LINUX_DIR", Path(temp_dir)),
            patch.object(
                self.builder, "unknown_requested_instances", return_value=[]
            ),
            patch.object(
                self.builder,
                "filter_instances",
                side_effect=lambda items, _mode: list(items),
            ),
            patch.object(
                self.builder,
                "mode_has_pending_base_dependency",
                return_value=True,
            ),
            patch.object(self.builder, "build_base", side_effect=build_base),
            patch.object(
                self.builder,
                "ensure_compatible_linux_base",
                side_effect=ensure_base,
            ),
            patch.object(
                self.builder,
                "build_instances_parallel",
                side_effect=build_instances,
            ),
            patch.object(
                self.builder, "repair_fixed_vulnerable_parents", return_value=[]
            ) as repair_parents,
            patch.object(self.builder, "log"),
            patch.object(
                sys,
                "argv",
                [
                    str(BUILD_IMAGES),
                    "--mode",
                    "all",
                    "--instances",
                    "CVE-test",
                    "--skip-existing",
                    "--no-progress",
                ],
            ),
        ):
            result = self.builder.main()

        self.assertEqual(result, 0)
        self.assertEqual(
            events,
            ["base-phase", "base-contract", "vuln", "fixed", "latest"],
        )
        repair_parents.assert_called_once()
        self.assertTrue(repair_parents.call_args.args[1].skip_existing)

    def test_all_stops_before_leaves_when_base_contract_recheck_fails(self) -> None:
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch.object(self.builder, "LINUX_DIR", Path(temp_dir)),
            patch.object(
                self.builder, "unknown_requested_instances", return_value=[]
            ),
            patch.object(
                self.builder,
                "filter_instances",
                side_effect=lambda items, _mode: list(items),
            ),
            patch.object(
                self.builder,
                "mode_has_pending_base_dependency",
                return_value=True,
            ),
            patch.object(self.builder, "build_base", return_value=True),
            patch.object(
                self.builder,
                "ensure_compatible_linux_base",
                return_value=False,
            ),
            patch.object(
                self.builder,
                "build_instances_parallel",
            ) as build_instances,
            patch.object(self.builder, "log"),
            patch.object(
                sys,
                "argv",
                [
                    str(BUILD_IMAGES),
                    "--mode",
                    "all",
                    "--instances",
                    "CVE-test",
                    "--skip-existing",
                    "--no-progress",
                ],
            ),
        ):
            result = self.builder.main()

        self.assertEqual(result, 1)
        build_instances.assert_not_called()

    def test_all_with_every_leaf_skipped_preserves_base_skip_semantics(self) -> None:
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch.object(self.builder, "LINUX_DIR", Path(temp_dir)),
            patch.object(
                self.builder, "unknown_requested_instances", return_value=[]
            ),
            patch.object(
                self.builder,
                "filter_instances",
                side_effect=lambda items, _mode: list(items),
            ),
            patch.object(
                self.builder,
                "mode_has_pending_base_dependency",
                return_value=False,
            ),
            patch.object(self.builder, "build_base", return_value=True),
            patch.object(self.builder, "ensure_compatible_linux_base") as ensure,
            patch.object(
                self.builder,
                "build_instances_parallel",
                return_value=[],
            ),
            patch.object(
                self.builder, "repair_fixed_vulnerable_parents", return_value=[]
            ),
            patch.object(self.builder, "log"),
            patch.object(
                sys,
                "argv",
                [
                    str(BUILD_IMAGES),
                    "--mode",
                    "all",
                    "--instances",
                    "CVE-test",
                    "--skip-existing",
                    "--no-progress",
                ],
            ),
        ):
            result = self.builder.main()

        self.assertEqual(result, 0)
        ensure.assert_not_called()

    def test_base_only_skip_does_not_add_a_compatibility_rebuild(self) -> None:
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch.object(self.builder, "LINUX_DIR", Path(temp_dir)),
            patch.object(
                self.builder, "unknown_requested_instances", return_value=[]
            ),
            patch.object(self.builder, "build_base", return_value=True) as build_base,
            patch.object(self.builder, "ensure_compatible_linux_base") as ensure,
            patch.object(self.builder, "log"),
            patch.object(
                sys,
                "argv",
                [
                    str(BUILD_IMAGES),
                    "--mode",
                    "base",
                    "--instances",
                    "CVE-test",
                    "--skip-existing",
                    "--no-progress",
                ],
            ),
        ):
            result = self.builder.main()

        self.assertEqual(result, 0)
        build_base.assert_called_once()
        ensure.assert_not_called()

    def test_standalone_mode_stops_when_base_recheck_fails(self) -> None:
        result, events = self._run_standalone_mode(
            "vuln", pending=["CVE-test"], base_ok=False
        )
        self.assertEqual(result, 1)
        self.assertEqual(events, ["base"])

    def test_skip_existing_all_leaves_avoids_base_rebuild(self) -> None:
        for mode in ("vuln", "latest"):
            with self.subTest(mode=mode):
                result, events = self._run_standalone_mode(
                    mode, pending=[], skip_existing=True
                )
                self.assertEqual(result, 0)
                self.assertEqual(events, [f"{mode}:CVE-test"])

    def test_fixed_requires_base_for_every_pending_leaf_lineage(self) -> None:
        result, events = self._run_standalone_mode(
            "fixed", pending=["CVE-test"], fixed_uses_base=True
        )
        self.assertEqual(result, 0)
        self.assertEqual(events, ["base", "fixed:CVE-test"])

        result, events = self._run_standalone_mode(
            "fixed", pending=["CVE-test"], fixed_uses_base=False
        )
        self.assertEqual(result, 0)
        self.assertEqual(events, ["base", "fixed:CVE-test"])

        result, events = self._run_standalone_mode(
            "fixed",
            pending=[],
            fixed_uses_base=True,
            skip_existing=True,
        )
        self.assertEqual(result, 0)
        self.assertEqual(events, ["fixed:CVE-test"])

    def test_pending_builds_respect_skip_existing(self) -> None:
        with patch.object(
            self.builder,
            "image_exists",
            side_effect=lambda tag: tag.endswith(":CVE-existing"),
        ) as image_exists:
            pending = self.builder.pending_instance_builds(
                "vuln",
                ["CVE-existing", "CVE-missing"],
                skip_existing=True,
            )
        self.assertEqual(pending, ["CVE-missing"])
        self.assertEqual(image_exists.call_count, 2)

        with patch.object(self.builder, "image_exists") as image_exists:
            pending = self.builder.pending_instance_builds(
                "fixed", ["CVE-one"], skip_existing=False
            )
        self.assertEqual(pending, ["CVE-one"])
        image_exists.assert_not_called()

    def test_vulnerable_build_records_the_immutable_base_id(self) -> None:
        base_id = "sha256:" + "a" * 64
        args = types.SimpleNamespace(
            kbuild_jobs=None,
            linux_ref="main",
            no_cache=False,
            parallel=1,
            platform="linux/amd64",
            skip_existing=False,
        )
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch.object(self.builder, "LINUX_DIR", Path(temp_dir)),
            patch.object(self.builder, "image_id", return_value=base_id),
            patch.object(
                self.builder,
                "build_image",
                return_value=("hwiwonlee/linux.x86_64:CVE-test", True, 0.0),
            ) as build_image,
            patch.object(self.builder, "log"),
        ):
            cve_dir = Path(temp_dir) / "CVE-test"
            cve_dir.mkdir()
            (cve_dir / "Dockerfile").write_text(
                "FROM hwiwonlee/linux.base:latest\n", encoding="utf-8"
            )
            failed = self.builder.build_instances_parallel(
                "vuln", ["CVE-test"], args, Path(temp_dir)
            )

        self.assertEqual(failed, [])
        self.assertEqual(
            build_image.call_args.kwargs["labels"],
            {self.builder.BASE_LINEAGE_LABEL: base_id},
        )

    def test_skipped_vulnerable_build_does_not_require_a_local_base(self) -> None:
        args = types.SimpleNamespace(skip_existing=True)
        with (
            patch.object(
                self.builder, "pending_instance_builds", return_value=[]
            ),
            patch.object(self.builder, "image_id") as image_id,
            patch.object(self.builder, "build_image") as build_image,
            patch.object(self.builder, "log"),
        ):
            failed = self.builder.build_instances_parallel(
                "vuln", ["CVE-existing"], args, Path("unused")
            )

        self.assertEqual(failed, [])
        image_id.assert_not_called()
        build_image.assert_not_called()

    def test_lineage_requires_matching_marker_and_rootfs_prefix(self) -> None:
        base_id = "sha256:" + "a" * 64

        def inspect_result(*, marker=base_id, layers=None, config=True):
            child = {
                "Id": "sha256:" + "b" * 64,
                "Config": (
                    {"Labels": {self.builder.BASE_LINEAGE_LABEL: marker}}
                    if config
                    else None
                ),
                "RootFS": {"Layers": layers or ["base-1", "base-2", "leaf"]},
            }
            records = [
                {"Id": base_id, "RootFS": {"Layers": ["base-1", "base-2"]}},
                child,
            ]
            return subprocess.CompletedProcess(
                ["docker", "image", "inspect"], 0, json.dumps(records), ""
            )

        cases = {
            "current": (inspect_result(), True),
            "stale marker": (inspect_result(marker="sha256:" + "c" * 64), False),
            "wrong rootfs": (inspect_result(layers=["old-base", "leaf"]), False),
            "malformed config": (inspect_result(config=False), False),
            "invalid json": (
                subprocess.CompletedProcess(
                    ["docker", "image", "inspect"], 0, "not-json", ""
                ),
                False,
            ),
        }
        for name, (completed, expected) in cases.items():
            with (
                self.subTest(name=name),
                patch.object(self.builder.subprocess, "run", return_value=completed),
            ):
                self.assertEqual(
                    self.builder.image_has_current_base_lineage(
                        "hwiwonlee/linux.x86_64:CVE-test"
                    ),
                    expected,
                )

    def test_fixed_rebuilds_and_verifies_a_stale_vulnerable_parent(self) -> None:
        args = types.SimpleNamespace(skip_existing=True, push=True)
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch.object(self.builder, "LINUX_DIR", Path(temp_dir)),
            patch.object(
                self.builder, "pending_instance_builds", return_value=["CVE-test"]
            ),
            patch.object(
                self.builder,
                "image_has_current_base_lineage",
                side_effect=[False, True],
            ),
            patch.object(
                self.builder, "build_instances_parallel", return_value=[]
            ) as build_parents,
            patch.object(
                self.builder.subprocess,
                "run",
                return_value=subprocess.CompletedProcess(["docker", "push"], 0),
            ) as run,
            patch.object(self.builder, "log"),
        ):
            cve_dir = Path(temp_dir) / "CVE-test"
            cve_dir.mkdir()
            (cve_dir / "Dockerfile.fixed").write_text(
                "FROM hwiwonlee/linux.x86_64:CVE-test\n", encoding="utf-8"
            )
            failures = self.builder.repair_fixed_vulnerable_parents(
                ["CVE-test"], args, Path(temp_dir)
            )

        self.assertEqual(failures, [])
        mode, rebuilt, rebuilt_args, *_ = build_parents.call_args.args
        self.assertEqual((mode, rebuilt), ("vuln", ["CVE-test"]))
        self.assertFalse(rebuilt_args.skip_existing)
        run.assert_called_once_with(
            ["docker", "push", "hwiwonlee/linux.x86_64:CVE-test"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def test_fixed_fails_closed_if_rebuilt_parent_has_wrong_lineage(self) -> None:
        args = types.SimpleNamespace(skip_existing=False, push=True)
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch.object(self.builder, "LINUX_DIR", Path(temp_dir)),
            patch.object(
                self.builder,
                "image_has_current_base_lineage",
                return_value=False,
            ),
            patch.object(
                self.builder, "build_instances_parallel", return_value=[]
            ),
            patch.object(self.builder.subprocess, "run") as run,
            patch.object(self.builder, "log"),
        ):
            cve_dir = Path(temp_dir) / "CVE-test"
            cve_dir.mkdir()
            (cve_dir / "Dockerfile.fixed").write_text(
                "FROM hwiwonlee/linux.x86_64:CVE-test\n", encoding="utf-8"
            )
            failures = self.builder.repair_fixed_vulnerable_parents(
                ["CVE-test"], args, Path(temp_dir)
            )

        self.assertEqual(failures, ["CVE-test"])
        run.assert_not_called()

    def test_explicit_unknown_instance_fails_before_any_build(self) -> None:
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch.object(self.builder, "LINUX_DIR", Path(temp_dir)),
            patch.object(self.builder, "build_base") as build_base,
            patch.object(self.builder, "build_instances_parallel") as build_instances,
            patch.object(self.builder, "log") as log,
            patch.object(
                sys,
                "argv",
                [
                    str(BUILD_IMAGES),
                    "--mode",
                    "fixed",
                    "--instances",
                    "CVE-not-present",
                    "--no-progress",
                ],
            ),
        ):
            result = self.builder.main()

        self.assertEqual(result, 1)
        self.assertIn("unknown requested instance", log.call_args.args[0])
        build_base.assert_not_called()
        build_instances.assert_not_called()

    def test_default_discovery_does_not_apply_explicit_instance_validation(self) -> None:
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch.object(self.builder, "LINUX_DIR", Path(temp_dir)),
            patch.object(
                self.builder, "discover_instances", return_value=["CVE-auto"]
            ),
            patch.object(self.builder, "unknown_requested_instances") as unknown,
            patch.object(self.builder, "build_base", return_value=True),
            patch.object(self.builder, "log"),
            patch.object(
                sys,
                "argv",
                [str(BUILD_IMAGES), "--mode", "base", "--no-progress"],
            ),
        ):
            result = self.builder.main()

        self.assertEqual(result, 0)
        unknown.assert_not_called()

    def test_repeated_explicit_instances_are_built_once(self) -> None:
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch.object(self.builder, "LINUX_DIR", Path(temp_dir)),
            patch.object(
                self.builder, "filter_instances", side_effect=lambda items, _mode: items
            ),
            patch.object(
                self.builder, "mode_has_pending_base_dependency", return_value=False
            ),
            patch.object(
                self.builder, "build_instances_parallel", return_value=[]
            ) as build_instances,
            patch.object(self.builder, "log"),
            patch.object(
                sys,
                "argv",
                [
                    str(BUILD_IMAGES),
                    "--mode",
                    "vuln",
                    "--instances",
                    "CVE-test",
                    "CVE-test",
                    "--no-progress",
                ],
            ),
        ):
            (Path(temp_dir) / "CVE-test").mkdir()
            result = self.builder.main()

        self.assertEqual(result, 0)
        self.assertEqual(build_instances.call_args.args[1], ["CVE-test"])

    def test_compatibility_rebuild_ignores_skip_existing_and_rechecks(self) -> None:
        args = types.SimpleNamespace(platform="linux/amd64")
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch.object(
                self.builder,
                "linux_base_is_compatible",
                side_effect=[False, True],
            ) as compatible,
            patch.object(self.builder, "build_base", return_value=True) as build_base,
            patch.object(self.builder, "log"),
        ):
            result = self.builder.ensure_compatible_linux_base(
                args, Path(temp_dir)
            )
        self.assertTrue(result)
        self.assertEqual(compatible.call_count, 2)
        build_base.assert_called_once_with(
            args, Path(temp_dir), None, force_rebuild=True
        )

    def test_forced_base_build_bypasses_only_the_skip_existing_flag(self) -> None:
        args = types.SimpleNamespace(
            platform="linux/amd64",
            no_cache=True,
            skip_existing=True,
        )
        completed = subprocess.CompletedProcess(
            [str(self.builder.BASE_BUILDER)], 0, b"canonical build output\n"
        )
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch.object(
                self.builder,
                "image_exists",
            ) as image_exists,
            patch.object(
                self.builder.subprocess,
                "run",
                return_value=completed,
            ) as run,
            patch.object(self.builder, "log"),
        ):
            log_dir = Path(temp_dir)
            result = self.builder.build_base(
                args,
                log_dir,
                force_rebuild=True,
            )
            log_contents = (log_dir / "base.log").read_bytes()

        self.assertTrue(result)
        image_exists.assert_not_called()
        command = run.call_args.args[0]
        self.assertEqual(
            command,
            [
                str(self.builder.BASE_BUILDER),
                "--platform",
                "linux/amd64",
                "--no-cache",
                "linux",
            ],
        )
        self.assertEqual(run.call_args.kwargs["env"]["DOCKER_BUILDKIT"], "1")
        self.assertEqual(log_contents, b"canonical build output\n")

    def test_base_build_skip_existing_avoids_canonical_builder(self) -> None:
        args = types.SimpleNamespace(
            platform="linux/amd64",
            no_cache=False,
            skip_existing=True,
        )
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch.object(self.builder, "image_exists", return_value=True) as exists,
            patch.object(self.builder.subprocess, "run") as run,
            patch.object(self.builder, "log"),
        ):
            log_dir = Path(temp_dir)
            result = self.builder.build_base(args, log_dir)
            log_contents = (log_dir / "base.log").read_text()

        self.assertTrue(result)
        exists.assert_called_once_with(self.builder.BASE_IMAGE)
        run.assert_not_called()
        self.assertEqual(log_contents, f"SKIPPED existing {self.builder.BASE_IMAGE}\n")

    def test_base_probe_covers_manifest_tools_agents_and_mcp(self) -> None:
        manifest = b"a" * 40 + b" https://example.test/linux.git\n"
        expected_sha = hashlib.sha256(manifest).hexdigest()
        completed = subprocess.CompletedProcess(["docker", "run"], 0, "", "")
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch.object(
                self.builder,
                "REQUIRED_COMMITS_MANIFEST",
                Path(temp_dir) / "required-commits.txt",
            ) as manifest_path,
        ):
            manifest_path.write_bytes(manifest)
            with (
                patch.object(self.builder, "image_exists", return_value=True),
                patch.object(
                    self.builder.subprocess,
                    "run",
                    return_value=completed,
                ) as run,
            ):
                compatible = self.builder.linux_base_is_compatible("linux/amd64")

        self.assertTrue(compatible)
        command = run.call_args.args[0]
        self.assertIn(expected_sha, command)
        self.assertIn("--platform", command)
        self.assertIn("--network", command)
        self.assertIn("--read-only", command)
        probe = command[command.index("-c") + 1]
        for expected in (
            "/base/required-commits.txt",
            "/etc/secb-agent-versions",
            "/src/linux.git",
            "cat-file -e",
            "secb-linux-vm-mcp",
            "import fastmcp, secb_linux_vm_mcp",
            "codex",
            "opencode",
            "claude",
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
        ):
            self.assertIn(expected, probe)

    def test_current_direct_base_fixed_set_is_detected(self) -> None:
        direct = [
            cve
            for cve in self.builder.discover_instances()
            if self.builder.fixed_dockerfile_uses_canonical_base(cve)
        ]
        self.assertEqual(direct, ["CVE-2023-54125", "CVE-2024-50211"])


if __name__ == "__main__":
    unittest.main()
