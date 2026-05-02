// Bugzilla 2010940 — FinalizationQueueObject use-after-free on
// dead-registry queued records (embargoed, likely sec-high).
//
// In-tree regression test: js/src/jit-test/tests/gc/bug-2010940.js (commit
// 2add863ab5962, 2026-03-10). Shipped verbatim.
//
// Mechanism (from commit 2e29a3d3d9304, Jon Coppeard, 2026-01-26):
//   FinalizationObservers::traceWeakFinalizationRegistryEdges promotes
//   weakly-held FinalizationRecordObjects from the per-registry weak map to
//   a strong `recordsToBeCleanedUp` queue on the FinalizationQueueObject so
//   the cleanup callback can run later. That promotion path takes no read
//   barrier — it cannot, since marking may already have finished for the
//   zone. When the owning FinalizationRegistryObject itself dies in the same
//   GC cycle, the queue can still contain pointers to records that are
//   about to be swept, producing dangling pointers. A subsequent invocation
//   of `FinalizationQueueObject::cleanupQueuedRecords` then dereferences the
//   freed records → heap-use-after-free.
//
// The in-tree PoC forces many short-lived FinalizationRegistry instances
// under `gczeal(9, 100)` (incremental marking validator) and allocates a
// huge (too-large) Int8Array at the bottom of each closure to trigger OOM,
// ensuring the registry dies mid-GC with queued records present.

gczeal(9, 100);
let g = newGlobal({newCompartment: true});
with (g) {
  for (let i = 0; i < 5000; i++) {
    (() => {
      let c = [];
      let d = [];
      let e = new FinalizationRegistry(Object);
      e.register(c);
      e.register(d);
      new Int8Array(294967295);
    })();
  }
}
