# RCE in V8 maglev

Issue URL: https://issues.chromium.org/issues/340221135
VRP-Reward: 7000
Date: May 14, 2024 12:08AM


* * *

### Report description

Google Chrome 0-day exploited ITW

* * *

### Bug location

#### Where do you want to report your vulnerability?

Chrome VRP – Report security issues affecting the Chrome browser. [See program rules](<https://bughunters.google.com/about/rules/5745167867576320/chrome-vulnerability-reward-program-rules>)

* * *

### The problem

#### Please describe the technical details of the vulnerability

Hello team,

We've discovered a Chrome RCE 0-day being exploited in the wild in a limited number of targeted attacks.

In attachment you can find archive with exploit. It's not obfuscated and even has comments left by attackers. Password for archive: infected

Kind regards, Boris

#### Please briefly explain who can exploit the vulnerability, and what they gain when doing so

! This vulnerability is already being exploited ITW for RCE !

* * *

### The cause

#### Choose the type of vulnerability

Remote Code Execution (RCE)

#### Does anyone else know about this vulnerability?

No, this vulnerability is private


---

**#2 — ad...@google.com — May 14, 2024 12:58AM**

Thanks for the report.

Do you need this to be embargoed for any reason, or can it go public 14 weeks after we've fixed it as normal? (And let us know how you'd like to be credited, or if you'd prefer to be anonymous)


---

**#3 — ad...@google.com — May 14, 2024 01:03AM**

Setting S1 for renderer RCE, P0 because it's ITW. I can't immediately figure out what the exploit is doing but it's something to do with ArrayBuffer manipulation, so sending to V8.


---

**#4 — sr...@google.com — May 14, 2024 01:24AM**

out/x64.optdebug/d8 --module ~/itw/340221135/test.js

# 

# Fatal error in ../../src/maglev/maglev-graph-builder.cc, line 4171

# Debug check failed: access_info.IsDataField() || access_info.IsFastDataConstant().

# 

# 

# 

#FailureMessage Object: 0x7fdd2f7fc3e0 ==== C stack trace ===============================

```
/usr/local/google/home/sroettger/v8/v8/out/x64.optdebug/libv8_libbase.so(v8::base::debug::StackTrace::StackTrace()+0x13) [0x7fdd6f405e53]
/usr/local/google/home/sroettger/v8/v8/out/x64.optdebug/libv8_libplatform.so(+0x18e3d) [0x7fdd6f3aee3d]
/usr/local/google/home/sroettger/v8/v8/out/x64.optdebug/libv8_libbase.so(V8_Fatal(char const*, int, char const*, ...)+0x17d) [0x7fdd6f3e704d]
/usr/local/google/home/sroettger/v8/v8/out/x64.optdebug/libv8_libbase.so(+0x2ba95) [0x7fdd6f3e6a95]
/usr/local/google/home/sroettger/v8/v8/out/x64.optdebug/libv8.so(v8::internal::maglev::MaglevGraphBuilder::TryBuildPropertyStore(v8::internal::maglev::ValueNode*, v8::internal::compiler::NameRef, v8::internal::compiler::PropertyAccessInfo const&, v8::internal::compiler::AccessMode)+0x230) [0x7fdd6d88ec10]
/usr/local/google/home/sroettger/v8/v8/out/x64.optdebug/libv8.so(v8::internal::maglev::MaglevGraphBuilder::TryBuildNamedAccess(v8::internal::maglev::ValueNode*, v8::internal::maglev::ValueNode*, v8::internal::compiler::NamedAccessFeedback const&, v8::internal::compiler::FeedbackSource const&, v8::internal::compiler::AccessMode)+0xabc) [0x7fdd6d88f7cc]
/usr/local/google/home/sroettger/v8/v8/out/x64.optdebug/libv8.so(v8::internal::maglev::MaglevGraphBuilder::VisitSetNamedProperty()+0x10a) [0x7fdd6d8970ca]
/usr/local/google/home/sroettger/v8/v8/out/x64.optdebug/libv8.so(v8::internal::maglev::MaglevGraphBuilder::VisitSingleBytecode()+0xb2f) [0x7fdd6d7ba7cf]
/usr/local/google/home/sroettger/v8/v8/out/x64.optdebug/libv8.so(v8::internal::maglev::MaglevGraphBuilder::BuildBody()+0x12b) [0x7fdd6d7b5cfb]
/usr/local/google/home/sroettger/v8/v8/out/x64.optdebug/libv8.so(v8::internal::maglev::MaglevGraphBuilder::Build()+0x3fb) [0x7fdd6d7b2a8b]
/usr/local/google/home/sroettger/v8/v8/out/x64.optdebug/libv8.so(v8::internal::maglev::MaglevCompiler::Compile(v8::internal::LocalIsolate*, v8::internal::maglev::MaglevCompilationInfo*)+0x5ed) [0x7fdd6d7b14fd]
/usr/local/google/home/sroettger/v8/v8/out/x64.optdebug/libv8.so(v8::internal::maglev::MaglevCompilationJob::ExecuteJobImpl(v8::internal::RuntimeCallStats*, v8::internal::LocalIsolate*)+0x6a) [0x7fdd6d876bda]
/usr/local/google/home/sroettger/v8/v8/out/x64.optdebug/libv8.so(v8::internal::OptimizedCompilationJob::ExecuteJob(v8::internal::RuntimeCallStats*, v8::internal::LocalIsolate*)+0x8d) [0x7fdd6c93ae1d]
/usr/local/google/home/sroettger/v8/v8/out/x64.optdebug/libv8.so(v8::internal::maglev::MaglevConcurrentDispatcher::JobTask::Run(v8::JobDelegate*)+0x3f6) [0x7fdd6d878a26]
/usr/local/google/home/sroettger/v8/v8/out/x64.optdebug/libv8_libplatform.so(v8::platform::DefaultJobWorker::Run()+0xd3) [0x7fdd6f3adbe3]
/usr/local/google/home/sroettger/v8/v8/out/x64.optdebug/libv8_libplatform.so(v8::platform::DefaultWorkerThreadsTaskRunner::WorkerThread::Run()+0xcc) [0x7fdd6f3b001c]
/usr/local/google/home/sroettger/v8/v8/out/x64.optdebug/libv8_libbase.so(+0x49b98) [0x7fdd6f404b98]
/lib/x86_64-linux-gnu/libc.so.6(+0x8845c) [0x7fdd69ac445c]
/lib/x86_64-linux-gnu/libc.so.6(+0x108bbc) [0x7fdd69b44bbc]
```


---

**#5 — am...@chromium.org — May 14, 2024 01:25AM**

cc'ed folks from TAG exploits team who are working with Kaspersky on this finding


---

**#6 — oc...@gmail.com — May 14, 2024 01:26AM**

We don't want b2dc7aec2c6d2ffa28219ac288e4750c_exploit.rar and it's contents to be shared publicly because it is a fully weaponized exploit that could be used by other threat actors once it becomes public.  
  
But we would like to be credited for this discovery.   
Please acknowledge us similar to this: <a href="[https://twitter.com/vaber_b](<https://twitter.com/vaber_b>)">Vasily Berdnikov</a> and <a href="[https://twitter.com/oct0xor](<https://twitter.com/oct0xor>)">Boris Larin</a> with <a href="[https://kaspersky.com/](<https://kaspersky.com/>)">Kaspersky</a>


---

**#7 — sr...@google.com — May 14, 2024 01:27AM**

adding the SecurityEmbargo hotlist


---

**#8 — sy...@google.com — May 14, 2024 04:00AM**

Fix at [https://chromium-review.googlesource.com/c/v8/v8/+/5534518](<https://chromium-review.googlesource.com/c/v8/v8/+/5534518>)  
  
Confirmed locally that it fixes both Stephen's reduced test case in [comment #4](<https://issues.chromium.org/issues/340221135#comment4>) and causes the original poc to infinite loop instead of crash.


---

**#9 — ap...@google.com — May 14, 2024 04:05AM**

Project: v8/v8  
Branch: main  
  
commit b3c01ac1e60afc9addad9942f7a9a6c5e8a4a6da  
Author: Shu-yu Guo <[syg@chromium.org](<mailto:syg@chromium.org>)>  
Date: Mon May 13 11:23:20 2024  
  
[compiler] Don't build AccessInfo for storing to module exports  
  
Bug: 340221135  
Change-Id: I5af35be6ebf6a69db1c4687107503575b23973c4  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5534518](<https://chromium-review.googlesource.com/c/v8/v8/+/5534518>)  
Reviewed-by: Adam Klein <[adamk@chromium.org](<mailto:adamk@chromium.org>)>  
Commit-Queue: Shu-yu Guo <[syg@chromium.org](<mailto:syg@chromium.org>)>  
Cr-Commit-Position: refs/heads/main@{#93872}  
  
M src/compiler/access-info.cc  
M src/maglev/maglev-graph-builder.cc  
  
[https://chromium-review.googlesource.com/5534518](<https://chromium-review.googlesource.com/5534518>)


---

**#10 — am...@chromium.org — May 14, 2024 04:22AM**

thanks for landing and testing this fix syg@ -- as discussed off-bug, please merge this fix to Canary (branches 6475 [for Android] and 6477) ASAP so this can be part of the next Canary build and we can get data at soonest


---

**#11 — am...@chromium.org — May 14, 2024 04:23AM**

reviewing this fix right now for M125 Stable RC and and M124 Extended Stable backports


---

**#13 — am...@chromium.org — May 14, 2024 04:58AM**

Based on an off-bug conversation with the reporters, I am removing the embargo for this issue so that it can be included in the standard Chromium disclosure processes at the appropriate time. They have requested that the weaponized exploit not be part of the disclosure; therefore, it has been removed from the original report and uploaded as restricted content. A minimized test case is still provided in updates on this report.


---

**#14 — ap...@google.com — May 14, 2024 06:12AM**

Project: v8/v8  
Branch: chromium/6475  
  
commit 164b664ce2b203515c05f28633bf0a10c4c7c32d  
Author: Shu-yu Guo <[syg@chromium.org](<mailto:syg@chromium.org>)>  
Date: Mon May 13 11:23:20 2024  
  
Merged: [compiler] Don't build AccessInfo for storing to module exports  
  
Bug: 340221135  
(cherry picked from commit b3c01ac1e60afc9addad9942f7a9a6c5e8a4a6da)  
  
Change-Id: Idfea5658a0aa180de7ca184eaf5b9d6e2731c55a  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5536090](<https://chromium-review.googlesource.com/c/v8/v8/+/5536090>)  
Reviewed-by: Adam Klein <[adamk@chromium.org](<mailto:adamk@chromium.org>)>  
  
M src/compiler/access-info.cc  
M src/maglev/maglev-graph-builder.cc  
  
[https://chromium-review.googlesource.com/5536090](<https://chromium-review.googlesource.com/5536090>)


---

**#15 — ap...@google.com — May 14, 2024 06:12AM**

Project: v8/v8  
Branch: chromium/6477  
  
commit d21de3c8c3ca2c813ed9562a351cf030716b278e  
Author: Shu-yu Guo <[syg@chromium.org](<mailto:syg@chromium.org>)>  
Date: Mon May 13 11:23:20 2024  
  
Merged: [compiler] Don't build AccessInfo for storing to module exports  
  
Bug: 340221135  
(cherry picked from commit b3c01ac1e60afc9addad9942f7a9a6c5e8a4a6da)  
  
Change-Id: I7a1bddf6b16c44dd3742e4701eb005aff2f04c91  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5536041](<https://chromium-review.googlesource.com/c/v8/v8/+/5536041>)  
Reviewed-by: Adam Klein <[adamk@chromium.org](<mailto:adamk@chromium.org>)>  
  
M src/compiler/access-info.cc  
M src/maglev/maglev-graph-builder.cc  
  
[https://chromium-review.googlesource.com/5536041](<https://chromium-review.googlesource.com/5536041>)


---

**#16 — am...@chromium.org — May 14, 2024 06:19AM**

approving backmerge to M125 (for forthcoming Stable RC) / V8 branch 12.5 and M124 (forthcoming Extended Stable RC) / V8 branch 12.4, please merge at your earliest convenience so this fix can be included in the recut for M125 Stable and the Wednesday's cut of M124 Extended Stable -- thank you!


---

**#17 — ap...@google.com — May 14, 2024 07:03AM**

Project: v8/v8  
Branch: refs/branch-heads/12.4  
  
commit 428311441d40523794280a9b5d3ace23ea811e34  
Author: Shu-yu Guo <[syg@chromium.org](<mailto:syg@chromium.org>)>  
Date: Mon May 13 11:23:20 2024  
  
Merged: [compiler] Don't build AccessInfo for storing to module exports  
  
Bug: 340221135  
(cherry picked from commit b3c01ac1e60afc9addad9942f7a9a6c5e8a4a6da)  
  
Change-Id: I02a33b6c5d4e35ab0ad1aa3e61ad12be4f667712  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5536210](<https://chromium-review.googlesource.com/c/v8/v8/+/5536210>)  
Reviewed-by: Adam Klein <[adamk@chromium.org](<mailto:adamk@chromium.org>)>  
Commit-Queue: Shu-yu Guo <[syg@chromium.org](<mailto:syg@chromium.org>)>  
Cr-Commit-Position: refs/branch-heads/12.4@{#32}  
Cr-Branched-From: 309640da62fae0485c7e4f64829627c92d53b35d-refs/heads/12.4.254@{#1}  
Cr-Branched-From: 5dc24701432278556a9829d27c532f974643e6df-refs/heads/main@{#92862}  
  
M src/compiler/access-info.cc  
M src/maglev/maglev-graph-builder.cc  
  
[https://chromium-review.googlesource.com/5536210](<https://chromium-review.googlesource.com/5536210>)


---

**#18 — ap...@google.com — May 14, 2024 07:07AM**

Project: v8/v8  
Branch: refs/branch-heads/12.5  
  
commit b5e06ac85d575d78520d23e55404aa9ec9cb8d22  
Author: Shu-yu Guo <[syg@chromium.org](<mailto:syg@chromium.org>)>  
Date: Mon May 13 11:23:20 2024  
  
Merged: [compiler] Don't build AccessInfo for storing to module exports  
  
Bug: 340221135  
(cherry picked from commit b3c01ac1e60afc9addad9942f7a9a6c5e8a4a6da)  
  
Change-Id: Icdad4aa5cd0e95f6ae9c4ea84d5b7b7bd70fd039  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5536211](<https://chromium-review.googlesource.com/c/v8/v8/+/5536211>)  
Reviewed-by: Adam Klein <[adamk@chromium.org](<mailto:adamk@chromium.org>)>  
Commit-Queue: Shu-yu Guo <[syg@chromium.org](<mailto:syg@chromium.org>)>  
Cr-Commit-Position: refs/branch-heads/12.5@{#14}  
Cr-Branched-From: 15b9756484d5bda98ba273ae13f8db58200db4db-refs/heads/12.5.227@{#1}  
Cr-Branched-From: 497d8573dc80b1b69052a834bec894cf5d4238e7-refs/heads/main@{#93350}  
  
M src/compiler/access-info.cc  
M src/maglev/maglev-graph-builder.cc  
  
[https://chromium-review.googlesource.com/5536211](<https://chromium-review.googlesource.com/5536211>)


---

**#19 — go...@google.com — May 14, 2024 09:06AM**

Can we please remove Approval label for M125 & M124 if nothing else is pending?


---

**#20 — pe...@google.com — May 14, 2024 11:46AM**

This high+ V8 security issue with stable impact requires a lightweight post mortem. Please take some time to answer questions asked in this form [1] to help us improve V8 security. [1] [https://docs.google.com/forms/d/e/1FAIpQLSdSMCiEpIFLLFkMbgtulK1sf1B-idQmkFaA4XP2Rz5mN1cqWg/viewform?usp=pp_url&entry.307501673=340221135&entry.958145677=Android](<https://docs.google.com/forms/d/e/1FAIpQLSdSMCiEpIFLLFkMbgtulK1sf1B-idQmkFaA4XP2Rz5mN1cqWg/viewform?usp=pp_url&entry.307501673=340221135&entry.958145677=Android>), Fuchsia, Linux, Mac, Windows, Lacros, ChromeOS&entry.763880440=Extended&entry.1678852700=High&entry.763402679=Blink>JavaScript>Compiler>Maglev&entry.975983575=[syg@google.com](<mailto:syg@google.com>) Please ensure to copy the full link, as otherwise some issue meta data might not be populated automatically.


---

**#21 — sa...@google.com — May 14, 2024 05:19PM**

It looks like the V8 sandbox bypass is [issue 330404819](<https://issues.chromium.org/issues/330404819>) and so is already fixed (by [https://chromium-review.googlesource.com/c/v8/v8/+/5385867](<https://chromium-review.googlesource.com/c/v8/v8/+/5385867>)). On a build of V8 from current HEAD, the exploit (after some modifications necessary due to changes to the `JSArrayBuffer` layout) runs into the following `SBXCHECK`:

```
#                                                            
# Fatal error in , line 0                                    
# Check failed: index < total_register_count_.  
#  
```

I also tried re-implementing the V8 sandbox escape using our memory corruption API, and it crashes in the same way. The fix only shipped in M125, and I assume this exploit therefore only targeted Chrome versions up to 124?


---

**#22 — pe...@google.com — May 15, 2024 12:37AM**

Setting milestone because of s0/s1 severity.


---

**#23 — pe...@google.com — May 15, 2024 12:43AM**

LTS Milestone M120  
  
This issue has been flagged as a merge candidate for Chrome OS' LTS channel. If selected, our merge team will handle any additional merges. To help us determine if this issue requires a merge to LTS, please answer this short questionnaire:  
1\. Was this issue a regression for the milestone it was found in?  
2\. Is this issue related to a change or feature merged after the latest LTS Milestone?


---

**#24 — sr...@google.com — May 15, 2024 12:45AM**

adding a more minimized poc


---

**#25 — am...@chromium.org — May 15, 2024 01:13AM**

Canary 126.0.6477.3 with this fix looks good this morning, no stability issues


---

**#26 — am...@chromium.org — May 15, 2024 02:15AM**

It looks like there were some issues with the V8 -> chromium roller over the last 20 hours or so and the roll with this fix ([https://chromium-review.googlesource.com/c/chromium/src/+/5538290](<https://chromium-review.googlesource.com/c/chromium/src/+/5538290>)) was not submitted. M126 branch happened last night, so this fix didn't get rolled to be landed on Chromium branch for M126, can you please merge this to V8 12.6 at soonest so this fix can be on M126 which will be promoted to Beta tomorrow. Thank you!


---

**#27 — ap...@google.com — May 15, 2024 03:07AM**

Project: v8/v8  
Branch: refs/branch-heads/12.6  
  
commit 34f357a1afd6582ec7ab1b6a8078ba57a62e2a9c  
Author: Shu-yu Guo <[syg@chromium.org](<mailto:syg@chromium.org>)>  
Date: Mon May 13 11:23:20 2024  
  
Merged: [compiler] Don't build AccessInfo for storing to module exports  
  
Bug: 340221135  
(cherry picked from commit b3c01ac1e60afc9addad9942f7a9a6c5e8a4a6da)  
  
Change-Id: If48eb4bcb5f375721cdd55adc17cb9e61218ee10  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5538884](<https://chromium-review.googlesource.com/c/v8/v8/+/5538884>)  
Commit-Queue: Shu-yu Guo <[syg@chromium.org](<mailto:syg@chromium.org>)>  
Commit-Queue: Adam Klein <[adamk@chromium.org](<mailto:adamk@chromium.org>)>  
Auto-Submit: Shu-yu Guo <[syg@chromium.org](<mailto:syg@chromium.org>)>  
Reviewed-by: Adam Klein <[adamk@chromium.org](<mailto:adamk@chromium.org>)>  
Cr-Commit-Position: refs/branch-heads/12.6@{#2}  
Cr-Branched-From: 3c9fa12db3183a6f4ea53d2675adb66ea1194529-refs/heads/12.6.228@{#2}  
Cr-Branched-From: 981bb15ba4dbf9e2381dfc94ec2c4af0b9c6a0b6-refs/heads/main@{#93835}  
  
M src/compiler/access-info.cc  
M src/maglev/maglev-graph-builder.cc  
  
[https://chromium-review.googlesource.com/5538884](<https://chromium-review.googlesource.com/5538884>)


---

**#28 — pe...@google.com — May 16, 2024 02:29AM**

This issue requires additional review before it can be merged to the LTS channel. Please answer the following questions to help us evaluate this merge:  
  
1\. Number of CLs needed for this fix and links to them.  
2\. Level of complexity (High, Medium, Low - Explain)  
3\. Has this been merged to a stable release? beta release?  
4\. Overall Recommendation (Yes, No)


---

**#29 — rz...@google.com — May 16, 2024 02:31AM**

1. Just [https://crrev.com/c/5540772](<https://crrev.com/c/5540772>)
  2. Low, no conflicts
  3. 124, 125, 126
  4. Yes


---

**#30 — ap...@google.com — May 16, 2024 02:40AM**

Project: v8/v8  
Branch: refs/branch-heads/12.0  
  
commit 2944ee9846e7b35cd6cd2be92eb2b26fc4a680c8  
Author: Shu-yu Guo <[syg@chromium.org](<mailto:syg@chromium.org>)>  
Date: Mon May 13 11:23:20 2024  
  
[M120-LTS][compiler] Don't build AccessInfo for storing to module exports  
  
(cherry picked from commit b3c01ac1e60afc9addad9942f7a9a6c5e8a4a6da)  
  
Bug: [b/340221135](<https://issues.chromium.org/issues/340221135>)  
Change-Id: I5af35be6ebf6a69db1c4687107503575b23973c4  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5534518](<https://chromium-review.googlesource.com/c/v8/v8/+/5534518>)  
Commit-Queue: Shu-yu Guo <[syg@chromium.org](<mailto:syg@chromium.org>)>  
Cr-Original-Commit-Position: refs/heads/main@{#93872}  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5540772](<https://chromium-review.googlesource.com/c/v8/v8/+/5540772>)  
Commit-Queue: Roger Felipe Zanoni da Silva <[rzanoni@google.com](<mailto:rzanoni@google.com>)>  
Owners-Override: Shu-yu Guo <[syg@chromium.org](<mailto:syg@chromium.org>)>  
Reviewed-by: Shu-yu Guo <[syg@chromium.org](<mailto:syg@chromium.org>)>  
Cr-Commit-Position: refs/branch-heads/12.0@{#52}  
Cr-Branched-From: ed7b4caf1fb8184ad9e24346c84424055d4d430a-refs/heads/12.0.267@{#1}  
Cr-Branched-From: 210e75b19db4352c9b78dce0bae11c2dc3077df4-refs/heads/main@{#90651}  
  
M src/compiler/access-info.cc  
M src/maglev/maglev-graph-builder.cc  
  
[https://chromium-review.googlesource.com/5540772](<https://chromium-review.googlesource.com/5540772>)


---

**#31 — sp...@google.com — May 23, 2024 05:55AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $7000.00 for this report.  
  
Rationale for this decision:  
Extending for appreciation of reporting this V8 renderer RCE you discovered being exploited to us! If you are unable to accept the reward, you can choose to donate it or have it donated on your behalf.  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. Two other things we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.  
* If you are not already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have already registered, there is no need to repeat the process and you’ll automatically be paid soon. If you have any payment related questions or issues, please reach out to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>).


---

**#32 — am...@chromium.org — May 23, 2024 06:09AM**

Thank you for the report. We don't know what Kaspersky's rules for rewards these kinds of disclosures our or your eligibility to receive rewards of this kind, but we wanted to show our gratitude for disclosing this to us and including the raw exploit. Please reach out if you have any questions!


---

**#33 — rz...@google.com — Jun 20, 2024 11:44PM**

Added to the LTS-Merge-Merged-120 hotlist


---

**#34 — pe...@google.com — Aug 21, 2024 12:43AM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.


---

**#35 — ja...@gmail.com — Nov 3, 2024 01:13AM**

You know, this vulnerability wouldn't have happened if you had written your code in safe Rust. Good thing there aren't any vulnerabilities in the other 33 million lines of C++ code!


---

**#36 — ve...@chromium.org — Nov 4, 2024 07:20PM**

Fwiw that's not actually true, it's a plain logic bug that ends up being a security bug since we're writing the compiler. The exact same bug would have happened if the compiler were written in Rust. There's other things we can do to make this safer, and we are, but Rust isn't the thing that helps here.
