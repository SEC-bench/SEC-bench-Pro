// CVE-2026-2785 / Bugzilla 2019813 — Wasm imported memory off-by-one importIndex
// Source: in-tree regression test js/src/jit-test/tests/wasm/builtin-modules/bug2019813.js
// committed alongside the fix 9ef71fcf90d12 (Ben Visness, 2026-02-27).
//
// AddImport() in js/src/wasm/WasmValidate.cpp set the imported memory's
// `importIndex` AFTER calling moduleMeta->imports.emplaceBack(), so the
// recorded index pointed one past the just-added import. With a single
// imported memory plus a builtin function import, downstream code that
// resolved the memory via imports[importIndex] read out-of-bounds /
// wrong slot → assertion or ASAN heap-buffer-overflow.

const bytes = wasmTextToBinary(`(module
  (import "wasm:js-string" "length" (func (param externref) (result i32)))
  (import "m" "mem" (memory 0))
)`);

const mod = new WebAssembly.Module(bytes, { builtins: ["js-string"] });
const mem = new WebAssembly.Memory({ initial: 0 });
new WebAssembly.Instance(mod, { m: { mem } });
