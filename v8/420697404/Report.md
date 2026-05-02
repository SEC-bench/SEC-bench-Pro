# Debug check failed: escapes >= 0 (-2005397586 vs. 0)

Issue URL: https://issues.chromium.org/issues/420697404
VRP-Reward: 7000
Date: May 28, 2025 06:26AM


#### VULNERABILITY DETAILS

```
#
# Fatal error in ..\..\src\objects\js-regexp.cc, line 234
# Debug check failed: escapes >= 0 (-2005397586 vs. 0).
#
#
#
#FailureMessage Object: 00000012179FD550
==== C stack trace ===============================

	v8::base::debug::StackTrace::StackTrace [0x0x7fff2bb5b685+37] (D:\Browser\v8\v8\src\base\debug\stack_trace_win.cc:173)
	v8::platform::`anonymous namespace'::PrintStackTrace [0x0x7fff2bcdab89+57] (D:\Browser\v8\v8\src\libplatform\default-platform.cc:28)
	V8_Fatal [0x0x7fff2bb35463+323] (D:\Browser\v8\v8\src\base\logging.cc:214)
	v8::base::`anonymous namespace'::DefaultDcheckHandler [0x0x7fff2bb34e8c+44] (D:\Browser\v8\v8\src\base\logging.cc:59)
	V8_Dcheck [0x0x7fff2bb35571+81] (D:\Browser\v8\v8\src\base\logging.cc:228)
	v8::internal::`anonymous namespace'::CountAdditionalEscapeChars<unsigned short> [0x0x7ffeaae0b824+740] (D:\Browser\v8\v8\src\objects\js-regexp.cc:234)
	v8::internal::`anonymous namespace'::EscapeRegExpSource [0x0x7ffeaae08824+420] (D:\Browser\v8\v8\src\objects\js-regexp.cc:306)
	v8::internal::JSRegExp::Initialize [0x0x7ffeaae07dfa+618] (D:\Browser\v8\v8\src\objects\js-regexp.cc:344)
	v8::internal::JSRegExp::Initialize [0x0x7ffeaae08581+529] (D:\Browser\v8\v8\src\objects\js-regexp.cc:179)
	v8::internal::__RT_impl_Runtime_RegExpInitializeAndCompile [0x0x7ffeab3fe615+549] (D:\Browser\v8\v8\src\runtime\runtime-regexp.cc:2147)
	v8::internal::Runtime_RegExpInitializeAndCompile [0x0x7ffeab3fe10d+413] (D:\Browser\v8\v8\src\runtime\runtime-regexp.cc:2137)
	Builtins_CEntry_Return1_ArgvOnStack_NoBuiltinExit [0x0x7ffeaf6b5b41+65]
	Builtins_RegExpConstructor [0x0x7ffeaf5f40db+7579]
	Builtins_InterpreterPushArgsThenFastConstructFunction [0x0x7ffeaf247501+1089]
	Builtins_ConstructHandler [0x0x7ffeafe522c5+8261]
	Builtins_InterpreterEntryTrampoline [0x0x7ffeaf2467f2+370]
	Builtins_InterpreterEntryTrampoline [0x0x7ffeaf2467f2+370]
	Builtins_JSEntryTrampoline [0x0x7ffeaf239ce7+103]
	Builtins_JSEntry [0x0x7ffeaf23983f+255]
	v8::internal::GeneratedCode<unsigned long long,unsigned long long,unsigned long long,unsigned long long,unsigned long long,long long,unsigned long long **>::Call [0x0x7ffea9f5438c+108] (D:\Browser\v8\v8\src\execution\simulator.h:212)
	v8::internal::`anonymous namespace'::Invoke [0x0x7ffea9f503cd+5469] (D:\Browser\v8\v8\src\execution\execution.cc:441)
	v8::internal::Execution::CallScript [0x0x7ffea9f50c61+513] (D:\Browser\v8\v8\src\execution\execution.cc:542)
	v8::Script::Run [0x0x7ffea978b5cf+1135] (D:\Browser\v8\v8\src\api\api.cc:1964)
	v8::Script::Run [0x0x7ffea978b148+120] (D:\Browser\v8\v8\src\api\api.cc:1929)
	v8::Shell::ExecuteString [0x0x7ff6ae1d21b6+3142] (D:\Browser\v8\v8\src\d8\d8.cc:1030)
	v8::SourceGroup::Execute [0x0x7ff6ae1f7e26+1174] (D:\Browser\v8\v8\src\d8\d8.cc:5073)
	v8::Shell::RunMainIsolate [0x0x7ff6ae1ff287+631] (D:\Browser\v8\v8\src\d8\d8.cc:6027)
	v8::Shell::RunMain [0x0x7ff6ae1feced+205] (D:\Browser\v8\v8\src\d8\d8.cc:5935)
	v8::Shell::Main [0x0x7ff6ae201901+3873] (D:\Browser\v8\v8\src\d8\d8.cc:6801)
	main [0x0x7ff6ae202333+35] (D:\Browser\v8\v8\src\d8\d8.cc:6893)
	invoke_main [0x0x7ff6ae368489+57] (D:\a\_work\1\s\src\vctools\crt\vcstartup\src\startup\exe_common.inl:79)
	__scrt_common_main_seh [0x0x7ff6ae3685c2+306] (D:\a\_work\1\s\src\vctools\crt\vcstartup\src\startup\exe_common.inl:288)
	__scrt_common_main [0x0x7ff6ae36864e+14] (D:\a\_work\1\s\src\vctools\crt\vcstartup\src\startup\exe_common.inl:331)
	mainCRTStartup [0x0x7ff6ae36866e+14] (D:\a\_work\1\s\src\vctools\crt\vcstartup\src\startup\exe_main.cpp:17)
	BaseThreadInitThunk [0x0x7fff6adfe8d7+23]
	RtlUserThreadStart [0x0x7fff6cafc5dc+44]
```

#### VERSION

V8 version 13.9.0 (candidate)

#### REPRODUCTION CASE

Build: `python3 tools/dev/gm.py x64.debug`

Run: `./d8 poc.js`

* * *

Reporter credit: Shaheen Fazim


---

**#2 — fa...@gmail.com — May 28, 2025 06:30AM**

In my setup (Windows 11 x64)(Intel), the proof-of-concept consistently triggers the issue after running for at least 50 seconds.


---

**#3 — cl...@appspot.gserviceaccount.com — May 28, 2025 06:33AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5832560584097792](<https://clusterfuzz.com/testcase?key=5832560584097792>).


---

**#4 — 24...@project.gserviceaccount.com — May 28, 2025 06:54AM**

Testcase 5832560584097792 failed to reproduce the crash. Please inspect the program output at [https://clusterfuzz.com/testcase?key=5832560584097792](<https://clusterfuzz.com/testcase?key=5832560584097792>).


---

**#5 — ch...@google.com — May 28, 2025 09:36PM**

Setting milestone because of s0/s1 severity.


---

**#6 — ch...@google.com — May 28, 2025 09:36PM**

Setting Priority to P1 to match Severity s1. If this is incorrect, please reset the priority. The automation bot account won't make this change again.


---

**#7 — cf...@google.com — May 30, 2025 07:43PM**

Thanks for the report!

pthier@ could you PTAL? I can reproduce this on HEAD.


---

**#8 — dx...@google.com — Jun 3, 2025 05:11PM**

Project: v8/v8  
Branch: main  
Author: pthier [pthier@chromium.org](<mailto:pthier@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6611425](<https://chromium-review.googlesource.com/6611425>)

[regexp] Use uint32_t over int in EscapeRegExpSource

* * *

Expand for full commit details

```
     
    While escaping the regexp source, a regular signed int might overflow, 
    while an uint32_t can always hold the maximum length for the escaped 
    source. 
     
    Fixed: 420697404 
    Change-Id: I61084b93d51a2729204332b4285922fd82ee8fc7 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6611425 
    Reviewed-by: Jakob Linke <jgruber@chromium.org> 
    Auto-Submit: Patrick Thier <pthier@chromium.org> 
    Commit-Queue: Patrick Thier <pthier@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#100636}
```

* * *

Files:

  * M `src/objects/js-regexp.cc`

* * *

Hash: 62ee3244f3b212b92e22b8e2651afbed35de9768  
Date: Tue Jun 3 07:16:02 2025

* * *


---

**#9 — ch...@google.com — Jun 3, 2025 09:41PM**

Security Merge Request Consideration: This is sufficiently serious that it should be merged to extended stable. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M136. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately. Security Merge Request Consideration: This is sufficiently serious that it should be merged to stable. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M137. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately. Security Merge Request Consideration: This is sufficiently serious that it should be merged to beta. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M138. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately. Security Merge Request - Manual Review: Merge review required: no relevant commits could be automatically detected (via Git Watcher comments), sending to merge review for manual evaluation. If you have not already manually listed the relevant commits to be merged via a comment above, please do so ASAP.

Security Merge Request - Manual Review: Merge review required: no relevant commits could be automatically detected (via Git Watcher comments), sending to merge review for manual evaluation. If you have not already manually listed the relevant commits to be merged via a comment above, please do so ASAP.

Security Merge Request - Manual Review: Merge review required: no relevant commits could be automatically detected (via Git Watcher comments), sending to merge review for manual evaluation. If you have not already manually listed the relevant commits to be merged via a comment above, please do so ASAP.

Security Merge Request: Thank you for fixing this security bug! We aim to ship security fixes as quickly as possible, to limit their opportunity for exploitation as an "n-day" (that is, a bug where git fixes are developed into attacks before those fixes reach users).

We have determined this fix is necessary on milestone(s): [136, 137, 138].

Please answer the following questions so that we can safely process this merge request:

  1. Which CLs should be backmerged? (Please include Gerrit links.)
  2. Has this fix been verified on Canary to not pose any stability regressions?
  3. Does this fix pose any potential non-verifiable stability risks?
  4. Does this fix pose any known compatibility risks?
  5. Does it require manual verification by the test team? If so, please describe required testing.
  6. (no answer required) Please check the OS custom field to ensure all impacted OSes are checked!


---

**#10 — vo...@google.com — Jun 4, 2025 07:58PM**

Drive-by comment: Would it make sense to turn `DCHECK_EQ(result->length(), d)` in [`WriteEscapedRegExpSource`](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/objects/js-regexp.cc;l=299;drc=62ee3244f3b212b92e22b8e2651afbed35de9768>) into a hard check?

I was trying to understand whether & where this DCHECK failure would turn into a memory overwrite, which seems to happen in `WriteEscapedRegExpSource`. That code seems to quite carefully assert its invariants, but all as `DCHECK`s. That particular check seems cheap; is in the right place; and might provide some hardening.


---

**#11 — pt...@chromium.org — Jun 4, 2025 08:20PM**

I don't think turning this particular `DCHECK` into a hard check helps, as memory is already corrupted when this check would trigger. At least one might be able to create a racy exploit when corrupting memory that way on a worker thread.

Especially looking forward with the V8 sandbox being established as a security boundary, this would be a useless check as `result->length()` is assumed to be attacker controlled under this model.


---

**#12 — sp...@google.com — Jun 5, 2025 07:56AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $7000.00 for this report.  
  
Rationale for this decision:  
memory corruption in a sandboxed process / renderer   
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#13 — am...@chromium.org — Jun 5, 2025 08:02AM**

Thank you for your efforts and reporting this issue to us.


---

**#14 — fa...@gmail.com — Jun 5, 2025 08:18AM**

> V8 security bugs older than M105 may be eligible for a reward higher than specified in the table, based on the age of the bug.

Hi, according to Chrome VRP, this bug existed before M105. May I get a higher reward.

```
V8 version 10.4.132.20

#
# Fatal error in ../../src/objects/js-regexp.cc, line 304
# Debug check failed: escapes >= 0 (-2005397586 vs. 0).
#
#
#
#FailureMessage Object: 0x7fba04450c60
==== C stack trace ===============================

    ./x64.asan/d8(backtrace+0x5b) [0x55cd616670db]
    /home/user/v8-old/v8/out/x64.asan/libv8_libbase.so(v8::base::debug::StackTrace::StackTrace()+0x1e) [0x7fba0769b4ce]
    /home/user/v8-old/v8/out/x64.asan/libv8_libplatform.so(+0x88943) [0x7fba07532943]
    /home/user/v8-old/v8/out/x64.asan/libv8_libbase.so(V8_Fatal(char const*, int, char const*, ...)+0x28c) [0x7fba07625fac]
    /home/user/v8-old/v8/out/x64.asan/libv8_libbase.so(+0xa37b7) [0x7fba076257b7]
    /home/user/v8-old/v8/out/x64.asan/libv8_libbase.so(V8_Dcheck(char const*, int, char const*)+0x27) [0x7fba076260c7]
    /home/user/v8-old/v8/out/x64.asan/libv8.so(+0x69e8ec5) [0x7fba0e0b1ec5]
    /home/user/v8-old/v8/out/x64.asan/libv8.so(+0x69e786e) [0x7fba0e0b086e]
    /home/user/v8-old/v8/out/x64.asan/libv8.so(v8::internal::JSRegExp::Initialize(v8::internal::Handle<v8::internal::JSRegExp>, v8::internal::Handle<v8::internal::String>, v8::base::Flags<v8::internal::JSRegExp::Flag, int>, unsigned int)+0xba9) [0x7fba0e0acec9]
    /home/user/v8-old/v8/out/x64.asan/libv8.so(v8::internal::JSRegExp::Initialize(v8::internal::Handle<v8::internal::JSRegExp>, v8::internal::Handle<v8::internal::String>, v8::internal::Handle<v8::internal::String>)+0x7e2) [0x7fba0e0b00d2]
    /home/user/v8-old/v8/out/x64.asan/libv8.so(+0x776caa0) [0x7fba0ee35aa0]
    /home/user/v8-old/v8/out/x64.asan/libv8.so(v8::internal::Runtime_RegExpInitializeAndCompile(int, unsigned long*, v8::internal::Isolate*)+0x36b) [0x7fba0ee353eb]
    [0x7fb99f9d1b3f]
Trace/breakpoint trap (core dumped)
```


---

**#15 — am...@chromium.org — Jun 5, 2025 08:32AM**

Hello, this report does not qualify for reward for `Rewards for V8 Bugs in Stable Channel and Older versions` as it does not meet the criteria expected for these rewards, such as:

> To be eligible for these increased reward amounts, the report of the V8 bug should include a bisection to help validate the age / version of Chrome the bug was introduced in. The report must clearly describe through analysis or demonstrate exploitability of the bug being reported.

Please see [https://g.co/chrome/vrp#rewards-for-v8-bugs-in-stable-channel-and-older-versions](<https://g.co/chrome/vrp#rewards-for-v8-bugs-in-stable-channel-and-older-versions>) for the full details of examples of demonstrations of exploitability required for rewards in this category.

It would also be expected that the bisect (demonstrating the age of the bug / channel introduced) and the exploitability information be included in the original report, not after the bug is resolved.


---

**#16 — fa...@gmail.com — Jun 5, 2025 08:41AM**

CVE! When dost thou cometh? (Good thing they funding MITRE)


---

**#17 — am...@chromium.org — Jun 6, 2025 11:30PM**

CVEs are issued at the fix ships in a Stable channel udpate [https://chromium.googlesource.com/chromium/src/+/main/docs/security/vrp-faq.md#will-i-receive-a-cve-for-my-bug](<https://chromium.googlesource.com/chromium/src/+/main/docs/security/vrp-faq.md#will-i-receive-a-cve-for-my-bug>)

Please also be mindful that that public disclosure of bugs is not until 14 weeks after the bug is fixed [1] which, for this issue, would be 2 September 2025.

[1] [https://chromium.googlesource.com/chromium/src/+/main/docs/security/vrp-faq.md#when-will-the-bug-i-reported-be-publicly-disclosed](<https://chromium.googlesource.com/chromium/src/+/main/docs/security/vrp-faq.md#when-will-the-bug-i-reported-be-publicly-disclosed>)


---

**#18 — pe...@google.com — Jun 7, 2025 12:36AM**

The NextAction date has arrived: 2025-06-06 To opt-out from this automation rule, please add Optout-Blintz-Nextaction-Alert to the "Chromium Labels" custom field.


---

**#19 — am...@chromium.org — Jun 7, 2025 06:45AM**

[https://crrev.com/c/6611425](<https://crrev.com/c/6611425>) approved for merges, please feel free to merge to 13.8, 13.7, 13.6 at your earliest convenience; there is no rush on this and can wait until after the Monday MUC holiday


---

**#20 — dx...@google.com — Jun 10, 2025 06:52PM**

Project: v8/v8  
Branch: refs/branch-heads/13.6  
Author: pthier [pthier@chromium.org](<mailto:pthier@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6632467](<https://chromium-review.googlesource.com/6632467>)

Merged: [regexp] Use uint32_t over int in EscapeRegExpSource

* * *

Expand for full commit details

```
     
    While escaping the regexp source, a regular signed int might overflow, 
    while an uint32_t can always hold the maximum length for the escaped 
    source. 
     
    Bug: 420697404 
    (cherry picked from commit 62ee3244f3b212b92e22b8e2651afbed35de9768) 
     
    Change-Id: I595897ec14fa0ee6d88c62cb673fbde6c228a6db 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6632467 
    Commit-Queue: Patrick Thier <pthier@chromium.org> 
    Commit-Queue: Jakob Linke <jgruber@chromium.org> 
    Auto-Submit: Patrick Thier <pthier@chromium.org> 
    Reviewed-by: Jakob Linke <jgruber@chromium.org> 
    Cr-Commit-Position: refs/branch-heads/13.6@{#32} 
    Cr-Branched-From: 04fa9cbe26525ab96ab3ff2a18b5d25e443e12fa-refs/heads/13.6.233@{#1} 
    Cr-Branched-From: f6be4827a049a8c3ea9218934c7bb5728369a3e7-refs/heads/main@{#99571}
```

* * *

Files:

  * M `src/objects/js-regexp.cc`

* * *

Hash: 9197519a790333173d80dade37598a326e180d3d  
Date: Tue Jun 3 07:16:02 2025

* * *


---

**#21 — dx...@google.com — Jun 10, 2025 06:55PM**

Project: v8/v8  
Branch: refs/branch-heads/13.8  
Author: pthier [pthier@chromium.org](<mailto:pthier@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6632466](<https://chromium-review.googlesource.com/6632466>)

Merged: [regexp] Use uint32_t over int in EscapeRegExpSource

* * *

Expand for full commit details

```
     
    While escaping the regexp source, a regular signed int might overflow, 
    while an uint32_t can always hold the maximum length for the escaped 
    source. 
     
    Bug: 420697404 
    (cherry picked from commit 62ee3244f3b212b92e22b8e2651afbed35de9768) 
     
    Change-Id: I7c22b7a761b6e712db9f6b55a8f85ae78eda1355 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6632466 
    Reviewed-by: Jakob Linke <jgruber@chromium.org> 
    Commit-Queue: Jakob Linke <jgruber@chromium.org> 
    Auto-Submit: Patrick Thier <pthier@chromium.org> 
    Commit-Queue: Patrick Thier <pthier@chromium.org> 
    Cr-Commit-Position: refs/branch-heads/13.8@{#25} 
    Cr-Branched-From: 61ddd471ece346840bbebbb308dceb4b4ce31b28-refs/heads/13.8.258@{#1} 
    Cr-Branched-From: fdb5de2c741658e94944f2ec1218530e98601c23-refs/heads/main@{#100480}
```

* * *

Files:

  * M `src/objects/js-regexp.cc`

* * *

Hash: c31f5c76082820bd6cb300c4791aa975e66b9822  
Date: Tue Jun 3 07:16:02 2025

* * *


---

**#22 — pe...@google.com — Jun 10, 2025 06:58PM**

LTS Milestone M132

This issue has been flagged as a merge candidate for Chrome OS' LTS channel. If selected, our merge team will handle any additional merges. To help us determine if this issue requires a merge to LTS, please answer this short questionnaire:

  1. Was this issue a regression for the milestone it was found in?
  2. Is this issue related to a change or feature merged after the latest LTS Milestone?


---

**#23 — pt...@chromium.org — Jun 10, 2025 07:52PM**

Answers to [comment #22](<https://issues.chromium.org/issues/420697404#comment22>)

Answering both 1. and 2.: No, the issue was originally introduced in M73

Since the fix is trivial, I would suggest merging to LTS.


---

**#24 — ch...@google.com — Jun 10, 2025 09:42PM**

This issue has been approved for a merge. Please merge the fix to any appropriate branches as soon as possible!

Thanks for your time! To disable nags, add Disable-Nags (case sensitive) to the Chromium Labels custom field.


---

**#25 — ch...@google.com — Jun 10, 2025 09:42PM**

This issue has been approved for a merge. Please merge the fix to any appropriate branches as soon as possible!

Thanks for your time! To disable nags, add Disable-Nags (case sensitive) to the Chromium Labels custom field.


---

**#26 — ch...@google.com — Jun 10, 2025 09:42PM**

This issue has been approved for a merge. Please merge the fix to any appropriate branches as soon as possible!

Thanks for your time! To disable nags, add Disable-Nags (case sensitive) to the Chromium Labels custom field.


---

**#27 — dx...@google.com — Jun 10, 2025 09:53PM**

Project: v8/v8  
Branch: refs/branch-heads/13.7  
Author: pthier [pthier@chromium.org](<mailto:pthier@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6632486](<https://chromium-review.googlesource.com/6632486>)

Merged: [regexp] Use uint32_t over int in EscapeRegExpSource

* * *

Expand for full commit details

```
     
    While escaping the regexp source, a regular signed int might overflow, 
    while an uint32_t can always hold the maximum length for the escaped 
    source. 
     
    Bug: 420697404 
    (cherry picked from commit 62ee3244f3b212b92e22b8e2651afbed35de9768) 
     
    Change-Id: I45810a1d148b23d4a29f03078acf35d8c66cedd5 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6632486 
    Reviewed-by: Jakob Linke <jgruber@chromium.org> 
    Commit-Queue: Patrick Thier <pthier@chromium.org> 
    Auto-Submit: Patrick Thier <pthier@chromium.org> 
    Cr-Commit-Position: refs/branch-heads/13.7@{#30} 
    Cr-Branched-From: dd5370d3d251320f6a5bed609ff8e1b71c767d97-refs/heads/13.7.152@{#1} 
    Cr-Branched-From: fa9b75303b0b5d2940a67096dca3babd14aa1fd2-refs/heads/main@{#99927}
```

* * *

Files:

  * M `src/objects/js-regexp.cc`

* * *

Hash: 59579e02020412e150a032960411cfcd4a5157bf  
Date: Tue Jun 3 07:16:02 2025

* * *


---

**#28 — pe...@google.com — Jun 12, 2025 02:16PM**

This issue requires additional review before it can be merged to the LTS channel. Please answer the following questions to help us evaluate this merge:

  1. Number of CLs needed for this fix and links to them.
  2. Level of complexity (High, Medium, Low - Explain)
  3. Has this been merged to a stable release? beta release?
  4. Overall Recommendation (Yes, No)


---

**#29 — qk...@google.com — Jun 12, 2025 02:23PM**

1\. [https://chromium-review.googlesource.com/c/v8/v8/+/6636620](<https://chromium-review.googlesource.com/c/v8/v8/+/6636620>)  
2\. Low - There was no conflict.  
3\. 136, 137, and 138  
4\. Yes. According to the [comment #23](<https://issues.chromium.org/issues/420697404#comment23>), the issue has existed since M73.


---

**#30 — dx...@google.com — Jun 17, 2025 06:41PM**

Project: v8/v8  
Branch: refs/branch-heads/13.2  
Author: pthier [pthier@chromium.org](<mailto:pthier@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6636620](<https://chromium-review.googlesource.com/6636620>)

[M132-LTS][regexp] Use uint32_t over int in EscapeRegExpSource

* * *

Expand for full commit details

```
     
    While escaping the regexp source, a regular signed int might overflow, 
    while an uint32_t can always hold the maximum length for the escaped 
    source. 
     
    (cherry picked from commit 62ee3244f3b212b92e22b8e2651afbed35de9768) 
     
    Fixed: 420697404 
    Change-Id: I61084b93d51a2729204332b4285922fd82ee8fc7 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6611425 
    Reviewed-by: Jakob Linke <jgruber@chromium.org> 
    Auto-Submit: Patrick Thier <pthier@chromium.org> 
    Commit-Queue: Patrick Thier <pthier@chromium.org> 
    Cr-Original-Commit-Position: refs/heads/main@{#100636} 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6636620 
    Commit-Queue: Gyuyoung Kim (xWF) <qkim@google.com> 
    Reviewed-by: Patrick Thier <pthier@chromium.org> 
    Cr-Commit-Position: refs/branch-heads/13.2@{#96} 
    Cr-Branched-From: 24068c59cedad9ee976ddc05431f5f497b1ebd71-refs/heads/13.2.152@{#1} 
    Cr-Branched-From: 6054ba94db0969220be4f94dc1677fc4696bdc4f-refs/heads/main@{#97085}
```

* * *

Files:

  * M `src/objects/js-regexp.cc`

* * *

Hash: 20c1b8e9bba9227ea836a8cde695b5bf8df113b4  
Date: Tue Jun 3 07:16:02 2025

* * *


---

**#31 — sr...@google.com — Jun 25, 2025 06:09PM**

We discussed this bug Yesterday and we believe that:  
1) the issue is not fixed by the CL  
2) the overflow currently doesn't lead to a security issue  
So I'm re-opening and downgrading this bug to S2.  
  
Here's what we were thinking:  
* CountAdditionalEscapeChars() won't overflow the variable anymore, but it can still return a value that is 5*String::kMaxLength  
* This is used in EscapeRegExpSource as `uint32_t length = source->length() + additional_escape_chars;` => this addition can now get up to 6*String::kMaxLength  
* This is then used as the argument to NewRawOneByteString. This implicitly casts the length back to a signed integer.  
* NewRawStringWithMap has an explicit check for negative values here: [https://source.chromium.org/chromium/chromium/src/+/main:v8/src/heap/factory-base.cc;l=818;drc=b8b5768e5d0d1c2a84fe4896eae884d97fd1131e](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/heap/factory-base.cc;l=818;drc=b8b5768e5d0d1c2a84fe4896eae884d97fd1131e>)  
  
This doesn't look a security issue at the moment since, while it can turn into a negative integer, we catch it and throw an exception.  
It would lead to a buffer that we allocate with a too small size if it overflows enough to reach a small positive integer. As far as I can tell, this is not possible right now, since 6*String::kMaxLength doesn't overflow a uint32_t.


---

**#32 — ch...@google.com — Jun 25, 2025 09:39PM**

pthier: Uh oh! This issue still open and hasn't been updated in the last 14 days. This is a serious vulnerability, and we want to ensure that there's progress. Could you please leave an update with the current status and any potential blockers?

If you're not the right owner for this issue, could you please remove yourself as soon as possible or help us find the right one?

If the issue is fixed or you can't reproduce it, please close the bug. If you've started working on a fix, please set the status to Started.[internal debugging info: security_nag_check]

Thanks for your time! To disable nags, add Disable-Nags (case sensitive) to the Chromium Labels custom field.


---

**#33 — pt...@chromium.org — Jun 26, 2025 11:11PM**

Hmpf yeah that's embarassing. I guess this never was exploitable after all. That happens when you "verify" the issue and work on a fix separately. I looked at it and thought "Oh this can go negative, the final length can be shorter than the previous length" without checking at this point, that the new length can be less than the previous length but still a valid length (which is not possible after looking at it again).

The "fix" is still valid, eventhough the only benefit was adding a `static_assert` that `uint32_t` overflows can't happen given the current constraints on `String::kMaxLength` and the maximum growth-factor (although I added the assert only on the `CoundAdditionalEscapeChars` method). I will add an additional assert that the final length also can't overflow + more comments.


---

**#34 — dx...@google.com — Jun 27, 2025 05:39PM**

Project: v8/v8  
Branch: main  
Author: pthier [pthier@chromium.org](<mailto:pthier@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6678714](<https://chromium-review.googlesource.com/6678714>)

[regexp] Add more clarifying comments to EscapeRegExpSource

* * *

Expand for full commit details

```
     
    ... explaining and asserting why overflows while calculating the new 
    length won't lead to any issues. 
     
    Fixed: 420697404 
    Change-Id: Ibf3edaea0886c9d6f68723b20364a5299f5c949f 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6678714 
    Auto-Submit: Patrick Thier <pthier@chromium.org> 
    Reviewed-by: Jakob Linke <jgruber@chromium.org> 
    Commit-Queue: Patrick Thier <pthier@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#101079}
```

* * *

Files:

  * M `src/objects/js-regexp.cc`

* * *

Hash: c4af5ea5737e8c38aced137169c75e2a18fc9bd3  
Date: Fri Jun 27 08:01:02 2025

* * *


---

**#35 — ch...@google.com — Oct 4, 2025 09:41PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
