// Bug 1885775 — WeakMap+Symbol cross-zone use-after-free.
// When a JS::Symbol is used as a WeakMap key, WeakMap::addImplicitEdges
// failed to add the sweep-group edge from the symbol's zone to the
// WeakMap's zone. Across multiple zones the two could end up in
// different sweep groups, so GC could collect the symbol while the
// WeakMap entry was still considered live — UAF in GCMarker.
// sec-high (csectype-uaf).
// Fix: 26125066c9f657eae22718920085779bb586b72b
//      (Yoshi Cheng-Hao Huang, 2024-03-26, r=jonco)
//
// Combined repro using both jit-test scenarios from the fix commit:
// - bug-1884927.js: WeakMap holds Debugger value across symbol key
// - bug-1885775.js: per-realm WeakMap+symbol churn under gcslice
// |jit-test| --enable-symbols-as-weakmap-keys

// Scenario A: Debugger value forces cross-zone interactions
for (var x = 0; x < 10000; ++x) {
    try {
        var m13 = new WeakMap;
        var sym = Symbol();
        m13.set(sym, new Debugger);
        startgc(1);
    } catch (exc) {}
}

// Scenario B: per-realm WeakMap+symbol+gcslice (forces sweep groups)
var code = `
var m58 = new WeakMap;
var sym = Symbol();
m58.set(sym, ({ entry16: 0, length: 1 }));
function testCompacting() {
  gcslice(50000);
}
testCompacting(2, 100000, 50000);
`;
for (var y = 0; y < 10000; ++y) {
    evaluate(code);
}
