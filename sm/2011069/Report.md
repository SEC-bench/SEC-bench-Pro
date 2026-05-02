# GC Race Condition

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=2011069
CVE: CVE-2026-2802
Component: JavaScript Engine: GC
Bounty: (unknown)
Keywords: sec-high

## Summary

A race condition vulnerability exists in SpiderMonkey's garbage collector. The GC can race with mutator threads, leading to incorrect object state and potential use-after-free conditions. The fix commit (4faa7e9916a8f) is test-only, meaning the actual code fix was landed in a prior commit. The test file added by this commit (js/src/jit-test/tests/gc/bug-2011069.js) serves as the PoC.

NOTE: This is a race condition and may not reproduce deterministically. Multiple runs may be needed to trigger the vulnerability.

## Fix

Commit: 4faa7e9916a8f — "Add testcase" (test-only, actual fix was earlier)

## Affected Files

- js/src/jit-test/tests/gc/bug-2011069.js

## Steps to Reproduce

Run the test file from the fix commit with `--fuzzing-safe` flag. May require multiple attempts due to the non-deterministic nature of race conditions.
