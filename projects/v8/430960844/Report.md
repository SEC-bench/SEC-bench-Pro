# V8 Sandbox Bypass: InstantiateAsmJs builtin doesn't protect against mid-builtin dispatch handle swaps

Issue URL: https://issues.chromium.org/issues/430960844
VRP-Reward: 20000
Date: Jul 11, 2025 10:56AM


The `InstantiateAsmJs` Turbofan builtin is installed as the active code object for asm.js functions after their respective compilation job finishes; when invoked, it will try to instantiate the translated Wasm module built during the compilation job. If the instantiation fails for any reason however, the builtin (and its associated runtime function) transparently falls back to the regular JavaScript compilation pipeline, replacing the function's installed code with the `CompileLazy` builtin before tail calling its own `JSFunction` to start executing the function in an ordinary manner. When performing this tail call, the builtin loads the code object to be invoked from the dispatch handle stored in the `JSFunction` at the moment of the tail call; the dispatch handle being used for the invocation however is the one retrieved at the start of the builtin's code. This discrepancy can be exploited by an attacker with control over the sandbox by swapping the dispatch handle with one with a different formal parameter count mid-builtin; when this newly placed dispatch handle's code is being invoked its stack frame will be set up for an incorrect formal parameter count, corrupting the stack frame and allowing an attacker to escape the V8 sandbox.

This attack can be pulled of using a race condition by performing the swap from a different thread; however, a minor defect of the asm.js instantiation process can also be leveraged instead. asm.js modules are able to either return a single function, or an object containing several exported functions; in the former case, V8 keeps track of this single function to return by defining a `__single_function__` property on the internal asm.js `WasmInstanceObject`, which is retrieved later on during the instantiation process. However, this retrieval is performed using `Object::GetProperty`, which also invokes any defined property accessors. This can be abused by defining a `__single_function__` property accessor on the `WebAssembly.Instance` prototype - this accessor will be invoked at the end of the instantiation process, at which point an attacker can perform the dispatch handle swap attack described earlier. Returning an SMI from the accessor will subsequently be interpreted as a failure to instantiate, triggering the tail-call and allowing the issue to be exploited without the need for a second thread, making the attack 100% predictable and deterministic.

See attached a proof of concept exploit script to be invoked in d8's sandbox testing mode (`--sandbox-testing`) which will result in a write to an attacker-controlled address. This POC has been tested using a d8 artifact built from commit 1786d269d8275be400579d52b3fd19fd8a6ea0b3 in release mode, however because of the nature of the exploit Chromium / other V8 configurations are also expected to be vulnerable.

This issue can be fixed by loading the code object to tailcall from the same dispatch handle used to perform the tailcall afterwards; in practice, this can be done by swapping out the call to `LoadJSFunctionCode` in line 1684 of builtins-internal-gen.cc with a call to `LoadCodeObjectFromJSDispatchTable` instead, similar to what is done in `TieringBuiltinImpl`. Additionally, the accessor loophole used for reliable exploitation of this issue should most likely also be addressed, either by refactoring the way single-function asm.js modules are handled, or by blocking property accessors from being executed during the instantiation process. While I was not able to exploit this accessor invocation on its own, I was able to trip several (debug) assertions related to exception handling (since exceptions thrown within the accessor aren't properly handled, resulting in the isolate containing a stale exception object while regular JS is still being executed), so it might be possible that there is a viable route to exploitation of just this defect in isolation which I was unable to find.

Reporter credit: if applicable, please credit my pseudonym Popax21 in regards to this report.


---

**#2 — ma...@google.com — Jul 15, 2025 01:14AM**

Thank you for the report! Over to the current V8 security shepherd for triage.


---

**#3 — bi...@google.com — Jul 16, 2025 05:29PM**

Clemens, could you please take a look?


---

**#4 — cl...@chromium.org — Jul 21, 2025 07:42PM**

I can reproduce on the given revision.

With debug code enabled, we get `abort: Wrong value in dispatch handle register passed`, without that we crash.

I'll upload to clusterfuzz to get bisection.

The problematic code seems to be in `CodeStubAssembler::LoadJSFunctionCode`, which (transparently) loads through the dispatch handle. This looks like a footgun. I would propose to fully remove that method if leaptiering is enabled. That code was added in [https://crrev.com/c/5803650/33/src/codegen/code-stub-assembler.cc](<https://crrev.com/c/5803650/33/src/codegen/code-stub-assembler.cc>); CCing Samuel and Oli.


---

**#5 — cl...@appspot.gserviceaccount.com — Jul 21, 2025 07:43PM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=6065604737826816](<https://clusterfuzz.com/testcase?key=6065604737826816>).


---

**#6 — 24...@project.gserviceaccount.com — Jul 21, 2025 07:50PM**

ClusterFuzz testcase 6065604737826816 appears to be flaky, updating reproducibility hotlist.


---

**#7 — 24...@project.gserviceaccount.com — Jul 21, 2025 07:50PM**

Detailed Report: [https://clusterfuzz.com/testcase?key=6065604737826816](<https://clusterfuzz.com/testcase?key=6065604737826816>)  
  
Fuzzer: None  
Job Type: linux_asan_d8_sandbox_testing  
Platform Id: linux  
  
Crash Type: V8 sandbox violation  
Crash Address: 0x133713371337  
Crash State:  
NULL  
Sanitizer: address (ASAN)  
  
Crash Revision: [https://clusterfuzz.com/revisions?job=linux_asan_d8_sandbox_testing&revision=101257](<https://clusterfuzz.com/revisions?job=linux_asan_d8_sandbox_testing&revision=101257>)  
  
Reproducer Testcase: [https://clusterfuzz.com/download?testcase_id=6065604737826816](<https://clusterfuzz.com/download?testcase_id=6065604737826816>)  
  
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

**#8 — ol...@chromium.org — Jul 21, 2025 07:57PM**

Ah yes, this is a nice variant of [https://chromium-review.googlesource.com/c/v8/v8/+/6554252](<https://chromium-review.googlesource.com/c/v8/v8/+/6554252>) .

I think the more problematic api is `TailCallJSCode`. This builtin should probably use `LazyBuiltinsAssembler::GenerateTailCallToJSFunction`, which closes this hole.

That said if it's easy to remove `LoadJSFunctionCode` then by all means...


---

**#9 — cl...@chromium.org — Jul 21, 2025 08:41PM**

I don't know why Clusterfuzz reports this as flaky, it reproduces 100% locally.

Let me try to re-upload with a higher retry count. Otherwise I'll bisect locally, but this is probably as old as the CL linked in [comment #4](<https://issues.chromium.org/issues/430960844#comment4>).

Oli, do you want to take this one?


---

**#10 — cl...@appspot.gserviceaccount.com — Jul 21, 2025 08:41PM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5513701910052864](<https://clusterfuzz.com/testcase?key=5513701910052864>).


---

**#11 — 24...@project.gserviceaccount.com — Jul 21, 2025 09:16PM**

ClusterFuzz testcase 5513701910052864 is verified as fixed in [https://clusterfuzz.com/revisions?job=linux_asan_d8_sandbox_testing&range=101274:101275](<https://clusterfuzz.com/revisions?job=linux_asan_d8_sandbox_testing&range=101274:101275>)  
  
If this is incorrect, please add the hotlistid:5433040 and re-open the issue.


---

**#12 — cl...@chromium.org — Jul 21, 2025 09:37PM**

Hm, fixed via `Reland "Remove g_thread_in_wasm_code flag"`? Unlikely. Let me reopen.


---

**#13 — cl...@chromium.org — Jul 21, 2025 10:52PM**

Ha, local bisection confirms that this does not reproduce any more after `Reland "Remove g_thread_in_wasm_code flag"`. I don't understand why, that CL shouldn't change anything about this dispatch handle register or object layouts (which could require changes to the reproducer).

I'll prepare a fix now anyway, and then we can discuss follow-up hardenings.


---

**#14 — ol...@chromium.org — Jul 21, 2025 10:54PM**

Ok, thanks. If you have time that would be awesome. Happy to review.


---

**#15 — dx...@google.com — Jul 23, 2025 07:51PM**

Project: v8/v8  
Branch: main  
Author: Clemens Backes [clemensb@chromium.org](<mailto:clemensb@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6771792](<https://chromium-review.googlesource.com/6771792>)

[asm.js] Fix double read of dispatch handle

* * *

Expand for full commit details

```
     
    Read the code from the dispatch handle to avoid the dangerous 
    double-fetch of the dispatch handle. 
     
    R=olivf@chromium.org 
     
    Bug: 430960844 
    Change-Id: Id7b6fd007598edfd93ddce445de46fab963db4d7 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6771792 
    Reviewed-by: Olivier Flückiger <olivf@chromium.org> 
    Commit-Queue: Clemens Backes <clemensb@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#101588}
```

* * *

Files:

  * M `src/builtins/builtins-internal-gen.cc`
  * A `test/mjsunit/sandbox/regress-430960844.js`

* * *

Hash: [c82024befbfe8458e0482f2f24c9f69361b56e75](<http://crrev.com/c82024befbfe8458e0482f2f24c9f69361b56e75>)  
Date: Wed Jul 23 09:14:12 2025

* * *


---

**#16 — dx...@google.com — Jul 23, 2025 08:58PM**

Project: v8/v8  
Branch: main  
Author: Clemens Backes [clemensb@chromium.org](<mailto:clemensb@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6771793](<https://chromium-review.googlesource.com/6771793>)

Remove CSA::LoadJSFunctionCode

* * *

Expand for full commit details

```
     
    With leap tiering (which is the default) this method loads the dispatch 
    handle from the JSFunction and then reads the code from the dispatch 
    table. This can lead to hard-to-spot double reads of the dispatch 
    handle. 
     
    Thus remove that method. 
     
    The one caller now explicitly reads the `code` field from the 
    `JSFunction` if leaptiering is disabled, and reads from the dispatch 
    handle otherwise. 
     
    R=olivf@chromium.org 
     
    Bug: 430960844 
    Change-Id: I13ef655bfe3772177db59f1ad8ca5907bec24386 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6771793 
    Commit-Queue: Clemens Backes <clemensb@chromium.org> 
    Reviewed-by: Olivier Flückiger <olivf@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#101592}
```

* * *

Files:

  * M `src/builtins/builtins-lazy-gen.cc`
  * M `src/codegen/code-stub-assembler.cc`
  * M `src/codegen/code-stub-assembler.h`

* * *

Hash: [703b582b1d61ec981caf3fc46c1ece97c72a8b58](<http://crrev.com/703b582b1d61ec981caf3fc46c1ece97c72a8b58>)  
Date: Wed Jul 23 10:06:17 2025

* * *


---

**#17 — sa...@google.com — Jul 24, 2025 06:12PM**

It would be good to backmerge this fix, and from the size of the CL, it seems like that should be possible. I'll set the respective labels now but please raise any concerns regarding a backmerge (e.g. stability).


---

**#18 — ch...@google.com — Jul 24, 2025 06:14PM**

Merge review required: no relevant commits could be automatically detected (via Git Watcher comments), sending to merge review for manual evaluation. If you have not already manually listed the relevant commits to be merged via a comment above, please do so ASAP.

Please answer the following questions so that we can safely process your merge request:

  1. Why does your merge fit within the merge criteria for these milestones?

  * Chrome Browser: [https://chromiumdash.appspot.com/branches](<https://chromiumdash.appspot.com/branches>)
  * Chrome OS: [https://goto.google.com/cros-release-branch-merge-guidelines](<https://goto.google.com/cros-release-branch-merge-guidelines>)

  2. What changes specifically would you like to merge? Please link to Gerrit.
  3. Have the changes been released and tested on canary?
  4. Is this a new feature? If yes, is it behind a Finch flag and are experiments active in any release channels?
  5. [Chrome OS only]: Was the change reviewed and approved by the Eng Prod Representative? [https://goto.google.com/cros-engprodcomponents](<https://goto.google.com/cros-engprodcomponents>)
  6. If this merge addresses a major issue in the stable channel, does it require manual verification by the test team? If so, please describe required testing.

Please contact the milestone owner if you have questions. Owners: andywu (ChromeOS), srinivassista (Desktop US), danielyip (Desktop EMEA), harrysouders (Mobile US), eakpobaro (Mobile EMEA)


---

**#19 — ch...@google.com — Jul 24, 2025 06:14PM**

Merge review required: no relevant commits could be automatically detected (via Git Watcher comments), sending to merge review for manual evaluation. If you have not already manually listed the relevant commits to be merged via a comment above, please do so ASAP.

Please answer the following questions so that we can safely process your merge request:

  1. Why does your merge fit within the merge criteria for these milestones?

  * Chrome Browser: [https://chromiumdash.appspot.com/branches](<https://chromiumdash.appspot.com/branches>)
  * Chrome OS: [https://goto.google.com/cros-release-branch-merge-guidelines](<https://goto.google.com/cros-release-branch-merge-guidelines>)

  2. What changes specifically would you like to merge? Please link to Gerrit.
  3. Have the changes been released and tested on canary?
  4. Is this a new feature? If yes, is it behind a Finch flag and are experiments active in any release channels?
  5. [Chrome OS only]: Was the change reviewed and approved by the Eng Prod Representative? [https://goto.google.com/cros-engprodcomponents](<https://goto.google.com/cros-engprodcomponents>)
  6. If this merge addresses a major issue in the stable channel, does it require manual verification by the test team? If so, please describe required testing.

Please contact the milestone owner if you have questions. Owners: alonbajayo (ChromeOS), srinivassista (Desktop US), danielyip (Desktop EMEA), govind (Mobile US), eakpobaro (Mobile EMEA)


---

**#20 — dx...@google.com — Jul 25, 2025 06:51PM**

Project: v8/v8  
Branch: main  
Author: Clemens Backes [clemensb@chromium.org](<mailto:clemensb@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6780590](<https://chromium-review.googlesource.com/6780590>)

Rename LazyBuiltinsAssembler to JSTrampolineAssembler

* * *

Expand for full commit details

```
     
    This assembler is not only used for lazy compilation builtins any more, 
    hence rename it to make its intended use more clear. 
     
    Also add a short comment to the class and rename the methods to be in 
    line with other methods on the CodeStubAssembler. 
     
    R=olivf@chromium.org 
     
    Bug: 430960844 
    Change-Id: I00ce124cf75e022bae5907ccffbe5170470de6f9 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6780590 
    Reviewed-by: Olivier Flückiger <olivf@chromium.org> 
    Commit-Queue: Clemens Backes <clemensb@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#101633}
```

* * *

Files:

  * M `BUILD.bazel`
  * M `BUILD.gn`
  * M `src/builtins/builtins-internal-gen.cc`
  * D `src/builtins/builtins-lazy-gen.h`
  * R `src/builtins/js-trampoline-assembler.cc`
  * A `src/builtins/js-trampoline-assembler.h`

* * *

Hash: [72c6f133031af8165bfb18b2c7cbcbca51bc6aaf](<http://crrev.com/72c6f133031af8165bfb18b2c7cbcbca51bc6aaf>)  
Date: Thu Jul 24 15:53:49 2025

* * *


---

**#21 — dx...@google.com — Jul 31, 2025 06:50PM**

Project: v8/v8  
Branch: main  
Author: Clemens Backes [clemensb@chromium.org](<mailto:clemensb@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6799599](<https://chromium-review.googlesource.com/6799599>)

[asm] Use symbol for storing single exported function

* * *

Expand for full commit details

```
     
    Do not store the single exported function as a property on the instance 
    object where it can be retrieved and manipulated easily from user code. 
    Use a symbol instead which is much less visible and can only be 
    manipulated using in-sandbox manipulation primitives. 
     
    This also removes a convenient hook for manipulating in-sandbox objects 
    after instantiation but before running the start function. 
     
    R=jkummerow@chromium.org 
     
    Bug: 430960844, 433809112 
    Change-Id: I613f270909c70ca9e5214a8c47d8fad870c78a6f 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6799599 
    Commit-Queue: Clemens Backes <clemensb@chromium.org> 
    Reviewed-by: Jakob Kummerow <jkummerow@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#101705}
```

* * *

Files:

  * M `src/asmjs/asm-js.cc`
  * M `src/init/heap-symbols.h`
  * M `src/roots/static-roots-intl-nowasm.h`
  * M `src/roots/static-roots-intl-wasm.h`
  * M `src/roots/static-roots-nointl-nowasm.h`
  * M `src/roots/static-roots-nointl-wasm.h`
  * M `src/wasm/module-instantiate.cc`
  * A `test/mjsunit/regress/wasm/regress-433809112.js`

* * *

Hash: [d8243e8c5655ed21f4ce13a1103fe31b200a4cb6](<http://crrev.com/d8243e8c5655ed21f4ce13a1103fe31b200a4cb6>)  
Date: Wed Jul 30 12:11:16 2025

* * *


---

**#22 — pg...@google.com — Aug 1, 2025 04:52AM**

nothing relevant to the fix seen in canary/dev afaict -

merge approved for M139 given that this is a sandbox bypass! please merge ASAP to attempt get this fix into the next M139 release!

merge for 138 on pause for now due to scheduling - we will comment back on the bug next week!


---

**#23 — dx...@google.com — Aug 4, 2025 06:29PM**

Project: v8/v8  
Branch: refs/branch-heads/13.9  
Author: Clemens Backes [clemensb@chromium.org](<mailto:clemensb@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6811147](<https://chromium-review.googlesource.com/6811147>)

Merged: [asm.js] Fix double read of dispatch handle

* * *

Expand for full commit details

```
     
    Read the code from the dispatch handle to avoid the dangerous 
    double-fetch of the dispatch handle. 
     
    R=olivf@chromium.org 
     
    (cherry picked from commit c82024befbfe8458e0482f2f24c9f69361b56e75) 
     
    Bug: 430960844 
    Change-Id: Ibb37036fe61e28e77548f18b4419b3bfe6ca7fd7 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6811147 
    Auto-Submit: Clemens Backes <clemensb@chromium.org> 
    Reviewed-by: Olivier Flückiger <olivf@chromium.org> 
    Commit-Queue: Olivier Flückiger <olivf@chromium.org> 
    Cr-Commit-Position: refs/branch-heads/13.9@{#36} 
    Cr-Branched-From: 76ea4091129171336d347c2624f6062bd9708042-refs/heads/13.9.205@{#1} 
    Cr-Branched-From: 28242121f590fe04758efec176658cd57310b297-refs/heads/main@{#100941}
```

* * *

Files:

  * M `src/builtins/builtins-internal-gen.cc`
  * A `test/mjsunit/sandbox/regress-430960844.js`

* * *

Hash: [b7355c4a72116f5b4e66e9538d3d23d2994f76d0](<http://crrev.com/b7355c4a72116f5b4e66e9538d3d23d2994f76d0>)  
Date: Wed Jul 23 09:14:12 2025

* * *


---

**#24 — ch...@google.com — Aug 4, 2025 09:43PM**

This issue has been approved for a merge. Please merge the fix to any appropriate branches as soon as possible!

Thanks for your time! To disable nags, add Disable-Nags (case sensitive) to the Chromium Labels custom field.


---

**#25 — am...@chromium.org — Aug 5, 2025 03:05AM**

Not considering this fix for backmerge to extended stable


---

**#26 — sp...@google.com — Aug 14, 2025 07:55AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $20000.00 for this report.  
  
Rationale for this decision:  
report of V8 sandbox bypass demonstrating a controlled write outside the V8 heap sandbox  
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#27 — ch...@google.com — Oct 30, 2025 09:46PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.


---

**#28 — cl...@chromium.org — Jan 8, 2026 07:33PM**

Removing `Clusterfuzz-ignore` hotlist from some old bugs as it's preventing Clusterfuzz from filing similar bugs.
