// CVE-2026-4702 / Bugzilla 2013560 — Force-return at yield opcode in generator
// Source: in-tree regression test js/src/jit-test/tests/debug/Frame-onStep-generator-resumption-04.js
// committed alongside the fix 1bd7ef2aa4bdb (Iain Ireland, 2026-02-13).
//
// Completion::fromJSFramePop in js/src/debugger/Debugger.cpp had three switch
// cases (InitialYield/Yield/Await) that asserted `!generatorObj->isClosed()`
// without first checking that GetGeneratorObjectForFrame returned non-null.
// When onStep returns {return: ...} at a frame paused between Generator and
// SetAliasedVar, generatorObj is null → null deref / MOZ_ASSERT failure
// in debug builds. The fix wraps the switch in `if (generatorObj && !closed)`
// and falls through to a normal Return otherwise.

// Don't crash on {return:} from onStep in a generator at a Yield.
//
// This test force-returns from each bytecode instruction in a generator.

let g = newGlobal({ newCompartment: true });
g.eval(`
function* gen() {
  yield 1;
}
`)

let dbg = new Debugger(g);

let targetSteps = 0;
let found = true;
dbg.onEnterFrame = (frame) => {
  let steps = 0;
  frame.onStep = () => {
    if (steps++ == targetSteps) {
      found = true;
      return { return: 0xdead };
    }
  }
}
dbg.uncaughtExceptionHook = () => undefined

while (found) {
  found = false;
  targetSteps++;
  for (var y of g.gen()) {}
}
