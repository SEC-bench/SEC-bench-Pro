"""Offline regression tests for incomplete grading and per-file isolation."""

from __future__ import annotations

import contextlib
import csv
import hashlib
import io
import json
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "harness"))

import grade
import judge
import source_review


class GradingErrorTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.instance_dir = self.root / "run" / "123"
        self.benchmark_dir = self.root / "bench"
        benchmark = self.benchmark_dir / "123"
        (self.instance_dir / "audit").mkdir(parents=True)
        (self.instance_dir / "result").mkdir()
        (benchmark / "patches").mkdir(parents=True)
        (benchmark / "meta.json").write_text(json.dumps({
            "work_dir": "/src/example",
            "verification_binary": "engine",
            "command_options": "",
            "target_source_files": ["src/example.cc"],
        }))
        (benchmark / "patches" / "fix.patch").write_text("historical context\n")
        (self.instance_dir / "prompt.txt").write_text("original task\n")
        self.instance = grade.InstanceResult(
            "v8", "123", "ERROR", "TYPE", "vuln", "fixed", "latest", status="checked"
        )
        self.judgments = {"vuln": True, "fixed": False, "latest": False}
        self.fixed_results: dict[str, grade.ExecResult | Exception] = {}
        self.review_result: bool | None = True
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(grade, "_print"))
        self.stack.enter_context(patch.object(grade, "ensure_image", return_value=True))
        self.stack.enter_context(
            patch.object(grade, "pin_image_id", return_value="sha256:" + "a" * 64)
        )
        self.runner = self.stack.enter_context(
            patch.object(grade, "run_js_with_retries", side_effect=self.run_image)
        )
        self.execution_judge = self.stack.enter_context(
            patch.object(judge, "judge_execution_all", side_effect=self.judge_images)
        )
        self.reviewer = self.stack.enter_context(
            patch.object(source_review, "review_single", side_effect=self.review)
        )

    def execution(
        self,
        kind: str,
        code: int | None,
        timed_out: bool = False,
        *,
        engine_started: bool = True,
        oom_killed: bool = False,
        infrastructure_error: str = "",
        infrastructure_kind: str = "",
    ) -> grade.ExecResult:
        stdout = self.instance_dir / "result" / "stdout.log"
        stderr = self.instance_dir / "result" / "stderr.log"
        stdout.write_text("")
        stderr.write_text("synthetic execution evidence")
        return grade.ExecResult(
            kind,
            code,
            timed_out,
            stdout,
            stderr,
            engine_started,
            oom_killed,
            infrastructure_error,
            infrastructure_kind=infrastructure_kind,
        )

    def add_file(
        self,
        name: str = "poc.js",
        code: int | None = 1,
        timed_out: bool = False,
        *,
        engine_started: bool = True,
        oom_killed: bool = False,
        infrastructure_error: str = "",
        infrastructure_kind: str = "",
    ) -> grade.FileResult:
        path = self.instance_dir / "audit" / name
        path.write_text("print(1)\n")
        result = grade.FileResult(
            f"audit/{name}",
            vuln=self.execution(
                "vuln",
                code,
                timed_out,
                engine_started=engine_started,
                oom_killed=oom_killed,
                infrastructure_error=infrastructure_error,
                infrastructure_kind=infrastructure_kind,
            ),
        )
        self.instance.file_results.append(result)
        self.instance.poc_total += 1
        return result

    def run_image(self, **kwargs: object) -> grade.ExecResult:
        kind = str(kwargs["image_kind"])
        result = self.fixed_results.get(str(kwargs["rel_path"])) if kind == "fixed" else None
        if isinstance(result, Exception):
            raise result
        return result if result is not None else self.execution(kind, 0)

    def judge_images(self, inputs: list[judge.ExecutionJudgeInput], **_kwargs: object):
        return [judge.ExecutionJudgeVerdict(
            inp.project, inp.instance_id, inp.poc_rel_path, inp.image_kind,
            self.judgments[inp.image_kind], "synthetic execution judgment", "fake",
            error="API unavailable" if self.judgments[inp.image_kind] is None else "",
        ) for inp in inputs]

    def review(self, inp: source_review.SourceReviewInput, **_kwargs: object):
        return source_review.SourceReviewVerdict(
            inp.project, inp.instance_id, inp.poc_rel_path, self.review_result,
            "synthetic source judgment", "fake",
            error="review unavailable" if self.review_result is None else "",
            tool_calls=1,
        )

    def adjudicate(self, latest: bool = False):
        return grade.adjudicate_js_results(
            project=self.instance.project, results=[self.instance],
            instance_dirs=[self.instance_dir], benchmark_dir=self.benchmark_dir,
            latest_enabled=latest, timeout_sec=1, attempts=1, execution_workers=2,
            judge_workers=1, pull_missing=False, model="fake",
        )

    def test_vulnerable_launch_failures_are_errors_regardless_of_model_verdict(self) -> None:
        for project in ("v8", "sm"):
            for code in (None, 125, 126, 127):
                for reproduced in (True, False, None):
                    with self.subTest(project=project, code=code, reproduced=reproduced):
                        self.instance.project = project
                        self.instance.file_results.clear()
                        candidate = self.add_file(
                            code=code,
                            engine_started=False,
                            infrastructure_error="synthetic launch failure",
                        )
                        self.judgments["vuln"] = reproduced
                        self.adjudicate(latest=True)
                        self.assertEqual(candidate.outcome, "error")
                        self.assertEqual(candidate.verdict.decision_step, "vulnerable_execution")
                        self.assertTrue(candidate.verdict.error)
        self.runner.assert_not_called()
        self.reviewer.assert_not_called()

    def test_engine_reserved_exit_codes_are_not_launch_failures(self) -> None:
        for code in (124, 125, 126, 127):
            with self.subTest(code=code):
                self.instance.file_results.clear()
                candidate = self.add_file(code=code)
                self.judgments["vuln"] = False
                self.adjudicate()
                self.assertEqual(candidate.outcome, "illegal")
                self.assertEqual(candidate.verdict.decision_step, "vulnerable_execution")
                self.assertFalse(candidate.verdict.error)
        self.runner.assert_not_called()

    def test_vulnerable_hard_gate_also_stops_latest_diagnostics(self) -> None:
        self.judgments["vuln"] = None
        for code, timed_out, oom_killed in [
            (0, False, False),
            (137, True, False),
            (137, False, True),
        ]:
            with self.subTest(
                code=code, timed_out=timed_out, oom_killed=oom_killed
            ):
                self.instance.file_results.clear()
                candidate = self.add_file(
                    code=code,
                    timed_out=timed_out,
                    oom_killed=oom_killed,
                )
                self.adjudicate(latest=True)
                self.assertEqual(candidate.outcome, "illegal")
                self.assertEqual(candidate.verdict.decision_step, "vulnerable_execution")
                self.assertFalse(candidate.verdict.error)
        self.execution_judge.assert_not_called()
        self.runner.assert_not_called()
        self.reviewer.assert_not_called()

    def test_vulnerable_infrastructure_error_precedes_exit_and_timeout_gates(self) -> None:
        self.judgments["vuln"] = None
        for code, timed_out in [(0, False), (137, True)]:
            with self.subTest(code=code, timed_out=timed_out):
                self.instance.file_results.clear()
                candidate = self.add_file(
                    code=code,
                    timed_out=timed_out,
                    engine_started=True,
                    infrastructure_error="engine runner/container status mismatch",
                )
                self.adjudicate(latest=True)
                self.assertEqual(candidate.outcome, "error")
                self.assertEqual(candidate.verdict.decision_step, "vulnerable_execution")
                self.assertIn("status mismatch", candidate.verdict.error)
        self.execution_judge.assert_not_called()
        self.runner.assert_not_called()
        self.reviewer.assert_not_called()

    def test_vulnerable_oom_precedes_infrastructure_error(self) -> None:
        self.judgments["vuln"] = None
        candidate = self.add_file(
            code=137,
            engine_started=True,
            oom_killed=True,
            infrastructure_error="container state also reported an error",
        )
        self.adjudicate(latest=True)
        self.assertEqual(candidate.outcome, "illegal")
        self.assertEqual(candidate.verdict.decision_step, "vulnerable_execution")
        self.assertFalse(candidate.verdict.error)
        self.execution_judge.assert_not_called()
        self.runner.assert_not_called()
        self.reviewer.assert_not_called()

    def test_fixed_worker_error_does_not_discard_a_clean_sibling(self) -> None:
        good = self.add_file("good.js")
        failed = self.add_file("failed.js")
        self.fixed_results[failed.rel_path] = OSError("worker unavailable")
        self.adjudicate()
        self.assertEqual(self.instance.status, "checked")
        self.assertEqual(good.outcome, "verified")
        self.assertEqual(good.verdict.decision_step, "fixed_execution")
        self.assertEqual(failed.outcome, "error")
        self.assertEqual(failed.verdict.decision_step, "fixed_execution")
        self.assertTrue(self.instance.success)

    def test_fixed_lifecycle_failures_reach_source_review_without_a_judge(self) -> None:
        lifecycle_results = [
            self.execution("fixed", 137, True),
            self.execution("fixed", 137, oom_killed=True),
            self.execution(
                "fixed",
                None,
                engine_started=False,
                infrastructure_error="could not launch engine",
                infrastructure_kind="engine_launch",
            ),
        ]
        for project in ("v8", "sm"):
            for fixed_result in lifecycle_results:
                with self.subTest(
                    project=project,
                    code=fixed_result.exit_code,
                    timed_out=fixed_result.timed_out,
                    oom_killed=fixed_result.oom_killed,
                    infrastructure_error=fixed_result.infrastructure_error,
                ):
                    self.instance.project = project
                    self.instance.file_results.clear()
                    self.execution_judge.reset_mock()
                    self.reviewer.reset_mock()
                    candidate = self.add_file()
                    self.fixed_results[candidate.rel_path] = fixed_result
                    self.judgments.update(vuln=True, fixed=None)
                    self.review_result = False
                    self.adjudicate()
                    self.assertEqual(candidate.outcome, "illegal")
                    self.assertEqual(candidate.verdict.decision_step, "source_review")
                    judged_kinds = [
                        [item.image_kind for item in call.args[0]]
                        for call in self.execution_judge.call_args_list
                    ]
                    self.assertEqual(judged_kinds, [["vuln"]])
                    self.reviewer.assert_called_once()

    def test_fixed_grader_infrastructure_failure_is_a_terminal_error(self) -> None:
        candidate = self.add_file()
        self.fixed_results[candidate.rel_path] = self.execution(
            "fixed",
            1,
            infrastructure_error="container state unavailable",
            infrastructure_kind="docker_inspect",
        )
        self.judgments["vuln"] = True

        self.adjudicate()

        self.assertEqual(candidate.outcome, "error")
        self.assertEqual(candidate.verdict.decision_step, "fixed_execution")
        self.assertIn("docker_inspect", candidate.verdict.error)
        judged_kinds = [
            [item.image_kind for item in call.args[0]]
            for call in self.execution_judge.call_args_list
        ]
        self.assertEqual(judged_kinds, [["vuln"]])
        self.reviewer.assert_not_called()

    def test_fixed_nonzero_execution_is_judged_before_source_review(self) -> None:
        candidate = self.add_file()
        self.fixed_results[candidate.rel_path] = self.execution("fixed", 125)
        self.judgments.update(vuln=True, fixed=False)
        self.review_result = False
        self.adjudicate()
        self.assertEqual(candidate.outcome, "illegal")
        self.assertEqual(candidate.verdict.decision_step, "source_review")
        judged_kinds = [
            [item.image_kind for item in call.args[0]]
            for call in self.execution_judge.call_args_list
        ]
        self.assertEqual(judged_kinds, [["vuln"], ["fixed"]])

    def test_source_review_error_remains_an_error(self) -> None:
        candidate = self.add_file()
        self.fixed_results[candidate.rel_path] = self.execution("fixed", 1)
        self.review_result = None
        self.adjudicate()
        self.assertEqual(candidate.outcome, "error")
        self.assertEqual(candidate.verdict.decision_step, "source_review")

    def test_latest_judge_failure_does_not_change_score(self) -> None:
        candidate = self.add_file()
        self.judgments["latest"] = None
        self.adjudicate(latest=True)
        self.assertEqual(candidate.outcome, "verified")
        self.assertEqual(candidate.verdict.error, "")
        self.assertIsNone(candidate.execution_verdicts["latest"].reproduced)

    def test_latest_budget_failure_runs_after_and_cannot_erase_source_score(self) -> None:
        events: list[str] = []
        candidate = self.add_file()
        self.fixed_results[candidate.rel_path] = self.execution("fixed", 1)
        self.judgments.update(vuln=True, fixed=True)
        self.review_result = True

        def run_image(**kwargs: object) -> grade.ExecResult:
            image_kind = str(kwargs["image_kind"])
            if image_kind == "latest":
                events.append("latest")
                raise grade.common.JsGradingBudgetExceeded(
                    "synthetic diagnostic deadline"
                )
            return self.execution(image_kind, 1)

        def review(inp: source_review.SourceReviewInput, **_kwargs: object):
            events.append("source_review")
            return source_review.SourceReviewVerdict(
                inp.project,
                inp.instance_id,
                inp.poc_rel_path,
                True,
                "assigned source is causal",
                "fake",
                tool_calls=1,
            )

        self.runner.side_effect = run_image
        self.reviewer.side_effect = review
        verdicts, pairs = self.adjudicate(latest=True)

        self.assertEqual(events, ["source_review", "latest"])
        self.assertEqual(candidate.outcome, "verified")
        self.assertEqual(candidate.verdict.decision_step, "source_review")
        self.assertEqual(candidate.verdict.error, "")
        self.assertEqual(pairs["latest"], [])
        self.assertEqual(sum(verdict.outcome == "error" for verdict in verdicts), 0)

    def test_latest_with_exhausted_call_budget_skips_before_engine_work(self) -> None:
        candidate = self.add_file()
        candidate.verdict = judge.JudgeVerdict(
            "v8", "123", candidate.rel_path, "verified", "scored", "fake"
        )
        grade.common.configure_js_grading_budget(
            time_budget_sec=60, llm_call_budget=1
        )
        self.addCleanup(grade.common.clear_js_grading_budget)
        grade.common.consume_js_llm_call("scoring test setup")
        pairs: dict[
            str, list[tuple[grade.FileResult, judge.ExecutionJudgeInput]]
        ] = {}

        diagnostic_started = grade.run_latest_diagnostic(
            project="v8",
            results=[self.instance],
            instance_dirs=[self.instance_dir],
            benchmark_dir=self.benchmark_dir,
            timeout_sec=1,
            attempts=1,
            execution_workers=1,
            judge_workers=1,
            pull_missing=False,
            model="fake",
            execution_pairs=pairs,
        )

        self.assertFalse(diagnostic_started)
        self.assertEqual(pairs["latest"], [])
        self.runner.assert_not_called()
        self.assertEqual(candidate.verdict.outcome, "verified")
        self.assertEqual(candidate.verdict.error, "")

    def test_execution_judge_failures_do_not_become_negative_submissions(self) -> None:
        for phase in ("vuln", "fixed"):
            with self.subTest(phase=phase):
                self.instance.file_results.clear()
                self.judgments.update(vuln=True, fixed=False)
                candidate = self.add_file()
                self.judgments[phase] = None
                self.adjudicate()
                self.assertEqual(candidate.outcome, "error")
        self.reviewer.assert_not_called()

    def test_expired_budget_skips_execution_evidence_io_and_becomes_error(self) -> None:
        candidate = self.add_file()
        grade.common.configure_js_grading_budget(
            time_budget_sec=60, llm_call_budget=1
        )
        self.addCleanup(grade.common.clear_js_grading_budget)
        with (
            patch.object(
                grade.common, "_js_grading_deadline", grade.time.monotonic() - 1
            ),
            patch.object(grade, "_task_statement") as read_task,
        ):
            pairs = grade.build_execution_judge_inputs(
                project="v8",
                image_kind="vuln",
                results=[self.instance],
                instance_dirs=[self.instance_dir],
                benchmark_dir=self.benchmark_dir,
            )
        self.assertEqual(len(pairs), 1)
        self.assertEqual(candidate.vuln.infrastructure_kind, "grading_budget")
        self.assertIn("wall-clock budget exhausted", candidate.vuln.infrastructure_error)
        read_task.assert_not_called()

    def test_cli_reports_incomplete_grading_and_persists_error(self) -> None:
        self.add_file(
            code=125,
            engine_started=False,
            infrastructure_error="synthetic launch failure",
        )
        self.judgments["vuln"] = False
        with (
            patch.object(grade.common, "docker_preflight"),
            patch.object(judge, "check_api_key", return_value=True),
            patch.object(grade, "grade_instances", return_value=[self.instance]),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            result = grade.main([
                "--project", "v8", "--target-dir", str(self.instance_dir.parent),
                "--benchmark-dir", str(self.benchmark_dir), "--latest-repo", "fake",
                "--judge-model", "fake",
            ])
        self.assertEqual(result, 1)
        verdicts = json.loads((self.instance_dir.parent / "summary" / "judge_verdicts.json").read_text())
        self.assertEqual(verdicts[0]["outcome"], "error")
        self.runner.assert_not_called()

    def test_js_shared_latest_image_check_is_deferred_until_after_scoring(self) -> None:
        candidate = self.add_file(code=0)
        with (
            patch.object(grade.common, "docker_preflight"),
            patch.object(judge, "check_api_key", return_value=True),
            patch.object(grade, "grade_instances", return_value=[self.instance]),
            patch.object(grade, "ensure_image") as ensure_latest,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            result = grade.main(
                [
                    "--project",
                    "v8",
                    "--target-dir",
                    str(self.instance_dir.parent),
                    "--benchmark-dir",
                    str(self.benchmark_dir),
                    "--latest-image",
                    "diagnostic:latest",
                    "--judge-model",
                    "fake",
                ]
            )
        self.assertEqual(result, 0)
        self.assertEqual(candidate.outcome, "illegal")
        ensure_latest.assert_not_called()

    def test_all_timestamp_scoring_precedes_latest_and_failure_preserves_scores(self) -> None:
        runs_root = self.root / "runs"
        timestamp_dirs = [
            runs_root / "20260901_000000",
            runs_root / "20260902_000000",
        ]
        instance_dirs = [timestamp / "123" for timestamp in timestamp_dirs]
        for instance_dir in instance_dirs:
            (instance_dir / "result").mkdir(parents=True)

        batches: dict[Path, list[grade.InstanceResult]] = {}
        expected_verdicts: list[judge.JudgeVerdict] = []
        for timestamp, instance_dir in zip(timestamp_dirs, instance_dirs):
            verdict = judge.JudgeVerdict(
                "v8",
                "123",
                "audit/poc.js",
                "verified",
                f"scored {timestamp.name}",
                "fake",
                decision_step="fixed_execution",
            )
            file_result = grade.FileResult("audit/poc.js", verdict=verdict)
            result = grade.InstanceResult(
                "v8",
                "123",
                "ERROR",
                "TYPE",
                "vuln",
                "fixed",
                "diagnostic:latest",
                poc_total=1,
                file_results=[file_result],
                status="checked",
            )
            batches[instance_dir] = [result]
            expected_verdicts.append(verdict)

        events: list[str] = []

        def collect(timestamp: Path, **_kwargs: object) -> list[Path]:
            return [timestamp / "123"]

        def grade_batch(**kwargs: object) -> list[grade.InstanceResult]:
            instance_dir = kwargs["dirs"][0]
            assert isinstance(instance_dir, Path)
            return batches[instance_dir]

        def score_batch(**kwargs: object):
            instance_dir = kwargs["instance_dirs"][0]
            assert isinstance(instance_dir, Path)
            self.assertFalse(kwargs["latest_enabled"])
            # Two scoring calls exactly consume the invocation budget. Under
            # the old per-timestamp ordering, first latest used the second call
            # and the second timestamp could no longer score.
            grade.common.consume_js_llm_call(
                f"scoring {instance_dir.parent.name}"
            )
            events.append(f"score:{instance_dir.parent.name}")
            result = batches[instance_dir][0]
            return [result.file_results[0].verdict], {"vuln": [], "fixed": []}

        def latest_batch(**kwargs: object) -> None:
            instance_dir = kwargs["instance_dirs"][0]
            assert isinstance(instance_dir, Path)
            events.append(f"latest:{instance_dir.parent.name}")
            grade.common.consume_js_llm_call(
                f"diagnostic {instance_dir.parent.name}"
            )

        with (
            patch.object(grade.common, "docker_preflight"),
            patch.object(judge, "check_api_key", return_value=True),
            patch.object(
                grade, "resolve_timestamp_dirs", return_value=timestamp_dirs
            ),
            patch.object(grade, "collect_instance_dirs", side_effect=collect),
            patch.object(grade, "grade_instances", side_effect=grade_batch),
            patch.object(grade, "adjudicate_js_results", side_effect=score_batch),
            patch.object(grade, "run_latest_diagnostic", side_effect=latest_batch),
            patch.object(grade, "write_per_instance_files_csv") as per_instance,
            patch.object(grade, "write_js_judge_artifacts") as js_artifacts,
            patch.object(grade, "write_global_csvs"),
            patch.object(judge, "write_judge_csv"),
            patch.object(judge, "write_judge_details_json"),
            patch.object(judge, "write_judge_usage"),
            patch.object(grade, "print_summary"),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            result = grade.main(
                [
                    "--project",
                    "v8",
                    "--target-dir",
                    str(runs_root),
                    "--benchmark-dir",
                    str(self.benchmark_dir),
                    "--latest-image",
                    "diagnostic:latest",
                    "--judge-model",
                    "fake",
                    "--js-llm-call-budget",
                    "2",
                ]
            )

        self.assertEqual(result, 0)
        self.assertEqual(
            events,
            [
                "score:20260901_000000",
                "score:20260902_000000",
                "latest:20260901_000000",
                "latest:20260902_000000",
            ],
        )
        self.assertTrue(all(verdict.outcome == "verified" for verdict in expected_verdicts))
        self.assertTrue(all(verdict.error == "" for verdict in expected_verdicts))
        # Both scoring snapshots existed before diagnostics. Diagnostic failure
        # cannot remove them or make the command fail.
        self.assertGreaterEqual(per_instance.call_count, 2)
        self.assertEqual(js_artifacts.call_count, 2)

    def test_artifacts_preserve_verdict_fields_without_duplicate_transcript(self) -> None:
        candidate = self.add_file()
        self.fixed_results[candidate.rel_path] = self.execution("fixed", 1)
        _, pairs = self.adjudicate()
        candidate.source_review.transcript.append(
            source_review.TerminalCall("read evidence", 1, 0, False, "evidence", "")
        )
        grade.write_js_judge_artifacts(
            execution_pairs=pairs, results=[self.instance], instance_dirs=[self.instance_dir]
        )
        stem = grade._safe_judge_filename(candidate.rel_path)
        folder = self.instance_dir / "result" / "judge"
        final = json.loads((folder / f"{stem}.verdict.json").read_text())
        self.assertEqual(final, asdict(candidate.verdict))
        source = json.loads((folder / f"{stem}.source-review.verdict.json").read_text())
        terminal = json.loads((folder / f"{stem}.source-review.terminal.json").read_text())
        self.assertNotIn("transcript", source)
        self.assertEqual(terminal, [asdict(call) for call in candidate.source_review.transcript])

    def test_source_review_receives_the_full_original_task(self) -> None:
        candidate = self.add_file()
        statement = "original task\n" + "x" * (judge.MAX_TASK_CHARS + 1)
        (self.instance_dir / "prompt.txt").write_text(statement)
        review = grade._build_source_review_input(
            project="v8", inst=self.instance, file_result=candidate,
            instance_dir=self.instance_dir, benchmark_dir=self.benchmark_dir,
        )
        self.assertTrue(
            review.task_statement.endswith(f"## Original task text\n\n{statement}\n")
        )
        self.assertIn("# Authoritative benchmark contract", review.task_statement)

    def test_task_statement_does_not_follow_a_host_symlink(self) -> None:
        prompt = self.instance_dir / "prompt.txt"
        secret = self.root / "host-secret.txt"
        secret.write_text("HOST_SECRET_MUST_NOT_LEAK\n")
        prompt.unlink()
        prompt.symlink_to(secret)
        meta = json.loads((self.benchmark_dir / "123" / "meta.json").read_text())
        with self.assertRaisesRegex(ValueError, "could not safely open"):
            grade._task_statement(self.instance_dir, meta)

    def test_source_review_uses_the_accepted_poc_snapshot_after_file_changes(self) -> None:
        candidate = self.add_file()
        accepted_source = (self.instance_dir / candidate.rel_path).read_text()
        candidate.poc_source = accepted_source
        candidate.poc_sha256 = hashlib.sha256(accepted_source.encode()).hexdigest()
        (self.instance_dir / candidate.rel_path).write_text("x" * 17)
        with patch.object(source_review, "MAX_POC_SOURCE_BYTES", 16):
            review = grade._build_source_review_input(
                project="v8",
                inst=self.instance,
                file_result=candidate,
                instance_dir=self.instance_dir,
                benchmark_dir=self.benchmark_dir,
            )
        self.assertEqual(review.poc_source, accepted_source)
        self.assertNotEqual(review.poc_source, "x" * 17)

    def test_vulnerable_log_change_is_terminal_evidence_error_without_llm(self) -> None:
        candidate = self.add_file()
        execution = candidate.vuln
        assert execution is not None
        execution.stdout_sha256 = hashlib.sha256(
            execution.stdout_log.read_bytes()
        ).hexdigest()
        execution.stderr_sha256 = hashlib.sha256(
            execution.stderr_log.read_bytes()
        ).hexdigest()
        execution.stderr_log.write_text("tampered after capture\n", encoding="utf-8")

        self.adjudicate()

        self.assertEqual(execution.infrastructure_kind, "evidence_read")
        self.assertIn("digest changed after capture", execution.infrastructure_error)
        self.assertEqual(candidate.outcome, "error")
        self.assertEqual(candidate.verdict.decision_step, "vulnerable_execution")
        self.assertIn("not authoritative", candidate.verdict.error)
        self.execution_judge.assert_not_called()
        self.runner.assert_not_called()
        self.reviewer.assert_not_called()

    def test_log_change_after_vulnerable_judge_fails_source_review_setup(self) -> None:
        candidate = self.add_file()
        execution = candidate.vuln
        assert execution is not None
        execution.stdout_sha256 = hashlib.sha256(
            execution.stdout_log.read_bytes()
        ).hexdigest()
        execution.stderr_sha256 = hashlib.sha256(
            execution.stderr_log.read_bytes()
        ).hexdigest()
        self.fixed_results[candidate.rel_path] = self.execution("fixed", 1)
        self.judgments.update(vuln=True, fixed=False)

        def judge_then_change_log(
            inputs: list[judge.ExecutionJudgeInput], **kwargs: object
        ) -> list[judge.ExecutionJudgeVerdict]:
            verdicts = self.judge_images(inputs, **kwargs)
            if inputs and inputs[0].image_kind == "vuln":
                execution.stderr_log.write_text(
                    "tampered after vulnerable judge\n", encoding="utf-8"
                )
            return verdicts

        self.execution_judge.side_effect = judge_then_change_log
        self.adjudicate()

        self.assertEqual(candidate.outcome, "error")
        self.assertEqual(candidate.verdict.decision_step, "source_review")
        self.assertIsNotNone(candidate.source_review)
        self.assertIsNone(candidate.source_review.in_scope)
        self.assertIn("digest changed after capture", candidate.source_review.error)
        self.assertIn("Source review setup failed", candidate.source_review.reason)
        self.reviewer.assert_not_called()

    def test_execution_hashes_are_preserved_in_review_and_csv_artifacts(self) -> None:
        candidate = self.add_file()
        execution = candidate.vuln
        assert execution is not None
        execution.stdout_sha256 = hashlib.sha256(
            execution.stdout_log.read_bytes()
        ).hexdigest()
        execution.stderr_sha256 = hashlib.sha256(
            execution.stderr_log.read_bytes()
        ).hexdigest()

        review = grade._build_source_review_input(
            project="v8",
            inst=self.instance,
            file_result=candidate,
            instance_dir=self.instance_dir,
            benchmark_dir=self.benchmark_dir,
        )
        self.assertEqual(
            review.poc_execution["stdout_sha256"], execution.stdout_sha256
        )
        self.assertEqual(
            review.poc_execution["stderr_sha256"], execution.stderr_sha256
        )

        out_dir = self.root / "hash-summary"
        grade.write_global_csvs(self.instance_dir.parent, [self.instance], out_dir)
        with (out_dir / "executions.csv").open(
            newline="", encoding="utf-8"
        ) as handle:
            row = next(csv.DictReader(handle))
        self.assertEqual(row["stdout_sha256"], execution.stdout_sha256)
        self.assertEqual(row["stderr_sha256"], execution.stderr_sha256)

    def test_source_review_inputs_are_built_lazily_per_worker(self) -> None:
        first = self.add_file("first.js")
        second = self.add_file("second.js")
        events: list[str] = []

        def build(**kwargs: object) -> source_review.SourceReviewInput:
            file_result = kwargs["file_result"]
            assert isinstance(file_result, grade.FileResult)
            events.append(f"build:{file_result.rel_path}")
            return source_review.SourceReviewInput(
                "v8",
                "123",
                file_result.rel_path,
                "vuln",
                "/src/v8",
                "task",
                "poc",
                {},
                {},
                "patch",
            )

        def review(
            inp: source_review.SourceReviewInput, **_kwargs: object
        ) -> source_review.SourceReviewVerdict:
            events.append(f"review:{inp.poc_rel_path}")
            return source_review.SourceReviewVerdict(
                "v8", "123", inp.poc_rel_path, True, "scoped", "fake"
            )

        with (
            patch.object(grade, "_build_source_review_input", side_effect=build),
            patch.object(source_review, "review_single", side_effect=review),
        ):
            grade.run_source_reviews(
                project="v8",
                candidates=[(self.instance, first), (self.instance, second)],
                instance_dirs=[self.instance_dir],
                benchmark_dir=self.benchmark_dir,
                model="fake",
                workers=1,
            )
        self.assertEqual(
            events,
            [
                "build:audit/first.js",
                "review:audit/first.js",
                "build:audit/second.js",
                "review:audit/second.js",
            ],
        )

    def test_source_review_pool_does_not_queue_past_container_capacity(self) -> None:
        first = self.add_file("first-capacity.js")
        second = self.add_file("second-capacity.js")
        first_review_started = threading.Event()
        release_first = threading.Event()
        second_built = threading.Event()

        def build(**kwargs: object) -> source_review.SourceReviewInput:
            file_result = kwargs["file_result"]
            assert isinstance(file_result, grade.FileResult)
            if file_result is second:
                second_built.set()
            return source_review.SourceReviewInput(
                "v8", "123", file_result.rel_path, "vuln", "/src/v8",
                "task", "poc", {}, {}, "patch",
            )

        def review(
            inp: source_review.SourceReviewInput, **_kwargs: object
        ) -> source_review.SourceReviewVerdict:
            if inp.poc_rel_path == first.rel_path:
                first_review_started.set()
                self.assertTrue(release_first.wait(timeout=2))
            return source_review.SourceReviewVerdict(
                "v8", "123", inp.poc_rel_path, True, "scoped", "fake"
            )

        with (
            patch.object(grade.common, "MAX_JS_CONTAINERS", 1),
            patch.object(grade, "_build_source_review_input", side_effect=build),
            patch.object(source_review, "review_single", side_effect=review),
            ThreadPoolExecutor(max_workers=1) as outer,
        ):
            future = outer.submit(
                grade.run_source_reviews,
                project="v8",
                candidates=[(self.instance, first), (self.instance, second)],
                instance_dirs=[self.instance_dir],
                benchmark_dir=self.benchmark_dir,
                model="fake",
                workers=2,
            )
            self.assertTrue(first_review_started.wait(timeout=2))
            self.assertFalse(second_built.wait(timeout=0.1))
            release_first.set()
            future.result(timeout=2)
        self.assertTrue(second_built.is_set())

    def test_one_vulnerable_worker_failure_preserves_sibling_results(self) -> None:
        names = ("poc-a-good.js", "poc-b-broken.js", "poc-c-good.js")
        for name in names:
            (self.instance_dir / "audit" / name).write_text("print(1)\n")

        def process(**kwargs: object) -> grade.FileResult:
            poc_file = kwargs["poc_file"]
            assert isinstance(poc_file, Path)
            if poc_file.name == "poc-b-broken.js":
                raise RuntimeError("docker inspect unavailable")
            return grade.FileResult(f"audit/{poc_file.name}")

        with patch.object(grade, "process_file", side_effect=process) as process_mock:
            result, _elapsed = grade.grade_instance_worker(
                project="v8",
                benchmark_dir=self.benchmark_dir,
                instance_dir=self.instance_dir,
                timeout_sec=1,
                attempts=1,
                fixed_repo="fixed",
                latest_image=None,
                latest_repo=None,
                pull_missing=False,
                poc_filter=None,
            )

        self.assertEqual(process_mock.call_count, 3)
        self.assertEqual(result.status, "checked")
        self.assertEqual([item.rel_path for item in result.file_results], [
            "audit/poc-a-good.js",
            "audit/poc-b-broken.js",
            "audit/poc-c-good.js",
        ])
        self.assertIsNone(result.file_results[0].verdict)
        self.assertEqual(result.file_results[1].outcome, "error")
        self.assertIn("docker inspect unavailable", result.file_results[1].verdict.error)
        self.assertIsNone(result.file_results[2].verdict)

    def test_summary_distinguishes_grader_errors_from_negative_submissions(self) -> None:
        candidate = self.add_file()
        candidate.verdict = judge.JudgeVerdict(
            "v8",
            "123",
            candidate.rel_path,
            "error",
            "synthetic grader failure",
            "fake",
            error="synthetic grader failure",
            decision_step="source_review",
        )
        out_dir = self.root / "summary"
        grade.write_global_csvs(self.instance_dir.parent, [self.instance], out_dir)
        with (out_dir / "summary.csv").open(newline="", encoding="utf-8") as fh:
            row = next(csv.DictReader(fh))
        self.assertEqual(row["error_pocs"], "1")
        self.assertEqual(row["grading_complete"], "no")

        with (out_dir / "executions.csv").open(newline="", encoding="utf-8") as fh:
            execution = next(csv.DictReader(fh))
        self.assertEqual(execution["engine_started"], "yes")
        self.assertEqual(execution["oom_killed"], "no")
        self.assertEqual(execution["infrastructure_error"], "")

    def test_linux_execution_csv_preserves_legacy_timeout_fields(self) -> None:
        self.instance.project = "linux"
        candidate = self.add_file(
            "poc.c",
            code=137,
            timed_out=True,
            engine_started=True,
            oom_killed=True,
            infrastructure_error="JS-only lifecycle sentinel",
            infrastructure_kind="container_status",
        )
        execution = candidate.vuln
        assert execution is not None
        execution.input_integrity_error = True
        execution.input_tree_sha256 = "input-digest"
        execution.stdout_sha256 = "stdout-digest"
        execution.stderr_sha256 = "stderr-digest"

        out_dir = self.root / "linux-summary"
        grade.write_global_csvs(self.instance_dir.parent, [self.instance], out_dir)
        with (out_dir / "executions.csv").open(newline="", encoding="utf-8") as fh:
            row = next(csv.DictReader(fh))

        self.assertEqual(row["exit_code"], "timeout")
        for field in (
            "engine_started",
            "oom_killed",
            "infrastructure_error",
            "infrastructure_kind",
            "input_integrity_error",
            "input_tree_sha256",
        ):
            self.assertEqual(row[field], "", field)
        self.assertEqual(row["stdout_sha256"], "stdout-digest")
        self.assertEqual(row["stderr_sha256"], "stderr-digest")


if __name__ == "__main__":
    unittest.main()
