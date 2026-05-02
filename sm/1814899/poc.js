// CVE-2023-25751 / Bugzilla 1814899 — Ion OsiSpace codegen
//
// In-tree regression test: js/src/jit-test/tests/ion/bug1814899.js
// (commit 5ba1f3caa6dd8, 2023-04-25).
//
// Mechanism (fix d307cab06d56b, Iain Ireland, 2023-02-13):
//   Ion uses on-stack invalidation (OSI) points to let the GC patch the
//   return address of an active Ion frame to a bailout stub when jitcode
//   is invalidated. An OSI point is patched by overwriting a
//   PatchWrite_NearCallSize() span of bytes immediately before the
//   associated callJit / callWithABI. CodeGeneratorShared::ensureOsiSpace()
//   pads the code stream with nops so that span always fits.
//
//   The bug is that several call sites in CodeGenerator.cpp (callVMInternal,
//   visitCallNative, visitCallDOMNative, visitCallGeneric, visitCallKnown,
//   emitApplyGeneric, visitGetDOMProperty, visitSetDOMProperty,
//   emitIonToWasmCallBase) emitted `masm.callJit` / `masm.callWithABI`
//   without calling ensureOsiSpace() beforehand, and ensureOsiSpace() itself
//   in CodeGenerator-shared.cpp incorrectly advanced lastOsiPointOffset_ at
//   the end — the patch removes that erroneous advance and restricts the
//   invariant to actual markOsiPoint calls. Result: two consecutive OSI
//   points could sit closer together than PatchWrite_NearCallSize, so when
//   GC tried to patch the second one it would overwrite bytes belonging to
//   the first, corrupting Ion-compiled code and the subsequent bailout.
//
//   Triggering the pre-fix state requires two OSI points within a single
//   basic block close enough to collide: the test arranges a bar/foo
//   mutual-recursion chain inside a `with ({})` scope, uses `for (var s in
//   bar(x))` to inline through with-environment guards, and drops gczeal(14,1)
//   inside bar to provoke compacting GC patching of the Ion code.

function bar(x) {
  with ({}) {}
  switch (x) {
  case 1:
    foo(2);
    break;
  case 2:
    gczeal(14, 1);
    break;
  }
  return "a sufficiently long string";
}

function foo(x) {
  for (var s in bar(x)) { gczeal(0); }
}

with ({}) {}
for (var i = 0; i < 100; i++) {
  foo(0);
}
foo(1);
