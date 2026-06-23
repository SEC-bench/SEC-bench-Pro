# V8 Sandbox Bypass: Arbitrary code execution via interpreter-to-baseline OSR Code type confusion

Issue URL: https://issues.chromium.org/issues/429703123
VRP-Reward: 20000
Date: Jul 5, 2025 10:23PM


### VULNERABILITY DETAILS

#### Summary

V8 sandbox bypass, arbitrary native code execution (without JIT page overwrite) via OSR Code type confusion. Interpreter & builtins double-fetches `Code` from `sfi.trusted_function_data` where the interpreter asserts that it is a Code object but the builtin side never verifies this and re-fetches it with `kUnknownIndirectPointerTag`. This allows an attacker to confuse an `ExposedTrustedObject` as a Code object, ultimately resulting in a jump to arbitrary code pointer with arbitrary offsets.

This is a variant of [b/395659804](<https://issues.chromium.org/issues/395659804>).

#### Details

[b/395659804](<https://issues.chromium.org/issues/395659804>) demonstrated a second-order type confusion in OSR, resulting in a trivial arbitrary code execution. Similar issues exist on its OSR-to-baseline variant, `Builtins_InterpreterOnStackReplacement_ToBaseline`. Ignition invokes this on JumpLoop when it checks that `SharedFunctionInfoHasBaselineCode(sfi)`, translating to `TaggedIsCode(LoadSharedFunctionInfoTrustedData(sfi))`.

However, this `Code` object is fetched again from within the builtin:

```
void Builtins::Generate_InterpreterOnStackReplacement_ToBaseline(
    MacroAssembler* masm) {
  Label start;
  __ bind(&start);

  // Get function from the frame.
  Register closure = rdi;
  __ movq(closure, MemOperand(rbp, StandardFrameConstants::kFunctionOffset));

  // Get the InstructionStream object from the shared function info.
  Register code_obj = rbx;
  Register shared_function_info(code_obj);
  __ LoadTaggedField(
      shared_function_info,
      FieldOperand(closure, JSFunction::kSharedFunctionInfoOffset));

  ResetSharedFunctionInfoAge(masm, shared_function_info);

  __ LoadTrustedPointerField(
      code_obj,
      FieldOperand(shared_function_info,
                   SharedFunctionInfo::kTrustedFunctionDataOffset),
      kUnknownIndirectPointerTag, kScratchRegister);                      // [!] double-fetch with arbitrarily tagged trusted pointer

  // ...

  // Compute baseline pc for bytecode offset.
  Register get_baseline_pc = r11;
  __ LoadAddress(get_baseline_pc,
                 ExternalReference::baseline_pc_for_next_executed_bytecode());

  __ subq(kInterpreterBytecodeOffsetRegister,
          Immediate(BytecodeArray::kHeaderSize - kHeapObjectTag));

  // Get bytecode array from the stack frame.
  __ movq(kInterpreterBytecodeArrayRegister,
          MemOperand(rbp, InterpreterFrameConstants::kBytecodeArrayFromFp));
  __ pushq(kInterpreterAccumulatorRegister);
  {
    FrameScope scope(masm, StackFrame::INTERNAL);
    __ PrepareCallCFunction(3);
    __ movq(kCArgRegs[0], code_obj);
    __ movq(kCArgRegs[1], kInterpreterBytecodeOffsetRegister);
    __ movq(kCArgRegs[2], kInterpreterBytecodeArrayRegister);
    __ CallCFunction(get_baseline_pc, 3);                                 // [!] compute baseline OSR jump offset
  }
  __ LoadCodeInstructionStart(code_obj, code_obj, kJSEntrypointTag);      // [!] loads from CPT using self indirect pointer, which may be a TPT entry
  __ addq(code_obj, kReturnRegister0);
  __ popq(kInterpreterAccumulatorRegister);

  Generate_OSREntry(masm, code_obj);

  // ...
}
```

It even uses `kUnknownIndirectPointerTag`, which means that an attacker can replace this with any code pointer or even with an arbitrary exposed trusted pointer. Execution continues on, where BytecodeArray and bytecode offset stored within the current interpreter frame is used together with the supposed Code object to compute the baseline PC matching that of the next bytecode to execute.

```
uintptr_t Code::GetBaselinePCForNextExecutedBytecode(
    int bytecode_offset, Tagged<BytecodeArray> bytecodes) {
  DisallowGarbageCollection no_gc;
  CHECK_EQ(kind(), CodeKind::BASELINE);
  baseline::BytecodeOffsetIterator offset_iterator(
      Cast<TrustedByteArray>(bytecode_offset_table()), bytecodes);
  Handle<BytecodeArray> bytecodes_handle(
      reinterpret_cast<Address*>(&bytecodes));
  interpreter::BytecodeArrayIterator bytecode_iterator(bytecodes_handle,
                                                       bytecode_offset);
  interpreter::Bytecode bytecode = bytecode_iterator.current_bytecode();
  if (bytecode == interpreter::Bytecode::kJumpLoop) {
    return GetBaselineStartPCForBytecodeOffset(
        bytecode_iterator.GetJumpTargetOffset(), bytecodes);
  } // ...
}

uintptr_t Code::GetBaselineStartPCForBytecodeOffset(
    int bytecode_offset, Tagged<BytecodeArray> bytecodes) {
  return GetBaselinePCForBytecodeOffset(bytecode_offset, kPcAtStartOfBytecode,
                                        bytecodes);
}

uintptr_t Code::GetBaselinePCForBytecodeOffset(
    int bytecode_offset, BytecodeToPCPosition position,
    Tagged<BytecodeArray> bytecodes) {
  DisallowGarbageCollection no_gc;
  CHECK_EQ(kind(), CodeKind::BASELINE);
  // The following check ties together the bytecode being executed in
  // Generate_BaselineOrInterpreterEntry with the bytecode that was used to
  // compile this baseline code. Together, this ensures that we don't OSR into a
  // wrong code object.
  auto maybe_bytecodes = bytecode_or_interpreter_data();
  if (IsBytecodeArray(maybe_bytecodes)) {
    SBXCHECK_EQ(maybe_bytecodes, bytecodes);
  } else {
    CHECK(IsInterpreterData(maybe_bytecodes));
    SBXCHECK_EQ(Cast<InterpreterData>(maybe_bytecodes)->bytecode_array(),
                bytecodes);
  }
  baseline::BytecodeOffsetIterator offset_iterator(
      Cast<TrustedByteArray>(bytecode_offset_table()), bytecodes);
  offset_iterator.AdvanceToBytecodeOffset(bytecode_offset);
  uintptr_t pc = 0;
  if (position == kPcAtStartOfBytecode) {
    pc = offset_iterator.current_pc_start_offset();
  } else {
    DCHECK_EQ(position, kPcAtEndOfBytecode);
    pc = offset_iterator.current_pc_end_offset();
  }
  return pc;
}
```

We see a huge amount of `(SBX)CHECK`s since any discrepancy between Code and bytecode may result in invalid offset computation. What is being checked is notably the following:

  1. `code->kind() == CodeKind::BASELINE`
  2. `code->bytecode_or_interpreter_data()` is either: 
     * `BytecodeArray` and is equivalent to `bytecodes` from the interpreter frame
     * `InterpreterData` and its `bytecode_array()` is equivalent to `bytecodes`

Note that none of these checks assert that `this` is actually a `Code` object, which in this case the caller failed to assert. Thus, an attacker may meticulously craft a fake `Code` object using an `ExposedTrustedObject` such that all the checks pass.

Assuming that the attacker is able to bypass all of the checks, this grants the ability to indirectly control:

  1. `bytecode_offset_table()`, a `TrustedByteArray` consisting of VLQ-encoded baseline PC sizes for each bytecode ops, used to compute baseline OSR offset
  2. Target code pointer, as the self indirect pointer of the supposed Code object could instead be a TrustedPointer for an ExposedTrustedObject

The attached exploit demonstrates the use of `WasmDispatchTable` to satisfy these constraints along with some trusted heap shaping techniques, then uses this to jump to an invalid offset with the same code pointer such that it jumps to an immediate value encoding `nop; nop; ud2;`. Due to some constraints some constants are baked in based on the tested version and the specific repro code.

### VERSION

V8: Tested on `d8-sandbox-testing-linux-release-v8-component-101269`

### REPRODUCTION CASE

Attached as `osr-to-baseline-code-confusion.js`, run with `./d8 --sandbox-testing`.

The repro attempts arbitrary code execution of `nop; nop; ud2` compiled as part of baseline JIT which results in a `SIGILL` with `ILL_ILLOPN`.

Likely will not repro on other versions, with code modifications or with other flags, unless some constants are modified as needed (`OSR_FUNC_BYTECODE`, `target_initial/target_capacity`, fake VLQ-encoded offset table @ `spray_fn_str`, ...)

### FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION

Type of crash: Sandbox violation

### CREDIT INFORMATION

Reporter credit: Seunghyun Lee (@0x10n) of CMU CyLab


---

**#2 — pg...@google.com — Jul 7, 2025 10:58PM**

Olivier, can you take a look? skipping the sheriff, setting preliminary (S2 P1, ) since this is a variant (:


---

**#3 — ol...@chromium.org — Jul 8, 2025 11:09PM**

Nice work and reliable repro. The fix is in review.


---

**#4 — ol...@chromium.org — Jul 9, 2025 12:53AM**

Follow-up suggestions:

  * Review all uses of `kUnknownIndirectPointerTag`
  * See if we could afford implicit type checks on all `Cast<TrustedObject>(x)`


---

**#5 — dx...@google.com — Jul 9, 2025 01:24AM**

Project: v8/v8  
Branch: main  
Author: Olivier Flückiger [olivf@chromium.org](<mailto:olivf@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6714868](<https://chromium-review.googlesource.com/6714868>)

[builtins] Use correct pointer tag in OSR after we checked

* * *

Expand for full commit details

```
     
    After checking that the trusted_function_data_offset is actually a code 
    object we must use the correct tag to reload it. This prevents its type 
    to change between the double fetches. 
     
    Bug: 429703123 
    Change-Id: Iac860e6daf93d0e20dc21948e9a9cc252d43dc43 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6714868 
    Reviewed-by: Samuel Groß <saelo@chromium.org> 
    Commit-Queue: Olivier Flückiger <olivf@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#101311}
```

* * *

Files:

  * M `src/builtins/arm64/builtins-arm64.cc`
  * M `src/builtins/loong64/builtins-loong64.cc`
  * M `src/builtins/ppc/builtins-ppc.cc`
  * M `src/builtins/riscv/builtins-riscv.cc`
  * M `src/builtins/x64/builtins-x64.cc`

* * *

Hash: ebf22f9a925a45549a6124158ad935d624e7bf8f  
Date: Tue Jul 8 15:41:37 2025

* * *


---

**#6 — dx...@google.com — Jul 9, 2025 01:25AM**

Project: v8/v8  
Branch: main  
Author: Olivier Flückiger [olivf@chromium.org](<mailto:olivf@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6714904](<https://chromium-review.googlesource.com/6714904>)

[builtins] Additional checks when computing baseline osr offsets

* * *

Expand for full commit details

```
     
    Additional checks to ensure we have the object type we expect when 
    interacting with the SFI::trusted_function_data from builtins. 
     
    Drive-By: 
    * Remove unused baseline_pc_for_bytecode_offset 
    * Remove dangerous CheckSharedFunctionInfoBytecodeOrBaseline since it 
      only does a partial check. 
     
    Bug: 429703123 
    Change-Id: I15eff7d48b87704e78a17aaa61781aafebb8bcae 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6714904 
    Auto-Submit: Olivier Flückiger <olivf@chromium.org> 
    Reviewed-by: Samuel Groß <saelo@chromium.org> 
    Commit-Queue: Olivier Flückiger <olivf@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#101312}
```

* * *

Files:

  * M `src/builtins/arm64/builtins-arm64.cc`
  * M `src/builtins/x64/builtins-x64.cc`
  * M `src/codegen/external-reference.cc`
  * M `src/codegen/external-reference.h`

* * *

Hash: 5528bede4a1dd511436772370d1129d172db1293  
Date: Tue Jul 8 15:43:47 2025

* * *


---

**#7 — ch...@google.com — Jul 9, 2025 01:59AM**

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

**#8 — ch...@google.com — Jul 9, 2025 01:59AM**

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

**#9 — dx...@google.com — Jul 11, 2025 10:39AM**

Project: v8/v8  
Branch: main  
Author: Lu Yahan [yahan@iscas.ac.cn](<mailto:yahan@iscas.ac.cn>)  
Link: [https://chromium-review.googlesource.com/6715563](<https://chromium-review.googlesource.com/6715563>)

[riscv][builtins] Additional checks when computing baseline osr offsets

* * *

Expand for full commit details

```
     
    Port commit 5528bede4a1dd511436772370d1129d172db1293 
    Bug: 429703123 
     
    Change-Id: I451026836fe3d2c6497585abca46a9c34b7bc91e 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6715563 
    Auto-Submit: Yahan Lu (LuYahan) <yahan@iscas.ac.cn> 
    Reviewed-by: Kasper Lund <kasperl@rivosinc.com> 
    Commit-Queue: Yahan Lu (LuYahan) <yahan@iscas.ac.cn> 
    Cr-Commit-Position: refs/heads/main@{#101355}
```

* * *

Files:

  * M `src/builtins/riscv/builtins-riscv.cc`
  * M `src/codegen/riscv/macro-assembler-riscv.cc`
  * M `src/codegen/riscv/macro-assembler-riscv.h`

* * *

Hash: 60a7a31d70cee08c1d1b7fdebdd3d8805773d1f6  
Date: Thu Jul 10 01:55:05 2025

* * *


---

**#10 — ol...@chromium.org — Jul 11, 2025 09:18PM**

re. merge review:

  1. security. it's a V8 sandbox escape
  2. [https://chromium-review.googlesource.com/6714868](<https://chromium-review.googlesource.com/6714868>)
  3. y 4-6. n


---

**#11 — am...@chromium.org — Jul 18, 2025 07:44AM**

merges approved for [https://crrev.com/c/6714868](<https://crrev.com/c/6714868>)

Please merge this fix to 13.9 and 13.8 by EOD tomorrow / Friday, so this fix can be included in the next M138 Stable update and M139 Stable RC cut on Tuesday.

There are other CLs associated with this issue, based on the response to the merge review questionnaire I presume they are not security critical for backmerge. If this is incorrect, please reach out to security and we'll review other necessary CLs for potential backmerge. If multiple CLs are required for security mitigation, this may be strictly deferred to Beta release at this juncture.


---

**#12 — dx...@google.com — Jul 18, 2025 10:20PM**

Project: v8/v8  
Branch: refs/branch-heads/13.8  
Author: Olivier Flückiger [olivf@chromium.org](<mailto:olivf@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6769985](<https://chromium-review.googlesource.com/6769985>)

Merged: [builtins] Use correct pointer tag in OSR after we checked

* * *

Expand for full commit details

```
     
    After checking that the trusted_function_data_offset is actually a code 
    object we must use the correct tag to reload it. This prevents its type 
    to change between the double fetches. 
     
    Bug: 429703123 
    (cherry picked from commit ebf22f9a925a45549a6124158ad935d624e7bf8f) 
     
    Change-Id: I81a5f4cf5875f8efae062ed62b6eaf0664a620ad 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6769985 
    Auto-Submit: Olivier Flückiger <olivf@chromium.org> 
    Commit-Queue: Olivier Flückiger <olivf@chromium.org> 
    Reviewed-by: Samuel Groß <saelo@chromium.org> 
    Commit-Queue: Samuel Groß <saelo@chromium.org> 
    Cr-Commit-Position: refs/branch-heads/13.8@{#55} 
    Cr-Branched-From: 61ddd471ece346840bbebbb308dceb4b4ce31b28-refs/heads/13.8.258@{#1} 
    Cr-Branched-From: fdb5de2c741658e94944f2ec1218530e98601c23-refs/heads/main@{#100480}
```

* * *

Files:

  * M `src/builtins/arm64/builtins-arm64.cc`
  * M `src/builtins/loong64/builtins-loong64.cc`
  * M `src/builtins/ppc/builtins-ppc.cc`
  * M `src/builtins/riscv/builtins-riscv.cc`
  * M `src/builtins/x64/builtins-x64.cc`

* * *

Hash: [bbdf73f97c5c7def72b8cacbdeb3e99e1c554fc9](<http://crrev.com/bbdf73f97c5c7def72b8cacbdeb3e99e1c554fc9>)  
Date: Tue Jul 8 15:41:37 2025

* * *


---

**#13 — dx...@google.com — Jul 18, 2025 10:22PM**

Project: v8/v8  
Branch: refs/branch-heads/13.9  
Author: Olivier Flückiger [olivf@chromium.org](<mailto:olivf@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6769984](<https://chromium-review.googlesource.com/6769984>)

Merged: [builtins] Use correct pointer tag in OSR after we checked

* * *

Expand for full commit details

```
     
    After checking that the trusted_function_data_offset is actually a code 
    object we must use the correct tag to reload it. This prevents its type 
    to change between the double fetches. 
     
    Bug: 429703123 
    (cherry picked from commit ebf22f9a925a45549a6124158ad935d624e7bf8f) 
     
    Change-Id: I1193fa180b659dc888d7aa484f386faca815dacc 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6769984 
    Commit-Queue: Olivier Flückiger <olivf@chromium.org> 
    Commit-Queue: Samuel Groß <saelo@chromium.org> 
    Auto-Submit: Olivier Flückiger <olivf@chromium.org> 
    Reviewed-by: Samuel Groß <saelo@chromium.org> 
    Cr-Commit-Position: refs/branch-heads/13.9@{#22} 
    Cr-Branched-From: 76ea4091129171336d347c2624f6062bd9708042-refs/heads/13.9.205@{#1} 
    Cr-Branched-From: 28242121f590fe04758efec176658cd57310b297-refs/heads/main@{#100941}
```

* * *

Files:

  * M `src/builtins/arm64/builtins-arm64.cc`
  * M `src/builtins/loong64/builtins-loong64.cc`
  * M `src/builtins/ppc/builtins-ppc.cc`
  * M `src/builtins/riscv/builtins-riscv.cc`
  * M `src/builtins/x64/builtins-x64.cc`

* * *

Hash: [26af7c26bdb5e470377109506a8cecfc77888e76](<http://crrev.com/26af7c26bdb5e470377109506a8cecfc77888e76>)  
Date: Tue Jul 8 15:41:37 2025

* * *


---

**#14 — ol...@chromium.org — Jul 18, 2025 10:39PM**

Ok, all necessary merges for 138 and 139 are done.


---

**#15 — ch...@google.com — Jul 21, 2025 09:42PM**

This issue has been approved for a merge. Please merge the fix to any appropriate branches as soon as possible!

Thanks for your time! To disable nags, add Disable-Nags (case sensitive) to the Chromium Labels custom field.


---

**#16 — ch...@google.com — Jul 21, 2025 09:42PM**

This issue has been approved for a merge. Please merge the fix to any appropriate branches as soon as possible!

Thanks for your time! To disable nags, add Disable-Nags (case sensitive) to the Chromium Labels custom field.


---

**#17 — sp...@google.com — Jul 22, 2025 05:55AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $20000.00 for this report.  
  
Rationale for this decision:  
report of V8 sandbox bypass demonstrating arbitrary code execution outside the V8 heap sandbox  
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#18 — am...@chromium.org — Jul 22, 2025 06:27AM**

Congratulations! Thank you for your efforts hunting in the V8 sandbox and reporting this issue to us -- nice work!


---

**#19 — se...@gmail.com — Jul 23, 2025 02:47PM**

As usual, please mark the rewards towards charity, thanks!


---

**#20 — ch...@google.com — Oct 15, 2025 09:49PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
