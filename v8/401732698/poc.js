const kHeapObjectTag = 1;
let memory = new DataView(new Sandbox.MemoryView(0, 0x100000000));
function getPtr(obj) {
  return Sandbox.getAddressOf(obj) + kHeapObjectTag;
}
function setField(obj, offset, value) {
  memory.setUint32(obj + offset - kHeapObjectTag, value, true);
}

var v0 = {};
function f0() {
    setField(getPtr(v0), 4, getPtr(RangeError));
    Object.getOwnPropertyNames(v0);
}
f0();
for (var v8 = 0; v8 < 25; v8++) {
  v0["p" + v8] = 0;
}
f0();
//flags: --sandbox-fuzzing