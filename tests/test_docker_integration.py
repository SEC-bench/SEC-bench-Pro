"""Opt-in Docker integration tests for JavaScript grading and source review.

These tests build a small network-independent image from the test host's local
BusyBox, shell, and Python runtime. They are intentionally excluded from normal
unit-test runs; set ``SECB_RUN_DOCKER_INTEGRATION=1`` to use the real daemon.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import signal
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import time
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness"))

import common  # noqa: E402
import grade  # noqa: E402
import source_review  # noqa: E402


RUN_DOCKER_INTEGRATION = os.environ.get("SECB_RUN_DOCKER_INTEGRATION") == "1"


@unittest.skipUnless(
    RUN_DOCKER_INTEGRATION,
    "set SECB_RUN_DOCKER_INTEGRATION=1 to run real Docker integration tests",
)
class DockerIntegrationTests(unittest.TestCase):
    """Exercise the Docker CLI boundaries without downloading a base image."""

    fixture_image: str
    fixture_without_timeout_image: str
    run_token: str

    @staticmethod
    def _copy_runtime_dependency(path: str, rootfs: Path) -> None:
        """Copy one absolute runtime path while preserving its loader-visible name."""
        normalised = Path(os.path.normpath(path))
        if not normalised.is_absolute() or not normalised.exists():
            return
        destination = rootfs / normalised.relative_to("/")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(normalised.resolve(), destination)

    @classmethod
    def _copy_elf_dependencies(cls, binary: Path, rootfs: Path) -> None:
        """Copy dependencies reported by ldd for a local ELF executable/module."""
        result = subprocess.run(
            ["ldd", str(binary)],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=30,
        )
        if result.returncode != 0:
            if (
                "not a dynamic executable" in result.stderr
                or "statically linked" in result.stdout
            ):
                return
            raise RuntimeError(
                f"could not inspect runtime dependencies for {binary}: {result.stderr}"
            )
        for line in result.stdout.splitlines():
            match = re.search(r"=>\s+(/\S+)", line)
            if match is None:
                match = re.match(r"\s*(/\S+)\s+\(", line)
            if match is not None:
                cls._copy_runtime_dependency(match.group(1), rootfs)

    @classmethod
    def _populate_python_runtime(cls, context: Path, busybox: str) -> None:
        """Create a compact Python/BusyBox rootfs from the already-local test host."""
        rootfs = context / "rootfs"
        busybox_target = rootfs / "bin" / "busybox"
        busybox_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(busybox, busybox_target)
        cls._copy_elf_dependencies(Path(busybox), rootfs)

        shell = shutil.which("dash") or shutil.which("bash")
        if shell is None:
            raise RuntimeError("the Docker integration fixture requires dash or bash")
        shell_target = rootfs / "bin" / "fixture-sh"
        shutil.copy2(Path(shell).resolve(), shell_target)
        cls._copy_elf_dependencies(Path(shell).resolve(), rootfs)

        python_binary = Path(sys.executable).resolve()
        python_target = rootfs / python_binary.relative_to("/")
        python_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(python_binary, python_target)
        cls._copy_elf_dependencies(python_binary, rootfs)

        stdlib = Path(sysconfig.get_path("stdlib")).resolve()
        stdlib_target = rootfs / stdlib.relative_to("/")
        shutil.copytree(
            stdlib,
            stdlib_target,
            symlinks=False,
            ignore=shutil.ignore_patterns(
                "__pycache__",
                "*.pyc",
                "site-packages",
                "dist-packages",
                "test",
                "tests",
                "idlelib",
                "tkinter",
                "turtledemo",
                "ensurepip",
                "venv",
            ),
        )
        for extension in stdlib_target.rglob("*.so"):
            cls._copy_elf_dependencies(extension, rootfs)

        python_entrypoint = rootfs / "usr" / "bin" / "python3"
        python_entrypoint.parent.mkdir(parents=True, exist_ok=True)
        if python_entrypoint != python_target:
            python_entrypoint.symlink_to(python_binary)

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.run_token = uuid.uuid4().hex[:12]
        cls.fixture_image = f"secbench-docker-integration-{cls.run_token}:fixture"
        cls.fixture_without_timeout_image = (
            f"secbench-docker-integration-{cls.run_token}:no-timeout"
        )

        docker = subprocess.run(
            ["docker", "version", "--format", "{{.Server.Version}}"],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=30,
        )
        if docker.returncode != 0:
            raise RuntimeError(f"Docker daemon is unavailable: {docker.stderr.strip()}")

        busybox = shutil.which("busybox")
        if busybox is None:
            raise RuntimeError("the Docker integration fixture requires a local busybox")

        cls._fixture_temp = tempfile.TemporaryDirectory(
            prefix="secbench-docker-integration-build-"
        )
        cls.addClassCleanup(cls._fixture_temp.cleanup)
        context = Path(cls._fixture_temp.name)
        cls._populate_python_runtime(context, busybox)

        engine = context / "engine"
        engine.write_text(
            """#!/bin/sh
set -eu
last_arg=""
for arg in "$@"; do
    last_arg="$arg"
done
printf 'fixture-host='
cat /etc/hostname
printf 'fixture-argv'
for arg in "$@"; do
    printf ' <%s>' "$arg"
done
printf '\n'
awk '$1 == "CapEff:" { print "fixture-cap-eff=" $2 }' /proc/self/status
printf 'fixture-home=%s\n' "$HOME"
printf 'fixture-tmpdir=%s\n' "$TMPDIR"
printf 'fixture-xdg-cache-home=%s\n' "$XDG_CACHE_HOME"
input_mode="$(stat -c '%a' "$last_arg")"
printf 'fixture-input-mode=%s\n' "$input_mode"
if [ -e "${last_arg%/*}/helper.js" ]; then
    printf 'fixture-helper-visible=yes\n'
else
    printf 'fixture-helper-visible=no\n'
fi
if cat /secb-selected-poc.js >/dev/null 2>&1; then
    printf 'fixture-private-input-readable=yes\n'
else
    printf 'fixture-private-input-readable=no\n'
fi
if touch /secb-grader-status/engine-owned >/dev/null 2>&1; then
    printf 'fixture-private-status-writable=yes\n'
else
    printf 'fixture-private-status-writable=no\n'
fi
mode="$(cat "$last_arg")"
case "$mode" in
    *OOM*) exec /usr/bin/python3 -c 'chunks = []; [(chunks.append(bytearray(8 * 1024 * 1024))) for _ in iter(int, 1)]' ;;
    *EXIT_124*) exit 124 ;;
    *EXIT_125*) exit 125 ;;
    *MIDDLE_MARKER*)
        /usr/bin/python3 -c "import sys; sys.stderr.write('a' * 1100000 + 'SUMMARY: AddressSanitizer: heap-use-after-free\\n' + 'z' * 1100000)"
        exit 1
        ;;
    *INSPECT_HOLD*) sleep 5 ;;
    *TIMEOUT*) exec sleep 30 ;;
    *) exit 0 ;;
esac
""",
            encoding="utf-8",
        )
        engine.chmod(0o755)

        sleep_wrapper = context / "sleep"
        sleep_wrapper.write_text(
            """#!/bin/sh
if [ "${1:-}" = "infinity" ]; then
    while :; do
        /bin/busybox sleep 86400
    done
fi
exec /bin/busybox sleep "$@"
""",
            encoding="utf-8",
        )
        sleep_wrapper.chmod(0o755)

        timeout_wrapper = context / "timeout"
        timeout_wrapper.write_text(
            """#!/usr/bin/python3
import os
import signal
import subprocess
import sys


def seconds(value):
    return float(value[:-1] if value.endswith("s") else value)


arguments = sys.argv[1:]
grace = 5.0
if arguments and arguments[0].startswith("--kill-after="):
    grace = seconds(arguments.pop(0).split("=", 1)[1])
if len(arguments) < 2:
    raise SystemExit(125)
duration = seconds(arguments.pop(0))
try:
    child = subprocess.Popen(arguments, start_new_session=True)
except OSError as exc:
    print(f"timeout: {exc}", file=sys.stderr)
    raise SystemExit(125)
try:
    status = child.wait(timeout=duration)
except subprocess.TimeoutExpired:
    try:
        os.killpg(child.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        child.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        child.wait()
    raise SystemExit(124)
raise SystemExit(status if status >= 0 else 128 - status)
""",
            encoding="utf-8",
        )
        timeout_wrapper.chmod(0o755)

        (context / "assigned.cc").write_text(
            "// fixture assigned source sentinel\n", encoding="utf-8"
        )
        (context / "stale.txt").write_text(
            "this file must be removed before staging\n", encoding="utf-8"
        )
        (context / "Dockerfile").write_text(
            """FROM scratch
COPY rootfs /
RUN ["/bin/busybox", "--install", "-s", "/bin"]
COPY engine /workspace/engine
COPY sleep /usr/local/bin/sleep
COPY timeout /usr/local/bin/timeout
RUN ["/bin/busybox", "rm", "/bin/timeout", "/bin/sleep", "/bin/sh"]
RUN ["/bin/busybox", "ln", "-s", "/usr/local/bin/sleep", "/bin/sleep"]
RUN ["/bin/busybox", "ln", "-s", "/bin/fixture-sh", "/bin/sh"]
COPY assigned.cc /workspace/src/assigned.cc
COPY stale.txt /workspace/audit/stale.txt
ENV PATH=/usr/local/bin:/bin
WORKDIR /workspace
""",
            encoding="utf-8",
        )

        cls.addClassCleanup(cls._remove_fixture_images)
        built = subprocess.run(
            [
                "docker",
                "build",
                "--network",
                "none",
                "--pull=false",
                "--tag",
                cls.fixture_image,
                str(context),
            ],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=180,
        )
        if built.returncode != 0:
            raise RuntimeError(
                "fixture image build failed:\n"
                f"stdout:\n{built.stdout}\n"
                f"stderr:\n{built.stderr}"
            )

        no_timeout_context = context / "no-timeout"
        no_timeout_context.mkdir()
        (no_timeout_context / "Dockerfile").write_text(
            f"""FROM {cls.fixture_image}
RUN ["/bin/busybox", "rm", "-f", "/usr/local/bin/timeout", "/bin/timeout"]
""",
            encoding="utf-8",
        )
        built_without_timeout = subprocess.run(
            [
                "docker",
                "build",
                "--network",
                "none",
                "--pull=false",
                "--tag",
                cls.fixture_without_timeout_image,
                str(no_timeout_context),
            ],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=60,
        )
        if built_without_timeout.returncode != 0:
            raise RuntimeError(
                "fixture image without timeout build failed:\n"
                f"stdout:\n{built_without_timeout.stdout}\n"
                f"stderr:\n{built_without_timeout.stderr}"
            )

    @classmethod
    def _remove_fixture_images(cls) -> None:
        for image in (cls.fixture_without_timeout_image, cls.fixture_image):
            subprocess.run(
                ["docker", "image", "rm", "--force", image],
                capture_output=True,
                timeout=60,
            )

    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(
            prefix=f"secbench-docker-integration-{self.run_token}-"
        )
        self.addCleanup(temporary.cleanup)
        self._temporary = temporary
        Path(temporary.name).chmod(0o755)
        self.instance_dir = Path(temporary.name) / f"instance-{uuid.uuid4().hex[:10]}"
        (self.instance_dir / "audit").mkdir(parents=True)
        self.result_dir = self.instance_dir / "result"
        self.addCleanup(self._remove_test_containers)

    def _docker(self, *args: str, timeout: int = 30) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["docker", *args],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
        )

    def _matching_container_names(self) -> list[str]:
        result = self._docker("ps", "--all", "--format", "{{.Names}}")
        self.assertEqual(result.returncode, 0, result.stderr)
        return [
            name
            for name in result.stdout.splitlines()
            if self.instance_dir.name in name or self.run_token in name
        ]

    def _remove_test_containers(self) -> None:
        result = subprocess.run(
            ["docker", "ps", "--all", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=30,
        )
        if result.returncode != 0:
            return
        for name in result.stdout.splitlines():
            if self.instance_dir.name in name or self.run_token in name:
                subprocess.run(
                    ["docker", "rm", "--force", "--volumes", name],
                    capture_output=True,
                    timeout=30,
                )

    def _run_js(
        self,
        source: str,
        *,
        attempt: int = 1,
        binary: str = "engine",
        timeout_sec: int = 5,
    ) -> grade.ExecResult:
        poc = self.instance_dir / "audit" / "poc.js"
        poc.write_text(source, encoding="utf-8")
        poc.chmod(0o600)
        return self._invoke_js(
            attempt=attempt,
            binary=binary,
            timeout_sec=timeout_sec,
        )

    def _invoke_js(
        self,
        *,
        attempt: int = 1,
        binary: str = "engine",
        timeout_sec: int = 5,
        rel_path: str = "audit/poc.js",
    ) -> grade.ExecResult:
        return grade.run_js_once(
            project="v8",
            image=self.fixture_image,
            image_kind="vuln",
            instance_dir=self.instance_dir,
            rel_path=rel_path,
            work_dir="/workspace",
            binary=binary,
            options=["--fixture-flag=value", "argument with spaces"],
            timeout_sec=timeout_sec,
            result_dir=self.result_dir,
            attempt=attempt,
        )

    def test_long_poc_basename_has_a_bounded_execution_log_name(self) -> None:
        name = "poc-" + "a" * 244 + ".js"
        poc = self.instance_dir / "audit" / name
        poc.write_text("NORMAL_EXIT\n", encoding="utf-8")
        poc.chmod(0o600)

        result = self._invoke_js(rel_path=f"audit/{name}")

        self.assertEqual(result.exit_code, 0, result.infrastructure_error)
        self.assertTrue(result.engine_started)
        self.assertLessEqual(len(result.stdout_log.name.encode("utf-8")), 255)
        self.assertLessEqual(len(result.stderr_log.name.encode("utf-8")), 255)
        self.assertTrue(result.stdout_log.is_file())
        self.assertTrue(result.stderr_log.is_file())
        self.assertEqual(self._matching_container_names(), [])

    def test_submitted_path_can_descend_from_internal_input_filename(self) -> None:
        rel_path = "secb-selected-poc.js/nested/poc.js"
        poc = self.instance_dir / rel_path
        poc.parent.mkdir(parents=True)
        poc.write_text("NORMAL_EXIT\n", encoding="utf-8")
        poc.chmod(0o600)

        result = self._invoke_js(rel_path=rel_path)

        diagnostic = (
            f"stderr={result.stderr_log.read_text(encoding='utf-8')!r}; "
            f"infra={result.infrastructure_error!r}"
        )
        self.assertEqual(result.exit_code, 0, diagnostic)
        self.assertTrue(result.engine_started)
        self.assertEqual(result.infrastructure_error, "")
        stdout = result.stdout_log.read_text(encoding="utf-8")
        self.assertIn(
            "</tmp/secb-eval-instance/secb-selected-poc.js/nested/poc.js>",
            stdout,
        )
        self.assertIn("fixture-input-mode=444", stdout)
        self.assertIn("fixture-private-input-readable=no", stdout)
        self.assertEqual(self._matching_container_names(), [])

    @staticmethod
    def _fixture_hostname(result: grade.ExecResult) -> str:
        stdout = result.stdout_log.read_text(encoding="utf-8")
        match = re.search(r"^fixture-host=([0-9a-f]+)$", stdout, re.MULTILINE)
        if match is None:
            raise AssertionError(f"fixture hostname missing from stdout: {stdout!r}")
        return match.group(1)

    def test_engine_exit_125_is_not_mistaken_for_a_launch_failure_and_is_fresh(self) -> None:
        first = self._run_js("EXIT_125\n", attempt=1)
        second = self._run_js("EXIT_125\n", attempt=2)

        for result in (first, second):
            diagnostic = (
                f"stderr={result.stderr_log.read_text(encoding='utf-8')!r}; "
                f"infra={result.infrastructure_error!r}"
            )
            self.assertEqual(result.exit_code, 125, diagnostic)
            self.assertFalse(result.timed_out)
            self.assertTrue(result.engine_started)
            self.assertFalse(result.oom_killed)
            self.assertEqual(result.infrastructure_error, "")
            stdout = result.stdout_log.read_text(encoding="utf-8")
            self.assertIn("<--fixture-flag=value>", stdout)
            self.assertIn("<argument with spaces>", stdout)
            self.assertIn("</tmp/secb-eval-instance/audit/poc.js>", stdout)

        self.assertNotEqual(self._fixture_hostname(first), self._fixture_hostname(second))
        self.assertEqual(self._matching_container_names(), [])

    def test_engine_exit_124_is_preserved_without_becoming_a_timeout(self) -> None:
        result = self._run_js("EXIT_124\n")

        self.assertEqual(result.exit_code, 124)
        self.assertFalse(result.timed_out)
        self.assertTrue(result.engine_started)
        self.assertFalse(result.oom_killed)
        self.assertEqual(result.infrastructure_error, "")
        self._fixture_hostname(result)
        self.assertEqual(self._matching_container_names(), [])

    def test_mode_0600_poc_is_staged_for_the_unprivileged_engine(self) -> None:
        helper = self.instance_dir / "audit" / "helper.js"
        helper.write_text("UNVALIDATED_HELPER_MUST_NOT_BE_STAGED\n", encoding="utf-8")
        result = self._run_js("NORMAL_EXIT\n")
        poc = self.instance_dir / "audit" / "poc.js"

        self.assertEqual(poc.stat().st_mode & 0o777, 0o600)
        self.assertEqual(result.exit_code, 0)
        self.assertFalse(result.timed_out)
        self.assertTrue(result.engine_started)
        self.assertFalse(result.oom_killed)
        self.assertEqual(result.infrastructure_error, "")
        self.assertIn(
            "fixture-input-mode=444",
            result.stdout_log.read_text(encoding="utf-8"),
        )
        stdout = result.stdout_log.read_text(encoding="utf-8")
        self.assertIn("fixture-helper-visible=no", stdout)
        self.assertIn("fixture-private-input-readable=no", stdout)
        self.assertIn("fixture-private-status-writable=no", stdout)
        self.assertNotIn("UNVALIDATED_HELPER_MUST_NOT_BE_STAGED", stdout)
        self.assertEqual(self._matching_container_names(), [])

    def test_unprivileged_engine_has_no_effective_capabilities(self) -> None:
        result = self._run_js("NORMAL_EXIT\n")

        self.assertEqual(result.exit_code, 0)
        self.assertTrue(result.engine_started)
        stdout_bytes = result.stdout_log.read_bytes()
        stderr_bytes = result.stderr_log.read_bytes()
        stdout = stdout_bytes.decode("utf-8")
        self.assertIn("fixture-cap-eff=0000000000000000", stdout)
        self.assertIn("fixture-home=/tmp", stdout)
        self.assertIn("fixture-tmpdir=/tmp", stdout)
        self.assertIn("fixture-xdg-cache-home=/tmp/.cache", stdout)
        self.assertEqual(
            result.stdout_sha256, hashlib.sha256(stdout_bytes).hexdigest()
        )
        self.assertEqual(
            result.stderr_sha256, hashlib.sha256(stderr_bytes).hexdigest()
        )
        self.assertEqual(self._matching_container_names(), [])

    def test_live_js_container_uses_read_only_isolation_and_read_only_binds(self) -> None:
        volumes_before_result = self._docker("volume", "ls", "--quiet")
        self.assertEqual(volumes_before_result.returncode, 0, volumes_before_result.stderr)
        volumes_before = set(volumes_before_result.stdout.splitlines())
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                self._run_js, "INSPECT_HOLD\n", timeout_sec=10
            )
            deadline = time.monotonic() + 8
            names: list[str] = []
            while time.monotonic() < deadline:
                names = self._matching_container_names()
                if names:
                    break
                if future.done():
                    break
                time.sleep(0.05)
            self.assertEqual(len(names), 1)

            inspected = self._docker("inspect", names[0])
            self.assertEqual(inspected.returncode, 0, inspected.stderr)
            state = json.loads(inspected.stdout)[0]
            host = state["HostConfig"]
            self.assertEqual(host["NetworkMode"], "none")
            self.assertTrue(host["ReadonlyRootfs"])
            self.assertEqual(set(host["Tmpfs"]), {"/tmp", "/run"})
            self.assertIn("ALL", host["CapDrop"])
            cap_add = {
                str(capability).upper().removeprefix("CAP_")
                for capability in host["CapAdd"]
            }
            self.assertTrue(
                {"SETUID", "SETGID", "KILL", "DAC_READ_SEARCH"}.issubset(
                    cap_add
                ),
                host["CapAdd"],
            )
            self.assertTrue(
                any(
                    option == "no-new-privileges"
                    or option.startswith("no-new-privileges:")
                    for option in host["SecurityOpt"]
                )
            )
            self.assertGreater(host["Memory"], 0)
            self.assertGreater(host["NanoCpus"], 0)
            self.assertGreater(host["PidsLimit"], 0)
            mounts = {
                mount["Destination"]: mount for mount in state["Mounts"]
            }
            self.assertEqual(
                set(mounts),
                {
                    "/secb-selected-poc.js",
                    "/secb-grader-status",
                    "/tmp/secb-js-engine-runner.py",
                },
            )
            self.assertFalse(mounts["/secb-selected-poc.js"]["RW"])
            self.assertFalse(mounts["/tmp/secb-js-engine-runner.py"]["RW"])
            self.assertTrue(mounts["/secb-grader-status"]["RW"])
            self.assertEqual(mounts["/secb-selected-poc.js"]["Type"], "bind")
            self.assertEqual(
                mounts["/tmp/secb-js-engine-runner.py"]["Type"], "bind"
            )
            self.assertEqual(mounts["/secb-grader-status"]["Type"], "volume")
            snapshot_source = Path(mounts["/secb-selected-poc.js"]["Source"])
            status_volume = mounts["/secb-grader-status"]["Name"]
            self.assertTrue(snapshot_source.is_file())
            self.assertNotIn(status_volume, volumes_before)

            result = future.result(timeout=15)

        self.assertEqual(result.exit_code, 0, result.infrastructure_error)
        self.assertTrue(result.engine_started)
        self.assertEqual(result.infrastructure_error, "")
        self.assertFalse(snapshot_source.exists())
        volumes_after_result = self._docker("volume", "ls", "--quiet")
        self.assertEqual(volumes_after_result.returncode, 0, volumes_after_result.stderr)
        volumes_after = set(volumes_after_result.stdout.splitlines())
        self.assertEqual(volumes_after, volumes_before)
        self.assertNotIn(status_volume, volumes_after)
        self.assertEqual(self._matching_container_names(), [])

    def test_missing_binary_is_reported_as_an_infrastructure_error(self) -> None:
        result = self._run_js("EXIT_125\n", binary="does-not-exist")

        self.assertIsNone(result.exit_code)
        self.assertFalse(result.timed_out)
        self.assertFalse(result.engine_started)
        self.assertFalse(result.oom_killed)
        self.assertTrue(result.infrastructure_error)
        self.assertIn("could not launch engine", result.infrastructure_error)
        self.assertEqual(self._matching_container_names(), [])

    def test_timeout_preserves_engine_start_and_removes_the_container(self) -> None:
        started = time.monotonic()
        result = self._run_js("TIMEOUT\n", timeout_sec=1)
        elapsed = time.monotonic() - started

        diagnostic = (
            f"stderr={result.stderr_log.read_text(encoding='utf-8')!r}; "
            f"infra={result.infrastructure_error!r}"
        )
        self.assertEqual(result.exit_code, 128 + signal.SIGKILL, diagnostic)
        self.assertTrue(result.timed_out)
        self.assertTrue(result.engine_started)
        self.assertFalse(result.oom_killed)
        self.assertEqual(result.infrastructure_error, "")
        self.assertLess(elapsed, 10)
        self._fixture_hostname(result)
        self.assertEqual(self._matching_container_names(), [])

    def test_docker_capture_preserves_sanitizer_marker_from_discarded_middle(self) -> None:
        result = self._run_js("MIDDLE_MARKER\n")

        self.assertEqual(result.exit_code, 1)
        self.assertFalse(result.timed_out)
        self.assertTrue(result.engine_started)
        stderr = result.stderr_log.read_text(encoding="utf-8")
        self.assertIn("host capture truncated; middle discarded", stderr)
        self.assertIn("SUMMARY: AddressSanitizer: heap-use-after-free", stderr)
        evidence = grade._read_instance_execution_stderr(
            self.instance_dir,
            result.stderr_log,
            8_000,
            "ASAN_CRASH",
            result.stderr_sha256,
        )
        self.assertIn("SUMMARY: AddressSanitizer: heap-use-after-free", evidence)
        self.assertEqual(self._matching_container_names(), [])

    def test_child_engine_oom_is_reported_by_docker_state(self) -> None:
        # The runner is PID 1. Exercise the harder boundary where only its child
        # engine is selected by the cgroup OOM killer and the runner survives to
        # write status.
        with patch.object(grade, "JS_EXEC_MEMORY", "64m"):
            result = self._run_js("OOM\n", timeout_sec=15)

        diagnostic = (
            f"exit={result.exit_code!r}; timed_out={result.timed_out!r}; "
            f"engine_started={result.engine_started!r}; "
            f"stderr={result.stderr_log.read_text(encoding='utf-8')!r}; "
            f"infra={result.infrastructure_error!r}"
        )
        self.assertEqual(result.exit_code, 128 + signal.SIGKILL, diagnostic)
        self.assertFalse(result.timed_out, diagnostic)
        self.assertTrue(result.engine_started, diagnostic)
        self.assertTrue(result.oom_killed, diagnostic)
        self.assertEqual(result.infrastructure_error, "", diagnostic)
        self.assertEqual(self._matching_container_names(), [])

    def test_symlink_poc_is_neither_discovered_nor_staged(self) -> None:
        secret_marker = f"HOST_FILE_MUST_NOT_BE_STAGED_{uuid.uuid4().hex}"
        host_file = Path(self._temporary.name) / "outside-instance.js"
        host_file.write_text(f"EXIT_124\n{secret_marker}\n", encoding="utf-8")
        poc = self.instance_dir / "audit" / "poc.js"
        poc.symlink_to(host_file)

        self.assertEqual(grade.find_js_files(self.instance_dir), [])
        result = self._invoke_js()

        self.assertIsNone(result.exit_code)
        self.assertFalse(result.engine_started)
        self.assertTrue(result.input_integrity_error)
        self.assertEqual(result.infrastructure_kind, "input_integrity")
        self.assertIn("no longer readable", result.infrastructure_error)
        self.assertNotIn(secret_marker, result.infrastructure_error)
        self.assertEqual(result.stdout_log.read_text(), "")
        self.assertEqual(result.stderr_log.read_text(), "")
        self.assertEqual(self._matching_container_names(), [])

    def test_source_review_container_stages_exact_contract_and_is_isolated(self) -> None:
        review = source_review.SourceReviewInput(
            project="v8",
            instance_id=f"docker-it-{self.run_token}-{uuid.uuid4().hex[:8]}",
            poc_rel_path="audit/poc.js",
            vuln_image=self.fixture_image,
            work_dir="/workspace",
            task_statement="task statement sentinel\n",
            poc_source="poc source sentinel\n",
            poc_execution={"exit_code": 125, "stderr": "execution sentinel"},
            solver_trajectory={"events": [{"tool": "trajectory sentinel"}]},
            reference_patch="reference patch sentinel\n",
        )

        name = ""
        try:
            name = source_review._start_container(review)
            inspected = self._docker("inspect", name)
            self.assertEqual(inspected.returncode, 0, inspected.stderr)
            state = json.loads(inspected.stdout)[0]
            container_logs = self._docker("logs", name)
            self.assertTrue(
                state["State"]["Running"],
                f"state={state['State']!r}; logs={container_logs.stdout!r}; "
                f"log_stderr={container_logs.stderr!r}",
            )
            host = state["HostConfig"]
            self.assertEqual(host["NetworkMode"], "none")
            self.assertIn("ALL", host["CapDrop"])
            self.assertTrue(
                any(
                    option == "no-new-privileges"
                    or option.startswith("no-new-privileges:")
                    for option in host["SecurityOpt"]
                )
            )
            self.assertGreater(host["Memory"], 0)
            self.assertGreater(host["NanoCpus"], 0)
            self.assertGreater(host["PidsLimit"], 0)
            self.assertTrue(host["ReadonlyRootfs"])
            self.assertEqual(
                set(host["Tmpfs"]),
                {"/tmp", "/run", "/workspace/audit"},
            )
            self.assertEqual(state["Mounts"], [])

            source_review._stage_audit_files(name, review.work_dir, review)
            listing = source_review._run_terminal(
                name,
                review.work_dir,
                "for path in audit/*; do basename \"$path\"; done | sort",
                10,
            )
            self.assertEqual(listing.exit_code, 0, listing.stderr)
            self.assertFalse(listing.timed_out)
            self.assertEqual(
                listing.stdout.splitlines(),
                [
                    "poc.js",
                    "poc_execution.json",
                    "reference.patch",
                    "solver_trajectory.json",
                    "task_statement.md",
                ],
            )

            identity = source_review._run_terminal(
                name,
                review.work_dir,
                "printf '%s\\n' \"$(id -u)\" \"$(id -g)\" \"$HOME\"",
                10,
            )
            self.assertEqual(identity.exit_code, 0, identity.stderr)
            self.assertEqual(identity.stdout.splitlines(), ["65534", "65534", "/tmp"])

            mutation = source_review._run_terminal(
                name,
                review.work_dir,
                (
                    "if printf hacked > audit/poc.js; then exit 91; fi; "
                    "if touch audit/unexpected; then exit 92; fi; "
                    "if printf hacked > src/assigned.cc; then exit 93; fi; "
                    "if touch source-review-unexpected; then exit 94; fi; "
                    "exit 0"
                ),
                10,
            )
            self.assertEqual(mutation.exit_code, 0, mutation.stderr)

            expected_text = {
                "task_statement.md": review.task_statement,
                "poc.js": review.poc_source,
                "reference.patch": review.reference_patch,
            }
            for filename, expected in expected_text.items():
                call = source_review._run_terminal(
                    name, review.work_dir, f"cat audit/{filename}", 10
                )
                self.assertEqual(call.exit_code, 0, call.stderr)
                self.assertEqual(call.stdout, expected)

            for filename, expected in (
                ("poc_execution.json", review.poc_execution),
                ("solver_trajectory.json", review.solver_trajectory),
            ):
                call = source_review._run_terminal(
                    name, review.work_dir, f"cat audit/{filename}", 10
                )
                self.assertEqual(call.exit_code, 0, call.stderr)
                self.assertEqual(json.loads(call.stdout), expected)

            source = source_review._run_terminal(
                name, review.work_dir, "cat src/assigned.cc", 10
            )
            self.assertEqual(source.exit_code, 0, source.stderr)
            self.assertEqual(source.stdout, "// fixture assigned source sentinel\n")
        finally:
            if name:
                source_review._remove_container(name)

        self.assertNotIn(name, common._active_containers)  # type: ignore[attr-defined]
        removed = self._docker("inspect", name)
        self.assertNotEqual(removed.returncode, 0)
        self.assertEqual(self._matching_container_names(), [])

    def test_source_review_does_not_run_commands_without_timeout_tool(self) -> None:
        review = source_review.SourceReviewInput(
            project="v8",
            instance_id=f"docker-it-{self.run_token}-{uuid.uuid4().hex[:8]}",
            poc_rel_path="audit/poc.js",
            vuln_image=self.fixture_without_timeout_image,
            work_dir="/workspace",
            task_statement="task\n",
            poc_source="poc\n",
            poc_execution={"exit_code": 1},
            solver_trajectory={"events": []},
            reference_patch="patch\n",
        )
        marker = f"/tmp/source-review-command-ran-{uuid.uuid4().hex}"
        name = ""
        try:
            name = source_review._start_container(review)

            started = time.monotonic()
            call = source_review._run_terminal(
                name,
                review.work_dir,
                f"touch {marker}; sleep 30",
                1,
            )
            elapsed = time.monotonic() - started

            self.assertEqual(call.exit_code, 125)
            self.assertFalse(call.timed_out)
            self.assertIn("timeout command not found", call.stderr)
            self.assertLess(elapsed, 5)
            marker_check = self._docker("exec", name, "test", "!", "-e", marker)
            self.assertEqual(marker_check.returncode, 0, marker_check.stderr)
        finally:
            if name:
                source_review._remove_container(name)

        self.assertEqual(self._matching_container_names(), [])


if __name__ == "__main__":
    unittest.main()
