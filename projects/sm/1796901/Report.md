# Bugzilla 1796901 / CVE-2022-45409

**Title:** Realm incremental-marking state cleared at end-of-GC instead of start-of-GC, leaving a poisoned realm reachable into the next GC cycle
**Severity:** sec-high (MFSA 2022-47, Firefox 107)
**Component:** SpiderMonkey — GC — `js/src/gc/GC.cpp`
**Fix commit:** `041774db08880cca1ab10e807d0d71718964dffe` (Jon Coppeard, 2022-10) — "Bug 1796901 - Move incremental marking state reset to start of GC"
**Vulnerable revision:** `041774db08880cca1ab10e807d0d71718964dffe~1`

## Summary

`GCRuntime` carries per-realm bookkeeping that records whether a realm
was created mid-incremental-marking (`Realm::wasAllocatedDuringGC` and
related flags). Pre-fix, this state was reset at the *end* of a GC.
If a GC was aborted (`abortgc()`), or terminated early because the
slice budget hit zero before the sweep, the reset was skipped. The
next collection then started with stale "allocated during GC" flags
on realms that had since been finalised, so `sweepZones` walked into a
dead zone whose realms list still pointed at freed compartments,
asserting `zoneIsDead` (debug) and dereferencing a poisoned pointer
on release/ASAN.

## Fix

Move the per-realm reset to the *start* of every GC
(`GCRuntime::beginCollection` path), so an aborted or partial GC
cannot leave residual state visible to the next cycle.

## Trigger (`poc.js`)

```js
gcslice(0);     // begin an incremental GC, do zero work
evalcx("lazy"); // create a new lazy compartment/realm
abortgc();      // cancel the in-progress GC, leaving stale flags
                // shutdown GC then walks the poisoned zone
```

## Expected crash

Debug build: `MOZ_CRASH(zoneIsDead)` at `js/src/gc/GC.cpp:2083`.
ASAN build: SEGV (write to `0x0`) inside
`js::gc::GCRuntime::sweepZones` at `GC.cpp:2083`, reached from
`JSRuntime::destroyRuntime` → final `gc()`.

## Verification

```sh
docker build -t hwiwonlee/sm.x86_64:1796901 spidermonkey/1796901
bash spidermonkey/crash_check.sh 1796901
```

Expected: `CONFIMRED: ASAN_CRASH`.
