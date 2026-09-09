"""LLM-as-a-judge helpers for SEC-bench PoC classification.

Linux uses one combined judge over vulnerable/fixed/latest evidence. V8 and
SpiderMonkey use the execution judge in this module independently for each
image; ambiguous fixed-image results are resolved by ``source_review.py``.
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

import common

PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts" / "judge"
DEFAULT_BEDROCK_MODEL = "us.anthropic.claude-sonnet-4-6"
DEFAULT_OPENAI_MODEL = "gpt-5.4"
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-6"
DEFAULT_REASONING_EFFORT = "high"
DEFAULT_TEMPERATURE = 0
CLAUDE_THINKING_TEMPERATURE = 1
MAX_STDERR_CHARS = 8_000
MAX_STDOUT_CHARS = 4_000
# Preserve the combined/Linux judge's established prompt size. The staged
# JavaScript judge receives the complete selected PoC under its separate cap.
MAX_POC_CHARS = 30_000
MAX_EXECUTION_POC_CHARS = 128 * 1024
MAX_TASK_CHARS = 40_000
MAX_HISTORICAL_STDERR_CHARS = 8_000
DEFAULT_JUDGE_WORKERS = 5
DEFAULT_JUDGE_SAMPLES = 1
DEFAULT_LLM_REQUEST_TIMEOUT_SEC = 120.0
DEFAULT_LLM_OVERALL_TIMEOUT_SEC = 360.0
MAX_EXECUTION_JUDGE_OUTPUT_TOKENS = 2_048

OUTCOMES = ("verified", "unsure", "illegal")


@dataclass
class JudgeVerdict:
    project: str
    instance_id: str
    poc_rel_path: str
    outcome: str
    reason: str
    model: str
    latency_ms: int = 0
    error: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    decision_step: str = ""


@dataclass
class JudgeInput:
    project: str
    instance_id: str
    target_source_files: list[str]
    target_vulnerability_type: str
    error_type: str
    command_options: str
    poc_rel_path: str
    poc_source: str
    vuln_exit_code: str
    vuln_stderr: str
    vuln_stdout: str
    fixed_exit_code: str
    fixed_stderr: str
    fixed_stdout: str
    latest_exit_code: str
    latest_stderr: str
    latest_stdout: str


@dataclass
class ExecutionJudgeInput:
    """Evidence for judging one PoC execution on exactly one image."""

    project: str
    instance_id: str
    image_kind: str
    task_statement: str
    poc_rel_path: str
    poc_source: str
    historical_stderr: str
    actual_exit_code: str
    actual_timed_out: bool
    actual_stderr: str
    actual_stdout: str
    actual_engine_started: bool = True
    actual_oom_killed: bool = False
    actual_infrastructure_error: str = ""
    actual_infrastructure_kind: str = ""
    actual_input_integrity_error: bool = False
    actual_stdout_sha256: str = ""
    actual_stderr_sha256: str = ""
    authoritative_target_source_files: tuple[str, ...] = ()
    authoritative_target_vulnerability_type: str = ""
    authoritative_error_type: str = ""
    authoritative_command_options: str = ""


@dataclass
class ExecutionJudgeVerdict:
    project: str
    instance_id: str
    poc_rel_path: str
    image_kind: str
    reproduced: bool | None
    reason: str
    model: str
    latency_ms: int = 0
    error: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0


def _is_bedrock_env() -> bool:
    return bool(
        os.environ.get("AWS_ACCESS_KEY_ID")
        and os.environ.get("AWS_SECRET_ACCESS_KEY")
        and os.environ.get("AWS_REGION_NAME")
        and os.environ.get("CLAUDE_CODE_USE_BEDROCK")
    )


def _is_bedrock_model(model: str) -> bool:
    return model.startswith("bedrock/") or model.startswith("us.")


def get_default_model() -> str:
    if _is_bedrock_env():
        return DEFAULT_BEDROCK_MODEL
    if os.environ.get("ANTHROPIC_API_KEY"):
        return DEFAULT_ANTHROPIC_MODEL
    return DEFAULT_OPENAI_MODEL


def resolve_model(model: str) -> str:
    if model.startswith("bedrock/"):
        return model
    if model.startswith("us."):
        return f"bedrock/{model}"
    return model


def _uses_claude_extended_thinking(resolved_model: str, reasoning_effort: str) -> bool:
    effort = (reasoning_effort or "").strip().lower()
    if effort in {"", "none", "off", "disabled"}:
        return False
    model = resolved_model.lower()
    return "claude" in model or "anthropic" in model


def _temperature_for_model(resolved_model: str, reasoning_effort: str) -> int:
    if _uses_claude_extended_thinking(resolved_model, reasoning_effort):
        return CLAUDE_THINKING_TEMPERATURE
    return DEFAULT_TEMPERATURE


def check_api_key(model: str | None = None) -> bool:
    if model is None:
        model = get_default_model()
    if _is_bedrock_model(model):
        return _is_bedrock_env()
    if "claude" in model or "anthropic" in model:
        return bool(os.environ.get("ANTHROPIC_API_KEY"))
    return bool(os.environ.get("OPENAI_API_KEY"))


def warn_missing_api_key(model: str | None = None) -> None:
    if model is None:
        model = get_default_model()
    if _is_bedrock_model(model):
        missing = [
            k
            for k in (
                "AWS_ACCESS_KEY_ID",
                "AWS_SECRET_ACCESS_KEY",
                "AWS_REGION_NAME",
                "CLAUDE_CODE_USE_BEDROCK",
            )
            if not os.environ.get(k)
        ]
        print(
            f"[WARN] AWS Bedrock environment not fully configured.\n"
            f"       Missing: {', '.join(missing)}\n"
            f"       Required: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, "
            f"AWS_REGION_NAME, CLAUDE_CODE_USE_BEDROCK",
            file=sys.stderr,
            flush=True,
        )
    elif "claude" in model or "anthropic" in model:
        print(
            "[WARN] ANTHROPIC_API_KEY environment variable is not set.\n"
            "       Set it with: export ANTHROPIC_API_KEY=<your-key>",
            file=sys.stderr,
            flush=True,
        )
    else:
        print(
            "[WARN] OPENAI_API_KEY environment variable is not set.\n"
            "       Set it with: export OPENAI_API_KEY=<your-key>",
            file=sys.stderr,
            flush=True,
        )


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    half = max_chars // 2
    return (
        text[:half]
        + f"\n\n... [{len(text) - max_chars} chars truncated] ...\n\n"
        + text[-half:]
    )


def template_name(project: str) -> str:
    return f"{project}.j2"


def _template_environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(PROMPTS_DIR)),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _load_named_template(name: str) -> Any:
    return _template_environment().get_template(name)


def _load_template(project: str) -> Any:
    return _load_named_template(template_name(project))


def build_prompt(ji: JudgeInput) -> str:
    """Render the judge prompt for ``ji`` using the project's template."""
    return _render_prompt(_load_template(ji.project), ji)


def build_execution_prompt(ji: ExecutionJudgeInput) -> str:
    """Render the single-image execution-judge prompt for ``ji``."""
    return _load_named_template("execution.j2").render(
        project=ji.project,
        instance_id=ji.instance_id,
        image_kind=ji.image_kind,
        task_statement=ji.task_statement,
        poc_rel_path=ji.poc_rel_path,
        poc_source=ji.poc_source,
        historical_stderr=ji.historical_stderr,
        actual_exit_code=ji.actual_exit_code,
        actual_timed_out=ji.actual_timed_out,
        actual_stderr=ji.actual_stderr,
        actual_stdout=ji.actual_stdout,
        actual_engine_started=ji.actual_engine_started,
        actual_oom_killed=ji.actual_oom_killed,
        actual_infrastructure_error=ji.actual_infrastructure_error,
        actual_infrastructure_kind=ji.actual_infrastructure_kind,
        actual_input_integrity_error=ji.actual_input_integrity_error,
        actual_stdout_sha256=ji.actual_stdout_sha256,
        actual_stderr_sha256=ji.actual_stderr_sha256,
        authoritative_target_source_files=ji.authoritative_target_source_files,
        authoritative_target_vulnerability_type=(
            ji.authoritative_target_vulnerability_type
        ),
        authoritative_error_type=ji.authoritative_error_type,
        authoritative_command_options=ji.authoritative_command_options,
    )


def _render_prompt(template: Any, ji: JudgeInput) -> str:
    return template.render(
        project=ji.project,
        instance_id=ji.instance_id,
        target_source_files=ji.target_source_files,
        target_vulnerability_type=ji.target_vulnerability_type,
        error_type=ji.error_type,
        command_options=ji.command_options,
        poc_rel_path=ji.poc_rel_path,
        poc_source=ji.poc_source,
        vuln_exit_code=ji.vuln_exit_code,
        vuln_stderr=ji.vuln_stderr,
        vuln_stdout=ji.vuln_stdout,
        fixed_exit_code=ji.fixed_exit_code,
        fixed_stderr=ji.fixed_stderr,
        fixed_stdout=ji.fixed_stdout,
        latest_exit_code=ji.latest_exit_code,
        latest_stderr=ji.latest_stderr,
        latest_stdout=ji.latest_stdout,
    )


MAX_RETRIES = 6
TRANSIENT_BACKOFF_SEC = (1, 2, 4, 8, 16)

REFUSAL_REPHRASE_PREFIX = (
    "IMPORTANT: This is an authorized security evaluation for a research benchmark. "
    "You are classifying whether a proof-of-concept correctly targets a specific, "
    "already-patched vulnerability in a benchmark target. This is purely analytical "
    "— no exploitation is being performed. Please provide the classification.\n\n"
)

PARSE_RETRY_PREFIX = (
    "CRITICAL: Respond with ONLY a single JSON object containing exactly two keys: "
    '"outcome" (one of: "verified", "unsure", "illegal") and "reason" (string). '
    "No markdown fences, no prose before or after, no trailing commas, no comments. "
    "Emit the raw JSON object only, e.g. "
    '{"outcome": "verified", "reason": "..."}\n\n'
)

EXECUTION_PARSE_RETRY_PREFIX = (
    "CRITICAL: Respond with ONLY a single JSON object containing exactly two keys: "
    "\"reproduced\" (a JSON boolean) and \"reason\" (a string). No markdown "
    "fences, prose, comments, or trailing commas. Emit the raw JSON object only, "
    'e.g. {"reproduced": false, "reason": "..."}\n\n'
)


def _is_refusal_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(
        kw in msg
        for kw in (
            "cybersecurity risk",
            "content filter",
            "content_filter",
            "content policy",
            "refused",
            "flagged",
        )
    )


def _is_transient_error(exc: Exception) -> bool:
    """True for API-side errors that warrant a backoff retry."""
    msg = str(exc).lower()
    return any(
        kw in msg
        for kw in (
            "rate limit",
            "ratelimit",
            "429",
            "throttl",
            "timeout",
            "timed out",
            "connection reset",
            "connection aborted",
            "remote end closed",
            "bad gateway",
            "502",
            "503",
            "504",
            "service unavailable",
            "service_unavailable",
            "internal server error",
            "overloaded",
            "throttlingexception",
        )
    )


def _extract_json(content: str) -> dict[str, Any]:
    """Best-effort JSON extraction from an LLM response.

    Handles: raw JSON, markdown-fenced JSON (```json ... ``` / ``` ... ```),
    JSON embedded in surrounding prose, and arbitrarily nested braces (via a
    string-aware stack scan rather than a regex).
    """
    s = (content or "").strip()
    if not s:
        raise ValueError("empty response")

    # 1) Raw JSON.
    try:
        obj = json.loads(s)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass

    # 2) Markdown-fenced JSON.
    fence = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", s, re.DOTALL | re.IGNORECASE)
    if fence:
        inner = fence.group(1).strip()
        try:
            obj = json.loads(inner)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass

    # 3) Stack-balanced top-level { ... } block, ignoring braces in string
    #    literals. Try every opening brace from first to last so we don't
    #    lock onto a malformed earlier block.
    for start in (i for i, ch in enumerate(s) if ch == "{"):
        block = _scan_balanced_brace_block(s, start)
        if block is None:
            continue
        try:
            obj = json.loads(block)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            continue

    preview = content[:300].replace("\n", "\\n")
    raise ValueError(f"could not parse JSON from response: {preview!r}")


def _scan_balanced_brace_block(s: str, start: int) -> str | None:
    """Return the balanced ``{...}`` block beginning at ``s[start]``.

    Tracks JSON string literals so braces inside strings are ignored.
    Returns ``None`` if the block is unterminated.
    """
    depth = 0
    in_str = False
    esc = False
    i = start
    while i < len(s):
        ch = s[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return s[start : i + 1]
        i += 1
    return None


@dataclass
class _LLMResult:
    parsed: dict[str, Any]
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0


class _SchemaError(ValueError):
    """Raised when the parsed JSON is missing required fields or has bad values."""


def _validate_schema(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise _SchemaError(f"expected JSON object, got {type(raw).__name__}")
    if "outcome" not in raw:
        raise _SchemaError("missing required key: 'outcome'")
    outcome = str(raw.get("outcome", "")).strip().lower()
    if outcome not in OUTCOMES:
        raise _SchemaError(
            f"outcome must be one of {OUTCOMES}, got {raw.get('outcome')!r}"
        )
    reason = raw.get("reason", "")
    if not isinstance(reason, str):
        raise _SchemaError(f"reason must be a string, got {type(reason).__name__}")
    return {"outcome": outcome, "reason": reason.strip()}


def _validate_execution_schema(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise _SchemaError(f"expected JSON object, got {type(raw).__name__}")
    if set(raw) != {"reproduced", "reason"}:
        raise _SchemaError(
            "execution verdict must contain exactly 'reproduced' and 'reason'"
        )
    reproduced = raw["reproduced"]
    if type(reproduced) is not bool:
        raise _SchemaError("reproduced must be a JSON boolean")
    reason = raw["reason"]
    if not isinstance(reason, str):
        raise _SchemaError(f"reason must be a string, got {type(reason).__name__}")
    reason = reason.strip()
    if not reason:
        raise _SchemaError("reason must be a non-empty string")
    return {"reproduced": reproduced, "reason": reason}


def _parse_outcome(raw: dict[str, Any]) -> tuple[str, str]:
    """Return (outcome, reason) from a validated response dict.

    ``raw`` is assumed to have already passed :func:`_validate_schema`.
    """
    return raw["outcome"], raw["reason"]


def _call_llm(
    prompt: str,
    model: str,
    reasoning_effort: str,
    *,
    validator: Callable[[Any], dict[str, Any]] = _validate_schema,
    parse_retry_prefix: str = PARSE_RETRY_PREFIX,
    request_timeout_sec: float | None = None,
    overall_timeout_sec: float | None = None,
    max_output_tokens: int = 16_000,
) -> _LLMResult:
    """Call the LLM with layered retries for transient / refusal / parse failures.

    Retry policy:
      * Transient API error (rate limit, 5xx, connection drop, overloaded)
        → exponential backoff and resend the same prompt.
      * Content-policy refusal → prepend :data:`REFUSAL_REPHRASE_PREFIX`.
      * Malformed JSON or schema violation → prepend :data:`PARSE_RETRY_PREFIX`
        to the next request so the model re-emits strict JSON.

    The final exception (if any) is raised after ``MAX_RETRIES`` attempts so
    the caller records a meaningful error on the verdict.
    """
    import litellm

    litellm.drop_params = True
    resolved_model = resolve_model(model)
    temperature = _temperature_for_model(resolved_model, reasoning_effort)

    current_prompt = prompt
    last_exc: Exception | None = None
    deadline = (
        time.monotonic() + max(0.001, float(overall_timeout_sec))
        if overall_timeout_sec is not None
        else common.js_grading_budget_deadline()
    )
    if deadline is not None:
        deadline = common.clamp_js_grading_deadline(
            deadline, "an LLM judge request"
        )

    for attempt in range(MAX_RETRIES):
        remaining = deadline - time.monotonic() if deadline is not None else None
        if remaining is not None and remaining <= 0:
            raise TimeoutError("judge model requests exceeded their overall deadline")
        kwargs: dict[str, Any] = {
            "model": resolved_model,
            "messages": [{"role": "user", "content": current_prompt}],
            "reasoning_effort": reasoning_effort,
            "temperature": temperature,
            "max_tokens": max_output_tokens,
        }
        if request_timeout_sec is not None or remaining is not None:
            request_cap = (
                float(request_timeout_sec)
                if request_timeout_sec is not None
                else float(remaining)
            )
            kwargs["timeout"] = max(
                0.001,
                min(request_cap, float(remaining))
                if remaining is not None
                else request_cap,
            )

        # Count every real provider attempt, including retries for transport,
        # refusal, and malformed output. Reservation is atomic across workers.
        common.consume_js_llm_call("an LLM judge provider call")
        try:
            response = litellm.completion(**kwargs)
            content = response.choices[0].message.content or ""

            usage = getattr(response, "usage", None)
            prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
            completion_tokens = getattr(usage, "completion_tokens", 0) or 0
            total_tokens = getattr(usage, "total_tokens", 0) or 0
            try:
                cost_usd = litellm.completion_cost(completion_response=response)
            except Exception:
                cost_usd = 0.0

            raw = _extract_json(content)
            validated = validator(raw)

            return _LLMResult(
                parsed=validated,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost_usd=cost_usd,
            )
        except (_SchemaError, ValueError, json.JSONDecodeError) as exc:
            # Parse / schema failure: re-prompt with a strict format reminder.
            last_exc = exc
            if attempt < MAX_RETRIES - 1:
                current_prompt = parse_retry_prefix + prompt
                continue
            raise
        except Exception as exc:
            last_exc = exc
            if _is_refusal_error(exc) and attempt < MAX_RETRIES - 1:
                current_prompt = REFUSAL_REPHRASE_PREFIX + prompt
                continue
            if _is_transient_error(exc) and attempt < MAX_RETRIES - 1:
                delay = TRANSIENT_BACKOFF_SEC[
                    min(attempt, len(TRANSIENT_BACKOFF_SEC) - 1)
                ]
                if deadline is not None:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError(
                            "judge model requests exceeded their overall deadline"
                        ) from exc
                    delay = min(delay, remaining)
                time.sleep(delay)
                continue
            raise

    raise last_exc  # type: ignore[misc]


def _judge_single_call(
    prompt: str,
    judge_input: JudgeInput,
    model: str,
    reasoning_effort: str,
) -> JudgeVerdict:
    start = time.monotonic()
    try:
        result = _call_llm(prompt, model, reasoning_effort)
        outcome, reason = _parse_outcome(result.parsed)
        return JudgeVerdict(
            project=judge_input.project,
            instance_id=judge_input.instance_id,
            poc_rel_path=judge_input.poc_rel_path,
            outcome=outcome,
            reason=reason,
            model=model,
            latency_ms=int((time.monotonic() - start) * 1000),
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            total_tokens=result.total_tokens,
            cost_usd=result.cost_usd,
        )
    except Exception as exc:
        return JudgeVerdict(
            project=judge_input.project,
            instance_id=judge_input.instance_id,
            poc_rel_path=judge_input.poc_rel_path,
            outcome="error",
            reason=f"LLM call failed: {exc}",
            model=model,
            latency_ms=int((time.monotonic() - start) * 1000),
            error=str(exc),
        )


def judge_execution_single(
    judge_input: ExecutionJudgeInput,
    *,
    model: str = "",
    reasoning_effort: str = DEFAULT_REASONING_EFFORT,
) -> ExecutionJudgeVerdict:
    """Judge one concrete execution without consulting other image runs."""
    if not model:
        model = get_default_model()
    start = time.monotonic()
    try:
        prompt = build_execution_prompt(judge_input)
        result = _call_llm(
            prompt,
            model,
            reasoning_effort,
            validator=_validate_execution_schema,
            parse_retry_prefix=EXECUTION_PARSE_RETRY_PREFIX,
            request_timeout_sec=DEFAULT_LLM_REQUEST_TIMEOUT_SEC,
            overall_timeout_sec=DEFAULT_LLM_OVERALL_TIMEOUT_SEC,
            max_output_tokens=MAX_EXECUTION_JUDGE_OUTPUT_TOKENS,
        )
        return ExecutionJudgeVerdict(
            project=judge_input.project,
            instance_id=judge_input.instance_id,
            poc_rel_path=judge_input.poc_rel_path,
            image_kind=judge_input.image_kind,
            reproduced=result.parsed["reproduced"],
            reason=result.parsed["reason"],
            model=model,
            latency_ms=int((time.monotonic() - start) * 1000),
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            total_tokens=result.total_tokens,
            cost_usd=result.cost_usd,
        )
    except Exception as exc:
        return ExecutionJudgeVerdict(
            project=judge_input.project,
            instance_id=judge_input.instance_id,
            poc_rel_path=judge_input.poc_rel_path,
            image_kind=judge_input.image_kind,
            reproduced=None,
            reason=f"Execution judge failed: {exc}",
            model=model,
            latency_ms=int((time.monotonic() - start) * 1000),
            error=str(exc),
        )


def judge_execution_all(
    inputs: list[ExecutionJudgeInput],
    *,
    model: str = "",
    reasoning_effort: str = DEFAULT_REASONING_EFFORT,
    workers: int = DEFAULT_JUDGE_WORKERS,
    print_fn: Any = None,
) -> list[ExecutionJudgeVerdict]:
    """Judge independent image executions in stable input order."""
    if not model:
        model = get_default_model()
    if not inputs:
        return []

    _print = print_fn or (lambda msg, **kw: print(msg, flush=True))
    total = len(inputs)
    _print(f"[execution judge] Evaluating {total} execution(s) with {model}...")

    def report(done: int, inp: ExecutionJudgeInput, verdict: ExecutionJudgeVerdict) -> None:
        label = "error" if verdict.reproduced is None else str(verdict.reproduced).lower()
        _print(
            f"[execution judge] [{done}/{total}] {inp.instance_id}/"
            f"{inp.poc_rel_path} ({inp.image_kind}): reproduced={label} "
            f"({verdict.latency_ms}ms)"
        )

    if workers <= 1 or total == 1:
        verdicts: list[ExecutionJudgeVerdict] = []
        for idx, inp in enumerate(inputs, start=1):
            verdict = judge_execution_single(
                inp, model=model, reasoning_effort=reasoning_effort
            )
            verdicts.append(verdict)
            report(idx, inp, verdict)
        return verdicts

    executor = ThreadPoolExecutor(
        max_workers=min(workers, total), thread_name_prefix="execution-judge"
    )
    future_to_idx = {
        executor.submit(
            judge_execution_single,
            inp,
            model=model,
            reasoning_effort=reasoning_effort,
        ): idx
        for idx, inp in enumerate(inputs)
    }
    results_by_idx: dict[int, ExecutionJudgeVerdict] = {}
    completed = 0
    for future in as_completed(future_to_idx):
        idx = future_to_idx[future]
        verdict = future.result()
        results_by_idx[idx] = verdict
        completed += 1
        report(completed, inputs[idx], verdict)
    executor.shutdown(wait=True)
    return [results_by_idx[idx] for idx in range(total)]


def _majority_verdict(samples: list[JudgeVerdict]) -> JudgeVerdict:
    """Majority vote over outcomes; aggregates usage across samples."""
    from collections import Counter

    valid = [s for s in samples if s.outcome != "error"]
    if not valid:
        return samples[0]

    counts = Counter(s.outcome for s in valid)
    winning = counts.most_common(1)[0][0]
    representative = next(s for s in valid if s.outcome == winning)

    total_prompt = sum(s.prompt_tokens for s in samples)
    total_completion = sum(s.completion_tokens for s in samples)
    total_tokens = sum(s.total_tokens for s in samples)
    total_cost = sum(s.cost_usd for s in samples)
    total_latency = sum(s.latency_ms for s in samples)

    return JudgeVerdict(
        project=representative.project,
        instance_id=representative.instance_id,
        poc_rel_path=representative.poc_rel_path,
        outcome=representative.outcome,
        reason=representative.reason,
        model=representative.model,
        latency_ms=total_latency,
        prompt_tokens=total_prompt,
        completion_tokens=total_completion,
        total_tokens=total_tokens,
        cost_usd=total_cost,
    )


def judge_single(
    judge_input: JudgeInput,
    *,
    model: str = "",
    reasoning_effort: str = DEFAULT_REASONING_EFFORT,
    samples: int = DEFAULT_JUDGE_SAMPLES,
) -> JudgeVerdict:
    if not model:
        model = get_default_model()
    template = _load_template(judge_input.project)
    prompt = _render_prompt(template, judge_input)

    if samples <= 1:
        return _judge_single_call(prompt, judge_input, model, reasoning_effort)

    results: list[JudgeVerdict] = [
        _judge_single_call(prompt, judge_input, model, reasoning_effort)
        for _ in range(samples)
    ]
    return _majority_verdict(results)


def judge_all(
    inputs: list[JudgeInput],
    *,
    model: str = "",
    reasoning_effort: str = DEFAULT_REASONING_EFFORT,
    workers: int = DEFAULT_JUDGE_WORKERS,
    samples: int = DEFAULT_JUDGE_SAMPLES,
    print_fn: Any = None,
) -> list[JudgeVerdict]:
    if not model:
        model = get_default_model()
    if not inputs:
        return []

    _print = print_fn or (lambda msg, **kw: print(msg, flush=True))
    total = len(inputs)
    samples_info = f", samples={samples}" if samples > 1 else ""
    _print(
        f"[judge] Evaluating {total} PoC(s) with {model}{samples_info}..."
    )

    lock = threading.Lock()

    if workers <= 1 or total == 1:
        verdicts: list[JudgeVerdict] = []
        for idx, inp in enumerate(inputs):
            v = judge_single(
                inp, model=model, reasoning_effort=reasoning_effort, samples=samples
            )
            verdicts.append(v)
            _print(
                f"[judge] [{idx + 1}/{total}] {inp.instance_id}/{inp.poc_rel_path}: "
                f"{v.outcome} ({v.latency_ms}ms)"
            )
        return verdicts

    effective_workers = min(workers, total)
    executor = ThreadPoolExecutor(
        max_workers=effective_workers, thread_name_prefix="judge"
    )
    future_to_idx: dict[Any, int] = {}
    for idx, inp in enumerate(inputs):
        future = executor.submit(
            judge_single,
            inp,
            model=model,
            reasoning_effort=reasoning_effort,
            samples=samples,
        )
        future_to_idx[future] = idx

    results_by_idx: dict[int, JudgeVerdict] = {}
    completed = 0
    for future in as_completed(future_to_idx):
        idx = future_to_idx[future]
        v = future.result()
        results_by_idx[idx] = v
        completed += 1
        inp = inputs[idx]
        with lock:
            _print(
                f"[judge] [{completed}/{total}] {inp.instance_id}/{inp.poc_rel_path}: "
                f"{v.outcome} ({v.latency_ms}ms)"
            )

    executor.shutdown(wait=True)
    return [results_by_idx[i] for i in range(total)]


def write_judge_csv(verdicts: list[JudgeVerdict], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "judge_verdicts.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            [
                "project",
                "instance_id",
                "poc_rel_path",
                "outcome",
                "reason",
                "decision_step",
                "model",
                "latency_ms",
                "error",
            ]
        )
        for v in verdicts:
            writer.writerow(
                [
                    v.project,
                    v.instance_id,
                    v.poc_rel_path,
                    v.outcome,
                    v.reason,
                    v.decision_step,
                    v.model,
                    v.latency_ms,
                    v.error,
                ]
            )
    return csv_path


def write_judge_details_json(verdicts: list[JudgeVerdict], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "judge_verdicts.json"
    records = [
        {
            "project": v.project,
            "instance_id": v.instance_id,
            "poc_rel_path": v.poc_rel_path,
            "outcome": v.outcome,
            "reason": v.reason,
            "decision_step": v.decision_step,
            "model": v.model,
            "latency_ms": v.latency_ms,
            "prompt_tokens": v.prompt_tokens,
            "completion_tokens": v.completion_tokens,
            "total_tokens": v.total_tokens,
            "cost_usd": v.cost_usd,
            "error": v.error,
        }
        for v in verdicts
    ]
    json_path.write_text(
        json.dumps(records, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return json_path


def write_judge_usage(verdicts: list[JudgeVerdict], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    usage_path = out_dir / "judge_usage.json"

    total_prompt = sum(v.prompt_tokens for v in verdicts)
    total_completion = sum(v.completion_tokens for v in verdicts)
    total_tokens = sum(v.total_tokens for v in verdicts)
    total_cost = sum(v.cost_usd for v in verdicts)
    total_latency_ms = sum(v.latency_ms for v in verdicts)
    evaluated = sum(1 for v in verdicts if v.outcome != "error")
    errors = sum(1 for v in verdicts if v.outcome == "error")

    model = verdicts[0].model if verdicts else "unknown"

    usage_data = {
        "model": model,
        "total_requests": len(verdicts),
        "successful_requests": evaluated,
        "failed_requests": errors,
        "token_usage": {
            "prompt_tokens": total_prompt,
            "completion_tokens": total_completion,
            "total_tokens": total_tokens,
        },
        "cost": {
            "total_usd": round(total_cost, 6),
            "avg_per_request_usd": round(total_cost / len(verdicts), 6)
            if verdicts
            else 0.0,
        },
        "latency": {
            "total_ms": total_latency_ms,
            "avg_per_request_ms": round(total_latency_ms / len(verdicts))
            if verdicts
            else 0,
        },
        "failures": [
            {
                "instance_id": v.instance_id,
                "poc_rel_path": v.poc_rel_path,
                "reason": v.error,
            }
            for v in verdicts
            if v.outcome == "error" and v.error
        ],
    }

    usage_path.write_text(
        json.dumps(usage_data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return usage_path
