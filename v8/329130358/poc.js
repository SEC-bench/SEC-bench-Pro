try {
  d8.file.execute('test/mjsunit/wasm/wasm-module-builder.js');
} catch (e) {}
const v1 = new WasmModuleBuilder();
const v2 = v1.addType(kSig_i_i);
const v3 = v1.addImportedGlobal('m', 'val', kWasmAnyFunc);
try {
  v1.addFunction('main', v2).addBody([kExprLocalGet, 0, kExprGlobalGet, v3, kGCPrefix, kExprRefCast, v2, kExprCallRef, v2]).exportFunc();
} catch (e) {}
const v4 = v1.toModule();
function f1(v18) {
  try {
    gc();
  } catch (v20) {}
}
const v5 = new WebAssembly.Function({
  parameters: ['i32'],
  results: ['i32']
}, f1);
let v6 = new WebAssembly.Instance(v4, {
  m: {
    val: v5
  }
});
v6.exports.main(3);
v6.exports.main(3);
//flags: --expose-gc --jit-fuzzing --wasm-staging
