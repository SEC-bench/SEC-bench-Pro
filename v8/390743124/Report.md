# SIGSEGV in v8 regexp

Issue URL: https://issues.chromium.org/issues/390743124
VRP-Reward: 7000
Date: Jan 18, 2025 11:37PM


#### Description

ki...@gmail.com created issue [ #1](</issues/390743124#comment1>)

Jan 18, 2025 11:37PM

  
VULNERABILITY DETAILS  
## INTRODUCE  
After bisect, it was determined that following commit caused this problem.  
  
\- Commit Info  
\- Version: 97957  
\- link: [https://crrev.com/d1e497387a953db6daa37792e73150e397fbf7e3](<https://crrev.com/d1e497387a953db6daa37792e73150e397fbf7e3>)  
\- Commit Message  
  
```  
commit d1e497387a953db6daa37792e73150e397fbf7e3  
Author: Samuel Groß <[saelo@chromium.org](<mailto:saelo@chromium.org>)>  
Date: Fri Jan 3 17:27:02 2025 +0000  
  
[sandbox] Reserve some pages at the start of trusted space  
  
This CL adds a simple mitigation for compressed nullptr dereference bugs  
in trusted space. Since we use zero as empty/missing value for protected  
pointer fields (pointers between objects in trusted space), we can have  
the equivalent of nullptr dereference bugs, but instead of accessing  
address zero, they will access the start of trusted space (because they  
are just offsets from the start of trusted space). With this CL, we now  
simply place a PROT_NONE mapping at the start of trusted space which  
should render most of these bugs unexploitable.  
  
Bug: 387491279  
Change-Id: Ic00e8bfa5f2373bc0d43bb6730a07b183e862c1f  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/6141634](<https://chromium-review.googlesource.com/c/v8/v8/+/6141634>)  
Reviewed-by: Michael Lippautz <[mlippautz@chromium.org](<mailto:mlippautz@chromium.org>)>  
Commit-Queue: Samuel Groß <[saelo@chromium.org](<mailto:saelo@chromium.org>)>  
Cr-Commit-Position: refs/heads/main@{#97957}  
  
```  
  
## CRASH LOG  
\- Debug output  
  
```bash  
# CMD: /tmp/d8-linux-debug-v8-component-98188/d8 --allow-natives-syntax poc.js  
# OUTPUT ==============================================================  
Received signal 11 SEGV_ACCERR 3e8700140000  
  
==== C stack trace ===============================  
  
/tmp/d8-linux-debug-v8-component-98188/libv8_libbase.so(_ZN2v84base5debug10StackTraceC2Ev+0x13)[0x7f71e6a88a13]  
/tmp/d8-linux-debug-v8-component-98188/libv8_libbase.so(+0x4b962)[0x7f71e6a88962]  
/lib/x86_64-linux-gnu/libc.so.6(+0x42520)[0x7f71e0442520]  
/tmp/d8-linux-debug-v8-component-98188/libv8.so(_ZNK2v88internal10HandleBase20IsDereferenceAllowedEv+0x44)[0x7f71e3be5de4]  
/tmp/d8-linux-debug-v8-component-98188/libv8.so(_ZNK2v88internal15TranslatedValue11GetRawValueEv+0x41)[0x7f71e3a71ab1]  
/tmp/d8-linux-debug-v8-component-98188/libv8.so(_ZN2v88internal15TranslatedValue8GetValueEv+0x17)[0x7f71e3a724e7]  
/tmp/d8-linux-debug-v8-component-98188/libv8.so(_ZN2v88internal15TranslatedState23EnsureChildrenAllocatedEiPNS0_15TranslatedFrameEPiPNSt4__Cr5stackIiNS5_5dequeIiNS5_9allocatorIiEEEEEE+0x158)[0x7f71e3a7efc8]  
/tmp/d8-linux-debug-v8-component-98188/libv8.so(_ZN2v88internal15TranslatedState31EnsureCapturedObjectAllocatedAtEiPNSt4__Cr5stackIiNS2_5dequeIiNS2_9allocatorIiEEEEEE+0x765)[0x7f71e3a7db45]  
/tmp/d8-linux-debug-v8-component-98188/libv8.so(_ZN2v88internal15TranslatedState23EnsureObjectAllocatedAtEPNS0_15TranslatedValueE+0xfe)[0x7f71e3a72cee]  
/tmp/d8-linux-debug-v8-component-98188/libv8.so(_ZN2v88internal15TranslatedValue8GetValueEv+0x337)[0x7f71e3a72807]  
/tmp/d8-linux-debug-v8-component-98188/libv8.so(_ZN2v88internal11Deoptimizer22MaterializeHeapObjectsEv+0xb0)[0x7f71e3a607a0]  
/tmp/d8-linux-debug-v8-component-98188/libv8.so(+0x3cf7084)[0x7f71e48f7084]  
/tmp/d8-linux-debug-v8-component-98188/libv8.so(_ZN2v88internal25Runtime_NotifyDeoptimizedEiPmPNS0_7IsolateE+0x89)[0x7f71e48f6989]  
[0x7f715f73babd]  
[end of stack trace]  
  
```  
  
## Other  
Please note to include the flags `--allow-natives-syntax` for clusterfuzz classification.  
  
VERSION  
Tested on v8 version: 13.4.0 - 13.4.0  
  
REPRODUCTION CASE  
1\. Download debug v8 from: gs://v8-asan/linux-debug/d8-linux-debug-v8-component-98188.zip  
2\. Run: `d8 --allow-natives-syntax poc.js`  
  
FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION  
Type of crash: tab  
  
CREDIT INFORMATION  
Reporter credit: Zhenghang Xiao (@Kipreyyy) and Nan Wang (@eternalsakura13)  

poc.js 

518 B [ View](<https://issues.chromium.org/action/issues/390743124/attachments/62250184?download=false>)[ Download](<https://issues.chromium.org/action/issues/390743124/attachments/62250184?download=true>)


---

**#2 — cl...@appspot.gserviceaccount.com — Jan 19, 2025 01:02AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=6283911583694848](<https://clusterfuzz.com/testcase?key=6283911583694848>).


---

**#3 — 24...@project.gserviceaccount.com — Jan 19, 2025 01:43AM**

Detailed Report: [https://clusterfuzz.com/testcase?key=6283911583694848](<https://clusterfuzz.com/testcase?key=6283911583694848>)  
  
Fuzzer: None  
Job Type: linux_asan_d8_dbg  
Platform Id: linux  
  
Crash Type: UNKNOWN READ  
Crash Address: 0x734000140000  
Crash State:  
v8::internal::HandleBase::IsDereferenceAllowed  
v8::internal::TranslatedValue::GetRawValue  
v8::internal::TranslatedValue::GetValue  
  
Sanitizer: address (ASAN)  
  
Recommended Security Severity: Medium  
  
Regressed: [https://clusterfuzz.com/revisions?job=linux_asan_d8_dbg&range=97956:97957](<https://clusterfuzz.com/revisions?job=linux_asan_d8_dbg&range=97956:97957>)  
  
Reproducer Testcase: [https://clusterfuzz.com/download?testcase_id=6283911583694848](<https://clusterfuzz.com/download?testcase_id=6283911583694848>)  
  
To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.   
  
If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.  
  
If you have any feedback on reproducing test cases, let us know at [https://forms.gle/Yh3qCYFveHj6E5jz5](<https://forms.gle/Yh3qCYFveHj6E5jz5>) so we can improve.  
  
  
A recommended severity was added to this bug. Please change the severity if it is inaccurate.


---

**#4 — 24...@project.gserviceaccount.com — Jan 19, 2025 01:52AM**

Automatically applying components based on crash stacktrace and information from OWNERS files.  
  
If this is incorrect, please apply the hotlistid:4801165.


---

**#5 — 24...@project.gserviceaccount.com — Jan 19, 2025 01:52AM**

Automatically assigning owner based on suspected regression changelist [https://chromium.googlesource.com/v8/v8/+/d1e497387a953db6daa37792e73150e397fbf7e3](<https://chromium.googlesource.com/v8/v8/+/d1e497387a953db6daa37792e73150e397fbf7e3>) ([sandbox] Reserve some pages at the start of trusted space  
  
This CL adds a simple mitigation for compressed nullptr dereference bugs  
in trusted space. Since we use zero as empty/missing value for protected  
pointer fields (pointers between objects in trusted space), we can have  
the equivalent of nullptr dereference bugs, but instead of accessing  
address zero, they will access the start of trusted space (because they  
are just offsets from the start of trusted space). With this CL, we now  
simply place a PROT_NONE mapping at the start of trusted space which  
should render most of these bugs unexploitable.  
  
Bug: 387491279  
Change-Id: Ic00e8bfa5f2373bc0d43bb6730a07b183e862c1f  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/6141634](<https://chromium-review.googlesource.com/c/v8/v8/+/6141634>)  
Reviewed-by: Michael Lippautz <[mlippautz@chromium.org](<mailto:mlippautz@chromium.org>)>  
Commit-Queue: Samuel Groß <[saelo@chromium.org](<mailto:saelo@chromium.org>)>  
Cr-Commit-Position: refs/heads/main@{#97957}  
).  
  
If this is incorrect, please let us know why and apply the hotlistid:5433122. If you aren't the correct owner for this issue, please unassign yourself as soon as possible so it can be re-triaged.


---

**#6 — pe...@google.com — Jan 20, 2025 12:36AM**

Setting milestone because of s2 severity.


---

**#7 — pe...@google.com — Jan 20, 2025 12:36AM**

This is a serious security regression. If you are not able to fix this quickly, please revert the change that introduced it.

If this doesn't affect a release branch, or has not been properly classified for severity, please update the Security Impact hotlist or the Severity field, and remove the ReleaseBlock hotlist.


---

**#8 — pe...@google.com — Jan 20, 2025 12:37AM**

Setting Priority to P1 to match Severity s2. If this is incorrect, please reset the priority. The automation bot account won't make this change again.


---

**#9 — ki...@gmail.com — Jan 29, 2025 12:57PM**

hello, any update?


---

**#10 — pe...@google.com — Feb 3, 2025 12:37AM**

saelo: Uh oh! This issue still open and hasn't been updated in the last 14 days. This is a serious vulnerability, and we want to ensure that there's progress. Could you please leave an update with the current status and any potential blockers?

If you're not the right owner for this issue, could you please remove yourself as soon as possible or help us find the right one?

If the issue is fixed or you can't reproduce it, please close the bug. If you've started working on a fix, please set the status to Started.

Thanks for your time! To disable nags, add Disable-Nags (case sensitive) to the Chromium Labels custom field.


---

**#11 — am...@chromium.org — Feb 15, 2025 11:31AM**

based on the CL this bisected to, clusterfuzz assigned this to saelo@ who is presently OOO and it appears to have fallen between the cracks; this is presently tagged as RBS for M134, the RC for Early Stable is being cut on Tuesday

PTAL ASAP and prioritize quickly for resolution or update the `ReleaseBlock` field if this should not be considered a security regression


---

**#12 — ml...@chromium.org — Feb 17, 2025 05:48PM**

cc'ing some deoptimizer folks for visibility and helping triage.


---

**#13 — le...@chromium.org — Feb 17, 2025 11:55PM**

It looks like this is seeing a Phi that thinks it is tagged, but one input is a TrustedHeapConstant (and the trusted cage bits are getting wiped out by decompression elimination, leading to an invalid pointer). Probably this is an issue originating in [https://chromium-review.googlesource.com/c/v8/v8/+/5756708](<https://chromium-review.googlesource.com/c/v8/v8/+/5756708>)


---

**#14 — ap...@google.com — Feb 18, 2025 07:28PM**

Project: v8/v8  
Branch: main  
Author: Darius Mercadier <[dmercadier@chromium.org](<mailto:dmercadier@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6278358](<https://chromium-review.googlesource.com/6278358>)

[turbofan] Disable escape analysis for TrustedHeapConstant

* * *

Expand for full commit details

```
[turbofan] Disable escape analysis for TrustedHeapConstant 
 
More precisely: prevent eliding objects that contain 
TrustedHeapConstant, because it can lead to this constant flowing into 
a Phis where other inputs are regular HeapConstant, which confuses 
decompression optimization and leads to memory corruption. 
 
Fixed: chromium:390743124 
Change-Id: Ic60e4d7dd156367f7d4bb385d422591384c3033c 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6278358 
Reviewed-by: Nico Hartmann <nicohartmann@chromium.org> 
Commit-Queue: Nico Hartmann <nicohartmann@chromium.org> 
Auto-Submit: Darius Mercadier <dmercadier@chromium.org> 
Cr-Commit-Position: refs/heads/main@{#98748}
```

* * *

Files:

  * M `src/compiler/escape-analysis.cc`

* * *

Hash: b75e527fb521dca5e7621928846c0c7c6becc8dd  
Date: Tue Feb 18 09:32:04 2025

* * *


---

**#15 — 24...@project.gserviceaccount.com — Feb 19, 2025 04:29PM**

ClusterFuzz testcase 6283911583694848 is verified as fixed in [https://clusterfuzz.com/revisions?job=linux_asan_d8_dbg&range=98747:98748](<https://clusterfuzz.com/revisions?job=linux_asan_d8_dbg&range=98747:98748>)  
  
If this is incorrect, please add the hotlistid:5433040 and re-open the issue.


---

**#16 — pe...@google.com — Feb 21, 2025 12:37AM**

This release blocking issue appears to be targeted for one or more milestones which may have already branched:

  * M134, which branched on 2025-02-03 (Chromium branch: 6998, Chromium branch position: 1415337)

Because this issue was marked as fixed on or after branch day, a merge of any CLs which landed on or after branch day may be required.

If no merge is needed (e.g. the necessary CLs are already present in the relevant branch), please remove TBD-## from the Merge field and replace it with NA-## (where ## corresponds to the milestone under evaluation). If a merge is necessary, the requested milestone(s) to the Merge-Request field. If you're not sure, reach out to the relevant release manager (can be found at [https://chromiumdash.appspot.com/schedule](<https://chromiumdash.appspot.com/schedule>)).

To learn more about the merge process, including how to land any required merges, see [https://chromium.googlesource.com/chromium/src.git/+/refs/heads/main/docs/process/merge_request.md](<https://chromium.googlesource.com/chromium/src.git/+/refs/heads/main/docs/process/merge_request.md>).


---

**#17 — dm...@chromium.org — Feb 21, 2025 12:46AM**

The issue has been around since [https://crrev.com/c/5756708](<https://crrev.com/c/5756708>) (==> M129), so we should backmerge [https://crrev.com/c/6278358](<https://crrev.com/c/6278358>) to M134 and M133.

(I tried to reflect this in the Merge-Request and Milestones field; I hope I got it right)


---

**#18 — ph...@google.com — Feb 21, 2025 02:39AM**

Merge review required: M134 is already shipping to beta.

Please answer the following questions so that we can safely process your merge request:

  1. Why does your merge fit within the merge criteria for these milestones?

  * Chrome Browser: [https://chromiumdash.appspot.com/branches](<https://chromiumdash.appspot.com/branches>)
  * Chrome OS: [https://goto.google.com/cros-release-branch-merge-guidelines](<https://goto.google.com/cros-release-branch-merge-guidelines>)

  2. What changes specifically would you like to merge? Please link to Gerrit.
  3. Have the changes been released and tested on canary?
  4. Is this a new feature? If yes, is it behind a Finch flag and are experiments active in any release channels?
  5. [Chrome OS only]: Was the change reviewed and approved by the Eng Prod Representative? [https://goto.google.com/cros-engprodcomponents](<https://goto.google.com/cros-engprodcomponents>)
  6. If this merge addresses a major issue in the stable channel, does it require manual verification by the test team? If so, please describe required testing.

Please contact the milestone owner if you have questions. Owners: lmenezes (ChromeOS), srinivassista (Desktop US), danielyip (Desktop EMEA), govind (Mobile US), eakpobaro (Mobile EMEA)


---

**#19 — ph...@google.com — Feb 21, 2025 02:39AM**

Merge review required: M133 is already shipping to stable.

Please answer the following questions so that we can safely process your merge request:

  1. Why does your merge fit within the merge criteria for these milestones?

  * Chrome Browser: [https://chromiumdash.appspot.com/branches](<https://chromiumdash.appspot.com/branches>)
  * Chrome OS: [https://goto.google.com/cros-release-branch-merge-guidelines](<https://goto.google.com/cros-release-branch-merge-guidelines>)

  2. What changes specifically would you like to merge? Please link to Gerrit.
  3. Have the changes been released and tested on canary?
  4. Is this a new feature? If yes, is it behind a Finch flag and are experiments active in any release channels?
  5. [Chrome OS only]: Was the change reviewed and approved by the Eng Prod Representative? [https://goto.google.com/cros-engprodcomponents](<https://goto.google.com/cros-engprodcomponents>)
  6. If this merge addresses a major issue in the stable channel, does it require manual verification by the test team? If so, please describe required testing.

Please contact the milestone owner if you have questions. Owners: andywu (ChromeOS), pbommana (Desktop US), danielyip (Desktop EMEA), harrysouders (Mobile US), eakpobaro (Mobile EMEA)


---

**#20 — dm...@chromium.org — Feb 21, 2025 05:03PM**

Reply to comments #18 and #19:

  1. Security vulnerability on stable
  2. [https://crrev.com/c/6278358](<https://crrev.com/c/6278358>)
  3. Yes (it's in 135.0.7023.0)
  4. no
  5. N/A
  6. no


---

**#21 — pe...@google.com — Feb 22, 2025 12:37AM**

This release blocking issue appears to be targeted for one or more milestones which may have already branched:

  * M132, which branched on 2024-11-11 (Chromium branch: 6834, Chromium branch position: 1381561)

Because this issue was marked as fixed on or after branch day, a merge of any CLs which landed on or after branch day may be required.

If no merge is needed (e.g. the necessary CLs are already present in the relevant branch), please remove TBD-## from the Merge field and replace it with NA-## (where ## corresponds to the milestone under evaluation). If a merge is necessary, the requested milestone(s) to the Merge-Request field. If you're not sure, reach out to the relevant release manager (can be found at [https://chromiumdash.appspot.com/schedule](<https://chromiumdash.appspot.com/schedule>)).

To learn more about the merge process, including how to land any required merges, see [https://chromium.googlesource.com/chromium/src.git/+/refs/heads/main/docs/process/merge_request.md](<https://chromium.googlesource.com/chromium/src.git/+/refs/heads/main/docs/process/merge_request.md>).


---

**#22 — am...@chromium.org — Feb 22, 2025 04:26AM**

[https://crrev.com/c/6278358](<https://crrev.com/c/6278358>) approved for merge to M134 Beta and M133 Stable; please merge to branches 13.4 and 13.3 at your earliest convenience. M134 Stable RC is being cut Tuesday and final respin of M133 Stable shipping on Tuesday, and there are no further planned releases of M132 Extended.


---

**#23 — pe...@google.com — Feb 23, 2025 12:36AM**

This release blocking issue appears to be targeted for one or more milestones which may have already branched:

  * M132, which branched on 2024-11-11 (Chromium branch: 6834, Chromium branch position: 1381561)

Because this issue was marked as fixed on or after branch day, a merge of any CLs which landed on or after branch day may be required.

If no merge is needed (e.g. the necessary CLs are already present in the relevant branch), please remove TBD-## from the Merge field and replace it with NA-## (where ## corresponds to the milestone under evaluation). If a merge is necessary, the requested milestone(s) to the Merge-Request field. If you're not sure, reach out to the relevant release manager (can be found at [https://chromiumdash.appspot.com/schedule](<https://chromiumdash.appspot.com/schedule>)).

To learn more about the merge process, including how to land any required merges, see [https://chromium.googlesource.com/chromium/src.git/+/refs/heads/main/docs/process/merge_request.md](<https://chromium.googlesource.com/chromium/src.git/+/refs/heads/main/docs/process/merge_request.md>).


---

**#24 — ap...@google.com — Feb 24, 2025 05:23PM**

Project: v8/v8  
Branch: refs/branch-heads/13.3  
Author: Darius Mercadier <[dmercadier@chromium.org](<mailto:dmercadier@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6297384](<https://chromium-review.googlesource.com/6297384>)

Merged: [turbofan] Disable escape analysis for TrustedHeapConstant

* * *

Expand for full commit details

```
Merged: [turbofan] Disable escape analysis for TrustedHeapConstant 
 
More precisely: prevent eliding objects that contain 
TrustedHeapConstant, because it can lead to this constant flowing into 
a Phis where other inputs are regular HeapConstant, which confuses 
decompression optimization and leads to memory corruption. 
 
Bug: chromium:390743124 
(cherry picked from commit b75e527fb521dca5e7621928846c0c7c6becc8dd) 
 
Change-Id: I2546cf6480fe18602b4bbedd354bf8580403cd6b 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6297384 
Reviewed-by: Patrick Thier <pthier@chromium.org> 
Auto-Submit: Darius Mercadier <dmercadier@chromium.org> 
Commit-Queue: Patrick Thier <pthier@chromium.org> 
Cr-Commit-Position: refs/branch-heads/13.3@{#44} 
Cr-Branched-From: 41dacffe436aeb9311879cb07648f1e36609a804-refs/heads/13.3.415@{#1} 
Cr-Branched-From: 3348638c0af67c885b30891a358c89a917ac9759-refs/heads/main@{#97937}
```

* * *

Files:

  * M `src/compiler/escape-analysis.cc`

* * *

Hash: 47d46ecc2a5efb263a9ade1b8e5bbbbace5fa818  
Date: Tue Feb 18 09:32:04 2025

* * *


---

**#25 — ap...@google.com — Feb 24, 2025 05:25PM**

Project: v8/v8  
Branch: refs/branch-heads/13.4  
Author: Darius Mercadier <[dmercadier@chromium.org](<mailto:dmercadier@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6297463](<https://chromium-review.googlesource.com/6297463>)

Merged: [turbofan] Disable escape analysis for TrustedHeapConstant

* * *

Expand for full commit details

```
Merged: [turbofan] Disable escape analysis for TrustedHeapConstant 
 
More precisely: prevent eliding objects that contain 
TrustedHeapConstant, because it can lead to this constant flowing into 
a Phis where other inputs are regular HeapConstant, which confuses 
decompression optimization and leads to memory corruption. 
 
Bug: chromium:390743124 
(cherry picked from commit b75e527fb521dca5e7621928846c0c7c6becc8dd) 
 
Change-Id: Ied1bfa7f57e5d22ea30f58a6c5fe63d2d17dd1b1 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6297463 
Reviewed-by: Patrick Thier <pthier@chromium.org> 
Auto-Submit: Darius Mercadier <dmercadier@chromium.org> 
Commit-Queue: Patrick Thier <pthier@chromium.org> 
Cr-Commit-Position: refs/branch-heads/13.4@{#25} 
Cr-Branched-From: 0f87a54dade4353b6ece1d7591ca8c66f90c1c93-refs/heads/13.4.114@{#1} 
Cr-Branched-From: 27af2e9363b2701abc5f3feb701b1dad7d1a9fe8-refs/heads/main@{#98459}
```

* * *

Files:

  * M `src/compiler/escape-analysis.cc`

* * *

Hash: 95520eaf46efe69d64a41541a9f8c3a09d4d0ac5  
Date: Tue Feb 18 09:32:04 2025

* * *


---

**#26 — pe...@google.com — Feb 24, 2025 05:28PM**

LTS Milestone M132

This issue has been flagged as a merge candidate for Chrome OS' LTS channel. If selected, our merge team will handle any additional merges. To help us determine if this issue requires a merge to LTS, please answer this short questionnaire:

  1. Was this issue a regression for the milestone it was found in?
  2. Is this issue related to a change or feature merged after the latest LTS Milestone?


---

**#27 — dm...@chromium.org — Feb 25, 2025 04:37PM**

Replies to [comment #26](<https://issues.chromium.org/issues/390743124#comment26>):

  1. The issue has been around since 129
  2. no

(==> it would make sense to backmerge to LTS M132)


---

**#28 — pe...@google.com — Feb 26, 2025 12:37AM**

This release blocking issue appears to be targeted for one or more milestones which may have already branched:

  * M132, which branched on 2024-11-11 (Chromium branch: 6834, Chromium branch position: 1381561)

Because this issue was marked as fixed on or after branch day, a merge of any CLs which landed on or after branch day may be required.

If no merge is needed (e.g. the necessary CLs are already present in the relevant branch), please remove TBD-## from the Merge field and replace it with NA-## (where ## corresponds to the milestone under evaluation). If a merge is necessary, the requested milestone(s) to the Merge-Request field. If you're not sure, reach out to the relevant release manager (can be found at [https://chromiumdash.appspot.com/schedule](<https://chromiumdash.appspot.com/schedule>)).

To learn more about the merge process, including how to land any required merges, see [https://chromium.googlesource.com/chromium/src.git/+/refs/heads/main/docs/process/merge_request.md](<https://chromium.googlesource.com/chromium/src.git/+/refs/heads/main/docs/process/merge_request.md>).


---

**#29 — sp...@google.com — Feb 27, 2025 09:55AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $7000.00 for this report.  
  
Rationale for this decision:  
report of memory corruption in a sandboxed process / renderer   
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#30 — am...@chromium.org — Feb 27, 2025 10:08AM**

Congratulations Zhenghang and Nan! Thank you for your efforts and reporting this issue to us!


---

**#31 — pe...@google.com — Mar 4, 2025 11:13AM**

This issue requires additional review before it can be merged to the LTS channel. Please answer the following questions to help us evaluate this merge:

  1. Number of CLs needed for this fix and links to them.
  2. Level of complexity (High, Medium, Low - Explain)
  3. Has this been merged to a stable release? beta release?
  4. Overall Recommendation (Yes, No)


---

**#32 — qk...@google.com — Mar 4, 2025 11:38AM**

1\. [https://chromium-review.googlesource.com/c/v8/v8/+/6317725](<https://chromium-review.googlesource.com/c/v8/v8/+/6317725>)  
2\. Low - There was no conflict.  
3\. 133, 134  
4\. Yes. According to [comment #27](<https://issues.chromium.org/issues/390743124#comment27>), this issue has existed since M129.


---

**#33 — ch...@google.com — Mar 7, 2025 12:45AM**

Dear owner, thanks for fixing this bug. We've reopened it because:

  * It is not clear which CLs have ‘fixed’ (=required to consider the bug resolved; e.g. not logging) this bug. Please fill in the “Fixed By Code Changes” field with the appropriate Gerrit url to disambiguate using the following guidelines: 
    * If there are multiple CLs required, please list all.
    * If the fix landed in a third party library (v8, Dawn, etc), please list the third party commits - not the rolls.
    * If there are cherrypicks or back merges, please list the original commits which landed on HEAD.
    * If there is no relevant Gerrit link (i.e. the fix does not live in or roll into Chromium), please use the value ‘NA’.
    * If this is a non-browser ChromeOS-specific bug, please move it to component 1335705 in the Google issue tracker.
    * If this field requires human intervention for some reason, please add this bug to the hotlist id 6265590. After resolving the above issue(s), this bug can be marked closed again. Thanks for your time!


---

**#34 — ap...@google.com — Mar 11, 2025 11:37AM**

Project: v8/v8  
Branch: refs/branch-heads/13.2  
Author: Darius Mercadier <[dmercadier@chromium.org](<mailto:dmercadier@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6317725](<https://chromium-review.googlesource.com/6317725>)

[M132-LTS][turbofan] Disable escape analysis for TrustedHeapConstant

* * *

Expand for full commit details

```
[M132-LTS][turbofan] Disable escape analysis for TrustedHeapConstant 
 
More precisely: prevent eliding objects that contain 
TrustedHeapConstant, because it can lead to this constant flowing into 
a Phis where other inputs are regular HeapConstant, which confuses 
decompression optimization and leads to memory corruption. 
 
(cherry picked from commit b75e527fb521dca5e7621928846c0c7c6becc8dd) 
 
Fixed: chromium:390743124 
Change-Id: Ic60e4d7dd156367f7d4bb385d422591384c3033c 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6278358 
Reviewed-by: Nico Hartmann <nicohartmann@chromium.org> 
Commit-Queue: Nico Hartmann <nicohartmann@chromium.org> 
Auto-Submit: Darius Mercadier <dmercadier@chromium.org> 
Cr-Original-Commit-Position: refs/heads/main@{#98748} 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6317725 
Reviewed-by: Darius Mercadier <dmercadier@chromium.org> 
Commit-Queue: Gyuyoung Kim (xWF) <qkim@google.com> 
Cr-Commit-Position: refs/branch-heads/13.2@{#82} 
Cr-Branched-From: 24068c59cedad9ee976ddc05431f5f497b1ebd71-refs/heads/13.2.152@{#1} 
Cr-Branched-From: 6054ba94db0969220be4f94dc1677fc4696bdc4f-refs/heads/main@{#97085}
```

* * *

Files:

  * M `src/compiler/escape-analysis.cc`

* * *

Hash: 91343bb45c78ac5cf3d214f68161d8150d81fa8c  
Date: Tue Feb 18 09:32:04 2025

* * *


---

**#35 — rz...@google.com — Mar 12, 2025 03:29AM**

Labelling as not applicable for 126 because TrustedHeapConstant was introduced only in 129


---

**#36 — sr...@google.com — Apr 3, 2025 09:15PM**

We discussed this issue in the team and we believe this won't be exploitable, so downgrading this to S2.

The SIGSEGV only happens in a slow debug check. In a release build, the code will end with a potentially controlled pointer [here](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/deoptimizer/translated-state.cc;l=2575;drc=a13ed9dc2f85d1cc3e9a9f69abe704ed795807b0>).  
If one manages to control the data it will be possible to pass the CHECK. But then, it only reads the SelfIndirectPointer (an EPT handle) from there and copies it to the materialized object.  
This should only lead to correctness issues since the RegExpData is self-contained and doesn't rely on the relation to other objects.


---

**#37 — ch...@google.com — Jun 13, 2025 09:38PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
