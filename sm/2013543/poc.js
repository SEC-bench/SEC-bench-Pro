// Bug 2013543 — OptimizeIteratorIndices block-level vs instruction-level
// dominance mismatch in js/src/jit/IonAnalysis.cpp.
// Pre-fix used otherIter->block()->dominates(ins->block()) which ignores
// intra-block ordering; the fix uses otherIter->dominates(ins) for proper
// instruction-level dominance. Deterministic Ion debug assertion on every
// compile once warmup reaches Ion-compile threshold.
//
// Fix: commit bf98f12eb281d60b77984d9497a08209c69ad8d8

function foo(obj1, obj2) {
  var keys1 = Object.keys(obj1);
  var val = obj2[keys1[0]];
  var keys2 = Object.keys(obj2);
  return val;
}

var objs = [];
for (var i = 0; i < 30; i++) {
  var o = {};
  for (var j = 0; j <= i; j++) {
    o["p" + j] = j + 1;
  }
  objs.push(o);
}

for (var i = 0; i < 5000; i++) {
  var o = objs[i % objs.length];
  foo(o, o);
}
