// Bug 1989978 — CVE-2025-11711: Segmentation fault in JSON.stringify
//
// Root cause: FastSerializeJSONProperty in js/src/builtin/JSON.cpp uses
// MaybeGetRawJSON to peek at the slot of a JSON.rawJSON-wrapped object
// without re-validating that the slot still holds a JSString*. When the
// caller iterates the object with `for ... in` and the body writes into
// the rawJSON slot (e.g. `a[it] = 5`), Ion's iteration optimisation lets
// the write reach the slot directly even though the property is supposed
// to be non-writable. The next FastSerializeJSONProperty call reads the
// stale slot, dereferences the integer it now holds, and SEGVs.
//
// Fix: fa91ed58b791 — Don't support unwritable iterator indices (Jan de
// Mooij, 2025-09-26).
//
// Bugzilla testcase verbatim.
function opt(a) {
    for (const it in a) {
        a[it] = 5;
    }
}
const obj = JSON.rawJSON(256n, 256n, opt);
for (let i = 0; i < 100; i++) {
    opt(obj);
}
JSON.stringify(obj);
