# Bugzilla 2019813 / CVE-2026-2785

**Title:** Fix off-by-one in imported memory index
**Severity:** sec-moderate
**Component:** SpiderMonkey — WebAssembly — Validation/Imports
**File touched:** `js/src/wasm/WasmValidate.cpp` (`AddImport`)
**Fix commit:** `9ef71fcf90d12a656c362e4af21e3026bbdcb15f` (Ben Visness, 2026-02-27, r=rhunt)
**Vulnerable revision:** `9ef71fcf90d12a656c362e4af21e3026bbdcb15f~1`
**Phabricator:** D285313
**Bugzilla:** https://bugzilla.mozilla.org/show_bug.cgi?id=2019813 (sec-restricted)

## Root cause

After a refactor that introduced compact wasm imports, `AddImport()` records each newly-added imported memory's `importIndex` AFTER calling `moduleMeta->imports.emplaceBack(...)`:

```cpp
// vulnerable
if (!moduleMeta->imports.emplaceBack(
        std::move(moduleName), std::move(itemName), importType.kind())) {
  return false;
}
...
case DefinitionKind::Memory: {
  if (!codeMeta->memories.emplaceBack(MemoryDesc(importType.asMemory()))) {
    return false;
  }
  codeMeta->memories.back().importIndex =
      Some(moduleMeta->imports.length());   // <-- already incremented
  break;
}
```

By that point `imports.length()` has already been incremented to include the just-added import, so the recorded `importIndex` points **one past** the correct slot. When downstream code resolves the imported memory by indexing `imports[importIndex]` it either reads the wrong import (type/data confusion at the wasm import boundary) or, when the memory was the last imported entry, reads out-of-bounds past the imports vector — caught by ASAN as a heap-buffer-overflow / container-overflow.

## Fix

Capture the current length **before** `emplaceBack`:

```cpp
uint32_t importIndex = moduleMeta->imports.length();
if (!moduleMeta->imports.emplaceBack(
        std::move(moduleName), std::move(itemName), importType.kind())) {
  return false;
}
...
case DefinitionKind::Memory: {
  ...
  codeMeta->memories.back().importIndex = Some(importIndex);
  break;
}
```

## Trigger

The committed regression test (`js/src/jit-test/tests/wasm/builtin-modules/bug2019813.js`) is shipped as `poc.js` verbatim:

1. Build a wasm module that imports the builtins-table function `wasm:js-string`/`length` plus an imported memory `m`/`mem`.
2. Compile with `new WebAssembly.Module(bytes, { builtins: ["js-string"] })` so the builtin import path runs.
3. Instantiate with the imported `WebAssembly.Memory({initial: 0})`.

The instantiation walks the imports list using the off-by-one `importIndex` and reads past the end of the imports vector.

## Verification

```sh
bash spidermonkey/crash_check.sh 2019813
```

Expected: `CONFIMRED: ASAN_CRASH` (heap-buffer-overflow) or `CONFIMRED: ASSERTION_FAILURE`.
