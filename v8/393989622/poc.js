let sbx_memory = new DataView(new Sandbox.MemoryView(0, 0x100000000));
const s2 = "asdq";
const addr = Sandbox.getAddressOf(s2);

// Make the string a TwoByteString
sbx_memory.setUint32(addr, 0x8d, true);
// Set the length of the string.
sbx_memory.setUint32(addr + 8, 0x7ffffffb, true);

"asdf".localeCompare(s2)

