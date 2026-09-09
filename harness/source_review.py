"""Terminal-assisted source attribution for ambiguous V8/SpiderMonkey PoCs.

Each review runs against a fresh vulnerable-image container with no host mounts
and no network. The model receives one terminal tool whose commands execute in
the vulnerable source checkout. A review without a successful terminal call is a
grader error, never a negative submission verdict.
"""

from __future__ import annotations

import json
import os
import signal
import stat
import subprocess
import tempfile
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from jinja2 import Environment, FileSystemLoader

import common
import judge

PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts" / "judge"
MAX_MODEL_TURNS = 8
DEFAULT_MAX_TURNS = MAX_MODEL_TURNS
DEFAULT_TERMINAL_TIMEOUT_SEC = 120
DEFAULT_REVIEW_TIMEOUT_SEC = 900
MAX_REVIEW_TIMEOUT_SEC = 900
MAX_TERMINAL_TIMEOUT_SEC = 300
MAX_TERMINAL_CALLS = 8
MAX_TERMINAL_EXECUTIONS = 12
MAX_MODEL_CALLS = 12
MAX_MODEL_OUTPUT_TOKENS = 4_096
MAX_TOTAL_MODEL_TOKENS = 250_000
MAX_MODEL_CONTEXT_CHARS = 200_000
MAX_TOOL_OUTPUT_CHARS = 50_000
MAX_TOOL_CAPTURE_CHARS = 1_000_000
MAX_FINAL_RETRIES = 1
MAX_MANIFEST_BYTES = 1 * 1024 * 1024
MAX_TASK_STATEMENT_BYTES = 1 * 1024 * 1024
MAX_POC_SOURCE_BYTES = 8 * 1024 * 1024
MAX_EXECUTION_EVIDENCE_BYTES = 8 * 1024 * 1024
MAX_SOLVER_TRAJECTORY_BYTES = 4 * 1024 * 1024
MAX_REFERENCE_PATCH_BYTES = 16 * 1024 * 1024
MAX_TRAJECTORY_FILES = 256
MAX_REFERENCE_PATCH_FILES = 256
SOURCE_REVIEW_MEMORY = os.environ.get("SECB_SOURCE_REVIEW_MEMORY", "8g")
SOURCE_REVIEW_CPUS = os.environ.get("SECB_SOURCE_REVIEW_CPUS", "4")
SOURCE_REVIEW_PIDS = os.environ.get("SECB_SOURCE_REVIEW_PIDS", "512")
SOURCE_REVIEW_TMPFS_SIZE = os.environ.get("SECB_SOURCE_REVIEW_TMPFS_SIZE", "1g")
SOURCE_REVIEW_RUN_TMPFS_SIZE = os.environ.get(
    "SECB_SOURCE_REVIEW_RUN_TMPFS_SIZE", "16m"
)
SOURCE_REVIEW_AUDIT_TMPFS_SIZE = os.environ.get(
    "SECB_SOURCE_REVIEW_AUDIT_TMPFS_SIZE", "64m"
)

TERMINAL_TOOL = {
    "type": "function",
    "function": {
        "name": "terminal",
        "description": (
            "Run a shell command in the fresh vulnerable source checkout. "
            "Use it to inspect audit evidence and source files or to perform "
            "local experiments under /tmp. The source checkout is read-only, "
            "and the container has no network or host mounts."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to run from the source checkout root.",
                },
                "timeout_sec": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": MAX_TERMINAL_TIMEOUT_SEC,
                    "description": "Optional command timeout in seconds.",
                },
            },
            "required": ["command"],
            "additionalProperties": False,
        },
    },
}

SOURCE_REVIEW_PARSE_REMINDER = (
    "Respond now with only one JSON object containing exactly `in_scope` as a "
    "JSON boolean and `reason` as a string. Do not use markdown fences or add prose."
)
REQUIRED_EVIDENCE_COMMANDS = {
    "task_statement": "cat -- audit/task_statement.md",
    "poc_execution": "cat -- audit/poc_execution.json",
}


@dataclass
class SourceReviewInput:
    project: str
    instance_id: str
    poc_rel_path: str
    vuln_image: str
    work_dir: str
    task_statement: str
    poc_source: str
    poc_execution: dict[str, Any]
    solver_trajectory: Any
    reference_patch: str


@dataclass
class TerminalCall:
    command: str
    timeout_sec: int
    exit_code: int | None
    timed_out: bool
    stdout: str
    stderr: str
    purpose: str = "model"


@dataclass
class SourceReviewVerdict:
    project: str
    instance_id: str
    poc_rel_path: str
    in_scope: bool | None
    reason: str
    model: str
    latency_ms: int = 0
    error: str = ""
    tool_calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    transcript: list[TerminalCall] = field(default_factory=list)


def build_prompt() -> str:
    env = Environment(
        loader=FileSystemLoader(str(PROMPTS_DIR)),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return env.get_template("source_review.j2").render()


def _deadline_timeout(deadline: float | None, cap: float, operation: str) -> float:
    if deadline is None:
        return cap
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError(f"source review deadline expired before {operation}")
    return min(cap, remaining)


def _read_bounded_bytes_descriptor(
    descriptor: int, max_bytes: int, description: str
) -> bytes:
    """Read an already-open regular file without allocating past ``max_bytes``."""
    if max_bytes < 0:
        raise ValueError(f"invalid byte limit for {description}: {max_bytes}")
    metadata = os.fstat(descriptor)
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError(f"{description} is not a regular file")
    if metadata.st_size > max_bytes:
        raise ValueError(
            f"{description} exceeds the {max_bytes}-byte source-review limit"
        )
    chunks: list[bytes] = []
    observed = 0
    while True:
        chunk = os.read(descriptor, min(1024 * 1024, max_bytes + 1 - observed))
        if not chunk:
            break
        chunks.append(chunk)
        observed += len(chunk)
        if observed > max_bytes:
            raise ValueError(
                f"{description} exceeds the {max_bytes}-byte source-review limit"
            )
    return b"".join(chunks)


def _read_bounded_descriptor(
    descriptor: int, max_bytes: int, description: str
) -> str:
    return _read_bounded_bytes_descriptor(
        descriptor, max_bytes, description
    ).decode("utf-8", errors="replace")


def read_bounded_text_file(path: Path, max_bytes: int, description: str) -> str:
    """Read one regular non-symlink file without allocating past ``max_bytes``."""
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ValueError(f"could not safely read {description}: {exc}") from exc
    try:
        return _read_bounded_descriptor(descriptor, max_bytes, description)
    finally:
        os.close(descriptor)


def _open_instance_entry(
    instance_dir: Path,
    relative_path: str | Path,
    *,
    directory: bool = False,
) -> tuple[int, Path]:
    """Open an instance entry from a root dirfd without following any symlink."""
    relative = Path(relative_path)
    if (
        relative.is_absolute()
        or not relative.parts
        or any(part in ("", ".", "..") for part in relative.parts)
    ):
        raise ValueError(f"unsafe instance-relative path: {relative_path}")
    descriptor = -1
    try:
        # Resolve neither the root nor its final component before opening it.
        # O_NOFOLLOW must cover the actual open to close a root replacement race.
        root = instance_dir.absolute()
        directory_flags = (
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_DIRECTORY", 0)
            | getattr(os, "O_NOFOLLOW", 0)
        )
        anchor = root.anchor or os.sep
        descriptor = os.open(anchor, directory_flags)
        for root_part in root.parts[1:]:
            next_descriptor = os.open(
                root_part, directory_flags, dir_fd=descriptor
            )
            os.close(descriptor)
            descriptor = next_descriptor
        candidate = root
        for index, part in enumerate(relative.parts):
            candidate /= part
            expect_directory = directory or index < len(relative.parts) - 1
            flags = (
                os.O_RDONLY
                | getattr(os, "O_CLOEXEC", 0)
                | getattr(os, "O_NOFOLLOW", 0)
                | getattr(os, "O_NONBLOCK", 0)
            )
            if expect_directory:
                flags |= getattr(os, "O_DIRECTORY", 0)
            next_descriptor = os.open(part, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_descriptor
        metadata = os.fstat(descriptor)
        expected = stat.S_ISDIR if directory else stat.S_ISREG
        if not expected(metadata.st_mode):
            raise ValueError(f"instance entry has the wrong file type: {relative}")
        return descriptor, candidate
    except FileNotFoundError:
        if descriptor >= 0:
            os.close(descriptor)
        raise
    except (OSError, RuntimeError, ValueError) as exc:
        if descriptor >= 0:
            os.close(descriptor)
        if isinstance(exc, ValueError):
            raise
        raise ValueError(f"could not safely open instance entry {relative}: {exc}") from exc


def read_instance_bounded_text_file(
    instance_dir: Path,
    relative_path: str | Path,
    max_bytes: int,
    description: str,
) -> str:
    """Atomically traverse and read one root-contained instance regular file."""
    descriptor, _candidate = _open_instance_entry(instance_dir, relative_path)
    try:
        return _read_bounded_descriptor(descriptor, max_bytes, description)
    finally:
        os.close(descriptor)


def read_instance_bounded_bytes_file(
    instance_dir: Path,
    relative_path: str | Path,
    max_bytes: int,
    description: str,
) -> bytes:
    """Atomically traverse and read one root-contained instance regular file."""
    descriptor, _candidate = _open_instance_entry(instance_dir, relative_path)
    try:
        return _read_bounded_bytes_descriptor(descriptor, max_bytes, description)
    finally:
        os.close(descriptor)


def _manifest_source(instance_dir: Path, manifest_name: str) -> Path | None:
    try:
        raw_manifest = read_instance_bounded_text_file(
            instance_dir,
            manifest_name,
            MAX_MANIFEST_BYTES,
            manifest_name,
        )
    except FileNotFoundError:
        return None
    except ValueError as exc:
        raise ValueError(
            f"{manifest_name} must be a real regular file inside the instance"
        ) from exc
    try:
        manifest = json.loads(raw_manifest)
    except json.JSONDecodeError:
        return None
    source = manifest.get("source") if isinstance(manifest, dict) else None
    if not isinstance(source, str) or not source:
        return None
    try:
        descriptor, _candidate = _open_instance_entry(instance_dir, source)
    except FileNotFoundError:
        return None
    except ValueError as exc:
        raise ValueError(
            f"{manifest_name} source must be a real regular file inside the instance"
        ) from exc
    os.close(descriptor)
    return Path(source)


def _load_jsonl(instance_dir: Path, relative_path: Path) -> list[Any]:
    events: list[Any] = []
    content = read_instance_bounded_text_file(
        instance_dir,
        relative_path,
        MAX_SOLVER_TRAJECTORY_BYTES,
        "solver trajectory",
    )
    for line_number, line in enumerate(content.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            events.append({"line": line_number, "unparsed": line})
    return events


def load_solver_trajectory(instance_dir: Path) -> dict[str, Any]:
    """Return the collected solver transcript in one JSON-serializable object."""
    for manifest_name, provider in (
        ("codex_manifest.json", "codex"),
        ("claude_manifest.json", "claude"),
    ):
        source = _manifest_source(instance_dir, manifest_name)
        if source is not None:
            return {
                "provider": provider,
                "source": str(source),
                "events": _load_jsonl(instance_dir, source),
            }

    try:
        trajectory_descriptor, trajectory_dir = _open_instance_entry(
            instance_dir, "trajectory", directory=True
        )
    except FileNotFoundError:
        trajectory_dir = None
        trajectory_descriptor = -1
    except ValueError as exc:
        raise ValueError(
            "solver trajectory directory must be a real directory inside the instance"
        ) from exc
    if trajectory_dir is not None:
        try:
            with os.scandir(trajectory_descriptor) as entries:
                names = sorted(
                    entry.name
                    for entry in entries
                    if Path(entry.name).suffix == ".json"
                )
        finally:
            os.close(trajectory_descriptor)
        sessions: list[dict[str, Any]] = []
        paths = [trajectory_dir / name for name in names]
        if len(paths) > MAX_TRAJECTORY_FILES:
            raise ValueError(
                f"solver trajectory exceeds the {MAX_TRAJECTORY_FILES}-file limit"
            )
        total_bytes = 0
        for path in paths:
            relative_path = Path("trajectory") / path.name
            try:
                raw_bytes = read_instance_bounded_bytes_file(
                    instance_dir,
                    relative_path,
                    MAX_SOLVER_TRAJECTORY_BYTES - total_bytes,
                    "solver trajectory",
                )
            except FileNotFoundError as exc:
                raise ValueError(
                    "solver trajectory is not a real regular file inside the instance: "
                    f"{path.name}"
                ) from exc
            except ValueError as exc:
                if "exceeds" in str(exc):
                    raise ValueError(
                        "solver trajectory exceeds the "
                        f"{MAX_SOLVER_TRAJECTORY_BYTES}-byte limit"
                    ) from exc
                raise ValueError(
                    "solver trajectory is not a real regular file inside the instance: "
                    f"{path.name}"
                ) from exc
            total_bytes += len(raw_bytes)
            raw = raw_bytes.decode("utf-8", errors="replace")
            try:
                content = json.loads(raw)
            except json.JSONDecodeError:
                content = {"unparsed": raw}
            sessions.append(
                {"source": str(relative_path), "content": content}
            )
        if sessions:
            return {"provider": "opencode", "sessions": sessions}

    try:
        transcript = read_instance_bounded_text_file(
            instance_dir,
            "agent_stdout.txt",
            MAX_SOLVER_TRAJECTORY_BYTES,
            "solver stdout trajectory",
        )
    except FileNotFoundError:
        return {"provider": "unknown", "events": []}
    except ValueError as exc:
        raise ValueError(
            "solver stdout trajectory must be a real regular file inside the instance"
        ) from exc
    return {
        "provider": "unknown",
        "source": "agent_stdout.txt",
        "transcript": transcript,
    }


def load_reference_patch(benchmark_instance_dir: Path, meta: dict[str, Any]) -> str:
    """Load historical patch files declared by metadata, preserving sequence."""
    candidates: list[tuple[int, Path]] = []
    fixes = meta.get("fixes")
    if isinstance(fixes, list):
        for index, fix in enumerate(fixes):
            if not isinstance(fix, dict) or fix.get("kind") != "patch_file":
                continue
            rel_path = fix.get("path")
            if not isinstance(rel_path, str) or not rel_path:
                continue
            path = (benchmark_instance_dir / rel_path).resolve()
            if path.is_relative_to(benchmark_instance_dir.resolve()) and path.is_file():
                sequence = fix.get("sequence", index + 1)
                try:
                    order = int(sequence)
                except (TypeError, ValueError):
                    order = index + 1
                candidates.append((order, path))

    if not candidates:
        benchmark_root = benchmark_instance_dir.resolve()
        for index, path in enumerate(
            sorted((benchmark_instance_dir / "patches").glob("*.patch")),
            start=1,
        ):
            resolved = path.resolve()
            if resolved.is_relative_to(benchmark_root) and resolved.is_file():
                candidates.append((index, resolved))
    if not candidates:
        raise FileNotFoundError(
            f"no historical patch found under {benchmark_instance_dir / 'patches'}"
        )
    if len(candidates) > MAX_REFERENCE_PATCH_FILES:
        raise ValueError(
            f"historical reference patch set exceeds the "
            f"{MAX_REFERENCE_PATCH_FILES}-file limit"
        )

    sections: list[str] = []
    total_bytes = 0
    for _order, path in sorted(candidates, key=lambda item: (item[0], str(item[1]))):
        section = read_bounded_text_file(
            path,
            MAX_REFERENCE_PATCH_BYTES,
            "historical reference patch",
        ).rstrip()
        total_bytes += len(section.encode("utf-8"))
        if total_bytes > MAX_REFERENCE_PATCH_BYTES:
            raise ValueError(
                "historical reference patches exceed the "
                f"{MAX_REFERENCE_PATCH_BYTES}-byte limit"
            )
        sections.append(section)
    return "\n\n".join(sections) + "\n"


def _validate_source_review(raw: Any) -> tuple[bool, str]:
    if not isinstance(raw, dict) or set(raw) != {"in_scope", "reason"}:
        raise ValueError("source review must contain exactly 'in_scope' and 'reason'")
    if type(raw["in_scope"]) is not bool:
        raise ValueError("in_scope must be a JSON boolean")
    if not isinstance(raw["reason"], str):
        raise ValueError("reason must be a string")
    reason = raw["reason"].strip()
    if not reason:
        raise ValueError("reason must be a non-empty string")
    return raw["in_scope"], reason


def _message_attr(message: Any, name: str, default: Any = None) -> Any:
    if isinstance(message, dict):
        return message.get(name, default)
    return getattr(message, name, default)


def _normalise_tool_call(tool_call: Any) -> tuple[dict[str, Any], str, str, str]:
    call_id = str(_message_attr(tool_call, "id", ""))
    function = _message_attr(tool_call, "function", {})
    name = str(_message_attr(function, "name", ""))
    arguments = _message_attr(function, "arguments", "{}")
    if not isinstance(arguments, str):
        arguments = json.dumps(arguments)
    serialised = {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": arguments},
    }
    return serialised, call_id, name, arguments


def _truncate_tool_output(text: str) -> str:
    return judge._truncate(text, MAX_TOOL_OUTPUT_CHARS)


def _run_bounded_subprocess(
    command: list[str], timeout_sec: int
) -> tuple[int | None, bool, str, str]:
    """Run a terminal command while draining and bounding both host buffers."""
    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []

    def drain(stream: Any, chunks: list[str]) -> None:
        buffered: list[str] = []
        total = 0
        truncated = False
        head = ""
        tail_chunks: deque[str] = deque()
        tail_chars = 0
        half = MAX_TOOL_CAPTURE_CHARS // 2
        try:
            while True:
                chunk = stream.read(8192)
                if not chunk:
                    break
                total += len(chunk)
                if not truncated:
                    buffered.append(chunk)
                    if total <= MAX_TOOL_CAPTURE_CHARS:
                        continue
                    combined = "".join(buffered)
                    head = combined[:half]
                    tail_chunks.append(combined[-half:])
                    tail_chars = len(tail_chunks[0])
                    buffered.clear()
                    truncated = True
                else:
                    tail_chunks.append(chunk)
                    tail_chars += len(chunk)
                    while tail_chars > half and tail_chunks:
                        excess = tail_chars - half
                        first = tail_chunks[0]
                        if len(first) <= excess:
                            tail_chars -= len(tail_chunks.popleft())
                        else:
                            tail_chunks[0] = first[excess:]
                            tail_chars -= excess
        except (OSError, ValueError):
            pass
        if truncated:
            chunks.extend(
                [
                    head,
                    "\n...[host capture truncated; middle discarded]...\n",
                    "".join(tail_chunks),
                ]
            )
        else:
            chunks.extend(buffered)

    proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
        start_new_session=True,
    )
    stdout_thread = threading.Thread(target=drain, args=(proc.stdout, stdout_chunks), daemon=True)
    stderr_thread = threading.Thread(target=drain, args=(proc.stderr, stderr_chunks), daemon=True)
    stdout_thread.start()
    stderr_thread.start()
    timed_out = False
    try:
        proc.wait(timeout=timeout_sec)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            proc.kill()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
    stdout_thread.join(timeout=5)
    stderr_thread.join(timeout=5)
    for stream in (proc.stdout, proc.stderr):
        if stream is not None:
            try:
                stream.close()
            except OSError:
                pass
    stdout_thread.join(timeout=1)
    stderr_thread.join(timeout=1)
    return proc.returncode, timed_out, "".join(stdout_chunks), "".join(stderr_chunks)


def _run_terminal(
    container_name: str,
    work_dir: str,
    command: str,
    timeout_sec: int,
    *,
    purpose: str = "model",
) -> TerminalCall:
    try:
        exit_code, outer_timeout, stdout, stderr = _run_bounded_subprocess(
            [
                "docker",
                "exec",
                "--user",
                "65534:65534",
                "--env",
                "HOME=/tmp",
                "--env",
                "GIT_CONFIG_COUNT=1",
                "--env",
                "GIT_CONFIG_KEY_0=safe.directory",
                "--env",
                f"GIT_CONFIG_VALUE_0={work_dir}",
                "--workdir",
                work_dir,
                container_name,
                "sh",
                "-lc",
                (
                    "if command -v timeout >/dev/null 2>&1; then "
                    "exec timeout --kill-after=5s \"$1\"s sh -lc \"$2\"; "
                    "else printf '%s\\n' "
                    "'source-review terminal unavailable: timeout command not found' "
                    ">&2; exit 125; fi"
                ),
                "source-review-terminal",
                str(timeout_sec),
                command,
            ],
            timeout_sec + 10,
        )
        return TerminalCall(
            command=command,
            timeout_sec=timeout_sec,
            exit_code=exit_code,
            timed_out=outer_timeout or common.is_timeout_exit_code(exit_code),
            stdout=_truncate_tool_output(stdout),
            stderr=_truncate_tool_output(stderr),
            purpose=purpose,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return TerminalCall(
            command=command,
            timeout_sec=timeout_sec,
            exit_code=None,
            timed_out=True,
            stdout="",
            stderr=_truncate_tool_output(str(exc)),
            purpose=purpose,
        )


def _tool_result_content(call: TerminalCall) -> str:
    status = "timeout" if call.timed_out else str(call.exit_code)
    return json.dumps(
        {"exit_code": status, "stdout": call.stdout, "stderr": call.stderr},
        ensure_ascii=False,
    )


def _tool_result_with_evidence(
    call: TerminalCall, evidence: dict[str, TerminalCall]
) -> str:
    if not evidence:
        return _tool_result_content(call)
    return json.dumps(
        {
            "required_evidence": {
                label: json.loads(_tool_result_content(result))
                for label, result in evidence.items()
            },
            "command_result": json.loads(_tool_result_content(call)),
        },
        ensure_ascii=False,
    )


def _write_bounded_text(
    path: Path, text: str, max_bytes: int, description: str
) -> None:
    observed = 0
    with path.open("w", encoding="utf-8") as fh:
        for offset in range(0, len(text), 64 * 1024):
            chunk = text[offset : offset + 64 * 1024]
            observed += len(chunk.encode("utf-8"))
            if observed > max_bytes:
                raise ValueError(f"{description} exceeds the {max_bytes}-byte limit")
            fh.write(chunk)


def _write_bounded_json(
    path: Path, value: Any, max_bytes: int, description: str
) -> None:
    observed = 0
    encoder = json.JSONEncoder(indent=2, ensure_ascii=False)
    with path.open("w", encoding="utf-8") as fh:
        for chunk in encoder.iterencode(value):
            observed += len(chunk.encode("utf-8"))
            if observed > max_bytes:
                raise ValueError(f"{description} exceeds the {max_bytes}-byte limit")
            fh.write(chunk)
        fh.write("\n")


def _stage_audit_files(
    container_name: str,
    work_dir: str,
    review: SourceReviewInput,
    *,
    deadline: float | None = None,
) -> None:
    setup = subprocess.run(
        [
            "docker",
            "exec",
            "--workdir",
            work_dir,
            container_name,
            "sh",
            "-lc",
            (
                "mkdir -p audit && "
                "find audit -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +"
            ),
        ],
        capture_output=True,
        text=True,
        errors="replace",
        timeout=_deadline_timeout(deadline, 30, "audit directory setup"),
    )
    if setup.returncode != 0:
        raise RuntimeError(f"could not prepare audit directory: {setup.stderr.strip()}")

    with tempfile.TemporaryDirectory(prefix="sec-bench-source-review-") as temp_dir:
        staging = Path(temp_dir)
        _deadline_timeout(deadline, 1, "audit evidence serialization")
        _write_bounded_text(
            staging / "task_statement.md",
            review.task_statement,
            MAX_TASK_STATEMENT_BYTES,
            "task statement",
        )
        _write_bounded_text(
            staging / "poc.js",
            review.poc_source,
            MAX_POC_SOURCE_BYTES,
            "PoC source",
        )
        _write_bounded_json(
            staging / "poc_execution.json",
            review.poc_execution,
            2 * MAX_EXECUTION_EVIDENCE_BYTES,
            "PoC execution evidence",
        )
        _write_bounded_json(
            staging / "solver_trajectory.json",
            review.solver_trajectory,
            2 * MAX_SOLVER_TRAJECTORY_BYTES,
            "solver trajectory",
        )
        _write_bounded_text(
            staging / "reference.patch",
            review.reference_patch,
            MAX_REFERENCE_PATCH_BYTES,
            "historical reference patch",
        )
        # `docker cp` refuses all writes when ReadonlyRootfs is enabled, even
        # when its destination is a writable tmpfs. Stream each fixed-name
        # evidence file through `docker exec -i` into the audit tmpfs instead.
        for source in sorted(staging.iterdir(), key=lambda path: path.name):
            _deadline_timeout(deadline, 1, "audit evidence copy")
            payload = source.read_bytes()
            copied = subprocess.run(
                [
                    "docker",
                    "exec",
                    "--interactive",
                    "--workdir",
                    work_dir,
                    container_name,
                    "sh",
                    "-c",
                    f"umask 022; cat > audit/{source.name}",
                ],
                input=payload,
                capture_output=True,
                timeout=_deadline_timeout(deadline, 60, "audit evidence copy"),
            )
            if copied.returncode != 0:
                detail = copied.stderr.decode("utf-8", errors="replace").strip()
                raise RuntimeError(
                    f"could not copy source-review evidence {source.name}: {detail}"
                )


def _start_container(
    review: SourceReviewInput, *, timeout_sec: float = 60
) -> str:
    work_path = Path(review.work_dir)
    if not work_path.is_absolute() or ".." in work_path.parts:
        raise RuntimeError(
            f"source-review work directory must be an absolute safe path: "
            f"{review.work_dir}"
        )
    audit_mount = str(work_path / "audit")
    name = f"{review.project}-source-review-{review.instance_id}-{uuid.uuid4().hex[:12]}"
    common.register_active_container(name)
    try:
        result = subprocess.run(
            [
                "docker",
                "run",
                "--detach",
                "--name",
                name,
                "--network",
                "none",
                "--read-only",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--memory",
                SOURCE_REVIEW_MEMORY,
                "--cpus",
                SOURCE_REVIEW_CPUS,
                "--pids-limit",
                SOURCE_REVIEW_PIDS,
                "--tmpfs",
                (
                    "/tmp:rw,nosuid,nodev,"
                    f"size={SOURCE_REVIEW_TMPFS_SIZE},mode=1777"
                ),
                "--tmpfs",
                (
                    "/run:rw,nosuid,nodev,noexec,"
                    f"size={SOURCE_REVIEW_RUN_TMPFS_SIZE},mode=0755"
                ),
                "--tmpfs",
                (
                    f"{audit_mount}:rw,nosuid,nodev,noexec,"
                    f"size={SOURCE_REVIEW_AUDIT_TMPFS_SIZE},mode=0755"
                ),
                "--log-driver",
                "none",
                review.vuln_image,
                "sh",
                "-lc",
                "sleep infinity",
            ],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout_sec,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        _remove_container(name)
        raise RuntimeError(f"could not start source-review container: {exc}") from exc
    except BaseException:
        _remove_container(name)
        raise
    if result.returncode != 0:
        _remove_container(name)
        raise RuntimeError(f"could not start source-review container: {result.stderr.strip()}")
    # Cleanup may have claimed the provisional name while docker run was
    # pending. Register the now-created container again for the next sweep.
    common.register_active_container(name)
    return name


def _remove_container(name: str) -> None:
    removed = False
    for attempt in range(3):
        try:
            result = subprocess.run(
                ["docker", "rm", "-f", "-v", name],
                capture_output=True,
                text=True,
                errors="replace",
                timeout=30,
            )
            removed = result.returncode == 0 or "no such container" in (
                result.stderr or ""
            ).casefold()
            if removed:
                break
        except (OSError, subprocess.TimeoutExpired):
            pass
        if attempt < 2:
            time.sleep(0.1 * (attempt + 1))
    if removed:
        common.unregister_active_container(name)
    else:
        # A signal cleanup may have atomically claimed this name already.
        # Preserve it for the next cleanup sweep when removal did not succeed.
        common.register_active_container(name)


def _usage(response: Any) -> tuple[int, int, int, float]:
    usage = getattr(response, "usage", None)
    prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
    completion_tokens = getattr(usage, "completion_tokens", 0) or 0
    total_tokens = getattr(usage, "total_tokens", 0) or 0
    try:
        import litellm

        cost = litellm.completion_cost(completion_response=response)
    except Exception:
        cost = 0.0
    return prompt_tokens, completion_tokens, total_tokens, cost


def _completion_with_retries(
    kwargs: dict[str, Any],
    *,
    deadline: float | None = None,
    before_request: Callable[[], None] | None = None,
) -> Any:
    """Retry transient provider failures without changing the review request."""
    import litellm

    request = dict(kwargs)
    configured_timeout = request.get("timeout")
    for attempt in range(judge.MAX_RETRIES):
        attempt_request = dict(request)
        if deadline is not None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("source reviewer exceeded its overall deadline")
            try:
                timeout_cap = float(configured_timeout)
            except (TypeError, ValueError):
                timeout_cap = remaining
            attempt_request["timeout"] = max(0.001, min(timeout_cap, remaining))
        if before_request is not None:
            before_request()
        try:
            return litellm.completion(**attempt_request)
        except Exception as exc:
            if judge._is_transient_error(exc) and attempt < judge.MAX_RETRIES - 1:
                delay = judge.TRANSIENT_BACKOFF_SEC[
                    min(attempt, len(judge.TRANSIENT_BACKOFF_SEC) - 1)
                ]
                if deadline is not None:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError(
                            "source reviewer exceeded its overall deadline"
                        ) from exc
                    delay = min(delay, remaining)
                time.sleep(delay)
                continue
            raise
    raise RuntimeError("source-review model retries exhausted")


def _call_model_with_terminal(
    review: SourceReviewInput,
    *,
    container_name: str,
    model: str,
    reasoning_effort: str,
    max_turns: int,
    terminal_timeout_sec: int,
    overall_timeout_sec: float = DEFAULT_REVIEW_TIMEOUT_SEC,
    deadline: float | None = None,
    transcript_out: list[TerminalCall] | None = None,
) -> SourceReviewVerdict:
    import litellm

    litellm.drop_params = True
    resolved_model = judge.resolve_model(model)
    temperature = judge._temperature_for_model(resolved_model, reasoning_effort)
    messages: list[dict[str, Any]] = [{"role": "user", "content": build_prompt()}]
    transcript = transcript_out if transcript_out is not None else []
    prompt_tokens = completion_tokens = total_tokens = 0
    cost_usd = 0.0
    final_retries = 0
    model_terminal_calls = 0
    terminal_requests = 0
    terminal_executions = 0
    required_evidence: dict[str, TerminalCall] = {}
    model_calls = 0
    if not 1 <= max_turns <= MAX_MODEL_TURNS:
        raise ValueError(
            f"source-review max_turns must be between 1 and {MAX_MODEL_TURNS}"
        )
    if deadline is None:
        deadline = time.monotonic() + min(
            max(0.001, overall_timeout_sec), MAX_REVIEW_TIMEOUT_SEC
        )
        deadline = common.clamp_js_grading_deadline(
            deadline, "a source-review request"
        )

    def reserve_model_call() -> None:
        nonlocal model_calls
        if model_calls >= MAX_MODEL_CALLS:
            raise RuntimeError(
                f"source reviewer exceeded {MAX_MODEL_CALLS} model calls"
            )
        context_chars = len(
            json.dumps(messages, ensure_ascii=False, default=str)
        )
        if context_chars > MAX_MODEL_CONTEXT_CHARS:
            raise RuntimeError(
                "source reviewer exceeded the "
                f"{MAX_MODEL_CONTEXT_CHARS}-character model context limit"
            )
        common.consume_js_llm_call("a source-review provider call")
        model_calls += 1

    def bounded_terminal_timeout(requested: Any) -> int:
        remaining = int(deadline - time.monotonic()) - 10
        if remaining < 1:
            raise RuntimeError("source reviewer exceeded its overall deadline")
        return max(1, min(int(requested), MAX_TERMINAL_TIMEOUT_SEC, remaining))

    def run_terminal_bounded(
        command: str, timeout: int, *, purpose: str = "model"
    ) -> TerminalCall:
        nonlocal terminal_executions
        if terminal_executions >= MAX_TERMINAL_EXECUTIONS:
            raise RuntimeError(
                "source reviewer exceeded "
                f"{MAX_TERMINAL_EXECUTIONS} terminal executions"
            )
        terminal_executions += 1
        return _run_terminal(
            container_name,
            review.work_dir,
            command,
            timeout,
            purpose=purpose,
        )

    for _turn in range(max_turns):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise RuntimeError("source reviewer exceeded its overall deadline")
        response = _completion_with_retries(
            {
                "model": resolved_model,
                "messages": messages,
                "tools": [TERMINAL_TOOL],
                "tool_choice": "auto",
                "reasoning_effort": reasoning_effort,
                "temperature": temperature,
                "max_tokens": MAX_MODEL_OUTPUT_TOKENS,
                "timeout": max(0.1, min(120.0, remaining)),
            },
            deadline=deadline,
            before_request=reserve_model_call,
        )
        pt, ct, tt, cost = _usage(response)
        prompt_tokens += pt
        completion_tokens += ct
        total_tokens += tt
        cost_usd += cost
        if total_tokens > MAX_TOTAL_MODEL_TOKENS:
            raise RuntimeError(
                "source reviewer exceeded the "
                f"{MAX_TOTAL_MODEL_TOKENS}-token cumulative limit"
            )

        message = response.choices[0].message
        content = _message_attr(message, "content", "") or ""
        assistant_message: dict[str, Any] = {"role": "assistant", "content": content}
        # Providers may require their signed thinking blocks on the next tool
        # turn. Preserve the response metadata when reconstructing history.
        for key in ("thinking_blocks", "reasoning_content"):
            value = _message_attr(message, key)
            if value is not None:
                assistant_message[key] = value
        tool_calls = _message_attr(message, "tool_calls", None) or []
        if tool_calls:
            assistant_calls: list[dict[str, Any]] = []
            parsed_calls: list[tuple[str, str, str]] = []
            for tool_call in tool_calls:
                serialised, call_id, name, arguments = _normalise_tool_call(tool_call)
                assistant_calls.append(serialised)
                parsed_calls.append((call_id, name, arguments))
            assistant_message["tool_calls"] = assistant_calls
            messages.append(assistant_message)
            if terminal_requests + len(parsed_calls) > MAX_TERMINAL_CALLS:
                raise RuntimeError(
                    f"source reviewer exceeded {MAX_TERMINAL_CALLS} terminal requests"
                )
            terminal_requests += len(parsed_calls)

            for call_id, name, arguments in parsed_calls:
                if name != "terminal":
                    result_content = json.dumps({"error": f"unknown tool: {name}"})
                else:
                    try:
                        args = json.loads(arguments)
                        command = args["command"]
                        if not isinstance(command, str) or not command.strip():
                            raise ValueError("command must be a non-empty string")
                        requested_timeout = args.get("timeout_sec", terminal_timeout_sec)
                        timeout = bounded_terminal_timeout(requested_timeout)
                        evidence_for_this_call: dict[str, TerminalCall] = {}
                        for label, evidence_command in REQUIRED_EVIDENCE_COMMANDS.items():
                            previous = required_evidence.get(label)
                            if previous is not None and previous.exit_code == 0 and not previous.timed_out:
                                continue
                            evidence_call = run_terminal_bounded(
                                evidence_command,
                                bounded_terminal_timeout(terminal_timeout_sec),
                                purpose=f"required_evidence:{label}",
                            )
                            required_evidence[label] = evidence_call
                            evidence_for_this_call[label] = evidence_call
                            transcript.append(evidence_call)
                        call = run_terminal_bounded(
                            command,
                            bounded_terminal_timeout(timeout),
                        )
                        transcript.append(call)
                        model_terminal_calls += 1
                        result_content = _tool_result_with_evidence(
                            call, evidence_for_this_call
                        )
                    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                        result_content = json.dumps({"error": f"invalid terminal call: {exc}"})
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call_id,
                        "name": name,
                        "content": result_content,
                    }
                )
            continue

        if model_terminal_calls == 0:
            raise RuntimeError("source reviewer returned without using the terminal tool")
        if not any(
            call.purpose == "model"
            and call.exit_code == 0
            and not call.timed_out
            for call in transcript
        ):
            raise RuntimeError("source reviewer made no successful terminal calls")
        for label in REQUIRED_EVIDENCE_COMMANDS:
            evidence_call = required_evidence.get(label)
            if evidence_call is None or evidence_call.exit_code != 0 or evidence_call.timed_out:
                raise RuntimeError(
                    "source reviewer could not inspect the task statement and "
                    f"execution evidence ({label})"
                )
        try:
            raw = json.loads(str(content).strip())
            in_scope, reason = _validate_source_review(raw)
            return SourceReviewVerdict(
                project=review.project,
                instance_id=review.instance_id,
                poc_rel_path=review.poc_rel_path,
                in_scope=in_scope,
                reason=reason,
                model=model,
                tool_calls=model_terminal_calls,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost_usd=cost_usd,
                transcript=transcript,
            )
        except (ValueError, json.JSONDecodeError):
            if final_retries >= MAX_FINAL_RETRIES:
                raise
            final_retries += 1
            messages.append(assistant_message)
            messages.append({"role": "user", "content": SOURCE_REVIEW_PARSE_REMINDER})

    raise RuntimeError(f"source reviewer exceeded {max_turns} model turns")


def review_single(
    review: SourceReviewInput,
    *,
    model: str = "",
    reasoning_effort: str = judge.DEFAULT_REASONING_EFFORT,
    max_turns: int = DEFAULT_MAX_TURNS,
    terminal_timeout_sec: int = DEFAULT_TERMINAL_TIMEOUT_SEC,
    overall_timeout_sec: float = DEFAULT_REVIEW_TIMEOUT_SEC,
) -> SourceReviewVerdict:
    """Run one isolated source review and convert all failures to grader errors."""
    if not model:
        model = judge.get_default_model()
    started = time.monotonic()
    js_container_slots = None
    container_name = ""
    transcript: list[TerminalCall] = []
    try:
        if review.project in {"v8", "sm"}:
            common.js_grading_budget_remaining("waiting to start source review")
            common.require_js_llm_call_capacity("starting source review")
            js_container_slots = common.acquire_js_container_slot()
            common.require_js_llm_call_capacity("starting source review")
        # Queue time consumes the process-wide budget through the interruptible
        # semaphore, while this per-review allowance starts only once the
        # review owns capacity.
        deadline = time.monotonic() + min(
            max(0.001, overall_timeout_sec), MAX_REVIEW_TIMEOUT_SEC
        )
        if review.project in {"v8", "sm"}:
            deadline = common.clamp_js_grading_deadline(
                deadline, "starting source review"
            )
        container_name = _start_container(
            review,
            timeout_sec=_deadline_timeout(deadline, 60, "container startup"),
        )
        _deadline_timeout(deadline, 1, "audit evidence staging")
        _stage_audit_files(
            container_name, review.work_dir, review, deadline=deadline
        )
        _deadline_timeout(deadline, 1, "model review")
        verdict = _call_model_with_terminal(
            review,
            container_name=container_name,
            model=model,
            reasoning_effort=reasoning_effort,
            max_turns=max_turns,
            terminal_timeout_sec=terminal_timeout_sec,
            overall_timeout_sec=overall_timeout_sec,
            deadline=deadline,
            transcript_out=transcript,
        )
        verdict.latency_ms = int((time.monotonic() - started) * 1000)
        return verdict
    except Exception as exc:
        return SourceReviewVerdict(
            project=review.project,
            instance_id=review.instance_id,
            poc_rel_path=review.poc_rel_path,
            in_scope=None,
            reason=f"Source review failed: {exc}",
            model=model,
            latency_ms=int((time.monotonic() - started) * 1000),
            error=str(exc),
            tool_calls=sum(call.purpose == "model" for call in transcript),
            transcript=transcript,
        )
    finally:
        try:
            if container_name:
                _remove_container(container_name)
        finally:
            if js_container_slots is not None:
                common.release_js_container_slot(js_container_slots)
