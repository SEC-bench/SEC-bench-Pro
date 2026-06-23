modBuf = wasmTextToBinary(`
(module
  (type (;0;) (func))
  (func (;0;) (type 0)
  )
  (table (;0;) 219 640821 (ref null 0) ref.func 0)
  (export "" (table 0))
)
`);
imports = {};
args = [1];
setPrefValue("wasm_lazy_tiering_synchronous", true);
setPrefValue("wasm_lazy_tiering_level", 9);
setPrefValue("wasm_lazy_tiering", true);
try { module = new WebAssembly.Module(modBuf, { builtins: ["js-string"] }); } catch(exc) {}
try { instance = new WebAssembly.Instance(module, imports); } catch(exc) {} 
el = instance.exports[""];
eel = el.get(0);
try {
  tmp = function() {
    for (let j = 0; j < 23; ++j) {
      try {
        eel(...args);
      } catch(exc) {}
    }
  };
  evaluate("tmp();");
} catch(exc) {}