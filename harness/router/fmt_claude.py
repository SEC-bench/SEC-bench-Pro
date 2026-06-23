"""Claude Code ``stream-json`` output formatter.

Parses JSON-lines emitted by ``claude -p --output-format stream-json``
and renders concise, human-readable terminal output.

Colour scheme
~~~~~~~~~~~~~
* **Session init**  -- bold cyan
* **Thinking**      -- magenta / italic
* **Assistant text** -- bold white
* **Tool calls**    -- yellow ``>`` prefix
* **Tool results**  -- dim (errors in red)
* **Sub-agents**    -- green background tag
* **Final result**  -- bold cyan header, green/red status
"""

from __future__ import annotations

import json

from .ansi import (
    BG_GREEN,
    BG_MAGENTA,
    BOLD,
    CYAN,
    DIM,
    GREEN,
    ITALIC,
    MAGENTA,
    NC,
    RED,
    YELLOW,
)

MAX_RESULT_PREVIEW = 120


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _truncate(text: str, limit: int = MAX_RESULT_PREVIEW) -> str:
    text = text.replace("\n", " ").strip()
    return text if len(text) <= limit else text[:limit] + "..."


def _format_tool_input(name: str, inp: dict) -> str:
    """One-line summary of a tool call."""
    if name == "Read":
        path = inp.get("file_path", "?")
        parts = [path]
        if inp.get("offset"):
            parts.append(f"offset={inp['offset']}")
        if inp.get("limit"):
            parts.append(f"limit={inp['limit']}")
        return f"Read({', '.join(parts)})"
    if name == "Write":
        return f"Write({inp.get('file_path', '?')})"
    if name == "Edit":
        return f"Edit({inp.get('file_path', '?')})"
    if name == "Glob":
        return f"Glob({inp.get('pattern', '?')}, path={inp.get('path', '.')})"
    if name == "Grep":
        pattern = inp.get("pattern", "?")
        path = inp.get("path", ".")
        return f"Grep({pattern!r}, path={path})"
    if name == "Bash":
        cmd = inp.get("command", "?")
        return f"Bash({_truncate(cmd, 80)})"
    if name == "Task":
        desc = inp.get("description", "")
        return f"Task({desc})"
    if name == "TodoWrite":
        todos = inp.get("todos", [])
        return f"TodoWrite({len(todos)} items)"
    # Generic fallback
    keys = list(inp.keys())
    return f"{name}({', '.join(keys)})"


# ---------------------------------------------------------------------------
# Per-event handlers (each returns a formatted string or None)
# ---------------------------------------------------------------------------


def _format_system(obj: dict) -> str | None:
    subtype = obj.get("subtype", "")
    if subtype == "init":
        model = obj.get("model", "?")
        tools = obj.get("tools", [])
        skills = obj.get("skills", [])
        return (
            f"{BOLD}{CYAN}[session]{NC} "
            f"model={BOLD}{model}{NC}  "
            f"tools={len(tools)}  skills={len(skills)}"
        )
    if subtype == "task_started":
        desc = obj.get("description", "")
        task_type = obj.get("task_type", "")
        label = f" ({task_type})" if task_type else ""
        return (
            f"  {BG_MAGENTA}{BOLD} + {NC} "
            f"{MAGENTA}Sub-agent{NC}{label}: {desc}"
        )
    return None


def _format_assistant(obj: dict) -> str | None:
    msg = obj.get("message", {})
    is_subagent = bool(obj.get("parent_tool_use_id"))
    indent = "    " if is_subagent else "  "
    sa_tag = f"{BG_GREEN}{BOLD} sub {NC} " if is_subagent else ""

    lines: list[str] = []
    for block in msg.get("content", []):
        btype = block.get("type")
        if btype == "thinking":
            length = len(block.get("thinking", ""))
            lines.append(
                f"{indent}{sa_tag}{MAGENTA}{ITALIC}"
                f"... thinking ({length} chars){NC}"
            )
        elif btype == "text":
            text = block.get("text", "")
            lines.append(f"{indent}{sa_tag}{BOLD}{text}{NC}")
        elif btype == "tool_use":
            name = block.get("name", "?")
            inp = block.get("input", {})
            summary = _format_tool_input(name, inp)
            lines.append(f"{indent}{sa_tag}{YELLOW}>{NC} {summary}")
    return "\n".join(lines) if lines else None


def _format_user(obj: dict) -> str | None:
    is_subagent = bool(obj.get("parent_tool_use_id"))
    indent = "    " if is_subagent else "  "
    sa_tag = f"{BG_GREEN}{BOLD} sub {NC} " if is_subagent else ""

    lines: list[str] = []
    for block in obj.get("message", {}).get("content", []):
        btype = block.get("type")
        if btype == "tool_result":
            is_error = block.get("is_error", False)
            content = block.get("content", "")
            if isinstance(content, list):
                parts = [
                    c.get("text", "") for c in content if isinstance(c, dict)
                ]
                content = " ".join(parts)
            preview = _truncate(str(content))
            if is_error:
                lines.append(
                    f"{indent}{sa_tag}{RED}< ERROR: {preview}{NC}"
                )
            else:
                lines.append(f"{indent}{sa_tag}{DIM}< {preview}{NC}")
    return "\n".join(lines) if lines else None


def _format_result(obj: dict) -> str | None:
    is_error = obj.get("is_error", False)
    duration_ms = obj.get("duration_ms", 0)
    num_turns = obj.get("num_turns", 0)
    result_text = obj.get("result", "")

    mins = duration_ms / 60_000
    status = f"{RED}ERROR{NC}" if is_error else f"{GREEN}success{NC}"
    header = (
        f"\n{BOLD}{CYAN}[result]{NC} {status}  "
        f"turns={num_turns}  duration={mins:.1f}m"
    )
    if result_text:
        preview = result_text[:500]
        if len(result_text) > 500:
            preview += f"\n{DIM}... ({len(result_text)} chars total){NC}"
        return f"{header}\n{preview}"
    return header


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_HANDLERS = {
    "system": _format_system,
    "assistant": _format_assistant,
    "user": _format_user,
    "result": _format_result,
}


def format_line(line: str) -> str | None:
    """Format a single Claude Code ``stream-json`` line.

    Returns formatted text, the raw line (if not JSON), or ``None``
    to suppress blank/unrecognised lines.
    """
    stripped = line.strip()
    if not stripped:
        return None
    try:
        obj = json.loads(stripped)
    except json.JSONDecodeError:
        # Not JSON -- pass through as-is.
        return line

    handler = _HANDLERS.get(obj.get("type", ""))
    if handler is not None:
        return handler(obj)
    return None
