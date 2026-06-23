# V8 Sandbox Bypass: In-sandbox corruption allows execution of DebugBreakTrampoline, leading to invalid tail call

Issue URL: https://issues.chromium.org/issues/435630467
VRP-Reward: 20000
Date: Aug 2, 2025 02:40PM


### VULNERABILITY DETAILS

> Another example of the meta-bug [b/435630464](<https://issues.chromium.org/issues/435630464>) to show that these issues are prevalent, not only for the `v8_flags.*` gated ones. Feel free to dup this into the meta-bug if necessary, but keep in mind that every reachable code, not just ones that are "commonly used and fuzzed", need to be fixed as according to the v8 sandbox threat model.

#### Summary

As explained in [b/435630464](<https://issues.chromium.org/issues/435630464>), an attacker may exploit in-sandbox corruption primitives to unlock a vast amount of dangerous or experimental code that is not fully verified or tested. This bypass uses `DebugBreakTrampoline` which is an example of a builtin that is irrelevant to feature flags (`v8_flags.*`), but is still obviously not intended under normal execution.

#### Details

`DebugBreakTrampoline` blindly trusts that the arguments supplied is sufficient for `sfi->code` and executes a [tail call](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/builtins/builtins-internal-gen.cc;drc=72c6f133031af8165bfb18b2c7cbcbca51bc6aaf;l=116>) to this code. This violates Leaptiering CFI, and is also mentioned in the comments as a TODO. However, it seems that this issue has not been considered a threat due to being a debugging-only code. [b/435630464](<https://issues.chromium.org/issues/435630464>) proves that this is not the case.

The bug allows the callee to pop more arguments than existing on the stack, leading to stack pointer popping above the current used stack and even the frame pointer. Execution from this state corrupts the stack which easily leads to v8sbx violations.

Attached exploit uses this bypass to tail call into a 0x100-arity function with no arguments, immediately followed by a Wasm stack spraying call that corrupts the stack. This allows the attacker to pivot the stack into fully controlled Wasm stack, resulting in PC + stack control. Both the calls are made within a wrapper function that is tiered up to avoid issues with InterpreterEntryTrampoline.

### VERSION

V8: Tested on `d8-sandbox-testing-linux-release-v8-component-101728`

### REPRODUCTION CASE

Attached as `v8sbx-unlock-debugbreaktrampoline.js`, run with `./d8 --sandbox-testing`.

> The repro already has `SharedFunctionInfo` matching that of the tested version hardcoded inside. This should work on most latest d8 builds.

The repro attempts a stack pivot into attacker-controlled Wasm stack sprayed with values 0x4242424200XX, resulting in PC + stack control.

### FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION

Type of crash: Sandbox violation

### CREDIT INFORMATION

Reporter credit: Seunghyun Lee (@0x10n) of CMU CyLab

* * *

One-of-many variants of the fuzzer-found [b/435630464](<https://issues.chromium.org/issues/435630464>).  
Marking any rewards for charity in advance.


---

**#2 — ja...@chromium.org — Aug 5, 2025 05:37AM**

[security shepherd]

Thanks for this additional example. I'm adding the v8 shepherd, assigning provisional severity and priority, and I'll send it to clusterfuzz for bisection as well.


---

**#3 — cl...@appspot.gserviceaccount.com — Aug 5, 2025 05:42AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5047763926450176](<https://clusterfuzz.com/testcase?key=5047763926450176>).


---

**#4 — se...@gmail.com — Aug 5, 2025 07:34AM**

Re #3: Tinkering with the SPRAY size will make it repro, e.g. on that specific build CF is testing on `SPRAY = 0x60` works.


---

**#5 — cl...@appspot.gserviceaccount.com — Aug 5, 2025 07:49AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5436454607978496](<https://clusterfuzz.com/testcase?key=5436454607978496>).


---

**#6 — ja...@chromium.org — Aug 5, 2025 07:49AM**

Thanks! Acknowledged and running it again with the updated spray value.

I'm provisionally adding OS to be Desktop and Android.


---

**#7 — is...@chromium.org — Aug 21, 2025 11:17PM**

Thank you for the report! Nice catch!


---

**#8 — dx...@google.com — Aug 22, 2025 03:57AM**

Project: v8/v8  
Branch: main  
Author: Igor Sheludko [ishell@chromium.org](<mailto:ishell@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6871396](<https://chromium-review.googlesource.com/6871396>)

[sandbox] Make DebugBreakTrampoline check the arguments count

* * *

Expand for full commit details

```
     
    ... when tail calling to code. 
     
    Drive-by: introduce TailCallJSCode() variants for loading the code 
    from dispatch table or function (according to V8_ENABLE_LEAPTIERING 
    state) and for validating that the code's parameter count matches 
    the parameter count stored in dispatch table. 
     
    Fixed: 435630467 
    Change-Id: I446c2d08071a1acc4d450f3f7603ae9a5c3020a9 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6871396 
    Reviewed-by: Samuel Groß <saelo@chromium.org> 
    Commit-Queue: Igor Sheludko <ishell@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#101985}
```

* * *

Files:

  * M `src/builtins/builtins-internal-gen.cc`
  * M `src/builtins/js-trampoline-assembler.cc`
  * M `src/codegen/code-stub-assembler.cc`
  * M `src/codegen/code-stub-assembler.h`
  * A `test/mjsunit/sandbox/regress-435630467.js`

* * *

Hash: [269d7c0f238a38e272f19f98a217989524c9f799](<https://chromiumdash.appspot.com/commit/269d7c0f238a38e272f19f98a217989524c9f799>)  
Date: Thu Aug 21 17:14:08 2025

* * *


---

**#9 — sp...@google.com — Aug 29, 2025 02:54AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $20000.00 for this report.  
  
Rationale for this decision:  
report of V8 sandbox bypass demonstrating attacker stack spray and stack control outside of the V8 heap sandbox  
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#10 — ch...@google.com — Nov 28, 2025 09:45PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
