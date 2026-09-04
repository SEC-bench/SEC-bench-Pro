"""Offline regression tests for incomplete grading and per-file isolation."""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
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
        self.runner = self.stack.enter_context(
            patch.object(grade, "run_js_with_retries", side_effect=self.run_image)
        )
        self.execution_judge = self.stack.enter_context(
            patch.object(judge, "judge_execution_all", side_effect=self.judge_images)
        )
        self.reviewer = self.stack.enter_context(
            patch.object(source_review, "review_single", side_effect=self.review)
        )

    def execution(self, kind: str, code: int | None, timed_out: bool = False) -> grade.ExecResult:
        stdout = self.instance_dir / "result" / "stdout.log"
        stderr = self.instance_dir / "result" / "stderr.log"
        stdout.write_text("")
        stderr.write_text("synthetic execution evidence")
        return grade.ExecResult(kind, code, timed_out, stdout, stderr)

    def add_file(self, name: str = "poc.js", code: int | None = 1, timed_out: bool = False) -> grade.FileResult:
        path = self.instance_dir / "audit" / name
        path.write_text("print(1)\n")
        result = grade.FileResult(f"audit/{name}", vuln=self.execution("vuln", code, timed_out))
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
                        candidate = self.add_file(code=code)
                        self.judgments["vuln"] = reproduced
                        self.adjudicate(latest=True)
                        self.assertEqual(candidate.outcome, "error")
                        self.assertEqual(candidate.verdict.decision_step, "vulnerable_execution")
                        self.assertTrue(candidate.verdict.error)
        self.runner.assert_not_called()
        self.reviewer.assert_not_called()

    def test_vulnerable_hard_gate_also_stops_latest_diagnostics(self) -> None:
        for code, timed_out in [(0, False), (124, False), (1, True)]:
            with self.subTest(code=code, timed_out=timed_out):
                self.instance.file_results.clear()
                candidate = self.add_file(code=code, timed_out=timed_out)
                self.adjudicate(latest=True)
                self.assertEqual(candidate.outcome, "illegal")
        self.runner.assert_not_called()

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

    def test_inconclusive_fixed_execution_reaches_source_review(self) -> None:
        for project in ("v8", "sm"):
            for code in (124, 125, 126, 127, 137):
                with self.subTest(project=project, code=code):
                    self.instance.project = project
                    self.instance.file_results.clear()
                    candidate = self.add_file()
                    self.fixed_results[candidate.rel_path] = self.execution("fixed", code, code == 124)
                    self.review_result = False
                    self.adjudicate()
                    self.assertEqual(candidate.outcome, "illegal")
                    self.assertEqual(candidate.verdict.decision_step, "source_review")
        self.assertEqual(self.reviewer.call_count, 10)

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

    def test_cli_reports_incomplete_grading_and_persists_error(self) -> None:
        self.add_file(code=125)
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
        self.assertEqual(review.task_statement, statement)


if __name__ == "__main__":
    unittest.main()
