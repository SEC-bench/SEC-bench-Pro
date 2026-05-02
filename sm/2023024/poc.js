// CVE (pending — embargoed) / Bugzilla 2023024 — CacheIR fuse on RegExp
// reserved slot (`lastIndex`) never invalidated by Watchtower → JIT reads
// stale type.
//
// In-tree regression test: js/src/jit-test/tests/fuses/bug2023024.js
// (committed alongside the fix, 6e91b751bf989).
//
// Fix commit: 0d8fa12735898 — IRGenerator::canOptimizeConstantDataProperty in
// js/src/jit/CacheIR.cpp bailed out when the property being optimized lives
// in a JSClass reserved slot. Watchtower (the fuse-invalidation infrastructure)
// does not observe writes to reserved slots, so the per-object fuse never
// trips when the slot is rewritten, and subsequent Ion-compiled reads return
// the stale cached value.
//
// Here, `re.lastIndex = {}` seeds a RegExp reserved slot with an object,
// `obj.lastIndex` installs the CacheIR "ConstantDataProperty" stub (which
// attaches to the seeded object), the warmup loop monomorphizes it, then
// `re.exec(...)` rewrites the reserved slot to an Int32 inside the engine —
// but the fuse never invalidates. The final `read()` returns the stale cached
// object value while the actual slot now holds an Int32, producing type
// confusion that the ASAN+debug build catches as an assertion / MOZ_CRASH.

var re = /foo/g;
re.lastIndex = {};
var obj = Object.create(re);

function read() {
  return obj.lastIndex;
}

for (var i = 0; i < 50; i++) read();

re.exec("foofoofoo");

read();
