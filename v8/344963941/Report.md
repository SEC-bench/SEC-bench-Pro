# V8 Sandbox Bypass: Irregexp engine bytecode modification leads to arbitrary read/write outside the sandbox

Issue URL: https://issues.chromium.org/issues/344963941
VRP-Reward: 5250
Date: Jun 5, 2024 09:07AM


# V8 Sandbox Bypass: Irregexp engine bytecode modification leads to arbitrary read/write outside the sandbox

**VULNERABILITY DETAILS**

Since the bytecode used by the Irregexp engine resides on the V8 heap, it can be arbitrarily modified by an attacker. In `IrregexpInterpreter::Result RawMatch` the `backtrack_stack` is not guarded against an attacker controlling this bytecode. By performing a pop on an empty `backtrack_stack`, data in front of the original stack data can be accessed OOB. This can be achieved by using any of the following bytecodes: `POP_CP, POP_BT, POP_REGISTER and CHECK_GREEDY` [1].

The `backtrack_stack` data is initially allocated on the OS stack. Therefore, this OOB can be used to modify OS stack data directly. Concretely, I target the corresponding `backtrack_stack.data_` structure that is directly accessible with the OOB. I exploit this with the following steps to write to an arbitrary address (here the Sandbox.targetPage):

  * Underflow `backtrack_stack` by using the `POP_REGISTER` bytecode.
  * Overwrite `backtrack_stack.data_.end_of_storage_` with a random unaligned value. This effectively allows for OOB access in both directions now since the check that could potentially reallocate `backtrack_stack.data_` will always fail even once the stack becomes full [2].
  * Overwrite `backtrack_stack.data_.end_` to point to the location on the stack where the data pointer of `InterpreterRegisters` is stored [3]. Without first modifying `backtrack_stack.data_.end_of_storage_`, this would fail because this pointer is stored directly after the original end of `backtrack_stack.data_`.
  * Use the `PUSH_BT` bytecode to write an arbitrary pointer (here Sandbox.targetPage) to the data pointer of `InterpreterRegisters`.
  * Using the `SET_REGISTER` bytecode will now write to our given pointer.

The corresponding bytecode, which illustrates this better, looks like this:

```
POP_REGISTER | 0x000,
PUSH_BT, 0x1, // overwrite backtrack_stack.data_.end_of_storage_
POP_REGISTER | 0x000, POP_REGISTER | 0x000, POP_REGISTER | 0x000,
POP_REGISTER | 0x100, ADVANCE_REGISTER | 0x100, BACKTRACK_END_TO_REGS_OFF, // BACKTRACK_END_TO_REGS_OFF = 0x10c
PUSH_REGISTER | 0x100, // overwrite backtrack_stack.data_.end => &registers.begin_
PUSH_BT, sbxLower,   // overwrite registers.begin_ with Sandbox.targetPage
PUSH_BT, sbxUpper,
SET_REGISTER | 0x000, 0x41414141, // write 0x41414141 to targetPage
```

To reproduce this, use the attached expl.js below. This relies on stack offsets, so you might need to replicate my setup or adjust those offsets to make it work on other distros. However, in my tests this was consistent and did not need to be adjusted. I developed the repro on commit V8 `2106d9c81a1fb9d758ebda1560e2251b0f05150c` and used the following docker image `archlinux:base-20240101.0.204074 `.

[1] [https://source.chromium.org/chromium/chromium/src/+/main:v8/src/regexp/regexp-interpreter.cc;l=552](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/regexp/regexp-interpreter.cc;l=552>)

[2] [https://source.chromium.org/chromium/chromium/src/+/main:v8/src/base/small-vector.h;l=153](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/base/small-vector.h;l=153>)

[3] [https://source.chromium.org/chromium/chromium/src/+/main:v8/src/regexp/regexp-interpreter.cc;l=454](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/regexp/regexp-interpreter.cc;l=454>)

**VERSION**

Tested on d8 stable (12.5.227.13)

Operating system: Arch Linux

**FIX**

Turn the DCHECK in BacktrackStack::peek() into a SBXCHECK (see fix.patch)


---

**#2 — ke...@chromium.org — Jun 6, 2024 06:24AM**

Thanks for the report.  
  
I'm setting provisional triage values and assigning to the V8 sheriff.


---

**#3 — pe...@google.com — Jun 7, 2024 02:41AM**

Setting milestone because of s0/s1 severity.


---

**#4 — pe...@google.com — Jun 7, 2024 02:42AM**

Setting Priority to P1 to match Severity s1. If this is incorrect, please reset the priority. The automation bot account won't make this change again.


---

**#5 — cl...@appspot.gserviceaccount.com — Jun 7, 2024 05:33PM**

Detailed Report: [https://clusterfuzz.com/testcase?key=5105540240703488](<https://clusterfuzz.com/testcase?key=5105540240703488>)  
  
Fuzzer: None  
Job Type: linux_d8_sandbox_testing  
Platform Id: linux  
  
Crash Type: V8 sandbox violation  
Crash Address:   
Crash State:  
NULL  
Sanitizer: address (ASAN)  
  
Crash Revision: [https://clusterfuzz.com/revisions?job=linux_d8_sandbox_testing&revision=94304](<https://clusterfuzz.com/revisions?job=linux_d8_sandbox_testing&revision=94304>)  
  
Reproducer Testcase: [https://clusterfuzz.com/download?testcase_id=5105540240703488](<https://clusterfuzz.com/download?testcase_id=5105540240703488>)  
  
To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.   
  
If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.  
  
If you have any feedback on reproducing test cases, let us know at [https://forms.gle/Yh3qCYFveHj6E5jz5](<https://forms.gle/Yh3qCYFveHj6E5jz5>) so we can improve.


---

**#6 — sa...@chromium.org — Jun 7, 2024 05:34PM**

Great work! Managed to reproduce this on Clusterfuzz. Patrick, could you also take a look at this one? Thanks!


---

**#7 — ap...@google.com — Jun 7, 2024 06:46PM**

Project: v8/v8  
Branch: main  
  
commit 8859e5e21f4b5e587d9b75839c27befbdf1b9ddd  
Author: pthier <[pthier@chromium.org](<mailto:pthier@chromium.org>)>  
Date: Fri Jun 07 11:06:57 2024  
  
[regexp] Harden backtrack strack access in interpreter  
  
Prevent reading/popping on empty stack.  
  
Fixed: 344963941  
Bug: 42204606  
Change-Id: Ia962afb4241df42dc460e6895513892fb5fd36be  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5604430](<https://chromium-review.googlesource.com/c/v8/v8/+/5604430>)  
Auto-Submit: Patrick Thier <[pthier@chromium.org](<mailto:pthier@chromium.org>)>  
Reviewed-by: Olivier Flückiger <[olivf@chromium.org](<mailto:olivf@chromium.org>)>  
Commit-Queue: Patrick Thier <[pthier@chromium.org](<mailto:pthier@chromium.org>)>  
Commit-Queue: Olivier Flückiger <[olivf@chromium.org](<mailto:olivf@chromium.org>)>  
Cr-Commit-Position: refs/heads/main@{#94308}  
  
M src/regexp/regexp-interpreter.cc  
  
[https://chromium-review.googlesource.com/5604430](<https://chromium-review.googlesource.com/5604430>)


---

**#8 — am...@chromium.org — Jun 8, 2024 09:44AM**

the V8 sandbox is not currently considered a security boundary, reduced severity to accurately reflect that as well as to ensure the bot doesn't update this for merge review


---

**#9 — 24...@project.gserviceaccount.com — Jun 8, 2024 04:19PM**

ClusterFuzz testcase 5105540240703488 is verified as fixed in [https://clusterfuzz.com/revisions?job=linux_d8_sandbox_testing&range=94307:94308](<https://clusterfuzz.com/revisions?job=linux_d8_sandbox_testing&range=94307:94308>)  
  
If this is incorrect, please add the hotlistid:5432646 and re-open the issue.


---

**#10 — sp...@google.com — Jul 18, 2024 07:57AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $5250.00 for this report.  
  
Rationale for this decision:  
V8 heap sandbox bypass reward + $250 patch bonus  
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#11 — am...@chromium.org — Jul 18, 2024 08:19AM**

Thank you for your efforts in discovering and reporting this V8 sandbox bypass -- nice work!


---

**#12 — as...@gmail.com — Jul 18, 2024 05:33PM**

Thank you for the reward!


---

**#13 — pg...@google.com — Jul 23, 2024 08:16AM**

Hello reporter, how would you like to be credited for this report?


---

**#14 — am...@chromium.org — Jul 23, 2024 08:43AM**

the v8 sandbox is not considered a security boundary at this time; updating as SI-None and removing release label


---

**#15 — as...@gmail.com — Jul 23, 2024 12:47PM**

You can use my Twitter/X: @ju256_


---

**#16 — pe...@google.com — Sep 15, 2024 12:40AM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
