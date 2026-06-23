// Flags: --wasm-wrapper-tiering-budget=1
d8.file.execute('test/mjsunit/wasm/wasm-module-builder.js');

(function TierUpIndirectlyCalledFunction() {
  let builder = new WasmModuleBuilder();
  let sig = builder.addType(kSig_v_v);
  let imp = builder.addImport('m', 'f', sig);
  builder.addTable(kWasmArrayRef, 1, 1)
  builder.addTable(kWasmFuncRef, 1, 1, [kExprRefFunc, 0, ])

  builder.addFunction('main', kSig_i_i).exportFunc().addBody([
    kExprLoop, kWasmVoid,
    kExprI32Const, 0,
    kExprCallIndirect, 0, 1,
    kExprLocalGet, 0,
    kExprI32Const, 1,
    kExprI32Sub,
    kExprLocalTee, 0,
    kExprI32Eqz,
    kExprI32Eqz,
    kExprBrIf, 0,
    kExprEnd,
    kExprI32Const, 0,
  ]);

  let instance = builder.instantiate({ m: { f: (x) => x } });
  // The argument is the iteration count: enough to tier up the wasm-to-js
  // wrapper.
  instance.exports.main(2);
})();