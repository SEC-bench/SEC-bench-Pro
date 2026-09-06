"""Regression coverage for the established Linux grading interfaces."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness"))

import common  # noqa: E402
import grade  # noqa: E402
import judge  # noqa: E402


LEGACY_SUMMARY_COLUMNS = [
    "project",
    "instance_id",
    "status",
    "poc_total",
    "expected_type",
    "target_vulnerability_type",
    "success",
    "verified_pocs",
    "unsure_pocs",
    "illegal_pocs",
    "invalid_pocs",
    "vuln_image",
    "fixed_image",
    "latest_image",
    "notes",
]
LEGACY_EXECUTION_COLUMNS = [
    "instance_id",
    "poc_rel_path",
    "image_kind",
    "exit_code",
    "timed_out",
    "stdout_log",
    "stderr_log",
]


class LinuxCompatibilityTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.run_dir = self.root / "run"
        self.benchmark_dir = self.root / "benchmark"
        self.run_dir.mkdir()
        self.benchmark_dir.mkdir()
        common.clear_js_grading_budget()
        self.addCleanup(common.clear_js_grading_budget)

    @staticmethod
    def _execution(instance_dir: Path, kind: str) -> grade.ExecResult:
        logs = instance_dir / "result" / kind
        logs.mkdir(parents=True, exist_ok=True)
        stdout = logs / "stdout.log"
        stderr = logs / "stderr.log"
        stdout.write_text(f"{kind} stdout\n", encoding="utf-8")
        stderr.write_text(f"{kind} stderr\n", encoding="utf-8")
        return grade.ExecResult(kind, 0, False, stdout, stderr, engine_started=True)

    def _result(self, instance_dir: Path) -> grade.InstanceResult:
        candidate = grade.FileResult(
            "audit/poc.c",
            vuln=self._execution(instance_dir, "vuln"),
            fixed=self._execution(instance_dir, "fixed"),
            latest=self._execution(instance_dir, "latest"),
        )
        return grade.InstanceResult(
            project="linux",
            instance_id=instance_dir.name,
            expected_type="KASAN_CRASH",
            target_vulnerability_type="USE_AFTER_FREE",
            vuln_image="vuln:image",
            fixed_image="fixed:image",
            latest_image="latest:image",
            vuln_image_id="sha256:" + "a" * 64,
            fixed_image_id="sha256:" + "b" * 64,
            latest_image_id="sha256:" + "c" * 64,
            poc_total=1,
            file_results=[candidate],
            status="checked",
            notes="legacy note",
        )

    def test_all_oversized_checked_in_reference_pocs_survive_seeded_judge_input(self) -> None:
        references = sorted(
            path
            for path in (ROOT / "projects" / "linux").glob("*/poc/poc.c")
            if path.stat().st_size > grade.MAX_EXECUTABLE_POC_BYTES
        )
        self.assertEqual(len(references), 9)

        results: list[grade.InstanceResult] = []
        instance_dirs: list[Path] = []
        expected_prefixes: dict[str, str] = {}
        for reference in references:
            instance_id = reference.parents[1].name
            instance_dir = self.run_dir / instance_id
            audit = instance_dir / "audit"
            audit.mkdir(parents=True)
            # This is the on-disk layout produced by seed_reference_poc.
            shutil.copyfile(reference, audit / "poc.c")
            with reference.open(encoding="utf-8", errors="replace") as handle:
                expected_prefixes[instance_id] = handle.read(256)
            results.append(self._result(instance_dir))
            instance_dirs.append(instance_dir)

        pairs = grade.build_judge_inputs(
            project="linux",
            results=results,
            instance_dirs=instance_dirs,
            benchmark_dir=self.benchmark_dir,
        )

        self.assertEqual(len(pairs), len(references))
        for file_result, judge_input in pairs:
            self.assertIsNone(file_result.verdict)
            self.assertTrue(
                judge_input.poc_source.startswith(
                    expected_prefixes[judge_input.instance_id]
                )
            )
            self.assertLessEqual(len(judge_input.poc_source), judge.MAX_POC_CHARS)
            self.assertIn("truncated after bounded prefix", judge_input.poc_source)

    def test_unsafe_linux_poc_read_becomes_a_per_file_grader_error(self) -> None:
        instance_dir = self.run_dir / "CVE-test"
        audit = instance_dir / "audit"
        audit.mkdir(parents=True)
        outside = self.root / "outside-poc.c"
        outside.write_text("host data must not be read\n", encoding="utf-8")
        (audit / "poc.c").symlink_to(outside)
        result = self._result(instance_dir)
        (audit / "good.c").write_text("int main(void) { return 0; }\n")
        original = result.file_results[0]
        result.file_results.append(
            grade.FileResult(
                "audit/good.c",
                vuln=original.vuln,
                fixed=original.fixed,
                latest=original.latest,
            )
        )
        result.poc_total = 2

        pairs = grade.build_judge_inputs(
            project="linux",
            results=[result],
            instance_dirs=[instance_dir],
            benchmark_dir=self.benchmark_dir,
        )

        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0][0].rel_path, "audit/good.c")
        candidate = result.file_results[0]
        self.assertEqual(candidate.outcome, "error")
        self.assertEqual(candidate.verdict.decision_step, "linux_judge_input")
        self.assertIn("safely prepare Linux judge input", candidate.verdict.reason)
        self.assertFalse(result.grading_complete)

    def test_linux_judge_excerpt_is_not_limited_by_the_js_evidence_cap(self) -> None:
        instance_dir = self.run_dir / "CVE-test"
        audit = instance_dir / "audit"
        audit.mkdir(parents=True)
        (audit / "poc.c").write_text("int main(void) {}\n", encoding="utf-8")
        result = self._result(instance_dir)
        result.expected_type = "KASAN_UAF"
        execution = result.file_results[0].vuln
        assert execution is not None
        marker = "BUG: KASAN: use-after-free"
        raw_stderr = (
            "head\n"
            + "x" * (grade.MAX_COMMAND_OUTPUT_CHARS // 2)
            + marker
            + "y" * (grade.MAX_COMMAND_OUTPUT_CHARS // 2)
            + "\ntail\n"
        )
        execution.stderr_log.write_text(raw_stderr, encoding="utf-8")
        execution.stderr_sha256 = hashlib.sha256(raw_stderr.encode()).hexdigest()

        with patch.object(
            grade.source_review_module, "MAX_EXECUTION_EVIDENCE_BYTES", 64
        ):
            pairs = grade.build_judge_inputs(
                project="linux",
                results=[result],
                instance_dirs=[instance_dir],
                benchmark_dir=self.benchmark_dir,
            )

        self.assertEqual(len(pairs), 1)
        self.assertIn(marker, pairs[0][1].vuln_stderr)
        self.assertEqual(execution.stderr_log.read_text(encoding="utf-8"), raw_stderr)

    def test_linux_output_streams_complete_logs_while_js_capture_stays_bounded(self) -> None:
        command = [
            sys.executable,
            "-c",
            "import sys; sys.stdout.write('HEAD' + 'x' * 400 + 'TAIL')",
        ]
        with patch.object(grade, "MAX_COMMAND_OUTPUT_CHARS", 100):
            capped = grade.run_interruptible_command(command, timeout_sec=10)
        self.assertIn("host capture truncated", capped.stdout)

        stdout_log = self.root / "streamed" / "stdout.log"
        stderr_log = self.root / "streamed" / "stderr.log"
        payload_chars = grade.MAX_COMMAND_OUTPUT_CHARS + 123
        streamed = grade.run_interruptible_command_to_logs(
            [
                sys.executable,
                "-c",
                (
                    "import sys; "
                    f"sys.stdout.buffer.write(b'H' + b'x' * {payload_chars} "
                    "+ b'\\xff\\r\\nT'); "
                    "sys.stderr.buffer.write(b'complete\\xff stderr')"
                ),
            ],
            stdout_log=stdout_log,
            stderr_log=stderr_log,
            timeout_sec=10,
        )

        self.assertEqual(stdout_log.stat().st_size, payload_chars + 5)
        with stdout_log.open("rb") as handle:
            self.assertEqual(handle.read(1), b"H")
            handle.seek(-4, 2)
            self.assertEqual(handle.read(), b"\xff\r\nT")
        self.assertEqual(stderr_log.read_bytes(), b"complete\xff stderr")
        self.assertEqual(
            streamed.stdout_sha256,
            hashlib.sha256(stdout_log.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            streamed.stderr_sha256,
            hashlib.sha256(stderr_log.read_bytes()).hexdigest(),
        )

    def test_linux_execution_uses_disk_streaming_and_records_its_digests(self) -> None:
        instance_dir = self.run_dir / "CVE-test"
        (instance_dir / "audit").mkdir(parents=True)
        (instance_dir / "audit" / "poc.c").write_text("int main(void) {}\n")
        benchmark_instance = self.benchmark_dir / "CVE-test"
        benchmark_instance.mkdir()
        expected_stdout = "complete stdout"
        expected_stderr = "complete stderr"

        stream_calls = 0

        def stream_command(_command: list[str], **kwargs: object):
            nonlocal stream_calls
            stream_calls += 1
            stdout_log = kwargs["stdout_log"]
            stderr_log = kwargs["stderr_log"]
            assert isinstance(stdout_log, Path)
            assert isinstance(stderr_log, Path)
            stdout = "a" * 64 + "\n" if stream_calls == 1 else expected_stdout
            stderr = "" if stream_calls == 1 else expected_stderr
            grade._replace_execution_log(stdout_log, stdout.encode())
            grade._replace_execution_log(stderr_log, stderr.encode())
            return grade.StreamedCommandResult(
                0,
                False,
                hashlib.sha256(stdout.encode()).hexdigest(),
                hashlib.sha256(stderr.encode()).hexdigest(),
            )

        with (
            patch.object(
                grade,
                "run_interruptible_command_to_logs",
                side_effect=stream_command,
            ) as streamed,
            patch.object(common, "require_linux_kvm", return_value=True),
            patch.object(common, "setup_linux_evaluation_container"),
            patch.object(grade, "add_container"),
            patch.object(grade, "discard_container"),
            patch.object(grade, "_force_remove_container", return_value=True),
        ):
            execution = grade.run_linux_once(
                project="linux",
                image="linux:image",
                image_kind="vuln",
                instance_dir=instance_dir,
                rel_path="audit/poc.c",
                benchmark_instance_dir=benchmark_instance,
                secb_config_content="[kernel]\n",
                timeout_sec=10,
                result_dir=instance_dir / "result",
            )

        self.assertEqual(streamed.call_count, 2)
        self.assertEqual(execution.stdout_log.read_text(encoding="utf-8"), expected_stdout)
        self.assertEqual(execution.stderr_log.read_text(encoding="utf-8"), expected_stderr)
        self.assertEqual(
            execution.stdout_sha256,
            hashlib.sha256(expected_stdout.encode()).hexdigest(),
        )
        self.assertEqual(
            execution.stderr_sha256,
            hashlib.sha256(expected_stderr.encode()).hexdigest(),
        )

    def test_linux_input_error_is_terminal_and_replaces_stale_judge_artifacts(self) -> None:
        instance_dir = self.run_dir / "CVE-test"
        audit = instance_dir / "audit"
        audit.mkdir(parents=True)
        outside = self.root / "outside-poc.c"
        outside.write_text("untrusted host source\n")
        (audit / "poc.c").symlink_to(outside)
        result = self._result(instance_dir)

        judge_dir = instance_dir / "result" / "judge"
        judge_dir.mkdir(parents=True)
        stem = grade._safe_judge_filename("audit/poc.c")
        stale_prompt = judge_dir / f"{stem}.prompt.md"
        stale_verdict = judge_dir / f"{stem}.verdict.json"
        stale_prompt.write_text("stale prompt\n")
        stale_verdict.write_text('{"outcome":"verified"}\n')

        with (
            patch.object(grade, "_print"),
            patch.object(common, "docker_preflight"),
            patch.object(grade, "ensure_image", return_value=True),
            patch.object(judge, "check_api_key", return_value=True),
            patch.object(
                grade, "resolve_timestamp_dirs", return_value=[self.run_dir]
            ),
            patch.object(
                grade, "collect_instance_dirs", return_value=[instance_dir]
            ),
            patch.object(grade, "grade_instances", return_value=[result]),
            patch.object(judge, "judge_all") as judge_all,
        ):
            exit_code = grade.main(
                [
                    "--project",
                    "linux",
                    "--target-dir",
                    str(self.run_dir),
                    "--benchmark-dir",
                    str(self.benchmark_dir),
                    "--latest-image",
                    "latest:image",
                    "--judge-model",
                    "fake",
                ]
            )

        self.assertEqual(exit_code, 1)
        judge_all.assert_not_called()
        self.assertFalse(stale_prompt.exists())
        per_instance = json.loads(stale_verdict.read_text())
        self.assertEqual(per_instance["outcome"], "error")
        self.assertEqual(per_instance["decision_step"], "linux_judge_input")
        self.assertEqual(per_instance["total_tokens"], 0)

        out_dir = self.run_dir / "summary"
        with (out_dir / "judge_verdicts.csv").open(
            newline="", encoding="utf-8"
        ) as handle:
            verdict_rows = list(csv.DictReader(handle))
        self.assertEqual(len(verdict_rows), 1)
        self.assertEqual(verdict_rows[0]["outcome"], "error")
        self.assertEqual(verdict_rows[0]["decision_step"], "linux_judge_input")

        details = json.loads((out_dir / "judge_verdicts.json").read_text())
        self.assertEqual(len(details), 1)
        self.assertEqual(details[0]["outcome"], "error")
        usage = json.loads((out_dir / "judge_usage.json").read_text())
        self.assertEqual(usage["total_requests"], 1)
        self.assertEqual(usage["successful_requests"], 0)
        self.assertEqual(usage["failed_requests"], 1)
        self.assertEqual(usage["token_usage"]["total_tokens"], 0)
        self.assertEqual(usage["cost"]["total_usd"], 0.0)

    def test_global_csvs_keep_legacy_columns_in_their_original_positions(self) -> None:
        instance_dir = self.run_dir / "CVE-test"
        (instance_dir / "audit").mkdir(parents=True)
        result = self._result(instance_dir)
        out_dir = self.root / "summary"

        grade.write_global_csvs(self.run_dir, [result], out_dir)

        with (out_dir / "summary.csv").open(newline="", encoding="utf-8") as handle:
            summary_rows = list(csv.reader(handle))
        self.assertEqual(summary_rows[0][: len(LEGACY_SUMMARY_COLUMNS)], LEGACY_SUMMARY_COLUMNS)
        self.assertEqual(
            summary_rows[0][len(LEGACY_SUMMARY_COLUMNS) :],
            [
                "error_pocs",
                "grading_complete",
                "vuln_image_id",
                "fixed_image_id",
                "latest_image_id",
            ],
        )
        self.assertEqual(summary_rows[1][11:15], [
            "vuln:image", "fixed:image", "latest:image", "legacy note"
        ])

        with (out_dir / "executions.csv").open(newline="", encoding="utf-8") as handle:
            execution_rows = list(csv.reader(handle))
        self.assertEqual(
            execution_rows[0][: len(LEGACY_EXECUTION_COLUMNS)],
            LEGACY_EXECUTION_COLUMNS,
        )
        self.assertEqual(
            execution_rows[0][len(LEGACY_EXECUTION_COLUMNS) :],
            [
                "engine_started",
                "oom_killed",
                "infrastructure_error",
                "infrastructure_kind",
                "input_integrity_error",
                "input_tree_sha256",
                "stdout_sha256",
                "stderr_sha256",
            ],
        )
        self.assertEqual(execution_rows[1][0:5], [
            "CVE-test", "audit/poc.c", "vuln", "0", "no"
        ])
        self.assertTrue(execution_rows[1][5].endswith("result/vuln/stdout.log"))
        self.assertTrue(execution_rows[1][6].endswith("result/vuln/stderr.log"))


if __name__ == "__main__":
    unittest.main()
