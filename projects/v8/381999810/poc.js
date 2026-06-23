try {
  g0;
} catch (e) {
  this.g0 = new Proxy({}, {
    get(target, name) {}
  });
}
function f0(a0, a1, a2) {
  desc = Object.getOwnPropertyDescriptor(a0, a1);
  return typeof a2 === 'undefined' || typeof desc.value === a2;
}
function f1(a0, a1) {
  let v0 = [];
  for (let v1 of Object.getOwnPropertyNames(a0))
    if (f0(a0, v1, a1)) v0.push(v1);
  return v0;
}
function* f2(a0 = this, a1 = 0) {
  let v0 = f1(a0, 'object');
  for (let v1 of v0) {
    let obj = a0[v1];
    if (obj === a0) continue;
    yield obj;
    yield* f2(obj, a1 + 1);
  }
}
function f3(seed) {
  let v0 = [Object, Error, AggregateError, EvalError, RangeError, ReferenceError, SyntaxError, TypeError, URIError, String, BigInt, Function, Number, Boolean, Date, RegExp, Array, ArrayBuffer, DataView, Int8Array, Int16Array, Int32Array, Uint8Array, Uint8ClampedArray, Uint16Array, Uint32Array, Float32Array, Float64Array, BigInt64Array, BigUint64Array, Set, Map, WeakMap, WeakSet, Symbol, Proxy];
  for (let v1 of f2()) {
    v0.push(v1);
  }
  return v0[seed % v0.length];
}
(function (globalThis) {
  d8.file.execute('test/mjsunit/wasm/wasm-module-builder.js');
  let builder = new WasmModuleBuilder();
  let struct_type = builder.addStruct([makeField(kWasmI32, true)]);
  let array_type = builder.addArray(kWasmI32, true);
  builder.addFunction('MakeStruct', makeSig([], [kWasmExternRef])).exportFunc().addBody([kExprI32Const, 42, kGCPrefix, kExprStructNew, struct_type, kGCPrefix, kExprExternConvertAny]);
  builder.addFunction('MakeArray', makeSig([], [kWasmExternRef])).exportFunc().addBody([kExprI32Const, 2, kGCPrefix, kExprArrayNewDefault, array_type, kGCPrefix, kExprExternConvertAny]);
  let instance = builder.instantiate();
  globalThis.struct = instance.exports.MakeStruct();
  globalThis.array = instance.exports.MakeArray();
})(this);
function __corrupt_in_sandbox_addr(addr_in_sbx, byte_length, available_vars, rng) {
  let memory = new DataView(new Sandbox.MemoryView(addr_in_sbx, byte_length));
  for (let i = 0; i < byte_length; i += 4) {
    if (rng.nextInt(2) < 1) {
      let currentValue = memory.getUint32(i, true);
      if (currentValue & 0x1 && rng.nextInt(7) < 5) {
        if (rng.nextInt(11) < 3 && Sandbox.isValidObjectAt(ptr)) {} else {
            rng.nextInt(available_vars.length);
            continue;
        }
      }
      let randomValue = rng.nextUint32();
      memory.setUint32(i, randomValue, true);
    }
  }
}
function __corrupt_obj_in_sandbox(victim_obj, randseed, ...available_vars) {
  class SimpleRandom {
    constructor(seed) {
      const a = 1664525;
      const c = 1013904223;
      const m = Math.pow(2, 32);
      let state = seed;
      this.next = function () {
        state = (a * state + c) % m;
        return state / m;
      };
      this.nextInt = function (max) {
        return Math.floor(this.next() * max);
      };
      this.nextUint32 = function () {
        return Math.floor(this.next() * Math.pow(2, 32));
      };
    }
  }
  try {
    let obj_addr = Sandbox.getAddressOf(victim_obj);
    let obj_size = Sandbox.getSizeOf(victim_obj);
    let rng = new SimpleRandom(randseed);
    __corrupt_in_sandbox_addr(obj_addr, obj_size, available_vars, rng);
  } catch {}
}
function main() {
  v0 = 10;
  v1 = new WebAssembly.Memory({ initial: v0 });
  v5 = v1.v5;
  v5 = new Uint8Array(v5);
  __corrupt_obj_in_sandbox(f3(462015), 534874);
  WebAssembly.validate(v5);
}
main();
//flags: --fuzzing --sandbox-fuzzing