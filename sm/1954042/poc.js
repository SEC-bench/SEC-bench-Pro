function wasmEvalBinary(binary, imports, compileOptions) {
    try {
        m = new WebAssembly.Module(binary, compileOptions);
    } catch(e) {}
}
function wasmEvalText(str, imports, compileOptions) {
    return wasmEvalBinary(wasmTextToBinary(str), imports, compileOptions);
};
function testNewStruct() {
  let { newStruct, newArray } = wasmEvalText(`
    (module
    (type $s (sub (struct)))
    (func (export "newStruct") (result anyref)
        struct.new $s)
    )
  `).exports;
}
oomTest(testNewStruct);