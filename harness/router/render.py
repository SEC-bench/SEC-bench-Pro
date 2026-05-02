"""Unified rendering entry-point for agent output.

Dispatches to per-agent formatters based on the agent type string.
Each formatter module exposes a ``format_line(line) -> str | None``
function that transforms a single stdout line into terminal-ready text.
"""

from __future__ import annotations

from typing import Any

from . import fmt_claude, fmt_codex, fmt_opencode

_FORMATTERS: dict[str, Any] = {
    "claude": fmt_claude,
    "codex": fmt_codex,
    "opencode": fmt_opencode,
}


def format_line(agent_type: str, line: str) -> str | None:
    """Format a single output line using the agent-specific formatter.

    Parameters
    ----------
    agent_type:
        One of ``"claude"``, ``"codex"``, or ``"opencode"``.
    line:
        Raw stdout line (newline already stripped).

    Returns
    -------
    str | None
        Formatted text to print, or ``None`` to suppress the line.
    """
    fmt = _FORMATTERS.get(agent_type)
    if fmt is None:
        return line
    return fmt.format_line(line)
