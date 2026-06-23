#!/usr/bin/env python3
"""Shared SpiderMonkey crash classification and signature matching helpers.

Adapted from v8/common.py for SpiderMonkey-specific crash patterns.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

# ═══════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════

TIMEOUT_EXIT_CODE = 124
OOM_ALERT_TYPE = "OOM"

VALID_CRASH_TYPE_ORDER = (
    "ASAN_CRASH",
    "MOZ_CRASH",
    "RUNTIME_CRASH",
)
VALID_CRASH_TYPES = frozenset[str](VALID_CRASH_TYPE_ORDER)

# ═══════════════════════════════════════════════════════════════════════
# Crash-type classification
# ═══════════════════════════════════════════════════════════════════════

_ASAN_RE = re.compile(r"AddressSanitizer")
_MOZ_CRASH_RE = re.compile(r"MOZ_CRASH|Trace/breakpoint trap", re.IGNORECASE)
_MOZ_ASSERT_RE = re.compile(r"Assertion failure:", re.IGNORECASE)
_RUNTIME_RE = re.compile(
    r"Segmentation fault"
    r"|core dumped"
    r"|Aborted"
    r"|Received signal\s+\d+(?:\s+\S+)?"
    r"|Illegal instruction",
    re.IGNORECASE,
)

_OOM_RE = re.compile(
    r"out of memory"
    r"|js_ReportOutOfMemory"
    r"|alloc::oom::oom_impl"
    r"|moz_xmalloc: out of memory"
    r"|NS_ABORT_OOM",
    re.IGNORECASE,
)


def classify_crash_type(text: str) -> str:
    """Coarse classification matching crash_check.sh logic."""
    if _ASAN_RE.search(text):
        return "ASAN_CRASH"
    if _RUNTIME_RE.search(text):
        return "RUNTIME_CRASH"
    if _MOZ_CRASH_RE.search(text) or _MOZ_ASSERT_RE.search(text):
        return "MOZ_CRASH"
    if text.strip():
        return "STDERR_NONEMPTY"
    return "CLEAN"


def classify_crash_type_precise(text: str) -> str:
    """Fine-grained classification for patch verification."""
    return classify_crash_type(text)


# ═══════════════════════════════════════════════════════════════════════
# OOM / timeout detection
# ═══════════════════════════════════════════════════════════════════════


def is_oom_output(text: str) -> bool:
    """Return True if the output indicates an out-of-memory condition."""
    return bool(_OOM_RE.search(text))


def is_process_timeout(exit_code: int | None, timed_out: bool = False) -> bool:
    return timed_out or exit_code == TIMEOUT_EXIT_CODE


# ═══════════════════════════════════════════════════════════════════════
# Defensive block detection
# ═══════════════════════════════════════════════════════════════════════

_CHECK_FAILED_RE = re.compile(r"\bCheck failed\b", re.IGNORECASE)
_FATAL_RE = re.compile(r"Fatal error|Fatal process out of memory", re.IGNORECASE)


def is_defensive_block(text: str) -> bool:
    """Return True for release-mode hard stops that represent a patch block.

    MOZ_RELEASE_ASSERT / CHECK failures in release builds are acceptable
    for patched-image validation when the original crash is no longer reproduced.
    """
    crash_type = classify_crash_type_precise(text)
    if crash_type in VALID_CRASH_TYPES:
        return False
    if _CHECK_FAILED_RE.search(text) or _FATAL_RE.search(text):
        return True
    return False


# ═══════════════════════════════════════════════════════════════════════
# Text normalisation
# ═══════════════════════════════════════════════════════════════════════

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
_HEX_ADDR_RE = re.compile(r"0x[0-9a-fA-F]+")
_PID_RE = re.compile(r"==\d+==")
_THREAD_RE = re.compile(r"\bT\d+\b")


def _normalise_addresses(text: str) -> str:
    text = _ANSI_RE.sub("", text)
    text = _HEX_ADDR_RE.sub("0xADDR", text)
    text = _PID_RE.sub("==PID==", text)
    text = _THREAD_RE.sub("TID", text)
    text = re.sub(r"[ \t]+", " ", text)
    return "\n".join(ln.strip() for ln in text.splitlines())


def _normalise_line(line: str) -> str:
    return _normalise_addresses(line).strip()


def _dedupe_lines(lines: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for line in lines:
        if not line or line in seen:
            continue
        seen.add(line)
        out.append(line)
    return out


# ═══════════════════════════════════════════════════════════════════════
# Core text extraction
# ═══════════════════════════════════════════════════════════════════════

_ASAN_ERROR_LINE_RE = re.compile(r"ERROR:\s*AddressSanitizer:", re.IGNORECASE)
_ASAN_SUMMARY_LINE_RE = re.compile(r"SUMMARY:\s*AddressSanitizer:", re.IGNORECASE)
_ASAN_ACCESS_LINE_RE = re.compile(
    r"^(?P<kind>READ|WRITE) of size (?P<size>\d+) at .* thread T(?:\d+|ID)$",
    re.IGNORECASE,
)
_ASAN_SIGNAL_LINE_RE = re.compile(
    r"^(?:==\d+==|==PID==)The signal is caused by a "
    r"(?P<kind>READ|WRITE) memory access\.$",
    re.IGNORECASE,
)
_ASAN_FRAME0_RE = re.compile(r"^\s*#0\s+")
_ASAN_STACK_LOCATION_RE = re.compile(r"^\s*#\d+\s+\S+\s+in\s+(.+)$")
_ASAN_SUMMARY_RE = re.compile(
    r"SUMMARY:\s*AddressSanitizer:\s*(?P<type>\S+)(?P<rest>.*)$"
)
_SOURCE_FILE_RE = re.compile(
    r"(?P<file>(?:[A-Za-z0-9_./+-]+/)*[A-Za-z0-9_.+-]+"
    r"\.(?:cc|h|hh|hpp|c|cpp|inc|tq|S|s))(?::\d+(?::\d+)?)?"
)


def _extract_asan_core_lines(text: str) -> list[str]:
    parts: list[str] = []
    for raw in text.splitlines():
        line = _normalise_line(raw)
        if not line:
            continue
        if line == "AddressSanitizer:DEADLYSIGNAL":
            parts.append(line)
        elif _ASAN_ERROR_LINE_RE.search(line):
            parts.append(line)
        elif _ASAN_SIGNAL_LINE_RE.match(line):
            parts.append(line)
        elif _ASAN_ACCESS_LINE_RE.match(line):
            parts.append(line)
        elif _ASAN_FRAME0_RE.match(line):
            parts.append(line)
            break

    for raw in text.splitlines():
        line = _normalise_line(raw)
        if _ASAN_SUMMARY_LINE_RE.search(line):
            parts.append(line)
            break

    return _dedupe_lines(parts)


def _extract_runtime_signal_lines(text: str) -> list[str]:
    parts: list[str] = []
    for raw in text.splitlines():
        line = _normalise_line(raw)
        if not line:
            continue
        if re.search(r"Segmentation fault", line, re.IGNORECASE):
            parts.append("Segmentation fault")
        elif re.search(r"Aborted", line, re.IGNORECASE):
            parts.append("Aborted")
        elif re.search(r"Trace/breakpoint trap", line, re.IGNORECASE):
            parts.append("Trace/breakpoint trap")
        elif re.search(r"Illegal instruction", line, re.IGNORECASE):
            parts.append("Illegal instruction")
    return _dedupe_lines(parts)


def extract_core_text(text: str, crash_type: str) -> str:
    if crash_type == "ASAN_CRASH":
        lines = _extract_asan_core_lines(text)
    elif crash_type == "RUNTIME_CRASH":
        lines = _extract_runtime_signal_lines(text)
    elif crash_type == "MOZ_CRASH":
        lines = []
        for raw in text.splitlines():
            line = _normalise_line(raw)
            if not line:
                continue
            if _MOZ_CRASH_RE.search(line) or _MOZ_ASSERT_RE.search(line):
                lines.append(line)
        lines = _dedupe_lines(lines)
    else:
        lines = [_normalise_line(l) for l in text.splitlines() if _normalise_line(l)]
        lines = _dedupe_lines(lines)
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════
# ASAN report parsing
# ═══════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class AsanReport:
    vuln_type: str
    access_kind: str
    access_size: str
    locations: tuple[str, ...]


def _compact_function_symbol(symbol: str) -> str:
    symbol = re.sub(r"\s+", " ", symbol).strip()
    if not symbol:
        return ""
    if symbol.endswith(")") and "(" in symbol:
        depth = 0
        for idx in range(len(symbol) - 1, -1, -1):
            char = symbol[idx]
            if char == ")":
                depth += 1
            elif char == "(":
                depth -= 1
                if depth == 0:
                    inner = symbol[idx + 1 : -1].strip()
                    if inner != "anonymous namespace":
                        symbol = symbol[:idx].strip()
                    break
    return symbol


def _normalise_asan_location(raw_location: str) -> str:
    loc = _normalise_line(raw_location)
    loc = re.sub(r"\s+\(BuildId:.*?\)$", "", loc)
    loc = re.sub(r"\s+\([^)]*\+0xADDR\)$", "", loc)
    if not loc or "<unknown module>" in loc or "[stack]" in loc:
        return ""

    matches = list(_SOURCE_FILE_RE.finditer(loc))
    if not matches:
        return ""
    match = matches[-1]
    source = re.sub(r":\d+(?::\d+)?$", "", match.group("file"))
    if "/lib/" in source or "glibc" in source or source.endswith("libc-start.c"):
        return ""

    symbol = _compact_function_symbol(loc[: match.start()])
    if not symbol:
        return ""
    return f"{symbol} {source}"


def _extract_asan_report(text: str) -> AsanReport:
    vuln_type = ""
    access_kind = ""
    access_size = ""
    locations: list[str] = []

    for raw in text.splitlines():
        line = _normalise_line(raw)
        if not line:
            continue

        if not vuln_type:
            error_match = re.search(r"ERROR:\s*AddressSanitizer:\s*(\S+)", line)
            if error_match:
                vuln_type = error_match.group(1)

        access_match = _ASAN_ACCESS_LINE_RE.match(line)
        if access_match and not access_kind:
            access_kind = access_match.group("kind").upper()
            access_size = access_match.group("size")
            continue

        signal_match = _ASAN_SIGNAL_LINE_RE.match(line)
        if signal_match and not access_kind:
            access_kind = signal_match.group("kind").upper()
            continue

        frame_match = _ASAN_STACK_LOCATION_RE.match(line)
        if frame_match:
            loc = _normalise_asan_location(frame_match.group(1))
            if loc and loc not in locations:
                locations.append(loc)
            continue

        summary_match = _ASAN_SUMMARY_RE.search(line)
        if summary_match:
            if not vuln_type:
                vuln_type = summary_match.group("type")

    return AsanReport(
        vuln_type=vuln_type,
        access_kind=access_kind,
        access_size=access_size,
        locations=tuple(locations),
    )


# ═══════════════════════════════════════════════════════════════════════
# Similarity / match decision
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class MatchResult:
    actual_type: str
    expected_type: str
    type_compatible: bool
    sig_sim: float
    text_sim: float
    score: float
    matched: bool
    reason: str


def _lcs_len(left: tuple[str, ...], right: tuple[str, ...]) -> int:
    if not left or not right:
        return 0
    prev = [0] * (len(right) + 1)
    for lhs in left:
        cur = [0]
        for idx, rhs in enumerate(right, start=1):
            if lhs == rhs:
                cur.append(prev[idx - 1] + 1)
            else:
                cur.append(max(prev[idx], cur[-1]))
        prev = cur
    return prev[-1]


def _runtime_signal_tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    for m in re.finditer(
        r"^Received signal[ \t]+(\d+)(?:[ \t]+(\S+))?(?:[ \t]+\S+)?$",
        text,
        re.MULTILINE,
    ):
        tokens.add(f"signal_num:{m.group(1)}")
        detail = m.group(2)
        if detail and detail != "<unknown>":
            tokens.add(f"signal_detail:{detail}")

    for pat, label in (
        (r"Segmentation fault", "segmentation_fault"),
        (r"Aborted", "aborted"),
        (r"Trace/breakpoint trap", "trace_breakpoint_trap"),
        (r"Illegal instruction", "illegal_instruction"),
    ):
        if re.search(pat, text, re.IGNORECASE):
            tokens.add(label)
    return tokens


def _compatible_runtime_signal(actual_text: str, expected_text: str) -> bool:
    actual = _runtime_signal_tokens(actual_text)
    expected = _runtime_signal_tokens(expected_text)
    if not actual or not expected:
        return False
    return bool(actual & expected)


def _match_asan(actual_text: str, expected_text: str) -> tuple[bool, float, str]:
    actual = _extract_asan_report(actual_text)
    expected = _extract_asan_report(expected_text)

    if not actual.vuln_type or not expected.vuln_type:
        return False, 0.0, "asan_vuln_type_missing"
    if actual.vuln_type != expected.vuln_type:
        return (
            False,
            0.0,
            f"asan_vuln_mismatch:{actual.vuln_type}!={expected.vuln_type}",
        )
    if actual.access_kind and expected.access_kind:
        if actual.access_kind != expected.access_kind:
            return (
                False,
                0.0,
                f"asan_access_mismatch:{actual.access_kind}!={expected.access_kind}",
            )
    if not actual.locations or not expected.locations:
        return True, 0.8, "matched:asan_type_no_locations"

    matched_locations = _lcs_len(actual.locations, expected.locations)
    denominator = max(len(actual.locations), len(expected.locations))
    location_ratio = matched_locations / denominator if denominator else 0.0
    matched = location_ratio > 0.3
    reason = (
        "matched:asan_locations"
        if matched
        else f"asan_location_overlap:{matched_locations}/{denominator}"
    )
    return matched, location_ratio, reason


def compute_match(
    actual_text: str,
    expected_text: str,
    expected_type_hint: Optional[str] = None,
) -> MatchResult:
    """Determine whether actual_text reproduces the crash in expected_text."""
    actual_text = actual_text.strip()
    expected_text = expected_text.strip()

    if not actual_text:
        return MatchResult(
            "CLEAN",
            classify_crash_type(expected_text),
            False, 0.0, 0.0, 0.0, False, "actual_empty",
        )
    if not expected_text:
        return MatchResult(
            classify_crash_type(actual_text),
            "CLEAN",
            False, 0.0, 0.0, 0.0, False, "expected_empty",
        )

    actual_type = classify_crash_type(actual_text)
    expected_type = expected_type_hint or classify_crash_type(expected_text)

    if actual_type not in VALID_CRASH_TYPES:
        return MatchResult(
            actual_type, expected_type,
            False, 0.0, 0.0, 0.0, False, f"invalid_actual_type:{actual_type}",
        )
    if expected_type not in VALID_CRASH_TYPES:
        return MatchResult(
            actual_type, expected_type,
            False, 0.0, 0.0, 0.0, False, f"invalid_expected_type:{expected_type}",
        )

    if actual_type != expected_type:
        return MatchResult(
            actual_type, expected_type,
            False, 0.0, 0.0, 0.0, False, f"type_mismatch:{actual_type}!={expected_type}",
        )

    if actual_type == "ASAN_CRASH":
        matched, score, reason = _match_asan(actual_text, expected_text)
        return MatchResult(
            actual_type, expected_type, True, score, score, score, matched, reason,
        )

    if actual_type == "RUNTIME_CRASH":
        if _compatible_runtime_signal(actual_text, expected_text):
            return MatchResult(
                actual_type, expected_type, True, 1.0, 1.0, 1.0, True,
                "matched:runtime_signal",
            )

    if actual_type == "MOZ_CRASH":
        actual_core = extract_core_text(actual_text, "MOZ_CRASH")
        expected_core = extract_core_text(expected_text, "MOZ_CRASH")
        if actual_core and actual_core == expected_core:
            return MatchResult(
                actual_type, expected_type, True, 1.0, 1.0, 1.0, True,
                "matched:exact_moz_crash",
            )
        if actual_core and expected_core:
            return MatchResult(
                actual_type, expected_type, True, 0.5, 0.5, 0.5, True,
                "matched:moz_crash_type",
            )

    return MatchResult(
        actual_type, expected_type, True, 0.0, 0.0, 0.0, False, "no_match",
    )
