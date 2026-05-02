modBuf = new Uint8Array([
  0,97,115,109,1,0,0,0,1,23,2,80,0,96,0,1,125,78,3,94,120,
  0,80,0,95,0,80,1,0,96,0,1,125,6,7,1,99,0,0,208,3,11,7,4,
  1,0,3,0,9,4,1,5,112,0
]);
module = new WebAssembly.Module(modBuf);
new WebAssembly.Instance(module, {});