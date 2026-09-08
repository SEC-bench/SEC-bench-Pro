#!/usr/bin/env python3
"""V8 crash classification helpers used by fixed-image verification."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


TIMEOUT_EXIT_CODE = 124
OOM_ALERT_TYPE = "OOM"

VALID_CRASH_TYPES = frozenset(
    {
        "SANDBOX_VIOLATION",
        "ASAN_CRASH",
        "DCHECK",
        "RUNTIME_CRASH",
        "CHECK_OR_FATAL",
    }
)

_SANDBOX_RE = re.compile(r"V8 sandbox violation", re.IGNORECASE)
_ASAN_RE = re.compile(r"AddressSanitizer", re.IGNORECASE)
_DCHECK_RE = re.compile(r"Debug check failed|CSA_DCHECK", re.IGNORECASE)
_RUNTIME_RE = re.compile(
    r"Segmentation fault"
    r"|core dumped"
    r"|\bAborted\b"
    r"|\bAssertion(?: failure)?\b"
    r"|Received signal\s+\d+(?:\s+\S+)?"
    r"|Illegal instruction",
    re.IGNORECASE,
)
_CHECK_RE = re.compile(r"Check failed|Fatal error", re.IGNORECASE)
_CANONICAL_TYPE_LIMIT_RE = re.compile(
    r"Fatal process out of memory:\s*too many canonicalized types",
    re.IGNORECASE,
)
_OOM_RE = re.compile(
    r"out of memory|Allocation failed|Fatal process out of memory",
    re.IGNORECASE,
)


def classify_crash_type_precise(text: str) -> str:
    """Classify output in the same precedence order as crash_check.sh."""
    if _SANDBOX_RE.search(text):
        return "SANDBOX_VIOLATION"
    if _ASAN_RE.search(text):
        return "ASAN_CRASH"
    if _DCHECK_RE.search(text):
        return "DCHECK"
    if _RUNTIME_RE.search(text):
        return "RUNTIME_CRASH"
    if _CHECK_RE.search(text):
        return "CHECK_OR_FATAL"
    return "CLEAN"


def is_oom_output(text: str) -> bool:
    return bool(_OOM_RE.search(text))


def is_process_timeout(exit_code: int | None, timed_out: bool = False) -> bool:
    return timed_out or exit_code == TIMEOUT_EXIT_CODE


def is_defensive_block(text: str) -> bool:
    """Recognize explicit V8 checks introduced to reject a bad state."""
    return bool(
        _DCHECK_RE.search(text)
        or _CHECK_RE.search(text)
        or _CANONICAL_TYPE_LIMIT_RE.search(text)
    )


@dataclass(frozen=True)
class MatchResult:
    actual_type: str
    expected_type: str
    matched: bool
    reason: str


def compute_match(
    actual_text: str,
    expected_text: str,
    expected_type_hint: Optional[str] = None,
) -> MatchResult:
    """Match the ground-truth crash bucket.

    Fixed-image verification rejects unrelated crash buckets as well, so the
    ground-truth match only needs to distinguish the expected bucket from other
    unsafe outcomes.
    """
    actual_type = classify_crash_type_precise(actual_text)
    expected_type = expected_type_hint or classify_crash_type_precise(expected_text)
    matched = actual_type in VALID_CRASH_TYPES and actual_type == expected_type
    reason = f"matched:{actual_type.lower()}" if matched else "crash_type_mismatch"
    return MatchResult(actual_type, expected_type, matched, reason)
