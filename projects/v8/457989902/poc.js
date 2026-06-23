// Minimal testcase to cause a dcheck failure
function createArray(x) {
    return new Array(x, 1.1);
}

let dv = new DataView(new ArrayBuffer(8));
dv.setUint32(0, 0xFFF7FFFF, true);
dv.setUint32(4, 0xFFF7FFFF, true);
let x = dv.getFloat64(0, true);
% PrepareFunctionForOptimization(createArray);
createArray(x);
% OptimizeMaglevOnNextCall(createArray);
let arr = createArray(x);
//%DebugPrint(arr);
print(arr);
