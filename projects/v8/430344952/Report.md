# Debug check failed: IsInBounds(index)

Issue URL: https://issues.chromium.org/issues/430344952
VRP-Reward: 8000
Date: Jul 9, 2025 05:49PM


```
#
# Fatal error in ../../src/objects/fixed-array-inl.h, line 116
# Debug check failed: IsInBounds(index).
#
#
#
#FailureMessage Object: 0x7ffdb6786b58
==== C stack trace ===============================

    /home/user/v8/v8/out/x64.debug/libv8_libbase.so(v8::base::debug::StackTrace::StackTrace()+0x1e) [0x7f64fec3792e]
    /home/user/v8/v8/out/x64.debug/libv8_libplatform.so(+0x4b60d) [0x7f64feba460d]
    /home/user/v8/v8/out/x64.debug/libv8_libbase.so(V8_Fatal(char const*, int, char const*, ...)+0x205) [0x7f64fec10ce5]
    /home/user/v8/v8/out/x64.debug/libv8_libbase.so(+0x4d69c) [0x7f64fec1069c]
    /home/user/v8/v8/out/x64.debug/libv8_libbase.so(V8_Dcheck(char const*, int, char const*)+0x4d) [0x7f64fec10dbd]
    /home/user/v8/v8/out/x64.debug/libv8.so(v8::internal::TaggedArrayBase<v8::internal::WeakFixedArray, v8::internal::WeakFixedArrayShape, v8::internal::HeapObjectLayout>::get(int) const+0x47) [0x7f650670c1b7]
    /home/user/v8/v8/out/x64.debug/libv8.so(void v8::internal::DeclarationScope::AllocateScopeInfos<v8::internal::Isolate>(v8::internal::ParseInfo*, v8::internal::DirectHandle<v8::internal::Script>, v8::internal::Isolate*)+0x2ec) [0x7f650670ab0c]
    /home/user/v8/v8/out/x64.debug/libv8.so(+0x7c0ac9b) [0x7f6506853c9b]
    /home/user/v8/v8/out/x64.debug/libv8.so(v8::internal::Compiler::Compile(v8::internal::Isolate*, v8::internal::Handle<v8::internal::SharedFunctionInfo>, v8::internal::Compiler::ClearExceptionFlag, v8::internal::IsCompiledScope*, v8::internal::CreateSourcePositions)+0x9f0) [0x7f65068537a0]
    /home/user/v8/v8/out/x64.debug/libv8.so(v8::internal::Compiler::Compile(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::Compiler::ClearExceptionFlag, v8::internal::IsCompiledScope*)+0x4f0) [0x7f6506854730]
    /home/user/v8/v8/out/x64.debug/libv8.so(+0x8e5a176) [0x7f6507aa3176]
    /home/user/v8/v8/out/x64.debug/libv8.so(v8::internal::Runtime_CompileLazy(int, unsigned long*, v8::internal::Isolate*)+0x151) [0x7f6507aa2bb1]
    /home/user/v8/v8/out/x64.debug/libv8.so(+0x6fca53d) [0x7f6505c1353d]
Trace/breakpoint trap (core dumped)
```

#### VERSION

V8 version 13.9.0 (candidate)

#### REPRODUCTION CASE

Build: `python3 tools/dev/gm.py x64.debug`

Run: `./d8 poc.js`

* * *

Reporter credit: Shaheen Fazim


---

**#2 — fa...@gmail.com — Jul 9, 2025 05:52PM**

#### BISECT

```
commit cc09cc9195b326dee8a24881eed9f670b4916969

    [parsing] Reuse scope infos held alive through eval

    ... by inserting the scope_info of the context in which we eval in
    what used to be the "shared_function_infos" table. This CL renames
    that table to the "infos" table. It would have been nice to add a
    separate table, but mixing it into the same table has the advantage
    that nested infos are easy to find.

    As a drive-by change this change also drops `eval_scope_position` as a
    way to distinguish eval. While it's technically fine for multiple
    evals in the scope to share scripts, it actually breaks source
    position info because the stack includes where eval was called by
    attaching that position to the script. It's relatively unlikely that
    we'll have multiple evals in the same scope with the same script
    anyway...

    Change-Id: I40fe2ed0c3fc9353e98846728561828f9803869d
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/5701108
```


---

**#3 — cl...@appspot.gserviceaccount.com — Jul 9, 2025 11:49PM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=6011440636821504](<https://clusterfuzz.com/testcase?key=6011440636821504>).


---

**#4 — cl...@appspot.gserviceaccount.com — Jul 9, 2025 11:58PM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=6235884219203584](<https://clusterfuzz.com/testcase?key=6235884219203584>).


---

**#5 — el...@chromium.org — Jul 10, 2025 02:29AM**

Note that clusterfuzz failed to reproduce this.


---

**#6 — cl...@chromium.org — Jul 10, 2025 05:59PM**

Weird that clusterfuzz cannot reproduce. It reproduces easily locally. I'll try again, but also assigning to Leszek already based on the bisection in [comment #2](<https://issues.chromium.org/issues/430344952#comment2>).


---

**#7 — cl...@chromium.org — Jul 10, 2025 06:01PM**

There is no better CF job to upload to, so I'll just confirm the bisection locally.


---

**#8 — ch...@google.com — Jul 10, 2025 09:41PM**

Setting milestone because of s0/s1 severity.


---

**#9 — ch...@google.com — Jul 10, 2025 09:42PM**

Setting Priority to P1 to match Severity s1. If this is incorrect, please reset the priority. The automation bot account won't make this change again.


---

**#10 — cl...@chromium.org — Jul 11, 2025 12:23AM**

Bisection confirmed locally. But I see that there is already an (easy) fix uploaded :)


---

**#11 — dx...@google.com — Jul 11, 2025 12:23AM**

Project: v8/v8  
Branch: main  
Author: Toon Verwaest [verwaest@chromium.org](<mailto:verwaest@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6722355](<https://chromium-review.googlesource.com/6722355>)

[preparser] Support escapes in eval

* * *

Expand for full commit details

```
     
    Bug: 430344952 
    Change-Id: I81ca2d30da871d9d1ec4c7850a94f2a3e90658ac 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6722355 
    Auto-Submit: Toon Verwaest <verwaest@chromium.org> 
    Commit-Queue: Toon Verwaest <verwaest@chromium.org> 
    Reviewed-by: Leszek Swirski <leszeks@chromium.org> 
    Commit-Queue: Leszek Swirski <leszeks@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#101351}
```

* * *

Files:

  * M `src/parsing/preparser.cc`
  * A `test/mjsunit/regress/regress-430344952.js`

* * *

Hash: 9a884b1b9a53cd23531c5428001c3f85389cb8f8  
Date: Thu Jul 10 14:38:52 2025

* * *


---

**#12 — ve...@chromium.org — Jul 11, 2025 05:51PM**

Thanks for the report!  
  
This bug was probably introduced in 2016 or so (when we started using the preparser for inner functions) based on confusing divergence between the parser and preparsed probably from the initial release. Since 2016 this would have caused semantics issues (variables wouldn't be context allocated even though they should have). My changes were designed to prevent issues in the parser from becoming context confusion issues; but I suspect that the required changes for eval in this particular case introduced the issues they were trying to prevent.


---

**#13 — ch...@google.com — Jul 11, 2025 09:38PM**

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

**#14 — dx...@google.com — Jul 14, 2025 09:35PM**

Project: v8/v8  
Branch: main  
Author: Toon Verwaest [verwaest@chromium.org](<mailto:verwaest@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6732379](<https://chromium-review.googlesource.com/6732379>)

[preparser] Support escapes in arguments contextual keywords

* * *

Expand for full commit details

```
     
    Bug: 430344952 
    Change-Id: Ib35df2f992cfe5a5207109ab500a0baaadf9b988 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6732379 
    Reviewed-by: Leszek Swirski <leszeks@chromium.org> 
    Commit-Queue: Leszek Swirski <leszeks@chromium.org> 
    Commit-Queue: Toon Verwaest <verwaest@chromium.org> 
    Auto-Submit: Toon Verwaest <verwaest@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#101389}
```

* * *

Files:

  * M `src/parsing/preparser.cc`
  * A `test/message/fail/preparse-arguments.js`
  * A `test/message/fail/preparse-arguments.out`

* * *

Hash: 0559da28e2a55930279071a18b7444501e8d1223  
Date: Mon Jul 14 11:56:15 2025

* * *


---

**#15 — ve...@chromium.org — Jul 14, 2025 09:58PM**

(this last cl is equivalent to the former, but not a security issue; just a semantics issue.)


---

**#16 — dx...@google.com — Jul 17, 2025 06:53PM**

Project: v8/v8  
Branch: main  
Author: Toon Verwaest [verwaest@chromium.org](<mailto:verwaest@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6765068](<https://chromium-review.googlesource.com/6765068>)

[compiler] Verify SFI deduplication

* * *

Expand for full commit details

```
     
    Check that preexisting SFIs have the same shape as the function literal 
    for which we reuse it. 
     
    Bug: 430344952 
    Change-Id: I0a884bb9123cdb2d9d31549847e8638389cb89bd 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6765068 
    Auto-Submit: Toon Verwaest <verwaest@chromium.org> 
    Commit-Queue: Toon Verwaest <verwaest@chromium.org> 
    Reviewed-by: Leszek Swirski <leszeks@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#101480}
```

* * *

Files:

  * M `src/objects/script.cc`

* * *

Hash: [328f6c467b940f322544567740c9c871064d045c](<http://crrev.com/328f6c467b940f322544567740c9c871064d045c>)  
Date: Thu Jul 17 09:11:24 2025

* * *


---

**#17 — am...@chromium.org — Jul 18, 2025 07:38AM**

[merge review only for https://crrev.com/c/6722355 -- security fix] No issues related to this specific fix on Canary, therefore approving this fix for merge to 13.8 and 13.9. If backmerge of this fix is dependent on any other CLs, please reach out to the release team for a merge review of the functional / semantics changes.

It is (perhaps?) also worth noting in looking at canary data for this fix, this is issue related to other preparsing changes, please see this crash report: [https://crash.corp.google.com/browse?q=&stbtiq=product:Chrome%20PreParser&reportid=54bc70c9d093cf58&index=14](<https://crash.corp.google.com/browse?q=&stbtiq=product:Chrome%20PreParser&reportid=54bc70c9d093cf58&index=14>)


---

**#18 — ch...@google.com — Jul 21, 2025 09:42PM**

This issue has been approved for a merge. Please merge the fix to any appropriate branches as soon as possible!

Thanks for your time! To disable nags, add Disable-Nags (case sensitive) to the Chromium Labels custom field.


---

**#19 — ch...@google.com — Jul 21, 2025 09:42PM**

This issue has been approved for a merge. Please merge the fix to any appropriate branches as soon as possible!

Thanks for your time! To disable nags, add Disable-Nags (case sensitive) to the Chromium Labels custom field.


---

**#20 — dx...@google.com — Jul 22, 2025 01:57AM**

Project: v8/v8  
Branch: refs/branch-heads/13.9  
Author: Toon Verwaest [verwaest@chromium.org](<mailto:verwaest@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6772975](<https://chromium-review.googlesource.com/6772975>)

Merged: [preparser] Support escapes in eval

* * *

Expand for full commit details

```
     
    Bug: 430344952 
    (cherry picked from commit 9a884b1b9a53cd23531c5428001c3f85389cb8f8) 
     
    Change-Id: I88b16aec1b81abb25fc9b0c12b0a3224ec5cfd1a 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6772975 
    Commit-Queue: Toon Verwaest <verwaest@chromium.org> 
    Auto-Submit: Toon Verwaest <verwaest@chromium.org> 
    Reviewed-by: Olivier Flückiger <olivf@chromium.org> 
    Commit-Queue: Olivier Flückiger <olivf@chromium.org> 
    Cr-Commit-Position: refs/branch-heads/13.9@{#26} 
    Cr-Branched-From: 76ea4091129171336d347c2624f6062bd9708042-refs/heads/13.9.205@{#1} 
    Cr-Branched-From: 28242121f590fe04758efec176658cd57310b297-refs/heads/main@{#100941}
```

* * *

Files:

  * M `src/parsing/preparser.cc`
  * A `test/mjsunit/regress/regress-430344952.js`

* * *

Hash: [7fa33be5ee17d396fbffb28091984598d50e1de0](<http://crrev.com/7fa33be5ee17d396fbffb28091984598d50e1de0>)  
Date: Thu Jul 10 14:38:52 2025

* * *


---

**#21 — dx...@google.com — Jul 22, 2025 01:57AM**

Project: v8/v8  
Branch: refs/branch-heads/13.8  
Author: Toon Verwaest [verwaest@chromium.org](<mailto:verwaest@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6771573](<https://chromium-review.googlesource.com/6771573>)

Merged: [preparser] Support escapes in eval

* * *

Expand for full commit details

```
     
    Bug: 430344952 
    (cherry picked from commit 9a884b1b9a53cd23531c5428001c3f85389cb8f8) 
     
    Change-Id: I67a5f2bf07ae5692fd60f0213190af99e889cb85 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6771573 
    Reviewed-by: Olivier Flückiger <olivf@chromium.org> 
    Commit-Queue: Olivier Flückiger <olivf@chromium.org> 
    Auto-Submit: Toon Verwaest <verwaest@chromium.org> 
    Commit-Queue: Toon Verwaest <verwaest@chromium.org> 
    Cr-Commit-Position: refs/branch-heads/13.8@{#58} 
    Cr-Branched-From: 61ddd471ece346840bbebbb308dceb4b4ce31b28-refs/heads/13.8.258@{#1} 
    Cr-Branched-From: fdb5de2c741658e94944f2ec1218530e98601c23-refs/heads/main@{#100480}
```

* * *

Files:

  * M `src/parsing/preparser.cc`
  * A `test/mjsunit/regress/regress-430344952.js`

* * *

Hash: [4dc4bcc2ee59212c3b36849c843bc8dda1b1ef7b](<http://crrev.com/4dc4bcc2ee59212c3b36849c843bc8dda1b1ef7b>)  
Date: Thu Jul 10 14:38:52 2025

* * *


---

**#22 — pe...@google.com — Jul 22, 2025 01:59AM**

LTS Milestone M132

This issue has been flagged as a merge candidate for Chrome OS' LTS channel. If selected, our merge team will handle any additional merges. To help us determine if this issue requires a merge to LTS, please answer this short questionnaire:

  1. Was this issue a regression for the milestone it was found in?
  2. Is this issue related to a change or feature merged after the latest LTS Milestone?


---

**#23 — sp...@google.com — Jul 22, 2025 05:55AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $8000.00 for this report.  
  
Rationale for this decision:  
$7,000 report of memory corruption in a sandboxed process / the renderer + $1,000 bisect bonus   
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#24 — am...@chromium.org — Jul 22, 2025 06:20AM**

Thank you for your efforts and reporting this issue to us.


---

**#25 — pe...@google.com — Jul 22, 2025 03:15PM**

This issue requires additional review before it can be merged to the LTS channel. Please answer the following questions to help us evaluate this merge:

  1. Number of CLs needed for this fix and links to them.
  2. Level of complexity (High, Medium, Low - Explain)
  3. Has this been merged to a stable release? beta release?
  4. Overall Recommendation (Yes, No)


---

**#26 — qk...@google.com — Jul 22, 2025 03:21PM**

1. [https://chromium-review.googlesource.com/c/v8/v8/+/6772930](<https://chromium-review.googlesource.com/c/v8/v8/+/6772930>)
  2. Low - There was no conflict.
  3. 138 and 139
  4. Yes. According to the [comment #2](<https://issues.chromium.org/issues/430344952#comment2>), the commit (cc09cc9)[1] caused the issue and M132 contains the CL.

[1] [https://chromium-review.googlesource.com/c/v8/v8/+/5701108](<https://chromium-review.googlesource.com/c/v8/v8/+/5701108>)


---

**#27 — dx...@google.com — Jul 29, 2025 09:16PM**

Project: v8/v8  
Branch: refs/branch-heads/13.2  
Author: Toon Verwaest [verwaest@chromium.org](<mailto:verwaest@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6772930](<https://chromium-review.googlesource.com/6772930>)

[M132-LTS][preparser] Support escapes in eval

* * *

Expand for full commit details

```
     
    (cherry picked from commit 9a884b1b9a53cd23531c5428001c3f85389cb8f8) 
     
    Bug: 430344952 
    Change-Id: I81ca2d30da871d9d1ec4c7850a94f2a3e90658ac 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6722355 
    Auto-Submit: Toon Verwaest <verwaest@chromium.org> 
    Commit-Queue: Toon Verwaest <verwaest@chromium.org> 
    Reviewed-by: Leszek Swirski <leszeks@chromium.org> 
    Commit-Queue: Leszek Swirski <leszeks@chromium.org> 
    Cr-Original-Commit-Position: refs/heads/main@{#101351} 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6772930 
    Reviewed-by: Marja Hölttä <marja@chromium.org> 
    Reviewed-by: Toon Verwaest <verwaest@chromium.org> 
    Cr-Commit-Position: refs/branch-heads/13.2@{#102} 
    Cr-Branched-From: 24068c59cedad9ee976ddc05431f5f497b1ebd71-refs/heads/13.2.152@{#1} 
    Cr-Branched-From: 6054ba94db0969220be4f94dc1677fc4696bdc4f-refs/heads/main@{#97085}
```

* * *

Files:

  * M `src/parsing/preparser.cc`
  * A `test/mjsunit/regress/regress-430344952.js`

* * *

Hash: [42421010c5a87e30b01e0efca8ccb67547bdfc9b](<http://crrev.com/42421010c5a87e30b01e0efca8ccb67547bdfc9b>)  
Date: Thu Jul 10 14:38:52 2025

* * *


---

**#28 — ch...@google.com — Oct 18, 2025 09:47PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
