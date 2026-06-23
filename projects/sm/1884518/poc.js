var wasm_code = wasmTextToBinary(`
(module
  (tag $a)
  (func $f0
    ref.null i31
    ref.cast anyref
    try_table $l7 (param anyref)
      (catch_all 0)
      try
        throw $a
      delegate 0
      drop
    end
  )
  (export "main" (func 0))
)
`);
var wasm_module = new WebAssembly.Module(wasm_code);
var wasm_instance = new WebAssembly.Instance(wasm_module);
var f = wasm_instance.exports.main;
f();
print("exit happy :)")
