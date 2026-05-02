"""Shared ANSI escape-code constants for agent output rendering."""

from __future__ import annotations

BOLD = "\033[1m"
DIM = "\033[2m"
ITALIC = "\033[3m"

RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[97m"

BG_GREEN = "\033[42m"
BG_BLUE = "\033[44m"
BG_RED = "\033[41m"
BG_CYAN = "\033[46m"
BG_MAGENTA = "\033[45m"

NC = "\033[0m"

# Short display labels for agent types.
AGENT_SHORT: dict[str, str] = {
    "claude": "claude",
    "codex": "codex",
    "opencode": "opencode",
}


def short_agent(name: str) -> str:
    """Return the compact display label for an agent name."""
    return AGENT_SHORT.get(name, name)
