# RegExp Bailout Recovery GC Corruption

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1942881
CVE: CVE-2025-1934
Component: JavaScript Engine: JIT
Bounty: (sec-bounty+)
Keywords: sec-high

## Summary

A vulnerability exists in SpiderMonkey's JIT compiler where `MRegExpMatcher` was marked with `can_recover: true` in MIROps.yaml. When RegExpMatcher bails out and tries to recover via `RRegExpMatcher::recover()`, it calls `RegExpMatcherRaw` which can trigger GC. During GC in the recover phase, the snapshot state is inconsistent, causing corruption. The assertion `!cx->suppressGC` fires because GC is suppressed during recovery but RegExpMatcherRaw attempts it anyway.

## Steps to Reproduce

On the vulnerable revision, run with `--fuzzing-safe --fast-warmup`:

```javascript
for (a = 0; ; a++) {
    for (b = true; b; b = !inIon())
        c = 0
    function d() {
        if (c++ < 10)
            interruptIf(true)
        return true
    }
    setInterruptCallback(d)
    d()
    const e = "".substring().match("0*[]")
    if (a >= 50)
        e.f
}
```

Testing revision: `d55e89d48a8053ce45a74b0ec92c0ff6a9dcc43d`

## Crash Type

Assertion failure: `!cx->suppressGC` at js/src/vm/Interpreter.cpp:463

## Fix

Fix commit: `38e094298030` (git: `38e09429803061b0eab79fa3ee2efc116577a134`)

The fix removes `can_recover: true` from MRegExpMatcher in MIROps.yaml and removes the entire RRegExpMatcher recover instruction from Recover.cpp and Recover.h. This prevents the dangerous GC-triggering code path during bailout recovery.

## Affected Versions

Firefox 135-136, ESR 128.
