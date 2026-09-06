from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness"))

import common  # noqa: E402
import grade  # noqa: E402
import js_engine_runner  # noqa: E402
import judge  # noqa: E402
import source_review  # noqa: E402


class FileRowDecisionStepTests(unittest.TestCase):
    def test_invalid_input_and_native_policy_have_distinct_decision_steps(self) -> None:
        instance = grade.InstanceResult(
            "sm", "1", "ASAN_CRASH", "UAF", "vuln", "fixed", "latest"
        )
        input_error = grade.FileResult(
            "poc.js", invalid=True, invalid_reason="cannot_read_poc:too large"
        )
        native_error = grade.FileResult(
            "poc.js",
            invalid=True,
            invalid_reason="blocked_native_intrinsics:%SystemBreak",
        )

        self.assertEqual(grade._file_row(instance, input_error)[12], "input_validation")
        self.assertEqual(grade._file_row(instance, native_error)[12], "native_validation")


class JsContainerConcurrencyTests(unittest.TestCase):
    def test_invalid_container_limits_fail_closed_to_one(self) -> None:
        for raw in (
            None,
            "",
            " ",
            "0",
            "-1",
            "1.5",
            "257",
            "9" * 10_000,
            "many",
        ):
            with self.subTest(raw=raw):
                self.assertEqual(common.parse_max_js_containers(raw), 1)
        self.assertEqual(common.parse_max_js_containers("2"), 2)
        self.assertEqual(common.parse_max_js_containers(" 17 "), 17)

    def test_shared_container_limit_serializes_callers(self) -> None:
        limiter = threading.BoundedSemaphore(1)
        first_acquired = threading.Event()
        release_first = threading.Event()
        second_acquired = threading.Event()

        def first() -> None:
            slot = common.acquire_js_container_slot()
            first_acquired.set()
            self.assertTrue(release_first.wait(timeout=2))
            common.release_js_container_slot(slot)

        def second() -> None:
            self.assertTrue(first_acquired.wait(timeout=2))
            slot = common.acquire_js_container_slot()
            second_acquired.set()
            common.release_js_container_slot(slot)

        with (
            patch.object(common, "_js_container_slots", limiter),
            ThreadPoolExecutor(max_workers=2) as executor,
        ):
            first_future = executor.submit(first)
            second_future = executor.submit(second)
            self.assertTrue(first_acquired.wait(timeout=2))
            self.assertFalse(second_acquired.wait(timeout=0.1))
            release_first.set()
            self.assertTrue(second_acquired.wait(timeout=2))
            first_future.result(timeout=2)
            second_future.result(timeout=2)

    def test_interrupted_slot_acquisition_does_not_leak_capacity(self) -> None:
        limiter = threading.BoundedSemaphore(1)
        with (
            patch.object(common, "_js_container_slots", limiter),
            patch.object(common, "INTERRUPTED", True),
            self.assertRaises(KeyboardInterrupt),
        ):
            common.acquire_js_container_slot()

        self.assertTrue(limiter.acquire(blocking=False))
        limiter.release()

    def test_js_execution_releases_slot_only_after_container_cleanup(self) -> None:
        events: list[str] = []
        token = threading.BoundedSemaphore(1)

        def acquire() -> threading.BoundedSemaphore:
            events.append("acquire")
            return token

        def remove(_name: str) -> bool:
            events.append("remove")
            return True

        def release(slots: threading.BoundedSemaphore) -> None:
            self.assertIs(slots, token)
            events.append("release")

        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch.object(common, "acquire_js_container_slot", side_effect=acquire),
            patch.object(common, "release_js_container_slot", side_effect=release),
            patch.object(
                grade,
                "run_interruptible_command",
                side_effect=grade.GradingInterrupted,
            ),
            patch.object(grade, "_force_remove_container", side_effect=remove),
        ):
            root = Path(temp_dir)
            with self.assertRaises(grade.GradingInterrupted):
                grade.run_js_once(
                    project="v8",
                    image="sha256:" + "a" * 64,
                    image_kind="vuln",
                    instance_dir=root,
                    rel_path="audit/poc.js",
                    work_dir="/src/v8",
                    binary="out/d8",
                    options=[],
                    timeout_sec=1,
                    result_dir=root / "result",
                    poc_snapshot_bytes=b"print(1)\n",
                )

        self.assertEqual(events[0], "acquire")
        self.assertEqual(events[-1], "release")
        self.assertGreaterEqual(events.count("remove"), 1)

    def test_waiting_js_worker_rechecks_interrupt_before_launch(self) -> None:
        token = threading.BoundedSemaphore(1)
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch.object(
                grade,
                "raise_if_interrupted",
                side_effect=[None, grade.GradingInterrupted()],
            ) as interrupt_check,
            patch.object(
                common, "acquire_js_container_slot", return_value=token
            ),
            patch.object(common, "release_js_container_slot") as release,
            patch.object(grade, "run_interruptible_command") as launch,
            patch.object(grade, "_force_remove_container", return_value=True),
        ):
            root = Path(temp_dir)
            with self.assertRaises(grade.GradingInterrupted):
                grade.run_js_once(
                    project="v8",
                    image="sha256:" + "a" * 64,
                    image_kind="vuln",
                    instance_dir=root,
                    rel_path="audit/poc.js",
                    work_dir="/src/v8",
                    binary="out/d8",
                    options=[],
                    timeout_sec=1,
                    result_dir=root / "result",
                    poc_snapshot_bytes=b"print(1)\n",
                )

        self.assertEqual(interrupt_check.call_count, 2)
        launch.assert_not_called()
        release.assert_called_once_with(token)


class JsGradingBudgetTests(unittest.TestCase):
    def tearDown(self) -> None:
        common.clear_js_grading_budget()

    def test_invalid_environment_budgets_fail_closed_to_safe_defaults(self) -> None:
        invalid = ("", "0", "-1", "1.5", "99999999999", "many")
        for raw in (None, *invalid):
            with self.subTest(raw=raw):
                self.assertEqual(
                    common.parse_js_grading_time_budget(raw),
                    common.DEFAULT_JS_GRADING_TIME_BUDGET_SEC,
                )
        self.assertIsNone(common.parse_js_llm_call_budget(None))
        for raw in invalid:
            with self.subTest(llm_raw=raw):
                self.assertEqual(
                    common.parse_js_llm_call_budget(raw),
                    common.INVALID_JS_LLM_CALL_BUDGET_FALLBACK,
                )
        self.assertEqual(common.parse_js_grading_time_budget(" 120 "), 120)
        self.assertEqual(common.parse_js_llm_call_budget(" 7 "), 7)

    def test_automatic_llm_budget_accumulates_bounded_timestamp_workloads(self) -> None:
        common.configure_js_grading_budget(time_budget_sec=60, llm_call_budget=None)

        def full_sweep(size: int, project: str) -> list[grade.InstanceResult]:
            return [
                grade.InstanceResult(
                    project,
                    str(index),
                    "ASAN_CRASH",
                    "TYPE_CONFUSION",
                    "vuln",
                    "fixed",
                    "latest",
                    status="checked",
                    file_results=[grade.FileResult("audit/poc.js")],
                )
                for index in range(size)
            ]

        first_added, first_total = grade.reserve_automatic_js_llm_capacity(
            full_sweep(52, "v8"), latest_enabled=True
        )
        second_added, v8_total = grade.reserve_automatic_js_llm_capacity(
            full_sweep(51, "v8"), latest_enabled=True
        )
        self.assertEqual(first_total, first_added)
        self.assertEqual(v8_total, 103 * grade.MAX_JS_LLM_CALLS_PER_POC)
        self.assertEqual(v8_total, first_added + second_added)
        self.assertGreaterEqual(v8_total, 2 * 103)

        common.clear_js_grading_budget()
        common.configure_js_grading_budget(time_budget_sec=60, llm_call_budget=None)
        grade.reserve_automatic_js_llm_capacity(
            full_sweep(52, "sm"), latest_enabled=True
        )
        _added, sm_total = grade.reserve_automatic_js_llm_capacity(
            full_sweep(52, "sm"), latest_enabled=True
        )
        self.assertEqual(sm_total, 104 * grade.MAX_JS_LLM_CALLS_PER_POC)
        self.assertGreaterEqual(sm_total, 2 * 104)
        self.assertGreater(sm_total, 256)
        self.assertLessEqual(sm_total, common.MAX_JS_LLM_CALL_BUDGET)

    def test_explicit_llm_budget_is_not_expanded_by_workload(self) -> None:
        common.configure_js_grading_budget(time_budget_sec=60, llm_call_budget=2)
        self.assertEqual(common.add_automatic_js_llm_call_capacity(1_000), 2)
        self.assertEqual(common.consume_js_llm_call("first"), (1, 2))
        self.assertEqual(common.consume_js_llm_call("second"), (2, 2))
        with self.assertRaisesRegex(
            common.JsGradingBudgetExceeded, "LLM-call budget exhausted"
        ):
            common.consume_js_llm_call("third")

    def test_budget_that_cannot_honor_engine_timeout_fails_before_launch(self) -> None:
        token = threading.BoundedSemaphore(1)
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch.object(
                common,
                "js_grading_budget_remaining",
                side_effect=[100.0, 20.0],
            ),
            patch.object(
                common, "acquire_js_container_slot", return_value=token
            ),
            patch.object(common, "release_js_container_slot") as release,
            patch.object(grade, "add_container") as register,
            patch.object(grade, "run_interruptible_command") as launch,
            self.assertRaisesRegex(
                common.JsGradingBudgetExceeded,
                "insufficient time to honor the requested 10s engine timeout",
            ),
        ):
            root = Path(temp_dir)
            grade.run_js_once(
                project="v8",
                image="sha256:" + "a" * 64,
                image_kind="vuln",
                instance_dir=root,
                rel_path="audit/poc.js",
                work_dir="/src/v8",
                binary="out/d8",
                options=[],
                timeout_sec=10,
                result_dir=root / "result",
                poc_snapshot_bytes=b"print(1)\n",
            )

        register.assert_not_called()
        launch.assert_not_called()
        release.assert_called_once_with(token)

    def test_wall_clock_budget_error_propagates_to_the_top_level(self) -> None:
        error = common.JsGradingBudgetExceeded("synthetic wall-clock exhaustion")
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch.object(grade.judge_module, "check_api_key", return_value=True),
            patch.object(grade.common, "docker_preflight"),
            patch.object(grade, "grade_instances", side_effect=error),
            patch.object(grade, "_print") as output,
        ):
            root = Path(temp_dir)
            (root / "123").mkdir()
            self.assertEqual(
                grade.main(
                    [
                        "--project",
                        "v8",
                        "--target-dir",
                        str(root),
                        "--benchmark-dir",
                        str(root),
                    ]
                ),
                1,
            )

        self.assertTrue(
            any(
                "grader error: synthetic wall-clock exhaustion" in call.args[0]
                for call in output.call_args_list
            )
        )

    def test_docker_preflight_uses_remaining_js_deadline_for_each_check(self) -> None:
        completed = subprocess.CompletedProcess([], 0, "", "")
        with (
            patch.object(common.time, "monotonic", side_effect=[100.0, 102.5]),
            patch.object(common.subprocess, "run", return_value=completed) as run,
        ):
            common.docker_preflight(deadline=110.0)

        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args_list[0].args[0], ["docker", "--version"])
        self.assertEqual(run.call_args_list[0].kwargs["timeout"], 10.0)
        self.assertEqual(run.call_args_list[1].args[0], ["docker", "info"])
        self.assertEqual(run.call_args_list[1].kwargs["timeout"], 7.5)

    def test_docker_preflight_timeout_is_a_grading_budget_error(self) -> None:
        completed = subprocess.CompletedProcess([], 0, "", "")
        timeout = subprocess.TimeoutExpired(["docker", "info"], 4.0)
        with (
            patch.object(common.time, "monotonic", side_effect=[100.0, 101.0]),
            patch.object(
                common.subprocess,
                "run",
                side_effect=[completed, timeout],
            ),
            self.assertRaisesRegex(
                common.JsGradingBudgetExceeded,
                "budget exhausted during Docker preflight.*daemon check",
            ),
        ):
            common.docker_preflight(deadline=105.0)

    def test_expired_js_deadline_does_not_start_docker_preflight(self) -> None:
        with (
            patch.object(common.time, "monotonic", return_value=101.0),
            patch.object(common.subprocess, "run") as run,
            self.assertRaisesRegex(
                common.JsGradingBudgetExceeded,
                "budget exhausted before Docker preflight.*version check",
            ),
        ):
            common.docker_preflight(deadline=100.0)
        run.assert_not_called()

    def test_top_level_reports_docker_preflight_budget_exhaustion(self) -> None:
        error = common.JsGradingBudgetExceeded(
            "synthetic Docker preflight exhaustion"
        )
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch.object(grade.judge_module, "check_api_key", return_value=True),
            patch.object(grade.common, "docker_preflight", side_effect=error) as preflight,
            patch.object(grade, "_print") as output,
        ):
            root = Path(temp_dir)
            (root / "123").mkdir()
            self.assertEqual(
                grade.main(
                    [
                        "--project",
                        "v8",
                        "--target-dir",
                        str(root),
                        "--benchmark-dir",
                        str(root),
                    ]
                ),
                1,
            )

        self.assertIsNotNone(preflight.call_args.kwargs["deadline"])
        self.assertTrue(
            any(
                "grader error: synthetic Docker preflight exhaustion" in call.args[0]
                for call in output.call_args_list
            )
        )

    def test_linux_docker_preflight_keeps_the_legacy_unbounded_call(self) -> None:
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch.object(grade.judge_module, "check_api_key", return_value=True),
            patch.object(
                grade.common,
                "docker_preflight",
                side_effect=RuntimeError("stop after preflight"),
            ) as preflight,
            patch.object(grade, "_print"),
        ):
            root = Path(temp_dir)
            (root / "123").mkdir()
            self.assertEqual(
                grade.main(
                    [
                        "--project",
                        "linux",
                        "--target-dir",
                        str(root),
                        "--benchmark-dir",
                        str(root),
                    ]
                ),
                1,
            )

        preflight.assert_called_once_with(deadline=None)

    def test_unbounded_docker_preflight_does_not_add_subprocess_timeouts(self) -> None:
        completed = subprocess.CompletedProcess([], 0, "", "")
        with patch.object(
            common.subprocess, "run", return_value=completed
        ) as run:
            common.docker_preflight()

        self.assertEqual(run.call_count, 2)
        for call in run.call_args_list:
            self.assertNotIn("timeout", call.kwargs)

    def test_top_level_clears_budget_only_after_running_workers_finish(self) -> None:
        second_started = threading.Event()
        first_failed = threading.Event()
        release_second = threading.Event()
        second_finished = threading.Event()
        launch_after_clear = unittest.mock.Mock()
        main_result: list[int] = []

        def worker(**kwargs: object) -> tuple[grade.InstanceResult, float]:
            instance_dir = kwargs["instance_dir"]
            self.assertIsInstance(instance_dir, Path)
            if instance_dir.name == "first":
                self.assertTrue(second_started.wait(timeout=2))
                first_failed.set()
                raise common.JsGradingBudgetExceeded(
                    "synthetic concurrent wall-clock exhaustion"
                )

            second_started.set()
            self.assertTrue(first_failed.wait(timeout=2))
            self.assertTrue(release_second.wait(timeout=5))
            if common.js_grading_budget_deadline() is None:
                launch_after_clear()
            second_finished.set()
            return (
                grade.InstanceResult(
                    project="v8",
                    instance_id="second",
                    expected_type="ASAN_CRASH",
                    target_vulnerability_type="TYPE_CONFUSION",
                    vuln_image="vuln",
                    fixed_image="fixed",
                    latest_image="latest",
                ),
                0.0,
            )

        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch.object(grade, "install_interrupt_handler"),
            patch.object(grade.judge_module, "check_api_key", return_value=True),
            patch.object(grade.common, "docker_preflight"),
            patch.object(grade, "grade_instance_worker", side_effect=worker),
            patch.object(grade, "_print"),
        ):
            root = Path(temp_dir)
            timestamp = root / "20260101_000000"
            (timestamp / "first").mkdir(parents=True)
            (timestamp / "second").mkdir()

            main_thread = threading.Thread(
                target=lambda: main_result.append(
                    grade.main(
                        [
                            "--project",
                            "v8",
                            "--target-dir",
                            str(root),
                            "--benchmark-dir",
                            str(root),
                            "--workers",
                            "2",
                        ]
                    )
                )
            )
            main_thread.start()
            self.assertTrue(first_failed.wait(timeout=2))

            # The budget-error path must wait for the sibling before main() can
            # clear the shared deadline and return.  The old wait=False path
            # finishes during this bounded join and exposes deadline=None to
            # the still-running worker.
            main_thread.join(timeout=0.2)
            self.assertTrue(main_thread.is_alive())
            self.assertIsNotNone(common.js_grading_budget_deadline())

            release_second.set()
            main_thread.join(timeout=5)

        self.assertFalse(main_thread.is_alive())
        self.assertTrue(second_finished.is_set())
        self.assertEqual(main_result, [1])
        self.assertIsNone(common.js_grading_budget_deadline())
        launch_after_clear.assert_not_called()

    def test_worker_does_not_convert_wall_clock_budget_to_instance_error(self) -> None:
        error = common.JsGradingBudgetExceeded("synthetic wall-clock exhaustion")
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch.object(grade, "process_instance", side_effect=error),
            self.assertRaises(common.JsGradingBudgetExceeded),
        ):
            grade.grade_instance_worker(
                project="v8", instance_dir=Path(temp_dir) / "123"
            )

    def test_llm_budget_is_atomic_across_workers(self) -> None:
        common.configure_js_grading_budget(time_budget_sec=60, llm_call_budget=5)

        def reserve() -> bool:
            try:
                common.consume_js_llm_call("test provider call")
                return True
            except common.JsGradingBudgetExceeded:
                return False

        with ThreadPoolExecutor(max_workers=16) as executor:
            reservations = list(executor.map(lambda _index: reserve(), range(16)))
        self.assertEqual(sum(reservations), 5)

    def test_command_is_killed_at_the_global_wall_clock_deadline(self) -> None:
        common.configure_js_grading_budget(time_budget_sec=1, llm_call_budget=1)
        started = time.monotonic()
        with self.assertRaisesRegex(
            common.JsGradingBudgetExceeded, "wall-clock budget exhausted"
        ):
            grade.run_interruptible_command(
                [sys.executable, "-c", "import time; time.sleep(10)"],
                timeout_sec=30,
            )
        self.assertLess(time.monotonic() - started, 3)
        self.assertEqual(grade._active_processes, set())

    def test_expired_budget_does_not_start_a_child_process(self) -> None:
        common.configure_js_grading_budget(time_budget_sec=60, llm_call_budget=1)
        with (
            patch.object(common, "_js_grading_deadline", time.monotonic() - 1),
            patch.object(grade.subprocess, "Popen") as popen,
            self.assertRaisesRegex(
                common.JsGradingBudgetExceeded, "wall-clock budget exhausted"
            ),
        ):
            grade.run_interruptible_command(
                [sys.executable, "-c", "pass"], timeout_sec=30
            )
        popen.assert_not_called()

    def test_expired_budget_does_not_stage_js_snapshot(self) -> None:
        common.configure_js_grading_budget(time_budget_sec=60, llm_call_budget=1)
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch.object(common, "_js_grading_deadline", time.monotonic() - 1),
            patch.object(grade.tempfile, "mkstemp") as mkstemp,
            self.assertRaisesRegex(
                common.JsGradingBudgetExceeded, "wall-clock budget exhausted"
            ),
        ):
            root = Path(temp_dir)
            grade.run_js_once(
                project="v8",
                image="sha256:" + "a" * 64,
                image_kind="vuln",
                instance_dir=root,
                rel_path="audit/poc.js",
                work_dir="/src/v8",
                binary="out/d8",
                options=[],
                timeout_sec=1,
                result_dir=root / "result",
                poc_snapshot_bytes=b"print(1)\n",
            )
        mkstemp.assert_not_called()

    def test_actual_provider_retries_consume_the_shared_call_budget(self) -> None:
        import litellm

        response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="not json"))],
            usage=None,
        )
        common.configure_js_grading_budget(time_budget_sec=60, llm_call_budget=1)
        with (
            patch.object(litellm, "completion", return_value=response) as completion,
            self.assertRaisesRegex(
                common.JsGradingBudgetExceeded, "LLM-call budget exhausted"
            ),
        ):
            judge._call_llm("prompt", "fake", "high")
        completion.assert_called_once()

    def test_js_timeout_oom_and_infrastructure_results_are_not_retried(self) -> None:
        def result(**changes: object) -> grade.ExecResult:
            values = {
                "image_kind": "vuln",
                "exit_code": 0,
                "timed_out": False,
                "stdout_log": Path("stdout"),
                "stderr_log": Path("stderr"),
                "engine_started": True,
                "oom_killed": False,
                "infrastructure_error": "",
            }
            values.update(changes)
            return grade.ExecResult(**values)  # type: ignore[arg-type]

        terminal_states = (
            result(timed_out=True, exit_code=137),
            result(oom_killed=True, exit_code=137),
            result(infrastructure_error="Docker inspect failed", exit_code=1),
            result(infrastructure_kind="docker_state", exit_code=1),
            result(engine_started=False, exit_code=126),
            result(exit_code=None),
        )
        for terminal in terminal_states:
            calls = 0

            def run_once(_attempt: int) -> grade.ExecResult:
                nonlocal calls
                calls += 1
                return terminal

            with self.subTest(state=terminal):
                grade._run_with_retries("v8", 3, run_once)
                self.assertEqual(calls, 1)

        js_calls = 0

        def clean_js(_attempt: int) -> grade.ExecResult:
            nonlocal js_calls
            js_calls += 1
            return result()

        grade._run_with_retries("v8", 10_000, clean_js)
        self.assertEqual(js_calls, 3)

        linux_calls = 0

        def linux_infra(_attempt: int) -> grade.ExecResult:
            nonlocal linux_calls
            linux_calls += 1
            return result(exit_code=2, infrastructure_error="harness error")

        grade._run_with_retries("linux", 3, linux_infra)
        self.assertEqual(linux_calls, 3)

    def test_js_poc_file_count_has_a_small_hard_cap(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            instance = Path(temp_dir)
            for index in range(grade.MAX_JS_POC_FILES + 1):
                (instance / f"poc-{index}.js").write_text("print(1)\n")
            with self.assertRaisesRegex(ValueError, "exceeds 4 PoC files"):
                grade.find_js_files(instance)

    def test_js_instance_discovery_is_bounded_without_changing_linux(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run = Path(temp_dir)
            for index in range(5):
                (run / str(index)).mkdir()
            with (
                patch.object(grade, "MAX_JS_INSTANCES", 4),
                self.assertRaisesRegex(ValueError, "exceeds 4 instance directories"),
            ):
                grade.collect_instance_dirs(run, js_limits=True)
            self.assertEqual(len(grade.collect_instance_dirs(run)), 5)

    def test_preexisting_js_result_cleanup_is_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = Path(temp_dir) / "result"
            result.mkdir()
            for index in range(5):
                (result / str(index)).write_text("old output")
            with (
                patch.object(grade, "MAX_JS_RESULT_CLEANUP_ENTRIES", 4),
                self.assertRaisesRegex(ValueError, "exceeds 4 cleanup entries"),
            ):
                grade._prepare_result_dir(result, "v8")
            self.assertTrue(result.is_dir())

    def test_js_cli_rejects_unbounded_attempt_and_worker_fanout(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for option, value in (
                ("--attempts", str(grade.MAX_JS_ATTEMPTS + 1)),
                ("--workers", str(grade.MAX_JS_EXECUTION_WORKERS + 1)),
                ("--judge-workers", str(grade.MAX_JS_JUDGE_WORKERS + 1)),
            ):
                with self.subTest(option=option):
                    self.assertEqual(
                        grade.main(
                            [
                                "--project",
                                "v8",
                                "--target-dir",
                                str(root),
                                "--benchmark-dir",
                                str(root),
                                option,
                                value,
                            ]
                        ),
                        1,
                    )


class ExecutionJudgeSchemaTests(unittest.TestCase):
    def test_combined_schema_preserves_legacy_empty_reason_behavior(self) -> None:
        self.assertEqual(
            judge._validate_schema({"outcome": "verified", "reason": "  "}),
            {"outcome": "verified", "reason": ""},
        )

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
        with self.assertRaisesRegex(ValueError, "non-empty"):
            judge._validate_execution_schema({"reproduced": False, "reason": "  "})
        with self.assertRaisesRegex(ValueError, "non-empty"):
            source_review._validate_source_review(
                {"in_scope": False, "reason": "\n"}
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

    def test_execution_judge_uses_the_small_output_token_cap(self) -> None:
        evidence = judge.ExecutionJudgeInput(
            "v8", "1", "vuln", "task", "audit/poc.js", "print(1)",
            "", "1", False, "synthetic evidence", "",
        )
        with patch.object(
            judge, "_call_llm", side_effect=RuntimeError("synthetic stop")
        ) as completion:
            verdict = judge.judge_execution_single(evidence, model="fake")
        self.assertIsNone(verdict.reproduced)
        self.assertEqual(
            completion.call_args.kwargs["max_output_tokens"],
            judge.MAX_EXECUTION_JUDGE_OUTPUT_TOKENS,
        )
        self.assertEqual(
            completion.call_args.kwargs["request_timeout_sec"],
            judge.DEFAULT_LLM_REQUEST_TIMEOUT_SEC,
        )
        self.assertEqual(
            completion.call_args.kwargs["overall_timeout_sec"],
            judge.DEFAULT_LLM_OVERALL_TIMEOUT_SEC,
        )

    def test_combined_judge_keeps_legacy_provider_timeout_semantics(self) -> None:
        import litellm

        response = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content='{"outcome": "verified", "reason": "ok"}'
                    )
                )
            ],
            usage=None,
        )
        common.clear_js_grading_budget()
        with patch.object(
            litellm, "completion", return_value=response
        ) as completion:
            result = judge._call_llm("prompt", "fake", "high")

        self.assertEqual(result.parsed["outcome"], "verified")
        self.assertNotIn("timeout", completion.call_args.kwargs)

    def test_judge_model_request_timeout_is_capped_by_overall_deadline(self) -> None:
        import litellm

        response = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content='{"outcome": "verified", "reason": "ok"}'
                    )
                )
            ],
            usage=SimpleNamespace(
                prompt_tokens=1, completion_tokens=1, total_tokens=2
            ),
        )
        with (
            patch.object(judge.time, "monotonic", return_value=100.0),
            patch.object(litellm, "completion", return_value=response) as completion,
        ):
            result = judge._call_llm(
                "prompt",
                "fake",
                "high",
                request_timeout_sec=120,
                overall_timeout_sec=17,
            )

        self.assertEqual(result.parsed["outcome"], "verified")
        self.assertEqual(completion.call_args.kwargs["timeout"], 17.0)

    def test_judge_retries_cannot_outlive_overall_deadline(self) -> None:
        import litellm

        clock = [0.0]
        observed_timeouts: list[float] = []
        observed_sleeps: list[float] = []

        def completion(**kwargs: object) -> object:
            observed_timeouts.append(float(kwargs["timeout"]))
            clock[0] = 9.5
            raise RuntimeError("503 service unavailable")

        def sleep(delay: float) -> None:
            observed_sleeps.append(delay)
            clock[0] += delay

        with (
            patch.object(judge.time, "monotonic", side_effect=lambda: clock[0]),
            patch.object(judge.time, "sleep", side_effect=sleep),
            patch.object(litellm, "completion", side_effect=completion),
            self.assertRaisesRegex(TimeoutError, "overall deadline"),
        ):
            judge._call_llm(
                "prompt",
                "fake",
                "high",
                request_timeout_sec=120,
                overall_timeout_sec=10,
            )

        self.assertEqual(observed_timeouts, [10.0])
        self.assertEqual(observed_sleeps, [0.5])

    def test_required_marker_in_the_middle_of_a_long_log_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            stderr = Path(temp_dir) / "stderr.log"
            stderr.write_text(
                "a" * 6_000
                + "\nSUMMARY: AddressSanitizer: heap-use-after-free\n"
                + "z" * 6_000
            )
            excerpt = grade._read_instance_execution_stderr(
                Path(temp_dir), stderr, 8_000, "ASAN_CRASH"
            )
        self.assertIn("SUMMARY: AddressSanitizer", excerpt)
        self.assertIn("required error-marker contexts", excerpt)

    def test_command_capture_is_bounded_and_keeps_head_and_tail(self) -> None:
        script = "import sys; sys.stdout.write('HEAD' + 'x' * 200 + 'TAIL')"
        with patch.object(grade, "MAX_COMMAND_OUTPUT_CHARS", 100):
            result = grade.run_interruptible_command(
                [sys.executable, "-c", script], timeout_sec=10
            )
        self.assertEqual(result.exit_code, 0)
        self.assertTrue(result.stdout.startswith("HEAD"))
        self.assertTrue(result.stdout.endswith("TAIL"))
        self.assertIn("middle discarded", result.stdout)

    def test_command_capture_preserves_crash_markers_from_discarded_middle(self) -> None:
        marker = "SUMMARY: AddressSanitizer: heap-use-after-free"
        script = (
            "import sys; "
            f"sys.stderr.write('HEAD' + 'a' * 80 + {marker!r} + 'z' * 80 + 'TAIL')"
        )
        with patch.object(grade, "MAX_COMMAND_OUTPUT_CHARS", 80):
            result = grade.run_interruptible_command(
                [sys.executable, "-c", script], timeout_sec=10
            )
        self.assertEqual(result.exit_code, 0)
        self.assertIn(marker, result.stderr)
        self.assertIn("marker contexts preserved during capture", result.stderr)

    def test_judge_artifact_stems_are_bounded_and_collision_resistant(self) -> None:
        self.assertEqual(grade._safe_judge_filename("audit/poc.js"), "audit__poc.js")
        self.assertNotEqual(
            grade._safe_judge_filename("a/b.js"),
            grade._safe_judge_filename("a__b.js"),
        )
        stem = grade._safe_judge_filename("audit/" + "a" * 240 + ".js")
        self.assertLessEqual(
            len(stem.encode("utf-8")), grade.MAX_JUDGE_ARTIFACT_STEM_BYTES
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            long_rel_path = "audit/" + "a" * 244 + ".js"
            first = grade._execution_log_path(
                Path(temp_dir), "vuln", "stderr", long_rel_path, 1
            )
            second = grade._execution_log_path(
                Path(temp_dir), "vuln", "stderr", long_rel_path + "x", 1
            )
            first.parent.mkdir(parents=True)
            first.write_text("captured\n")
            self.assertLessEqual(len(first.name.encode("utf-8")), 255)
            self.assertNotEqual(first, second)
            self.assertEqual(
                grade._linux_execution_log_path(
                    Path(temp_dir), "vuln", "stderr", "audit/poc.c", 2
                ),
                Path(temp_dir)
                / "vuln"
                / "stderr"
                / "audit"
                / "poc.c.attempt2.log",
            )


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

    def test_source_review_holds_shared_slot_through_container_cleanup(self) -> None:
        events: list[str] = []
        token = threading.BoundedSemaphore(1)
        expected = source_review.SourceReviewVerdict(
            "v8", "1", "audit/poc.js", True, "scoped", "fake"
        )

        def acquire() -> threading.BoundedSemaphore:
            events.append("acquire")
            return token

        def start(*_args: object, **_kwargs: object) -> str:
            events.append("start")
            return "fake-container"

        def remove(_name: str) -> None:
            events.append("remove")

        def release(slots: threading.BoundedSemaphore) -> None:
            self.assertIs(slots, token)
            events.append("release")

        with (
            patch.object(common, "acquire_js_container_slot", side_effect=acquire),
            patch.object(common, "release_js_container_slot", side_effect=release),
            patch.object(source_review, "_start_container", side_effect=start),
            patch.object(source_review, "_stage_audit_files"),
            patch.object(
                source_review,
                "_call_model_with_terminal",
                return_value=expected,
            ),
            patch.object(source_review, "_remove_container", side_effect=remove),
        ):
            observed = source_review.review_single(self.review, model="fake")

        self.assertIs(observed, expected)
        self.assertEqual(events, ["acquire", "start", "remove", "release"])

    def test_per_review_deadline_starts_after_container_slot_acquisition(self) -> None:
        clock = [0.0]
        token = threading.BoundedSemaphore(1)
        expected = source_review.SourceReviewVerdict(
            "v8", "123", "audit/poc.js", True, "scoped", "fake"
        )

        def acquire() -> threading.BoundedSemaphore:
            clock[0] = 899.0
            return token

        with (
            patch.object(source_review.time, "monotonic", side_effect=lambda: clock[0]),
            patch.object(common, "acquire_js_container_slot", side_effect=acquire),
            patch.object(common, "release_js_container_slot"),
            patch.object(source_review, "_start_container", return_value="fake") as start,
            patch.object(source_review, "_stage_audit_files"),
            patch.object(source_review, "_call_model_with_terminal", return_value=expected),
            patch.object(source_review, "_remove_container"),
        ):
            observed = source_review.review_single(self.review, model="fake")

        self.assertIs(observed, expected)
        self.assertEqual(start.call_args.kwargs["timeout_sec"], 60)

    def test_non_js_source_review_does_not_consume_a_js_container_slot(self) -> None:
        self.review.project = "linux"
        expected = source_review.SourceReviewVerdict(
            "linux", "1", "audit/poc.js", True, "scoped", "fake"
        )
        with (
            patch.object(common, "acquire_js_container_slot") as acquire,
            patch.object(common, "release_js_container_slot") as release,
            patch.object(source_review, "_start_container", return_value="fake"),
            patch.object(source_review, "_stage_audit_files"),
            patch.object(
                source_review,
                "_call_model_with_terminal",
                return_value=expected,
            ),
            patch.object(source_review, "_remove_container"),
        ):
            observed = source_review.review_single(self.review, model="fake")

        self.assertIs(observed, expected)
        acquire.assert_not_called()
        release.assert_not_called()

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

        def fake_run(command: list[str], **kwargs: object):
            if command[1:3] == ["exec", "--interactive"]:
                target = command[-1].rsplit("audit/", 1)[1]
                copied_names.add(target)
                payload = kwargs["input"]
                assert isinstance(payload, bytes)
                if target in {"poc_execution.json", "solver_trajectory.json"}:
                    json.loads(payload)
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

    def test_oversized_staged_evidence_is_rejected_before_docker_cp(self) -> None:
        self.review.poc_source = "x" * 17
        calls: list[list[str]] = []

        def fake_run(command: list[str], **_kwargs: object):
            calls.append(command)
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        with (
            patch.object(source_review, "MAX_POC_SOURCE_BYTES", 16),
            patch.object(source_review.subprocess, "run", side_effect=fake_run),
            self.assertRaisesRegex(ValueError, "PoC source exceeds"),
        ):
            source_review._stage_audit_files("container", "/src/v8", self.review)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][:2], ["docker", "exec"])

    def test_start_timeout_cleans_up_the_known_container_name(self) -> None:
        timeout = subprocess.TimeoutExpired(["docker", "run"], 1)
        removed = SimpleNamespace(returncode=0, stdout="", stderr="")
        fake_uuid = SimpleNamespace(hex="a" * 32)
        with (
            patch.object(source_review.uuid, "uuid4", return_value=fake_uuid),
            patch.object(source_review.subprocess, "run", side_effect=[timeout, removed]) as run,
            self.assertRaisesRegex(RuntimeError, "could not start"),
        ):
            source_review._start_container(self.review, timeout_sec=1)
        name = "v8-source-review-1-aaaaaaaaaaaa"
        self.assertEqual(
            run.call_args_list[1].args[0], ["docker", "rm", "-f", "-v", name]
        )
        self.assertNotIn(name, source_review.common._active_containers)

    def test_failed_container_removal_remains_registered_for_exit_cleanup(self) -> None:
        name = "source-review-removal-failed"
        source_review.common.register_active_container(name)
        self.addCleanup(source_review.common.unregister_active_container, name)
        failed = SimpleNamespace(returncode=1, stdout="", stderr="daemon unavailable")

        with (
            patch.object(source_review.subprocess, "run", return_value=failed) as run,
            patch.object(source_review.time, "sleep"),
        ):
            source_review._remove_container(name)

        self.assertEqual(run.call_count, 3)
        self.assertIn(name, source_review.common._active_containers)

    def test_global_cleanup_keeps_failed_removals_registered(self) -> None:
        name = "grade-cleanup-retry-fixture"
        grade.add_container(name)
        self.addCleanup(grade.discard_container, name)
        failed = subprocess.CompletedProcess(
            ["docker", "rm", "-f", "-v", name], 1, "", "daemon unavailable"
        )

        with (
            patch.object(grade.subprocess, "run", return_value=failed) as run,
            patch.object(grade.time, "sleep"),
        ):
            grade.cleanup_active_containers()

        self.assertEqual(run.call_count, 3)
        self.assertIn(name, source_review.common._active_containers)

    def test_overall_deadline_includes_container_start_and_staging(self) -> None:
        def delayed_start(*_args: object, **_kwargs: object) -> str:
            time.sleep(0.02)
            return "fake"

        with (
            patch.object(source_review, "_start_container", side_effect=delayed_start),
            patch.object(source_review, "_stage_audit_files") as stage,
            patch.object(source_review, "_call_model_with_terminal") as model_call,
            patch.object(source_review, "_remove_container") as cleanup,
        ):
            verdict = source_review.review_single(
                self.review, model="fake", overall_timeout_sec=0.001
            )
        self.assertIsNone(verdict.in_scope)
        self.assertIn("deadline expired", verdict.error)
        stage.assert_not_called()
        model_call.assert_not_called()
        cleanup.assert_called_once_with("fake")

    def test_trajectory_symlink_is_not_followed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            instance = root / "instance"
            trajectory = instance / "trajectory"
            trajectory.mkdir(parents=True)
            secret = root / "secret.json"
            secret.write_text('{"secret":"must not leak"}')
            (trajectory / "session.json").symlink_to(secret)
            with self.assertRaisesRegex(ValueError, "not a real regular file"):
                source_review.load_solver_trajectory(instance)

    def test_oversized_trajectory_is_rejected_from_file_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            instance = Path(temp_dir) / "instance"
            trajectory = instance / "trajectory"
            trajectory.mkdir(parents=True)
            oversized = trajectory / "session.json"
            with oversized.open("wb") as fh:
                fh.truncate(source_review.MAX_SOLVER_TRAJECTORY_BYTES + 1)
            with self.assertRaisesRegex(ValueError, "trajectory exceeds"):
                source_review.load_solver_trajectory(instance)

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
        def successful_terminal(
            _container: str,
            _work_dir: str,
            command: str,
            timeout: int,
            *,
            purpose: str = "model",
        ) -> source_review.TerminalCall:
            return source_review.TerminalCall(
                command, timeout, 0, False, "evidence", "", purpose
            )

        with (
            patch.object(source_review, "_completion_with_retries", side_effect=responses) as completion,
            patch.object(source_review, "_run_terminal", side_effect=successful_terminal),
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
        self.assertEqual(
            [call.purpose for call in verdict.transcript],
            [
                "required_evidence:task_statement",
                "required_evidence:poc_execution",
                "model",
            ],
        )
        history = completion.call_args_list[1].args[0]["messages"]
        self.assertEqual(history[1]["thinking_blocks"], thinking)
        tool_payload = json.loads(history[2]["content"])
        self.assertIn("required_evidence", tool_payload)
        self.assertIn("command_result", tool_payload)
        self.assertEqual(
            completion.call_args_list[0].args[0]["max_tokens"],
            source_review.MAX_MODEL_OUTPUT_TOKENS,
        )
        self.assertIn("before_request", completion.call_args_list[0].kwargs)

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
                    evidence_calls = {
                        label: source_review.TerminalCall(
                            command,
                            30,
                            0,
                            False,
                            label,
                            "",
                            f"required_evidence:{label}",
                        )
                        for label, command in source_review.REQUIRED_EVIDENCE_COMMANDS.items()
                    }

                    def terminal_side_effect(
                        _container: str,
                        _work_dir: str,
                        _command: str,
                        _timeout: int,
                        *,
                        purpose: str = "model",
                    ) -> source_review.TerminalCall:
                        if purpose.startswith("required_evidence:"):
                            return evidence_calls[purpose.split(":", 1)[1]]
                        return failed_call

                    with (
                        patch.object(source_review, "_start_container", return_value="fake"),
                        patch.object(source_review, "_stage_audit_files"),
                        patch.object(source_review, "_remove_container") as cleanup,
                        patch.object(source_review, "_completion_with_retries", side_effect=responses),
                        patch.object(source_review, "_run_terminal", side_effect=terminal_side_effect),
                        patch.object(source_review, "_usage", return_value=(0, 0, 0, 0.0)),
                    ):
                        verdict = source_review.review_single(self.review, model="fake")
                    self.assertIsNone(verdict.in_scope)
                    self.assertIn("no successful terminal calls", verdict.error)
                    self.assertEqual(
                        verdict.transcript,
                        [*evidence_calls.values(), failed_call],
                    )
                    cleanup.assert_called_once_with("fake")

    def test_inner_terminal_timeout_is_reported_as_timeout(self) -> None:
        with patch.object(
            source_review,
            "_run_bounded_subprocess",
            return_value=(124, False, "partial", ""),
        ):
            call = source_review._run_terminal("fake", "/src/example", "pwd", 1)
        self.assertTrue(call.timed_out)
        self.assertEqual(json.loads(source_review._tool_result_content(call))["exit_code"], "timeout")

    def test_missing_timeout_tool_fails_closed_before_running_the_command(self) -> None:
        captured: dict[str, object] = {}

        def bounded(command: list[str], timeout_sec: int):
            captured["command"] = command
            captured["timeout_sec"] = timeout_sec
            return (
                125,
                False,
                "",
                "source-review terminal unavailable: timeout command not found\n",
            )

        with patch.object(source_review, "_run_bounded_subprocess", side_effect=bounded):
            call = source_review._run_terminal(
                "fake", "/src/example", "touch /tmp/must-not-run", 3
            )

        wrapper = next(
            part
            for part in captured["command"]  # type: ignore[union-attr]
            if "timeout command not found" in part
        )
        self.assertIn("timeout command not found", wrapper)
        self.assertNotIn("else exec sh", wrapper)
        self.assertEqual(captured["timeout_sec"], 13)
        self.assertEqual(call.exit_code, 125)
        self.assertFalse(call.timed_out)
        self.assertIn("timeout command not found", call.stderr)

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

    def test_source_review_retry_timeout_shrinks_with_overall_deadline(self) -> None:
        import litellm

        clock = [0.0]
        observed_timeouts: list[float] = []

        def completion(**kwargs: object):
            observed_timeouts.append(float(kwargs["timeout"]))
            if len(observed_timeouts) == 1:
                clock[0] = 9.0
                raise RuntimeError("503 service unavailable")
            return object()

        with (
            patch.object(litellm, "completion", side_effect=completion),
            patch.object(source_review.time, "monotonic", side_effect=lambda: clock[0]),
            patch.object(source_review.time, "sleep"),
        ):
            source_review._completion_with_retries(
                {"timeout": 120.0}, deadline=10.0
            )

        self.assertEqual(observed_timeouts, [10.0, 1.0])

    def test_source_review_provider_retries_have_a_per_instance_call_cap(self) -> None:
        import litellm

        common.configure_js_grading_budget(time_budget_sec=60, llm_call_budget=64)
        self.addCleanup(common.clear_js_grading_budget)
        with (
            patch.object(source_review, "MAX_MODEL_CALLS", 2),
            patch.object(
                litellm,
                "completion",
                side_effect=RuntimeError("503 service unavailable"),
            ) as completion,
            patch.object(source_review.time, "sleep"),
            self.assertRaisesRegex(RuntimeError, "exceeded 2 model calls"),
        ):
            source_review._call_model_with_terminal(
                self.review,
                container_name="fake",
                model="fake",
                reasoning_effort="high",
                max_turns=source_review.DEFAULT_MAX_TURNS,
                terminal_timeout_sec=30,
            )
        self.assertEqual(completion.call_count, 2)

    def test_exhausted_global_call_budget_skips_source_container_setup(self) -> None:
        common.configure_js_grading_budget(time_budget_sec=60, llm_call_budget=1)
        self.addCleanup(common.clear_js_grading_budget)
        common.consume_js_llm_call("test setup")
        with patch.object(source_review, "_start_container") as start:
            verdict = source_review.review_single(self.review, model="fake")
        self.assertIsNone(verdict.in_scope)
        self.assertIn("LLM-call budget exhausted", verdict.error)
        start.assert_not_called()

    def test_source_review_rejects_turn_counts_above_the_hard_cap(self) -> None:
        with self.assertRaisesRegex(ValueError, "max_turns must be between"):
            source_review._call_model_with_terminal(
                self.review,
                container_name="fake",
                model="fake",
                reasoning_effort="high",
                max_turns=source_review.DEFAULT_MAX_TURNS + 1,
                terminal_timeout_sec=30,
            )


class ImagePinningTests(unittest.TestCase):
    def test_pin_image_id_accepts_only_a_full_content_id(self) -> None:
        image_id = "sha256:" + "a" * 64
        with (
            patch.object(grade, "ensure_image", return_value=True) as ensure,
            patch.object(
                grade,
                "run_interruptible_command",
                return_value=SimpleNamespace(
                    exit_code=0, stdout=f"{image_id}\n", stderr=""
                ),
            ) as inspect,
        ):
            self.assertEqual(
                grade.pin_image_id("mutable:image", pull_missing=False), image_id
            )

        ensure.assert_called_once_with("mutable:image", pull_missing=False)
        self.assertEqual(
            inspect.call_args.args[0],
            [
                "docker",
                "image",
                "inspect",
                "--format",
                "{{.Id}}",
                "mutable:image",
            ],
        )

    def test_pin_image_id_fails_closed_for_missing_or_malformed_images(self) -> None:
        with (
            patch.object(grade, "ensure_image", return_value=False),
            patch.object(grade, "run_interruptible_command") as inspect,
        ):
            self.assertIsNone(
                grade.pin_image_id("missing:image", pull_missing=False)
            )
        inspect.assert_not_called()

        for stdout, exit_code in (
            ("mutable:image\n", 0),
            ("sha256:abc\n", 0),
            ("sha256:" + "b" * 64 + "\n", 1),
        ):
            with (
                self.subTest(stdout=stdout, exit_code=exit_code),
                patch.object(grade, "ensure_image", return_value=True),
                patch.object(
                    grade,
                    "run_interruptible_command",
                    return_value=SimpleNamespace(
                        exit_code=exit_code, stdout=stdout, stderr="inspect failed"
                    ),
                ),
                patch.object(grade, "_print"),
            ):
                self.assertIsNone(
                    grade.pin_image_id("mutable:image", pull_missing=False)
                )

    def test_process_instance_passes_pinned_vulnerable_id_to_first_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            instance = root / "run" / "123"
            audit = instance / "audit"
            audit.mkdir(parents=True)
            poc = audit / "poc.js"
            poc.write_text("print(1)\n")
            benchmark = root / "benchmark" / "123"
            benchmark.mkdir(parents=True)
            (benchmark / "meta.json").write_text(
                json.dumps(
                    {
                        "image_name": "mutable:vulnerable",
                        "work_dir": "/src/v8",
                        "verification_binary": "out/d8",
                        "command_options": "",
                        "target_vulnerability_type": "TYPE_CONFUSION",
                        "error_type": "ASAN_CRASH",
                    }
                )
            )
            image_id = "sha256:" + "c" * 64

            with (
                patch.object(grade, "pin_image_id", return_value=image_id),
                patch.object(
                    grade,
                    "process_file",
                    return_value=grade.FileResult("audit/poc.js"),
                ) as process,
            ):
                result = grade.process_instance(
                    project="v8",
                    benchmark_dir=root / "benchmark",
                    instance_dir=instance,
                    timeout_sec=1,
                    attempts=1,
                    fixed_repo="mutable/fixed",
                    latest_image=None,
                    latest_repo=None,
                    pull_missing=False,
                )

            self.assertEqual(result.vuln_image_id, image_id)
            self.assertEqual(process.call_args.kwargs["vuln_image"], image_id)

    def test_later_js_phases_pin_and_execute_both_content_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            instance_dir = root / "run" / "123"
            result_dir = instance_dir / "result"
            result_dir.mkdir(parents=True)
            (result_dir / "run_config.txt").write_text("")
            benchmark = root / "benchmark" / "123"
            benchmark.mkdir(parents=True)
            (benchmark / "meta.json").write_text(
                json.dumps(
                    {
                        "work_dir": "/src/v8",
                        "verification_binary": "out/d8",
                        "command_options": "",
                    }
                )
            )
            stdout = result_dir / "stdout.log"
            stderr = result_dir / "stderr.log"
            stdout.write_text("")
            stderr.write_text("")
            tree_digest = "d" * 64
            candidate = grade.FileResult(
                "audit/poc.js",
                vuln=grade.ExecResult(
                    "vuln",
                    1,
                    False,
                    stdout,
                    stderr,
                    engine_started=True,
                    input_tree_sha256=tree_digest,
                ),
                poc_source="print(1)\n",
                poc_sha256="e" * 64,
            )
            instance = grade.InstanceResult(
                "v8",
                "123",
                "ASAN_CRASH",
                "TYPE_CONFUSION",
                "mutable:vulnerable",
                "mutable:fixed",
                "mutable:latest",
                vuln_image_id="sha256:" + "a" * 64,
                status="checked",
                file_results=[candidate],
            )
            ids = {
                "mutable:fixed": "sha256:" + "f" * 64,
                "mutable:latest": "sha256:" + "9" * 64,
            }

            def execute(**kwargs: object) -> grade.ExecResult:
                kind = str(kwargs["image_kind"])
                return grade.ExecResult(
                    kind, 0, False, stdout, stderr, engine_started=True
                )

            with (
                patch.object(
                    grade,
                    "pin_image_id",
                    side_effect=lambda image, **_kwargs: ids[image],
                ) as pin,
                patch.object(
                    grade, "run_js_with_retries", side_effect=execute
                ) as run,
            ):
                for kind in ("fixed", "latest"):
                    grade.run_js_image_phase(
                        image_kind=kind,
                        project="v8",
                        results=[instance],
                        instance_dirs=[instance_dir],
                        benchmark_dir=root / "benchmark",
                        timeout_sec=1,
                        attempts=1,
                        workers=1,
                        pull_missing=False,
                        model="fake",
                        eligible=lambda _file: True,
                    )

            self.assertEqual(pin.call_count, 2)
            self.assertEqual(
                [call.kwargs["image"] for call in run.call_args_list],
                [ids["mutable:fixed"], ids["mutable:latest"]],
            )
            for call in run.call_args_list:
                self.assertEqual(
                    call.kwargs["expected_input_tree_sha256"], tree_digest
                )


class JsEngineRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_cwd = Path.cwd()

    def tearDown(self) -> None:
        os.chdir(self.original_cwd)

    def test_engine_receives_writable_cache_environment(self) -> None:
        class FakeProcess:
            pid = 424242

            @staticmethod
            def wait(timeout: float | None = None) -> int:
                del timeout
                return 0

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source"
            source.mkdir()
            poc = source / "secb-selected-poc.js"
            poc.write_text("BENIGN_INPUT\n", encoding="utf-8")
            expected_sha256 = hashlib.sha256(poc.read_bytes()).hexdigest()
            status = root / "status" / "engine-status.json"

            with (
                patch.object(
                    js_engine_runner.subprocess,
                    "Popen",
                    return_value=FakeProcess(),
                ) as popen,
                patch.object(js_engine_runner.os, "killpg"),
            ):
                result = js_engine_runner.main(
                    [
                        "--cwd",
                        str(root),
                        "--status-file",
                        str(status),
                        "--timeout-sec",
                        "1",
                        "--input-root",
                        str(source),
                        "--staged-input-root",
                        str(root / "staged"),
                        "--required-input",
                        poc.name,
                        "--required-input-sha256",
                        expected_sha256,
                        "--execution-input-relative-path",
                        "audit/poc.js",
                        "--",
                        "/bin/true",
                        str(poc),
                    ]
                )

            self.assertEqual(result, 0)
            environment = popen.call_args.kwargs["env"]
            self.assertEqual(environment["HOME"], "/tmp")
            self.assertEqual(environment["TMPDIR"], "/tmp")
            self.assertEqual(environment["XDG_CACHE_HOME"], "/tmp/.cache")
            self.assertEqual(
                popen.call_args.args[0][-1],
                str(root / "staged" / "audit" / "poc.js"),
            )

    def test_internal_input_name_does_not_collide_with_submitted_parent_path(self) -> None:
        class FakeProcess:
            pid = 424242

            @staticmethod
            def wait(timeout: float | None = None) -> int:
                del timeout
                return 0

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source"
            source.mkdir()
            poc = source / "secb-selected-poc.js"
            poc.write_text("BENIGN_INPUT\n", encoding="utf-8")
            expected_sha256 = hashlib.sha256(poc.read_bytes()).hexdigest()
            status = root / "status" / "engine-status.json"
            staged = root / "staged"
            submitted_path = "secb-selected-poc.js/nested/poc.js"

            with (
                patch.object(
                    js_engine_runner.subprocess,
                    "Popen",
                    return_value=FakeProcess(),
                ) as popen,
                patch.object(js_engine_runner.os, "killpg"),
            ):
                result = js_engine_runner.main(
                    [
                        "--cwd",
                        str(root),
                        "--status-file",
                        str(status),
                        "--timeout-sec",
                        "1",
                        "--input-root",
                        str(source),
                        "--staged-input-root",
                        str(staged),
                        "--required-input",
                        poc.name,
                        "--required-input-sha256",
                        expected_sha256,
                        "--execution-input-relative-path",
                        submitted_path,
                        "--",
                        "/bin/true",
                        str(poc),
                    ]
                )

            relocated = staged / submitted_path
            self.assertEqual(result, 0)
            self.assertEqual(relocated.read_text(encoding="utf-8"), "BENIGN_INPUT\n")
            self.assertEqual(popen.call_args.args[0][-1], str(relocated))
            self.assertFalse(
                (root / ".secb-trusted-selected-input" / poc.name).exists()
            )

    def test_required_input_tree_digest_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source"
            source.mkdir()
            (source / "poc.js").write_text("BENIGN_INPUT\n")

            first = js_engine_runner._copy_input_tree(
                source, root / "first", "poc.js"
            )
            second = js_engine_runner._copy_input_tree(
                source, root / "second", "poc.js"
            )

            self.assertRegex(first, r"^[0-9a-f]{64}$")
            self.assertEqual(second, first)

    def test_required_input_tree_digest_detects_selected_poc_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source"
            source.mkdir()
            poc = source / "poc.js"
            poc.write_text("FIRST_INPUT\n")
            accepted = js_engine_runner._copy_input_tree(
                source, root / "accepted", "poc.js"
            )
            poc.write_text("CHANGED_INPUT\n")
            changed = js_engine_runner._copy_input_tree(
                source, root / "changed", "poc.js"
            )

            self.assertNotEqual(changed, accepted)
            with self.assertRaisesRegex(
                js_engine_runner.InputIntegrityError,
                "does not match the vulnerable execution snapshot",
            ):
                js_engine_runner._verify_input_tree_digest(changed, accepted)

    def test_required_only_staging_excludes_unvalidated_siblings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source"
            source.mkdir()
            (source / "poc.js").write_text("VISIBLE_POC\n")
            helper = source / "helper.js"
            helper.write_text("HIDDEN_HELPER_FIRST\n")
            first_destination = root / "first"
            first = js_engine_runner._copy_input_tree(
                source, first_destination, "poc.js"
            )
            helper.write_text("HIDDEN_HELPER_CHANGED\n")
            second_destination = root / "second"
            second = js_engine_runner._copy_input_tree(
                source, second_destination, "poc.js"
            )

            self.assertEqual(first, second)
            self.assertEqual(
                sorted(path.name for path in first_destination.iterdir()),
                ["poc.js"],
            )
            self.assertFalse((second_destination / "helper.js").exists())

    def test_parent_staging_failure_is_reported_as_input_integrity_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            status = root / "status.json"
            result = js_engine_runner.main(
                [
                    "--cwd",
                    str(root),
                    "--status-file",
                    str(status),
                    "--timeout-sec",
                    "1",
                    "--input-root",
                    str(root / "missing-parent" / "audit"),
                    "--staged-input-root",
                    str(root / "staged"),
                    "--required-input",
                    "poc.js",
                    "--required-input-sha256",
                    "0" * 64,
                    "--execution-input-relative-path",
                    "audit/poc.js",
                    "--",
                    "/bin/true",
                ]
            )

            self.assertEqual(result, 126)
            payload = json.loads(status.read_text())
            self.assertFalse(payload["engine_started"])
            self.assertTrue(payload["input_integrity_error"])
            self.assertIn("could not stage the accepted input tree", payload["infrastructure_error"])

    def test_input_root_intermediate_swap_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            anchor = root / "anchor"
            source = anchor / "nested" / "source"
            source.mkdir(parents=True)
            (source / "poc.js").write_text("BENIGN_INPUT\n")
            outside = root / "outside"
            (outside / "source").mkdir(parents=True)
            (outside / "source" / "poc.js").write_text("ROOT_ONLY_SECRET\n")
            destination = root / "destination"
            original_nested = anchor / "nested"
            moved_nested = anchor / "moved-nested"
            real_open = js_engine_runner.os.open
            swapped = False

            def swapping_open(
                path: object,
                flags: int,
                mode: int = 0o777,
                *,
                dir_fd: int | None = None,
            ) -> int:
                nonlocal swapped
                if path == "nested" and dir_fd is not None and not swapped:
                    original_nested.rename(moved_nested)
                    original_nested.symlink_to(outside, target_is_directory=True)
                    swapped = True
                return real_open(path, flags, mode, dir_fd=dir_fd)  # type: ignore[arg-type]

            with (
                patch.object(js_engine_runner.os, "open", side_effect=swapping_open),
                self.assertRaisesRegex(ValueError, "input root is not a safe directory"),
            ):
                js_engine_runner._copy_input_tree(source, destination)

            self.assertTrue(swapped)
            self.assertFalse((destination / "poc.js").exists())

    def test_directory_swap_cannot_redirect_descriptor_relative_copy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source"
            original_directory = source / "nested"
            original_directory.mkdir(parents=True)
            (original_directory / "poc.js").write_text("BENIGN_INPUT\n")
            outside = root / "outside"
            outside.mkdir()
            (outside / "poc.js").write_text("ROOT_ONLY_SECRET\n")
            destination = root / "destination"
            moved_directory = source / "moved"
            real_open = js_engine_runner.os.open
            swapped = False

            def swapping_open(
                path: object,
                flags: int,
                mode: int = 0o777,
                *,
                dir_fd: int | None = None,
            ) -> int:
                nonlocal swapped
                if path == "poc.js" and dir_fd is not None and not swapped:
                    original_directory.rename(moved_directory)
                    original_directory.symlink_to(outside, target_is_directory=True)
                    swapped = True
                return real_open(path, flags, mode, dir_fd=dir_fd)  # type: ignore[arg-type]

            with patch.object(js_engine_runner.os, "open", side_effect=swapping_open):
                js_engine_runner._copy_input_tree(source, destination)

            self.assertTrue(swapped)
            self.assertEqual(
                (destination / "nested" / "poc.js").read_text(), "BENIGN_INPUT\n"
            )
            self.assertNotIn(
                "ROOT_ONLY_SECRET",
                (destination / "nested" / "poc.js").read_text(),
            )


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
                        vuln=grade.ExecResult(
                            "vuln", 1, False, stdout, stderr, engine_started=True
                        ),
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
                            engine_started=True,
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
