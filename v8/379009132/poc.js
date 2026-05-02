d8.file.execute("test/mjsunit/wasm/wasm-module-builder.js");
const v5 = new WasmModuleBuilder();
const v7 = WebAssembly.Memory;
const o11 = {
    "initial": 35391,
    "maximum": 40722,
    "shared": false,
};
const v12 = new v7(o11);
const v15 = new DataView(v12.buffer);
const v17 = WebAssembly.Memory;
const o21 = {
    "initial": 57557,
    "maximum": undefined,
    "shared": false,
};
const v22 = new v17(o21);
new DataView(v22.buffer);
const v26 = v5.addType(kSig_i_iii);
const v27 = v5.nextTypeIndex(v15, WasmModuleBuilder, DataView);
v5.addType(makeSig([kWasmI32,kWasmI32,kWasmI32,kWasmI32,kWasmI32,kWasmI32,kWasmI32,kWasmI32,kWasmI32,kWasmI32,kWasmI32,kWasmI32], [wasmRefType(v27),kWasmI32,kWasmF32,kWasmI64,kWasmF64,kWasmI32]));
const v53 = v5.addType(kSig_v_v);
v5.addImportedMemory("imp_mem", "imp_mem0");
const v65 = v5.addImportedMemory("imp_mem", "imp_mem1");
const v67 = v5.addFunction(undefined, v26);
const v69 = v5.addFunction(undefined, v27);
v5.addMemory();
const v77 = v5.addTable(kWasmFuncRef).index;
const v80 = wasmI32Const(0);
const v89 = v5.addActiveElementSegment(v77, v80, []);
v5.addTag(v53);
const v106 = [kExprRefFunc,v69.index,kExprLocalSet,8,kExprRefFunc,v67.index,kExprLocalSet,9,kExprRefFunc,v67.index,kExprLocalSet,13,...wasmI32Const(3113)];
const v110 = wasmRefType(v26);
const v120 = wasmRefType(kWasmFuncRef);
const v123 = wasmRefType(v27);
const v139 = v67.addLocals(kWasmF64, 1).addLocals(kWasmI32, 3).addLocals(kWasmF64, 1).addLocals(v123, 1).addLocals(v120, 1).addLocals(kWasmF32, 1).addLocals(kWasmI32, 1).addLocals(kWasmF32, 1).addLocals(v110, 1);
const v140 = v139.addLocals(kWasmI32);
v140.addBody(v106);
const v143 = v67.index;
const v147 = v67.index;
const v167 = [kExprRefFunc,v143,kExprLocalSet,13,kExprRefFunc,v147,kExprLocalSet,14,kExprRefFunc,v69.index,...wasmI32Const(176),...wasmF32Const(1, kExprRefFunc),...wasmI64Const(-752406821444559606n),...wasmF64Const(1, kWasmI32, v147, 3113, v89),kExprI32Const,3];
const v171 = wasmRefType(v26);
v69.addLocals(kWasmI32, 1).addLocals(v171, 2).addLocals(kWasmF64).addBody(v167);
v5.exportMemoryAs("exp_mem1", v65);
v5.addExport("exp_func1", v69.index);
v5.addExport();
const o187 = {
    "imp_mem1": v22,
    "imp_mem0": v12,
};
const o188 = {
    "imp_mem": o187,
};
const v192 = [kWasmF64,kWasmF64,kWasmF64];
const o193 = {
    "builtins": v192,
};
const v194 = v5.instantiate(o188);
const v197 = v194.exports;
v197.exp_func1();
const v200 = v197.exp_func1();
v200.toString();