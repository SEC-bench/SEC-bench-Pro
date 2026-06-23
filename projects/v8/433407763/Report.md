# V8 sandbox bypass due to NativeModule swapping while module instantiation was ongoing

Issue URL: https://issues.chromium.org/issues/433407763
VRP-Reward: 20000
Date: Jul 22, 2025 06:34PM


# V8 sandbox bypass due to NativeModule swapping while module instantiation was ongoing

**DETAILS**

According to this [commit](<https://chromium-review.googlesource.com/c/v8/v8/+/6691457>), it drops some dereference of `WasmModuleObject` while instantiation. However, there's still one part of code use that when creating `WasmTrustedInstanceData`

```
Maybe<bool> InstanceBuilder::Build_Phase1(
    const DisallowJavascriptExecution& no_js) {
    ...
trusted_data_ =
      WasmTrustedInstanceData::New(isolate_, untrusted_module_object_, false);
...
```

Here `untrusted_module_object_` is `WasmModuleObject`, `trusted_data_` will be created using information from `WasmModuleObject->NativeModule`. A swapping attack can cause `InstanceBuilder->module_` be different from `trusted_data_->module_` To achieve the confusing, before calling `Build_Phase1` it calls `SanitizeImports` which eventually calls `Object::GetPropertyOrElement` on the imported object

```
MaybeDirectHandle<WasmInstanceObject> InstanceBuilder::Build() {
  TRACE_EVENT0(TRACE_DISABLED_BY_DEFAULT("v8.wasm.detailed"),
               "wasm.InstanceBuilder.Build");
  // Will check whether {ffi_} is available.
  SanitizeImports();
  ...
  if (Build_Phase1(no_js).IsNothing()) return {};
```

Here i define an accessor that can change `NativeModule` of `WasmModuleObject` so that the `WasmTrustedInstanceData` created in `Build_Phase1` will use that `NativeModule` while `InstanceBuilder->module_` is still the old module In this code the builder allocates `DispatchTable` using information of `InstanceBuilder->module_` which can lead to oob when `WasmTrustedInstanceData->module_->tables.size()` is larger

```
Maybe<bool> InstanceBuilder::Build_Phase1(
    const DisallowJavascriptExecution& no_js) {
...

//--------------------------------------------------------------------------
  // Set up table storage space, and initialize it for non-imported tables.
  //--------------------------------------------------------------------------
  int table_count = static_cast<int>(module_->tables.size());
  if (table_count == 0) {
    trusted_data_->set_tables(*isolate_->factory()->empty_fixed_array());
    if (shared) {
      shared_trusted_data_->set_tables(
          *isolate_->factory()->empty_fixed_array());
    }
  } else {
    DirectHandle<FixedArray> tables =
        isolate_->factory()->NewFixedArray(table_count);
    DirectHandle<ProtectedFixedArray> dispatch_tables =
        isolate_->factory()->NewProtectedFixedArray(table_count);
    trusted_data_->set_tables(*tables);
    trusted_data_->set_dispatch_tables(*dispatch_tables);
    DirectHandle<FixedArray> shared_tables;
    DirectHandle<ProtectedFixedArray> shared_dispatch_tables;
    if (shared) {
      shared_tables = isolate_->factory()->NewFixedArray(
          table_count, AllocationType::kSharedOld);
      shared_dispatch_tables =
          isolate_->factory()->NewProtectedFixedArray(table_count);
      shared_trusted_data_->set_tables(*shared_tables);
      shared_trusted_data_->set_dispatch_tables(*shared_dispatch_tables);
    }
    for (int i = module_->num_imported_tables; i < table_count; i++) {
      const WasmTable& table = module_->tables[i];
      CanonicalValueType canonical_type = module_->canonical_type(table.type);
      // Initialize tables with null for now. We will initialize non-defaultable
      // tables later, in {SetTableInitialValues}.
      DirectHandle<WasmDispatchTable> dispatch_table;
      DirectHandle<WasmTableObject> table_obj = WasmTableObject::New(
          isolate_, trusted_data(table.shared), table.type, canonical_type,
          table.initial_size, table.has_maximum_size, table.maximum_size,
          table.type.use_wasm_null()
              ? DirectHandle<HeapObject>{isolate_->factory()->wasm_null()}
              : DirectHandle<HeapObject>{isolate_->factory()->null_value()},
          table.address_type, &dispatch_table);
      (table.shared ? shared_tables : tables)->set(i, *table_obj);
      if (!dispatch_table.is_null()) {
        (table.shared ? shared_dispatch_tables : dispatch_tables)
            ->set(i, *dispatch_table);
        if (i == 0) {
          trusted_data(table.shared)->set_dispatch_table0(*dispatch_table);
        }
      }
    }
  }
 .....
```

oob of `dispatch_tables` -> fake `dispatch_table` -> fake entry

Entry in `dispatch_table` has the following layout

`WasmCodePointer|Signature|implicit_arg`

I setup the fake entry using `WasmImportData` since it contains `implicit_arg` which is `WasmTrustedInstanceData`

In poc i have the entry that `WasmCodePointer` does not belong to `implicit_arg` which is a `WasmTrustedInstanceData`. When initilizing, `WasmCodePointer` will point to an entry that contains `WasmCompileLazy` which will compile and call function at `WasmTrustedInstanceData->module_[func_index]`

```
RUNTIME_FUNCTION(Runtime_WasmCompileLazy) {
  DCHECK_EQ(2, args.length());
  Tagged<WasmTrustedInstanceData> trusted_instance_data =
      Cast<WasmTrustedInstanceData>(args[0]);
  int func_index = args.smi_value_at(1);

  ...
  bool success = wasm::CompileLazy(isolate, trusted_instance_data, func_index);
```

The `func_index` is fixed when initilizing entry at `WasmCodePointer`

```
// static
void JumpTableAssembler::GenerateLazyCompileTable(
    Address base, uint32_t num_slots, uint32_t num_imported_functions,
    Address wasm_compile_lazy_target) {
... 
  // Assume enough space, so the Assembler does not try to grow the buffer.
  JumpTableAssembler jtasm(jit_allocation, base);
  for (uint32_t slot_index = 0; slot_index < num_slots; ++slot_index) {
    DCHECK_EQ(slot_index * kLazyCompileTableSlotSize, jtasm.pc_offset());
    jtasm.EmitLazyCompileJumpSlot(slot_index + num_imported_functions,
                                  wasm_compile_lazy_target);
  }
...
}
void JumpTableAssembler::EmitLazyCompileJumpSlot(uint32_t func_index,
                                                 Address lazy_compile_target) {
  // Use a push, because mov to an extended register takes 6 bytes.
  const uint8_t inst[kLazyCompileTableSlotSize] = {
      0x68, 0, 0, 0, 0,  // pushq func_index
      0xe9, 0, 0, 0, 0,  // near_jmp displacement
  };

  intptr_t displacement =
      lazy_compile_target - (pc_ + kLazyCompileTableSlotSize);

  emit<uint8_t>(inst[0]);
  emit<uint32_t>(func_index);
  emit<uint8_t>(inst[5]);
  emit<int32_t>(base::checked_cast<int32_t>(displacement));
}
```

In my poc, `WasmCodePointer` is `0` which contains `WasmCompileLazy` that compiles `func_index = 1`, this has signature `([kWasmI64, kWasmI64])` for check at `call_indirect`. But the `WasmTrustedInstanceData->module_[func_index]` do `StructSet` at first argument -> bypass sandbox

**FIX**

Removing the use of `WasmModuleObject` in `InstanceBuilder`

**REPRODUCE**

Run: `.\d8.exe --expose-memory-corruption-api swap_module.js`, it will try to write `0xdeadbeef` to `0x4141414141414141`

**CRASH STATE**

```
(1f58.4b60): Access violation - code c0000005 (first chance)
First chance exceptions are reported before any exception handling.
This exception may be expected and handled.
000000d9`c8e81a19 48894207        mov     qword ptr [rdx+7],rax ds:41414141`41414141=????????????????
```

```
RAX: 00000000DEADBEEF   RBX: 0000000000000000   RCX: 0000021471550000   
RDX: 414141414141413A   RSI: 00000382001076B9   RDI: 000000D9C8E81A08   
RIP: 000000D9C8E81A19   RSP: 0000008EFC1FEA68   RBP: 0000008EFC1FEA88   
R8:  0000000000000000   R9:  0000000000000000   R10: 0000000000000000   
R11: 0000000000000001   R12: 0000000000000000   R13: 0000021469420080   
R14: 0000022500000000   R15: 00000225000007BD  
```

Stack trace

```
0000008e`fc1fea68 000000d9`c8e81995     0x000000d9`c8e81a19
01 0000008e`fc1fea98 00007ff6`23325946     0x000000d9`c8e81995
02 0000008e`fc1feae8 00007ff6`23408673     d8!Builtins_JSToWasmWrapperAsm+0x86
03 0000008e`fc1feb20 00007ff6`23280ff5     d8!Builtins_JSToWasmWrapper+0xdb3
04 0000008e`fc1fed18 00007ff6`2327dc1c     d8!Builtins_InterpreterEntryTrampoline+0x135
05 0000008e`fc1fef30 00007ff6`2327d77f     d8!Builtins_JSEntryTrampoline+0x5c
06 0000008e`fc1fef58 00007ff6`21d2ebfa     d8!Builtins_JSEntry+0xff
07 (Inline Function) --------`--------     d8!v8::internal::GeneratedCode<unsigned long long,unsigned long long,unsigned long long,unsigned long long,unsigned long long,long long,unsigned long long **>::Call+0x12 [D:\22_7_2025\v8\v8\src\execution\simulator.h @ 212] 
08 0000008e`fc1ff080 00007ff6`21d2f4a2     d8!v8::internal::`anonymous namespace'::Invoke+0xaaa [D:\22_7_2025\v8\v8\src\execution\execution.cc @ 441] 
09 0000008e`fc1ff280 00007ff6`21ba875a     d8!v8::internal::Execution::CallScript+0xe2 [D:\22_7_2025\v8\v8\src\execution\execution.cc @ 542] 
0a 0000008e`fc1ff320 00007ff6`21ba847d     d8!v8::Script::Run+0x2ca [D:\22_7_2025\v8\v8\src\api\api.cc @ 1936] 
0b 0000008e`fc1ff470 00007ff6`21b17005     d8!v8::Script::Run+0xd [D:\22_7_2025\v8\v8\src\api\api.cc @ 1901] 
0c 0000008e`fc1ff4a0 00007ff6`21b33a0e     d8!v8::Shell::ExecuteString+0x755 [D:\22_7_2025\v8\v8\src\d8\d8.cc @ 1035] 
0d 0000008e`fc1ff730 00007ff6`21b37e90     d8!v8::SourceGroup::Execute+0x30e [D:\22_7_2025\v8\v8\src\d8\d8.cc @ 5351] 
0e 0000008e`fc1ff7e0 00007ff6`21b37ae9     d8!v8::Shell::RunMainIsolate+0x190 [D:\22_7_2025\v8\v8\src\d8\d8.cc @ 6307] 
0f 0000008e`fc1ff890 00007ff6`21b39ab6     d8!v8::Shell::RunMain+0x129 [D:\22_7_2025\v8\v8\src\d8\d8.cc @ 6215] 
10 0000008e`fc1ff920 00007ff6`23479bf8     d8!v8::Shell::Main+0x1246 [D:\22_7_2025\v8\v8\src\d8\d8.cc @ 7100] 
11 (Inline Function) --------`--------     d8!invoke_main+0x22 [D:\a\_work\1\s\src\vctools\crt\vcstartup\src\startup\exe_common.inl @ 78] 
12 0000008e`fc1ffe10 00007ff8`09eb259d     d8!__scrt_common_main_seh+0x10c [D:\a\_work\1\s\src\vctools\crt\vcstartup\src\startup\exe_common.inl @ 288] 
13 0000008e`fc1ffe50 00007ff8`0aaaaf78     KERNEL32!BaseThreadInitThunk+0x1d
14 0000008e`fc1ffe80 00000000`00000000     ntdll!RtlUserThreadStart+0x28
```

**CREDIT INFORMATION**

Reporter: @natsumikyono23


---

**#2 — th...@chromium.org — Jul 22, 2025 11:31PM**

[security shepherd] This is a V8 sandbox report. So I am doing the following:  
\- Set a provisional severity of Medium (S2).  
\- Set a provisional priority of P1.  
\- Assign to the current V8 Sheriff (assigning to thibaudm@, cc bikineev@)  
\- Apply the Security_Impact-None hotlist (hotlistID:5433277).  
\- Apply the V8 Sandbox hotlist (hotlistID:4802478).


---

**#3 — th...@chromium.org — Jul 23, 2025 05:58PM**

Jakob, can you please take this one? I think you are the best owner here given your previous work on this topic.  
I'm able to reproduce locally with the poc.


---

**#4 — dx...@google.com — Jul 25, 2025 12:35AM**

Project: v8/v8  
Branch: main  
Author: Jakob Kummerow [jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6781481](<https://chromium-review.googlesource.com/6781481>)

[sandbox][wasm] Harden instantiation some more

* * *

Expand for full commit details

```
     
    crrev.com/c/6691457 missed one case where we still read the 
    NativeModule pointer from the heap twice. 
     
    Fixed: 433407763 
    Bug: 336507783 
    Change-Id: I6c6d98716c3676fdf1940d13a4065bb038e3f145 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6781481 
    Auto-Submit: Jakob Kummerow <jkummerow@chromium.org> 
    Reviewed-by: Clemens Backes <clemensb@chromium.org> 
    Commit-Queue: Jakob Kummerow <jkummerow@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#101626}
```

* * *

Files:

  * M `src/wasm/module-instantiate.cc`
  * M `src/wasm/wasm-objects.cc`
  * M `src/wasm/wasm-objects.h`
  * M `test/common/wasm/wasm-run-utils.cc`
  * M `test/fuzzer/wasm/interpreter/interpreter-fuzzer-common.cc`

* * *

Hash: [bb8724fd6cc27651ce44165d0b97daefb42bee0d](<http://crrev.com/bb8724fd6cc27651ce44165d0b97daefb42bee0d>)  
Date: Thu Jul 24 14:30:25 2025

* * *


---

**#5 — sa...@chromium.org — Jul 25, 2025 10:00PM**

It would be good to backmerge this fix if possible. I'll set the respective labels now but please raise any concerns regarding a backmerge (e.g. stability).


---

**#6 — ch...@google.com — Jul 25, 2025 10:15PM**

Merge review required: no relevant commits could be automatically detected (via Git Watcher comments), sending to merge review for manual evaluation. If you have not already manually listed the relevant commits to be merged via a comment above, please do so ASAP.

Please answer the following questions so that we can safely process your merge request:

  1. Why does your merge fit within the merge criteria for these milestones?

  * Chrome Browser: [https://chromiumdash.appspot.com/branches](<https://chromiumdash.appspot.com/branches>)
  * Chrome OS: [https://goto.google.com/cros-release-branch-merge-guidelines](<https://goto.google.com/cros-release-branch-merge-guidelines>)

  2. What changes specifically would you like to merge? Please link to Gerrit.
  3. Have the changes been released and tested on canary?
  4. Is this a new feature? If yes, is it behind a Finch flag and are experiments active in any release channels?
  5. [Chrome OS only]: Was the change reviewed and approved by the Eng Prod Representative? [https://goto.google.com/cros-engprodcomponents](<https://goto.google.com/cros-engprodcomponents>)
  6. If this merge addresses a major issue in the stable channel, does it require manual verification by the test team? If so, please describe required testing.

Please contact the milestone owner if you have questions. Owners: andywu (ChromeOS), srinivassista (Desktop US), danielyip (Desktop EMEA), harrysouders (Mobile US), eakpobaro (Mobile EMEA)


---

**#7 — ch...@google.com — Jul 25, 2025 10:15PM**

Merge review required: no relevant commits could be automatically detected (via Git Watcher comments), sending to merge review for manual evaluation. If you have not already manually listed the relevant commits to be merged via a comment above, please do so ASAP.

Please answer the following questions so that we can safely process your merge request:

  1. Why does your merge fit within the merge criteria for these milestones?

  * Chrome Browser: [https://chromiumdash.appspot.com/branches](<https://chromiumdash.appspot.com/branches>)
  * Chrome OS: [https://goto.google.com/cros-release-branch-merge-guidelines](<https://goto.google.com/cros-release-branch-merge-guidelines>)

  2. What changes specifically would you like to merge? Please link to Gerrit.
  3. Have the changes been released and tested on canary?
  4. Is this a new feature? If yes, is it behind a Finch flag and are experiments active in any release channels?
  5. [Chrome OS only]: Was the change reviewed and approved by the Eng Prod Representative? [https://goto.google.com/cros-engprodcomponents](<https://goto.google.com/cros-engprodcomponents>)
  6. If this merge addresses a major issue in the stable channel, does it require manual verification by the test team? If so, please describe required testing.

Please contact the milestone owner if you have questions. Owners: alonbajayo (ChromeOS), srinivassista (Desktop US), danielyip (Desktop EMEA), govind (Mobile US), eakpobaro (Mobile EMEA)


---

**#8 — jk...@chromium.org — Jul 25, 2025 10:52PM**

#6/#7:

  1. Security hardening, backmerge requested by security folks (see #5).
  2. [https://chromium-review.googlesource.com/c/v8/v8/+/6781481](<https://chromium-review.googlesource.com/c/v8/v8/+/6781481>)
  3. Not yet, but it landed 24h ago, so it should reach the Canary channel any moment now. See [https://chromiumdash.appspot.com/commit/bb8724fd6cc27651ce44165d0b97daefb42bee0d](<https://chromiumdash.appspot.com/commit/bb8724fd6cc27651ce44165d0b97daefb42bee0d>).
  4. N/A
  5. N/A
  6. No manual testing required.

I have no concerns about the stability of the fix, I think backmerging it is fine.


---

**#9 — am...@chromium.org — Jul 29, 2025 01:35AM**

The last release of M138 Stable RC is being cut today. I do not consider this fix sufficiently urgent to ship in that release. Merges for [https://crrev.com/c/6781481](<https://crrev.com/c/6781481>) approved for M139, the RC for Early Stable is being cut tomorrow. Please merge this fix to 13.9 at your earliest convenience / before 8am Pacific Time tomorrow, so this fix can be included in next M139 Beta and M139 Early Stable.


---

**#10 — jk...@chromium.org — Jul 30, 2025 12:29AM**

Ah, I left the wrong "Bug:" line on the merge CL; the merge has happened: [https://chromium-review.googlesource.com/c/v8/v8/+/6797273](<https://chromium-review.googlesource.com/c/v8/v8/+/6797273>)


---

**#11 — sp...@google.com — Aug 22, 2025 07:56AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $20000.00 for this report.  
  
Rationale for this decision:  
report of V8 sandbox bypass demonstrating a controlled write outside the V8 heap sandbox  
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#12 — ch...@google.com — Oct 31, 2025 09:44PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
