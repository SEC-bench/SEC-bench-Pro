# Bugzilla 1814899 / CVE-2023-25751

**Title:** Ensure more OsiSpace
**Severity:** **sec-high** (MFSA 2023-09, Firefox 111)
**Component:** SpiderMonkey — IonMonkey — CodeGenerator / OSI
**Files touched:**
- `js/src/jit/CodeGenerator.cpp` (9 call sites)
- `js/src/jit/shared/CodeGenerator-shared.cpp` (1-line delete)

**Fix commit:** `d307cab06d56b4be62796b083b16feb86a47829c` (Iain Ireland, 2023-02-13, r=jandem)
**Test commit:** `5ba1f3caa6dd855ad9703944c4887069db5078aa` (Iain Ireland, 2023-04-25, r=jandem)
**Vulnerable revision:** `d307cab06d56b4be62796b083b16feb86a47829c~1`
**Phabricator:** D169274
**Bugzilla:** https://bugzilla.mozilla.org/show_bug.cgi?id=1814899 (sec-restricted)
**MFSA:** https://www.mozilla.org/en-US/security/advisories/mfsa2023-09/

## Background: OSI points

Ion codegen emits *OSI* (on-stack invalidation) points at locations where the GC or invalidation machinery may need to atomically re-route an active Ion frame's return address to a bailout stub. Patching is done by overwriting a single near-call instruction (`PatchWrite_NearCallSize()` ≈ 5 bytes on x86_64) in the code stream immediately before the associated `callJit` / `callWithABI`. To guarantee that 5-byte span always exists, `CodeGeneratorShared::ensureOsiSpace()` pads the stream with nops so that `masm.currentOffset() - lastOsiPointOffset_ >= PatchWrite_NearCallSize()`.

## Root cause

Two interacting defects:

1. **Missing `ensureOsiSpace()` before nine call sites.** `js/src/jit/CodeGenerator.cpp` emitted `masm.callJit` / `masm.callWithABI` inside the following routines without first calling `ensureOsiSpace()`:
   - `callVMInternal`
   - `visitCallNative`
   - `visitCallDOMNative`
   - `visitCallGeneric`
   - `visitCallKnown`
   - `emitApplyGeneric`
   - `visitGetDOMProperty`
   - `visitSetDOMProperty`
   - `emitIonToWasmCallBase`

2. **Bogus advance of the anchor.** `CodeGeneratorShared::ensureOsiSpace()` in `js/src/jit/shared/CodeGenerator-shared.cpp` ended with:

   ```cpp
   lastOsiPointOffset_ = masm.currentOffset();
   ```

   This advanced the invariant anchor **every time ensureOsiSpace was called**, even when no OSI point was actually emitted. Subsequent distance checks saw the span as already satisfied and skipped padding.

Together these let two OSI points sit closer together in the Ion code stream than `PatchWrite_NearCallSize()`. When the GC later patches the *second* OSI point, the 5-byte near-call instruction it writes overlaps the bytes of the *first* OSI point — corrupting that earlier instruction in-place. An Ion frame resuming through the corrupted region lands inside a mangled instruction, producing wildpointer dereferences (debug: `PatchableBackedge` / OSI iterator assertions; release: attacker-controlled control flow usable as a JIT miscompile primitive).

## Fix

```diff
 // js/src/jit/CodeGenerator.cpp, 9 sites, pattern:
 void CodeGenerator::visitCallGeneric(LCallGeneric* call) {
   ...
+  ensureOsiSpace();
   uint32_t callOffset = masm.callJit(objreg);
   markSafepointAt(callOffset, call);
 }

 // js/src/jit/shared/CodeGenerator-shared.cpp
 void CodeGeneratorShared::ensureOsiSpace() {
   ...
-  lastOsiPointOffset_ = masm.currentOffset();  // <-- wrong anchor advance
 }
```

`ensureOsiSpace()` now only reads `lastOsiPointOffset_`; the anchor is advanced exclusively by `markOsiPoint()` (the single source of truth for OSI emission).

## Trigger (`poc.js`)

The committed regression test ships as `poc.js` verbatim:

```js
function bar(x) {
  with ({}) {}
  switch (x) {
  case 1: foo(2); break;
  case 2: gczeal(14, 1); break;
  }
  return "a sufficiently long string";
}
function foo(x) {
  for (var s in bar(x)) { gczeal(0); }
}
with ({}) {}
for (var i = 0; i < 100; i++) foo(0);
foo(1);
```

The `with({})` scopes force Ion through the environment-guarded call path (`visitCallGeneric` specifically — the `foo → bar` call is a shape-guarded generic call). The warmup loop `for (var i = 0; i < 100; i++) foo(0)` tiers foo/bar into Ion. Then `foo(1)` takes the `case 1 → foo(2)` fall-through which hits `case 2 → gczeal(14,1)` inside bar. `gczeal(14, 1)` forces compacting GC on every allocation, triggering OSI-point patching of the live Ion frames just as the mutually-recursive call layout has produced two OSI points within the buggy-narrow window. The corrupted patch overlaps, and the next Ion resume crashes.

## Verification

```sh
bash spidermonkey/crash_check.sh 1814899
```

Expected: `CONFIMRED: ASAN_CRASH` or `CONFIMRED: ASSERTION_FAILURE` (OSI / Ion frame iterator invariant).
