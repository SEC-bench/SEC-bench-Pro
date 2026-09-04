from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness"))

import grade  # noqa: E402
import judge  # noqa: E402
import source_review  # noqa: E402


class ExecutionJudgeSchemaTests(unittest.TestCase):
    def test_execution_schema_requires_a_real_boolean_and_exact_keys(self) -> None:
        self.assertEqual(
            judge._validate_execution_schema(
                {"reproduced": True, "reason": "engine crash"}
            ),
            {"reproduced": True, "reason": "engine crash"},
        )
        with self.assertRaises(ValueError):
            judge._validate_execution_schema({"reproduced": "true", "reason": "x"})
        with self.assertRaises(ValueError):
            judge._validate_execution_schema(
                {"reproduced": True, "reason": "x", "extra": 1}
            )

    def test_prompt_rendering_failure_is_a_grader_error(self) -> None:
        evidence = judge.ExecutionJudgeInput(
            "v8", "1", "vuln", "task", "audit/poc.js", "print(1)",
            "", "1", False, "synthetic evidence", "",
        )
        with (
            patch.object(judge, "build_execution_prompt", side_effect=ValueError("bad template")),
            patch.object(judge, "_call_llm") as completion,
        ):
            verdict = judge.judge_execution_single(evidence, model="fake")
        self.assertIsNone(verdict.reproduced)
        self.assertEqual(verdict.error, "bad template")
        completion.assert_not_called()


class SourceReviewLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        self.review = source_review.SourceReviewInput(
            project="v8",
            instance_id="1",
            poc_rel_path="audit/poc.js",
            vuln_image="vuln",
            work_dir="/src/v8",
            task_statement="task",
            poc_source="x",
            poc_execution={},
            solver_trajectory={},
            reference_patch="patch",
        )

    def test_no_terminal_call_is_a_grader_error(self) -> None:
        response = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message={
                        "content": '{"in_scope":false,"reason":"guess"}',
                        "tool_calls": [],
                    }
                )
            ],
            usage=None,
        )
        with patch.object(source_review, "_completion_with_retries", return_value=response):
            with self.assertRaisesRegex(RuntimeError, "without using the terminal"):
                source_review._call_model_with_terminal(
                    self.review,
                    container_name="fake",
                    model="fake",
                    reasoning_effort="high",
                    max_turns=2,
                    terminal_timeout_sec=30,
                )

    def test_source_review_stages_exactly_the_five_contract_files(self) -> None:
        copied_names: set[str] = set()

        def fake_run(command: list[str], **_kwargs: object):
            if command[1] == "cp":
                staging = Path(command[2].removesuffix("/."))
                copied_names.update(path.name for path in staging.iterdir())
                json.loads((staging / "poc_execution.json").read_text())
                json.loads((staging / "solver_trajectory.json").read_text())
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        with patch.object(source_review.subprocess, "run", side_effect=fake_run):
            source_review._stage_audit_files("container", "/src/v8", self.review)

        self.assertEqual(
            copied_names,
            {
                "task_statement.md",
                "poc.js",
                "poc_execution.json",
                "solver_trajectory.json",
                "reference.patch",
            },
        )

    def test_terminal_call_then_strict_final_json_succeeds(self) -> None:
        thinking = [{"type": "thinking", "thinking": "synthetic", "signature": "test-signature"}]
        responses = [
            SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message={
                            "content": "",
                            "thinking_blocks": thinking,
                            "tool_calls": [
                                {
                                    "id": "call-1",
                                    "function": {
                                        "name": "terminal",
                                        "arguments": json.dumps(
                                            {
                                                "command": (
                                                    "cat audit/task_statement.md "
                                                    "audit/poc_execution.json"
                                                )
                                            }
                                        ),
                                    },
                                }
                            ],
                        }
                    )
                ],
                usage=None,
            ),
            SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message={
                            "content": (
                                '{"in_scope":true,'
                                '"reason":"assigned file is causal"}'
                            ),
                            "tool_calls": [],
                        }
                    )
                ],
                usage=None,
            ),
        ]
        terminal_result = source_review.TerminalCall(
            command="cat evidence",
            timeout_sec=30,
            exit_code=0,
            timed_out=False,
            stdout="evidence",
            stderr="",
        )
        with (
            patch.object(source_review, "_completion_with_retries", side_effect=responses) as completion,
            patch.object(source_review, "_run_terminal", return_value=terminal_result),
            patch.object(source_review, "_usage", return_value=(0, 0, 0, 0.0)),
        ):
            verdict = source_review._call_model_with_terminal(
                self.review,
                container_name="fake",
                model="fake",
                reasoning_effort="high",
                max_turns=4,
                terminal_timeout_sec=30,
            )
        self.assertIs(verdict.in_scope, True)
        self.assertEqual(verdict.tool_calls, 1)
        history = completion.call_args_list[1].args[0]["messages"]
        self.assertEqual(history[1]["thinking_blocks"], thinking)

    def test_failed_terminal_calls_cannot_produce_a_submission_verdict(self) -> None:
        for exit_code, timed_out in [(1, False), (125, False), (124, True), (None, True)]:
            for in_scope in (True, False):
                with self.subTest(exit_code=exit_code, in_scope=in_scope):
                    responses = [
                        SimpleNamespace(choices=[SimpleNamespace(message={
                            "tool_calls": [{
                                "id": "call-1",
                                "function": {
                                    "name": "terminal",
                                    "arguments": json.dumps({"command": "cat audit/task_statement.md audit/poc_execution.json"}),
                                },
                            }],
                        })]),
                        SimpleNamespace(choices=[SimpleNamespace(message={
                            "content": json.dumps({"in_scope": in_scope, "reason": "guess"}),
                        })]),
                    ]
                    failed_call = source_review.TerminalCall(
                        "read evidence", 30, exit_code, timed_out, "", "unavailable"
                    )
                    with (
                        patch.object(source_review, "_start_container", return_value="fake"),
                        patch.object(source_review, "_stage_audit_files"),
                        patch.object(source_review, "_remove_container") as cleanup,
                        patch.object(source_review, "_completion_with_retries", side_effect=responses),
                        patch.object(source_review, "_run_terminal", return_value=failed_call),
                        patch.object(source_review, "_usage", return_value=(0, 0, 0, 0.0)),
                    ):
                        verdict = source_review.review_single(self.review, model="fake")
                    self.assertIsNone(verdict.in_scope)
                    self.assertIn("no successful terminal calls", verdict.error)
                    self.assertEqual(verdict.transcript, [failed_call])
                    cleanup.assert_called_once_with("fake")

    def test_inner_terminal_timeout_is_reported_as_timeout(self) -> None:
        completed = SimpleNamespace(returncode=124, stdout="partial", stderr="")
        with patch.object(source_review.subprocess, "run", return_value=completed):
            call = source_review._run_terminal("fake", "/src/example", "pwd", 1)
        self.assertTrue(call.timed_out)
        self.assertEqual(json.loads(source_review._tool_result_content(call))["exit_code"], "timeout")

    def test_source_review_retries_only_transient_provider_errors(self) -> None:
        import litellm

        request = {"model": "fake", "messages": [{"role": "user", "content": "review"}]}
        with (
            patch.object(litellm, "completion", side_effect=[RuntimeError("429 rate limit"), "ok"]) as completion,
            patch.object(source_review.time, "sleep"),
        ):
            self.assertEqual(source_review._completion_with_retries(request), "ok")
        self.assertEqual(completion.call_args_list[0], completion.call_args_list[1])
        with patch.object(litellm, "completion", side_effect=RuntimeError("request refused")) as completion:
            with self.assertRaisesRegex(RuntimeError, "refused"):
                source_review._completion_with_retries(request)
        completion.assert_called_once_with(**request)


class StagedAdjudicationTests(unittest.TestCase):
    def test_all_three_terminal_decision_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            instance_dir = root / "run" / "123"
            benchmark_dir = root / "bench"
            benchmark_instance = benchmark_dir / "123"
            result_dir = instance_dir / "result"
            result_dir.mkdir(parents=True)
            benchmark_instance.mkdir(parents=True)
            meta = {
                "work_dir": "/src/v8",
                "verification_binary": "out/d8",
                "command_options": "",
                "target_source_files": ["src/x.cc"],
                "target_vulnerability_type": "UAF",
                "error_type": "ASAN_CRASH",
            }
            (benchmark_instance / "meta.json").write_text(json.dumps(meta))
            (benchmark_instance / "output.txt").write_text("historical")
            (instance_dir / "prompt.txt").write_text("task")

            files: list[grade.FileResult] = []
            for index in range(3):
                rel_path = f"audit/p{index}.js"
                poc_path = instance_dir / rel_path
                poc_path.parent.mkdir(exist_ok=True)
                poc_path.write_text("print(1)")
                stdout = result_dir / f"v{index}.out"
                stderr = result_dir / f"v{index}.err"
                stdout.write_text("")
                stderr.write_text("crash")
                files.append(
                    grade.FileResult(
                        rel_path=rel_path,
                        vuln=grade.ExecResult("vuln", 1, False, stdout, stderr),
                    )
                )
            instance = grade.InstanceResult(
                "v8",
                "123",
                "ASAN_CRASH",
                "UAF",
                "vuln",
                "fixed",
                "n/a",
                file_results=files,
                status="checked",
            )

            def fake_judge(inputs: list[judge.ExecutionJudgeInput], **_kwargs: object):
                verdicts = []
                for judge_input in inputs:
                    index = int(Path(judge_input.poc_rel_path).stem[1:])
                    reproduced = (
                        index != 0 if judge_input.image_kind == "vuln" else index == 2
                    )
                    verdicts.append(
                        judge.ExecutionJudgeVerdict(
                            judge_input.project,
                            judge_input.instance_id,
                            judge_input.poc_rel_path,
                            judge_input.image_kind,
                            reproduced,
                            f"{judge_input.image_kind}-{index}",
                            "fake",
                        )
                    )
                return verdicts

            def fake_phase(**kwargs: object) -> None:
                image_kind = str(kwargs["image_kind"])
                eligible = kwargs["eligible"]
                for file_result in files:
                    if not eligible(file_result):  # type: ignore[operator]
                        continue
                    index = int(Path(file_result.rel_path).stem[1:])
                    stdout = result_dir / f"{image_kind}{index}.out"
                    stderr = result_dir / f"{image_kind}{index}.err"
                    stdout.write_text("")
                    stderr.write_text("" if index == 1 else "crash")
                    setattr(
                        file_result,
                        image_kind,
                        grade.ExecResult(
                            image_kind,
                            0 if index == 1 else 1,
                            False,
                            stdout,
                            stderr,
                        ),
                    )

            def fake_reviews(**kwargs: object) -> None:
                for result, file_result in kwargs["candidates"]:  # type: ignore[union-attr]
                    file_result.source_review = source_review.SourceReviewVerdict(
                        "v8",
                        result.instance_id,
                        file_result.rel_path,
                        True,
                        "scoped",
                        "fake",
                        tool_calls=2,
                    )

            with (
                patch.object(grade.judge_module, "judge_execution_all", fake_judge),
                patch.object(grade, "run_js_image_phase", fake_phase),
                patch.object(grade, "run_source_reviews", fake_reviews),
            ):
                verdicts, pairs = grade.adjudicate_js_results(
                    project="v8",
                    results=[instance],
                    instance_dirs=[instance_dir],
                    benchmark_dir=benchmark_dir,
                    latest_enabled=False,
                    timeout_sec=3,
                    attempts=1,
                    execution_workers=2,
                    judge_workers=2,
                    pull_missing=False,
                    model="fake",
                )

            self.assertEqual(
                [(verdict.outcome, verdict.decision_step) for verdict in verdicts],
                [
                    ("illegal", "vulnerable_execution"),
                    ("verified", "fixed_execution"),
                    ("verified", "source_review"),
                ],
            )
            self.assertEqual(len(pairs["vuln"]), 3)
            self.assertEqual(len(pairs["fixed"]), 2)


if __name__ == "__main__":
    unittest.main()
