# JSPI stack switching breaks lazy deoptimization guarantees, leading to type confusion

Issue URL: https://issues.chromium.org/issues/365376497
VRP-Reward: 55000
Date: Sep 9, 2024 04:57AM


Wasm JSPI (JavaScript Promise Integration) is an experimental feature allowing Wasm functions to suspend and resume execution, integrating with JavaScript promises. This is implemented by executing asynchronous Wasm functions on a separately allocated stack, and switching to/from this stack when needed. However, the deoptimizer is currently unaware of these stacks when handling lazy deoptimization, which can result in deoptimized code still being executed after its invariants have been invalidated. These broken invariants can lead to memory corruption / type confusion, and together with a sandbox escape (like the one I reported recently, see [issue 361862752](<https://issues.chromium.org/issues/361862752>)) to a full renderer compromise.

Note that JSPI, while still in an experimental state right now, is [currently undergoing origin trials](<https://chromestatus.com/feature/5674874568704000>), effectively already making it part of the attack surface exposed to malicious actors. As a result, the exploit chain reported here can be used to compromise any Chromium build starting from build 123 to latest, as well as older builds whose `#enable-experimental-webassembly-jspi` flag has been manually enabled. JSPI is also close to being standardized ([the V8 blog post](<https://v8.dev/blog/jspi>) mentions that "we anticipate full standardization before the end of 2024"), and is likely to ship as a stable feature soon after, so future builds past the end of origin trials would most likely also be affected.

See the following attachments of this issue:

  * `poc.js`: a minimal proof-of-concept which triggers this bug. It exploits the reported issue to bypass stable map code dependencies, resulting in type confusion, which is used to leak the address of an heap object.
  * `exploit.js`: a full exploit chain utilizing this bug + the sandbox escape reported in [issue 361862752](<https://issues.chromium.org/issues/361862752>) to gain full remote code execution capabilities. The executed shellcode is configurable, but defaults to a single `int3`, which causes the Chromium tab to crash with error code `SIGTRAP` / `STATUS_BREAKPOINT`. 
    * A version of this exploit which has been instrumented with a WebSocket-based logging harness is also available, hosted at `https://cytc.popax21.dev/87230a91463f61e51f372e2242ca8364a9843cac5de36c6cb4f10953c95a5615` (append `?tab` to run the exploit in a popup window instead of an iframe). This can be used to view the log output as the exploit runs, and has been the main way I have tested this exploit on different devices. Note that if this domain were signed up for the JSPI origin trial, it could be used to compromise recent Chromium builds without the need to enable any feature flags.
  * `patch.diff`: a proposed patch for this issue. It patches the deoptimizer to also traverse all Wasm stacks when deoptimizing a function. Through my own testing, this is confirmed to fix this vulnerability.

There are multiple ways of fixing this issue aside from the one implemented in the submitted patch. For example, it would also be possible to handle stack switches while traversing the current stack; this would fix the attack vector for JavaScript functions, while also combating potential performance degradation as a result of having to traverse all suspended Wasm stacks. However, one would still have to traverse these stacks when a Wasm function gets deoptimized since the function might currently be suspended on such a stack, so a hybrid approach would be required to fully fix the vulnerability in this manner. Because of the complexity of such a hybrid fix, I have opted against implementing it, instead opting to implement the simpler, guaranteed-to-work fix.

This exploit (and its associated patch) has been tested and confirmed to work on the following platforms:

  * Chromium 128.0.6613.119, AMD64, Arch Linux 6.9.7-arch1-1, using the `#enable-experimental-webassembly-jspi` flag
  * Chrome Stable 128.0.6613.119, AMD64, Arch Linux 6.9.7-arch1-1, using the `#enable-experimental-webassembly-jspi` flag (*)
  * Chrome Canary 130.0.6705.0 (cohort: clang-64), AMD64, Windows 10, using the `#enable-experimental-webassembly-jspi` flag (*)
  * V8 commit 6f7722597815e33071508c02a0f2add34e83dd1d, release build, AMD64, Arch Linux 6.9.7-arch1-1, using `d8 --wasm-staging`
  * V8 commit 6f7722597815e33071508c02a0f2add34e83dd1d, debug build, AMD64, Arch Linux 6.9.7-arch1-1, using `d8 --wasm-staging`

(*): During testing, the exploit has failed to replicate reliably on Chrome because of randomized field trials (namely `V8WasmTurboshaft`, which causes the sandbox escape to fail, as well as others). However, in all cases the exploit failed after having already successfully triggered the initial vulnerability; only later stages were affected by failures. Setting the `#enable-benchmarking` flag causes the exploit to work reliably in all cases. This is not an inherent limitation of the vulnerability; it would be possible to craft a more reliable exploit using, for example, a different, less mitigated sandbox escape.

Reporter Credit: if applicable, please credit my pseudonym Popax21 in regards to this report.


---

**#2 — cl...@appspot.gserviceaccount.com — Sep 9, 2024 06:13AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5195964172140544](<https://clusterfuzz.com/testcase?key=5195964172140544>).


---

**#3 — aj...@google.com — Sep 9, 2024 06:16AM**

Thanks for the detailed report that covers both the issue and its impact. The OT means this is not impact=None.

Setting provisional labels and sending to the v8 rotation for further triage.


---

**#4 — cf...@google.com — Sep 9, 2024 08:26PM**

Assigning to thibaudm@ as the proper owner for this issue.


---

**#5 — th...@chromium.org — Sep 9, 2024 10:25PM**

Thanks for the great report!  
One comment on the suggested fix: I checked with mliedtke@ (owner of wasm deopt), and it sounds like this does not affect wasm. Wasm does not support lazy deopt and can only deopt inside the generated code, and there is no current plan to change that. So since suspended stacks don't contain JS frames, it should be sufficient to iterate the active stack and its ancestors here.


---

**#6 — ma...@gmail.com — Sep 9, 2024 10:47PM**

ClusterFuzz seems to label the POC as unreproducible, since it only causes "safe" memory corruption (i.e. leaking the address of an object). I've attached a modified variant of the POC which uses type confusion to create a garbage tagged pointer, which causes a crash; this variant should be more suitable for ClusterFuzz.


---

**#7 — ma...@gmail.com — Sep 9, 2024 11:39PM**

> One comment on the suggested fix: I checked with mliedtke@ (owner of wasm deopt), and it sounds like this does not affect wasm. Wasm does not support lazy deopt and can only deopt inside the generated code, and there is no current plan to change that. So since suspended stacks don't contain JS frames, it should be sufficient to iterate the active stack and its ancestors here.

I see. I was unsure of whether Wasm could also potentially be affected by this, so I opted for a more conservative fix. See attached an implementation of a stack switch-traversal based fix, based on `Isolate::UnwindAndFindHandler`. In my testing, it also fixes the issue, however, this would definitely need review by someone who's more familiar with Wasm stack switches / archived threads, since I'm not sure that I handled all the intricacies there correctly.


---

**#8 — sa...@google.com — Sep 10, 2024 12:06AM**

Thanks for the great report! Awesome work!


---

**#9 — pe...@google.com — Sep 10, 2024 12:38AM**

Setting milestone because of s0/s1 severity.


---

**#10 — ap...@google.com — Sep 10, 2024 08:17PM**

Project: v8/v8  
Branch: main  
  
commit 906e41b88fa5b79d2afc699f8c4da87c4eb9c7e5  
Author: Thibaud Michaud <[thibaudm@chromium.org](<mailto:thibaudm@chromium.org>)>  
Date: Tue Sep 10 10:52:38 2024  
  
[wasm][jspi] Fix JSPI + lazy deopt  
  
With JSPI, the stack frame iterator stops at the end of the current  
stack segment. Follow the chain of stacks to find all frames marked for  
deoptimization.  
  
R=[mliedtke@chromium.org](<mailto:mliedtke@chromium.org>)  
  
Fixed: 365376497  
Change-Id: Iff1112dbd2a86a014c8de6d844f585fd568ad552  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5850428](<https://chromium-review.googlesource.com/c/v8/v8/+/5850428>)  
Commit-Queue: Thibaud Michaud <[thibaudm@chromium.org](<mailto:thibaudm@chromium.org>)>  
Reviewed-by: Matthias Liedtke <[mliedtke@chromium.org](<mailto:mliedtke@chromium.org>)>  
Cr-Commit-Position: refs/heads/main@{#96028}  
  
M src/deoptimizer/deoptimizer.cc  
  
[https://chromium-review.googlesource.com/5850428](<https://chromium-review.googlesource.com/5850428>)


---

**#11 — pe...@google.com — Sep 11, 2024 12:42AM**

Security Merge Request Consideration: This is sufficiently serious that it should be merged to stable. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M128. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately. Security Merge Request Consideration: This is sufficiently serious that it should be merged to beta. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M129. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately. Security Merge Request: Thank you for fixing this security bug! We aim to ship security fixes as quickly as possible, to limit their opportunity for exploitation as an "n-day" (that is, a bug where git fixes are developed into attacks before those fixes reach users).

We have determined this fix is necessary on milestone(s): [].

Please answer the following questions so that we can safely process this merge request:

  1. Which CLs should be backmerged? (Please include Gerrit links.)
  2. Has this fix been verified on Canary to not pose any stability regressions?
  3. Does this fix pose any potential non-verifiable stability risks?
  4. Does this fix pose any known compatibility risks?
  5. Does it require manual verification by the test team? If so, please describe required testing.
  6. (no answer required) Please check the OS custom field to ensure all impacted OSes are checked!


---

**#12 — am...@chromium.org — Sep 11, 2024 02:07AM**

M129 Stable RC is being cut today; however this fix just landed this morning so there is no intent to get this merged for M129 Stable RC today. This will be assessed for backmerge later this week.


---

**#13 — pe...@google.com — Sep 11, 2024 08:29PM**

Merge review required: M129 has already been cut for stable release.

Please answer the following questions so that we can safely process your merge request:

  1. Why does your merge fit within the merge criteria for these milestones?

  * Chrome Browser: [https://chromiumdash.appspot.com/branches](<https://chromiumdash.appspot.com/branches>)
  * Chrome OS: [https://goto.google.com/cros-release-branch-merge-guidelines](<https://goto.google.com/cros-release-branch-merge-guidelines>)

  2. What changes specifically would you like to merge? Please link to Gerrit.
  3. Have the changes been released and tested on canary?
  4. Is this a new feature? If yes, is it behind a Finch flag and are experiments active in any release channels?
  5. [Chrome OS only]: Was the change reviewed and approved by the Eng Prod Representative? [https://goto.google.com/cros-engprodcomponents](<https://goto.google.com/cros-engprodcomponents>)
  6. If this merge addresses a major issue in the stable channel, does it require manual verification by the test team? If so, please describe required testing.

Please contact the milestone owner if you have questions. Owners: govind (Android), govind (iOS), matthewjoseph (ChromeOS), srinivassista (Desktop)


---

**#14 — pe...@google.com — Sep 11, 2024 08:29PM**

Merge review required: M128 is already shipping to stable.

Please answer the following questions so that we can safely process your merge request:

  1. Why does your merge fit within the merge criteria for these milestones?

  * Chrome Browser: [https://chromiumdash.appspot.com/branches](<https://chromiumdash.appspot.com/branches>)
  * Chrome OS: [https://goto.google.com/cros-release-branch-merge-guidelines](<https://goto.google.com/cros-release-branch-merge-guidelines>)

  2. What changes specifically would you like to merge? Please link to Gerrit.
  3. Have the changes been released and tested on canary?
  4. Is this a new feature? If yes, is it behind a Finch flag and are experiments active in any release channels?
  5. [Chrome OS only]: Was the change reviewed and approved by the Eng Prod Representative? [https://goto.google.com/cros-engprodcomponents](<https://goto.google.com/cros-engprodcomponents>)
  6. If this merge addresses a major issue in the stable channel, does it require manual verification by the test team? If so, please describe required testing.

Please contact the milestone owner if you have questions. Owners: harrysouders (Android), harrysouders (iOS), obenedict (ChromeOS), pbommana (Desktop)


---

**#15 — th...@chromium.org — Sep 11, 2024 11:16PM**

#11:  
1\. Which CLs should be backmerged? (Please include Gerrit links.)  
[https://chromium-review.googlesource.com/c/v8/v8/+/5850428](<https://chromium-review.googlesource.com/c/v8/v8/+/5850428>)  
2\. Has this fix been verified on Canary to not pose any stability regressions?  
Yes, in 130.0.6711.0  
3\. Does this fix pose any potential non-verifiable stability risks?  
No  
4\. Does this fix pose any known compatibility risks?  
No  
5\. Does it require manual verification by the test team? If so, please describe required testing.  
No  
  
#13, #14:  
1\. Why does your merge fit within the merge criteria for these milestones?  
Fixes an important security issue  
2\. What changes specifically would you like to merge? Please link to Gerrit.  
[https://chromium-review.googlesource.com/c/v8/v8/+/5850428](<https://chromium-review.googlesource.com/c/v8/v8/+/5850428>)  
3\. Have the changes been released and tested on canary?  
Yes, in 130.0.6711.0  
4\. Is this a new feature? If yes, is it behind a Finch flag and are experiments active in any release channels?  
This is not a new feature  
5\. 6. NA


---

**#16 — am...@chromium.org — Sep 13, 2024 06:37AM**

Not seeing any issues on Canary related to this change; merges approved for [https://crrev.com/c/5850428](<https://crrev.com/c/5850428>) please backmerge to 12.8 and 12.9 by EOD tomorrow, Friday, 13 September so this fix can be included in the recut of 129 Stable for release Tuesday


---

**#17 — ap...@google.com — Sep 13, 2024 07:40PM**

Project: v8/v8  
Branch: refs/branch-heads/12.8  
  
commit bac3426b79010612edf40319174fbc0ab6ea2f86  
Author: Thibaud Michaud <[thibaudm@chromium.org](<mailto:thibaudm@chromium.org>)>  
Date: Tue Sep 10 10:52:38 2024  
  
Merged: [wasm][jspi] Fix JSPI + lazy deopt  
  
With JSPI, the stack frame iterator stops at the end of the current  
stack segment. Follow the chain of stacks to find all frames marked for  
deoptimization.  
  
R=[mliedtke@chromium.org](<mailto:mliedtke@chromium.org>)  
  
Fixed: 365376497  
(cherry picked from commit 906e41b88fa5b79d2afc699f8c4da87c4eb9c7e5)  
  
Change-Id: Ic4174cdd114c2a851d86a3985d25fedff2ebaec8  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5860736](<https://chromium-review.googlesource.com/c/v8/v8/+/5860736>)  
Reviewed-by: Matthias Liedtke <[mliedtke@chromium.org](<mailto:mliedtke@chromium.org>)>  
Commit-Queue: Thibaud Michaud <[thibaudm@chromium.org](<mailto:thibaudm@chromium.org>)>  
Cr-Commit-Position: refs/branch-heads/12.8@{#65}  
Cr-Branched-From: 70cbb397b153166027e34c75adf8e7993858222e-refs/heads/12.8.374@{#1}  
Cr-Branched-From: 451b63ed4251c2b21c56144d8428f8be3331539b-refs/heads/main@{#95151}  
  
M src/deoptimizer/deoptimizer.cc  
  
[https://chromium-review.googlesource.com/5860736](<https://chromium-review.googlesource.com/5860736>)


---

**#18 — pe...@google.com — Sep 13, 2024 07:42PM**

LTS Milestone M126

This issue has been flagged as a merge candidate for Chrome OS' LTS channel. If selected, our merge team will handle any additional merges. To help us determine if this issue requires a merge to LTS, please answer this short questionnaire:

  1. Was this issue a regression for the milestone it was found in?
  2. Is this issue related to a change or feature merged after the latest LTS Milestone?


---

**#19 — ap...@google.com — Sep 13, 2024 07:42PM**

Project: v8/v8  
Branch: refs/branch-heads/12.9  
  
commit 000866bcb5d2f8868dbcb1b7b4a0d92dec9a006f  
Author: Thibaud Michaud <[thibaudm@chromium.org](<mailto:thibaudm@chromium.org>)>  
Date: Tue Sep 10 10:52:38 2024  
  
Merged: [wasm][jspi] Fix JSPI + lazy deopt  
  
With JSPI, the stack frame iterator stops at the end of the current  
stack segment. Follow the chain of stacks to find all frames marked for  
deoptimization.  
  
R=[mliedtke@chromium.org](<mailto:mliedtke@chromium.org>)  
  
Fixed: 365376497  
(cherry picked from commit 906e41b88fa5b79d2afc699f8c4da87c4eb9c7e5)  
  
Change-Id: I4e60cfcf83d66a3810caf3ace3ff32ce30728bf2  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5860576](<https://chromium-review.googlesource.com/c/v8/v8/+/5860576>)  
Reviewed-by: Matthias Liedtke <[mliedtke@chromium.org](<mailto:mliedtke@chromium.org>)>  
Commit-Queue: Thibaud Michaud <[thibaudm@chromium.org](<mailto:thibaudm@chromium.org>)>  
Cr-Commit-Position: refs/branch-heads/12.9@{#35}  
Cr-Branched-From: 64a21d7ad7fca1ddc73a9264132f703f35000b69-refs/heads/12.9.202@{#1}  
Cr-Branched-From: da4200b2cfe6eb1ad73c457ed27cf5b7ff32614f-refs/heads/main@{#95679}  
  
M src/deoptimizer/deoptimizer.cc  
  
[https://chromium-review.googlesource.com/5860576](<https://chromium-review.googlesource.com/5860576>)


---

**#20 — pb...@google.com — Sep 14, 2024 03:17AM**

The Cl has been merged to m128 branch as [https://chromium-review.googlesource.com/c/v8/v8/+/5860736](<https://chromium-review.googlesource.com/c/v8/v8/+/5860736>)


---

**#21 — sp...@google.com — Sep 19, 2024 08:56AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $55000.00 for this report.  
  
Rationale for this decision:  
high quality report with demonstration of RCE in a sandboxed process / the renderer   
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#22 — am...@chromium.org — Sep 19, 2024 09:06AM**

Congratulations Popax21! Thank you for you excellent work on this and the demonstration of exploitability and RCE. We appreciate your efforts and reporting this issue to us -- great work!


---

**#23 — pe...@google.com — Sep 20, 2024 12:27AM**

This issue requires additional review before it can be merged to the LTS channel. Please answer the following questions to help us evaluate this merge:

  1. Number of CLs needed for this fix and links to them.
  2. Level of complexity (High, Medium, Low - Explain)
  3. Has this been merged to a stable release? beta release?
  4. Overall Recommendation (Yes, No)


---

**#24 — qk...@google.com — Sep 20, 2024 09:53AM**

1\. [https://chromium-review.googlesource.com/c/v8/v8/+/5874952](<https://chromium-review.googlesource.com/c/v8/v8/+/5874952>)  
2\. Low, no conflicts  
3\. 128 and 129  
4\. Yes


---

**#25 — gm...@google.com — Sep 21, 2024 12:33AM**

Answer to question 3 is 128 and 129.  
Approving.


---

**#26 — qk...@google.com — Oct 10, 2024 03:41PM**

I labeled this bug from LTS-Merge-Approved-126 to LTS-NotApplicable-126 because the fix[1] requires merging complex dependency patches[2][3] together. In my opinion, it would be safer not to merge back them to M126.  
  
[1] [https://chromium-review.googlesource.com/c/v8/v8/+/5874952](<https://chromium-review.googlesource.com/c/v8/v8/+/5874952>)  
[2] [https://chromium-review.googlesource.com/c/v8/v8/+/5604267](<https://chromium-review.googlesource.com/c/v8/v8/+/5604267>)  
[3] [https://chromium-review.googlesource.com/c/v8/v8/+/5665558](<https://chromium-review.googlesource.com/c/v8/v8/+/5665558>)


---

**#27 — pe...@google.com — Dec 19, 2024 12:44AM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.


---

**#28 — ap...@google.com — Feb 8, 2025 07:23AM**

Project: v8/v8  
Branch: main  
Author: Thibaud Michaud <[thibaudm@chromium.org](<mailto:thibaudm@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6244297](<https://chromium-review.googlesource.com/6244297>)

[wasm] Add regression test

* * *

Expand for full commit details

```
[wasm] Add regression test 
 
R=jkummerow@chromium.org 
 
Bug: 365376497 
Change-Id: I733a39b796f7a72f6bd3f75cd0f852e4f7c90d24 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6244297 
Reviewed-by: Jakob Kummerow <jkummerow@chromium.org> 
Commit-Queue: Thibaud Michaud <thibaudm@chromium.org> 
Cr-Commit-Position: refs/heads/main@{#98588}
```

* * *

Files:

  * A `test/mjsunit/regress/wasm/regress-365376497.js`

* * *

Hash: 208862261fe346f83786703da16c1872ebe1e579  
Date: Fri Feb 07 17:42:05 2025

* * *
