# V8 Sandbox Bypass: ARR/W by sig confusion in WasmToJsWrapper tier-up with in-sandbox Tuple2 corruption

Issue URL: https://issues.chromium.org/issues/379140430
VRP-Reward: DUP
Date: Nov 15, 2024 03:28PM


### VULNERABILITY DETAILS

#### Summary

V8 sandbox bypass, arbitrary address read/write via WASM signature confusion in Wasm-to-JS wrapper tier-up with in-sandbox `Tuple2` corruption.

Similar bug class with [b/354408144](<https://issues.chromium.org/issues/354408144>) where we transitively trust a trusted-to-untrusted reference.

#### Details

For imported JS function that are exported and re-imported into another instances' table, `WasmImportData::origin` is set to a `Tuple2` containing `(instance, call_origin_index)`:

```
// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/wasm-objects.cc;drc=9b380b088e215784e8fc3f3e98ac256a474d2a75;l=1879
void WasmImportData::SetCrossInstanceTableIndexAsCallOrigin(
    Isolate* isolate, DirectHandle<WasmImportData> import_data,
    DirectHandle<WasmInstanceObject> instance_object, int entry_index) {
  DirectHandle<Tuple2> tuple = isolate->factory()->NewTuple2(
      instance_object, direct_handle(Smi::FromInt(entry_index + 1), isolate),
      AllocationType::kOld);
  import_data->set_call_origin(*tuple);
}
```

This is used to determine canonicalized signature index and target dispatch table entry to tier-up on `Runtime_TierUpWasmToJSWrapper()`:

```
// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/runtime/runtime-wasm.cc;drc=3b9350b6fc0274e1dbc7c0bd1cde7b9012e559f4;l=618
RUNTIME_FUNCTION(Runtime_TierUpWasmToJSWrapper) {
  // ...
  if (IsTuple2(*origin)) {
    auto tuple = Cast<Tuple2>(origin);
    // Note: This link is unsafe (via the untrusted WasmInstanceObject). We only
    // use it to find places to patch after tier-up, after additional checks.
    call_origin_instance_data =
        handle(Cast<WasmInstanceObject>(tuple->value1())->trusted_data(isolate),
               isolate);
    origin = direct_handle(tuple->value2(), isolate);
  }
  CHECK(IsSmi(*origin));
  Tagged<Smi> call_origin_index = Cast<Smi>(*origin);

  // Get the function's canonical signature index.
  // TODO(clemensb): Just get the sig_index based on WasmImportData::sig.
  wasm::CanonicalTypeIndex sig_index = wasm::CanonicalTypeIndex::Invalid();

  if (WasmImportData::CallOriginIsImportIndex(call_origin_index)) {
    int func_index = WasmImportData::CallOriginAsIndex(call_origin_index);
    const wasm::WasmModule* call_origin_module =
        call_origin_instance_data->module();
    sig_index = call_origin_module->canonical_sig_id(
        call_origin_module->functions[func_index].sig_index);
  } else {
    // Indirect function table index.
    int entry_index = WasmImportData::CallOriginAsIndex(call_origin_index);
    int table_count = call_origin_instance_data->dispatch_tables()->length();
    const wasm::WasmModule* call_origin_module =
        call_origin_instance_data->module();
    // We have to find the table which contains the correct entry.
    // ...
  }
  // Do not trust the `Tuple2` stored in `call_origin`. If we failed to find the
  // signature, crash early.
  SBXCHECK(sig_index.valid());
  // ...
}
```

There is a `SBXCHECK(sig_index.valid())` for the case where in-sandbox corruption results in the entry to be not found. However, the in-sandbox `Tuple2` object can still be corrupted to have an `call_origin_index` to represent a import table index (i.e. `WasmImportData::CallOriginIsImportIndex(call_origin_index)`).

In this case, we have a mismatch between `sig` and its assumed canonicalized signature index `sig_index`, resulting in using a different signature `sig` to as a tier-up compiled WasmToJsWrapper for the canonical index `sig_index` (and of course also using this for the modified target `call_origin_index`). This results in signature confusion and and thus arbitrary address read/writes outside of the V8 sandbox.

> Note that the funcref case (i.e. `IsWasmFuncRef(*origin)` branch) is also susceptible to type confusion by trusted `internal` handle transplant, but this requires racing against signature check in `CallRefIC()`. Similar bypasses might however work in other cases.

### VERSION

V8 Version: Tested on [5774972](<https://chromium.googlesource.com/v8/v8.git/+/5774972853d7bb893505377b0808af3535f12368>), exists up to ToT

### REPRODUCTION CASE

Repro added as `xinst-tierup-tuple2.js`. Run with `--sandbox-testing`.

### FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION

Type of crash: V8 sandbox bypass

### CREDIT INFORMATION

Reporter credit: Seunghyun Lee (@0x10n)


---

**#2 — cl...@chromium.org — Nov 15, 2024 05:41PM**

Thanks, we'll put this on the backlog of things to audit and fix (also see [https://crbug.com/369748454](<https://crbug.com/369748454>)). Nice to have a reproducer already!


---

**#3 — se...@gmail.com — Nov 15, 2024 05:52PM**

The linked issue [b/369748454](<https://issues.chromium.org/issues/369748454>) seems non-public unfortunately :(


---

**#4 — cl...@chromium.org — Nov 15, 2024 06:04PM**

Ah, yes, they are all access-restricted. I CCed you.


---

**#5 — ah...@google.com — Nov 16, 2024 02:08AM**

[Primary Security Shepherd] Handing over to the current V8/Wasm Security/Clusterfuzz Shepherd: [ishell@google.com](<mailto:ishell@google.com>)


---

**#6 — ch...@google.com — Mar 8, 2025 09:41PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
