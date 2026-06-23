# Bugzilla 2013562 / CVE-2026-2765

**Title:** Enter correct realm before resolving same-thread `Atomics.waitAsync` promise
**Severity:** sec-high
**Component:** SpiderMonkey — JavaScript Engine — Atomics
**File touched:** `js/src/builtin/AtomicsObject.cpp` (`js::atomics_notify_impl`)
**Fix commit:** `23cf0b3985c329aae2898bae518a7f5813c132ae` (Iain Ireland, 2026-02-09, r=arai)
**Vulnerable revision:** `23cf0b3985c329aae2898bae518a7f5813c132ae~1`
**Phabricator:** D281314
**Bugzilla:** https://bugzilla.mozilla.org/show_bug.cgi?id=2013562 (sec-restricted)
**MFSA:** Mozilla Foundation Security Advisory 2026 (Firefox release branch)

## Summary

`Atomics.waitAsync` returns a promise that is registered against a `SharedArrayBuffer`'s waiter list. When the buffer is shared between realms (e.g. via `newGlobal()` cross-assignment), each realm's `Atomics.waitAsync` call produces a promise inside its own realm, but all promises are tracked on the shared buffer's single waiter list. A subsequent `Atomics.notify` from any realm walks that combined list and resolves every matching waiter in one loop.

In the vulnerable code, `js::atomics_notify_impl` calls `PromiseObject::resolve(cx, promisesToResolve[i], "ok")` directly without first entering each promise's realm. SpiderMonkey requires the active realm on `JSContext` to match the realm of any object being mutated; resolving a foreign-realm promise this way violates AutoRealm/compartment invariants. In ASAN+debug builds this trips compartment assertions in the GC barrier or wrapping machinery; in release builds it leads to cross-realm state corruption.

## Root cause

```cpp
// js/src/builtin/AtomicsObject.cpp — js::atomics_notify_impl, vulnerable
RootedValue resultMsg(cx, StringValue(cx->names().ok));
for (uint32_t i = 0; i < promisesToResolve.length(); i++) {
  if (!PromiseObject::resolve(cx, promisesToResolve[i], resultMsg)) {
    MOZ_ASSERT(cx->isThrowingOutOfMemory() || cx->isThrowingOverRecursed());
    return false;
  }
}
```

The loop dereferences and rewrites foreign-realm `PromiseObject` slots while `cx` is still scoped to the realm that called `Atomics.notify`. There is no `AutoRealm` to switch.

## Fix

```cpp
// After 23cf0b3985c32 — entering each promise's realm before resolving
RootedValue resultMsg(cx, StringValue(cx->names().ok));
for (uint32_t i = 0; i < promisesToResolve.length(); i++) {
  AutoRealm ar(cx, promisesToResolve[i]);                   // <-- added
  if (!PromiseObject::resolve(cx, promisesToResolve[i], resultMsg)) {
    MOZ_ASSERT(cx->isThrowingOutOfMemory() || cx->isThrowingOverRecursed());
    return false;
  }
}
```

The fix also adds `#include "vm/Realm-inl.h"` so `AutoRealm` is in scope. No tests were committed publicly with the fix (sec-restricted bug).

## Trigger (reverse-engineered PoC)

`poc.js` constructs two realms sharing a single `SharedArrayBuffer`:

1. The non-default realm registers an async waiter via `Atomics.waitAsync(ia, 0, 0)`.
2. The default realm calls `Atomics.notify(i32, 0)`.
3. `atomics_notify_impl` walks the combined waiter list and calls `PromiseObject::resolve` on the foreign-realm promise without an `AutoRealm`.
4. `drainJobQueue()` ensures the resolution path runs in-turn so the crash is observed before shell exit.

The crash manifests as either an ASAN/MOZ assertion in compartment checking, a debug `MOZ_CRASH("wrong realm")`, or a sanitizer-flagged read/write through the wrapped object — depending on which assertion fires first under the chosen build flavor.

## Verification

Build the Docker image (`smlijun/spidermonkey.x86_64:2013562`) and run:

```sh
bash spidermonkey/crash_check.sh 2013562
```

Expected: `CONFIMRED: ASSERTION_FAILURE` or `CONFIMRED: ASAN_CRASH`.
