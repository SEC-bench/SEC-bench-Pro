# Bugzilla 2010940 — Embargoed (likely sec-high) FinalizationRegistry queue UAF

**Title:** Clear queued objects for dead finalization registries during sweep
**Severity:** embargoed, signals point to **sec-high** (access-restricted Bugzilla, ships with a committed regression test)
**Component:** SpiderMonkey — GC — FinalizationRegistry
**Files touched:**
- `js/src/builtin/FinalizationRegistryObject.cpp` (`FinalizationQueueObject::clear`, `cleanupQueuedRecords` invariant)
- `js/src/builtin/FinalizationRegistryObject.h` (method decl)
- `js/src/gc/FinalizationObservers.cpp` (call site)

**Fix commit:** `2e29a3d3d930453174717fd963413492a80b31ec` (Jon Coppeard, 2026-01-26, r=sfink)
**Test commit:** `2add863ab5962171d2c0f0b594ca4b3325744ffd` (Jon Coppeard, 2026-03-10, r=sfink)
**Vulnerable revision:** `2e29a3d3d930453174717fd963413492a80b31ec~1`
**Phabricator:** D279644 (code) + D279645 (test)
**Bugzilla:** https://bugzilla.mozilla.org/show_bug.cgi?id=2010940 (sec-restricted)

## Root cause

`FinalizationObservers::traceWeakFinalizationRegistryEdges` is called during GC to walk the per-zone map of active `FinalizationRegistryObject`s. For every record whose target cell has just become unreachable, it removes the record from the registry's internal weak map and **promotes** it — by calling `queue->queueRecordToBeCleanedUp(record)` — into the owning `FinalizationQueueObject`'s strong `recordsToBeCleanedUp` vector, so the JS cleanup callback can run in a later turn of the event loop.

That promotion path takes no read barrier on the record. A read barrier is not feasible at this point: marking for the record's zone may already have finished, and re-marking a freshly-strong reference after the snapshot boundary would violate the incremental-marking invariant. The commit message is explicit about this:

> "It's not really feasible to add [a read barrier] here either since we may have finished marking at this point."

The bug manifests when the `FinalizationRegistryObject` **itself** dies in the same GC cycle (e.g. because the program abandoned its only reference to the registry right before the GC fired). Its `FinalizationQueueObject` can outlive it briefly because the queue is still held by GC internal state (`queueFinalizationRegistryForCleanup` enqueues the queue for post-GC callback dispatch). During the same sweep, records that were promoted into that queue by the path above are themselves swept — the queue ends up with a vector of dangling `FinalizationRecordObject*` pointers. The next invocation of `FinalizationQueueObject::cleanupQueuedRecords` (js/src/builtin/FinalizationRegistryObject.cpp:825) iterates the vector and dereferences each record → heap-use-after-free, ASAN catches it inside `cleanupQueuedRecords` / `FinalizationRecordObject::queue`.

## Fix

Three pieces:

1. New `FinalizationQueueObject::clear()` that empties `recordsToBeCleanedUp`:
   ```cpp
   void FinalizationQueueObject::clear() {
     MOZ_ASSERT(!hasRegistry());
     if (FinalizationRecordVector* records = recordsToBeCleanedUp()) {
       records->clear();
     }
   }
   ```

2. `traceWeakFinalizationRegistryEdges` calls `clear()` the moment it notices the registry is dead, BEFORE removing the entry:
   ```cpp
   if (result.isDead()) {
     auto* registry = result.initialTarget();
     registry->queue()->setHasRegistry(false);
     // Remove any queued records. These might be dead since the registry was
     // not marked.
     registry->queue()->clear();
     e.removeFront();
   }
   ```

3. A new invariant check in `cleanupQueuedRecords` pins the fix in place:
   ```cpp
   FinalizationRecordVector* records = queue->recordsToBeCleanedUp();
   MOZ_ASSERT_IF(!queue->hasRegistry(), records->empty());
   ```

The commit also extends the block-comment inside `traceWeakFinalizationRegistryEdges` to explain why a read barrier is not used.

## Trigger

The committed regression test (`js/src/jit-test/tests/gc/bug-2010940.js`) ships as `poc.js` verbatim:

```js
gczeal(9, 100);                          // incremental marking validator
let g = newGlobal({newCompartment: true});
with (g) {
  for (let i = 0; i < 5000; i++) {
    (() => {
      let c = [], d = [];
      let e = new FinalizationRegistry(Object);
      e.register(c);
      e.register(d);
      new Int8Array(294967295);          // allocate ~295 MB → OOM mid-closure
    })();                                 // everything goes out of scope here
  }
}
```

The oversized `Int8Array` forces an OOM inside the closure, simultaneously:
- abandoning the registry `e` (so the GC observes it as dead)
- abandoning the targets `c` and `d` (so their records become eligible for promotion)
- triggering an allocation-failure path that runs a GC

Under `gczeal(9, 100)` (incremental marking validator) the marking pass pauses at a point where records have been queued but the registry's zone is swept before the queue is drained, hitting the UAF. 5000 iterations provide enough windows that at least one crashes reliably.

## Verification

```sh
bash spidermonkey/crash_check.sh 2010940
```

Expected: `CONFIMRED: ASAN_CRASH` (heap-use-after-free in `FinalizationRecordObject` / `cleanupQueuedRecords`) or `CONFIMRED: ASSERTION_FAILURE`.
