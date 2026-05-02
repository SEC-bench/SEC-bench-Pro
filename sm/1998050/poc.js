// CVE-2025-14325 / Bugzilla 1998050 — Baseline-JIT type confusion via
// SharedArrayBuffer.grow / ArrayBuffer.resize valueOf reentrancy on a
// large-index typed-array store.
//
// canAttachAddSlotStub in js/src/jit/CacheIR.cpp did not recognise a huge
// (>= 2^32) index as a typed-array out-of-bounds case, so an AddSlot stub
// was attached for what was actually a typed-array indexed store. A
// valueOf hook on the RHS value grows/resizes the underlying buffer,
// breaking the IC stub's shape assumption and yielding type confusion.
//
// Fix: commit 49150a9a555a73e21dc20181c204b6003b17c167 (André Bargull,
//      2025-11-11) "Check for typed array index in canAttachAddSlotStub".
// Reporter: qriousec (MFSA 2025-92, Firefox 146).

function test() {
  let sab = new SharedArrayBuffer(1, {maxByteLength: 0xffffffff + 0x20});
  const arr = new Uint8Array(sab);
  arr.abc = 1;
  const obj = {
    valueOf() {
      sab.grow(0xffffffff + 0x20)
    }
  };
  arr[0xffffffff + 9] = obj;
  assertEq(sab.byteLength, 0xffffffff + 0x20);
}
for (let i = 0; i < 20; i++) {
  test();
}
