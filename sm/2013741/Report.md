# Bugzilla 2013741 / CVE-2026-2767

**Title:** Clean up misleading comments in `array.fill` (substantive change: missing pre-write barrier)
**Severity:** **sec-high** (MFSA 2026-15 — "Use-after-free in the JavaScript: WebAssembly component")
**Component:** SpiderMonkey — WASM Baseline Compiler — GC arrays
**File touched:** `js/src/wasm/WasmBaselineCompile.cpp` (`BaseCompiler::emitArrayFill`)
**Fix commit:** `d867a6f69b9f026674f2e846572748818a61a41b` (Ben Visness, 2026-02-09, r=rhunt)
**Vulnerable revision:** `d867a6f69b9f026674f2e846572748818a61a41b~1`
**Phabricator:** D281627
**Bugzilla:** https://bugzilla.mozilla.org/show_bug.cgi?id=2013741 (sec-restricted)
**MFSA:** https://www.mozilla.org/en-US/security/advisories/mfsa2026-15/

## Root cause

The WASM Baseline Compiler's `emitArrayFill` emits an inline loop that stores `value` into every element of a WASM GC array. The per-element store is generated via `emitGcArraySet(...)`, and the call passed `PreBarrierKind::None` for the pre-write barrier kind:

```cpp
// vulnerable
if (!emitGcArraySet(rp, rdata, numElements, arrayType, value,
                    PreBarrierKind::None, PostBarrierKind::Imprecise)) {
  return false;
}
```

For SpiderMonkey's incremental marker, a snapshot-at-the-beginning invariant requires that any write that *overwrites an existing reference* in a marked-or-marking cell must first record the old reference (pre-write barrier) so the marker can mark it during the same incremental GC. `array.fill` does exactly that for every element: each store overwrites whatever reference was in the slot before. With `PreBarrierKind::None` the JIT skips the barrier entirely.

When an incremental major GC is in progress and the mutator runs an `array.fill` on a reference-typed GC array, the replaced references vanish from the marker's work list. The marker subsequently sweeps cells that are still referenced from the mutator stack or other live heap edges → those cells become dangling → next access is a heap-use-after-free.

The post-write barrier (`PostBarrierKind::Imprecise`) is correctly emitted, so the bug is strictly on the pre-barrier side. The misleading "Skip initialization if numElements = 0" comment in the original code suggested this loop was a no-overwrite *initialization* fill (where pre-barriers are unnecessary), but `array.fill` is reachable on already-initialized arrays.

## Fix

```cpp
// fixed
if (!emitGcArraySet(rp, rdata, numElements, arrayType, value,
                    PreBarrierKind::Normal, PostBarrierKind::Imprecise)) {
  return false;
}
```

Single-token swap; `emitGcArraySet` now emits the standard pre-write barrier sequence (load old slot value, isCell check, `PreWriteBarrierWithEmit` call). The commit also rewords the loop comments — the message intentionally focuses on comment cleanup because the bug was sec-restricted at the time of landing.

## Trigger (`poc.js`)

Reverse-engineered from the diff:

1. Build a WASM module that exports
   - `make(n)` → returns a `(ref (array (mut externref)))` of length `n`
   - `fill(a, v, n)` → wraps `array.fill` over the array
2. Allocate the array, seed every slot with a live JS object via `fill(arr, seed, 64)`.
3. Immediately overwrite every slot with a different JS object via `fill(arr, replacement, 64)`. Each per-element store hits the missing pre-write barrier site.
4. The PoC enables `gczeal(4, 1)` (Pre-Write Barrier Verifier). Under that mode SpiderMonkey records, for every barrier-less ref store on a marked cell, an assertion failure / `MOZ_CRASH` from the barrier verifier — directly fingering `emitArrayFill` as the offending site.

The PoC also runs 16 additional `fill(arr, freshObj, 64)` rounds inside a loop to amortise allocation pressure, ensuring incremental marking is mid-flight when at least one `array.fill` runs.

## Verification

```sh
bash spidermonkey/crash_check.sh 2013741
```

Expected: `CONFIMRED: ASSERTION_FAILURE` (pre-write barrier verifier) or `CONFIMRED: ASAN_CRASH`.
