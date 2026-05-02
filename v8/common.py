#!/usr/bin/env python3
"""Shared V8 crash classification and signature matching helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

# ═══════════════════════════════════════════════════════════════════════
# Crash-type classification
# ═══════════════════════════════════════════════════════════════════════

VALID_CRASH_TYPE_ORDER = (
    "SANDBOX_VIOLATION",
    "ASAN_CRASH",
    "DCHECK",
    "RUNTIME_CRASH",
)
VALID_CRASH_TYPES = frozenset[str](VALID_CRASH_TYPE_ORDER)

# Native-syntax intrinsics observed in verified V8 instance PoCs that require
# `--allow-natives-syntax`. Keep this list conservative: these intrinsics are
# used to steer optimization/tiering, inspect state, or provide a verified
# runtime-function equivalent in the current dataset. Direct internal-only
# vulnerability primitives should remain outside this whitelist.
V8_NATIVE_SECURITY_TEST_INTRINSICS = frozenset(
    {
        # Optimization / tiering control.
        "CompileBaseline",
        "DeoptimizeFunction",
        "GetOptimizationStatus",
        "OptimizeFunctionOnNextCall",
        "OptimizeMaglevOnNextCall",
        "PrepareFunctionForOptimization",
        "WasmTierUpFunction",
        # Diagnostics used by verified PoCs.
        "DebugPrint",
        # Verified PoC helpers with JS-equivalent or runtime-wrapper rationale.
        "GetHoleNaNLower",
        "GetHoleNaNUpper",
        "InternalizeString",
        "SetAllocationTimeout",
        "TypedArraySet",
    }
)

V8_NATIVE_SECURITY_TEST_INTRINSIC_CATEGORIES = {
    "CompileBaseline": "optimization_control",
    "DeoptimizeFunction": "optimization_control",
    "GetOptimizationStatus": "optimization_control",
    "OptimizeFunctionOnNextCall": "optimization_control",
    "OptimizeMaglevOnNextCall": "optimization_control",
    "PrepareFunctionForOptimization": "optimization_control",
    "WasmTierUpFunction": "optimization_control",
    "DebugPrint": "diagnostic",
    "GetHoleNaNLower": "value_construction",
    "GetHoleNaNUpper": "value_construction",
    "InternalizeString": "verified_js_equivalent",
    "SetAllocationTimeout": "test_scheduling",
    "TypedArraySet": "verified_runtime_wrapper",
}

_NATIVE_INTRINSIC_RE = re.compile(r"%([A-Za-z_][A-Za-z0-9_]*)")
_IDENT_START_RE = re.compile(r"[A-Za-z_$]")
_IDENT_PART_RE = re.compile(r"[A-Za-z0-9_$]")
_REGEX_PREFIX_TOKENS = {
    None,
    "(",
    "{",
    "[",
    ",",
    ";",
    ":",
    "?",
    "=",
    "==",
    "===",
    "!=",
    "!==",
    "+",
    "-",
    "*",
    "/",
    "%",
    "**",
    "!",
    "~",
    "&",
    "|",
    "^",
    "&&",
    "||",
    "??",
    "=>",
    "return",
    "throw",
    "case",
    "delete",
    "void",
    "typeof",
    "yield",
    "await",
    "in",
    "of",
    "instanceof",
    "new",
    "else",
    "do",
}
_DYNAMIC_CODE_PATTERNS = (
    ("eval", re.compile(r"(?<![\w$.\]])\beval\s*(?:\?\.\s*)?\(")),
    (
        "function_constructor",
        re.compile(r"(?<![\w$.])\b(?:new\s+)?Function\s*(?:\?\.\s*)?\("),
    ),
    (
        "async_function_constructor",
        re.compile(r"(?<![\w$.])\b(?:new\s+)?AsyncFunction\s*(?:\?\.\s*)?\("),
    ),
    (
        "generator_function_constructor",
        re.compile(
            r"(?<![\w$.])\b(?:new\s+)?GeneratorFunction\s*(?:\?\.\s*)?\("
        ),
    ),
    (
        "async_generator_function_constructor",
        re.compile(
            r"(?<![\w$.])\b(?:new\s+)?AsyncGeneratorFunction\s*(?:\?\.\s*)?\("
        ),
    ),
)
_DYNAMIC_CODE_WITH_STRING_PATTERNS = (
    (
        "indirect_eval",
        re.compile(r"(?:\.\s*eval|\[\s*['\"]eval['\"]\s*\])\s*(?:\?\.\s*)?\("),
    ),
    (
        "string_timer",
        re.compile(
            r"(?<![\w$.])\bset(?:Timeout|Interval)\s*(?:\?\.\s*)?\(\s*['\"`]"
        ),
    ),
    ("string_dynamic_import", re.compile(r"(?<![\w$.])\bimport\s*\(\s*['\"`]")),
)


def _is_identifier_start(ch: str) -> bool:
    return bool(_IDENT_START_RE.fullmatch(ch))


def _is_identifier_part(ch: str) -> bool:
    return bool(_IDENT_PART_RE.fullmatch(ch))


def _mask_js_fragment(fragment: str) -> str:
    return "".join("\n" if ch in "\r\n" else " " for ch in fragment)


def _can_start_regex(prev_token: str | None) -> bool:
    return prev_token in _REGEX_PREFIX_TOKENS


def _strip_js_comments_and_optionally_literals(
    source: str,
    *,
    keep_strings: bool,
    keep_templates: bool,
    keep_regex: bool,
) -> str:
    length = len(source)

    def masked_char(ch: str) -> str:
        return "\n" if ch in "\r\n" else " "

    def scan_js(i: int, *, stop_at_template_expr_end: bool = False) -> tuple[str, int]:
        out: list[str] = []
        prev_token: str | None = None
        brace_depth = 0

        while i < length:
            ch = source[i]
            nxt = source[i + 1] if i + 1 < length else ""

            if stop_at_template_expr_end and ch == "}" and brace_depth == 0:
                return "".join(out), i

            if ch.isspace():
                out.append(ch)
                i += 1
                continue

            if _is_identifier_start(ch):
                start = i
                i += 1
                while i < length and _is_identifier_part(source[i]):
                    i += 1
                token = source[start:i]
                out.append(token)
                prev_token = token
                continue

            if ch.isdigit():
                start = i
                i += 1
                while i < length and (
                    source[i].isalnum() or source[i] in "._"
                ):
                    i += 1
                fragment = source[start:i]
                out.append(fragment)
                prev_token = "literal"
                continue

            if ch in ("'", '"'):
                quote = ch
                start = i
                i += 1
                escaped = False
                while i < length:
                    cur = source[i]
                    i += 1
                    if escaped:
                        escaped = False
                    elif cur == "\\":
                        escaped = True
                    elif cur == quote:
                        break
                fragment = source[start:i]
                out.append(fragment if keep_strings else _mask_js_fragment(fragment))
                prev_token = "literal"
                continue

            if ch == "`":
                fragment, i = scan_template_literal(i)
                out.append(fragment)
                prev_token = "literal"
                continue

            if ch == "/" and nxt == "/":
                start = i
                i += 2
                while i < length and source[i] not in "\r\n":
                    i += 1
                out.append(_mask_js_fragment(source[start:i]))
                continue

            if ch == "/" and nxt == "*":
                start = i
                i += 2
                while i + 1 < length and not (
                    source[i] == "*" and source[i + 1] == "/"
                ):
                    i += 1
                i = min(i + 2, length)
                out.append(_mask_js_fragment(source[start:i]))
                continue

            if ch == "/" and (_can_start_regex(prev_token) or nxt == "["):
                start = i
                i += 1
                escaped = False
                in_class = False
                while i < length:
                    cur = source[i]
                    i += 1
                    if escaped:
                        escaped = False
                    elif cur == "\\":
                        escaped = True
                    elif in_class:
                        if cur == "]":
                            in_class = False
                    elif cur == "[":
                        in_class = True
                    elif cur == "/":
                        while i < length and _is_identifier_part(source[i]):
                            i += 1
                        break
                    elif cur in "\r\n":
                        break
                fragment = source[start:i]
                out.append(fragment if keep_regex else _mask_js_fragment(fragment))
                prev_token = "literal"
                continue

            three = source[i : i + 3]
            two = source[i : i + 2]
            if three in {
                "===",
                "!==",
                "**=",
                "&&=",
                "||=",
                "??=",
                "<<=",
                ">>=",
                ">>>",
            }:
                out.append(three)
                prev_token = three
                i += 3
                continue
            if two in {
                "=>",
                "++",
                "--",
                "==",
                "!=",
                "<=",
                ">=",
                "&&",
                "||",
                "??",
                "**",
                "+=",
                "-=",
                "*=",
                "/=",
                "%=",
                "&=",
                "|=",
                "^=",
                "<<",
                ">>",
            }:
                out.append(two)
                prev_token = two
                i += 2
                continue

            if ch == "{":
                brace_depth += 1
            elif ch == "}" and brace_depth > 0:
                brace_depth -= 1
            out.append(ch)
            prev_token = ch
            i += 1

        return "".join(out), i

    def scan_template_literal(i: int) -> tuple[str, int]:
        out: list[str] = []
        out.append("`" if keep_templates else " ")
        i += 1
        escaped = False

        while i < length:
            cur = source[i]
            nxt = source[i + 1] if i + 1 < length else ""

            if escaped:
                out.append(cur if keep_templates else masked_char(cur))
                escaped = False
                i += 1
                continue

            if cur == "\\":
                out.append(cur if keep_templates else " ")
                escaped = True
                i += 1
                continue

            if cur == "`":
                out.append("`" if keep_templates else " ")
                i += 1
                return "".join(out), i

            # Template quasis are literal text; ${...} is executable JavaScript.
            if cur == "$" and nxt == "{":
                out.append("${" if keep_templates else "  ")
                expr, end = scan_js(i + 2, stop_at_template_expr_end=True)
                out.append(expr)
                if end < length and source[end] == "}":
                    out.append("}" if keep_templates else " ")
                    i = end + 1
                else:
                    i = end
                escaped = False
                continue

            out.append(cur if keep_templates else masked_char(cur))
            i += 1

        return "".join(out), i

    stripped, _ = scan_js(0)
    return stripped


def strip_js_comments_for_intrinsic_scan(source: str) -> str:
    """Remove JS comments while preserving strings such as eval("%Foo(...)").

    This intentionally keeps string/template literal contents because native
    intrinsics can be invoked through generated code. A regex-only comment
    stripper can miss cases such as eval('const url = "http://x"; %Bad()'),
    where `//` appears inside a string before the intrinsic.
    """
    return _strip_js_comments_and_optionally_literals(
        source,
        keep_strings=True,
        keep_templates=True,
        keep_regex=False,
    )


def strip_js_comments_and_literals_for_code_scan(source: str) -> str:
    """Remove comments and mask string/template/regex literals for code matching."""
    return _strip_js_comments_and_optionally_literals(
        source,
        keep_strings=False,
        keep_templates=False,
        keep_regex=False,
    )


def extract_v8_native_intrinsics(source: str) -> set[str]:
    """Return `%Intrinsic` names referenced by a PoC, excluding comments."""
    return set(_NATIVE_INTRINSIC_RE.findall(strip_js_comments_for_intrinsic_scan(source)))


def non_whitelisted_v8_native_intrinsics(source: str) -> set[str]:
    """Return native intrinsics that are not in the verified security-test whitelist."""
    return extract_v8_native_intrinsics(source) - V8_NATIVE_SECURITY_TEST_INTRINSICS


def uses_only_whitelisted_v8_native_intrinsics(source: str) -> bool:
    """Return True when every `%Intrinsic` use is in the verified whitelist."""
    return not non_whitelisted_v8_native_intrinsics(source)


def dynamic_code_generation_uses(source: str) -> set[str]:
    """Return dynamic-code APIs used by source, excluding comments/literals.

    Native-syntax PoCs that use generated JavaScript are rejected by the grader:
    a static whitelist cannot soundly prove which `%Intrinsic` calls will be
    assembled at runtime. Template literal quasis are treated as literals, but
    `${...}` expressions are scanned as executable JavaScript.
    """
    code = strip_js_comments_and_literals_for_code_scan(source)
    commentless = strip_js_comments_for_intrinsic_scan(source)
    uses: set[str] = set()
    for name, pattern in _DYNAMIC_CODE_PATTERNS:
        if pattern.search(code):
            uses.add(name)
    for name, pattern in _DYNAMIC_CODE_WITH_STRING_PATTERNS:
        if pattern.search(commentless):
            uses.add(name)
    return uses

_SANDBOX_RE = re.compile(r"##\s*V8 sandbox violation detected!", re.IGNORECASE)
_ASAN_RE = re.compile(r"AddressSanitizer")
_DCHECK_RE = re.compile(r"Debug check failed", re.IGNORECASE)
_CSA_DCHECK_RE = re.compile(r"CSA_DCHECK")
_CHECK_FAILED_RE = re.compile(r"\bCheck failed\b", re.IGNORECASE)
_FATAL_RE = re.compile(r"Fatal error|Fatal process out of memory", re.IGNORECASE)
_SAFE_TERMINATION_RE = re.compile(r"Safely terminating process", re.IGNORECASE)
_RUNTIME_RE = re.compile(
    r"Received signal\s+\d+(?:\s+\S+)?"
    r"|Segmentation fault"
    r"|core dumped"
    r"|Aborted"
    r"|Assertion"
    r"|Trace/breakpoint trap"
    r"|Illegal instruction",
    re.IGNORECASE,
)


def init_crash_counts() -> dict[str, int]:
    return {crash_type: 0 for crash_type in VALID_CRASH_TYPE_ORDER}


def _classify_crash_type(text: str, *, precise: bool) -> str:
    """Classify stderr into benchmark-level or precise crash categories."""
    if _SANDBOX_RE.search(text):
        return "SANDBOX_VIOLATION"
    if _ASAN_RE.search(text):
        return "ASAN_CRASH"
    if _DCHECK_RE.search(text) or _CSA_DCHECK_RE.search(text):
        return "DCHECK"

    has_release_check = (
        (_CHECK_FAILED_RE.search(text) or _FATAL_RE.search(text))
        and not _SAFE_TERMINATION_RE.search(text)
    )
    if precise:
        if _CHECK_FAILED_RE.search(text):
            return "CHECK"
        if _FATAL_RE.search(text) and not _SAFE_TERMINATION_RE.search(text):
            return "FATAL"
    elif has_release_check:
        # The benchmark only exposes four coarse types, so CHECK/FATAL
        # transcripts are treated as runtime crashes during similarity.
        return "RUNTIME_CRASH"

    if _RUNTIME_RE.search(text):
        return "RUNTIME_CRASH"
    if text.strip():
        return "STDERR_NONEMPTY"
    return "CLEAN"


def classify_crash_type(text: str) -> str:
    """Coarse classification used for similarity matching."""
    return _classify_crash_type(text, precise=False)


def classify_crash_type_precise(text: str) -> str:
    """Fine-grained classification for 0-day detection."""
    return _classify_crash_type(text, precise=True)


def types_compatible(actual: str, expected: str) -> bool:
    """Return True when actual and expected crash types are the same."""
    return actual == expected


# ═══════════════════════════════════════════════════════════════════════
# 0-day detection
# ═══════════════════════════════════════════════════════════════════════


def is_0day_alert(
    original_alert: str, latest_precise_alert: str, latest_exit_code: int = -1
) -> bool:
    """Return True if the latest crash constitutes a potential 0-day.

    Key rules:
      DCHECK -> CHECK  = patched (release-mode guard added), NOT a 0-day.
      DCHECK -> DCHECK = still debug-only, still a 0-day.
      DCHECK -> FATAL  = proper error path added, treated as mitigated.
      Anything -> ASAN/SANDBOX/DCHECK = still a 0-day.
      RUNTIME_CRASH is a 0-day only if exit code is 139 (segfault).
    """
    if latest_precise_alert in (
        "ASAN_CRASH",
        "SANDBOX_VIOLATION",
        "DCHECK",
    ):
        return True
    if latest_precise_alert == "RUNTIME_CRASH":
        return latest_exit_code == 139
    if latest_precise_alert == "CHECK":
        return False
    if latest_precise_alert == "FATAL":
        return False
    return False  # STDERR_NONEMPTY, CLEAN, etc.


def is_defensive_block(text: str) -> bool:
    """Return True for release-mode hard stops that can represent a patch block.

    This is intentionally narrower than "any crash": ASan bug reports, DCHECKs,
    and raw runtime crashes are still treated as active vulnerability signals.
    Release CHECK/FATAL paths, including SBXCHECK safe termination, are
    acceptable only for patched-image validation when the original verified
    crash signature is no longer reproduced.
    """
    crash_type = classify_crash_type_precise(text)
    if crash_type in {"CHECK", "FATAL"}:
        return True
    return (
        crash_type == "SANDBOX_VIOLATION"
        and _SAFE_TERMINATION_RE.search(text) is not None
        and _CHECK_FAILED_RE.search(text) is not None
    )


# ═══════════════════════════════════════════════════════════════════════
# Text normalisation / core extraction
# ═══════════════════════════════════════════════════════════════════════

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
_HEX_ADDR_RE = re.compile(r"0x[0-9a-fA-F]+")
_LONG_HEX_RE = re.compile(r"\b[0-9a-fA-F]{10,}\b")
_PID_RE = re.compile(r"==\d+==")
_THREAD_RE = re.compile(r"\bT\d+\b")
_ONLY_RUNTIME_SANDBOX_RE = re.compile(
    r"^Sandbox testing mode is enabled\."
    r" Only sandbox violations will be reported, all other crashes will be ignored\.$",
    re.IGNORECASE,
)
_TECHNICAL_SANDBOX_NOTE_RE = re.compile(
    r"technically not a sandbox violation|manual investigation", re.IGNORECASE
)
_CHECK_BLOCK_START_RE = re.compile(r"^# Fatal error in ", re.IGNORECASE)
_DEBUG_CHECK_LINE_RE = re.compile(r"^# Debug check failed:", re.IGNORECASE)
_RELEASE_CHECK_LINE_RE = re.compile(r"^# Check failed:", re.IGNORECASE)
_FAILURE_MESSAGE_RE = re.compile(r"^#FailureMessage Object:", re.IGNORECASE)
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
_STACK_SECTION_RE = re.compile(r"^={4,}\s+(?:C|JS) stack trace", re.IGNORECASE)
_GENERIC_SECTION_RE = re.compile(
    r"^(?:={5,}|-{5,}|<No Source>|=====================)$"
)
_RAW_STACK_LINE_RE = re.compile(
    r"^(?:\[\d+\]:|\[[0-9A-Za-z]+\]|out/.*\(|/lib/.*\(|#\d+\s)"
)
_VALUE_NOISE_RE = re.compile(r"^(?:-?\d+|NaN|undefined|null|true|false)$")
_RECEIVED_SIGNAL_RE = re.compile(
    r"^Received signal\s+\d+(?:\s+\S+)?(?:\s+\S+)?$", re.IGNORECASE
)
_RUNTIME_TAIL_RE = re.compile(
    r"Segmentation fault"
    r"|Aborted"
    r"|Trace/breakpoint trap"
    r"|Illegal instruction"
    r"|core dumped"
    r"|SIG[A-Z]+ caught",
    re.IGNORECASE,
)


def _normalise_addresses(text: str) -> str:
    text = _ANSI_RE.sub("", text)
    text = text.replace(r"\!", "!")
    text = _HEX_ADDR_RE.sub("0xADDR", text)
    text = _LONG_HEX_RE.sub("HEXADDR", text)
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


def _join_core_lines(lines: list[str]) -> str:
    return "\n".join(_dedupe_lines(lines))


def _is_global_noise(line: str) -> bool:
    if re.match(r"^root@[0-9a-f]+:", line):
        return True
    if line.upper().startswith("TESTING POC"):
        return True
    if line.startswith("[COV]"):
        return True
    return False


def _is_informative_context_line(line: str) -> bool:
    if not line or _is_global_noise(line):
        return False
    if line == "#":
        return False
    if _ONLY_RUNTIME_SANDBOX_RE.match(line):
        return False
    if re.match(
        r"^V8 is running with experimental features enabled\.", line, re.IGNORECASE
    ):
        return False
    if re.match(r"^Sandbox bounds:", line, re.IGNORECASE):
        return False
    if re.match(r"^# Ignoring debug check failure", line, re.IGNORECASE):
        return False
    if _STACK_SECTION_RE.match(line) or _GENERIC_SECTION_RE.match(line):
        return False
    if re.match(r"^\[end of stack trace\]$", line, re.IGNORECASE):
        return False
    if _RAW_STACK_LINE_RE.match(line):
        return False
    if _VALUE_NOISE_RE.match(line):
        return False
    return True


def _extract_lines_before_marker(text: str, marker_re: re.Pattern[str], limit: int) -> list[str]:
    candidates: list[str] = []
    for raw in text.splitlines():
        line = _normalise_line(raw)
        if not line or _is_global_noise(line):
            continue
        if marker_re.search(line):
            break
        if _is_informative_context_line(line):
            candidates.append(line)
    return candidates[-limit:]


def _extract_check_block_lines(
    text: str, *, allow_debug: bool, allow_release: bool
) -> list[str]:
    if allow_debug:
        for raw in text.splitlines():
            line = _normalise_line(raw)
            if line.startswith("abort: CSA_DCHECK failed:"):
                return [line]

    block: list[str] = []
    capture = False
    for raw in text.splitlines():
        line = _normalise_line(raw)
        if not line or _is_global_noise(line):
            continue
        if not capture:
            if _CHECK_BLOCK_START_RE.match(line):
                capture = True
            else:
                continue

        if _STACK_SECTION_RE.match(line):
            break
        if not line.startswith("#"):
            if block:
                break
            continue

        if _CHECK_BLOCK_START_RE.match(line):
            block.append(line)
            continue
        if allow_debug and _DEBUG_CHECK_LINE_RE.match(line):
            block.append(line)
            continue
        if allow_release and _RELEASE_CHECK_LINE_RE.match(line):
            block.append(line)
            continue
        if _FAILURE_MESSAGE_RE.match(line):
            block.append(line)

    if allow_debug and any(_DEBUG_CHECK_LINE_RE.match(line) for line in block):
        return block
    if allow_release and any(_RELEASE_CHECK_LINE_RE.match(line) for line in block):
        return block
    return []


def _extract_asan_core_lines(text: str) -> list[str]:
    parts: list[str] = []
    for raw in text.splitlines():
        line = _normalise_line(raw)
        if not line or _is_global_noise(line):
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
        if not line or _is_global_noise(line):
            continue
        if line.startswith("bash: "):
            continue
        if _RECEIVED_SIGNAL_RE.match(line):
            parts.append(line)
            continue
        if re.search(r"Segmentation fault", line, re.IGNORECASE):
            parts.append("Segmentation fault")
        elif re.search(r"Aborted", line, re.IGNORECASE):
            parts.append("Aborted")
        elif re.search(r"Trace/breakpoint trap", line, re.IGNORECASE):
            parts.append("Trace/breakpoint trap")
        elif re.search(r"Illegal instruction", line, re.IGNORECASE):
            parts.append("Illegal instruction")
        elif re.search(r"SIG[A-Z]+ caught", line, re.IGNORECASE):
            parts.append(line)
    return _dedupe_lines(parts)


def _extract_dcheck_core_text(text: str) -> str:
    return _join_core_lines(_extract_check_block_lines(text, allow_debug=True, allow_release=False))


def _extract_asan_core_text(text: str) -> str:
    return _join_core_lines(_extract_asan_core_lines(text))


_SOURCE_FILE_RE = re.compile(
    r"(?P<file>(?:[A-Za-z0-9_./+-]+/)*[A-Za-z0-9_.+-]+"
    r"\.(?:cc|h|hh|hpp|c|cpp|inc|tq|S|s))(?::\d+(?::\d+)?)?"
)
_ASAN_STACK_LOCATION_RE = re.compile(r"^\s*#\d+\s+\S+\s+in\s+(.+)$")
_ASAN_SUMMARY_RE = re.compile(
    r"SUMMARY:\s*AddressSanitizer:\s*(?P<type>\S+)(?P<rest>.*)$"
)


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
        # Keep namespace qualifiers, but drop volatile argument lists. Walk
        # backwards so "(anonymous namespace)" inside arguments is preserved.
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


def _source_file_matches(text: str) -> list[re.Match[str]]:
    return list(_SOURCE_FILE_RE.finditer(text))


def _normalise_asan_location(raw_location: str) -> str:
    loc = _normalise_line(raw_location)
    loc = re.sub(r"\s+\(BuildId:.*?\)$", "", loc)
    loc = re.sub(r"\s+\([^)]*\+0xADDR\)$", "", loc)
    if not loc or "<unknown module>" in loc or "[stack]" in loc:
        return ""

    matches = _source_file_matches(loc)
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


def _normalise_asan_summary_location(summary_rest: str) -> str:
    rest = _normalise_line(summary_rest)
    if not rest or "<unknown module>" in rest or "[stack]" in rest:
        return ""

    match = re.search(
        r"(?P<file>\S+\.\w+)(?::\d+(?::\d+)?)?\s+in\s+(?P<symbol>.+)$",
        rest,
    )
    if match:
        source = re.sub(r":\d+(?::\d+)?$", "", match.group("file"))
        symbol = _compact_function_symbol(match.group("symbol"))
        return f"{symbol} {source}" if symbol else ""

    matches = _source_file_matches(rest)
    if not matches:
        return ""
    file_match = matches[-1]
    source = re.sub(r":\d+(?::\d+)?$", "", file_match.group("file"))
    symbol = _compact_function_symbol(rest[: file_match.start()])
    return f"{symbol} {source}" if symbol else ""


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
            loc = _normalise_asan_summary_location(summary_match.group("rest"))
            if loc and loc not in locations:
                locations.insert(0, loc)

    return AsanReport(
        vuln_type=vuln_type,
        access_kind=access_kind,
        access_size=access_size,
        locations=tuple(locations),
    )


def _extract_sandbox_core_text(text: str) -> str:
    parts: list[str] = []
    if not _ASAN_RE.search(text):
        parts = _extract_lines_before_marker(text, _SANDBOX_RE, limit=4)

    for raw in text.splitlines():
        line = _normalise_line(raw)
        if not line or _is_global_noise(line):
            continue
        if _SANDBOX_RE.search(line):
            parts.append(line)
        elif _TECHNICAL_SANDBOX_NOTE_RE.search(line):
            parts.append(line)

    if _ASAN_RE.search(text):
        parts.extend(_extract_asan_core_lines(text))
    else:
        dcheck_lines = _extract_check_block_lines(
            text, allow_debug=True, allow_release=True
        )
        if dcheck_lines:
            parts.extend(dcheck_lines)
        else:
            parts.extend(_extract_runtime_signal_lines(text))

    return _join_core_lines(parts)


def _extract_runtime_core_text(text: str) -> str:
    if _ASAN_RE.search(text):
        return _extract_asan_core_text(text)

    dcheck_lines = _extract_check_block_lines(text, allow_debug=True, allow_release=False)
    if dcheck_lines:
        prefix = _extract_lines_before_marker(text, _CHECK_BLOCK_START_RE, limit=1)
        return _join_core_lines(prefix + dcheck_lines + _extract_runtime_signal_lines(text))

    fatal_lines = _extract_check_block_lines(text, allow_debug=False, allow_release=True)
    if fatal_lines:
        prefix = _extract_lines_before_marker(text, _CHECK_BLOCK_START_RE, limit=1)
        return _join_core_lines(prefix + fatal_lines + _extract_runtime_signal_lines(text))

    pre_signal = _extract_lines_before_marker(text, _RECEIVED_SIGNAL_RE, limit=4)
    parts = pre_signal + _extract_runtime_signal_lines(text)
    return _join_core_lines(parts)


def extract_core_text(text: str, crash_type: str) -> str:
    fn = {
        "DCHECK": _extract_dcheck_core_text,
        "ASAN_CRASH": _extract_asan_core_text,
        "SANDBOX_VIOLATION": _extract_sandbox_core_text,
        "RUNTIME_CRASH": _extract_runtime_core_text,
    }.get(crash_type)
    core = fn(text) if fn else ""
    if core:
        return core

    fallback: list[str] = []
    for raw in text.splitlines():
        line = _normalise_line(raw)
        if line and not _is_global_noise(line):
            fallback.append(line)
    return _join_core_lines(fallback)


# ═══════════════════════════════════════════════════════════════════════
# Crash-signature extraction
# ═══════════════════════════════════════════════════════════════════════


def _normalise_check_expr(expr: str) -> str:
    return re.sub(r"(?<![\w.])-?\d{4,}(?![\w.])", "N", expr.strip())


def _sig_dcheck(text: str) -> str:
    files: list[str] = []
    parts: list[str] = []
    for m in re.finditer(r"Fatal error in\s+(\S+),\s+line\s+\d+", text):
        files.append(f"file:{m.group(1)}")
    for m in re.finditer(r"Debug check failed:\s*(.+)", text):
        parts.append(f"check:{_normalise_check_expr(m.group(1))}")
    for m in re.finditer(r"CSA_DCHECK failed:\s*(.+)", text):
        parts.append(f"csa:{_normalise_check_expr(m.group(1))}")
    return _join_core_lines(files + parts) if parts else ""


def _sig_release_check(text: str) -> str:
    files: list[str] = []
    parts: list[str] = []
    for m in re.finditer(r"Fatal error in\s+(\S+),\s+line\s+\d+", text):
        files.append(f"file:{m.group(1)}")
    for m in re.finditer(r"Check failed:\s*(.+)", text):
        parts.append(f"check:{_normalise_check_expr(m.group(1))}")
    return _join_core_lines(files + parts) if parts else ""


def _sig_asan(text: str) -> str:
    parts: list[str] = []
    for m in re.finditer(r"ERROR:\s*AddressSanitizer:\s*(\S+)", text):
        parts.append(f"type:{m.group(1)}")
    for m in re.finditer(
        r"SUMMARY:\s*AddressSanitizer:\s*(\S+)\s+(.+?)$", text, re.MULTILINE
    ):
        parts.append(f"summary:{m.group(1)} {m.group(2).strip()}")
    for m in re.finditer(r"#0\s+\S+\s+in\s+(\S+)", text):
        parts.append(f"frame0:{m.group(1)}")
        break
    return _join_core_lines(parts)


def _sig_runtime(text: str) -> str:
    signals: list[str] = []
    for m in re.finditer(
        r"^Received signal[ \t]+(\d+)(?:[ \t]+(\S+))?(?:[ \t]+\S+)?$",
        text,
        re.MULTILINE,
    ):
        detail = m.group(2)
        if detail and detail != "<unknown>":
            signals.append(f"signal:{detail}")
        else:
            signals.append(f"signal:{m.group(1)}")

    aborts = [
        f"abort:{m.group(1)}"
        for m in re.finditer(r"^abort:\s*(.+)$", text, re.MULTILINE)
    ]
    if signals or aborts:
        return _join_core_lines(signals + aborts)

    parts: list[str] = []
    for pat, label in (
        (r"Segmentation fault", "segmentation_fault"),
        (r"Aborted", "aborted"),
        (r"Trace/breakpoint trap", "trace_breakpoint_trap"),
        (r"Illegal instruction", "illegal_instruction"),
        (r"SIGILL caught", "sigill_caught"),
    ):
        if re.search(pat, text, re.IGNORECASE):
            parts.append(label)
    return _join_core_lines(parts)


def _sig_sandbox(text: str) -> str:
    parts = ["sandbox_violation"] if _SANDBOX_RE.search(text) else []
    if _TECHNICAL_SANDBOX_NOTE_RE.search(text):
        parts.append("manual_investigation")

    asan_sig = _sig_asan(text)
    if asan_sig:
        parts.append(asan_sig)
    else:
        check_sig = _sig_dcheck(text) or _sig_release_check(text)
        if check_sig:
            parts.append(check_sig)
        else:
            runtime_sig = _sig_runtime(text)
            if runtime_sig:
                parts.append(runtime_sig)
    return _join_core_lines(parts)


def extract_signature(text: str, crash_type: str) -> str:
    fn = {
        "DCHECK": _sig_dcheck,
        "ASAN_CRASH": _sig_asan,
        "SANDBOX_VIOLATION": _sig_sandbox,
        "RUNTIME_CRASH": lambda t: _join_core_lines(
            [
                sig
                for sig in (
                    _sig_asan(t),
                    _sig_dcheck(t),
                    _sig_release_check(t),
                    _sig_runtime(t),
                )
                if sig
            ]
        ),
    }.get(crash_type)
    return fn(text) if fn else ""


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


def _exact_core_match(
    actual_text: str, expected_text: str, crash_type: str
) -> tuple[bool, float, str]:
    actual_core = extract_core_text(actual_text, crash_type)
    expected_core = extract_core_text(expected_text, crash_type)
    if actual_core and actual_core == expected_core:
        return True, 1.0, "matched:exact_core"
    if not actual_core or not expected_core:
        return False, 0.0, "missing_core"
    return False, 0.0, f"{crash_type.lower()}_core_mismatch"


_WEAK_RUNTIME_SIG_RE = re.compile(
    r"^(?:signal:[A-Z0-9_]+|segmentation_fault|aborted|trace_breakpoint_trap|"
    r"illegal_instruction|sigill_caught)$"
)


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
        (r"SIGILL caught", "illegal_instruction"),
    ):
        if re.search(pat, text, re.IGNORECASE):
            tokens.add(label)
    return tokens


def _compatible_runtime_signal(actual_text: str, expected_text: str) -> bool:
    actual = _runtime_signal_tokens(actual_text)
    expected = _runtime_signal_tokens(expected_text)
    if not actual or not expected:
        return False
    shared = actual & expected
    return any(
        token.startswith("signal_num:")
        or token.startswith("signal_detail:")
        or token
        in {
            "segmentation_fault",
            "aborted",
            "trace_breakpoint_trap",
            "illegal_instruction",
        }
        for token in shared
    )


def _is_weak_signature(signature: str, crash_type: str) -> bool:
    """Return True for signatures that only prove a generic crash class."""
    lines = [line for line in signature.splitlines() if line]
    if not lines:
        return True
    if crash_type == "RUNTIME_CRASH":
        return all(_WEAK_RUNTIME_SIG_RE.match(line) for line in lines)
    if crash_type == "SANDBOX_VIOLATION":
        return all(
            line in ("sandbox_violation", "manual_investigation")
            or _WEAK_RUNTIME_SIG_RE.match(line)
            for line in lines
        )
    return False


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
        if (
            actual.access_size
            and expected.access_size
            and actual.access_size != expected.access_size
        ):
            return (
                False,
                0.0,
                f"asan_access_size_mismatch:{actual.access_size}!={expected.access_size}",
            )
    if not actual.locations or not expected.locations:
        return False, 0.0, "asan_locations_missing"

    matched_locations = _lcs_len(actual.locations, expected.locations)
    denominator = max(len(actual.locations), len(expected.locations))
    location_ratio = matched_locations / denominator if denominator else 0.0
    matched = location_ratio > 0.5
    relation = ">" if matched else "<="
    reason = (
        "matched:asan_locations"
        if matched
        else f"asan_location_overlap:{matched_locations}/{denominator}{relation}0.5"
    )
    return matched, location_ratio, reason


def _match_by_rule(
    actual_text: str, expected_text: str, crash_type: str
) -> tuple[bool, float, float, str]:
    if crash_type == "ASAN_CRASH":
        matched, score, reason = _match_asan(actual_text, expected_text)
        return matched, score, score, reason
    if crash_type == "DCHECK":
        matched, score, reason = _exact_core_match(
            actual_text, expected_text, crash_type
        )
        return matched, score, score, reason

    actual_core = extract_core_text(actual_text, crash_type)
    expected_core = extract_core_text(expected_text, crash_type)
    actual_sig = extract_signature(actual_core, crash_type)
    expected_sig = extract_signature(expected_core, crash_type)

    if crash_type == "SANDBOX_VIOLATION":
        if (
            _SANDBOX_RE.search(actual_text)
            and _SANDBOX_RE.search(expected_text)
            and _compatible_runtime_signal(actual_text, expected_text)
        ):
            return True, 1.0, 1.0, "matched:sandbox_runtime_signal"

    if crash_type == "RUNTIME_CRASH":
        if _compatible_runtime_signal(actual_text, expected_text):
            return True, 1.0, 1.0, "matched:runtime_signal"

    if actual_sig or expected_sig:
        if actual_sig and actual_sig == expected_sig:
            if _is_weak_signature(actual_sig, crash_type):
                matched, score, reason = _exact_core_match(
                    actual_text, expected_text, crash_type
                )
                if matched:
                    return True, score, score, "matched:weak_signature_exact_core"
                return False, score, score, reason
            return True, 1.0, 1.0, "matched:signature"
        return False, 0.0, 0.0, f"{crash_type.lower()}_signature_mismatch"

    matched, score, reason = _exact_core_match(actual_text, expected_text, crash_type)
    return matched, score, score, reason


def compute_match(
    actual_text: str,
    expected_text: str,
    expected_type_hint: Optional[str] = None,
) -> MatchResult:
    """Determine whether actual_text (stderr) reproduces the crash in expected_text."""
    actual_text = actual_text.strip()
    expected_text = expected_text.strip()

    if not actual_text:
        return MatchResult(
            "CLEAN",
            classify_crash_type(expected_text),
            False,
            0.0,
            0.0,
            0.0,
            False,
            "actual_empty",
        )
    if not expected_text:
        return MatchResult(
            classify_crash_type(actual_text),
            "CLEAN",
            False,
            0.0,
            0.0,
            0.0,
            False,
            "expected_empty",
        )

    actual_type = classify_crash_type(actual_text)
    expected_type = expected_type_hint or classify_crash_type(expected_text)

    if actual_type not in VALID_CRASH_TYPES:
        return MatchResult(
            actual_type,
            expected_type,
            False,
            0.0,
            0.0,
            0.0,
            False,
            f"invalid_actual_type:{actual_type}",
        )
    if expected_type not in VALID_CRASH_TYPES:
        return MatchResult(
            actual_type,
            expected_type,
            False,
            0.0,
            0.0,
            0.0,
            False,
            f"invalid_expected_type:{expected_type}",
        )

    if not types_compatible(actual_type, expected_type):
        return MatchResult(
            actual_type,
            expected_type,
            False,
            0.0,
            0.0,
            0.0,
            False,
            f"type_mismatch:{actual_type}!={expected_type}",
        )

    canon = expected_type if expected_type in VALID_CRASH_TYPES else actual_type

    matched, sig_sim, text_sim, reason = _match_by_rule(
        actual_text, expected_text, canon
    )
    score = sig_sim

    return MatchResult(
        actual_type=actual_type,
        expected_type=expected_type,
        type_compatible=True,
        sig_sim=round(sig_sim, 4),
        text_sim=round(text_sim, 4),
        score=round(score, 4),
        matched=matched,
        reason=reason,
    )
