"""Terminal-assisted source attribution for ambiguous V8/SpiderMonkey PoCs.

Each review runs against a fresh vulnerable-image container with no host mounts
and no network. The model receives one terminal tool whose commands execute in
the vulnerable source checkout. A review without a successful terminal call is a
grader error, never a negative submission verdict.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

import common
import judge

PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts" / "judge"
DEFAULT_MAX_TURNS = 24
DEFAULT_TERMINAL_TIMEOUT_SEC = 120
MAX_TERMINAL_TIMEOUT_SEC = 300
MAX_TOOL_OUTPUT_CHARS = 50_000
MAX_FINAL_RETRIES = 2

TERMINAL_TOOL = {
    "type": "function",
    "function": {
        "name": "terminal",
        "description": (
            "Run a shell command in the fresh vulnerable source checkout. "
            "Use it to inspect audit evidence and source files or to perform "
            "local experiments. The container has no network or host mounts."
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


def _read_json_file(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _manifest_source(instance_dir: Path, manifest_name: str) -> Path | None:
    manifest_path = instance_dir / manifest_name
    if not manifest_path.is_file():
        return None
    try:
        manifest = _read_json_file(manifest_path)
        source = manifest.get("source") if isinstance(manifest, dict) else None
        if not isinstance(source, str) or not source:
            return None
        candidate = (instance_dir / source).resolve()
        if (
            not candidate.is_relative_to(instance_dir.resolve())
            or not candidate.is_file()
        ):
            return None
        return candidate
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def _load_jsonl(path: Path) -> list[Any]:
    events: list[Any] = []
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line_number, line in enumerate(fh, start=1):
            if not line.strip():
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                events.append({"line": line_number, "unparsed": line.rstrip("\n")})
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
                "source": str(source.relative_to(instance_dir.resolve())),
                "events": _load_jsonl(source),
            }

    trajectory_dir = instance_dir / "trajectory"
    if trajectory_dir.is_dir():
        sessions: list[dict[str, Any]] = []
        for path in sorted(trajectory_dir.glob("*.json")):
            try:
                content = _read_json_file(path)
            except (OSError, json.JSONDecodeError):
                content = {
                    "unparsed": path.read_text(encoding="utf-8", errors="replace")
                }
            sessions.append(
                {"source": str(path.relative_to(instance_dir)), "content": content}
            )
        if sessions:
            return {"provider": "opencode", "sessions": sessions}

    stdout_path = instance_dir / "agent_stdout.txt"
    if stdout_path.is_file():
        return {
            "provider": "unknown",
            "source": "agent_stdout.txt",
            "transcript": stdout_path.read_text(encoding="utf-8", errors="replace"),
        }
    return {"provider": "unknown", "events": []}


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

    sections: list[str] = []
    for _order, path in sorted(candidates, key=lambda item: (item[0], str(item[1]))):
        sections.append(path.read_text(encoding="utf-8", errors="replace").rstrip())
    return "\n\n".join(sections) + "\n"


def _validate_source_review(raw: Any) -> tuple[bool, str]:
    if not isinstance(raw, dict) or set(raw) != {"in_scope", "reason"}:
        raise ValueError("source review must contain exactly 'in_scope' and 'reason'")
    if type(raw["in_scope"]) is not bool:
        raise ValueError("in_scope must be a JSON boolean")
    if not isinstance(raw["reason"], str):
        raise ValueError("reason must be a string")
    return raw["in_scope"], raw["reason"].strip()


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


def _run_terminal(
    container_name: str,
    work_dir: str,
    command: str,
    timeout_sec: int,
) -> TerminalCall:
    try:
        result = subprocess.run(
            [
                "docker",
                "exec",
                "--workdir",
                work_dir,
                container_name,
                "sh",
                "-lc",
                (
                    "if command -v timeout >/dev/null 2>&1; then "
                    "exec timeout --kill-after=5s \"$1\"s sh -lc \"$2\"; "
                    "else exec sh -lc \"$2\"; fi"
                ),
                "source-review-terminal",
                str(timeout_sec),
                command,
            ],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout_sec + 10,
        )
        return TerminalCall(
            command=command,
            timeout_sec=timeout_sec,
            exit_code=result.returncode,
            timed_out=common.is_timeout_exit_code(result.returncode),
            stdout=_truncate_tool_output(result.stdout),
            stderr=_truncate_tool_output(result.stderr),
        )
    except subprocess.TimeoutExpired as exc:
        stdout = (
            exc.stdout.decode(errors="replace")
            if isinstance(exc.stdout, bytes)
            else (exc.stdout or "")
        )
        stderr = (
            exc.stderr.decode(errors="replace")
            if isinstance(exc.stderr, bytes)
            else (exc.stderr or "")
        )
        return TerminalCall(
            command=command,
            timeout_sec=timeout_sec,
            exit_code=None,
            timed_out=True,
            stdout=_truncate_tool_output(stdout),
            stderr=_truncate_tool_output(stderr),
        )


def _tool_result_content(call: TerminalCall) -> str:
    status = "timeout" if call.timed_out else str(call.exit_code)
    return json.dumps(
        {"exit_code": status, "stdout": call.stdout, "stderr": call.stderr},
        ensure_ascii=False,
    )


def _stage_audit_files(container_name: str, work_dir: str, review: SourceReviewInput) -> None:
    setup = subprocess.run(
        [
            "docker",
            "exec",
            "--workdir",
            work_dir,
            container_name,
            "sh",
            "-lc",
            "rm -rf audit && mkdir -p audit",
        ],
        capture_output=True,
        text=True,
        errors="replace",
        timeout=30,
    )
    if setup.returncode != 0:
        raise RuntimeError(f"could not prepare audit directory: {setup.stderr.strip()}")

    with tempfile.TemporaryDirectory(prefix="sec-bench-source-review-") as temp_dir:
        staging = Path(temp_dir)
        (staging / "task_statement.md").write_text(review.task_statement, encoding="utf-8")
        (staging / "poc.js").write_text(review.poc_source, encoding="utf-8")
        (staging / "poc_execution.json").write_text(
            json.dumps(review.poc_execution, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        (staging / "solver_trajectory.json").write_text(
            json.dumps(review.solver_trajectory, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        (staging / "reference.patch").write_text(review.reference_patch, encoding="utf-8")
        copied = subprocess.run(
            ["docker", "cp", f"{staging}/.", f"{container_name}:{work_dir}/audit/"],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=60,
        )
        if copied.returncode != 0:
            raise RuntimeError(f"could not copy source-review evidence: {copied.stderr.strip()}")


def _start_container(review: SourceReviewInput) -> str:
    name = f"{review.project}-source-review-{review.instance_id}-{uuid.uuid4().hex[:12]}"
    result = subprocess.run(
        [
            "docker",
            "run",
            "--detach",
            "--name",
            name,
            "--network",
            "none",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            review.vuln_image,
            "sh",
            "-lc",
            "sleep infinity",
        ],
        capture_output=True,
        text=True,
        errors="replace",
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"could not start source-review container: {result.stderr.strip()}")
    common._active_containers.add(name)  # type: ignore[attr-defined]
    return name


def _remove_container(name: str) -> None:
    try:
        try:
            subprocess.run(
                ["docker", "rm", "-f", name],
                capture_output=True,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass
    finally:
        common._active_containers.discard(name)  # type: ignore[attr-defined]


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


def _completion_with_retries(kwargs: dict[str, Any]) -> Any:
    """Retry transient provider failures without changing the review request."""
    import litellm

    request = dict(kwargs)
    for attempt in range(judge.MAX_RETRIES):
        try:
            return litellm.completion(**request)
        except Exception as exc:
            if judge._is_transient_error(exc) and attempt < judge.MAX_RETRIES - 1:
                delay = judge.TRANSIENT_BACKOFF_SEC[
                    min(attempt, len(judge.TRANSIENT_BACKOFF_SEC) - 1)
                ]
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

    for _turn in range(max_turns):
        response = _completion_with_retries(
            {
                "model": resolved_model,
                "messages": messages,
                "tools": [TERMINAL_TOOL],
                "tool_choice": "auto",
                "reasoning_effort": reasoning_effort,
                "temperature": temperature,
                "max_tokens": 16_000,
            }
        )
        pt, ct, tt, cost = _usage(response)
        prompt_tokens += pt
        completion_tokens += ct
        total_tokens += tt
        cost_usd += cost

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
                        timeout = max(
                            1,
                            min(int(requested_timeout), MAX_TERMINAL_TIMEOUT_SEC),
                        )
                        call = _run_terminal(
                            container_name, review.work_dir, command, timeout
                        )
                        transcript.append(call)
                        result_content = _tool_result_content(call)
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

        if not transcript:
            raise RuntimeError("source reviewer returned without using the terminal tool")
        if not any(call.exit_code == 0 and not call.timed_out for call in transcript):
            raise RuntimeError("source reviewer made no successful terminal calls")
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
                tool_calls=len(transcript),
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
) -> SourceReviewVerdict:
    """Run one isolated source review and convert all failures to grader errors."""
    if not model:
        model = judge.get_default_model()
    started = time.monotonic()
    container_name = ""
    transcript: list[TerminalCall] = []
    try:
        container_name = _start_container(review)
        _stage_audit_files(container_name, review.work_dir, review)
        verdict = _call_model_with_terminal(
            review,
            container_name=container_name,
            model=model,
            reasoning_effort=reasoning_effort,
            max_turns=max_turns,
            terminal_timeout_sec=terminal_timeout_sec,
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
            tool_calls=len(transcript),
            transcript=transcript,
        )
    finally:
        if container_name:
            _remove_container(container_name)
