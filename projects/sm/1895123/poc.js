
(function t() {
  timeout(.0001, () => {
    gc(); t(); return true;
  });
})();


function wasmEvalText(t, imp) {
  var wasm = wasmTextToBinary(t)
  var mod = new WebAssembly.Module(wasm);
  var ins = new WebAssembly.Instance(mod, imp);
  return ins;
}

var ins = wasmEvalText(`(module
  (import "" "f" (func $f (param externref i32) (param f64)))
  (export "main" (func $f))
)`, {"": {f: async (i) => { },},});


while (1) {
  for (let i = 0; i < 100; i++)
     ins.exports.main(void 0);
}
