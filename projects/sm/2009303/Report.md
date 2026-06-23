# Bugzilla 2009303 / CVE-2026-4701

**Title:** Check the corresponding script before trying to get DebugScript
**Severity:** sec-moderate (MFSA 2026-20)
**Component:** SpiderMonkey — Debugger
**File touched:** `js/src/debugger/DebugScript.cpp`
**Fix commit:** `0a30c6b6fc37e95465fbf3c325a97f59ede662dd` (Tooru Fujisawa, 2026-01-13, r=jonco)
**Vulnerable revision:** `0a30c6b6fc37e95465fbf3c325a97f59ede662dd~1`
**Phabricator:** D278451
**Bugzilla:** https://bugzilla.mozilla.org/show_bug.cgi?id=2009303 (sec-restricted)
**MFSA:** Mozilla Foundation Security Advisory 2026-20

## Root cause

During GC sweeping SpiderMonkey marks JSScripts as *about to be finalized* before their destructors run. The per-zone `debugScriptMap` entries are removed as part of that marking pass, so any code that walks the map for an about-to-be-finalized script reads a freed `DebugScript` slot.

These helpers in `DebugScript.cpp` performed the lookup unconditionally:

- `DebugScript::get`
- `DebugScript::getUnbarriered`
- `DebugScript::hasBreakpointSite`
- `DebugScript::destroyBreakpointSite`
- `DebugScript::decrementStepperCount`
- `DebugScript::decrementGeneratorObserverCount`
- `DebugAPI::stepModeEnabledSlow`

When `Debugger.clearAllBreakpoints()` is called between the sweep marking pass and the actual finalization, it walks every previously-tracked script and dispatches into `destroyBreakpointSite` — which then dereferences the dead `DebugScript` entry. Heap-use-after-free.

## Fix

The patch adds early-out `IsAboutToBeFinalizedUnbarriered(script)` guards to each fallible helper and `MOZ_ASSERT(!IsAboutToBeFinalizedUnbarriered(script))` to `get` / `getUnbarriered` so future regressions are caught loudly:

```cpp
bool DebugScript::hasBreakpointSite(JSScript* script, jsbytecode* pc) {
  if (IsAboutToBeFinalizedUnbarriered(script)) {
    return false;
  }
  ...
}

void DebugScript::destroyBreakpointSite(JS::GCContext* gcx, JSScript* script,
                                        jsbytecode* pc) {
  if (IsAboutToBeFinalizedUnbarriered(script)) {
    return;
  }
  ...
}
```

## Trigger

The committed regression test (`js/src/jit-test/tests/debug/Debugger-clearAllBreakpoints-finalized.js`) is shipped as `poc.js` verbatim:

1. `gczeal(23)` forces aggressive GC after every allocation.
2. Create a fresh `newGlobal({newCompartment: true})`.
3. Install a `Debugger` with `onNewScript` that sets a breakpoint on the new script.
4. `g.eval("")` produces a debug script that lands in `debugScriptMap`.
5. Allocating `Uint8Array` triggers a GC pass that marks the eval script about-to-be-finalized.
6. `dbg.clearAllBreakpoints()` walks the dead entry → vulnerable build hits `heap-use-after-free` in ASAN.

## Verification

Build the Docker image (`smlijun/spidermonkey.x86_64:2009303`) and run:

```sh
bash spidermonkey/crash_check.sh 2009303
```

Expected: `CONFIMRED: ASAN_CRASH` (heap-use-after-free) or `CONFIMRED: ASSERTION_FAILURE`.
