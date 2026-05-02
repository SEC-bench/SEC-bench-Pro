# JIT type confusion via corrupted inlining metadata

Issue URL: https://issues.chromium.org/issues/430572435
VRP-Reward: 7000
Date: Jul 10, 2025 04:10AM


```
#
# Fatal error in ../../src/base/bit-field.h, line 56
# Debug check failed: is_valid(value).
#
#
#
#FailureMessage Object: 0x7bc04a228c60
==== C stack trace ===============================

    ./out/test/d8(__interceptor_backtrace+0x46) [0x564f0c1e4c96]
    /home/user/v8-bisect/v8/out/test/libv8_libbase.so(v8::base::debug::StackTrace::StackTrace()+0x13) [0x7fc077c80a23]
    /home/user/v8-bisect/v8/out/test/libv8_libplatform.so(+0x36a8a) [0x7fc077bd5a8a]
    /home/user/v8-bisect/v8/out/test/libv8_libbase.so(V8_Fatal(char const*, int, char const*, ...)+0x2a0) [0x7fc077c4b8e0]
    /home/user/v8-bisect/v8/out/test/libv8_libbase.so(+0x5699f) [0x7fc077c4a99f]
    /home/user/v8-bisect/v8/out/test/libv8.so(v8::internal::SourcePosition::SetInliningId(int)+0x140) [0x7fc07c9bc9f0]
    /home/user/v8-bisect/v8/out/test/libv8.so(v8::internal::maglev::MaglevGraphBuilder::MaglevGraphBuilder(v8::internal::LocalIsolate*, v8::internal::maglev::MaglevCompilationUnit*, v8::internal::maglev::Graph*, float, v8::internal::BytecodeOffset, bool, int, v8::internal::maglev::MaglevGraphBuilder*)+0x7b8) [0x7fc07f0758f8]
    /home/user/v8-bisect/v8/out/test/libv8.so(v8::internal::maglev::MaglevGraphBuilder::TryBuildInlinedCall(v8::internal::maglev::ValueNode*, v8::internal::maglev::ValueNode*, v8::internal::maglev::ValueNode*, v8::internal::compiler::SharedFunctionInfoRef, v8::internal::compiler::OptionalRef<v8::internal::compiler::FeedbackVectorRef>, v8::internal::maglev::CallArguments&, v8::internal::compiler::FeedbackSource const&)+0xd9b) [0x7fc07f0f2e9b]
    /home/user/v8-bisect/v8/out/test/libv8.so(v8::internal::maglev::MaglevGraphBuilder::TryBuildCallKnownJSFunction(v8::internal::maglev::ValueNode*, v8::internal::maglev::ValueNode*, v8::internal::maglev::ValueNode*, v8::internal::compiler::SharedFunctionInfoRef, v8::internal::compiler::OptionalRef<v8::internal::compiler::FeedbackVectorRef>, v8::internal::maglev::CallArguments&, v8::internal::compiler::FeedbackSource const&)+0x137) [0x7fc07f11c1d7]
    /home/user/v8-bisect/v8/out/test/libv8.so(v8::internal::maglev::MaglevGraphBuilder::TryBuildCallKnownJSFunction(v8::internal::compiler::JSFunctionRef, v8::internal::maglev::ValueNode*, v8::internal::maglev::CallArguments&, v8::internal::compiler::FeedbackSource const&)+0x2ea) [0x7fc07f11be7a]
    /home/user/v8-bisect/v8/out/test/libv8.so(v8::internal::maglev::MaglevGraphBuilder::ReduceCallForConstant(v8::internal::compiler::JSFunctionRef, v8::internal::maglev::CallArguments&, v8::internal::compiler::FeedbackSource const&)+0x3d2) [0x7fc07f0b66c2]
    /home/user/v8-bisect/v8/out/test/libv8.so(v8::internal::maglev::MaglevGraphBuilder::ReduceCall(v8::internal::maglev::ValueNode*, v8::internal::maglev::CallArguments&, v8::internal::compiler::FeedbackSource const&)+0x305) [0x7fc07f0f9625]
    /home/user/v8-bisect/v8/out/test/libv8.so(v8::internal::maglev::MaglevGraphBuilder::BuildCallWithFeedback(v8::internal::maglev::ValueNode*, v8::internal::maglev::CallArguments&, v8::internal::compiler::FeedbackSource const&)+0x395) [0x7fc07f11f965]
    /home/user/v8-bisect/v8/out/test/libv8.so(v8::internal::maglev::MaglevGraphBuilder::BuildCallFromRegisters(int, v8::internal::ConvertReceiverMode)+0x28f) [0x7fc07f12317f]
    /home/user/v8-bisect/v8/out/test/libv8.so(v8::internal::maglev::MaglevGraphBuilder::VisitSingleBytecode()+0x19df) [0x7fc07ef3db9f]
    /home/user/v8-bisect/v8/out/test/libv8.so(v8::internal::maglev::MaglevGraphBuilder::BuildBody()+0x52b) [0x7fc07ef3584b]
    /home/user/v8-bisect/v8/out/test/libv8.so(v8::internal::maglev::MaglevGraphBuilder::Build()+0x7df) [0x7fc07ef29aef]
    /home/user/v8-bisect/v8/out/test/libv8.so(v8::internal::maglev::MaglevCompiler::Compile(v8::internal::LocalIsolate*, v8::internal::maglev::MaglevCompilationInfo*)+0x15ca) [0x7fc07ef2629a]
    /home/user/v8-bisect/v8/out/test/libv8.so(v8::internal::maglev::MaglevCompilationJob::ExecuteJobImpl(v8::internal::RuntimeCallStats*, v8::internal::LocalIsolate*)+0x10b) [0x7fc07f0688db]
    /home/user/v8-bisect/v8/out/test/libv8.so(v8::internal::OptimizedCompilationJob::ExecuteJob(v8::internal::RuntimeCallStats*, v8::internal::LocalIsolate*)+0x1a4) [0x7fc07c6b2414]
    /home/user/v8-bisect/v8/out/test/libv8.so(v8::internal::maglev::MaglevConcurrentDispatcher::JobTask::Run(v8::JobDelegate*)+0x85b) [0x7fc07f06d76b]
    /home/user/v8-bisect/v8/out/test/libv8_libplatform.so(v8::platform::DefaultJobWorker::Run()+0x2b9) [0x7fc077bd28a9]
    /home/user/v8-bisect/v8/out/test/libv8_libplatform.so(v8::platform::DefaultWorkerThreadsTaskRunner::WorkerThread::Run()+0x1e8) [0x7fc077bd97e8]
    /home/user/v8-bisect/v8/out/test/libv8_libbase.so(+0x8a33e) [0x7fc077c7e33e]
    ./out/test/d8(+0x163de7) [0x564f0c23ade7]
    /lib/x86_64-linux-gnu/libc.so.6(+0x9caa4) [0x7fc0762c3aa4]
    /lib/x86_64-linux-gnu/libc.so.6(+0x129c3c) [0x7fc076350c3c]
Trace/breakpoint trap
```

#### VERSION

V8 version 13.9.0 (candidate)

#### REPRODUCTION CASE

Build: `python3 tools/dev/gm.py x64.debug`

Run: `./d8 poc.js`

* * *

Reporter credit: Shaheen Fazim


---

**#2 — fa...@gmail.com — Jul 10, 2025 04:11AM**

#### BISECT

```
commit 738d3e3a50437883006dee3d263115fb14b03237

    [maglev] Ensure we only record deopt reasons with reasonable positions

    When we're collecting source positions we still didn't have a source
    position for the function entry point, since we didn't set up the
    current_source_position_ yet.

    When we're not collecting source positions we do still record deopt
    info for OSR in maglev. To allow us to DCHECK that we never record
    deopt info without valid source positions we simply initialize the
    current_source_position_ as the function's StartPosition().

    Change-Id: Iabfb8a4b6e83af2e9c30540c66238f470fb4147c
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6022961
```


---

**#3 — cl...@appspot.gserviceaccount.com — Jul 10, 2025 05:05AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=4958660904026112](<https://clusterfuzz.com/testcase?key=4958660904026112>).


---

**#4 — el...@chromium.org — Jul 10, 2025 05:06AM**

Security shepherd: thanks for the report! Fed this to clusterfuzz ([https://clusterfuzz.com/testcase-detail/4958660904026112](<https://clusterfuzz.com/testcase-detail/4958660904026112>)) and sending to v8 shepherd, with provisional Sev-1 and FoundIn-137.


---

**#5 — cl...@appspot.gserviceaccount.com — Jul 10, 2025 05:33PM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5504862867357696](<https://clusterfuzz.com/testcase?key=5504862867357696>).


---

**#6 — cl...@chromium.org — Jul 10, 2025 05:33PM**

I can reproduce locally. Re-uploading to another job on Clusterfuzz.


---

**#7 — cl...@chromium.org — Jul 10, 2025 05:35PM**

Tentatively setting component to Maglev.


---

**#8 — 24...@project.gserviceaccount.com — Jul 10, 2025 05:44PM**

Detailed Report: [https://clusterfuzz.com/testcase?key=5504862867357696](<https://clusterfuzz.com/testcase?key=5504862867357696>)  
  
Fuzzer: None  
Job Type: linux_d8_dbg  
Platform Id: linux  
  
Crash Type: DCHECK failure  
Crash Address:   
Crash State:  
is_valid(value) in bit-field.h  
  
Sanitizer: address (ASAN)  
  
Crash Revision: [https://clusterfuzz.com/revisions?job=linux_d8_dbg&revision=101340](<https://clusterfuzz.com/revisions?job=linux_d8_dbg&revision=101340>)  
  
Reproducer Testcase: [https://clusterfuzz.com/download?testcase_id=5504862867357696](<https://clusterfuzz.com/download?testcase_id=5504862867357696>)  
  
To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.   
  
If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.  
  
If you have any feedback on reproducing test cases, let us know at [https://forms.gle/Yh3qCYFveHj6E5jz5](<https://forms.gle/Yh3qCYFveHj6E5jz5>) so we can improve.  
  
  
************************* UNREPRODUCIBLE *************************  
Note: This crash might not be reproducible with the provided testcase. That said, for the past 14 days, we've been seeing this crash frequently.  
  
It may be possible to reproduce by trying the following options:  
\- Run testcase multiple times for a longer duration.  
\- Run fuzzing without testcase argument to hit the same crash signature.  
  
If it still does not reproduce, try a speculative fix based on the crash stacktrace and verify if it works by looking at the crash statistics in the report. We will auto-close the bug if the crash is not seen for 14 days.  
******************************************************************


---

**#9 — ch...@google.com — Jul 10, 2025 09:41PM**

Setting milestone because of s0/s1 severity.


---

**#10 — el...@chromium.org — Jul 11, 2025 01:27AM**

Security shepherd: setting OS based on ClusterFuzz report.


---

**#11 — cl...@chromium.org — Jul 11, 2025 09:40PM**

I confirmed the bisection manually.

I don't see a clear relation between the POC and the bisected CL (see commend #2). Toon, can you take a look please?


---

**#12 — cl...@chromium.org — Jul 14, 2025 08:51PM**

Forgot to reassign.


---

**#13 — dx...@google.com — Jul 15, 2025 10:27PM**

Project: v8/v8  
Branch: main  
Author: Toon Verwaest [verwaest@chromium.org](<mailto:verwaest@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6732846](<https://chromium-review.googlesource.com/6732846>)

[maglev] Cap inlining at MaxInliningId

* * *

Expand for full commit details

```
     
    Bug: 430572435 
    Change-Id: I4f20bad6c99e9d3d5a959cb801485dfb117e9884 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6732846 
    Commit-Queue: Toon Verwaest <verwaest@chromium.org> 
    Auto-Submit: Toon Verwaest <verwaest@chromium.org> 
    Reviewed-by: Olivier Flückiger <olivf@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#101423}
```

* * *

Files:

  * M `src/codegen/source-position.h`
  * M `src/maglev/maglev-graph-builder.cc`

* * *

Hash: [f22ca7b61a92d3cd2b856485a55a1519cb11b627](<http://crrev.com/f22ca7b61a92d3cd2b856485a55a1519cb11b627>)  
Date: Mon Jul 14 15:01:40 2025

* * *


---

**#14 — ch...@google.com — Jul 17, 2025 09:37PM**

Security Merge Request Consideration: This is sufficiently serious that it should be merged to stable. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M138. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately. Security Merge Request Consideration: This is sufficiently serious that it should be merged to beta. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M139. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately. Security Merge Request - Manual Review: Merge review required: no relevant commits could be automatically detected (via Git Watcher comments), sending to merge review for manual evaluation. If you have not already manually listed the relevant commits to be merged via a comment above, please do so ASAP.

Security Merge Request - Manual Review: Merge review required: no relevant commits could be automatically detected (via Git Watcher comments), sending to merge review for manual evaluation. If you have not already manually listed the relevant commits to be merged via a comment above, please do so ASAP.

Security Merge Request: Thank you for fixing this security bug! We aim to ship security fixes as quickly as possible, to limit their opportunity for exploitation as an "n-day" (that is, a bug where git fixes are developed into attacks before those fixes reach users).

We have determined this fix is necessary on milestone(s): [138, 139].

Please answer the following questions so that we can safely process this merge request:

  1. Which CLs should be backmerged? (Please include Gerrit links.)
  2. Has this fix been verified on Canary to not pose any stability regressions?
  3. Does this fix pose any potential non-verifiable stability risks?
  4. Does this fix pose any known compatibility risks?
  5. Does it require manual verification by the test team? If so, please describe required testing.
  6. (no answer required) Please check the OS custom field to ensure all impacted OSes are checked!


---

**#15 — ve...@chromium.org — Jul 17, 2025 09:46PM**

> Which CLs should be backmerged? (Please include Gerrit links.)

[https://chromium-review.googlesource.com/6732846](<https://chromium-review.googlesource.com/6732846>)

> Has this fix been verified on Canary to not pose any stability regressions?

Yes

> Does this fix pose any potential non-verifiable stability risks?

No

> Does this fix pose any known compatibility risks?

No

> Does it require manual verification by the test team? If so, please describe required testing.

No


---

**#16 — am...@chromium.org — Jul 18, 2025 07:30AM**

Not seeing any issues related to this fix at this time, please [https://crrev.com/c/6732846](<https://crrev.com/c/6732846>) to 13.9 and 13.8 by EOD tomorrow / Friday so this fix can be included in the next update of M138 Stable, and M139 Stable RC being cut on Tuesday


---

**#17 — ch...@google.com — Jul 21, 2025 09:42PM**

This issue has been approved for a merge. Please merge the fix to any appropriate branches as soon as possible!

Thanks for your time! To disable nags, add Disable-Nags (case sensitive) to the Chromium Labels custom field.


---

**#18 — ch...@google.com — Jul 21, 2025 09:42PM**

This issue has been approved for a merge. Please merge the fix to any appropriate branches as soon as possible!

Thanks for your time! To disable nags, add Disable-Nags (case sensitive) to the Chromium Labels custom field.


---

**#19 — dx...@google.com — Jul 22, 2025 01:53AM**

Project: v8/v8  
Branch: refs/branch-heads/13.9  
Author: Toon Verwaest [verwaest@chromium.org](<mailto:verwaest@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6771727](<https://chromium-review.googlesource.com/6771727>)

Merged: [maglev] Cap inlining at MaxInliningId

* * *

Expand for full commit details

```
     
    Bug: 430572435 
    (cherry picked from commit f22ca7b61a92d3cd2b856485a55a1519cb11b627) 
     
    Change-Id: I8b40910da72d695822250c3d832e931ea49f53d3 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6771727 
    Auto-Submit: Toon Verwaest <verwaest@chromium.org> 
    Reviewed-by: Olivier Flückiger <olivf@chromium.org> 
    Commit-Queue: Olivier Flückiger <olivf@chromium.org> 
    Commit-Queue: Toon Verwaest <verwaest@chromium.org> 
    Cr-Commit-Position: refs/branch-heads/13.9@{#24} 
    Cr-Branched-From: 76ea4091129171336d347c2624f6062bd9708042-refs/heads/13.9.205@{#1} 
    Cr-Branched-From: 28242121f590fe04758efec176658cd57310b297-refs/heads/main@{#100941}
```

* * *

Files:

  * M `src/codegen/source-position.h`
  * M `src/maglev/maglev-graph-builder.cc`

* * *

Hash: [4dec491c3886c1792812592a08548569e2892a51](<http://crrev.com/4dec491c3886c1792812592a08548569e2892a51>)  
Date: Mon Jul 14 15:01:40 2025

* * *


---

**#20 — dx...@google.com — Jul 22, 2025 01:56AM**

Project: v8/v8  
Branch: refs/branch-heads/13.8  
Author: Toon Verwaest [verwaest@chromium.org](<mailto:verwaest@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6771572](<https://chromium-review.googlesource.com/6771572>)

Merged: [maglev] Cap inlining at MaxInliningId

* * *

Expand for full commit details

```
     
    (cherry picked from commit f22ca7b61a92d3cd2b856485a55a1519cb11b627) 
     
    Bug: 430572435 
    Change-Id: I4f20bad6c99e9d3d5a959cb801485dfb117e9884 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6771572 
    Commit-Queue: Toon Verwaest <verwaest@chromium.org> 
    Auto-Submit: Toon Verwaest <verwaest@chromium.org> 
    Bot-Commit: Rubber Stamper <rubber-stamper@appspot.gserviceaccount.com> 
    Reviewed-by: Olivier Flückiger <olivf@chromium.org> 
    Commit-Queue: Rubber Stamper <rubber-stamper@appspot.gserviceaccount.com> 
    Cr-Commit-Position: refs/branch-heads/13.8@{#57} 
    Cr-Branched-From: 61ddd471ece346840bbebbb308dceb4b4ce31b28-refs/heads/13.8.258@{#1} 
    Cr-Branched-From: fdb5de2c741658e94944f2ec1218530e98601c23-refs/heads/main@{#100480}
```

* * *

Files:

  * M `src/codegen/source-position.h`
  * M `src/maglev/maglev-graph-builder.cc`

* * *

Hash: [99209d9542a609940e42da9b81b87059f8a92e25](<http://crrev.com/99209d9542a609940e42da9b81b87059f8a92e25>)  
Date: Mon Jul 14 15:01:40 2025

* * *


---

**#21 — pe...@google.com — Jul 22, 2025 01:59AM**

LTS Milestone M132

This issue has been flagged as a merge candidate for Chrome OS' LTS channel. If selected, our merge team will handle any additional merges. To help us determine if this issue requires a merge to LTS, please answer this short questionnaire:

  1. Was this issue a regression for the milestone it was found in?
  2. Is this issue related to a change or feature merged after the latest LTS Milestone?


---

**#22 — qk...@google.com — Jul 22, 2025 11:43AM**

Labelling as not applicable for LTS 132 because M132 doesn't have the suspected commit[1], and also it doesn't have `CanInlineCall()` method that the fix has to modify.

[1] [https://chromium-review.googlesource.com/c/v8/v8/+/6022961](<https://chromium-review.googlesource.com/c/v8/v8/+/6022961>)


---

**#23 — sp...@google.com — Jul 25, 2025 05:55AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $7000.00 for this report.  
  
Rationale for this decision:  
report of memory corruption in a sandboxed process  
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#24 — fa...@gmail.com — Jul 25, 2025 06:26AM**

Hi, I also added a bisect in the issue. Am I eligible for a bisect reward? Thanks.


---

**#25 — am...@chromium.org — Jul 25, 2025 06:29AM**

The bisect was not correct, therefore, it was not eligible for a bisect reward.


---

**#26 — ch...@google.com — Oct 24, 2025 09:50PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
