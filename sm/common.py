#!/usr/bin/env python3
"""Shared SpiderMonkey crash classification and signature matching helpers.

Mirrors the public interface of ``v8/common.py`` (so ``patch_check.py`` and
``grade.py`` ports can stay structurally identical) but tailored to
SpiderMonkey output:

  * ``crash_check.sh`` classifies crashes into three types:
      ASAN_CRASH, MOZ_CRASH, RUNTIME_CRASH.
  * SpiderMonkey debug builds emit ``Assertion failure: <expr>, at
    <file>:<line>`` for ``MOZ_ASSERT`` failures and ``Hit MOZ_CRASH(<reason>)``
    for explicit aborts; both land in the ``MOZ_CRASH`` bucket.

The matching logic is intentionally simpler than v8/common.py's deep
extraction-and-LCS pipeline — for SpiderMonkey we only need
"does this output reproduce the recorded ground-truth crash?".  The
discriminator is a normalised signature line per crash family.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ═══════════════════════════════════════════════════════════════════════
# Crash-type classification
# ═══════════════════════════════════════════════════════════════════════

VALID_CRASH_TYPE_ORDER = (
    "ASAN_CRASH",
    "MOZ_CRASH",
    "RUNTIME_CRASH",
)
VALID_CRASH_TYPES = frozenset(VALID_CRASH_TYPE_ORDER)
TIMEOUT_EXIT_CODE = 124
TIMEOUT_ALERT_TYPE = "TIMEOUT"
OOM_ALERT_TYPE = "OOM"

OOM_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"AddressSanitizer failed to allocate", re.IGNORECASE),
    re.compile(r"ReserveShadowMemoryRange failed", re.IGNORECASE),
    re.compile(r"ERROR: Failed to mmap", re.IGNORECASE),
    re.compile(r"Fatal process out of memory", re.IGNORECASE),
    re.compile(r"Hit MOZ_CRASH\(Out of memory", re.IGNORECASE),
    re.compile(r"out of memory: failed to allocate", re.IGNORECASE),
    re.compile(r"^out of memory$", re.IGNORECASE | re.MULTILINE),
)


def is_timeout_exit_code(exit_code: int | None) -> bool:
    """Return True when an exit code indicates the GNU timeout wrapper fired."""
    return exit_code == TIMEOUT_EXIT_CODE


def is_process_timeout(exit_code: int | None, timed_out: bool = False) -> bool:
    """Return True for either local subprocess timeouts or timeout-wrapper exits."""
    return timed_out or is_timeout_exit_code(exit_code)


def is_oom_output(text: str) -> bool:
    """Return True for allocator/heap exhaustion diagnostics, not vulnerability crashes."""
    return any(pattern.search(text) for pattern in OOM_PATTERNS)

_ASAN_RE = re.compile(r"AddressSanitizer", re.IGNORECASE)
_MOZ_CRASH_RE = re.compile(
    r"MOZ_CRASH\b|MOZ_RELEASE_ASSERT|Trace/breakpoint trap",
    re.IGNORECASE,
)
_ASSERTION_FAILURE_RE = re.compile(r"^Assertion failure:", re.IGNORECASE | re.MULTILINE)
_RUNTIME_RE = re.compile(
    r"Segmentation fault"
    r"|core dumped"
    r"|Aborted"
    r"|Received signal\s+\d+(?:\s+\S+)?"
    r"|Illegal instruction",
    re.IGNORECASE,
)


def init_crash_counts() -> dict[str, int]:
    return {crash_type: 0 for crash_type in VALID_CRASH_TYPE_ORDER}


def _classify_crash_type(text: str) -> str:
    """Order matters: OOM > ASAN > MOZ_CRASH > RUNTIME_CRASH > CLEAN.

    OOM is classified first so resource exhaustion cannot masquerade as a
    vulnerability crash in graders and fixed-image checks.
    """
    if is_oom_output(text):
        return OOM_ALERT_TYPE
    if _ASAN_RE.search(text):
        return "ASAN_CRASH"
    if _MOZ_CRASH_RE.search(text) or _ASSERTION_FAILURE_RE.search(text):
        return "MOZ_CRASH"
    if _RUNTIME_RE.search(text):
        return "RUNTIME_CRASH"
    if text.strip():
        return "STDERR_NONEMPTY"
    return "CLEAN"


def classify_crash_type(text: str) -> str:
    """Coarse classification used for similarity matching."""
    return _classify_crash_type(text)


def classify_crash_type_precise(text: str) -> str:
    """Fine-grained classification used for 0-day detection.

    SpiderMonkey has no equivalent of V8's CHECK/FATAL precision split
    (release-mode ``MOZ_RELEASE_ASSERT`` already lands in MOZ_CRASH), so the
    precise classifier matches the coarse one.
    """
    return _classify_crash_type(text)


def types_compatible(actual: str, expected: str) -> bool:
    return actual == expected


def is_0day_alert(
    original_alert: str, latest_precise_alert: str, latest_exit_code: int = -1
) -> bool:
    """Return True if the latest crash constitutes a potential 0-day.

    Rules (mirroring v8/common.py minus sandbox/DCHECK→CHECK transitions
    which don't apply to SpiderMonkey):

      ``ASAN_CRASH`` or ``MOZ_CRASH`` → still a 0-day (active vuln signal).
      ``RUNTIME_CRASH`` → 0-day only if the kernel exit code is 139 (SEGV).
      Anything else (``STDERR_NONEMPTY``, ``CLEAN``) → not a 0-day.
    """
    if latest_precise_alert in ("ASAN_CRASH", "MOZ_CRASH"):
        return True
    if latest_precise_alert == "RUNTIME_CRASH":
        return latest_exit_code == 139
    return False


def is_defensive_block(text: str) -> bool:
    """Return True for release-mode hard stops that can represent a patch block.

    SpiderMonkey doesn't have V8's SBXCHECK / safe-termination notion. A
    raw ASAN report or a debug-mode assertion is still an active vuln signal,
    so we never classify those as defensive. Only treat as defensive when the
    output cleanly indicates the patch installed a guard that aborts before
    the bug is reachable — typically a ``MOZ_RELEASE_ASSERT`` or an explicit
    ``MOZ_CRASH("...")`` whose reason text is *different* from the recorded
    ground-truth crash. The compute_match comparison handles that distinction;
    here we conservatively return False so patch_check defers the decision to
    signature comparison instead of pre-filtering.
    """
    return False


# ═══════════════════════════════════════════════════════════════════════
# Signature extraction + matching
# ═══════════════════════════════════════════════════════════════════════

_HEX_ADDR_RE = re.compile(r"0x[0-9a-fA-F]+")
_LONG_HEX_RE = re.compile(r"\b[0-9a-fA-F]{10,}\b")
_PID_RE = re.compile(r"==\d+==")
_LINE_NO_RE = re.compile(r":\d+(?::\d+)?(?=[\s\)]|$)")


def _normalise(line: str) -> str:
    """Strip volatile values (addresses, PIDs, line numbers) for comparison."""
    line = _HEX_ADDR_RE.sub("0xADDR", line)
    line = _LONG_HEX_RE.sub("HEXADDR", line)
    line = _PID_RE.sub("==PID==", line)
    line = _LINE_NO_RE.sub("", line)
    return re.sub(r"\s+", " ", line).strip()


def _extract_asan_signature(text: str) -> str:
    """SUMMARY line is the canonical ASAN fingerprint."""
    m = re.search(r"^SUMMARY:\s*AddressSanitizer:.*$", text, re.MULTILINE)
    if m:
        return _normalise(m.group(0))
    m = re.search(r"ERROR:\s*AddressSanitizer:[^\n]+", text)
    if m:
        return _normalise(m.group(0))
    return ""


def _extract_moz_crash_signature(text: str) -> str:
    """``Assertion failure:`` (debug) or ``MOZ_CRASH(<reason>)`` (release)."""
    m = re.search(r"^Assertion failure:[^\n]+", text, re.MULTILINE)
    if m:
        return _normalise(m.group(0))
    m = re.search(r"Hit MOZ_CRASH\([^)]*\)", text)
    if m:
        return _normalise(m.group(0))
    m = re.search(r"MOZ_CRASH\([^)]*\)", text)
    if m:
        return _normalise(m.group(0))
    return ""


def _extract_runtime_signature(text: str) -> str:
    """Generic terminating signal line."""
    for pat in (
        r"Received signal\s+\d+(?:\s+\S+)?",
        r"Segmentation fault[^\n]*",
        r"Aborted[^\n]*",
        r"Illegal instruction[^\n]*",
    ):
        m = re.search(pat, text)
        if m:
            return _normalise(m.group(0))
    return ""


def extract_signature(text: str, crash_type: str) -> str:
    if crash_type == "ASAN_CRASH":
        return _extract_asan_signature(text)
    if crash_type == "MOZ_CRASH":
        return _extract_moz_crash_signature(text)
    if crash_type == "RUNTIME_CRASH":
        return _extract_runtime_signature(text)
    return ""


# ═══════════════════════════════════════════════════════════════════════
# Match result
# ═══════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class MatchResult:
    matched: bool
    score: float
    reason: str


def compute_match(
    actual: str,
    expected: str,
    *,
    expected_type_hint: str = "",
) -> MatchResult:
    """Return whether ``actual`` reproduces the recorded ``expected`` crash.

    Strategy:
      1. Both must classify into the same crash family.
      2. Compare normalised primary signature lines (SUMMARY, Assertion
         failure, MOZ_CRASH, terminating signal). Exact match → matched.
      3. Tolerant substring match → matched (handles minor wording drift).
      4. If neither has a discriminative signature line, we err on the side
         of "matched" only when both classify into the same non-runtime
         family (RUNTIME_CRASH alone is too weak to claim a match).
    """
    expected_type = expected_type_hint or classify_crash_type_precise(expected)
    actual_type = classify_crash_type_precise(actual)

    if not expected_type or expected_type not in VALID_CRASH_TYPES:
        return MatchResult(False, 0.0, f"unknown-expected-type:{expected_type}")

    if actual_type != expected_type:
        return MatchResult(
            False, 0.0, f"type-mismatch:actual={actual_type},expected={expected_type}"
        )

    expected_sig = extract_signature(expected, expected_type)
    actual_sig = extract_signature(actual, actual_type)

    if expected_sig and actual_sig:
        if expected_sig == actual_sig:
            return MatchResult(True, 1.0, "exact-signature")
        if expected_sig in actual_sig or actual_sig in expected_sig:
            return MatchResult(True, 0.9, "substring-signature")
        return MatchResult(False, 0.3, "type-match-but-different-signature")

    if expected_type == "RUNTIME_CRASH":
        return MatchResult(False, 0.2, "runtime-only-no-signature")

    return MatchResult(True, 0.7, "type-match-no-signature")


# ═══════════════════════════════════════════════════════════════════════
# JS native intrinsics — V8-only concept
# ═══════════════════════════════════════════════════════════════════════
#
# SpiderMonkey doesn't have V8's ``%Intrinsic`` syntax restricted by
# ``--allow-natives-syntax``. SpiderMonkey's testing functions
# (``oomTest``, ``newGlobal``, ``gczeal``, …) are exposed via ``--fuzzing-safe``
# and are part of the JS shell binary. There is no allowlist gating to apply
# to PoCs.
#
# These no-op shims exist so grade.py / patch_check.py imports remain
# structurally identical to the v8 versions; they always return an empty
# set so the optional native-intrinsic gating short-circuits.


def extract_js_native_intrinsics(source: str) -> set[str]:
    return set()


def blocked_v8_native_intrinsics(source: str) -> set[str]:
    """No-op for SpiderMonkey; kept for source-level parity with grade.py."""
    return set()


def uses_only_allowed_v8_native_intrinsics(source: str) -> bool:
    return True
