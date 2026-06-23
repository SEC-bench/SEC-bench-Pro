# Type Confusion between WasmObject and JSObject in V8 MaglevGraphBuilder::TryBuildFastOrdinaryHasInstance

Issue URL: https://issues.chromium.org/issues/355256380
VRP-Reward: 7000
Date: Jul 25, 2024 11:50AM


VULNERABILITY DETAILS

## INTRODUCE

Without a doubt, the true introduction of this vulnerability, like most previous confusions between wasm and js objects, can be traced back to the point where wasm arrays and wasm structs were introduced.

## CRASH LOG

  * Debug output

```
#
# Fatal error in ../../src/compiler/heap-refs.cc, line 1127
# Debug check failed: IsJSObject().
#
#
#
#FailureMessage Object: 0x7f6ebeffb250
==== C stack trace ===============================

    d8-linux-debug-v8-component-95248/libv8_libbase.so(v8::base::debug::StackTrace::StackTrace()+0x13) [0x7f6ef59f4aa3]
    d8-linux-debug-v8-component-95248/libv8_libplatform.so(+0x19add) [0x7f6efb1ddadd]
    d8-linux-debug-v8-component-95248/libv8_libbase.so(V8_Fatal(char const*, int, char const*, ...)+0x194) [0x7f6ef59d6234]
    d8-linux-debug-v8-component-95248/libv8_libbase.so(+0x2bc55) [0x7f6ef59d5c55]
    d8-linux-debug-v8-component-95248/libv8.so(v8::internal::compiler::ObjectRef::AsJSObject() const+0x65) [0x7f6efa1bf575]
    d8-linux-debug-v8-component-95248/libv8.so(v8::internal::maglev::MaglevGraphBuilder::InferHasInPrototypeChain(v8::internal::maglev::ValueNode*, v8::internal::compiler::HeapObjectRef)+0x13a) [0x7f6ef963038a]
    d8-linux-debug-v8-component-95248/libv8.so(v8::internal::maglev::MaglevGraphBuilder::BuildHasInPrototypeChain(v8::internal::maglev::ValueNode*, v8::internal::compiler::HeapObjectRef)+0x1c) [0x7f6ef963071c]
    d8-linux-debug-v8-component-95248/libv8.so(v8::internal::maglev::MaglevGraphBuilder::TryBuildFastOrdinaryHasInstance(v8::internal::maglev::ValueNode*, v8::internal::compiler::JSObjectRef, v8::internal::maglev::ValueNode*)+0x278) [0x7f6ef9630aa8]
    d8-linux-debug-v8-component-95248/libv8.so(v8::internal::maglev::MaglevGraphBuilder::BuildOrdinaryHasInstance(v8::internal::maglev::ValueNode*, v8::internal::compiler::JSObjectRef, v8::internal::maglev::ValueNode*)+0x22) [0x7f6ef961d892]
    d8-linux-debug-v8-component-95248/libv8.so(v8::internal::maglev::MaglevGraphBuilder::TryBuildFastInstanceOf(v8::internal::maglev::ValueNode*, v8::internal::compiler::JSObjectRef, v8::internal::maglev::ValueNode*)+0x438) [0x7f6ef9630f48]
    d8-linux-debug-v8-component-95248/libv8.so(v8::internal::maglev::MaglevGraphBuilder::TryBuildFastInstanceOfWithFeedback(v8::internal::maglev::ValueNode*, v8::internal::maglev::ValueNode*, v8::internal::compiler::FeedbackSource)+0x163) [0x7f6ef9631943]
    d8-linux-debug-v8-component-95248/libv8.so(v8::internal::maglev::MaglevGraphBuilder::VisitTestInstanceOf()+0xa0) [0x7f6ef9631a00]
    d8-linux-debug-v8-component-95248/libv8.so(v8::internal::maglev::MaglevGraphBuilder::VisitSingleBytecode()+0xd7a) [0x7f6ef951dcaa]
    d8-linux-debug-v8-component-95248/libv8.so(v8::internal::maglev::MaglevGraphBuilder::BuildBody()+0x12a) [0x7f6ef951907a]
    d8-linux-debug-v8-component-95248/libv8.so(v8::internal::maglev::MaglevGraphBuilder::Build()+0x3bb) [0x7f6ef9515eab]
    d8-linux-debug-v8-component-95248/libv8.so(v8::internal::maglev::MaglevCompiler::Compile(v8::internal::LocalIsolate*, v8::internal::maglev::MaglevCompilationInfo*)+0x6d0) [0x7f6ef9514910]
    d8-linux-debug-v8-component-95248/libv8.so(v8::internal::maglev::MaglevCompilationJob::ExecuteJobImpl(v8::internal::RuntimeCallStats*, v8::internal::LocalIsolate*)+0x66) [0x7f6ef95de6c6]
    d8-linux-debug-v8-component-95248/libv8.so(v8::internal::OptimizedCompilationJob::ExecuteJob(v8::internal::RuntimeCallStats*, v8::internal::LocalIsolate*)+0x8d) [0x7f6ef83b5f1d]
    d8-linux-debug-v8-component-95248/libv8.so(v8::internal::maglev::MaglevConcurrentDispatcher::JobTask::Run(v8::JobDelegate*)+0x39b) [0x7f6ef95e041b]
    d8-linux-debug-v8-component-95248/libv8_libplatform.so(v8::platform::DefaultJobWorker::Run()+0xd3) [0x7f6efb1dc883]
    d8-linux-debug-v8-component-95248/libv8_libplatform.so(v8::platform::DefaultWorkerThreadsTaskRunner::WorkerThread::Run()+0xcc) [0x7f6efb1decbc]
    d8-linux-debug-v8-component-95248/libv8_libbase.so(+0x497f8) [0x7f6ef59f37f8]
    /lib/x86_64-linux-gnu/libc.so.6(+0x94ac3) [0x7f6ef5294ac3]
    /lib/x86_64-linux-gnu/libc.so.6(+0x126850) [0x7f6ef5326850]
[6]    1307572 trace trap  d8-linux-debug-v8-component-95248/d8 poc.js
```

VERSION Tested on v8 version: 11.9.0 - 12.0.0

REPRODUCTION CASE

  1. Download debug v8 from: gs://v8-asan/linux-debug/d8-linux-debug-v8-component-95248.zip
  2. Run: `d8 poc.js`

FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION Type of crash: tab

CREDIT INFORMATION Reporter credit: Zhenghang Xiao (@Kipreyyy)


---

**#2 — ki...@gmail.com — Jul 25, 2024 11:50AM**

Hi [mliedtke@chromium.org](<mailto:mliedtke@chromium.org>), This vulnerability has a similar root cause to a previous one I discovered([https://issues.chromium.org/u/1/issues/338908243](<https://issues.chromium.org/u/1/issues/338908243>)). Since you resolved the previous issue, could you please take a look at this one as well?

Additionally, [leszeks@chromium.org](<mailto:leszeks@chromium.org>), the maglev code([https://source.chromium.org/chromium/chromium/src/+/main:v8/src/maglev/maglev-graph-builder.cc;l=9970;drc=2017cd8a8925f180257662f78eaf9eb93e8e394d](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/maglev/maglev-graph-builder.cc;l=9970;drc=2017cd8a8925f180257662f78eaf9eb93e8e394d>)) where the vulnerability is triggered was developed by you. Could you also review it? Thank you.


---

**#3 — ki...@gmail.com — Jul 25, 2024 11:53AM**

Please note that I do not believe this vulnerability needs to be bisected using clusterfuzz, as it will only bisect to the point where wasm gc was shipped to stable or where the wasm-gc flag was introduced. This is unnecessary. Please CC the appropriate developer based on my [comment #2](<https://issues.chromium.org/issues/355256380#comment2>). Thank you.


---

**#4 — ma...@chromium.org — Jul 25, 2024 01:08PM**

[security shepherd]

Thank you for your report, and the note about ClusterFuzz bisecting this to where Wasm GC was enabled.

Provisionally setting the severity to S1 and Found In to LTS. I've CCd the two folks you mentioned on this issue, but will assign it to the V8 sheriff in case there's any process they need to follow.


---

**#5 — le...@chromium.org — Jul 25, 2024 04:20PM**

Victor, PTAL, should be an easy enough fix.


---

**#6 — le...@chromium.org — Jul 25, 2024 04:20PM**

Let's also audit for any other similar cases...


---

**#7 — ap...@google.com — Jul 25, 2024 08:48PM**

Project: v8/v8  
Branch: main  
  
commit 313905c4f2c153be4bf4b09b2b06ffad7106869c  
Author: Victor Gomes <[victorgomes@chromium.org](<mailto:victorgomes@chromium.org>)>  
Date: Thu Jul 25 11:36:01 2024  
  
[maglev] Consider WasmStruct in InferHasInPrototypeChain  
  
Fixed: 355256380  
Change-Id: I0d82c1a723685cf4c1a093ed9e8eb8190502fce8  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5741275](<https://chromium-review.googlesource.com/c/v8/v8/+/5741275>)  
Commit-Queue: Leszek Swirski <[leszeks@chromium.org](<mailto:leszeks@chromium.org>)>  
Auto-Submit: Victor Gomes <[victorgomes@chromium.org](<mailto:victorgomes@chromium.org>)>  
Reviewed-by: Leszek Swirski <[leszeks@chromium.org](<mailto:leszeks@chromium.org>)>  
Cr-Commit-Position: refs/heads/main@{#95271}  
  
M src/maglev/maglev-graph-builder.cc  
A test/mjsunit/maglev/regress-355256380.js  
M test/mjsunit/mjsunit.status  
  
[https://chromium-review.googlesource.com/5741275](<https://chromium-review.googlesource.com/5741275>)


---

**#8 — pe...@google.com — Jul 26, 2024 12:39AM**

Setting milestone because of s0/s1 severity.


---

**#9 — pe...@google.com — Jul 26, 2024 12:39AM**

Setting Priority to P1 to match Severity s1. If this is incorrect, please reset the priority. The automation bot account won't make this change again.


---

**#10 — pe...@google.com — Jul 26, 2024 12:44AM**

This is sufficiently serious that it should be merged to extended stable. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M126. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately. This is sufficiently serious that it should be merged to stable. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M127. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately. This is sufficiently serious that it should be merged to beta. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M128. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately. Thank you for fixing this security bug! We aim to ship security fixes as quickly as possible, to limit their opportunity for exploitation as an "n-day" (that is, a bug where git fixes are developed into attacks before those fixes reach users).

We have determined this fix is necessary on milestone(s): [].

Please answer the following questions so that we can safely process this merge request:

  1. Which CLs should be backmerged? (Please include Gerrit links.)
  2. Has this fix been verified on Canary to not pose any stability regressions?
  3. Does this fix pose any potential non-verifiable stability risks?
  4. Does this fix pose any known compatibility risks?
  5. Does it require manual verification by the test team? If so, please describe required testing.


---

**#11 — am...@chromium.org — Jul 30, 2024 06:56AM**

merge approved for [https://crrev.com/c/5741275](<https://crrev.com/c/5741275>) \-- please merge 12.8, 12.7, and 12.6 at your earliest convenience. Please merge to 12.8 by tomorrow, Tuesday, 30 July so this fix can be included in the next update of M128 beta -- thank you


---

**#12 — ap...@google.com — Jul 30, 2024 05:48PM**

Project: v8/v8  
Branch: refs/branch-heads/12.8  
  
commit 5746c053fcad10397ac4d2170e760c1a973056e2  
Author: Victor Gomes <[victorgomes@chromium.org](<mailto:victorgomes@chromium.org>)>  
Date: Thu Jul 25 11:36:01 2024  
  
Merged: [maglev] Consider WasmStruct in InferHasInPrototypeChain  
  
Fixed: 355256380  
  
(cherry picked from commit 313905c4f2c153be4bf4b09b2b06ffad7106869c)  
  
Change-Id: Ifb7589c000b4b01cc6a00a91083a4aa54ed55f89  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5746763](<https://chromium-review.googlesource.com/c/v8/v8/+/5746763>)  
Commit-Queue: Leszek Swirski <[leszeks@chromium.org](<mailto:leszeks@chromium.org>)>  
Auto-Submit: Victor Gomes <[victorgomes@chromium.org](<mailto:victorgomes@chromium.org>)>  
Commit-Queue: Victor Gomes <[victorgomes@chromium.org](<mailto:victorgomes@chromium.org>)>  
Reviewed-by: Leszek Swirski <[leszeks@chromium.org](<mailto:leszeks@chromium.org>)>  
Cr-Commit-Position: refs/branch-heads/12.8@{#6}  
Cr-Branched-From: 70cbb397b153166027e34c75adf8e7993858222e-refs/heads/12.8.374@{#1}  
Cr-Branched-From: 451b63ed4251c2b21c56144d8428f8be3331539b-refs/heads/main@{#95151}  
  
M src/maglev/maglev-graph-builder.cc  
A test/mjsunit/maglev/regress-355256380.js  
M test/mjsunit/mjsunit.status  
  
[https://chromium-review.googlesource.com/5746763](<https://chromium-review.googlesource.com/5746763>)


---

**#13 — ap...@google.com — Jul 30, 2024 05:57PM**

Project: v8/v8  
Branch: refs/branch-heads/12.7  
  
commit 9338284ec75623edf02c437aec339c1638345816  
Author: Victor Gomes <[victorgomes@chromium.org](<mailto:victorgomes@chromium.org>)>  
Date: Thu Jul 25 11:36:01 2024  
  
Merged: [maglev] Consider WasmStruct in InferHasInPrototypeChain  
  
Fixed: 355256380  
  
(cherry picked from commit 313905c4f2c153be4bf4b09b2b06ffad7106869c)  
  
Change-Id: I36a04ba945da014d13fe21568352bc6c74c21e68  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5743765](<https://chromium-review.googlesource.com/c/v8/v8/+/5743765>)  
Auto-Submit: Victor Gomes <[victorgomes@chromium.org](<mailto:victorgomes@chromium.org>)>  
Reviewed-by: Leszek Swirski <[leszeks@chromium.org](<mailto:leszeks@chromium.org>)>  
Commit-Queue: Leszek Swirski <[leszeks@chromium.org](<mailto:leszeks@chromium.org>)>  
Commit-Queue: Victor Gomes <[victorgomes@chromium.org](<mailto:victorgomes@chromium.org>)>  
Cr-Commit-Position: refs/branch-heads/12.7@{#32}  
Cr-Branched-From: 35cc908918d3f8083955ed8328506f964e17ae40-refs/heads/12.7.224@{#1}  
Cr-Branched-From: 6d60e6734b32211215c8410db6fe2b84b13abe0e-refs/heads/main@{#94324}  
  
M src/maglev/maglev-graph-builder.cc  
A test/mjsunit/maglev/regress-355256380.js  
M test/mjsunit/mjsunit.status  
  
[https://chromium-review.googlesource.com/5743765](<https://chromium-review.googlesource.com/5743765>)


---

**#14 — ap...@google.com — Jul 31, 2024 05:23PM**

Project: v8/v8  
Branch: refs/branch-heads/12.6  
  
commit 066d8467a280c5c3beaa1eeb8599941ffedb92d2  
Author: Victor Gomes <[victorgomes@chromium.org](<mailto:victorgomes@chromium.org>)>  
Date: Thu Jul 25 11:36:01 2024  
  
Merged: [maglev] Consider WasmStruct in InferHasInPrototypeChain  
  
Fixed: 355256380  
  
(cherry picked from commit 313905c4f2c153be4bf4b09b2b06ffad7106869c)  
  
Change-Id: I5b1ff15b146ac1054dee5f62b59af8337fca5287  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5743766](<https://chromium-review.googlesource.com/c/v8/v8/+/5743766>)  
Auto-Submit: Victor Gomes <[victorgomes@chromium.org](<mailto:victorgomes@chromium.org>)>  
Reviewed-by: Leszek Swirski <[leszeks@chromium.org](<mailto:leszeks@chromium.org>)>  
Commit-Queue: Leszek Swirski <[leszeks@chromium.org](<mailto:leszeks@chromium.org>)>  
Cr-Commit-Position: refs/branch-heads/12.6@{#54}  
Cr-Branched-From: 3c9fa12db3183a6f4ea53d2675adb66ea1194529-refs/heads/12.6.228@{#2}  
Cr-Branched-From: 981bb15ba4dbf9e2381dfc94ec2c4af0b9c6a0b6-refs/heads/main@{#93835}  
  
M src/maglev/maglev-graph-builder.cc  
A test/mjsunit/maglev/regress-355256380.js  
M test/mjsunit/mjsunit.status  
  
[https://chromium-review.googlesource.com/5743766](<https://chromium-review.googlesource.com/5743766>)


---

**#15 — sp...@google.com — Aug 1, 2024 07:55AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $7000.00 for this report.  
  
Rationale for this decision:  
$7,000 for report of memory corruption in a sandboxed process / renderer   
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#16 — am...@chromium.org — Aug 1, 2024 08:28AM**

Congratulations on another one Zhenghang! Thanks you for your efforts and reporting this issue to us.


---

**#17 — pe...@google.com — Nov 2, 2024 12:48AM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
