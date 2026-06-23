# Bugzilla 1791520 / CVE-2022-42928

**Title:** Missing GC keep-alive on TypedArray across BigInt allocation in Ion JIT-compiled BigInt64Array element ops
**Severity:** sec-high (MFSA 2022-46, Firefox 107)
**Component:** SpiderMonkey — Ion — `js/src/jit/IonAnalysis.cpp`
**Fix commit:** `c224760a76fa4c1f59d4bb82d3e69d74503dfc83` ("Bug 1791520: Add some keep alive annotations. r=jandem", André Bargull, 2022-10-06)
**Test commit:** `557d0219977ec65dca21449915b1db50e7d85507` ("Bug 1791520: Add tests. r=jandem", André Bargull, 2023-01-18)
**GC-unsafe instrumentation:** `a40af352d29a63054e12d2ae2519ec970f2d8580` ("Bug 1791520: Add GC unsafe region instructions for JIT code. r=jandem", André Bargull, 2023-01-18)
**Vulnerable revision:** `c224760a76fa4c1f59d4bb82d3e69d74503dfc83~1`
**Reporters:** Samuel Groß, Carl Smith

## Summary

Ion's lowering for `BigInt64Array` indexed and atomic ops generates MIR
nodes (`MLoadUnboxedScalar`, `MAtomicTypedArrayElementBinop`) that
return their `int64` result through `CreateBigIntFromInt64`. The
`createFromInt64` helper allocates a fresh `JS::BigInt` in the
nursery; if the nursery is full, a minor GC runs synchronously
*inside* the alloc. Pre-fix, the JIT-emitted code held the
`TypedArrayObject` (and its data pointer) in a register without
rooting it across the BigInt allocation. The minor GC could move or
free the typed array, leaving the register pointing at freed memory,
and the next instruction read/wrote through the dangling pointer.

## Fix

`IonAnalysis.cpp` is taught to walk the MIR graph and inject
`MKeepAliveObject` for the typed-array operand of every
BigInt-returning node whose result feeds a GC-allocating call. The
keep-alive ensures the typed array is live across the alloc, so the
nursery can't move/free it without updating the rooted reference.

## Trigger (`poc.js`, in-tree jit-test `bug1791520.js`)

```js
function testAtomicsAdd() {
  var x;
  for (var i = 0; i < 100; ++i) {
    var a = new BigInt64Array(2);
    x = Atomics.add(a, i & 1, 1n);
  }
  return x;
}
// ... 8 more parallel tests for sub/and/or/xor/exchange/compareExchange/load/element

gczeal(14);
testAtomicsAdd(); /* ... */
```

`gczeal(14)` (CompactNursery) forces a minor GC at every nursery
allocation, deterministically reproducing the dangling typed-array
pointer.

## Expected crash

ASAN **SEGV** at `js::Nursery::IsWriteableAddress` (Nursery.cpp) /
SEGV in JIT code reading a freed `TypedArrayObject` data pointer
right after `CreateBigIntFromInt64` returns. Equivalent to a heap
use-after-free.

## Verification

```sh
docker build -t hwiwonlee/sm.x86_64:1791520 spidermonkey/1791520
bash spidermonkey/crash_check.sh 1791520
```

Expected: `CONFIMRED: ASAN_CRASH`.
