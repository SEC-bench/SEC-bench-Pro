# Bugzilla 2013560 / CVE-2026-4702

**Title:** Handle force return at yield opcodes
**Severity:** sec-moderate (MFSA 2026-20)
**Component:** SpiderMonkey — Debugger
**File touched:** `js/src/debugger/Debugger.cpp` (`Completion::fromJSFramePop`)
**Fix commit:** `1bd7ef2aa4bdb9e584d192049cf5cba23a1e8ace` (Iain Ireland, 2026-02-13, r=mgaudet)
**Vulnerable revision:** `1bd7ef2aa4bdb9e584d192049cf5cba23a1e8ace~1`
**Phabricator:** D283332
**Bugzilla:** https://bugzilla.mozilla.org/show_bug.cgi?id=2013560 (sec-restricted)
**MFSA:** Mozilla Foundation Security Advisory 2026-20

## Root cause

`Completion::fromJSFramePop` builds a `Completion` describing the popped frame's outcome. For generator/await frames it dispatches on the current bytecode op:

```cpp
// vulnerable
Rooted<AbstractGeneratorObject*> generatorObj(
    cx, GetGeneratorObjectForFrame(cx, frame));
switch (JSOp(*pc)) {
  case JSOp::InitialYield:
    MOZ_ASSERT(!generatorObj->isClosed());
    return Completion(InitialYield(generatorObj));
  case JSOp::Yield:
    MOZ_ASSERT(!generatorObj->isClosed());
    return Completion(Yield(generatorObj, frame.returnValue()));
  case JSOp::Await:
    MOZ_ASSERT(!generatorObj->isClosed());
    return Completion(Await(generatorObj, frame.returnValue()));
  default:
    return Completion(Return(frame.returnValue()));
}
```

The pre-fix code commented that "by checking the opcode first we eliminate" the case where `GetGeneratorObjectForFrame` returns `nullptr`. That assumption is false: when a debugger force-returns from `onStep` at a frame paused **between** `JSOp::Generator` and `JSOp::SetAliasedVar`, the generator object slot is still null even though the surrounding op is `JSOp::Yield` / `JSOp::Await` / `JSOp::InitialYield`. The switch then dereferences `generatorObj` to call `isClosed()` and constructs a `Completion::Yield(nullptr, ...)`. Result: `MOZ_ASSERT(!generatorObj->isClosed())` fires (debug) or null-pointer dispatch (release).

## Fix

Wrap the switch in a non-null + not-closed guard, and fall through to a normal `Return` Completion when the generator object isn't yet established:

```cpp
if (generatorObj && !generatorObj->isClosed()) {
  switch (JSOp(*pc)) {
    case JSOp::InitialYield:
      return Completion(InitialYield(generatorObj));
    case JSOp::Yield:
      return Completion(Yield(generatorObj, frame.returnValue()));
    case JSOp::Await:
      return Completion(Await(generatorObj, frame.returnValue()));
    default:
      break;
  }
}
return Completion(Return(frame.returnValue()));
```

## Trigger

The committed regression test (`js/src/jit-test/tests/debug/Frame-onStep-generator-resumption-04.js`) is shipped as `poc.js` verbatim:

1. Define `function* gen() { yield 1; }` in a new compartment global.
2. Attach a `Debugger`. `onEnterFrame` installs `frame.onStep`.
3. `onStep` returns `{return: 0xdead}` after `targetSteps` steps.
4. Loop, incrementing `targetSteps`, iterating `g.gen()` each pass — eventually one iteration force-returns at the JSOp::InitialYield/Yield op while `generatorObj` is still null.

## Verification

```sh
bash spidermonkey/crash_check.sh 2013560
```

Expected: `CONFIMRED: ASSERTION_FAILURE` (null-pointer assertion in `Completion::fromJSFramePop`) or `CONFIMRED: ASAN_CRASH`.
