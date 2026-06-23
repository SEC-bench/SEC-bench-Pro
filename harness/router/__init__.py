"""Agent output rendering for evaluation harnesses.

Re-exports the unified ``format_line`` dispatcher so callers can simply
write ``from router import format_line``.
"""

from .render import format_line

__all__ = ["format_line"]
