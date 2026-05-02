var wasm_code = new Uint8Array([0,97,115,109,1,0,0,0,1,12,2,80,0,95,1,99,116,0,96,0,1,116,3,2,1,1,4,12,1,64,0,100,0,1,1,2,251,1,0,11,7,8,1,4,109,97,105,110,0,0,10,12,1,10,0,65,0,37,0,251,2,0,0,11]);
var wasm_module = new WebAssembly.Module(wasm_code);
var wasm_instance = new WebAssembly.Instance(wasm_module);
var wasm_function = wasm_instance.exports.main;
var wasm_null = wasm_function();
%DebugPrint(wasm_null);

