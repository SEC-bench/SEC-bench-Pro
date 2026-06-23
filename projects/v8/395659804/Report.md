# V8 Sandbox Bypass: Arbitrary code execution via OSR DeoptimizationData confusion

Issue URL: https://issues.chromium.org/issues/395659804
VRP-Reward: 20000
Date: Feb 11, 2025 12:40PM


### VULNERABILITY DETAILS

#### Summary

V8 sandbox bypass, arbitrary native code execution (without JIT page overwrite) via on-stack replacement `DeoptimizationData` confusion with `BytecodeArray`. This is due to the broken assumption that the `Code` object to be OSR'd into is tier-up compiled, which may instead be swapped out by an attacker with a baseline `Code` object.

#### Details

(Lengthy code follows, if already familiar with OSR skip two code snippets below)

JS interpreter implements OSR on `JumpLoop` to replace the currently executing code and its corresponding frame state into a tiered-up one. This is implemented in the following codes:

```
// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/interpreter/interpreter-generator.cc;drc=645888ea0178c3678d5486e34ce2a84b68254558;l=2427
// JumpLoop <imm> <loop_depth>
//
// Jump by the number of bytes represented by the immediate operand |imm|. Also
// performs a loop nesting check, a stack check, and potentially triggers OSR.
IGNITION_HANDLER(JumpLoop, InterpreterAssembler) {
  TNode<IntPtrT> relative_jump = Signed(BytecodeOperandUImmWord(0));
  // ...
#ifndef V8_JITLESS
  TVARIABLE(HeapObject, maybe_feedback_vector);
  Label ok(this);
  Label fbv_loaded(this);

  // Load FeedbackVector from Cache.
  maybe_feedback_vector = LoadFeedbackVector();                              // [!] FeedbackVector, in-sandbox
  // If cache is empty, try to load from function closure.
  GotoIfNot(IsUndefined(maybe_feedback_vector.value()), &fbv_loaded);
  maybe_feedback_vector =
      CodeStubAssembler::LoadFeedbackVector(LoadFunctionClosure(), &ok);
  // Update feedback vector stack cache.
  StoreRegister(maybe_feedback_vector.value(), Register::feedback_vector());
  Goto(&fbv_loaded);

  BIND(&fbv_loaded);

  TNode<FeedbackVector> feedback_vector = CAST(maybe_feedback_vector.value());
  TNode<Int8T> osr_state = LoadOsrState(feedback_vector);
  TNode<Int32T> loop_depth = BytecodeOperandImm(1);

  Label maybe_osr_because_osr_state(this, Label::kDeferred);
  // ...
  GotoIfNot(Uint32GreaterThanOrEqual(loop_depth, osr_state),                 // [!] Loop count exceeded threshold, trigger OSR
            &maybe_osr_because_osr_state);

  // Perhaps we've got cached baseline code?
  Label maybe_osr_because_baseline(this);
  TNode<SharedFunctionInfo> sfi = LoadObjectField<SharedFunctionInfo>(
      LoadFunctionClosure(), JSFunction::kSharedFunctionInfoOffset);
  Branch(SharedFunctionInfoHasBaselineCode(sfi), &maybe_osr_because_baseline,
         &ok);
  // ...
  BIND(&maybe_osr_because_osr_state);
  {
    TNode<Context> context = GetContext();
    TNode<IntPtrT> slot_index = Signed(BytecodeOperandIdx(2));
    OnStackReplacement(context, feedback_vector, relative_jump, loop_depth,  // [!] OSR
                       slot_index, osr_state,
                       OnStackReplacementParams::kDefault);
  }
#endif  // !V8_JITLESS
}

// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/interpreter/interpreter-assembler.cc;drc=14c99e9cdd960bc5e9bf6c7bcfcf8e17e804a493;l=1402
void InterpreterAssembler::OnStackReplacement(
    TNode<Context> context, TNode<FeedbackVector> feedback_vector,
    TNode<IntPtrT> relative_jump, TNode<Int32T> loop_depth,
    TNode<IntPtrT> feedback_slot, TNode<Int8T> osr_state,
    OnStackReplacementParams params) {
  // Three cases may cause us to attempt OSR, in the following order:
  //
  // 1) Presence of cached OSR Turbofan/Maglev code.
  // 2) Presence of cached OSR Sparkplug code.
  // 3) The OSR urgency exceeds the current loop depth - in that case, trigger
  //    a Turbofan OSR compilation.

  TVARIABLE(Object, maybe_target_code, SmiConstant(0));
  Label osr_to_opt(this), osr_to_sparkplug(this);

  // Case 1).
  {
    Label next(this);
    TNode<MaybeObject> maybe_cached_osr_code =
        LoadFeedbackVectorSlot(feedback_vector, feedback_slot);
    GotoIf(IsCleared(maybe_cached_osr_code), &next);
    maybe_target_code = GetHeapObjectAssumeWeak(maybe_cached_osr_code);

    // Is it marked_for_deoptimization? If yes, clear the slot.
    TNode<CodeWrapper> code_wrapper = CAST(maybe_target_code.value());
    maybe_target_code =
        LoadCodePointerFromObject(code_wrapper, CodeWrapper::kCodeOffset);   // [!] target code load from FeedbackVector -> CodeWrapper -> Code handle
    GotoIfNot(IsMarkedForDeoptimization(CAST(maybe_target_code.value())),
              &osr_to_opt);
    StoreFeedbackVectorSlot(feedback_vector, Unsigned(feedback_slot),
                            ClearedValue(), UNSAFE_SKIP_WRITE_BARRIER);
    maybe_target_code = SmiConstant(0);

    Goto(&next);
    BIND(&next);
  }

  // Case 2).
  if (params == OnStackReplacementParams::kBaselineCodeIsCached) {
    Goto(&osr_to_sparkplug);
  } else {
    DCHECK_EQ(params, OnStackReplacementParams::kDefault);
    TNode<SharedFunctionInfo> sfi = LoadObjectField<SharedFunctionInfo>(
        LoadFunctionClosure(), JSFunction::kSharedFunctionInfoOffset);
    GotoIf(SharedFunctionInfoHasBaselineCode(sfi), &osr_to_sparkplug);

    // Case 3).
    {
      static_assert(FeedbackVector::OsrUrgencyBits::kShift == 0);
      TNode<Int32T> osr_urgency = Word32And(
          osr_state, Int32Constant(FeedbackVector::OsrUrgencyBits::kMask));
      GotoIf(Uint32LessThan(loop_depth, osr_urgency), &osr_to_opt);          // [!] needs OSR, taken
      JumpBackward(relative_jump);
    }
  }

  BIND(&osr_to_opt);
  {
    TNode<BytecodeArray> bytecode = BytecodeArrayTaggedPointer();
    TNode<Uint32T> length = LoadAndUntagBytecodeArrayLength(bytecode);
    TNode<Uint32T> weight =
        Uint32Mul(length, Uint32Constant(v8_flags.osr_to_tierup));
    DecreaseInterruptBudget(Signed(weight), kDisableStackCheck);
    TNode<Smi> expected_param_count =
        SmiFromInt32(LoadBytecodeArrayParameterCount(bytecode));
    CallBuiltin(Builtin::kInterpreterOnStackReplacement, context,            // [!] OSR with target code
                maybe_target_code.value(), expected_param_count);
    UpdateInterruptBudget(Int32Mul(Signed(weight), Int32Constant(-1)));
    JumpBackward(relative_jump);
  }

  BIND(&osr_to_sparkplug);
  {
    // ...
  }
}
```

Note that we can fully control the `Code` given to the builtin OSR function. The function looks like below:

```
// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/builtins/x64/builtins-x64.cc;drc=14c99e9cdd960bc5e9bf6c7bcfcf8e17e804a493;l=3068
void Builtins::Generate_InterpreterOnStackReplacement(MacroAssembler* masm) {
  using D = OnStackReplacementDescriptor;
  static_assert(D::kParameterCount == 2);
  OnStackReplacement(masm, OsrSourceTier::kInterpreter,
                     D::MaybeTargetCodeRegister(),
                     D::ExpectedParameterCountRegister());
}

// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/builtins/x64/builtins-x64.cc;drc=14c99e9cdd960bc5e9bf6c7bcfcf8e17e804a493;l=2971
void OnStackReplacement(MacroAssembler* masm, OsrSourceTier source,
                        Register maybe_target_code,
                        Register expected_param_count) {
  Label jump_to_optimized_code;
  {
    // If maybe_target_code is not null, no need to call into runtime. A
    // precondition here is: if maybe_target_code is an InstructionStream
    // object, it must NOT be marked_for_deoptimization (callers must ensure
    // this).
    __ testq(maybe_target_code, maybe_target_code);
    __ j(not_equal, &jump_to_optimized_code, Label::kNear);                       // [!] taken if Code given
  }
  // ...
  if (source == OsrSourceTier::kInterpreter) {
    // Drop the handler frame that is be sitting on top of the actual
    // JavaScript frame.
    __ leave();
  }

  // Check the target has a matching parameter count. This ensures that the OSR
  // code will correctly tear down our frame when leaving.
  __ movzxwq(scratch,
             FieldOperand(maybe_target_code, Code::kParameterCountOffset));
  __ SmiUntag(expected_param_count);
  __ cmpq(scratch, expected_param_count);
  __ SbxCheck(Condition::equal, AbortReason::kOsrUnexpectedStackSize);            // [!] sbxcheck with code param count (for stack compat, b/354724082 and b/374812612)

  __ LoadProtectedPointerField(
      scratch, FieldOperand(maybe_target_code,
                            Code::kDeoptimizationDataOrInterpreterDataOffset));   // [!] assumes DeoptimizationData

  // Load the OSR entrypoint offset from the deoptimization data.
  __ SmiUntagField(
      scratch,
      FieldOperand(scratch, TrustedFixedArray::OffsetOfElementAt(
                                DeoptimizationData::kOsrPcOffsetIndex)));         // [!] assumes DeoptimizationData, but may be BytecodeArray or InterpreterData instead

  __ LoadCodeInstructionStart(maybe_target_code, maybe_target_code,
                              kJSEntrypointTag);

  // Compute the target address = code_entry + osr_offset
  __ addq(maybe_target_code, scratch);                                            // [!] uses type confused `scratch` field as osr_offset

  Generate_OSREntry(masm, maybe_target_code);                                     // [!] arbitrary offset call from other code (e.g. baseline-compiled)
}
```

Note how an attacker may forge the chain of `FeedbackVector -> CodeWrapper -> Code handle` to point it to a `Code` that is not tiered up with an optimizing compiler (i.e. `Code` is either interpreted or baseline compiled). This leads to OSR functions to mistakenly assume that the `Code` object has a `DeoptimizationData` in the offset of `Code::kDeoptimizationDataOrInterpreterDataOffset`, which as its name implies can be `BytecodeArray` for baseline compiled code and `InterpreterData` for interpreted code.

This can easily be exploited to obtain arbitrary code execution - by baseline JIT compiling a function with constant `smi`s for JIT sprays, then triggering an OSR with the baseline JIT compiled `Code` as described above we can jump to attacker-controlled offset within the baseline JIT compiled code. This is due to the very neat field alignment of `BytecodeArray::kFrameSizeOffset == DeoptimizationData::kOsrPcOffsetIndex`, where frame size is easily controlled by the number of local variables declared within the function.

Note how this exploits a "second-order" type confusion between `Code` object fields, and the introduced `SbxCheck()` to check OSR stack size (fix for [b/354724082](<https://issues.chromium.org/issues/354724082>) and [b/374812612](<https://issues.chromium.org/issues/374812612>)) does not apply here as we can simply match parameter counts.

### VERSION

V8: Tested on CF asan / no-asan sandbox-testing d8 @ revision 98615 (commit [1d65fd3](<https://chromium-review.googlesource.com/c/v8/v8/+/6227080>))

### REPRODUCTION CASE

Attached as `osr-deoptdata-confusion.js`, run with `./d8 --sandbox-testing`.

The repro attempts arbitrary code execution of `nop; nop; ud2` sprayed as part of baseline JIT compiled code which results in a `SIGILL` with `ILL_ILLOPN`.

### FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION

Type of crash: Sandbox violation

### CREDIT INFORMATION

Reporter credit: Seunghyun Lee (@0x10n) of CMU CyLab

* * *

This was discovered with a v8 sandbox fuzzer.


---

**#2 — se...@gmail.com — Feb 11, 2025 12:45PM**

I think that a simple fix would be to `SbxCheck()` that `FieldOperand(maybe_target_code, Code::kDeoptimizationDataOrInterpreterDataOffset)` is indeed a `DeoptimizationData`, given that all `Code` objects' OSR entries are compatible with each other (which Leaptiering should guarantee IMO).


---

**#3 — th...@chromium.org — Feb 12, 2025 08:21AM**

Since this is a V8 sandbox bypass, setting a provisional severity of Medium (S2) + provisional priority of P1, assigning to the current V8 Sheriff sroettger@. Adding the Security_Impact-None hotlist and the V8 Sandbox hotlist.


---

**#4 — sr...@google.com — Feb 12, 2025 05:59PM**

leszeks@ could you take a look or do you know who would be a good assignee?

Maybe there's a generic solution for this problem? I.e. whenever we have a union in a trusted object, we should probably sbx check the type when we read it?


---

**#5 — le...@chromium.org — Feb 13, 2025 07:21PM**

Oli, can you take a look?


---

**#6 — ol...@chromium.org — Feb 14, 2025 01:21AM**

Ok, since the code object is a trusted object I would rather like to rely on it being un-tampered and not start typechecking its contents. Imho that's the whole premise of trusted objects.  
  
I have a CL that checks if the code object is a code object for OSR. Imho, that is the stronger guarantee and also excludes potential shenanigans with installing a non-osr code object (which won't do entry stack checks...).


---

**#7 — ol...@chromium.org — Feb 18, 2025 02:07AM**

Landed [https://chromium-review.googlesource.com/c/v8/v8/+/6264504](<https://chromium-review.googlesource.com/c/v8/v8/+/6264504>), not sure why it didn't show up here...


---

**#8 — ap...@google.com — Feb 18, 2025 09:24PM**

Project: v8/v8  
Branch: main  
Author: Olivier Flückiger <[olivf@chromium.org](<mailto:olivf@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6264505](<https://chromium-review.googlesource.com/6264505>)

[sandbox] Port "Ensure we only OSR to osr code"

* * *

Expand for full commit details

```
[sandbox] Port "Ensure we only OSR to osr code" 
 
port to loong64, mips64, riscv 
 
Bug: 395659804 
Change-Id: I5bbebf853629b4c7af350ff4c2ebc2a2cfb35c81 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6264505 
Reviewed-by: Leszek Swirski <leszeks@chromium.org> 
Commit-Queue: Leszek Swirski <leszeks@chromium.org> 
Auto-Submit: Olivier Flückiger <olivf@chromium.org> 
Cr-Commit-Position: refs/heads/main@{#98752}
```

* * *

Files:

  * M `src/builtins/loong64/builtins-loong64.cc`
  * M `src/builtins/mips64/builtins-mips64.cc`
  * M `src/builtins/riscv/builtins-riscv.cc`

* * *

Hash: f6a824b9fb4575da56988a3281d752ded9abc6e6  
Date: Thu Feb 13 17:09:04 2025

* * *


---

**#9 — sp...@google.com — Feb 27, 2025 09:55AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $20000.00 for this report.  
  
Rationale for this decision:  
V8 sandbox bypass allowing for arbitrary code execution   
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#10 — am...@chromium.org — Feb 27, 2025 10:10AM**

Congratulations Seunghyun! Thank you for your efforts hunting in the V8 sandbox -- great work on another well reported find!


---

**#11 — se...@gmail.com — Feb 27, 2025 05:23PM**

Thanks, and please also mark the reward for charity.


---

**#12 — ol...@chromium.org — Feb 27, 2025 05:42PM**

Congrats and thanks for the report!


---

**#13 — ch...@google.com — May 27, 2025 09:47PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
