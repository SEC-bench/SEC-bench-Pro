loadFile(``);
loadFile(``);
loadFile(`
  var lfClass = new LFC1695437225();
`);
loadFile(`
  (function(global) {
    global.assertDeepEq = (function(){})();
  })(this);
`);
loadFile(`
  log = "";
`);
loadFile(`
  for (let invalid of (log("lhs before name a"), "a")) {}
`);
loadFile(`}`);
loadFile(`
  (function(global) {
    global.completesNormally = function completesNormally(code) {}
  })(this);
`);
loadFile(`
  for (let order = 0; order < 16; order++) {
    gc();
    setMark = undefined;
  }
`);
loadFile(`
  function f80() {}
  gc();
  delete Math
`);
loadFile(`
  for (const name of ["x", "y"]) {
    present = undefined;
    this[name] = function() {};
  }
`);
function loadFile(lfVarx) {
  try {
    evaluate(lfVarx);
  } catch (lfVare) {}
  Math = undefined;
}