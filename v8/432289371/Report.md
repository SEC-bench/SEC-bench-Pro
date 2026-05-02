# V8 sandbox bypass due to recreating funcref for imported wasm function

Issue URL: https://issues.chromium.org/issues/432289371
VRP-Reward: 5000
Date: Jul 17, 2025 03:24PM


**SUMMARY**

When importing a corrupted `WasmSuspendingObject` with `callable` is a wasm function lead to wrong func_index then reexporting it -> signature confusion

**DETAILS**

When importing a wasm function from another instance, it will use the original funcref of that function

```
bool InstanceBuilder::ProcessImportedFunction(
    DirectHandle<WasmTrustedInstanceData> trusted_instance_data,
    int import_index, int func_index, DirectHandle<Object> value,
    WellKnownImport preknown_import) {
  .....
  // Store any {WasmExternalFunction} callable in the instance before the call
  // is resolved to preserve its identity. This handles exported functions as
  // well as functions constructed via other means (e.g. WebAssembly.Function).
  if (WasmExternalFunction::IsWasmExternalFunction(*value)) {
    trusted_instance_data->func_refs()->set(
        func_index, Cast<WasmExternalFunction>(*value)->func_ref());
  }
.....
```

Here `value` is the imported function, it checks if `value` is `WasmExternalFunction` which is a wasm function, if true then stores the funcref to `trusted_instance_data->func_refs` This behaviour can be broken if we import an `WasmSuspendingObject` with `WasmSuspendingObject->callable` is a wasm function

```
ImportCallKind ResolvedWasmImport::ComputeKind(
    DirectHandle<WasmTrustedInstanceData> trusted_instance_data, int func_index,
    const wasm::CanonicalSig* expected_sig, CanonicalTypeIndex expected_sig_id,
    WellKnownImport preknown_import) {
    
  .....
      
  if (IsWasmSuspendingObject(*callable_)) {
    suspend_ = kSuspend;
    SetCallable(isolate, Cast<WasmSuspendingObject>(*callable_)->callable()); // [1]
  }
  if (!trusted_function_data_.is_null() &&
      IsWasmExportedFunctionData(*trusted_function_data_)) { // [2]
    Tagged<WasmExportedFunctionData> data =
        Cast<WasmExportedFunctionData>(*trusted_function_data_);
    if (!data->MatchesSignature(expected_sig_id)) {
      return ImportCallKind::kLinkError;
    }
    uint32_t function_index = static_cast<uint32_t>(data->function_index());
    if (function_index >=
        data->instance_data()->module()->num_imported_functions) {
      return ImportCallKind::kWasmToWasm;
    }
    // Resolve the shortcut to the underlying callable and continue.
    ImportedFunctionEntry entry(direct_handle(data->instance_data(), isolate),
                                function_index);
    suspend_ = Cast<WasmImportData>(entry.implicit_arg())->suspend();
    SetCallable(isolate, entry.callable());
  }
...
```

When calling `SetCallable` at `[1]` it will set `trusted_function_data_` to `WasmExportedFunctionData` of the wasm function so that it will return `ImportCallKind::kWasmToWasm`

```
bool InstanceBuilder::ProcessImportedFunction(
    DirectHandle<WasmTrustedInstanceData> trusted_instance_data,
    int import_index, int func_index, DirectHandle<Object> value,
    WellKnownImport preknown_import) {
    ....
        
        case ImportCallKind::kWasmToWasm: {
      // The imported function is a Wasm function from another instance.
      auto function_data =
          Cast<WasmExportedFunctionData>(trusted_function_data);
      // The import reference is the trusted instance data itself.
      Tagged<WasmTrustedInstanceData> instance_data =
          function_data->instance_data();
      CHECK_GE(function_data->function_index(),
               instance_data->module()->num_imported_functions);
      WasmCodePointer imported_target =
          instance_data->GetCallTarget(function_data->function_index());
      imported_entry.SetWasmToWasm(instance_data, imported_target, sig_index
#if V8_ENABLE_DRUMBRAKE
                                   ,
                                   function_data->function_index()
#endif  // V8_ENABLE_DRUMBRAKE
      );
      return true;
            
            ...
```

In consume, it imports the original wasm function normally but it doesnt store the funcfef of the wasm function

When reexporting that function

```
void InstanceBuilder::ProcessExports() {

    ...
        
        case kExternalFunction: {
        // Wrap and export the code as a JSFunction.
        bool shared = module_->function_is_shared(exp.index);
        DirectHandle<WasmFuncRef> func_ref =
            WasmTrustedInstanceData::GetOrCreateFuncRef( // [1]
                isolate_, trusted_data(shared), exp.index);
        DirectHandle<WasmInternalFunction> internal_function{
            func_ref->internal(isolate_), isolate_};
        DirectHandle<JSFunction> wasm_external_function =
            WasmInternalFunction::GetOrCreateExternal(internal_function);
        value = wasm_external_function;
            
            ....
```

It gets the funcref at `[1]`

```
DirectHandle<WasmFuncRef> WasmTrustedInstanceData::GetOrCreateFuncRef(
    Isolate* isolate,
    DirectHandle<WasmTrustedInstanceData> trusted_instance_data,
    int function_index) {
    
    ....
    if (trusted_instance_data->try_get_func_ref(function_index,
                                              &existing_func_ref)) {
    return direct_handle(existing_func_ref, isolate);
  }
    ...
```

The function will first check if the `func_refs` array contain entry for that function. If not it will create a new one

```
DirectHandle<WasmFuncRef> WasmTrustedInstanceData::GetOrCreateFuncRef(
    Isolate* isolate,
    DirectHandle<WasmTrustedInstanceData> trusted_instance_data,
    int function_index) {
    ....
        
        const WasmModule* module = trusted_instance_data->module();
  bool is_import =
      function_index < static_cast<int>(module->num_imported_functions);
  wasm::ModuleTypeIndex sig_index = module->functions[function_index].sig_index; //[1]
  DirectHandle<TrustedObject> implicit_arg =
      is_import ? direct_handle(
                      Cast<TrustedObject>(
                          trusted_instance_data->dispatch_table_for_imports()
                              ->implicit_arg(function_index)),
                      isolate)
                : trusted_instance_data;

  // TODO(14034): Create funcref RTTs lazily?
  DirectHandle<Map> rtt{
      Cast<Map>(
          trusted_instance_data->managed_object_maps()->get(sig_index.index)),
      isolate};

    ...
```

The problem goes here, the `function_index` is the index in the module. I will call the module of original function is `module1` and the second is `module2`. In here it uses the `function_index` of `module2` to retrieve the `sig_index` of the function in `module1`. So if the original function which has index `1` (in my poc) when imported in `SuspendingObject` of index `2` it will use the signature of function `2` in the original module but the `call_target` is still the original function

**FIX**

The fix is trivial, just check if the `callable` of the `WasmSuspendingObject` is not a wasm function

**REPRODUCE**

Run: `.\d8.exe --expose-memory-corruption-api poc.js`, it will try to write `0xdeadbeef` to `0x4141414141414141`

**CRASH**

```
(3078.4c50): Access violation - code c0000005 (first chance)
First chance exceptions are reported before any exception handling.
This exception may be expected and handled.
000001a2`bf16199c 48894207        mov     qword ptr [rdx+7],rax ds:41414141`41414141=????????????????
```

```
RAX: 00000000DEADBEEF   RBX: 000001B3000444CD   RCX: 00007FF627582ED0   
RDX: 414141414141413A   RSI: 0000034400106455   RDI: 000001A2BF16198B   
RIP: 000001A2BF16199C   RSP: 0000001CFFDFE670   RBP: 0000001CFFDFE690   
R8:  0000001CFFDFE828   R9:  000001B30006EA29   R10: 000001A2D93D0000   
R11: 0000001CFFDFE7D0   R12: 0000000000000001   R13: 000001A2C1397080   
R14: 000001B300000000   R15: 000001B3000007BD   
```

Stack trace

```
Child-SP          RetAddr               Call Site
00 0000001c`ffdfe670 00007ff6`289ce7c6     0x000001a2`bf16199c
01 0000001c`ffdfe6a0 00007ff6`28ab14f3     d8!Builtins_JSToWasmWrapperAsm+0x86
02 0000001c`ffdfe6d8 00007ff6`28929e75     d8!Builtins_JSToWasmWrapper+0xdb3
03 0000001c`ffdfe8d0 00007ff6`28926a9c     d8!Builtins_InterpreterEntryTrampoline+0x135
04 0000001c`ffdfeae0 00007ff6`289265ff     d8!Builtins_JSEntryTrampoline+0x5c
05 0000001c`ffdfeb08 00007ff6`273dea2a     d8!Builtins_JSEntry+0xff
06 (Inline Function) --------`--------     d8!v8::internal::GeneratedCode<unsigned long long,unsigned long long,unsigned long long,unsigned long long,unsigned long long,long long,unsigned long long **>::Call+0x12 [D:\16_7_2025\v8\v8\src\execution\simulator.h @ 212] 
07 0000001c`ffdfec30 00007ff6`273df2d2     d8!v8::internal::`anonymous namespace'::Invoke+0xaaa [D:\16_7_2025\v8\v8\src\execution\execution.cc @ 441] 
08 0000001c`ffdfee30 00007ff6`27258a2a     d8!v8::internal::Execution::CallScript+0xe2 [D:\16_7_2025\v8\v8\src\execution\execution.cc @ 542] 
09 0000001c`ffdfeed0 00007ff6`2725874d     d8!v8::Script::Run+0x2ca [D:\16_7_2025\v8\v8\src\api\api.cc @ 1936] 
0a 0000001c`ffdff020 00007ff6`271c7025     d8!v8::Script::Run+0xd [D:\16_7_2025\v8\v8\src\api\api.cc @ 1901] 
0b 0000001c`ffdff050 00007ff6`271e3a3e     d8!v8::Shell::ExecuteString+0x755 [D:\16_7_2025\v8\v8\src\d8\d8.cc @ 1035] 
0c 0000001c`ffdff2d0 00007ff6`271e8050     d8!v8::SourceGroup::Execute+0x30e [D:\16_7_2025\v8\v8\src\d8\d8.cc @ 5351] 
0d 0000001c`ffdff380 00007ff6`271e7ca9     d8!v8::Shell::RunMainIsolate+0x190 [D:\16_7_2025\v8\v8\src\d8\d8.cc @ 6307] 
0e 0000001c`ffdff430 00007ff6`271e9c76     d8!v8::Shell::RunMain+0x129 [D:\16_7_2025\v8\v8\src\d8\d8.cc @ 6215] 
0f 0000001c`ffdff4c0 00007ff6`28b229b8     d8!v8::Shell::Main+0x1246 [D:\16_7_2025\v8\v8\src\d8\d8.cc @ 7100] 
10 (Inline Function) --------`--------     d8!invoke_main+0x22 [D:\a\_work\1\s\src\vctools\crt\vcstartup\src\startup\exe_common.inl @ 78] 
11 0000001c`ffdff9b0 00007ff8`09eb259d     d8!__scrt_common_main_seh+0x10c [D:\a\_work\1\s\src\vctools\crt\vcstartup\src\startup\exe_common.inl @ 288] 
12 0000001c`ffdff9f0 00007ff8`0aaaaf78     KERNEL32!BaseThreadInitThunk+0x1d
13 0000001c`ffdffa20 00000000`00000000     ntdll!RtlUserThreadStart+0x28
```

**CREDIT INFORMATION**

Reporter: @natsumikyono23


---

**#2 — xi...@chromium.org — Jul 18, 2025 06:16AM**

Thanks for the report. Triaging V8 sandbox bypass bugs per [https://chromium.googlesource.com/chromium/src/+/HEAD/docs/security/shepherd.md#assign](<https://chromium.googlesource.com/chromium/src/+/HEAD/docs/security/shepherd.md#assign>). Assigning to the current V8 sheriff.


---

**#3 — bi...@google.com — Jul 18, 2025 11:23PM**

This looks wasm specific. Clemens, could you please take a look?


---

**#4 — pv...@gmail.com — Jul 19, 2025 12:25AM**

Edit: the actual code that decides the signature for the function is in `WasmExportedFunction::New` function. The confuse above is only for creating func_ref but `JSToWasmWrapperHelper` resolve the signature at `target.shared_function_info.wasm_exported_function_data.sig`

```
macro JSToWasmWrapperHelper(
    context: NativeContext, receiver: JSAny, target: JSFunction,
    arguments: Arguments, promise: constexpr Promise): JSAny {
  const functionData = target.shared_function_info.wasm_exported_function_data;

  ...

  const sig = functionData.sig;
```

The confuse in `WasmExportedFunction::New`

```
DirectHandle<WasmExportedFunction> WasmExportedFunction::New(
    Isolate* isolate, DirectHandle<WasmTrustedInstanceData> instance_data,
    DirectHandle<WasmFuncRef> func_ref,
    DirectHandle<WasmInternalFunction> internal_function, int arity,
    DirectHandle<Code> export_wrapper) {
...
int func_index = internal_function->function_index(); // [1]
  ...
  const wasm::WasmModule* module = instance_data->module();
  wasm::CanonicalTypeIndex sig_id =
      module->canonical_sig_id(module->functions[func_index].sig_index); // [2]
  const wasm::CanonicalSig* sig =
      wasm::GetTypeCanonicalizer()->LookupFunctionSignature(sig_id);
  DirectHandle<WasmExportedFunctionData> function_data =
      factory->NewWasmExportedFunctionData( // [3]
          export_wrapper, instance_data, func_ref, internal_function, sig,
          sig_id, v8_flags.wasm_wrapper_tiering_budget, promise);
...
```

Resolve `func_index` at `[1]`, resolve `sig_index` at `[2]` and finally create `WasmExportedFunctionData` with `sig` at `[3]`

Since `func_refs` array is in untrusted space, it can be corrupted to be invalid so that there's no need to use `WasmSuspendingObject` tho. `func_refs` array should be moved outside the sandbox


---

**#5 — cl...@appspot.gserviceaccount.com — Jul 24, 2025 12:37AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5647065677758464](<https://clusterfuzz.com/testcase?key=5647065677758464>).


---

**#6 — cl...@appspot.gserviceaccount.com — Jul 24, 2025 12:54AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5300865141243904](<https://clusterfuzz.com/testcase?key=5300865141243904>).


---

**#7 — cl...@chromium.org — Jul 24, 2025 01:01AM**

Huh, I just wanted to come back to this, and now I see that this does not reproduce any more after [https://crrev.com/c/6779120](<https://crrev.com/c/6779120>).


---

**#8 — cl...@chromium.org — Jul 24, 2025 01:51AM**

Yeah, it _does_ make sense that this CL fixes this issue. The confusion previously happened in `GetOrCreateExternal`, where we would create a `WasmExportedFunction` where the `WasmFuncRef` does not match the `WasmInternalFunction` (`func_ref->internal` is not the same as `internal`). And that CL changes when and how we generate that `WasmFuncRef` and the `WasmExportedFunction`.


---

**#9 — cl...@chromium.org — Jul 24, 2025 01:53AM**

This design really makes me feel uneasy BTW:

```
extern class WasmInternalFunction extends ExposedTrustedObject {
[...]
  // For exported Wasm functions: the function index in the defining module;
  // {protected_implicit_arg} is the {WasmTrustedInstanceData} corresponding
  // to this module.
  // For imported JS functions: the function index in the importing module;
  // {protected_implicit_arg} is a {WasmImportData} describing this module.
  // For WasmJSFunctions and WasmCapiFunctions: -1.
  function_index: Smi;
```

That's a field which has different meaning depending on whether it's a Wasm function or an imported JS function. Not sure yet if/how that could be robustified though.


---

**#10 — pv...@gmail.com — Jul 24, 2025 02:18AM**

In this [commit](<https://chromium-review.googlesource.com/c/v8/v8/+/6779120>), the reason why the poc doesnt is when calling `GetOrCreateFuncRef` with `kPrecreateExternal`, it will create the export immidiately using `module` from `trusted_instance_data` so that it will resolve signature at this module

```
DirectHandle<WasmFuncRef> WasmTrustedInstanceData::GetOrCreateFuncRef(
    Isolate* isolate,
    DirectHandle<WasmTrustedInstanceData> trusted_instance_data,
    int function_index, wasm::PrecreateExternal precreate_external) {
...
  const WasmModule* module = trusted_instance_data->module();

 ...

  if (precreate_external == wasm::kPrecreateExternal) {
    CreateExportedFunction(isolate, module, function_index, sig_index, func_ref,
                           internal_function, trusted_instance_data);
  }
```

But in `GetOrCreateExternal` it resolves the `module` from `internal`

```
DirectHandle<JSFunction> WasmInternalFunction::GetOrCreateExternal(
    DirectHandle<WasmInternalFunction> internal) {

  ....
  DirectHandle<TrustedObject> implicit_arg{internal->implicit_arg(), isolate};
  DirectHandle<WasmTrustedInstanceData> instance_data =
      IsWasmTrustedInstanceData(*implicit_arg)
          ? Cast<WasmTrustedInstanceData>(implicit_arg)
          : direct_handle(Cast<WasmImportData>(*implicit_arg)->instance_data(),
                          isolate);
  const WasmModule* module = instance_data->module();
  int function_index = internal->function_index();
  wasm::ModuleTypeIndex sig_index = module->functions[function_index].sig_index;
...
  return CreateExportedFunction(isolate, module, function_index, sig_index,
                                func_ref, internal, instance_data);
}
```

So to reproduce this in new commit, instead of creating external by exporting, the new poc will create func_Ref using `ConstantExpressionInterface::RefFunc` and resolve the external as return value of a wasm function


---

**#11 — 24...@project.gserviceaccount.com — Jul 24, 2025 02:21AM**

Detailed Report: [https://clusterfuzz.com/testcase?key=5300865141243904](<https://clusterfuzz.com/testcase?key=5300865141243904>)  
  
Fuzzer: None  
Job Type: linux_d8_sandbox_testing  
Platform Id: linux  
  
Crash Type: V8 sandbox violation  
Crash Address:   
Crash State:  
NULL  
Sanitizer: address (ASAN)  
  
Regressed: [https://clusterfuzz.com/revisions?job=linux_d8_sandbox_testing&range=99798:99799](<https://clusterfuzz.com/revisions?job=linux_d8_sandbox_testing&range=99798:99799>)  
  
Reproducer Testcase: [https://clusterfuzz.com/download?testcase_id=5300865141243904](<https://clusterfuzz.com/download?testcase_id=5300865141243904>)  
  
To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.   
  
If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.  
  
If you have any feedback on reproducing test cases, let us know at [https://forms.gle/Yh3qCYFveHj6E5jz5](<https://forms.gle/Yh3qCYFveHj6E5jz5>) so we can improve.


---

**#12 — cl...@chromium.org — Jul 24, 2025 02:22AM**

Yeah, this is not fixed yet. I am still looking for a good bottleneck to catch this issue reliably. I'll have to continue this tomorrow. We are already constructing a corrupted `WasmInternalFunction` where the function index is the index of the import (2), but the `implicit_arg` is not a `WasmImportData` but a `WasmTrustedInstanceData`.


---

**#13 — cl...@appspot.gserviceaccount.com — Jul 24, 2025 05:45PM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5862191798353920](<https://clusterfuzz.com/testcase?key=5862191798353920>).


---

**#14 — cl...@appspot.gserviceaccount.com — Jul 24, 2025 05:53PM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5403898688765952](<https://clusterfuzz.com/testcase?key=5403898688765952>).


---

**#15 — 24...@project.gserviceaccount.com — Jul 24, 2025 07:24PM**

Detailed Report: [https://clusterfuzz.com/testcase?key=5403898688765952](<https://clusterfuzz.com/testcase?key=5403898688765952>)  
  
Fuzzer: None  
Job Type: linux_d8_sandbox_testing  
Platform Id: linux  
  
Crash Type: V8 sandbox violation  
Crash Address:   
Crash State:  
NULL  
Sanitizer: address (ASAN)  
  
Regressed: [https://clusterfuzz.com/revisions?job=linux_d8_sandbox_testing&range=99798:99799](<https://clusterfuzz.com/revisions?job=linux_d8_sandbox_testing&range=99798:99799>)  
  
Reproducer Testcase: [https://clusterfuzz.com/download?testcase_id=5403898688765952](<https://clusterfuzz.com/download?testcase_id=5403898688765952>)  
  
To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.   
  
If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.  
  
If you have any feedback on reproducing test cases, let us know at [https://forms.gle/Yh3qCYFveHj6E5jz5](<https://forms.gle/Yh3qCYFveHj6E5jz5>) so we can improve.


---

**#16 — dx...@google.com — Jul 24, 2025 09:30PM**

Project: v8/v8  
Branch: main  
Author: Clemens Backes [clemensb@chromium.org](<mailto:clemensb@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6781165](<https://chromium-review.googlesource.com/6781165>)

Fix printing of WasmInternalFunction

* * *

Expand for full commit details

```
     
    1) Include the function index. 
    2) Include the Wasm code pointer for the call target. 
    3) Print the actual call target in hex instead of decimal. 
     
    R=jkummerow@chromium.org 
     
    Bug: 432289371 
    Change-Id: Ib4aa2dc3b6ba82be763b69b6ac21072fc04d8e3f 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6781165 
    Reviewed-by: Jakob Kummerow <jkummerow@chromium.org> 
    Commit-Queue: Clemens Backes <clemensb@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#101618}
```

* * *

Files:

  * M `src/diagnostics/objects-printer.cc`

* * *

Hash: [a8eee9def0e4f3d5df204a77210d72430fb12062](<http://crrev.com/a8eee9def0e4f3d5df204a77210d72430fb12062>)  
Date: Thu Jul 24 09:40:54 2025

* * *


---

**#17 — pv...@gmail.com — Jul 24, 2025 09:54PM**

I think the problem has not been fixed yet, as i said before the issue comes from recreating ExternalFunction with confused `func_index`. Using `WasmSuspendingObject` because the program would not set entry in `func_ref` array and since this array is in untrusted space, it can be manipulated to contains smi after set up so the problem still remains


---

**#18 — cl...@chromium.org — Jul 24, 2025 10:05PM**

Thanks for your continued support on this issue!

Yes, the proper fix is in [https://crrev.com/c/6781095](<https://crrev.com/c/6781095>) and did not land yet. Does that fix look reasonable to you?


---

**#19 — pv...@gmail.com — Jul 24, 2025 10:16PM**

yeah like i said above, it fix the issue when importing a corrupted `WasmSuspendingObject`, but the recreate of `ExternalFunction` can still be obtained due to corrupted `func_refs` array of `WasmTrustedInstanceData` since that array is in untrusted heap. Change the entry to smi so that it will recreate `func_ref` in `Runtime_WasmRefFunc`

```
RUNTIME_FUNCTION(Runtime_WasmRefFunc) {
  HandleScope scope(isolate);
  DCHECK_EQ(2, args.length());
  DirectHandle<WasmTrustedInstanceData> trusted_instance_data(
      Cast<WasmTrustedInstanceData>(args[0]), isolate);
  uint32_t function_index = args.positive_smi_value_at(1);

  return *WasmTrustedInstanceData::GetOrCreateFuncRef(
      isolate, trusted_instance_data, function_index);
}
```


---

**#20 — th...@chromium.org — Jul 30, 2025 06:50PM**

I experimented with corrupting the func_refs directly. The difficulty is that it is behind the trusted pointer to the instance data, so it cannot be accessed directly as an offset from a known object in the poc. I'm not sure how one would get that address in practice, but it can probably be done somehow.  
So I "cheated" a bit by introducing a helper function in src/sandbox/testing.cc that returns the address to the func_refs array from a given WasmInstanceObject, and with it I was indeed able to tweak the poc to reproduce without having to wrap the import in a `WebAssembly.Suspending`, and by corrupting the relevant func ref element instead after instantiating the module.


---

**#21 — cl...@chromium.org — Jul 31, 2025 12:34AM**

I tried to reproduce a crash by just ignoring existing funcrefs from the array (by commenting out parts of the code), but failed to cause a crash.

Can someone share a reproducer for this?


---

**#22 — pv...@gmail.com — Jul 31, 2025 12:38AM**

you mean you cannot trigger a crash by abusing func_refs array?


---

**#23 — cl...@chromium.org — Jul 31, 2025 12:41AM**

If you have a reproducer that I could just run to get the crash then that would save me the time to write it myself.


---

**#24 — th...@chromium.org — Jul 31, 2025 12:43AM**

On my side I was only able to reproduce it with the help of an additional helper function in the Sandbox corruption API to get the func refs address. Here is that helper function:

```
diff --git a/src/sandbox/testing.cc b/src/sandbox/testing.cc
index 52d7395145a..f9e75fe186b 100644
--- a/src/sandbox/testing.cc
+++ b/src/sandbox/testing.cc
@@ -425,6 +425,22 @@ void SandboxGetFieldOffset(const v8::FunctionCallbackInfo<v8::Value>& info) {
   info.GetReturnValue().Set(offset);
 }
 
+void SandboxGetWasmFuncRefsAddress(const v8::FunctionCallbackInfo<v8::Value>& info) {
+  DCHECK(ValidateCallbackInfo(info));
+  v8::Isolate* isolate = info.GetIsolate();
+  auto* i_isolate = reinterpret_cast<Isolate*>(isolate);
+
+  if (!IsWasmInstanceObject(*Utils::OpenDirectHandle(*info[0]))) {
+    isolate->ThrowError("First argument must be a wasm instance");
+    return;
+  }
+
+  auto instance = Cast<WasmInstanceObject>(*Utils::OpenDirectHandle(*info[0]));
+  auto trusted_data = instance->trusted_data(i_isolate);
+  uint32_t address = static_cast<uint32_t>(trusted_data->func_refs()->address());
+  info.GetReturnValue().Set(v8::Integer::NewFromUnsigned(isolate, address));
+}
+
 Handle<FunctionTemplateInfo> NewFunctionTemplate(
     Isolate* isolate, FunctionCallback func,
     ConstructorBehavior constructor_behavior) {
@@ -518,6 +534,7 @@ void SandboxTesting::InstallMemoryCorruptionApi(Isolate* isolate) {
   InstallFunction(isolate, sandbox, SandboxGetInstanceTypeIdFor,
                   "getInstanceTypeIdFor", 1);
   InstallFunction(isolate, sandbox, SandboxGetFieldOffset, "getFieldOffset", 2);
+  InstallFunction(isolate, sandbox, SandboxGetWasmFuncRefsAddress, "getWasmFuncRefsAddress", 1);
 
   // Install the Sandbox object as property on the global object.
   Handle<JSGlobalObject> global = isolate->global_object();
```

And here is the modified poc.js (based on [comment #10](<https://issues.chromium.org/issues/432289371#comment10>)) that uses it to corrupt the func ref entry:

```
diff --git a/poc.js b/poc-modified.js
index 955a2e5703d..106fdc892ef 100644
--- a/poc.js
+++ b/poc-modified.js
@@ -2546,9 +2546,9 @@ var write = exports.write;
 write(createStruct(), 0x1n);
 
 
-var suspending = new WebAssembly.Suspending(foo)
-// // change callable of WasmSuspendingObject
-write4(addOf(suspending) + 0xc, addOf(write) + 1);
+// var suspending = new WebAssembly.Suspending(foo)
+// // // change callable of WasmSuspendingObject
+// write4(addOf(suspending) + 0xc, addOf(write) + 1);
 
 
 var builder2 = new WasmModuleBuilder();
@@ -2565,7 +2565,9 @@ builder2.addFunction('reExportOnlyInternal', makeSig([], [kWasmFuncRef]))
 ]).exportFunc();
 
 
-var instance2 = builder2.instantiate({test: {write: suspending}});
+let instance2 = builder2.instantiate({test: {write}});
+write4(Sandbox.getWasmFuncRefsAddress(instance2) + 0x10, 0);
+
 var exports2 = instance2.exports;
 var reExportOnlyInternal = exports2.reExportOnlyInternal;
```


---

**#25 — pv...@gmail.com — Jul 31, 2025 12:45AM**

hmm, i wrote a poc that try to find `func_refs` array using some pattern and modify the entry so that there's no need to use a corrupted `WasmSuspendingObject`


---

**#26 — cl...@chromium.org — Jul 31, 2025 12:47AM**

Thanks, that was fast :)

I'll try with those reproducers tomorrow. What I tried was commenting out calls to `try_get_func_ref` in the code such that we recreate them more often, but I couldn't get this to crash.


---

**#27 — cl...@appspot.gserviceaccount.com — Jul 31, 2025 07:28PM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=6560132775215104](<https://clusterfuzz.com/testcase?key=6560132775215104>).


---

**#28 — dx...@google.com — Jul 31, 2025 07:56PM**

Project: v8/v8  
Branch: main  
Author: Clemens Backes [clemensb@chromium.org](<mailto:clemensb@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6781095](<https://chromium-review.googlesource.com/6781095>)

[wasm] Fix sandbox escape via manipulated WasmSuspendingObject

* * *

Expand for full commit details

```
     
    The `callable` stored in the `WasmSuspendingObject` must not be a Wasm 
    function. This is enforced in the constructor, but if this is changed 
    later via sandbox corruption it can lead to internal inconsistencies if 
    we process the import as both a suspending import and an import of an 
    exported Wasm function. 
     
    R=thibaudm@chromium.org 
    CC=​jkummerow@chromium.org 
     
    Bug: 432289371 
    Change-Id: I2ca6edd51ad93e233d8c8c9757057386956abb24 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6781095 
    Reviewed-by: Thibaud Michaud <thibaudm@chromium.org> 
    Commit-Queue: Clemens Backes <clemensb@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#101706}
```

* * *

Files:

  * M `src/wasm/module-instantiate.cc`
  * A `test/mjsunit/sandbox/regress-432289371.js`

* * *

Hash: [49e49f879a604b7f11ed32b0579231e8a139d623](<http://crrev.com/49e49f879a604b7f11ed32b0579231e8a139d623>)  
Date: Thu Jul 24 09:55:24 2025

* * *


---

**#29 — cl...@chromium.org — Jul 31, 2025 11:19PM**

I think we painted ourselves into a really difficult corner here.

Some of this has been explained in the original report already, but I want to describe the problem again in my own words:

The [`WasmInternalFunction`](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/wasm-objects.tq;l=74;drc=205d4102d9cebd4adada560c6f04ac2d15442ad2>) stores an `implicit_arg` and a `function_index`. For imports, the `function_index` is the import index, and if it's a Wasm import then the `implicit_arg` is the `WasmTrustedInstanceData` of the exporting instance.

When we later want to construct a `WasmFuncRef` from this `WasmInternalFunction` (via [`WasmInternalFunction::GetOrCreateExternal`](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/wasm-objects.cc;l=2074;drc=bb8724fd6cc27651ce44165d0b97daefb42bee0d>) we read both again and then use the function index to look up the signature in the module, but the module is the module that defined the function (not that one that imported it) so the `function_index` does not make sense in the context of that module. Hence the signature confusion.

It looks like we just don't have enough information to recreate the `WasmExportedFunctionData` at this point.

So we either need to refactor what `WasmInternalFunction` stores (such that we can recreate the `WasmExportedFunctionData` later) or we need to ensure that we never try to recreate it.


---

**#30 — dx...@google.com — Aug 1, 2025 11:18PM**

Project: v8/v8  
Branch: main  
Author: Clemens Backes [clemensb@chromium.org](<mailto:clemensb@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6812255](<https://chromium-review.googlesource.com/6812255>)

[wasm] Forbid recreating WasmInternalFunction for Wasm imports

* * *

Expand for full commit details

```
     
    From the information we have in the importing instance we cannot 
    correctly recreate the WasmInternalFunction because we would need to 
    get the declared function index (we only have the import index). 
    We usually also do not need to recreate them because when importing an 
    exported Wasm function we cache the func refs. So this can only be 
    exploited via in-sandbox corruption. 
     
    This CL introduces an SBXCHECK to crash in case we try to recreate the 
    WasmInternalFunction for imported Wasm functions. 
     
    R=jkummerow@chromium.org 
     
    Bug: 432289371 
    Change-Id: Iebdc55bb390ae4a937e8bcb8433952a1f31a8383 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6812255 
    Commit-Queue: Clemens Backes <clemensb@chromium.org> 
    Reviewed-by: Jakob Kummerow <jkummerow@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#101725}
```

* * *

Files:

  * M `src/wasm/wasm-objects.cc`
  * A `test/mjsunit/sandbox/regress-432289371-b.js`

* * *

Hash: [aedcea406cd3c0ce1e2ea5fd77b2c08edd912b34](<http://crrev.com/aedcea406cd3c0ce1e2ea5fd77b2c08edd912b34>)  
Date: Fri Aug 1 13:46:05 2025

* * *


---

**#31 — dx...@google.com — Aug 5, 2025 01:40AM**

Project: v8/v8  
Branch: main  
Author: Thibaud Michaud [thibaudm@chromium.org](<mailto:thibaudm@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6818338](<https://chromium-review.googlesource.com/6818338>)

[wasm][sandbox] Check sandbox-safety of WasmSuspendingObject

* * *

Expand for full commit details

```
     
    The tentative fix at: 
    https://chromium-review.googlesource.com/c/v8/v8/+/6781095 
    Turns out to be incorrect because we don't handle special JS import 
    call kinds correctly anymore. 
    Instead, resolve the callable regardless of WasmSuspendingObject, and 
    check at the end that it is not kWasmToWasm. 
    A check was already added to catch a more general case of this issue: 
    https://chromium-review.googlesource.com/c/v8/v8/+/6812255 
    So this just consolidates the protection for this more specific case. 
     
    R=jkummerow@chromium.org 
     
    Fixed: 435489665,432289371 
    Change-Id: Ia979fef5502a4187dc3033df0c09ee437b2917a7 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6818338 
    Commit-Queue: Thibaud Michaud <thibaudm@chromium.org> 
    Reviewed-by: Clemens Backes <clemensb@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#101752}
```

* * *

Files:

  * M `src/wasm/module-instantiate.cc`

* * *

Hash: [9c89058f3c979a063f84e8f7e1d89ce638929c4d](<http://crrev.com/9c89058f3c979a063f84e8f7e1d89ce638929c4d>)  
Date: Mon Aug 4 16:01:00 2025

* * *


---

**#32 — sp...@google.com — Aug 14, 2025 07:56AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $5000.00 for this report.  
  
Rationale for this decision:  
V8 sandbox bypass demonstrating memory corruption outside the V8 heap sandbox  
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#33 — dx...@google.com — Oct 2, 2025 09:45PM**

Project: v8/v8  
Branch: main  
Author: Clemens Backes [clemensb@chromium.org](<mailto:clemensb@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6811187](<https://chromium-review.googlesource.com/6811187>)

[wasm] Store canonical signature on WasmInternalFunction

* * *

Expand for full commit details

```
     
    We currently look up the signature from the module (using the stored 
    function index) when we need it. In the case of imports this can easily 
    go wrong though, since the stored function index is the import index, 
    but the stored `implicit_arg` can be a `WasmTrustedInstanceData` (of the 
    module that originally defined the function). 
     
    In order to avoid confusion there, we now store the signature directly 
    on the central `WasmInternalFunction`, and in turn remove the fields 
    from `WasmExportedFunctionData`, `WasmJSFunctionData`, and 
    `WasmCapiFunctionData` (which all link to an internal function anyway). 
     
    R=jkummerow@chromium.org 
     
    Bug: 432289371, 435582611 
    Change-Id: Ib7ddae0bd002c988d485b7d381df3b7a5c961a63 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6811187 
    Reviewed-by: Jakob Kummerow <jkummerow@chromium.org> 
    Reviewed-by: Darius Mercadier <dmercadier@chromium.org> 
    Commit-Queue: Clemens Backes <clemensb@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#102899}
```

* * *

Files:

  * M `src/builtins/js-to-wasm.tq`
  * M `src/compiler/access-info.cc`
  * M `src/compiler/js-call-reducer.cc`
  * M `src/compiler/turboshaft/turbolev-graph-builder.cc`
  * M `src/diagnostics/objects-printer.cc`
  * M `src/heap/factory.cc`
  * M `src/heap/factory.h`
  * M `src/objects/objects-body-descriptors.h`
  * M `src/objects/shared-function-info.cc`
  * M `src/wasm/module-instantiate.cc`
  * M `src/wasm/wasm-js.cc`
  * M `src/wasm/wasm-objects-inl.h`
  * M `src/wasm/wasm-objects.cc`
  * M `src/wasm/wasm-objects.h`
  * M `src/wasm/wasm-objects.tq`

* * *

Hash: [11f240aa5e1354705f3e35de71a73865ff927b35](<https://chromiumdash.appspot.com/commit/11f240aa5e1354705f3e35de71a73865ff927b35>)  
Date: Wed Oct 1 13:55:51 2025

* * *


---

**#34 — ch...@google.com — Nov 11, 2025 09:42PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.


---

**#35 — cl...@chromium.org — Jan 8, 2026 07:33PM**

Removing `Clusterfuzz-ignore` hotlist from some old bugs as it's preventing Clusterfuzz from filing similar bugs.
