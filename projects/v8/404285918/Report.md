# V8 Sandbox Bypass: SP/PC control via Wasm JSPI central stack top confusion

Issue URL: https://issues.chromium.org/issues/404285918
VRP-Reward: 20000
Date: Mar 18, 2025 04:16AM


### VULNERABILITY DETAILS

#### Summary

V8 sandbox bypass, SP/PC control (full stack control) via Wasm JSPI central stack top confusion. This requires using a staged WASM feature ([JSPI](<https://chromestatus.com/feature/5674874568704000>)), also available through Origin Trials.

This is a variant of [b/384553540](<https://issues.chromium.org/issues/384553540>).

#### Details

[b/356419168](<https://issues.chromium.org/issues/356419168>) and [b/384553540](<https://issues.chromium.org/issues/384553540>) demonstrated `WasmContinuationObject::jmpbuf` transplantation attack where we can "replay" stacks in invalid state / order, resulting in full control over WASM stack and thus PC control. Fix for the aformentioned issues were to 1. use `stack` instead of holding a separate `jmpbuf`, and to 2. validate the chain of `stack` (= `jmpbuf`) before switching back to the target stack.

Unfortunately, there still are cases where JSPI implicitly "switches" between stacks without an explicit `wasm::{switch_stacks,return_switch}` \- between JSPI stacks (secondary stacks) and JS stack (central stack) on Wasm-to-JS calls. Central stack top is updated on [`Isolate::UpdateCentralStackInfo()`](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/execution/isolate.cc;drc=c24df23717b6aaa8d433b21a216ed56b4aa2ccd2;l=3893>), but in a completely unprotected manner by choosing the latest (= deepest) central stack location from the continuation chain.

Thus, it is possible for an attacker to cause an invalid update of the central stack top to a shallower position in the stack which is currently in use. Subsequent Wasm-to-JS calls from a JSPI stack will result in switching to the invalid stack position, corrupting in-use stack which will later be returned to. This leads to full control over the central stack contents.

### VERSION

V8: Tested on latest CF asan / no-asan sandbox-testing d8 build @ revision 99291 (commit [b28b0a7](<https://chromium-review.googlesource.com/c/v8/v8/+/6361076>))

### REPRODUCTION CASE

Attached as `jspi-central-stack-confusion.js`, run with `./d8 --experimental-wasm-jspi --sandbox-testing`.

Both the repros return to address `0x424242424242` with frame pointer `0x414141414141` and with stack contents fully controlled (which is demonstrated by having the stack top set to`0x404040404040`), demonstrating full control over control flow & stack.

### FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION

Type of crash: Sandbox violation

### CREDIT INFORMATION

Reporter credit: Seunghyun Lee (@0x10n) of CMU CyLab

* * *

Marking any rewards for charity in advance.


---

**#2 — se...@gmail.com — Mar 18, 2025 04:29AM**

AFAICT many of the logic/checks around JSPI could also be racy, e.g. between `Isolate::SwitchStacks()` and the actual stack switching process, as the former loads stack from in-sandbox continuation object which could be swapped out any time by another thread. Also note that `Isolate::SwitchStacks()` calls `Isolate::UpdateCentralStackInfo()`, which due its current implementation allows an attacker to stall execution by a cyclic chain of continuations effectively making such race conditions a deterministically triggered one.


---

**#3 — ps...@google.com — Mar 18, 2025 05:02AM**

Unable to reproduce locally or fuzzed. Passing over to V8 shep while setting provisional severity and priority. Feel free to adjust as you see fit.  
  
[https://clusterfuzz.com/testcase-detail/6268517850480640](<https://clusterfuzz.com/testcase-detail/6268517850480640>)


---

**#4 — cf...@google.com — Mar 18, 2025 05:51AM**

Hi Seunghyun, thanks for the report! :)

thibaudm@ PTAL


---

**#5 — ch...@google.com — Mar 18, 2025 09:34PM**

Setting milestone because of s2 severity.


---

**#6 — th...@chromium.org — Mar 24, 2025 10:47PM**

The fix has landed, not sure why it was not linked automatically:  
[https://chromium-review.googlesource.com/c/v8/v8/+/6381013](<https://chromium-review.googlesource.com/c/v8/v8/+/6381013>)


---

**#7 — ch...@google.com — Mar 24, 2025 11:00PM**

Dear owner, thanks for fixing this bug. We've reopened it because:

  * It is not clear which CLs have ‘fixed’ (=required to consider the bug resolved; e.g. not logging) this bug. Please fill in the “Fixed By Code Changes” field with the appropriate Gerrit url to disambiguate using the following guidelines: 
    * If there are multiple CLs required, please list all.
    * If the fix landed in a third party library (v8, Dawn, etc), please list the third party commits - not the rolls.
    * If there are cherrypicks or back merges, please list the original commits which landed on HEAD.
    * If there is no relevant Gerrit link (i.e. the fix does not live in or roll into Chromium), please use the value ‘NA’.
    * If this is a non-browser ChromeOS-specific bug, please move it to component 1335705 in the Google issue tracker.
    * If this field requires human intervention for some reason, please add this bug to the hotlist id 6265590. After resolving the above issue(s), this bug can be marked closed again. Thanks for your time!


---

**#8 — th...@chromium.org — Mar 24, 2025 11:28PM**

Re [comment #2](<https://issues.chromium.org/issues/404285918#comment2>): that's also a good point. In fact I was planning to either move the WasmContinuationObjects to trusted space, or just remove them completely and use the `StackMemory` C++ objects directly through external pointers, which would eliminate all of these issues based on corrupting the continuation objects.


---

**#9 — ch...@google.com — Apr 1, 2025 09:36PM**

thibaudm: Uh oh! This issue still open and hasn't been updated in the last 14 days. This is a serious vulnerability, and we want to ensure that there's progress. Could you please leave an update with the current status and any potential blockers?

If you're not the right owner for this issue, could you please remove yourself as soon as possible or help us find the right one?

If the issue is fixed or you can't reproduce it, please close the bug. If you've started working on a fix, please set the status to Started.

Thanks for your time! To disable nags, add Disable-Nags (case sensitive) to the Chromium Labels custom field.


---

**#10 — ch...@google.com — Apr 2, 2025 09:35PM**

thibaudm: Uh oh! This issue still open and hasn't been updated in the last 15 days. This is a serious vulnerability, and we want to ensure that there's progress. Could you please leave an update with the current status and any potential blockers?

If you're not the right owner for this issue, could you please remove yourself as soon as possible or help us find the right one?

If the issue is fixed or you can't reproduce it, please close the bug. If you've started working on a fix, please set the status to Started.

Thanks for your time! To disable nags, add Disable-Nags (case sensitive) to the Chromium Labels custom field.


---

**#11 — ch...@google.com — Apr 3, 2025 09:35PM**

thibaudm: Uh oh! This issue still open and hasn't been updated in the last 16 days. This is a serious vulnerability, and we want to ensure that there's progress. Could you please leave an update with the current status and any potential blockers?

If you're not the right owner for this issue, could you please remove yourself as soon as possible or help us find the right one?

If the issue is fixed or you can't reproduce it, please close the bug. If you've started working on a fix, please set the status to Started.

Thanks for your time! To disable nags, add Disable-Nags (case sensitive) to the Chromium Labels custom field.


---

**#12 — dx...@google.com — Apr 3, 2025 09:52PM**

Project: v8/v8  
Branch: main  
Author: Thibaud Michaud [thibaudm@chromium.org](<mailto:thibaudm@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6426203](<https://chromium-review.googlesource.com/6426203>)

[wasm][jspi] Remove WasmContinuationObjects

* * *

Expand for full commit details

```
     
    These objects have become obsolete: 
    - We don't rely on the GC anymore to collect finished stacks. Instead, 
      they are considered free as soon as they have returned and are managed 
      by the stack pool afterwards, 
    - The parent-child relationship between stacks is already encoded in the 
      C++ StackMemory objects for sandbox safety purposes, so the 
      WasmContinuationObject#parent field is redundant. 
     
    Replace all uses of continuation objects with wasm::StackMemory objects. 
    This removes a significant sandbox attack surface and simplifies the 
    code in many places. 
     
    Drive-by: also avoid some unnecessary indirections between the stack and 
    the jump buffer. 
     
    R=jkummerow@chromium.org 
     
    Bug: 404285918,42202153 
    Change-Id: I817f2a1b01bd7949d0abb9881e8775af503d37ed 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6426203 
    Commit-Queue: Thibaud Michaud <thibaudm@chromium.org> 
    Reviewed-by: Camillo Bruni <cbruni@chromium.org> 
    Reviewed-by: Nikolaos Papaspyrou <nikolaos@chromium.org> 
    Reviewed-by: Matthias Liedtke <mliedtke@chromium.org> 
    Reviewed-by: Jakob Kummerow <jkummerow@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#99655}
```

* * *

Files:

  * M `src/builtins/arm/builtins-arm.cc`
  * M `src/builtins/arm64/builtins-arm64.cc`
  * M `src/builtins/ia32/builtins-ia32.cc`
  * M `src/builtins/x64/builtins-x64.cc`
  * M `src/deoptimizer/deoptimizer.cc`
  * M `src/diagnostics/objects-printer.cc`
  * M `src/execution/frames.cc`
  * M `src/execution/frames.h`
  * M `src/execution/isolate-data.h`
  * M `src/execution/isolate.cc`
  * M `src/execution/isolate.h`
  * M `src/heap/factory.cc`
  * M `src/heap/factory.h`
  * M `src/heap/finalization-registry-cleanup-task.cc`
  * M `src/heap/heap-visitor.h`
  * M `src/heap/mark-compact.cc`
  * M `src/heap/setup-heap-internal.cc`
  * M `src/objects/map.cc`
  * M `src/objects/map.h`
  * M `src/objects/object-list-macros.h`
  * M `src/objects/objects.cc`
  * M `src/profiler/cpu-profiler.cc`
  * M `src/profiler/tick-sample.cc`
  * M `src/roots/roots.h`
  * M `src/roots/static-roots.h`
  * M `src/runtime/runtime-test-wasm.cc`
  * M `src/runtime/runtime-wasm.cc`
  * M `src/wasm/stacks.h`
  * M `src/wasm/turboshaft-graph-interface.cc`
  * M `src/wasm/wasm-external-refs.cc`
  * M `src/wasm/wasm-external-refs.h`
  * M `src/wasm/wasm-objects-inl.h`
  * M `src/wasm/wasm-objects.cc`
  * M `src/wasm/wasm-objects.h`
  * M `src/wasm/wasm-objects.tq`

* * *

Hash: d4700da23d4ab417d9f706e3cd5371a3b12ab593  
Date: Thu Apr 3 12:14:53 2025

* * *


---

**#13 — dx...@google.com — Apr 8, 2025 10:02AM**

Project: v8/v8  
Branch: main  
Author: Lu Yahan [yahan@iscas.ac.cn](<mailto:yahan@iscas.ac.cn>)  
Link: [https://chromium-review.googlesource.com/6436518](<https://chromium-review.googlesource.com/6436518>)

[riscv][wasm][jspi] Remove WasmContinuationObjects

* * *

Expand for full commit details

```
     
    Port commit d4700da23d4ab417d9f706e3cd5371a3b12ab593 
    Port commit c310bfa7b81db3b36c34bacdbdeac938ed4937c7 
    Bug: 404285918,42202153 
     
    Change-Id: I65f6252890c35fe56b3e0287b6283bb1b2d9a148 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6436518 
    Auto-Submit: Yahan Lu (LuYahan) <yahan@iscas.ac.cn> 
    Reviewed-by: Ji Qiu <qiuji@iscas.ac.cn> 
    Commit-Queue: Yahan Lu (LuYahan) <yahan@iscas.ac.cn> 
    Cr-Commit-Position: refs/heads/main@{#99705}
```

* * *

Files:

  * M `src/builtins/riscv/builtins-riscv.cc`
  * M `src/codegen/riscv/macro-assembler-riscv.cc`
  * M `src/codegen/riscv/macro-assembler-riscv.h`
  * M `src/compiler/backend/riscv/instruction-selector-riscv32.cc`

* * *

Hash: 8f773cc37f4d8e51cf9dfbb2ef948e3f64bf3a7b  
Date: Mon Apr 7 02:24:16 2025

* * *


---

**#14 — sp...@google.com — Apr 11, 2025 12:56AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $20000.00 for this report.  
  
Rationale for this decision:  
V8 sandbox bypass report demonstrating control of stack and control flow outside the V8 sandbox  
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#15 — am...@chromium.org — Apr 11, 2025 01:12AM**

Congratulations Seunghyun! Thank you for your continued efforts hunting in the V8 sandbox -- nice work!


---

**#16 — ch...@google.com — Jul 11, 2025 09:37PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
