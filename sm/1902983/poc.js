// Bug 1902983 — Wasm bailout-data UAF after iterating Wasm frames.
// JSJitFrameIter held a BailoutInfo* into stack memory tied to a Wasm
// frame. After iterating past the Wasm frames the memory was reused,
// leaving the iterator pointing at freed data. Follow-up to bug 1900523
// (only JSJitToWasm was fixed; FrameType::Exit path remained vulnerable).
// Fix: d5df70357db3d244669ed3147467e5b7ade0f51c (Jan de Mooij, 2024-06-19).
//
// Official jit-test from commit d5df70357db3
// (js/src/jit-test/tests/ion/bug1902983.js).
// |jit-test| --fast-warmup; --gc-zeal=21,100; skip-if: !wasmIsSupported()
let counter = 0;
function g() {
    counter++;
    const y = BigInt.asIntN(counter, -883678545n);
    const z = y >> y;
    BigInt.asUintN(2 ** counter, 883678545n);
    try { g(); } catch (e) { }
}
function f() {
    for (let i = 0; i < 5; i++) {
        for (let j = 0; j < 30; j++) { }
        Promise.allSettled().catch(e => null);
        counter = 0;
        g();
    }
}
const binary = wasmTextToBinary(`(module (import "m" "f" (func $f)) (func (export "test") (call $f)))`);
const mod = new WebAssembly.Module(binary);
const inst = new WebAssembly.Instance(mod, { m: { f: f } });
for (let i = 0; i < 100; i++) { }
for (let i = 0; i < 5; i++) {
    inst.exports.test();
}
