function wasmEvalText(t, imp) {
  var wasm = wasmTextToBinary(t)
  var mod = new WebAssembly.Module(wasm);
  var ins = new WebAssembly.Instance(mod, imp);
  return ins;
}

const ins0 = wasmEvalText(
`(module
   (import "ns1" "gc" (func $gc))
   (func $f1 (export "f1") (param externref ) 
     call $gc
   )
 )`, {"ns1": {gc,},});

const ins1 = wasmEvalText(
`(module
  (type $t1 (func (param externref)))
  (import "ns2" "ext1" (global $ext1 externref))
  (import "x" "f1" (func  $f1 (param externref)))
  (elem declare func $f1)
  (func $f0 (export "f0") (result externref)
    (local $xx externref)
    (local.tee $xx (global.get $ext1))
    (local.get $xx)
    ;; at this point there are two pointers to $ext1 on the stack
    (ref.func $f1)
    (call_ref $t1)
  )
)`, {
  "ns2": {ext1: {}},
  x: {f1:ins0.exports.f1}
});

const res = ins1.exports.f0();
