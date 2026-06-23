# V8 Sandbox Bypass: Stack corruption via signature mismatch during call baseline code

Issue URL: https://issues.chromium.org/issues/417636716
VRP-Reward: 20000
Date: May 15, 2025 01:40AM


## VULNERABILITY DETAILS

When `shared_function_info.trusted_function_data` is `Code`, `Builtins_InterpreterEntryTrampoline` will call `Runtime_InstallBaselineCode` and jump to `code.instruction_start` of the returned code without checking the number of parameters.

```
void Builtins::Generate_InterpreterEntryTrampoline(
    MacroAssembler* masm, InterpreterEntryTrampolineMode mode) {
  // [...]
  GetSharedFunctionInfoBytecodeOrBaseline(
      masm, shared_function_info, kInterpreterBytecodeArrayRegister,
      kScratchRegister, &is_baseline, &compile_lazy);
  // [...]
  __ bind(&is_baseline);
  {
    // [...]
    __ GenerateTailCallToReturnedCode(Runtime::kInstallBaselineCode);
  }
  // [...]
}
```

However, only modifying `shared_function_info` will cause a crash at `function->UpdateCodeKeepTieringRequests(isolate, baseline_code);` in `Runtime_InstallBaselineCode`. A worker thread is needed to change `function.dispatch_handle` after the call of `Builtins_InterpreterEntryTrampoline` and before `GenerateTailCallToReturnedCode(Runtime::kInstallBaselineCode);`. If we can win the race, the stack can be corrupted by read and write arguments.

```
RUNTIME_FUNCTION(Runtime_InstallBaselineCode) {
  HandleScope scope(isolate);
  DCHECK_EQ(1, args.length());
  DirectHandle<JSFunction> function = args.at<JSFunction>(0);
  DirectHandle<SharedFunctionInfo> sfi(function->shared(), isolate);
  DCHECK(sfi->HasBaselineCode());
  {
    if (!V8_ENABLE_LEAPTIERING_BOOL || !function->has_feedback_vector()) {
      IsCompiledScope is_compiled_scope(*sfi, isolate);
      IsBaselineCompiledScope is_baseline_compiled_scope(*sfi, isolate);
      DCHECK(is_baseline_compiled_scope.is_compiled());
      DCHECK(!function->HasAvailableOptimizedCode(isolate));
      DCHECK(!function->has_feedback_vector());
      JSFunction::CreateAndAttachFeedbackVector(isolate, function,
                                                &is_compiled_scope);
    }
    DisallowGarbageCollection no_gc;
    Tagged<Code> baseline_code = sfi->baseline_code(kAcquireLoad);
    function->UpdateCodeKeepTieringRequests(isolate, baseline_code);
    return baseline_code;
  }
}
```

## VERSION

d8 commit `bb53a5d844b6020c7144e433166a98b1d7428b98`

## REPRODUCTION CASE

`./d8 --sandbox-testing --expose-gc ./baseline.js`

## FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION

Type of crash: v8 sandbox violation

## CREDIT INFORMATION

Reporter credit: Anonymous


---

**#2 — iw...@gmail.com — May 15, 2025 01:48AM**

The attached baseline.js uses Wasm to put `0x414141414141` on the stack, then reads `0x414141414141` from the stack and writes it to a `return address`. If all goes well, rip will be hijacked (like ROP).


---

**#3 — cl...@appspot.gserviceaccount.com — May 15, 2025 03:16AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=6314874573357056](<https://clusterfuzz.com/testcase?key=6314874573357056>).


---

**#4 — iw...@gmail.com — May 15, 2025 10:02AM**

Please use a d8 which is built with `v8_enable_memory_corruption_api = true` to reproduce. [https://clusterfuzz.com/testcase?key=6314874573357056](<https://clusterfuzz.com/testcase?key=6314874573357056>) used a wrong d8 build.


---

**#5 — cl...@appspot.gserviceaccount.com — May 16, 2025 01:53AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5280593231151104](<https://clusterfuzz.com/testcase?key=5280593231151104>).


---

**#6 — am...@chromium.org — May 16, 2025 02:21AM**

```
	+----------------------------------------Release Build Stacktrace----------------------------------------+

Sandbox testing mode is enabled. Only sandbox violations will be reported, all other crashes will be ignored.

  main: func_victim: 0x5eab9
  main: func_baseline_handle: 0x135500
  main: func_baseline_shared: 0x5e431
worker: func_victim: 0x5eab9
worker: func_baseline_handle: 0x135500
worker: racing
worker: victim patched
## V8 sandbox violation detected!

Received signal 11 SEGV_MAPERR 414141414141
```


---

**#7 — am...@chromium.org — May 16, 2025 02:30AM**

SI-none / S2 / P1 as this is a V8 sandbox bypass and the sandbox is not considered a security boundary at this time

assigned to dinfuehr@ based on looking at runtime code and recent change that looks like this may impact it, may be incorrect, I'm running a bisect right now and will update accordingly


---

**#8 — 24...@project.gserviceaccount.com — May 16, 2025 02:46AM**

Detailed Report: [https://clusterfuzz.com/testcase?key=5280593231151104](<https://clusterfuzz.com/testcase?key=5280593231151104>)  
  
Fuzzer: None  
Job Type: linux_d8_sandbox_testing  
Platform Id: linux  
  
Crash Type: V8 sandbox violation  
Crash Address:   
Crash State:  
NULL  
Sanitizer: address (ASAN)  
  
Regressed: [https://clusterfuzz.com/revisions?job=linux_d8_sandbox_testing&range=98678:98679](<https://clusterfuzz.com/revisions?job=linux_d8_sandbox_testing&range=98678:98679>)  
  
Reproducer Testcase: [https://clusterfuzz.com/download?testcase_id=5280593231151104](<https://clusterfuzz.com/download?testcase_id=5280593231151104>)  
  
To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.   
  
If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.  
  
If you have any feedback on reproducing test cases, let us know at [https://forms.gle/Yh3qCYFveHj6E5jz5](<https://forms.gle/Yh3qCYFveHj6E5jz5>) so we can improve.


---

**#9 — ol...@chromium.org — May 16, 2025 11:37PM**

Congrats on that nice repro :) This is a known sandbox escape issue that we somehow forgot to fix when closing <https://issues.chromium.org/issues/40931165> . Thanks for reporting it.


---

**#10 — iw...@gmail.com — May 19, 2025 10:48AM**

I noticed the `TODO(40931165)` comment in `LazyBuiltinsAssembler::GenerateTailCallToJSCode` when browsing through [crrev.com/c/6554252](<https://crrev.com/c/6554252>). This is indeed a known issue.


---

**#11 — dx...@google.com — May 19, 2025 10:24PM**

Project: v8/v8  
Branch: main  
Author: Olivier Flückiger [olivf@chromium.org](<mailto:olivf@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6554252](<https://chromium-review.googlesource.com/6554252>)

[sandbox] Harden TailCalls after code update

* * *

Expand for full commit details

```
     
    Instead of letting CompileLazy and friends return the new code object 
    always reload it from the dispatch handle (or closure). 
     
    This ensures that whatever confusion can be caused to the runtime 
    function we always call a code object with a parameter count that 
    matches the initially checked one. 
     
    Bug: 40931165 
    Fixed: 417636716 
     
    Change-Id: I7c70e178f6631a587772c55a90c511ded89fb466 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6554252 
    Reviewed-by: Igor Sheludko <ishell@chromium.org> 
    Commit-Queue: Olivier Flückiger <olivf@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#100345}
```

* * *

Files:

  * M `src/builtins/builtins-lazy-gen.cc`
  * M `src/builtins/builtins-lazy-gen.h`
  * M `src/codegen/arm/macro-assembler-arm.cc`
  * M `src/codegen/arm/macro-assembler-arm.h`
  * M `src/codegen/arm64/macro-assembler-arm64.cc`
  * M `src/codegen/arm64/macro-assembler-arm64.h`
  * M `src/codegen/ia32/macro-assembler-ia32.cc`
  * M `src/codegen/ia32/macro-assembler-ia32.h`
  * M `src/codegen/x64/macro-assembler-x64.cc`
  * M `src/codegen/x64/macro-assembler-x64.h`

* * *

Hash: 675d684c0cbc642f2c154f91a7ae40f29aa6129d  
Date: Mon May 19 12:42:33 2025

* * *


---

**#12 — sp...@google.com — May 29, 2025 08:56AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $20000.00 for this report.  
  
Rationale for this decision:  
report of V8 sandbox bypass demonstrating controlled write outside the sandbox  
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#13 — am...@chromium.org — May 29, 2025 09:15AM**

Congratulations! Thank you for your efforts hunting in the V8 sandbox and reporting this issue to us -- nice work!


---

**#14 — ch...@google.com — Aug 26, 2025 09:39PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
