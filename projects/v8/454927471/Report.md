# V8 Sandbox Bypass: AAW/PC control via CallKnownJSFunction reduction for builtins

Issue URL: https://issues.chromium.org/issues/454927471
VRP-Reward: 22000
Date: Oct 25, 2025 11:05AM


### VULNERABILITY DETAILS

#### Summary

It's possible to call JS linkage builtins that should be disabled (in [this](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/builtins/builtins.cc;l=589;drc=8900162810d457b64286ce653cb61bc2009c5068>) sense) via Maglev's `CallKnownJSFunction`. Since the dispatch handle isn't explicitly set, [tiering builtins](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/builtins/js-trampoline-assembler.cc;l=254-291;drc=269d7c0f238a38e272f19f98a217989524c9f799>) can be tricked into tailing to a function with different argument count, which imbalances the stack and leads to AAW/PC control as in the past. Attached is `maglev-known-builtin-poc.js` which demonstrates this.

**Note:** I tried this approach with TurboFan too, however it runs into [SBXCHECKS in the code generator](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/compiler/backend/x64/code-generator-x64.cc;l=1650;drc=5d6a71b10abe3348f6efd1428ef5d29da9bf79af>)

**Suggested fix:** See attached `fix.patch`. Similar to TurboFan, an `SBXCHECK` is added to `CallKnownJSFunction::GenerateCode` to prevent tailing to disabled builtins (can post to crrev for review if approach is OK). Alternatively, I wonder if `Builtins::GetFormalParameterCount` could be changed to SBXCHECK enabled in addition to the existing JS linkage CHECK...

#### Details

Notice the following in [CallKnownJSFunction::GenerateCode](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/maglev/maglev-ir.cc;l=6336-6345;drc=89c9b4b78d3affc3e645ff5f462103d988904d9e>):

```
void CallKnownJSFunction::GenerateCode(MaglevAssembler* masm,
                                       const ProcessingState& state) {
  MaglevAssembler::TemporaryRegisterScope temps(masm);
  Register scratch = temps.Acquire();
  int actual_parameter_count = num_args() + 1;
  if (actual_parameter_count < expected_parameter_count_) {
    int number_of_undefineds =
        expected_parameter_count_ - actual_parameter_count;
    __ LoadRoot(scratch, RootIndex::kUndefinedValue);
    __ PushReverse(receiver(), args(),
                   RepeatValue(scratch, number_of_undefineds));
  } else {
    __ PushReverse(receiver(), args());
  }
  // ... snipped ...
  if (shared_function_info().HasBuiltinId()) {
    Builtin builtin = shared_function_info().builtin_id();

    // This SBXCHECK is a defense-in-depth measure to ensure that we always
    // generate valid calls here (with matching signatures).
    SBXCHECK_EQ(expected_parameter_count_,
                Builtins::GetFormalParameterCount(builtin));

    __ CallBuiltin(builtin);
  } else {
    // ... snipped ...
  }
  masm->DefineExceptionHandlerAndLazyDeoptPoint(this);
}
```

  1. The builtin id comes from `untrusted_function_info` of `SharedFunctionInfo` which can be manipulated with in-sandbox memory corruption.
  2. `Builtins::GetFormalParameterCount` enforces that the builtin be of JS linkage (ie. has JSTrampoline descriptor), but besides that it could be any builtin (eg. disabled builtins such as the tiering ones).
  3. Notice it directly calls the builtin without explicitly setting arguments such as the dispatch handle like it might have had this function/builtin not been known. So for the dispatch handle, which is passed via register, whatever was the last value of said register is what ends up being "passed" to the builtin.

Meanwhile, notice in [TieringBuiltinImpl](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/builtins/js-trampoline-assembler.cc;l=223-252;drc=8900162810d457b64286ce653cb61bc2009c5068>) it tails to the dispatch handle that was passed as an argument:

```
template <typename Function>
void JSTrampolineAssembler::TieringBuiltinImpl(const Function& Impl) {
  // ... snipped ...

#ifdef V8_JS_LINKAGE_INCLUDES_DISPATCH_HANDLE
  auto dispatch_handle =
      UncheckedParameter<JSDispatchHandleT>(Descriptor::kDispatchHandle);
#else
 // ... snipped ...
#endif

  // Apply the actual tiering. This function must uninstall the tiering builtin.
  Impl(context, function);

  // The dispatch handle of the function shouldn't change.
  CSA_DCHECK(this,
             Word32Equal(dispatch_handle,
                         LoadObjectField<JSDispatchHandleT>(
                             function, JSFunction::kDispatchHandleOffset)));

  // TailCallJSCode will load the code from the dispatch table to guarantee
  // that the signature of the code matches with the number of arguments
  // passed when calling into this trampoline.
  TailCallJSCode(context, function, new_target, argc, dispatch_handle);
}
```

Putting it all together, with in-sandbox corruption, one can construct a maglev function that calls a tiering builtin directly with a stale dispatch handle register value of containing a handle with a larger parameter count. The subsequent under-application when the tiering builtin tails, can cause stack mismatch which leads to AAW/PC control.

### VERSION

V8 commit: 84b1a23c482f14acaf6813326da31077268b44e0

#### REPRODUCTION CASE

**NOTE (for the shepherd):** To reproduce in CF, the `linux_d8_sandbox_testing` job type with the below shell args should hopefully do the trick.

**Shell args** : `--allow-natives-syntax --sandbox-testing`

**Build args** :

```
is_debug=false
is_asan=true
v8_enable_sandbox=true
v8_enable_memory_corruption_api=true
dcheck_always_on=false
target_cpu="x64"
```

**Sample output (`--disable-in-process-stack-traces` used to show PC)**:

```
$ ./d8 --allow-natives-syntax --sandbox-testing --disable-in-process-stack-traces ./maglev-known-builtin-poc.js
Sandbox testing mode is enabled. Only sandbox violations will be reported, all other crashes will be ignored.
Sandbox bounds: [0x7ead00000000,0x7fad00000000)

## V8 sandbox violation detected!

The sandbox violation was a *read* access which is technically not a sandbox violation. This requires manual investigation.
AddressSanitizer:DEADLYSIGNAL
=================================================================
==167927==ERROR: AddressSanitizer: SEGV on unknown address 0x424242424242 (pc 0x424242424242 bp 0x7ead0081f24d sp 0x7ffcd59efc70 T0)
==167927==The signal is caused by a READ memory access.
    #0 0x424242424242  (<unknown module>)

==167927==Register values:
rax = 0x00007ead00000011  rbx = 0x00007ead00000011  rcx = 0x0000000000000002  rdx = 0x00006fdc9fae1000  
rdi = 0x0000000000000000  rsi = 0x0000000000000000  rbp = 0x00007ead0081f24d  rsp = 0x00007ffcd59efc70  
 r8 = 0x0000000000000002   r9 = 0x0000424242424242  r10 = 0x00005ff264480204  r11 = 0x00007ffcd59efaf1  
r12 = 0x00007ffcd59efa10  r13 = 0x00006fdc9fae1080  r14 = 0x00007ead00000000  r15 = 0x00006f5c9fae0309  
AddressSanitizer can not provide additional info.
SUMMARY: AddressSanitizer: SEGV (<unknown module>) 
==167927==ABORTING
```

### FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION

Type of crash: Sandbox violation

### CREDIT INFORMATION

Reporter credit: Krishna Ravishankar (@krsh732)


---

**#2 — cl...@appspot.gserviceaccount.com — Oct 28, 2025 02:03AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5782119276019712](<https://clusterfuzz.com/testcase?key=5782119276019712>).


---

**#3 — cl...@appspot.gserviceaccount.com — Oct 28, 2025 02:05AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=6188543642632192](<https://clusterfuzz.com/testcase?key=6188543642632192>).


---

**#4 — nh...@chromium.org — Oct 28, 2025 02:06AM**

Security shepherd here: I accidentally messed up the first clusterfuzz upload — please ignore that one.

V8 Shepherd: I'm provisionally setting severity to S2.


---

**#5 — kr...@gmail.com — Oct 29, 2025 12:36AM**

Sorry, I realize the fixes I suggested are insufficient. Since the dispatch handle isn't being set, enabled builtins which tail using the dispatch handle such as `InstantiateAsmJs` can still be abused. This can easily be seen by replacing `indexOf("FunctionLogNextExecution")` with `indexOf("InstantiateAsmJs")` in the attached POC... Perhaps the dispatch handle needs to be explicitly set to fully stop this.


---

**#6 — kr...@gmail.com — Oct 29, 2025 01:06AM**

FWIW, TurboFan seems to emit code to clobber/set the dispatch handle register to 0 before calling the builtin, so maybe something similar can be done for Maglev to allow it to crash when tailing.


---

**#7 — is...@chromium.org — Oct 31, 2025 03:06AM**

Thank you for the report! Nice catch!


---

**#8 — dx...@google.com — Oct 31, 2025 08:46PM**

Project: v8/v8  
Branch: main  
Author: Igor Sheludko [ishell@chromium.org](<mailto:ishell@chromium.org>)  
Link: [https://chromium-review.googlesource.com/7102180](<https://chromium-review.googlesource.com/7102180>)

[sandbox][maglev] Generate direct calls only to compatible builtins

* * *

Expand for full commit details

```
     
    ... i.e. to enabled JS builtins having compatible parameter count and 
    which are not JS trampolines (it doesn't make sense to call them from 
    generated code). 
     
    NO_IFTTT=Introducing IFTTT, no logical change. 
     
    Fixed: 454927471 
    Change-Id: I91914ffe5854b5d2e19b3644c7d28b93d7598e38 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/7102180 
    Reviewed-by: Leszek Swirski <leszeks@chromium.org> 
    Commit-Queue: Igor Sheludko <ishell@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#103439}
```

* * *

Files:

  * M `src/builtins/builtins-inl.h`
  * M `src/builtins/builtins.cc`
  * M `src/builtins/builtins.h`
  * M `src/maglev/maglev-assembler-inl.h`
  * M `src/maglev/maglev-assembler.h`
  * M `src/maglev/maglev-ir.cc`
  * M `src/sandbox/js-dispatch-table-inl.h`

* * *

Hash: [410f860463dd8df0905b757fdd7ca53ee1a88c4d](<https://chromiumdash.appspot.com/commit/410f860463dd8df0905b757fdd7ca53ee1a88c4d>)  
Date: Fri Oct 31 11:05:51 2025

* * *


---

**#9 — kr...@gmail.com — Nov 13, 2025 02:38AM**

ishell@ I noticed it's still possible to call disabled builtins via turbofan, so I've posted a patch similar to what you did earlier. As I don't have any concrete sandbox bypasses leveraging this, I've posted a patch that fixes it for review referencing this issue instead of filing a new report. Hopefully this is OK.


---

**#10 — dx...@google.com — Nov 18, 2025 06:57PM**

Project: v8/v8  
Branch: main  
Author: Krishna Ravishankar [krishna.ravi732@gmail.com](<mailto:krishna.ravi732@gmail.com>)  
Link: [https://chromium-review.googlesource.com/7147003](<https://chromium-review.googlesource.com/7147003>)

[compiler][sandbox] Generate direct calls only to compatible builtins

* * *

Expand for full commit details

```
     
    Drive-by: Abort on signature mismatches to trap on release builds as 
    it can be reached with sandbox corruption. 
     
    Bug: 454927471 
    Change-Id: I8a91ba82b93f44b7e44049497bf7290d09fa2f66 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/7147003 
    Reviewed-by: Olivier Flückiger <olivf@chromium.org> 
    Reviewed-by: Darius Mercadier <dmercadier@chromium.org> 
    Commit-Queue: Darius Mercadier <dmercadier@chromium.org> 
    Auto-Submit: Krishna Ravishankar <krishna.ravi732@gmail.com> 
    Cr-Commit-Position: refs/heads/main@{#103768}
```

* * *

Files:

  * M `src/compiler/backend/arm64/code-generator-arm64.cc`
  * M `src/compiler/backend/x64/code-generator-x64.cc`
  * M `src/compiler/js-typed-lowering.cc`

* * *

Hash: [591bf0f55fefecd1584f0bd9a814e3433d0b1b37](<https://chromiumdash.appspot.com/commit/591bf0f55fefecd1584f0bd9a814e3433d0b1b37>)  
Date: Mon Nov 17 11:31:31 2025

* * *


---

**#11 — sp...@google.com — Dec 9, 2025 08:58AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $22000.00 for this report.  
  
Rationale for this decision:  
Exploitation Mitigation Bypass (v8 sandbox) with a patch bonus  
  
  
Important: This payment will be issued by Bugcrowd. You will receive an email from Bugcrowd in the next 24 hours which contains a submission you must claim to be rewarded.  
  
If you do not receive an email from them, please check your spam folder and then reach out to us via a comment here. For issues related to Bugcrowd itself, please contact them via [https://bugcrowd.com/support](<https://bugcrowd.com/support>).  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#12 — ch...@google.com — Feb 7, 2026 09:47PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
