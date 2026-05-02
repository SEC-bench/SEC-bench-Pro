// CVE-2024-9403 / Bugzilla 1917807 — Wasm JIT entry stub mismatched the
// frame footer alignment for return_call_indirect with multi-arg targets.
// Subsequent frame walk reads garbage, MOZ_CRASH on footer type check.
// Fix: 16781a13b5ecce172cf06a272f1cee629c9afee2 (jandem reviewers).
function processWAST(source) {
    let modBuf = wasmTextToBinary(source);
    let module = new WebAssembly.Module(modBuf);
    let instance = new WebAssembly.Instance(module);
    for (let i = 0; i < 10; ++i) {
        try { instance.exports.odd(); } catch (e) {}
    }
}
processWAST(`(module (table 2 2 funcref)
(elem (i32.const 0) $odd $odd)
(type $t (func (param) (result i32)))
(func $odd (export "odd") (param i32 i32 i32 i32 i32 i32 i32) (result i32)
  (return_call_indirect (type $t) (i32.const 1) (local.get 1))))`);
