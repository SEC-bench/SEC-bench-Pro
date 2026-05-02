// Larger i16 array + many iterations under oomTest
let testModule = `(module
  (type $aI16 (array (mut i16)))
  (func $fcca (import "wasm:js-string" "fromCharCodeArray")
    (param (ref null $aI16) i32 i32) (result (ref extern)))
  (func (export "test") (param i32) (result externref)
    local.get 0
    (array.new_default $aI16)
    i32.const 0
    local.get 0
    call $fcca))`;
let m = new WebAssembly.Module(wasmTextToBinary(testModule), {builtins:['js-string']});
let inst = new WebAssembly.Instance(m, {});
for (let sz of [1, 2, 4, 8, 16, 32, 64, 100, 256, 1000, 4096]) {
  for (let k = 0; k < 10; k++) {
    try { oomTest(() => inst.exports.test(sz)); } catch(e) {}
  }
}
