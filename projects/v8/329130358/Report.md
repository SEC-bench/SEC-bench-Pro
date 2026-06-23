# Security: Signal SIGSEGV in v8

Issue URL: https://issues.chromium.org/issues/329130358
VRP-Reward: 7000
Date: Mar 12, 2024 10:17AM


#### Description

ki...@gmail.com created issue [ #1](</issues/329130358#comment1>)

Mar 12, 2024 10:17AM

VULNERABILITY DETAILS  
## INTRODUCE  
After bisect, it was determined that following commit caused this problem.  
  
\- Commit Info  
\- Version: 92403  
\- link: [https://crrev.com/6d26d2b5f88fbb3e3ea7020c2ec16e47ed1aceb6](<https://crrev.com/6d26d2b5f88fbb3e3ea7020c2ec16e47ed1aceb6>)   
\- Commit Message  
  
```  
commit 6d26d2b5f88fbb3e3ea7020c2ec16e47ed1aceb6  
Author: Andreas Haas <[ahaas@chromium.org](<mailto:ahaas@chromium.org>)>  
Date: Mon Feb 19 13:52:47 2024 +0100  
  
[wasm][fuzzing] Add jit_fuzzing implication for wasm  
  
R=[saelo@chromium.org](<mailto:saelo@chromium.org>)  
  
Change-Id: Icf7507797e62cd9956098394a070bdee2328b914  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5300094](<https://chromium-review.googlesource.com/c/v8/v8/+/5300094>)  
Commit-Queue: Andreas Haas <[ahaas@chromium.org](<mailto:ahaas@chromium.org>)>  
Reviewed-by: Matthias Liedtke <[mliedtke@chromium.org](<mailto:mliedtke@chromium.org>)>  
Reviewed-by: Samuel Groß <[saelo@chromium.org](<mailto:saelo@chromium.org>)>  
Cr-Commit-Position: refs/heads/main@{#92403}  
  
```  
  
## CRASH LOG  
\- Debug output  
  
```bash  
# CMD: /tmp/d8-linux-debug-v8-component-92762/d8 --expose-gc --jit-fuzzing --wasm-staging poc.js  
# OUTPUT ==============================================================  
Received signal 11 <unknown> 000000000000  
  
==== C stack trace ===============================  
  
[0x7f048d36b963]  
[0x7f048d36b8b2]  
[0x7f0487642520]  
[0x1d295d3e5915]  
[end of stack trace]  
  
```  
  
## Other  
Please note to include the flags `--expose-gc --jit-fuzzing --wasm-staging` for clusterfuzz classification.  
  
VERSION  
Tested on v8 version: 12.4.0 - 12.4.0  
  
REPRODUCTION CASE  
1\. Download debug v8 from: gs://v8-asan/linux-debug/d8-linux-debug-v8-component-92762.zip  
2\. Run: `d8 --expose-gc --jit-fuzzing --wasm-staging poc.js`  
  
FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION  
Type of crash: tab  
  
CREDIT INFORMATION  
Reporter credit: Zhenghang Xiao (@Kipreyyy)   

poc.js 

699 B [ View](<https://issues.chromium.org/action/issues/329130358/attachments/54555838?download=false>)[ Download](<https://issues.chromium.org/action/issues/329130358/attachments/54555838?download=true>)


---

**#2 — cl...@appspot.gserviceaccount.com — Mar 13, 2024 06:53AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5974772218789888](<https://clusterfuzz.com/testcase?key=5974772218789888>).


---

**#3 — ki...@gmail.com — Mar 14, 2024 10:42AM**

Please impot test/mjsunit/wasm/wasm-module-builder.js and re-run clusterfuzz


---

**#4 — ja...@chromium.org — Mar 15, 2024 02:59AM**

Thanks for pointing that out. I'll try again and include that file.

In the mean time, I'm setting a provisional severity of High (S1), and a Found In of the current Extended Stable: 122.

Adding the current v8 shepherd for further triage.


---

**#5 — cl...@appspot.gserviceaccount.com — Mar 15, 2024 03:06AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=4683893570994176](<https://clusterfuzz.com/testcase?key=4683893570994176>).


---

**#6 — ki...@gmail.com — Mar 15, 2024 08:14AM**

It seems there may still be issues with the sample you uploaded to ClusterFuzz. Could you try reproducing it locally to investigate further?


---

**#7 — ja...@chromium.org — Mar 15, 2024 08:48AM**

Hi, yes, I was able to reproduce locally on Linux using the steps you provided. cffsmith@ should be able to add more information when they take a look.

I'll try one more time with clusterfuzz


---

**#8 — cl...@appspot.gserviceaccount.com — Mar 15, 2024 08:55AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5133404613312512](<https://clusterfuzz.com/testcase?key=5133404613312512>).


---

**#9 — 24...@project.gserviceaccount.com — Mar 15, 2024 10:32AM**

Detailed Report: [https://clusterfuzz.com/testcase?key=5133404613312512](<https://clusterfuzz.com/testcase?key=5133404613312512>)  
  
Fuzzer: None  
Job Type: linux_asan_d8_dbg  
Platform Id: linux  
  
Crash Type: Segv on unknown address  
Crash Address:   
Crash State:  
Builtins_InterpreterEntryTrampoline  
Builtins_JSEntryTrampoline  
Builtins_JSEntry  
  
Sanitizer: address (ASAN)  
  
Regressed: [https://clusterfuzz.com/revisions?job=linux_asan_d8_dbg&range=92402:92403](<https://clusterfuzz.com/revisions?job=linux_asan_d8_dbg&range=92402:92403>)  
  
Reproducer Testcase: [https://clusterfuzz.com/download?testcase_id=5133404613312512](<https://clusterfuzz.com/download?testcase_id=5133404613312512>)  
  
To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.   
  
If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.  
  
If you have any feedback on reproducing test cases, let us know at [https://forms.gle/Yh3qCYFveHj6E5jz5](<https://forms.gle/Yh3qCYFveHj6E5jz5>) so we can improve.


---

**#10 — 24...@project.gserviceaccount.com — Mar 15, 2024 10:48AM**

Automatically applying components based on crash stacktrace and information from OWNERS files.  
  
If this is incorrect, please apply the hotlistid:4801165.


---

**#11 — pe...@google.com — Mar 16, 2024 12:38AM**

Setting milestone because of s0/s1 severity.


---

**#12 — pe...@google.com — Mar 16, 2024 12:38AM**

Setting Priority to P1 to match Severity s1. If this is incorrect, please reset the priority. The automation bot account won't make this change again.


---

**#13 — cf...@google.com — Mar 18, 2024 09:14PM**

ahaas@, could you PTAL?


---

**#14 — ah...@chromium.org — Mar 18, 2024 10:48PM**

The repro is quite simple, actually. It calls a WebAssembly.Function from WebAssembly with `ref.call`. The WebAssembly.Function wraps a JavaScript function that triggers a GC. The repro runs with --jit-fuzzing, which in this case means that the wasm-to-js wrapper triggers tier-up already with the first call. Note that the tier-up gets triggered synchronously at the beginning of the first call to the wasm-to-js wrapper, but the optimized wrapper only gets used at the second call of the wasm-to-js wrapper.   
  
There seems to be missing something in the GC support of `WasmInternalFunction`. Before the GC the `code` field is set correctly, but after the GC it is invalid. The tier up of the wasm-to-js wrapper seems to matter, because without the tier up the `code` field seems to be preserved. But with the tier up, the `code` field references the generic wasm-to-js builtin before tier up, the optimized wasm-to-js wrapper after tier-up, and an invalid value after the GC.


---

**#15 — ap...@google.com — Mar 18, 2024 11:59PM**

Project: v8/v8  
Branch: main  
  
commit b93975a48c722c2e5fe9b39437738eb2e23dac74  
Author: Andreas Haas <[ahaas@chromium.org](<mailto:ahaas@chromium.org>)>  
Date: Mon Mar 18 15:25:15 2024  
  
[wasm][gc] Scan the code field of the WasmInternalFunction  
  
The code field in the WasmInternalFunction is a code pointer since  
[https://crrev.com/c/5110559](<https://crrev.com/c/5110559>), so it has to be scanned explicitly.  
  
Bug: 329130358  
Change-Id: Ifc7a7cddb245e46fb9c006e560073a8d7ac65389  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5374907](<https://chromium-review.googlesource.com/c/v8/v8/+/5374907>)  
Commit-Queue: Andreas Haas <[ahaas@chromium.org](<mailto:ahaas@chromium.org>)>  
Reviewed-by: Clemens Backes <[clemensb@chromium.org](<mailto:clemensb@chromium.org>)>  
Cr-Commit-Position: refs/heads/main@{#92878}  
  
M src/objects/objects-body-descriptors-inl.h  
A test/mjsunit/regress/wasm/regress-329130358.js  
  
[https://chromium-review.googlesource.com/5374907](<https://chromium-review.googlesource.com/5374907>)


---

**#16 — pe...@google.com — Mar 19, 2024 11:47AM**

This high+ V8 security issue with stable impact requires a lightweight post mortem. Please take some time to answer questions asked in this form [1] to help us improve V8 security. [1] [https://docs.google.com/forms/d/e/1FAIpQLSdSMCiEpIFLLFkMbgtulK1sf1B-idQmkFaA4XP2Rz5mN1cqWg/viewform?usp=pp_url&entry.307501673=329130358&entry.958145677=Linux](<https://docs.google.com/forms/d/e/1FAIpQLSdSMCiEpIFLLFkMbgtulK1sf1B-idQmkFaA4XP2Rz5mN1cqWg/viewform?usp=pp_url&entry.307501673=329130358&entry.958145677=Linux>), Mac&entry.763880440=Extended&entry.1678852700=High&entry.763402679=Blink>JavaScript>API, Blink>JavaScript>Runtime, Infra>Client>V8&entry.975983575=[ahaas@chromium.org](<mailto:ahaas@chromium.org>) Please ensure to copy the full link, as otherwise some issue meta data might not be populated automatically.


---

**#17 — pe...@google.com — Mar 20, 2024 12:40AM**

This is sufficiently serious that it should be merged to extended stable. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M122. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately.  
This is sufficiently serious that it should be merged to stable. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M123. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately.  
Merge review required: M122 is already shipping to stable.  
  
  
Merge review required: M123 is already shipping to stable.  
  
  
Thank you for fixing this security bug! We aim to ship security fixes as quickly as possible, to limit their opportunity for exploitation as an "n-day" (that is, a bug where git fixes are developed into attacks before those fixes reach users).  
  
We have determined this fix is necessary on milestone(s): [122, 123].  
  
Please answer the following questions so that we can safely process this merge request:  
1\. Which CLs should be backmerged? (Please include Gerrit links.)  
2\. Has this fix been verified on Canary to not pose any stability regressions?  
3\. Does this fix pose any potential non-verifiable stability risks?  
4\. Does this fix pose any known compatibility risks?  
5\. Does it require manual verification by the test team? If so, please describe required testing.


---

**#18 — ah...@chromium.org — Mar 20, 2024 05:56PM**

1\. [https://chromium-review.googlesource.com/c/v8/v8/+/5374907](<https://chromium-review.googlesource.com/c/v8/v8/+/5374907>)  
2\. Yes, in 125.0.6368.0  
3\. No  
4\. No  
5\. No


---

**#19 — pe...@google.com — Mar 21, 2024 12:41AM**

This is sufficiently serious that it should be merged to extended stable. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M122. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately.  
This is sufficiently serious that it should be merged to stable. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M123. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately.  
This is sufficiently serious that it should be merged to dev. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M124. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately.  
Merge review required: M122 is already shipping to stable.  
  
  
Merge review required: M123 is already shipping to stable.  
  
  
Merge approved: your change passed merge requirements and is auto-approved for M124. Please go ahead and merge the CL to branch 6367 (refs/branch-heads/6367) manually. Please contact milestone owner if you have questions.  
Merge instructions: [https://chromium.googlesource.com/chromium/src.git/+/refs/heads/main/docs/process/merge_request.md](<https://chromium.googlesource.com/chromium/src.git/+/refs/heads/main/docs/process/merge_request.md>)  
Owners: eakpobaro (Android), eakpobaro (iOS), obenedict (ChromeOS), danielyip (Desktop)  
Thank you for fixing this security bug! We aim to ship security fixes as quickly as possible, to limit their opportunity for exploitation as an "n-day" (that is, a bug where git fixes are developed into attacks before those fixes reach users).  
  
We have determined this fix is necessary on milestone(s): [122, 123, 124].  
  
Please answer the following questions so that we can safely process this merge request:  
1\. Which CLs should be backmerged? (Please include Gerrit links.)  
2\. Has this fix been verified on Canary to not pose any stability regressions?  
3\. Does this fix pose any potential non-verifiable stability risks?  
4\. Does this fix pose any known compatibility risks?  
5\. Does it require manual verification by the test team? If so, please describe required testing.


---

**#20 — ah...@chromium.org — Mar 21, 2024 05:35PM**

1\. [https://chromium-review.googlesource.com/c/v8/v8/+/5374907](<https://chromium-review.googlesource.com/c/v8/v8/+/5374907>)  
2\. Yes, in 125.0.6368.0  
3\. No  
4\. No  
5\. No


---

**#21 — ap...@google.com — Mar 21, 2024 06:48PM**

Project: v8/v8  
Branch: refs/branch-heads/12.4  
  
commit 2a2e7a8b0a02a8211902a61eb588d2e05aa1c3a6  
Author: Andreas Haas <[ahaas@chromium.org](<mailto:ahaas@chromium.org>)>  
Date: Mon Mar 18 15:25:15 2024  
  
Merged: [wasm][gc] Scan the code field of the WasmInternalFunction  
  
The code field in the WasmInternalFunction is a code pointer since  
[https://crrev.com/c/5110559](<https://crrev.com/c/5110559>), so it has to be scanned explicitly.  
  
Bug: 329130358  
  
(cherry picked from commit b93975a48c722c2e5fe9b39437738eb2e23dac74)  
  
Change-Id: If179456d54b3790593c33ed5a6ac4dc2c24b631a  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5378293](<https://chromium-review.googlesource.com/c/v8/v8/+/5378293>)  
Reviewed-by: Clemens Backes <[clemensb@chromium.org](<mailto:clemensb@chromium.org>)>  
Commit-Queue: Andreas Haas <[ahaas@chromium.org](<mailto:ahaas@chromium.org>)>  
Cr-Commit-Position: refs/branch-heads/12.4@{#6}  
Cr-Branched-From: 309640da62fae0485c7e4f64829627c92d53b35d-refs/heads/12.4.254@{#1}  
Cr-Branched-From: 5dc24701432278556a9829d27c532f974643e6df-refs/heads/main@{#92862}  
  
M src/objects/objects-body-descriptors-inl.h  
A test/mjsunit/regress/wasm/regress-329130358.js  
  
[https://chromium-review.googlesource.com/5378293](<https://chromium-review.googlesource.com/5378293>)


---

**#22 — am...@google.com — Mar 28, 2024 01:52AM**

*** Boilerplate reminders! ***  
Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.  
******************************


---

**#23 — am...@chromium.org — Mar 28, 2024 01:55AM**

Congratulations! The Chrome VRP Panel has decided to award you $7,000 for this report. Thank you for your efforts and reporting this issue to us!


---

**#24 — am...@chromium.org — Mar 28, 2024 03:35AM**

M123 Stable and M122 Extended Stable merges approved for [https://crrev.com/c/5378293](<https://crrev.com/c/5378293>) please merge to 12.3-lkgr and 12.2-lkgr by EOD tomorrow, Thursday 28 March so this fix can be included in the next Stable and Extended Stable security updates -- thank you!


---

**#25 — pe...@google.com — Apr 1, 2024 11:47AM**

This issue has been approved for a merge. Please merge the fix to any appropriate branches as soon as possible!  
  
If all merges have been completed, please remove any remaining Merge-Approved labels from this issue.  
  
Thanks for your time! To disable nags, add Disable-Nags (case sensitive) to the Chromium Labels custom field.


---

**#26 — pb...@google.com — Apr 2, 2024 02:31AM**

Please find the merges to M123 and M122 below

12.3: [https://chromium-review.googlesource.com/c/v8/v8/+/5408910](<https://chromium-review.googlesource.com/c/v8/v8/+/5408910>) 12.2: [https://chromium-review.googlesource.com/c/v8/v8/+/5410311](<https://chromium-review.googlesource.com/c/v8/v8/+/5410311>)


---

**#27 — pe...@google.com — Apr 5, 2024 11:49AM**

This issue has been approved for a merge. Please merge the fix to any appropriate branches as soon as possible!  
  
If all merges have been completed, please remove any remaining Merge-Approved labels from this issue.  
  
Thanks for your time! To disable nags, add Disable-Nags (case sensitive) to the Chromium Labels custom field.


---

**#28 — pe...@google.com — Jun 26, 2024 12:42AM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
