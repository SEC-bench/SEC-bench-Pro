var log = typeof console !== "undefined" ? console.log.bind(console) : print;

// Module B: takes externref, USES IT as an object
// Calls a method or accesses a property → dereferences the pointer
var modBBytes = wasmTextToBinary(`(module
  ;; Import a JS function that will dereference the externref
  (import "env" "use" (func $use (param externref) (result i32)))
  (func (export "f") (param externref) (result i32)
    (call $use (local.get 0)))
)`);
var modB = new WebAssembly.Module(modBBytes);
var instB = new WebAssembly.Instance(modB, {
    env: {
        use: function(obj) {
            // This receives the raw i32 value as if it were an object
            // Accessing .x on a non-object (number 4) → type confusion
            return obj.x | 0;
        }
    }
});
var callBound = Function.prototype.call.bind(instB.exports.f);

var modABytes = wasmTextToBinary(`(module
  (type $t (func (param i32) (result i32)))
  (import "env" "imp" (func $imp (type $t)))
  (elem declare func $imp)
  (func (export "go") (param i32) (result i32)
    (call_ref $t (local.get 0) (ref.func $imp)))
)`);
var modA = new WebAssembly.Module(modABytes);
var instA = new WebAssembly.Instance(modA, { env: { imp: callBound } });

// i32(4) passed as externref → JS callback receives 4 (number, not object)
// → .x returns undefined → no crash via JS
// Need wasm-gc to deref directly

// Try: Module B uses struct.get on the externref cast to a struct type
log("test: " + instA.exports.go(4));
