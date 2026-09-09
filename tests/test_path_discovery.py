"""Regression tests for untrusted symlinks in grading input discovery."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness"))

import grade  # noqa: E402
import source_review  # noqa: E402


class PathDiscoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def test_js_discovery_does_not_follow_a_symlinked_directory(self) -> None:
        external = self.root / "outside-instance"
        external.mkdir()
        secret_poc = external / "poc.js"
        secret_poc.write_text("host file must not be graded\n", encoding="utf-8")

        instance = self.root / "run" / "123"
        audit = instance / "audit"
        audit.mkdir(parents=True)
        local_poc = audit / "poc_local.js"
        local_poc.write_text("print('local')\n", encoding="utf-8")
        (audit / "linked-host-directory").symlink_to(
            external, target_is_directory=True
        )

        self.assertEqual(grade.find_js_files(instance), [local_poc])

    def test_instance_discovery_does_not_follow_a_symlinked_directory(self) -> None:
        target = self.root / "run"
        target.mkdir()
        real_instance = target / "123"
        real_instance.mkdir()
        external = self.root / "outside-run"
        external.mkdir()
        (target / "linked-instance").symlink_to(external, target_is_directory=True)

        self.assertEqual(grade.collect_instance_dirs(target), [real_instance])

    def test_timestamp_discovery_does_not_follow_a_symlinked_directory(self) -> None:
        target = self.root / "runs"
        target.mkdir()
        real_timestamp = target / "20250101_010101"
        real_timestamp.mkdir()
        external = self.root / "outside-runs"
        external.mkdir()
        (target / "20250102_020202").symlink_to(
            external, target_is_directory=True
        )

        self.assertEqual(grade.resolve_timestamp_dirs(target), [real_timestamp])

    def test_explicitly_resolved_timestamp_symlink_remains_supported(self) -> None:
        external = self.root / "20250103_030303"
        external.mkdir()
        explicit_link = self.root / "explicit-link"
        explicit_link.symlink_to(external, target_is_directory=True)

        # main() resolves the explicitly supplied target before discovery. Preserve
        # that behavior while rejecting symlinks encountered below the target.
        resolved = explicit_link.resolve()
        self.assertEqual(grade.resolve_timestamp_dirs(resolved), [resolved])

    def test_linux_discovery_rejects_symlinked_audit_directory(self) -> None:
        instance = self.root / "instance"
        instance.mkdir()
        external_audit = self.root / "outside-audit"
        external_audit.mkdir()
        (external_audit / "poc.c").write_text("host secret\n", encoding="utf-8")
        (instance / "audit").symlink_to(external_audit, target_is_directory=True)

        self.assertEqual(grade.find_linux_poc_files(instance), [])

    def test_linux_discovery_rejects_symlinked_candidate(self) -> None:
        instance = self.root / "instance"
        audit = instance / "audit"
        audit.mkdir(parents=True)
        external_poc = self.root / "outside-poc.c"
        external_poc.write_text("host secret\n", encoding="utf-8")
        (audit / "poc.c").symlink_to(external_poc)

        self.assertEqual(grade.find_linux_poc_files(instance), [])

    def test_solver_trajectory_rejects_symlinked_directory(self) -> None:
        instance = self.root / "instance"
        instance.mkdir()
        external = self.root / "outside-trajectory"
        external.mkdir()
        (external / "session.json").write_text(
            '{"host_secret": "must not be read"}\n', encoding="utf-8"
        )
        (instance / "trajectory").symlink_to(external, target_is_directory=True)

        with self.assertRaisesRegex(ValueError, "real directory inside the instance"):
            source_review.load_solver_trajectory(instance)

    def test_solver_stdout_rejects_symlinked_file(self) -> None:
        instance = self.root / "instance"
        instance.mkdir()
        external = self.root / "outside-stdout.txt"
        external.write_text("host secret\n", encoding="utf-8")
        (instance / "agent_stdout.txt").symlink_to(external)

        with self.assertRaisesRegex(ValueError, "real regular file inside the instance"):
            source_review.load_solver_trajectory(instance)

    def test_task_statement_rejects_symlinked_file(self) -> None:
        instance = self.root / "instance"
        instance.mkdir()
        external = self.root / "outside-prompt.txt"
        external.write_text("host secret\n", encoding="utf-8")
        (instance / "prompt.txt").symlink_to(external)

        with self.assertRaisesRegex(ValueError, "could not safely open"):
            grade._task_statement(
                instance,
                {"target_source_files": ["src/assigned.cc"], "description": "safe"},
            )

    def test_task_statement_oversize_is_not_treated_as_missing(self) -> None:
        instance = self.root / "instance"
        instance.mkdir()
        (instance / "prompt.txt").write_text("oversized", encoding="utf-8")

        with (
            patch.object(source_review, "MAX_TASK_STATEMENT_BYTES", 4),
            self.assertRaisesRegex(ValueError, "exceeds"),
        ):
            grade._task_statement(instance, {"description": "fallback must not hide it"})

    def test_regular_manifest_and_nested_trajectory_source_are_loaded(self) -> None:
        instance = self.root / "instance"
        records = instance / "records"
        records.mkdir(parents=True)
        (records / "events.jsonl").write_text(
            '{"event": "one"}\n{"event": "two"}\n', encoding="utf-8"
        )
        (instance / "codex_manifest.json").write_text(
            json.dumps({"source": "records/events.jsonl"}), encoding="utf-8"
        )

        trajectory = source_review.load_solver_trajectory(instance)
        self.assertEqual(trajectory["provider"], "codex")
        self.assertEqual(trajectory["source"], "records/events.jsonl")
        self.assertEqual(
            trajectory["events"], [{"event": "one"}, {"event": "two"}]
        )

    def test_manifest_trajectory_source_rejects_a_symlink(self) -> None:
        instance = self.root / "instance"
        records = instance / "records"
        records.mkdir(parents=True)
        external = self.root / "outside-events.jsonl"
        external.write_text('{"host_secret": true}\n', encoding="utf-8")
        (records / "events.jsonl").symlink_to(external)
        (instance / "codex_manifest.json").write_text(
            json.dumps({"source": "records/events.jsonl"}), encoding="utf-8"
        )

        with self.assertRaisesRegex(ValueError, "source must be a real regular file"):
            source_review.load_solver_trajectory(instance)

    def test_regular_opencode_trajectory_is_loaded(self) -> None:
        instance = self.root / "instance"
        trajectory_dir = instance / "trajectory"
        trajectory_dir.mkdir(parents=True)
        (trajectory_dir / "session.json").write_text(
            '{"messages": ["safe"]}\n', encoding="utf-8"
        )

        trajectory = source_review.load_solver_trajectory(instance)
        self.assertEqual(trajectory["provider"], "opencode")
        self.assertEqual(trajectory["sessions"][0]["source"], "trajectory/session.json")
        self.assertEqual(
            trajectory["sessions"][0]["content"], {"messages": ["safe"]}
        )

    def test_regular_prompt_and_missing_prompt_fallback_are_preserved(self) -> None:
        instance = self.root / "instance"
        instance.mkdir()
        prompt = instance / "prompt.txt"
        prompt.write_text("original task\n", encoding="utf-8")
        task_statement = grade._task_statement(instance, {})
        self.assertIn("# Authoritative benchmark contract", task_statement)
        self.assertTrue(
            task_statement.endswith("## Original task text\n\noriginal task\n")
        )

        prompt.unlink()
        fallback = grade._task_statement(
            instance,
            {"target_source_files": ["src/assigned.cc"], "description": "safe"},
        )
        self.assertIn("src/assigned.cc", fallback)

    def test_authoritative_metadata_precedes_a_conflicting_original_prompt(self) -> None:
        instance = self.root / "instance"
        instance.mkdir()
        conflicting = (
            "Target Source Files: host/outside.cc\n"
            "Expected Error Type: WRONG\n"
            "Allowed Flags: --unsafe\n"
        )
        (instance / "prompt.txt").write_text(conflicting, encoding="utf-8")

        statement = grade._task_statement(
            instance,
            {
                "target_source_files": ["src/assigned.cc"],
                "target_vulnerability_type": "TYPE_CONFUSION",
                "error_type": "ASAN_CRASH",
                "verification_binary": "d8",
                "command_options": "--safe",
            },
        )
        contract, original = statement.split("## Original task text\n\n", 1)
        self.assertIn("overrides conflicting claims", contract)
        self.assertIn("Target Source Files: src/assigned.cc", contract)
        self.assertIn("Target Vulnerability Type: TYPE_CONFUSION", contract)
        self.assertIn("Expected Error Type: ASAN_CRASH", contract)
        self.assertIn("Verification Binary: d8", contract)
        self.assertIn("Allowed Flags: --safe", contract)
        self.assertNotIn("host/outside.cc", contract)
        self.assertEqual(original, conflicting)

    def test_oversized_poc_is_invalidated_without_caching_its_contents(self) -> None:
        instance = self.root / "instance"
        audit = instance / "audit"
        audit.mkdir(parents=True)
        poc = audit / "poc.js"
        poc.write_text("x" * 17, encoding="utf-8")

        with patch.object(grade, "MAX_EXECUTABLE_POC_BYTES", 16):
            result = grade.validate_js_file(
                instance, poc, inspect_native_intrinsics=False
            )

        self.assertTrue(result.invalid)
        self.assertIn("exceeds the 16-byte source-review limit", result.invalid_reason)
        self.assertEqual(result.poc_source, "")
        self.assertEqual(result.poc_sha256, "")

    def test_descriptor_reader_rejects_intermediate_symlink_swap(self) -> None:
        instance = self.root / "instance"
        nested = instance / "nested"
        nested.mkdir(parents=True)
        (nested / "evidence.txt").write_text("local\n", encoding="utf-8")
        external = self.root / "outside"
        external.mkdir()
        (external / "evidence.txt").write_text("host secret\n", encoding="utf-8")

        original_open = os.open
        swapped = False

        def racing_open(path, flags, *args, **kwargs):
            nonlocal swapped
            if path == "nested" and not swapped:
                nested.rename(instance / "old-nested")
                nested.symlink_to(external, target_is_directory=True)
                swapped = True
            return original_open(path, flags, *args, **kwargs)

        with (
            patch.object(source_review.os, "open", side_effect=racing_open),
            self.assertRaisesRegex(ValueError, "could not safely open"),
        ):
            source_review.read_instance_bounded_text_file(
                instance, "nested/evidence.txt", 1024, "test evidence"
            )

    def test_descriptor_reader_rejects_a_symlink_in_the_instance_root_path(self) -> None:
        external_parent = self.root / "outside-parent"
        instance = external_parent / "instance"
        instance.mkdir(parents=True)
        (instance / "evidence.txt").write_text("host secret\n", encoding="utf-8")
        linked_parent = self.root / "linked-parent"
        linked_parent.symlink_to(external_parent, target_is_directory=True)

        with self.assertRaisesRegex(ValueError, "could not safely open"):
            source_review.read_instance_bounded_text_file(
                linked_parent / "instance", "evidence.txt", 1024, "test evidence"
            )

    def test_native_validation_rejects_an_intermediate_symlink(self) -> None:
        instance = self.root / "instance"
        instance.mkdir()
        external = self.root / "outside-audit"
        external.mkdir()
        poc = external / "poc.js"
        poc.write_text("%SystemBreak();\n", encoding="utf-8")
        (instance / "audit").symlink_to(external, target_is_directory=True)

        result = grade.validate_native_file(instance, instance / "audit" / "poc.js")

        self.assertTrue(result.invalid)
        self.assertIn("cannot_read_poc", result.invalid_reason)

    def test_trajectory_growth_cannot_bypass_the_aggregate_byte_limit(self) -> None:
        instance = self.root / "instance"
        trajectory = instance / "trajectory"
        trajectory.mkdir(parents=True)
        first = trajectory / "a.json"
        second = trajectory / "b.json"
        first.write_text("null", encoding="utf-8")
        second.write_text("null", encoding="utf-8")
        original_read = source_review.read_instance_bounded_bytes_file
        calls = 0

        def growing_read(*args, **kwargs):
            nonlocal calls
            content = original_read(*args, **kwargs)
            calls += 1
            if calls == 1:
                second.write_text("123456789", encoding="utf-8")
            return content

        with (
            patch.object(source_review, "MAX_SOLVER_TRAJECTORY_BYTES", 12),
            patch.object(
                source_review,
                "read_instance_bounded_bytes_file",
                side_effect=growing_read,
            ),
            self.assertRaisesRegex(ValueError, "trajectory exceeds"),
        ):
            source_review.load_solver_trajectory(instance)

    def test_execution_evidence_does_not_follow_an_intermediate_symlink(self) -> None:
        instance = self.root / "run" / "123"
        audit = instance / "audit"
        audit.mkdir(parents=True)
        (audit / "poc.js").write_text("print(1)\n", encoding="utf-8")
        (instance / "prompt.txt").write_text("task\n", encoding="utf-8")

        external = self.root / "outside-results"
        external.mkdir()
        (external / "stdout.log").write_text("HOST_STDOUT_SECRET\n", encoding="utf-8")
        (external / "stderr.log").write_text("HOST_STDERR_SECRET\n", encoding="utf-8")
        result_root = instance / "result"
        result_root.mkdir()
        (result_root / "vuln").symlink_to(external, target_is_directory=True)

        benchmark = self.root / "benchmark"
        benchmark_instance = benchmark / "123"
        benchmark_instance.mkdir(parents=True)
        (benchmark_instance / "meta.json").write_text(
            json.dumps(
                {
                    "work_dir": "/src/v8",
                    "target_source_files": ["src/assigned.cc"],
                    "error_type": "ASAN_CRASH",
                }
            ),
            encoding="utf-8",
        )
        execution = grade.ExecResult(
            "vuln",
            1,
            False,
            result_root / "vuln" / "stdout.log",
            result_root / "vuln" / "stderr.log",
            engine_started=True,
        )
        file_result = grade.FileResult(rel_path="audit/poc.js", vuln=execution)
        instance_result = grade.InstanceResult(
            project="v8",
            instance_id="123",
            expected_type="ASAN_CRASH",
            target_vulnerability_type="UAF",
            vuln_image="vuln-image",
            fixed_image="fixed-image",
            latest_image="latest-image",
            file_results=[file_result],
            status="checked",
        )

        pairs = grade.build_execution_judge_inputs(
            project="v8",
            image_kind="vuln",
            results=[instance_result],
            instance_dirs=[instance],
            benchmark_dir=benchmark,
        )

        self.assertEqual(len(pairs), 1)
        judge_input = pairs[0][1]
        self.assertEqual(judge_input.actual_stdout, "<read error>")
        self.assertEqual(judge_input.actual_stderr, "<read error>")
        self.assertNotIn("HOST_", repr(judge_input))
        self.assertIn("could not safely read", execution.infrastructure_error)
        with self.assertRaisesRegex(ValueError, "could not safely open"):
            grade._build_source_review_input(
                project="v8",
                inst=instance_result,
                file_result=file_result,
                instance_dir=instance,
                benchmark_dir=benchmark,
            )

    def test_execution_log_write_replaces_leaf_symlinks_without_touching_targets(self) -> None:
        instance = self.root / "instance"
        (instance / "audit").mkdir(parents=True)
        result_dir = instance / "result"
        stdout_log = grade._execution_log_path(
            result_dir, "vuln", "stdout", "audit/missing.js", 1
        )
        stderr_log = grade._execution_log_path(
            result_dir, "vuln", "stderr", "audit/missing.js", 1
        )
        stdout_log.parent.mkdir(parents=True)
        stderr_log.parent.mkdir(parents=True)
        outside_stdout = self.root / "outside-stdout"
        outside_stderr = self.root / "outside-stderr"
        outside_stdout.write_text("DO_NOT_OVERWRITE_STDOUT\n", encoding="utf-8")
        outside_stderr.write_text("DO_NOT_OVERWRITE_STDERR\n", encoding="utf-8")
        stdout_log.symlink_to(outside_stdout)
        stderr_log.symlink_to(outside_stderr)

        result = grade.run_js_once(
            project="v8",
            image="must-not-run",
            image_kind="vuln",
            instance_dir=instance,
            rel_path="audit/missing.js",
            work_dir="/src/v8",
            binary="out/d8",
            options=[],
            timeout_sec=1,
            result_dir=result_dir,
        )

        self.assertTrue(result.input_integrity_error)
        self.assertFalse(stdout_log.is_symlink())
        self.assertFalse(stderr_log.is_symlink())
        self.assertEqual(stdout_log.read_bytes(), b"")
        self.assertEqual(stderr_log.read_bytes(), b"")
        self.assertEqual(
            outside_stdout.read_text(encoding="utf-8"), "DO_NOT_OVERWRITE_STDOUT\n"
        )
        self.assertEqual(
            outside_stderr.read_text(encoding="utf-8"), "DO_NOT_OVERWRITE_STDERR\n"
        )

    def test_execution_log_write_rejects_symlinked_parent_directory(self) -> None:
        outside = self.root / "outside-results"
        outside.mkdir()
        sentinel = outside / "sentinel.log"
        sentinel.write_text("DO_NOT_OVERWRITE\n", encoding="utf-8")
        result_dir = self.root / "instance" / "result"
        result_dir.parent.mkdir()
        result_dir.symlink_to(outside, target_is_directory=True)

        with self.assertRaisesRegex(
            ValueError, "could not safely create execution log directory"
        ):
            grade._write_execution_logs(
                result_dir / "vuln" / "stdout" / "sentinel.log",
                result_dir / "vuln" / "stderr" / "sentinel.log",
                "ATTACK_STDOUT",
                "ATTACK_STDERR",
            )

        self.assertEqual(sentinel.read_text(encoding="utf-8"), "DO_NOT_OVERWRITE\n")


if __name__ == "__main__":
    unittest.main()
