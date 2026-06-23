"""Codex agent output formatter.

Codex has two JSONL shapes in current harness data:

* ``codex exec --json`` stdout events such as ``thread.started`` and
  ``item.completed`` with a nested ``item`` object.
* persisted session JSONL envelopes such as ``event_msg`` and
  ``response_item`` with a nested ``payload`` object.

This formatter handles both shapes and falls back to plain text for non-JSON
Codex output.
"""

from __future__ import annotations

import json
import shlex
from typing import Any

from .ansi import BOLD, CYAN, DIM, GREEN, ITALIC, MAGENTA, NC, RED, YELLOW

MAX_RESULT_PREVIEW = 120
MAX_OUTPUT_PREVIEW = 240


def _truncate(text: str, limit: int = MAX_RESULT_PREVIEW) -> str:
    text = text.replace("\n", " ").strip()
    return text if len(text) <= limit else text[:limit] + "..."


def _json_preview(value: Any, limit: int = MAX_RESULT_PREVIEW) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, str):
        return _truncate(value, limit)
    try:
        rendered = json.dumps(value, ensure_ascii=False, sort_keys=True)
    except TypeError:
        rendered = str(value)
    return _truncate(rendered, limit)


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                text = (
                    item.get("text")
                    or item.get("output_text")
                    or item.get("input_text")
                    or item.get("content")
                )
                if text:
                    parts.append(str(text))
            elif item:
                parts.append(str(item))
        return "\n".join(parts)
    if content:
        return str(content)
    return ""


def _command_summary(command: str) -> str:
    command = command.strip()
    if not command:
        return "Bash(?)"
    try:
        parts = shlex.split(command)
    except ValueError:
        return f"Bash({_truncate(command, 100)})"
    if len(parts) >= 3 and parts[0].endswith("bash") and parts[1] == "-lc":
        command = parts[2]
    return f"Bash({_truncate(command, 100)})"


def _format_session(payload: dict) -> str | None:
    session_id = (
        payload.get("thread_id")
        or payload.get("id")
        or payload.get("session_id")
        or payload.get("sessionID")
    )
    model = payload.get("model") or payload.get("modelID")
    cwd = payload.get("cwd")
    parts = [f"{BOLD}{CYAN}[session]{NC}"]
    if session_id:
        parts.append(f"id={session_id}")
    if model:
        parts.append(f"model={BOLD}{model}{NC}")
    if cwd:
        parts.append(f"cwd={cwd}")
    return "  ".join(parts)


def _format_done(payload: dict) -> str | None:
    status = payload.get("status") or payload.get("reason") or "done"
    duration_ms = payload.get("duration_ms") or payload.get("durationMs")
    parts = [f"\n{BOLD}{CYAN}[done]{NC} {GREEN}{status}{NC}"]
    if duration_ms:
        try:
            parts.append(f"duration={float(duration_ms) / 60000:.1f}m")
        except (TypeError, ValueError):
            parts.append(f"duration_ms={duration_ms}")
    last = payload.get("last_agent_message")
    if last:
        parts.append(_truncate(str(last), 300))
    return "  ".join(parts)


def _format_error(payload: dict) -> str | None:
    message = payload.get("message") or payload.get("error") or payload
    return f"  {RED}ERROR: {_json_preview(message, 240)}{NC}"


def _format_message_payload(payload: dict) -> str | None:
    role = payload.get("role", "")
    text = _content_text(payload.get("content")).strip()
    if not text:
        return None
    if role == "assistant":
        return f"  {BOLD}{text}{NC}"
    if role in ("system", "developer"):
        return f"  {DIM}< {role} prompt ({len(text)} chars){NC}"
    if role == "user":
        return f"  {DIM}< user prompt ({len(text)} chars){NC}"
    return f"  {text}"


def _format_reasoning_payload(payload: dict) -> str | None:
    summary = payload.get("summary")
    content = payload.get("content")
    text = _content_text(summary) or _content_text(content)
    text = text.strip()
    if not text:
        return None
    return f"  {MAGENTA}{ITALIC}... thinking ({len(text)} chars){NC}"


def _format_function_call_payload(payload: dict) -> str | None:
    name = payload.get("name", "?")
    args = payload.get("arguments") or payload.get("input") or ""
    preview = _json_preview(args, 120)
    return f"  {YELLOW}>{NC} {name}({preview})"


def _format_function_output_payload(payload: dict) -> str | None:
    output = payload.get("output")
    if output is None:
        output = payload.get("result")
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    if isinstance(output, str) and output.lstrip().startswith("{"):
        try:
            decoded = json.loads(output)
        except json.JSONDecodeError:
            decoded = None
        if isinstance(decoded, dict):
            output = decoded.get("output", output)
            decoded_meta = decoded.get("metadata")
            if isinstance(decoded_meta, dict) and not metadata:
                metadata = decoded_meta
    exit_code = metadata.get("exit_code")
    prefix = f"exit {exit_code}: " if exit_code is not None else ""
    return f"  {DIM}< {prefix}{_json_preview(output, MAX_OUTPUT_PREVIEW)}{NC}"


def _format_event_msg(payload: dict) -> str | None:
    etype = payload.get("type", "")
    if etype == "agent_message":
        message = str(payload.get("message") or "").strip()
        if not message:
            return None
        phase = payload.get("phase")
        if phase == "final_answer":
            return f"  {BOLD}{GREEN}{message}{NC}"
        return f"  {BOLD}{message}{NC}"
    if etype == "task_started":
        return None
    if etype == "task_complete":
        return _format_done(payload)
    if etype in ("turn_aborted", "error"):
        return _format_error(payload)
    if etype == "token_count":
        info = payload.get("info")
        if not isinstance(info, dict):
            return None
        usage = info.get("last_token_usage") or info.get("total_token_usage")
        if not isinstance(usage, dict):
            return None
        total = usage.get("total_tokens")
        if total is None:
            return None
        return f"  {DIM}[tokens] {total}{NC}"
    return None


def _format_response_item(payload: dict) -> str | None:
    ptype = payload.get("type", "")
    if ptype == "message":
        return _format_message_payload(payload)
    if ptype == "reasoning":
        return _format_reasoning_payload(payload)
    if ptype in ("function_call", "custom_tool_call"):
        return _format_function_call_payload(payload)
    if ptype in ("function_call_output", "custom_tool_call_output"):
        return _format_function_output_payload(payload)
    if ptype == "web_search_call":
        status = payload.get("status") or ""
        return f"  {YELLOW}>{NC} web_search {DIM}{status}{NC}"
    return None


def _format_stdout_item(obj: dict) -> str | None:
    etype = obj.get("type", "")
    if etype == "thread.started":
        return _format_session(obj)
    if etype in ("turn.started", "turn.completed"):
        return None
    if etype in ("error", "turn.failed"):
        return _format_error(obj)

    item = obj.get("item")
    if not isinstance(item, dict):
        return None

    item_type = item.get("type", "")
    if item_type == "agent_message":
        text = str(item.get("text") or "").strip()
        return f"  {BOLD}{text}{NC}" if text else None
    if item_type == "reasoning":
        text = str(item.get("text") or item.get("summary") or "").strip()
        return f"  {MAGENTA}{ITALIC}... thinking ({len(text)} chars){NC}" if text else None
    if item_type == "command_execution":
        command = str(item.get("command") or "")
        if etype == "item.started":
            return f"  {YELLOW}>{NC} {_command_summary(command)}"
        if etype == "item.completed":
            status = item.get("status") or "completed"
            exit_code = item.get("exit_code")
            output = item.get("aggregated_output") or ""
            colour = RED if exit_code not in (None, 0) else DIM
            detail = f"exit {exit_code}" if exit_code is not None else str(status)
            preview = _truncate(str(output), MAX_OUTPUT_PREVIEW)
            suffix = f": {preview}" if preview else ""
            return f"  {colour}< {detail}{suffix}{NC}"
    if item_type in ("function_call", "custom_tool_call"):
        return _format_function_call_payload(item)
    if item_type in ("function_call_output", "custom_tool_call_output"):
        return _format_function_output_payload(item)
    return None


def _format_session_envelope(obj: dict) -> str | None:
    etype = obj.get("type", "")
    payload = obj.get("payload")
    payload = payload if isinstance(payload, dict) else {}
    if etype == "session_meta":
        return _format_session(payload)
    if etype == "turn_context":
        return _format_session(payload)
    if etype == "event_msg":
        return _format_event_msg(payload)
    if etype == "response_item":
        return _format_response_item(payload)
    if etype == "compacted":
        return f"  {DIM}[context compacted]{NC}"
    return None


def format_line(line: str) -> str | None:
    """Format one Codex stdout/session JSONL line."""
    stripped = line.strip()
    if not stripped:
        return None

    try:
        obj = json.loads(stripped)
    except json.JSONDecodeError:
        return line

    if not isinstance(obj, dict):
        return line

    event_type = obj.get("type", "")
    if event_type in {
        "session_meta",
        "turn_context",
        "event_msg",
        "response_item",
        "compacted",
    }:
        return _format_session_envelope(obj)

    formatted = _format_stdout_item(obj)
    if formatted is not None:
        return formatted

    return None
