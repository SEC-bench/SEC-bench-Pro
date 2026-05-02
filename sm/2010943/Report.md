# JIT Info Disclosure

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=2010943
CVE: CVE-2026-2783
Component: JavaScript Engine: JIT
Bounty: (unknown)
Keywords: sec-high

## Summary

A JIT miscompilation vulnerability in SpiderMonkey causes information disclosure. The JIT compiler incorrectly optimizes certain code patterns, allowing uninitialized or out-of-bounds memory to be read. The fix commit (e00390fd4e3b0) is test-only, meaning the actual code fix was landed earlier. The test files added by this commit (js/src/jit-test/tests/ion/bug2010943-1.js and bug2010943-2.js) serve as the PoC for this vulnerability.

## Fix

Commit: e00390fd4e3b0 — "Add tests"

NOTE: This is a test-only commit. The actual fix was landed in a prior commit. The PoC is extracted from the test files added in this commit.

## Affected Files

- js/src/jit-test/tests/ion/bug2010943-1.js
- js/src/jit-test/tests/ion/bug2010943-2.js

## Steps to Reproduce

Run the test files from the fix commit with `--fuzzing-safe` flag.
