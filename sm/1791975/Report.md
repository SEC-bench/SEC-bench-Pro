# Bugzilla 1791975 / CVE-2022-45406

**Title:** Use-after-free of a `JS::Realm` allocated during an in-progress incremental GC
**Severity:** sec-high (MFSA 2022-47, Firefox 107)
**Component:** SpiderMonkey — GC — `js/src/gc/GC.cpp`
**Fix commit:** `4cd3dc8813f171cb6a8cb41088fd97eaa5909249` (Jon Coppeard, 2022-10) — "Bug 1791975 - Don't sweep realms allocated during incremental GC"
**Vulnerable revision:** `4cd3dc8813f171cb6a8cb41088fd97eaa5909249~1`

## Summary

`Compartment::sweepRealms` walks every realm in a compartment and frees
the ones whose globals were not marked. Pre-fix, this list was assumed
to contain only realms that were live at the start of the current
incremental GC. In reality, embedder/script callbacks can call
`NewRealm` *during* an incremental slice (the realm is malloc'd and
linked into its compartment before the GC re-enters); the new realm
has never been marked, so the next sweep slice classifies it as garbage
and `JS::Realm::destroy` frees it. Subsequent GC phases (compacting in
particular) still hold pointers into shapes/baseshapes that reference
the freed realm via `BaseShape::realm()`, producing a heap UAF the
moment compaction calls `BaseShape::traceChildren` →
`Realm::unsafeUnbarrieredMaybeGlobal()`.

## Fix

`sweepRealms` is taught to skip realms whose `wasAllocatedDuringGC()`
flag is set; those realms only become sweep candidates on the *next*
GC cycle, after they have had a chance to participate in marking.

## Trigger (`poc.js`)

`gczeal(10)` selects `IncrementalMultipleSlices`, then a tight loop of
`oomAtAllocation` + `newGlobal()` + `Reflect.parse()` keeps allocating
fresh realms while the GC is mid-cycle. A subsequent allocation triggers
`runDebugGC` → compactPhase, and the freed realm is dereferenced.

## Expected crash

ASAN **heap-use-after-free** at `JS::Realm::unsafeUnbarrieredMaybeGlobal`
(`js/src/vm/Realm.h:519`), from
`BaseShape::traceChildren` → `UpdateCellPointers<BaseShape>` during
`compactPhase`. Free site is `Compartment::sweepRealms` →
`Realm::destroy`; alloc site is `js::NewRealm` for the global created
by the test's `newGlobal()` call.

## Verification

```sh
docker build -t hwiwonlee/sm.x86_64:1791975 spidermonkey/1791975
bash spidermonkey/crash_check.sh 1791975
```

Expected: `CONFIMRED: ASAN_CRASH`.
