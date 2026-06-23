function patchSrc(src, exc) {
  try {
    let srcParts = src.split("\n");
    let srcLine = "d262 = undefined;"
    srcParts.splice(exc.lineNumber - 1, 0, srcLine);
    return srcParts.join("\n");
  } catch(exc) {}
}
initGlobals = new Set(Object.keys(this));
loadFile(`
//xorefuzz-dcd-selectmode
/*---
description: SingleNameBinding does assign name
defines: [DETACHBUFFER]
---*/
function DETACHBUFFER(buffer) {
  d262.detachArrayBuffer(buffer);
}
assert = initGlobals;
assert.sameValue = DETACHBUFFER;
`);
loadFile(`
//xorefuzz-dcd-evaluate
// GENERATED, DO NOT EDIT
// file: temporalHelpers.js
// Copyright (C) 2021 Igalia, S.L. All rights reserved.
// This code is governed by the BSD license found in the LICENSE file.
/*---
---*/
C55 = class {
  [1 * 1] = () => {};
};
c29 = new C55();
assert.sameValue();
`);
function loadFile(lfVarx) {
    try {
      evaluate(lfVarx);
    } catch (lfVare) {
      if (lfVare.toString().indexOf("is not defined") >= 0 || lfVare.toString().indexOf("is undefined") >= 0) {
        newSrc = patchSrc(lfVarx, lfVare);
        loadFile(newSrc);
      }
    }
}