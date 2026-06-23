# Bugzilla 1914009

**Title:** Wasm baseline `emitReturnCallRef` mishandles multi-value stack results, corrupting the tail-call frame
**Severity:** sec-high (MFSA 2024-50 cluster, Firefox 130/131)
**Component:** SpiderMonkey — Wasm baseline — `js/src/wasm/WasmBaselineCompile.cpp`
**Fix commit:** `d942bcd55a236074e4fd0601a103e8c252e56899` (Ryan Hunt et al., 2024-08)
**Vulnerable revision:** `d942bcd55a236074e4fd0601a103e8c252e56899~1`

## Summary

The baseline compiler's `emitReturnCallRef` lowers the wasm
`return_call_ref` instruction (a tail call through a function
reference). When the callee's signature returns multiple values
(e.g. `(result i32 f32)`), the baseline tail-call sequence must
shuffle all stack-passed results into the caller's outgoing-results
area before jumping to the new function. Pre-fix, the lowering
treated the result count as if it were one, so for any multi-value
target it left part of the result region uninitialised and overwrote
adjacent slots that still belonged to the caller's frame footer.

After the tail call, the next frame walk (return, trap, or stack
capture) reads through the corrupted footer and either jumps to a
controlled return address or faults dereferencing an attacker-shaped
pointer.

## Fix

`emitReturnCallRef` is rewritten to use the same
multi-value-aware result-shuffling helper as ordinary `call_ref`,
ensuring all stack results are placed into their final slots before
the tail jump and that no caller frame slot is clobbered.

## Trigger (`poc.js`)

The PoC instantiates a one-function wasm module that does:

```wasm
(type $t1 (func (param externref i32 i32 f64 f64 f32 i64) (result i32 f32)))
(func $f0 (export "f0") (result i32 f32)
   ... materialise 7 args ...
   ref.func $f1
   return_call_ref $t1)
```

`$f1` is an imported JS function returning two values
(`[1, 1.125]`). Calling `f0()` from JS triggers the broken tail-call
lowering, corrupts the frame, and faults on the next dispatch.

This is the upstream jit-test reproducer reduced from gecko commit
`9ad11169dda1`.

## Expected crash

ASAN SEGV at PC `0x000000000001` (jump to a corrupted return
address). The harness records this as a "nested bug in the same
thread, aborting." trace because the second fault is inside ASAN's
own unwinder.

## Verification

```sh
docker build -t hwiwonlee/sm.x86_64:1914009 spidermonkey/1914009
bash spidermonkey/crash_check.sh 1914009
```

Expected: `CONFIMRED: ASAN_CRASH`.
