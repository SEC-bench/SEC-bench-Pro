# V8 Sandbox Bypass: AAW/PC control via OOB builtin in SharedFunctionInfo

Issue URL: https://issues.chromium.org/issues/451355210
VRP-Reward: 20000
Date: Oct 13, 2025 07:19PM


### VULNERABILITY DETAILS

#### Summary

[CodeStubAssembler::GetSharedFunctionInfoCode](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/builtins/builtins-internal-gen.cc;l=81;drc=c4e030495d8b5ffb1ff89d2fe02e83563ed0aba4>) is out of sync with [SharedFunctionInfo::GetCode](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/objects/shared-function-info.cc;l=75;drc=11f240aa5e1354705f3e35de71a73865ff927b35>) for builitins as unlike the latter the former doesn't ensure builtins indices are in-bounds.

**Suggested Fix:** Attached `0001-sandbox-Ensure-builtin-is-within-bounds-for-CSA-Load.patch` which changes the `CSA_DCHECK` to `CSA_SBXCHECK` in [CodeStubAssembler::LoadBuiltin](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/codegen/code-stub-assembler.cc;l=18174;drc=62a9a00176f862e688fa47919ed6f19b59f77b5f>) (can put it up for review in crrev if it looks good).

#### Details

In [CodeStubAssembler::GetSharedFunctionInfoCode](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/codegen/code-stub-assembler.cc;l=18334;drc=62a9a00176f862e688fa47919ed6f19b59f77b5f>) the following is done for builtins:

```
TNode<Code> CodeStubAssembler::GetSharedFunctionInfoCode(
    TNode<SharedFunctionInfo> shared_info, TVariable<Uint16T>* data_type_out,
    Label* if_compile_lazy) {
    // ... snipped ...

    // IsSmi: Is builtin
    GotoIf(TaggedIsNotSmi(untrusted_sfi_data), &check_instance_type);
    if (data_type_out) {
      *data_type_out = Uint16Constant(0);
    }
    if (if_compile_lazy) {
      GotoIf(SmiEqual(CAST(untrusted_sfi_data),
                      SmiConstant(Builtin::kCompileLazy)),
             if_compile_lazy);
    }
    sfi_code = LoadBuiltin(CAST(untrusted_sfi_data));
    Goto(&done);
  }
```

Notice the `untrusted_sfi_data` smi is only ever validated to be within bounds in `LoadBuiltin` for debug builds:

```
TNode<Code> CodeStubAssembler::LoadBuiltin(TNode<Smi> builtin_id) {
  CSA_DCHECK(this, SmiBelow(builtin_id, SmiConstant(Builtins::kBuiltinCount)));
  // ...snipped...
}
```

With in-sandbox corruption, an attacker can construct an OOB builtin index such that retrieved Code is in writable V8 heap. Since the Code is in writable heap, an attacker can forge a mismatched parameter count, allowing the stack to become imbalanced leading to AAW/PC control as in the past.

### VERSION

V8 commit: 0a96df301fdaadc26a059ee5cd06fc47f9a662b6

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
$ ./d8 --allow-natives-syntax  --sandbox-testing --disable-in-process-stack-traces ./oob-builtin-poc.js 
Sandbox testing mode is enabled. Only sandbox violations will be reported, all other crashes will be ignored.
Sandbox bounds: [0x735800000000,0x745800000000)

## V8 sandbox violation detected!

The sandbox violation was a *read* access which is technically not a sandbox violation. This requires manual investigation.
AddressSanitizer:DEADLYSIGNAL
=================================================================
==21556==ERROR: AddressSanitizer: SEGV on unknown address 0x424242424242 (pc 0x424242424242 bp 0x7ffc697eec00 sp 0x7ffc697eedf8 T0)
==21556==The signal is caused by a READ memory access.
    #0 0x424242424242  (<unknown module>)

==21556==Register values:
rax = 0x0000735800000011  rbx = 0x0000735800000011  rcx = 0x0000000000000002  rdx = 0x0000424242424242  
rdi = 0x0000000000000000  rsi = 0x0000000000000000  rbp = 0x00007ffc697eec00  rsp = 0x00007ffc697eedf8  
 r8 = 0x0000000000000001   r9 = 0x0000000000000000  r10 = 0x00005ee4ba2001a4  r11 = 0x00007ffc697eebc9  
r12 = 0x00007ffc697eeae8  r13 = 0x000077a95b6e1080  r14 = 0x0000735800000000  r15 = 0x000077295b6e0309  
AddressSanitizer can not provide additional info.
SUMMARY: AddressSanitizer: SEGV (<unknown module>) 
==21556==ABORTING
```

### FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION

Type of crash: Sandbox violation

### CREDIT INFORMATION

Reporter credit: Krishna Ravishankar (@krsh732)


---

**#2 — th...@chromium.org — Oct 13, 2025 10:32PM**

Triaging as V8 sandbox bypass bug:  
\- Set a provisional severity of Medium (S2).  
\- Set a provisional priority of P1.  
\- Assign to the current V8 Shepherd. --> skipping this since there is already an assignee  
\- Apply the Security_Impact-None hotlist (hotlistID:5433277).  
\- If possible, please also apply the V8 Sandbox hotlist (hotlistID:4802478). --> skipping this since it is already done


---

**#3 — is...@chromium.org — Oct 16, 2025 09:22PM**

Thank you for the report! Nice catch!


---

**#4 — dx...@google.com — Oct 16, 2025 10:16PM**

Project: v8/v8  
Branch: main  
Author: Igor Sheludko [ishell@chromium.org](<mailto:ishell@chromium.org>)  
Link: [https://chromium-review.googlesource.com/7045784](<https://chromium-review.googlesource.com/7045784>)

[sandbox] SBXCHECK that CSA::LoadBuiltin() gets valid builtin id

* * *

Expand for full commit details

```
     
    Drive-by: add IFTTT linter pragmas for CSA::GetSharedFunctionInfoCode() 
    and SharedFunctionInfo::GetCode(). 
     
    NO_IFTTT=Introducing IFTTT, no logical change. 
     
    Fixed: 451355210 
    Change-Id: Iad01aa8cb973f3d7e699ba135bf6ebe52cb2c928 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/7045784 
    Reviewed-by: Patrick Thier <pthier@chromium.org> 
    Auto-Submit: Igor Sheludko <ishell@chromium.org> 
    Commit-Queue: Patrick Thier <pthier@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#103164}
```

* * *

Files:

  * M `src/builtins/builtins-internal-gen.cc`
  * M `src/codegen/code-stub-assembler.cc`
  * M `src/objects/shared-function-info.cc`

* * *

Hash: [95b9fa928629d3aa86a20b5a6c29a9ccbe322385](<https://chromiumdash.appspot.com/commit/95b9fa928629d3aa86a20b5a6c29a9ccbe322385>)  
Date: Thu Oct 16 12:23:10 2025

* * *


---

**#5 — sp...@google.com — Nov 14, 2025 03:55AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $20000.00 for this report.  
  
Rationale for this decision:  
v8 sandbox escape demonstrating a controllable write  
  
  
Important: This payment will be issued by Bugcrowd. You will receive an email from Bugcrowd in the next 24 hours which contains a submission you must claim to be rewarded.  
  
If you do not receive an email from them, please check your spam folder and then reach out to us via a comment here. For issues related to Bugcrowd itself, please contact them via [https://bugcrowd.com/support](<https://bugcrowd.com/support>).  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#6 — ch...@google.com — Nov 14, 2025 09:42PM**

This V8 bug has been marked as either a release blocker or a vulnerability bug. V8 bugs affect all OSs supported by Chrome, so the OS field has been updated to reflect this. Please update the bug with the correct OS field if it only affects a subset of OSes.


---

**#7 — ch...@google.com — Jan 23, 2026 09:40PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.


---

**#8 — dx...@google.com — Feb 27, 2026 10:27PM**

Project: v8/v8  
Branch: main  
Author: Krishna Ravishankar [krishna.ravi732@gmail.com](<mailto:krishna.ravi732@gmail.com>)  
Link: [https://chromium-review.googlesource.com/7603043](<https://chromium-review.googlesource.com/7603043>)

[debug] Get Code with SFI::GetCode for DebugBreakTrampoline

* * *

Expand for full commit details

```
     
    Bug: 487213150, 451355210 
    Change-Id: I15e95ad60d0f8d26aa4ca0fbfe4f1239b1cd664e 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/7603043 
    Reviewed-by: Olivier Flückiger <olivf@chromium.org> 
    Commit-Queue: Igor Sheludko <ishell@chromium.org> 
    Reviewed-by: Igor Sheludko <ishell@chromium.org> 
    Auto-Submit: Krishna Ravishankar <krishna.ravi732@gmail.com> 
    Cr-Commit-Position: refs/heads/main@{#105500}
```

* * *

Files:

  * M `src/builtins/builtins-internal-gen.cc`
  * M `src/codegen/external-reference.cc`
  * M `src/runtime/runtime-debug.cc`

* * *

Hash: [c9d92eac458cdb227d37f2c839e966dc73803694](<https://chromiumdash.appspot.com/commit/c9d92eac458cdb227d37f2c839e966dc73803694>)  
Date: Fri Feb 27 12:30:17 2026

* * *
