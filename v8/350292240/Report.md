# V8 Sandbox Bypass: AAR/W via generic function table `call_indirect` rtt check bypass

Issue URL: https://issues.chromium.org/issues/350292240
VRP-Reward: 20000
Date: Jul 1, 2024 03:50PM


### VULNERABILITY DETAILS

V8 sandbox bypass, arbitrary address read/write via function signature confusion through rtt check bypass in `call_indirect` for generic function tables using in-sandbox exploit primitives.

Function signature confusion in tables are fixed by [https://chromium-review.googlesource.com/c/v8/v8/+/5626414](<https://chromium-review.googlesource.com/c/v8/v8/+/5626414>) and [https://chromium-review.googlesource.com/5659606](<https://chromium-review.googlesource.com/5659606>), with the former checking table updates and the latter checking table imports.

Notably, we're using `SBXCHECK(FunctionSigMatchesTable(...))` to check whether the function signature is in fact a canonical subtype of the actual table type. This check cannot be done statically with generic function typed tables and thus the checks are eventually [done in runtime via rtt subtype checks](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/baseline/liftoff-compiler.cc;drc=98618e309ba7ec15e3164651e26b5587a1d9cee2;l=8308>). However, all the objects involved in the checks are within the v8 sandbox (rtt `Map`, `WasmTypeInfo`, `ManagedObjectMaps`, etc.) and are subject to corruption.

Thus, an attacker may corrupt in-sandbox memory such that `WasmTypeInfo.supertype[rtt_depth] = formal_rtt` to bypass rtt subtype check, causing function signature confusion and obtain AAR/W primitives outside of the sandbox.

Note that this can be used to force other runtime casts to succeed, such as `rtt.cast`.

Analysis of Liftoff JIT compilation for the rtt subtype checks:

```
pwndbg> nearpc 0x23525d93889c 0x8
 ► 0x23525d93889c    mov    ecx, dword ptr [rsi + 7]
   0x23525d93889f    or     rcx, qword ptr [r13 + 0x1e0]
   0x23525d9388a6    mov    ebx, dword ptr [rcx + 0x17]
   0x23525d9388a9    cmp    ebx, 5
   0x23525d9388ac    je     0x23525d9388f0                <0x23525d9388f0>
 
   // __ emit_i32_cond_jumpi(kEqual, sig_mismatch_label, real_sig_id.gp_reg(), -1, frozen);
   0x23525d9388b2    cmp    ebx, -1
   0x23525d9388b5    je     0x23525d938948                <0x23525d938948>
 
   // __ LoadFullPointer(real_rtt.gp_reg(), kRootRegister, IsolateData::root_slot_offset(RootIndex::kWasmCanonicalRtts));
   0x23525d9388bb    mov    rdi, qword ptr [r13 + 0x1cf8]
   // __ LoadTaggedPointer(real_rtt.gp_reg(), real_rtt.gp_reg(), real_sig_id.gp_reg(), ObjectAccess::ToTagged(WeakArrayList::kHeaderSize), nullptr, true);
   0x23525d9388c2    mov    edi, dword ptr [rdi + rbx*4 + 0xb]
   0x23525d9388c6    add    rdi, r14
   // __ emit_i64_andi(real_rtt.reg(), real_rtt.reg(), static_cast<int32_t>(~kWeakHeapObjectMask));
   0x23525d9388c9    and    rdi, 0xfffffffffffffffd
   // Step 1: load the WasmTypeInfo.
   // ScopedTempRegister type_info{std::move(real_rtt)};
   // __ LoadTaggedPointer(type_info.gp_reg(), type_info.gp_reg(), no_reg, kTypeInfoOffset);
   0x23525d9388cd    mov    edi, dword ptr [rdi + 0x13]
   0x23525d9388d0    add    rdi, r14
   // Step 2: check the list's length if needed. => omitted
   // Step 3: load the candidate list slot, and compare it.
   // ScopedTempRegister maybe_match{std::move(type_info)};
   // __ LoadTaggedPointer(maybe_match.gp_reg(), maybe_match.gp_reg(), no_reg, ObjectAccess::ToTagged(WasmTypeInfo::kSupertypesOffset + rtt_depth * kTaggedSize));
   0x23525d9388d3    mov    edi, dword ptr [rdi + 0x13]
   0x23525d9388d6    add    rdi, r14
   // LOAD_TAGGED_PTR_INSTANCE_FIELD(formal_rtt.gp_reg(), ManagedObjectMaps, kGpCacheRegList);
   0x23525d9388d9    mov    ebx, dword ptr [rsi + 0xb3]
   0x23525d9388df    add    rbx, r14
   // __ LoadTaggedPointer(formal_rtt.gp_reg(), formal_rtt.gp_reg(), no_reg, wasm::ObjectAccess::ElementOffsetInTaggedFixedArray(imm.sig_imm.index));
   0x23525d9388e2    mov    ebx, dword ptr [rbx + 0xf]
   0x23525d9388e5    add    rbx, r14
   // __ emit_cond_jump(kNotEqual, sig_mismatch_label, kRtt, formal_rtt.gp_reg(), maybe_match.gp_reg(), frozen);
   0x23525d9388e8    cmp    ebx, edi
   0x23525d9388ea    jne    0x23525d938948                <0x23525d938948>
```

### VERSION

V8 Version: a832ff96bd41b40b9cfee90a314fa816802cf9ae

### REPRODUCTION CASE

Repro added as `rtt_subtype_check_bypass.js`.

### FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION

Type of crash: Sandbox violation

### CREDIT INFORMATION

Reporter credit: Seunghyun Lee (@0x10n)


---

**#2 — se...@gmail.com — Jul 1, 2024 04:43PM**

Update: Repro also working on latest v8 commit 362c1b605c7908bef1d6e48d2b2ee93f9eef23bf as expected.


---

**#3 — se...@gmail.com — Jul 1, 2024 05:00PM**

Minor update: Cleared up some variable naming (ex: `funcref_v_ls` -> `funcref_writer`) as funcref objects are related to the function it references, not its type. Its maps however are directly related to the type (i.e. function signature, see [`CreateMapForType()`](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/module-instantiate.cc;l=146;drc=7b232da0f22e8cdf555d43c52b6491baeb87f729>)), so the naming `map_v_ls` persists.

This does not affect the behavior of the PoC in any way.


---

**#4 — ah...@google.com — Jul 1, 2024 10:19PM**

Hello,  
Thanks for the report! Could you please provide the command line arguments used to reproduce this issue?


---

**#5 — ah...@google.com — Jul 1, 2024 10:35PM**

[security shepherd]  
Assigning to the current V8 Shepherd: [ishell@google.com](<mailto:ishell@google.com>)  
Provisionally setting severity to Low (S3) as per our guidelines.


---

**#6 — se...@gmail.com — Jul 1, 2024 11:23PM**

Re [comment#4](<https://issues.chromium.org/issues/350292240#comment4>):

This is a V8 sandbox bypass report as per [https://g.co/chrome/vrp/#v8-sandbox-bypass-rewards](<https://g.co/chrome/vrp/#v8-sandbox-bypass-rewards>) so the devs working on v8 sandbox would be aware of how this should be reproed.

For the record:

  1. Build a d8 binary with the given gn flags described in the above link
  2. Run `./d8 --sandbox-testing ./rtt_subtype_check_bypass.js` with both js files in the current directory
  3. Observe the "V8 sandbox violation detected!" message.

* * *

cc jkummerow@ as the assignee of multiple v8sbx bypasses reported recently ([b/348793147](<https://issues.chromium.org/issues/348793147>), [b/349529650](<https://issues.chromium.org/issues/349529650>), [b/349502157](<https://issues.chromium.org/issues/349502157>))


---

**#7 — pe...@google.com — Jul 2, 2024 12:39AM**

Setting Priority to P2 to match Severity s3. If this is incorrect, please reset the priority. The automation bot account won't make this change again.


---

**#8 — cl...@appspot.gserviceaccount.com — Jul 3, 2024 04:35PM**

Detailed Report: [https://clusterfuzz.com/testcase?key=6325971768508416](<https://clusterfuzz.com/testcase?key=6325971768508416>)  
  
Fuzzer: None  
Job Type: linux_d8_sandbox_testing  
Platform Id: linux  
  
Crash Type: V8 sandbox violation  
Crash Address:   
Crash State:  
NULL  
Sanitizer: address (ASAN)  
  
Crash Revision: [https://clusterfuzz.com/revisions?job=linux_d8_sandbox_testing&revision=94793](<https://clusterfuzz.com/revisions?job=linux_d8_sandbox_testing&revision=94793>)  
  
Reproducer Testcase: [https://clusterfuzz.com/download?testcase_id=6325971768508416](<https://clusterfuzz.com/download?testcase_id=6325971768508416>)  
  
To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.   
  
If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.  
  
If you have any feedback on reproducing test cases, let us know at [https://forms.gle/Yh3qCYFveHj6E5jz5](<https://forms.gle/Yh3qCYFveHj6E5jz5>) so we can improve.


---

**#9 — sa...@chromium.org — Jul 3, 2024 04:40PM**

Great work, as usual :) managed to reproduce this on Clusterfuzz without much issues (just inlined the wasm-module-builder.js at the start of the file as CF cannot do imports).


---

**#10 — se...@gmail.com — Jul 3, 2024 05:20PM**

Re saelo@: Thanks! By the way, are these reports being helpful? I've reported 5 v8sbx bypasses within WASM in the last few days, the bypasses are all different but boils down to manipulating things to call a WASM function with mismatching signature (although I suspect this is not the only way to exploit the same underlying problem). Is there a plan to implement a generic mitigation for these issues in the near future, something like `signature_hash` checks done in `call_ref`? I might be better off focusing on other stuff if there is one, but if not I could continue looking a bit more into these issues :)


---

**#11 — sa...@chromium.org — Jul 3, 2024 06:17PM**

Thanks for asking! In general, these reports are super helpful! Specifically for the latest reports I'll defer the question to Jakob who's been working on Wasm sandboxing and knows more about the current state, open issues, and planned upcoming changes.


---

**#12 — pe...@google.com — Oct 29, 2024 12:40AM**

jkummerow: Uh oh! This issue still open and hasn't been updated in the last 117 days. This is a serious vulnerability, and we want to ensure that there's progress. Could you please leave an update with the current status and any potential blockers?

If you're not the right owner for this issue, could you please remove yourself as soon as possible or help us find the right one?

If the issue is fixed or you can't reproduce it, please close the bug. If you've started working on a fix, please set the status to Started.

Thanks for your time! To disable nags, add Disable-Nags (case sensitive) to the Chromium Labels custom field.


---

**#13 — pe...@google.com — Nov 13, 2024 12:38AM**

jkummerow: Uh oh! This issue still open and hasn't been updated in the last 131 days. This is a serious vulnerability, and we want to ensure that there's progress. Could you please leave an update with the current status and any potential blockers?

If you're not the right owner for this issue, could you please remove yourself as soon as possible or help us find the right one?

If the issue is fixed or you can't reproduce it, please close the bug. If you've started working on a fix, please set the status to Started.

Thanks for your time! To disable nags, add Disable-Nags (case sensitive) to the Chromium Labels custom field.


---

**#14 — jk...@chromium.org — Nov 14, 2024 01:19AM**

#12/#13: The V8 sandbox is WIP, known sandbox escapes were only recently raised to P1. This is on my to-do list. Perhaps Clemens has time for it before I will.

The tricky part is that we have to decide how exactly to implement the subtype check such that it only uses off-heap/trusted data. One option might be to call a C++ function that performs a walk of the canonical supertype chain (we have all required data in the type canonicalizer), but calling such a function from the place in Liftoff where we need to perform the check is a bit tricky. Another option might be to store the canonical supertype chain somewhere where we can conveniently read it from generated code, but that'll have a memory cost, which is unfortunate because we're not aware of any production use cases that use non-final function types for `call_indirect`.


---

**#15 — jk...@chromium.org — Nov 14, 2024 01:47AM**

Addendum to #14: Forgot to mention a third option: we could include the signature hash in the `WasmDispatchTable`, and perform a signature hash check just like `call_ref` does. Again, the drawback is that this consumes more memory by making dispatch tables bigger. A variant of the idea is to have a separate (off-heap) sparse map from canonical type index to signature hash that only needs to be populated for non-final signatures; but that would make accessing the data structure more complicated (probably couldn't do it from generated code, would need a C++ call).


---

**#16 — 24...@project.gserviceaccount.com — Nov 14, 2024 04:36PM**

ClusterFuzz testcase 6325971768508416 is verified as fixed in [https://clusterfuzz.com/revisions?job=linux_d8_sandbox_testing&range=97150:97151](<https://clusterfuzz.com/revisions?job=linux_d8_sandbox_testing&range=97150:97151>)  
  
If this is incorrect, please add the hotlistid:5433040 and re-open the issue.


---

**#17 — sa...@chromium.org — Nov 14, 2024 05:30PM**

This isn't fixed, just the changes I made to --sandbox-testing yesterday broke the reproducer. I'll update and re-upload it.


---

**#18 — sa...@chromium.org — Nov 14, 2024 05:31PM**

With Stephen's recent work on a WasmCodePointerTable through which all indirect calls now go through, would it also be an option to store a signature there?


---

**#19 — cl...@appspot.gserviceaccount.com — Nov 14, 2024 05:47PM**

Detailed Report: [https://clusterfuzz.com/testcase?key=5106619641692160](<https://clusterfuzz.com/testcase?key=5106619641692160>)  
  
Fuzzer: None  
Job Type: linux_d8_sandbox_testing  
Platform Id: linux  
  
Crash Type: V8 sandbox violation  
Crash Address:   
Crash State:  
NULL  
Sanitizer: address (ASAN)  
  
Crash Revision: [https://clusterfuzz.com/revisions?job=linux_d8_sandbox_testing&revision=97177](<https://clusterfuzz.com/revisions?job=linux_d8_sandbox_testing&revision=97177>)  
  
Reproducer Testcase: [https://clusterfuzz.com/download?testcase_id=5106619641692160](<https://clusterfuzz.com/download?testcase_id=5106619641692160>)  
  
To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.   
  
If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.  
  
If you have any feedback on reproducing test cases, let us know at [https://forms.gle/Yh3qCYFveHj6E5jz5](<https://forms.gle/Yh3qCYFveHj6E5jz5>) so we can improve.


---

**#20 — se...@gmail.com — Nov 15, 2024 03:33PM**

Re #18: I was under the impression that `WasmCodePointerTable` is intended to block these signature confusion issues by (eventually) adding signature checks on the CPT entries, otherwise we will constantly have bypasses like [b/379140430](<https://issues.chromium.org/issues/379140430>). I'm not sure about the overhead though...


---

**#21 — sa...@chromium.org — Nov 15, 2024 07:22PM**

Yeah I believe that is something that Stephen had in mind as another potential use-case for the table.

I think it would be good to get to a point where at least one of the following is true (and ideally more than one):

  1. There's a central "bottleneck" through which all (indirect) calls go that provides sandbox safety guarantees (in essence, that means fine-grained CFI). Something that's ~trivial to manually verify for correctness. Maybe similar to how we [protect JS calls](<https://docs.google.com/document/d/1WkyEynMluvIr0LBmrapyF7MiE8wIHFHnlP5B6FFhQuA/edit?usp=sharing>), where everything relies on the consistency of the JSDispatchTable, and there's a [fairly straightforward CHECK for that](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/sandbox/js-dispatch-table-inl.h;l=65;drc=71c3653baa506585de54e6ef79d1cd5f6bd9a148>).
  2. We have software-based code validation in place that guarantees that any generated JS or Wasm code cannot write outside of the sandbox. This might mean using compressed loads for accessing argument values so that the verifier can prove that the pointers will point into the sandbox. In combination with (1), the verifier can then also easily prove that all outgoing calls are secure.
  3. We have hardware mechanisms in place that guarantee that JS or Wasm code cannot write outside the sandbox. Something like PKEYs, for example. See also [this doc](<https://docs.google.com/document/d/12MsaG6BYRB-jQWNkZiuM3bY8X2B2cAsCMLLdgErvK4c/edit?usp=sharing>).

Both (2) and (3) are not going to happen short-term, and we now already have the `WasmCodePointerTable` as central "bottleneck" for indirect Wasm calls AFAIK, so maybe we should explore option (1) for now. Then once we have one of (2) or (3), we could reconsider if necessary.


---

**#22 — ap...@google.com — Dec 12, 2024 09:09PM**

Project: v8/v8  
Branch: main  
Author: Stephen Roettger <[sroettger@google.com](<mailto:sroettger@google.com>)>  
Link: [https://chromium-review.googlesource.com/6072813](<https://chromium-review.googlesource.com/6072813>)

[sandbox][wasm] add signature checks to the code pointer table

* * *

Expand for full commit details

```
[sandbox][wasm] add signature checks to the code pointer table 
 
This CL replaces existing sandbox signature hash checks with checks in 
the WasmCodePointerTable. Every CPT entry stores the signature hash and 
every load will validate the signature. 
 
The signature hash is stored in the CallDescriptor and passed through 
the inputs to the codegen for kArchCallWasmFunction Arch instruction. 
CallWasmCodePointer then has new instructions (on 64 bit) to compare 
the signature hash. 
 
Fixed: 350292240 
Change-Id: I0746fa2b60917398b49bf685bfd51a1aa903de29 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6072813 
Commit-Queue: Stephen Röttger <sroettger@google.com> 
Reviewed-by: Jakob Kummerow <jkummerow@chromium.org> 
Reviewed-by: Nico Hartmann <nicohartmann@chromium.org> 
Cr-Commit-Position: refs/heads/main@{#97718}
```

* * *

Files:

  * M `src/builtins/arm64/builtins-arm64.cc`
  * M `src/builtins/builtins-wasm-gen.cc`
  * M `src/builtins/builtins-wasm-gen.h`
  * M `src/builtins/wasm.tq`
  * M `src/builtins/x64/builtins-x64.cc`
  * M `src/codegen/arm/macro-assembler-arm.cc`
  * M `src/codegen/arm64/macro-assembler-arm64.cc`
  * M `src/codegen/arm64/macro-assembler-arm64.h`
  * M `src/codegen/bailout-reason.h`
  * M `src/codegen/external-reference.cc`
  * M `src/codegen/external-reference.h`
  * M `src/codegen/ia32/macro-assembler-ia32.cc`
  * M `src/codegen/x64/macro-assembler-x64.cc`
  * M `src/codegen/x64/macro-assembler-x64.h`
  * M `src/common/code-memory-access.cc`
  * M `src/common/code-memory-access.h`
  * M `src/compiler/backend/arm64/code-generator-arm64.cc`
  * M `src/compiler/backend/instruction-selector.cc`
  * M `src/compiler/backend/instruction.h`
  * M `src/compiler/backend/x64/code-generator-x64.cc`
  * M `src/compiler/linkage.cc`
  * M `src/compiler/linkage.h`
  * M `src/compiler/pipeline.cc`
  * M `src/compiler/wasm-compiler-definitions.cc`
  * M `src/compiler/wasm-compiler.cc`
  * M `src/heap/factory.cc`
  * M `src/heap/factory.h`
  * M `src/wasm/DEPS`
  * M `src/wasm/baseline/arm/liftoff-assembler-arm-inl.h`
  * M `src/wasm/baseline/arm64/liftoff-assembler-arm64-inl.h`
  * M `src/wasm/baseline/ia32/liftoff-assembler-ia32-inl.h`
  * M `src/wasm/baseline/liftoff-assembler.h`
  * M `src/wasm/baseline/liftoff-compiler.cc`
  * M `src/wasm/baseline/x64/liftoff-assembler-x64-inl.h`
  * M `src/wasm/c-api.cc`
  * M `src/wasm/function-compiler.cc`
  * M `src/wasm/function-compiler.h`
  * M `src/wasm/module-compiler.cc`
  * M `src/wasm/signature-hashing.h`
  * M `src/wasm/turboshaft-graph-interface.cc`
  * M `src/wasm/turboshaft-graph-interface.h`
  * M `src/wasm/wasm-code-manager.cc`
  * M `src/wasm/wasm-code-manager.h`
  * M `src/wasm/wasm-code-pointer-table-inl.h`
  * M `src/wasm/wasm-code-pointer-table.cc`
  * M `src/wasm/wasm-code-pointer-table.h`
  * M `src/wasm/wasm-import-wrapper-cache.cc`
  * M `src/wasm/wasm-import-wrapper-cache.h`
  * M `src/wasm/wasm-js.cc`
  * M `src/wasm/wasm-objects.cc`
  * M `src/wasm/wasm-objects.h`
  * M `src/wasm/wasm-objects.tq`
  * M `src/wasm/wrappers.cc`
  * M `test/cctest/compiler/test-code-generator.cc`
  * M `test/cctest/compiler/test-multiple-return.cc`
  * M `test/cctest/wasm/test-c-wasm-entry.cc`
  * M `test/cctest/wasm/wasm-run-utils.cc`
  * M `test/cctest/wasm/wasm-run-utils.h`
  * M `test/fuzzer/multi-return.cc`

* * *

Hash: 58f407806ad0ea83d8174dd701ba4b84c3cca14f  
Date: Tue Dec 10 18:02:39 2024

* * *


---

**#23 — ap...@google.com — Dec 16, 2024 05:29PM**

Project: v8/v8  
Branch: main  
Author: Lu Yahan <[yahan@iscas.ac.cn](<mailto:yahan@iscas.ac.cn>)>  
Link: [https://chromium-review.googlesource.com/6094084](<https://chromium-review.googlesource.com/6094084>)

[riscv][sandbox][wasm] add signature checks to the code pointer table

* * *

Expand for full commit details

```
[riscv][sandbox][wasm] add signature checks to the code pointer table 
 
Port commit 58f407806ad0ea83d8174dd701ba4b84c3cca14f 
 
Fixed: 350292240 
Change-Id: I9fdd617865cdb4723cdcd750a07588bcf11c1454 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6094084 
Commit-Queue: Yahan Lu (LuYahan) <yahan@iscas.ac.cn> 
Reviewed-by: Jakob Kummerow <jkummerow@chromium.org> 
Reviewed-by: Ji Qiu <qiuji@iscas.ac.cn> 
Auto-Submit: Yahan Lu (LuYahan) <yahan@iscas.ac.cn> 
Cr-Commit-Position: refs/heads/main@{#97784}
```

* * *

Files:

  * M `src/builtins/riscv/builtins-riscv.cc`
  * M `src/codegen/riscv/macro-assembler-riscv.cc`
  * M `src/codegen/riscv/macro-assembler-riscv.h`
  * M `src/compiler/backend/riscv/code-generator-riscv.cc`
  * M `src/wasm/DEPS`
  * M `src/wasm/baseline/riscv/liftoff-assembler-riscv-inl.h`

* * *

Hash: 08a2541bb31eab179c0eae11903af8479ee0f5d8  
Date: Mon Dec 16 16:24:06 2024

* * *


---

**#24 — ap...@google.com — Dec 19, 2024 12:52AM**

Project: v8/v8  
Branch: main  
Author: Stephen Roettger <[sroettger@google.com](<mailto:sroettger@google.com>)>  
Link: [https://chromium-review.googlesource.com/6105853](<https://chromium-review.googlesource.com/6105853>)

[wasm][sandbox][x64] single abort for signature check

* * *

Expand for full commit details

```
[wasm][sandbox][x64] single abort for signature check 
 
Bug: 350292240 
Change-Id: Id20ee3d8a70316fc188e1ee6a1b72031a7b74a06 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6105853 
Reviewed-by: Jakob Kummerow <jkummerow@chromium.org> 
Commit-Queue: Stephen Röttger <sroettger@google.com> 
Cr-Commit-Position: refs/heads/main@{#97860}
```

* * *

Files:

  * M `src/codegen/x64/macro-assembler-x64.cc`

* * *

Hash: 58283795f2223422d3f83e3498288c5037d8b5e3  
Date: Wed Dec 18 16:18:13 2024

* * *


---

**#25 — sp...@google.com — Dec 19, 2024 06:56AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $20000.00 for this report.  
  
Rationale for this decision:  
V8 sandbox bypass reward for demonstration of controlled write outside the V8 sandbox   
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#26 — am...@chromium.org — Dec 19, 2024 09:09AM**

Congratulations Seunghyun! Thank you for this excellent report of another V8 sandbox bypass -- great work!


---

**#27 — ap...@google.com — Dec 19, 2024 01:48PM**

Project: v8/v8  
Branch: main  
Author: Lu Yahan <[yahan@iscas.ac.cn](<mailto:yahan@iscas.ac.cn>)>  
Link: [https://chromium-review.googlesource.com/6100531](<https://chromium-review.googlesource.com/6100531>)

[riscv][isolate-groups][sandbox] Move JS dispatch table into isolate group

* * *

Expand for full commit details

```
[riscv][isolate-groups][sandbox] Move JS dispatch table into isolate group 
 
Port commit 58f407806ad0ea83d8174dd701ba4b84c3cca14f 
Fixed: 350292240 
 
Change-Id: I1264f1d145d4e6370ca7ca951a4ad47c982b39d2 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6100531 
Reviewed-by: Ji Qiu <qiuji@iscas.ac.cn> 
Auto-Submit: Yahan Lu (LuYahan) <yahan@iscas.ac.cn> 
Commit-Queue: Yahan Lu (LuYahan) <yahan@iscas.ac.cn> 
Cr-Commit-Position: refs/heads/main@{#97868}
```

* * *

Files:

  * M `src/codegen/riscv/macro-assembler-riscv.cc`
  * M `src/wasm/baseline/riscv/liftoff-assembler-riscv-inl.h`

* * *

Hash: 044663d52cbf56ebdc515347d56f8500c4e1b534  
Date: Tue Dec 17 10:32:59 2024

* * *


---

**#28 — pe...@google.com — Jan 2, 2025 09:43PM**

Dear owner, thanks for fixing this bug. We've reopened it because:

  * It is not clear which CLs have ‘fixed’ (=required to consider the bug resolved; e.g. not logging) this bug. Please fill in the “Fixed By Code Changes” field with the appropriate Gerrit url to disambiguate using the following guidelines: 
    * If there are multiple CLs required, please list all.
    * If the fix landed in a third party library (v8, Dawn, etc), please list the third party commits - not the rolls.
    * If there are cherrypicks or back merges, please list the original commits which landed on HEAD.
    * If there is no relevant Gerrit link (i.e. the fix does not live in or roll into Chromium), please use the value ‘NA’.
    * If this is a non-browser ChromeOS-specific bug, please move it to component 1335705 in the Google issue tracker.
    * If this field requires human intervention for some reason, please add this bug to the hotlist id 6265590. After resolving the above issue(s), this bug can be marked closed again. Thanks for your time!


---

**#29 — pe...@google.com — Jan 3, 2025 05:59PM**

Dear owner, thanks for fixing this bug. We've reopened it because:

  * Some CLs listed in the “Fixed By Code Changes” field are invalid and have been removed. Please provide an appropriate Gerrit url that matches the pattern: `https://<host>-review.googlesource.com/c/<repo>/+/<change_number>` or use the value 'NA' and re-mark this bug as fixed. If this field requires human intervention for some reason, please add this bug to the hotlist id 6265590.After resolving the above issue(s), this bug can be marked closed again. Thanks for your time!


---

**#30 — ap...@google.com — Jan 15, 2025 01:07AM**

Project: v8/v8  
Branch: main  
Author: Stephen Roettger <[sroettger@google.com](<mailto:sroettger@google.com>)>  
Link: [https://chromium-review.googlesource.com/6174719](<https://chromium-review.googlesource.com/6174719>)

[wasm] gc NativeModules before EmptyStorageForTesting

* * *

Expand for full commit details

```
[wasm] gc NativeModules before EmptyStorageForTesting 
 
otherwise, the NativeModules might still reference the canonical types. 
This lead to a crash with crrev.com/c/6094047. 
 
Bug: 350292240 
Change-Id: I0c457e4d1f531d50232760e57fc13551965b5fac 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6174719 
Reviewed-by: Matthias Liedtke <mliedtke@chromium.org> 
Commit-Queue: Stephen Röttger <sroettger@google.com> 
Cr-Commit-Position: refs/heads/main@{#98101}
```

* * *

Files:

  * M `src/wasm/canonical-types.cc`
  * M `src/wasm/wasm-engine.h`
  * M `test/fuzzer/wasm/deopt.cc`
  * M `test/fuzzer/wasm/fuzzer-common.cc`
  * M `test/fuzzer/wasm/fuzzer-common.h`
  * M `test/fuzzer/wasm/init-expr.cc`

* * *

Hash: d45eee8a6957b718abab3bd268015dca512c6671  
Date: Tue Jan 14 14:19:20 2025

* * *


---

**#31 — ap...@google.com — Jan 15, 2025 03:47AM**

Project: v8/v8  
Branch: main  
Author: Stephen Roettger <[sroettger@google.com](<mailto:sroettger@google.com>)>  
Link: [https://chromium-review.googlesource.com/6175024](<https://chromium-review.googlesource.com/6175024>)

[wasm] guard NativeModuleCount with the mutex

* * *

Expand for full commit details

```
[wasm] guard NativeModuleCount with the mutex 
 
Bug: 350292240 
Change-Id: I8df0048a38c6b3ac40ce40a0b5ebc0ea63de53ee 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6175024 
Commit-Queue: Stephen Röttger <sroettger@google.com> 
Reviewed-by: Clemens Backes <clemensb@chromium.org> 
Cr-Commit-Position: refs/heads/main@{#98106}
```

* * *

Files:

  * M `src/wasm/wasm-engine.cc`
  * M `src/wasm/wasm-engine.h`
  * M `test/fuzzer/wasm/fuzzer-common.cc`

* * *

Hash: 0ba7a73ebde93f91a4ea2e2b806ef0f6d3a48861  
Date: Tue Jan 14 17:51:57 2025

* * *


---

**#32 — ch...@google.com — Apr 12, 2025 09:38PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
