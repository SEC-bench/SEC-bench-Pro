"""OpenCode ``run --format json`` output formatter.

OpenCode emits newline-delimited JSON events.  This formatter keeps the raw
agent output in ``agent_stdout.txt`` while rendering compact terminal updates
for text, reasoning, tool calls, steps, and errors.
"""

from __future__ import annotations

import json
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


def _event_payload(obj: dict) -> dict:
    part = obj.get("part")
    if isinstance(part, dict):
        return part
    return obj


def _format_text(obj: dict) -> str | None:
    part = _event_payload(obj)
    text = part.get("text", "").strip()
    if not text:
        return None
    return f"  {BOLD}{text}{NC}"


def _format_reasoning(obj: dict) -> str | None:
    part = _event_payload(obj)
    text = (
        part.get("text")
        or part.get("thinking")
        or part.get("content")
        or part.get("summary")
        or ""
    )
    if isinstance(text, list):
        text = "\n".join(str(item) for item in text)
    text = str(text).strip()
    if not text:
        return None
    return f"  {MAGENTA}{ITALIC}... thinking ({len(text)} chars){NC}"


def _format_tool(obj: dict) -> str | None:
    part = _event_payload(obj)
    name = (
        part.get("tool")
        or part.get("name")
        or part.get("toolName")
        or part.get("id")
        or "tool"
    )
    state = part.get("state")
    state = state if isinstance(state, dict) else {}
    status = state.get("status") or part.get("status")
    tool_input = state.get("input", part.get("input"))
    tool_output = state.get("output", part.get("output"))

    preview = _json_preview(tool_input, 90)
    suffix = f"({preview})" if preview else ""
    lines: list[str] = []
    if status in ("error", "failed"):
        err = _json_preview(tool_output or state.get("error") or part.get("error"))
        detail = f": {err}" if err else ""
        lines.append(f"  {RED}>{NC} {name}{suffix} {RED}{status}{detail}{NC}")
    elif status:
        lines.append(f"  {YELLOW}>{NC} {name}{suffix} {DIM}{status}{NC}")
    else:
        lines.append(f"  {YELLOW}>{NC} {name}{suffix}")

    if tool_output not in (None, ""):
        out_preview = _json_preview(tool_output, MAX_OUTPUT_PREVIEW)
        if out_preview:
            if status in ("error", "failed"):
                lines.append(f"  {RED}< ERROR: {out_preview}{NC}")
            else:
                lines.append(f"  {DIM}< {out_preview}{NC}")

    output_path = state.get("outputPath") or part.get("outputPath")
    if output_path:
        lines.append(f"  {DIM}< full output: {output_path}{NC}")

    return "\n".join(lines)


def _format_step_finish(obj: dict) -> str | None:
    part = _event_payload(obj)
    tokens = part.get("tokens") if isinstance(part.get("tokens"), dict) else {}
    cost = part.get("cost")
    reason = part.get("reason")
    info_parts: list[str] = []
    if reason:
        info_parts.append(str(reason))
    if tokens:
        input_tokens = tokens.get("input", 0)
        output_tokens = tokens.get("output", 0)
        info_parts.append(f"tokens={input_tokens}+{output_tokens}")
    if cost is not None:
        try:
            info_parts.append(f"cost=${float(cost):.4f}")
        except (TypeError, ValueError):
            info_parts.append(f"cost={cost}")
    if not info_parts:
        return None
    return f"  {DIM}[step] {' '.join(info_parts)}{NC}"


def _format_error(obj: dict) -> str | None:
    error = obj.get("error", "")
    if isinstance(error, dict):
        data = error.get("data")
        if isinstance(data, dict):
            msg = data.get("message")
        else:
            msg = None
        msg = msg or error.get("message") or error.get("name") or str(error)
    else:
        msg = str(error)
    return f"  {RED}ERROR: {_truncate(msg, 200)}{NC}"


def _format_session(obj: dict) -> str | None:
    session_id = obj.get("sessionID") or obj.get("session_id") or obj.get("id")
    model = obj.get("model") or obj.get("modelID")
    parts = [f"{BOLD}{CYAN}[session]{NC}"]
    if session_id:
        parts.append(f"id={session_id}")
    if model:
        parts.append(f"model={BOLD}{model}{NC}")
    return "  ".join(parts)


_HANDLERS = {
    "text": _format_text,
    "reasoning": _format_reasoning,
    "tool": _format_tool,
    "tool_use": _format_tool,
    "step-finish": _format_step_finish,
    "step_finish": _format_step_finish,
    "error": _format_error,
    "session": _format_session,
    "session.created": _format_session,
}


def format_line(line: str) -> str | None:
    """Format a single OpenCode JSON event line."""
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
    if event_type in ("step-start", "step_start"):
        return None
    part_type = ""
    part = obj.get("part")
    if isinstance(part, dict):
        part_type = part.get("type", "")
    handler = _HANDLERS.get(event_type) or _HANDLERS.get(part_type)
    if handler is not None:
        return handler(obj)

    if event_type == "done":
        return f"\n{BOLD}{CYAN}[done]{NC} {GREEN}success{NC}"
    return None
