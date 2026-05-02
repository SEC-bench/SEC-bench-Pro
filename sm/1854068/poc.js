gczeal(19, 1);
function wasmEvalText(str, imports) {
  let binary = wasmTextToBinary(str);
  try {
    m = new WebAssembly.Module(binary);
  } catch(e) {}
  return new WebAssembly.Instance(m, imports);
}
let WasmNonAnyrefValues = [];
let {ifNull} = wasmEvalText(`(module
  (func (export "ifNull") (param externref externref) (result externref)
    local.get 0
  )
)`).exports;
evaluate(`
  for (let i = 0; i < 10; ++i)
    ifNull(()=>{}) 
`);