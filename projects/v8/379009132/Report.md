# Potential type confusion in wasm and js interaction

Issue URL: https://issues.chromium.org/issues/379009132
VRP-Reward: 8000
Date: Nov 14, 2024 09:03PM


# VULNERABILITY DETAILS

It crashes when calling `toString()` on a wasm function's return value in javascript (the last line of the poc).

# VERSION

v8 Version: commit 7a9e78e98f59b7adf79e6ead0459718e4ed249e7 (Nov 14 2024)

Operating System: Ubuntu Linux 5.4.0-167-generic

# REPRODUCTION CASE

`gn gen out/release`

`./out/release/d8 --jit-fuzzing ./poc.js`

Note that the flag `--jit-fuzzing` is necessary for reproducing the crash.

# ADDITIONAL INFORMATION

provided in the attached crash.log


---

**#2 — li...@gmail.com — Nov 15, 2024 12:28AM**

We identified the earliest commit that introduces this crash is [0d15bbf1fb92f435e10c14f858d82d4cca851bf4](<https://chromium.googlesource.com/v8/v8/+/0d15bbf1fb92f435e10c14f858d82d4cca851bf4>)


---

**#3 — cl...@appspot.gserviceaccount.com — Nov 15, 2024 04:19AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5115553911865344](<https://clusterfuzz.com/testcase?key=5115553911865344>).


---

**#4 — cl...@appspot.gserviceaccount.com — Nov 15, 2024 04:20AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5079613088661504](<https://clusterfuzz.com/testcase?key=5079613088661504>).


---

**#5 — am...@chromium.org — Nov 15, 2024 04:45AM**

This didn't repro as either a DCHCEK or a CSA_CHECK failure as the crash.log shows.   
Going to tentatively pass it over to the wasm folks due to investigate since there has been a lot of recent work in this area.


---

**#6 — am...@chromium.org — Nov 15, 2024 04:46AM**

cc'ing ishell@ as current v8 shepherd  
tentatively setting as S1/P1 and foundin-131 (based on c#2); please adjust accordingly as this is reviewed


---

**#7 — 24...@project.gserviceaccount.com — Nov 15, 2024 06:37AM**

Automatically applying components based on crash stacktrace and information from OWNERS files.  
  
If this is incorrect, please apply the hotlistid:4801165.


---

**#8 — 24...@project.gserviceaccount.com — Nov 15, 2024 06:37AM**

Detailed Report: [https://clusterfuzz.com/testcase?key=5115553911865344](<https://clusterfuzz.com/testcase?key=5115553911865344>)  
  
Fuzzer: None  
Job Type: linux_asan_d8  
Platform Id: linux  
  
Crash Type: Abrt  
Crash Address: 0x05390000cb94  
Crash State:  
v8::internal::Isolate::PushStackTraceAndDie  
v8::internal::LookupIterator::GetRootForNonJSReceiver  
v8::internal::LookupIterator::GetRoot  
  
Sanitizer: address (ASAN)  
  
Regressed: [https://clusterfuzz.com/revisions?job=linux_asan_d8&range=96422:96423](<https://clusterfuzz.com/revisions?job=linux_asan_d8&range=96422:96423>)  
  
Reproducer Testcase: [https://clusterfuzz.com/download?testcase_id=5115553911865344](<https://clusterfuzz.com/download?testcase_id=5115553911865344>)  
  
To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.   
  
If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.  
  
If you have any feedback on reproducing test cases, let us know at [https://forms.gle/Yh3qCYFveHj6E5jz5](<https://forms.gle/Yh3qCYFveHj6E5jz5>) so we can improve.


---

**#9 — pe...@google.com — Nov 16, 2024 12:39AM**

Setting milestone because of s0/s1 severity.


---

**#10 — cl...@chromium.org — Nov 16, 2024 01:06AM**

I can reproduce. I'll minimize the provided POC.


---

**#11 — cl...@chromium.org — Nov 16, 2024 01:18AM**

```
// Flags: --jit-fuzzing

d8.file.execute("test/mjsunit/wasm/wasm-module-builder.js");

const builder = new WasmModuleBuilder();
const type = builder.nextTypeIndex();
builder.addType(makeSig([], [wasmRefType(type), kWasmI32]));
const func1 = builder.addFunction('func1', kSig_i_iii)
                  .addBody([...wasmI32Const(3113)])
                  .exportFunc();
const func2 = builder.addFunction('func2', type);
func2.addBody([
  kExprRefFunc, func2.index,
  ...wasmI32Const(176),
]).exportFunc();
const instance = builder.instantiate();
instance.exports.func2();
const v200 = instance.exports.func2();
v200.toString();
```


---

**#12 — cl...@chromium.org — Nov 16, 2024 01:19AM**

This produces:

```
abort: CSA_DCHECK failed: Torque assert 'Is<A>(o)' failed [src/builtins/cast.tq:846] [../../src/builtins/base.tq:612]
```

If I remove the `i32` return, I instead get this DCHECK error:

```
#
# Fatal error in ../../src/execution/arguments.h, line 100
# Debug check failed: Handle<To> v8::internal::Cast(Handle<From>, const v8::SourceLocation &) [To = v8::internal::Union<v8::internal::Smi, v8::internal::HeapNumber, v8::internal::BigInt, v8::internal::String, v8::internal::Symbol, v8::internal::Boolean, v8::internal::Null, v8::internal::Undefined, v8::internal::JSReceiver>, From = v8::internal::Object].
```


---

**#13 — cl...@chromium.org — Nov 16, 2024 01:20AM**

It reproduces with just `--wasm-wrapper-tiering-budget=1`.


---

**#14 — cl...@chromium.org — Nov 16, 2024 01:24AM**

Re-uploading the reduced reproducer to CF.


---

**#15 — cl...@appspot.gserviceaccount.com — Nov 16, 2024 01:24AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=6187955706068992](<https://clusterfuzz.com/testcase?key=6187955706068992>).


---

**#16 — cl...@chromium.org — Nov 16, 2024 01:27AM**

Looks like the `WasmFuncRef` leaks to JS, instead of being translated to the JSFunction at the boundary.


---

**#17 — cl...@chromium.org — Nov 16, 2024 01:31AM**

Also `func1` can be dropped, making the reproducer even shorter:

```
// Flags: --wasm-wrapper-tiering-budget=1

d8.file.execute('test/mjsunit/wasm/wasm-module-builder.js');

const builder = new WasmModuleBuilder();
const type = builder.nextTypeIndex();
builder.addType(makeSig([], [wasmRefType(type)]));
const func2 = builder.addFunction('func2', type);
func2.addBody([kExprRefFunc, func2.index]).exportFunc();
const instance = builder.instantiate();
// Trigger wrapper tier-up.
instance.exports.func2();
// This call runs the compiled wrapper, which returns a WasmFuncRef.
const v200 = instance.exports.func2();
// %DebugPrint(v200);
v200.toString();
```


---

**#18 — cl...@chromium.org — Nov 16, 2024 01:46AM**

Wait, this defines a recursive type outside of a recursion group. Isn't this forbidden?

The resulting canonical type is then wrong. It has canonical index `3`, but the return value is `(ref 0)`. This looks highly broken.


---

**#19 — cl...@chromium.org — Nov 16, 2024 01:59AM**

Ok, `(ref 0)` is actually correct, because this is a relative index (which we should print somehow to avoid confusion...).

In wrapper compilation we don't handle it like a relative index though: [https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/wrappers.cc;l=227;drc=9997fc01395257cffd7231f14bb4d9fa7eaa9665](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/wrappers.cc;l=227;drc=9997fc01395257cffd7231f14bb4d9fa7eaa9665>)

Here we look for the canonical index 0 instead of 3, and 0 is not a function signature, hence no conversion...

I'll fix this next week. Have a good weekend everyone!


---

**#20 — 24...@project.gserviceaccount.com — Nov 16, 2024 03:12AM**

Detailed Report: [https://clusterfuzz.com/testcase?key=6187955706068992](<https://clusterfuzz.com/testcase?key=6187955706068992>)  
  
Fuzzer: None  
Job Type: linux_asan_d8_dbg  
Platform Id: linux  
  
Crash Type: DCHECK failure  
Crash Address:   
Crash State:  
Handle<To> v8::internal::Cast(Handle<From>, const v8::SourceLocation &) [To = v8  
v8::internal::Handle<v8::internal::Union<v8::internal::Smi, v8::internal::HeapNu  
v8::internal::__RT_impl_Runtime_LoadNoFeedbackIC_Miss  
  
Sanitizer: address (ASAN)  
  
Regressed: [https://clusterfuzz.com/revisions?job=linux_asan_d8_dbg&range=96422:96423](<https://clusterfuzz.com/revisions?job=linux_asan_d8_dbg&range=96422:96423>)  
  
Reproducer Testcase: [https://clusterfuzz.com/download?testcase_id=6187955706068992](<https://clusterfuzz.com/download?testcase_id=6187955706068992>)  
  
To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.   
  
If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.  
  
If you have any feedback on reproducing test cases, let us know at [https://forms.gle/Yh3qCYFveHj6E5jz5](<https://forms.gle/Yh3qCYFveHj6E5jz5>) so we can improve.


---

**#21 — ap...@google.com — Nov 20, 2024 02:52AM**

Project: v8/v8  
Branch: main  
Author: Clemens Backes <[clemensb@chromium.org](<mailto:clemensb@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6035175](<https://chromium-review.googlesource.com/6035175>)

[wasm] Remove relative type indexes from canonical types

* * *

Expand for full commit details

```
[wasm] Remove relative type indexes from canonical types 
 
Those relative types were leaking from the type canonicalizer, which 
leads to type confusion in callers. 
 
This CL fully removes the concept of relative type indexes (and thus 
removes the `CanonicalRelativeField` bit from the bitfield in 
`ValueTypeBase`). During canonicalization we pass the start and end of 
the recursion group into hashing and equality checking, and use this to 
compute relative indexes within the recursion group on demand. The 
stored version will always have absolute indexes though. 
 
R=jkummerow@chromium.org 
 
Bug: 379612177 
Change-Id: I24154785c38dd3d8abb3d252bef4752024bad223 
Fixed: 379009132 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6035175 
Reviewed-by: Jakob Kummerow <jkummerow@chromium.org> 
Commit-Queue: Clemens Backes <clemensb@chromium.org> 
Cr-Commit-Position: refs/heads/main@{#97279}
```

* * *

Files:

  * M `src/base/bounds.h`
  * M `src/wasm/canonical-types.cc`
  * M `src/wasm/canonical-types.h`
  * M `src/wasm/std-object-sizes.h`
  * M `src/wasm/struct-types.h`
  * M `src/wasm/value-type.h`
  * M `src/wasm/wasm-objects.cc`
  * M `test/unittests/wasm/subtyping-unittest.cc`

* * *

Hash: 20d9a7f760c018183c836283017a321638b66810  
Date: Tue Nov 19 18:17:33 2024

* * *


---

**#22 — li...@gmail.com — Nov 20, 2024 12:56PM**

Thank you for your prompt confirmation and fixes!


---

**#23 — pe...@google.com — Nov 21, 2024 12:42AM**

Security Merge Request Consideration: This is sufficiently serious that it should be merged to stable. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M131. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately. Security Merge Request Consideration: This is sufficiently serious that it should be merged to beta. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M132. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately. Security Merge Request: Thank you for fixing this security bug! We aim to ship security fixes as quickly as possible, to limit their opportunity for exploitation as an "n-day" (that is, a bug where git fixes are developed into attacks before those fixes reach users).

We have determined this fix is necessary on milestone(s): [].

Please answer the following questions so that we can safely process this merge request:

  1. Which CLs should be backmerged? (Please include Gerrit links.)
  2. Has this fix been verified on Canary to not pose any stability regressions?
  3. Does this fix pose any potential non-verifiable stability risks?
  4. Does this fix pose any known compatibility risks?
  5. Does it require manual verification by the test team? If so, please describe required testing.
  6. (no answer required) Please check the OS custom field to ensure all impacted OSes are checked!


---

**#24 — pe...@google.com — Nov 21, 2024 02:58AM**

Merge review required: M132 is already shipping to beta.

Please answer the following questions so that we can safely process your merge request:

  1. Why does your merge fit within the merge criteria for these milestones?

  * Chrome Browser: [https://chromiumdash.appspot.com/branches](<https://chromiumdash.appspot.com/branches>)
  * Chrome OS: [https://goto.google.com/cros-release-branch-merge-guidelines](<https://goto.google.com/cros-release-branch-merge-guidelines>)

  2. What changes specifically would you like to merge? Please link to Gerrit.
  3. Have the changes been released and tested on canary?
  4. Is this a new feature? If yes, is it behind a Finch flag and are experiments active in any release channels?
  5. [Chrome OS only]: Was the change reviewed and approved by the Eng Prod Representative? [https://goto.google.com/cros-engprodcomponents](<https://goto.google.com/cros-engprodcomponents>)
  6. If this merge addresses a major issue in the stable channel, does it require manual verification by the test team? If so, please describe required testing.

Please contact the milestone owner if you have questions. Owners: govind (Android), govind (iOS), alonbajayo (ChromeOS), srinivassista (Desktop)


---

**#25 — pe...@google.com — Nov 21, 2024 02:58AM**

Merge review required: M131 is already shipping to stable.

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

**#26 — cl...@chromium.org — Nov 21, 2024 07:46PM**

1. Why does your merge fit within the merge criteria for these milestones?

Fixes a high-severity security issue.

  2. What changes specifically would you like to merge? Please link to Gerrit.

[https://crrev.com/c/6035175](<https://crrev.com/c/6035175>)

  3. Have the changes been released and tested on canary?

Yes (since 133.0.6848.0)

  4. Is this a new feature? If yes, is it behind a Finch flag and are experiments active in any release channels?

Not a new feature.

  5. [Chrome OS only]: Was the change reviewed and approved by the Eng Prod Representative? [https://goto.google.com/cros-engprodcomponents](<https://goto.google.com/cros-engprodcomponents>)

n/a

  6. If this merge addresses a major issue in the stable channel, does it require manual verification by the test team? If so, please describe required testing.

No manual testing required.


---

**#27 — am...@chromium.org — Nov 23, 2024 03:54AM**

[https://crrev.com/c/6035175](<https://crrev.com/c/6035175>) approved for merge, please merge to 13.2 and 13.1 at your convenience (before EOD 29 November) so this fix can be included in the first updates following next week's release freeze


---

**#28 — pe...@google.com — Nov 27, 2024 12:38AM**

This issue has been approved for a merge. Please merge the fix to any appropriate branches as soon as possible!

If all merges have been completed, please remove any remaining Merge-Approved labels from this issue.

Thanks for your time! To disable nags, add Disable-Nags (case sensitive) to the Chromium Labels custom field.


---

**#29 — cl...@chromium.org — Nov 27, 2024 06:07PM**

I'll go ahead and create the backmerges. Note that there is a follow-up fix ([https://crbug.com/380397544](<https://crbug.com/380397544>)) that should also be merged until Friday.


---

**#30 — ap...@google.com — Nov 27, 2024 07:03PM**

Project: v8/v8  
Branch: refs/branch-heads/13.2  
Author: Clemens Backes <[clemensb@chromium.org](<mailto:clemensb@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6049645](<https://chromium-review.googlesource.com/6049645>)

Merged: [wasm] Remove relative type indexes from canonical types

* * *

Expand for full commit details

```
Merged: [wasm] Remove relative type indexes from canonical types 
 
Those relative types were leaking from the type canonicalizer, which 
leads to type confusion in callers. 
 
This CL fully removes the concept of relative type indexes (and thus 
removes the `CanonicalRelativeField` bit from the bitfield in 
`ValueTypeBase`). During canonicalization we pass the start and end of 
the recursion group into hashing and equality checking, and use this to 
compute relative indexes within the recursion group on demand. The 
stored version will always have absolute indexes though. 
 
R=jkummerow@chromium.org 
 
Bug: 379009132 
(cherry picked from commit 20d9a7f760c018183c836283017a321638b66810) 
 
Change-Id: I9bee6b37b9da36684f8c5b2866725eac79c896ad 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6049645 
Commit-Queue: Clemens Backes <clemensb@chromium.org> 
Reviewed-by: Jakob Kummerow <jkummerow@chromium.org> 
Cr-Commit-Position: refs/branch-heads/13.2@{#22} 
Cr-Branched-From: 24068c59cedad9ee976ddc05431f5f497b1ebd71-refs/heads/13.2.152@{#1} 
Cr-Branched-From: 6054ba94db0969220be4f94dc1677fc4696bdc4f-refs/heads/main@{#97085}
```

* * *

Files:

  * M `src/base/bounds.h`
  * M `src/wasm/canonical-types.cc`
  * M `src/wasm/canonical-types.h`
  * M `src/wasm/std-object-sizes.h`
  * M `src/wasm/struct-types.h`
  * M `src/wasm/value-type.h`
  * M `src/wasm/wasm-objects.cc`
  * M `test/unittests/wasm/subtyping-unittest.cc`

* * *

Hash: 3fdedec45691a3ab005d62c3295436507e8d277a  
Date: Tue Nov 19 18:17:33 2024

* * *


---

**#31 — pe...@google.com — Nov 27, 2024 07:13PM**

LTS Milestone M126

This issue has been flagged as a merge candidate for Chrome OS' LTS channel. If selected, our merge team will handle any additional merges. To help us determine if this issue requires a merge to LTS, please answer this short questionnaire:

  1. Was this issue a regression for the milestone it was found in?
  2. Is this issue related to a change or feature merged after the latest LTS Milestone?


---

**#32 — ap...@google.com — Nov 27, 2024 08:22PM**

Project: v8/v8  
Branch: refs/branch-heads/13.1  
Author: Clemens Backes <[clemensb@chromium.org](<mailto:clemensb@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6049646](<https://chromium-review.googlesource.com/6049646>)

Merged: [wasm] Remove relative type indexes from canonical types

* * *

Expand for full commit details

```
Merged: [wasm] Remove relative type indexes from canonical types 
 
Those relative types were leaking from the type canonicalizer, which 
leads to type confusion in callers. 
 
This CL fully removes the concept of relative type indexes (and thus 
removes the `CanonicalRelativeField` bit from the bitfield in 
`ValueTypeBase`). During canonicalization we pass the start and end of 
the recursion group into hashing and equality checking, and use this to 
compute relative indexes within the recursion group on demand. The 
stored version will always have absolute indexes though. 
 
R=jkummerow@chromium.org 
 
Bug: 379009132 
(cherry picked from commit 20d9a7f760c018183c836283017a321638b66810) 
 
Change-Id: I8f89186bdd826febbaa57711e6ce4bb29c82e879 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6049646 
Reviewed-by: Jakob Kummerow <jkummerow@chromium.org> 
Commit-Queue: Clemens Backes <clemensb@chromium.org> 
Cr-Commit-Position: refs/branch-heads/13.1@{#24} 
Cr-Branched-From: 7998da66cb2883ef9734743857713b1194212d9a-refs/heads/13.1.201@{#1} 
Cr-Branched-From: 5e9af2a913539cf67091def99b62f49afece6f56-refs/heads/main@{#96554}
```

* * *

Files:

  * M `src/wasm/canonical-types.cc`
  * M `src/wasm/canonical-types.h`
  * M `src/wasm/std-object-sizes.h`
  * M `src/wasm/struct-types.h`
  * M `src/wasm/value-type.h`
  * M `test/unittests/wasm/subtyping-unittest.cc`

* * *

Hash: 0e98fadd4f327a1aec3019fce053da840fa22043  
Date: Wed Nov 27 11:20:22 2024

* * *


---

**#33 — sp...@google.com — Nov 28, 2024 08:58AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $8000.00 for this report.  
  
Rationale for this decision:  
$7,000 for report of memory corruption in the renderer + $1,000 bisect bonus  
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#34 — am...@chromium.org — Nov 28, 2024 09:07AM**

Congratulations! Thank you for your efforts and reporting this issue to us.


---

**#35 — qk...@google.com — Nov 28, 2024 09:15AM**

Labeling as LTS-NotApplicable-126 because the suspected CL[1] was not merged to M126 LTS. So it looks like we don't need to merge the fix to M126 LTS. Additionally, the fix couldn't be merged to M126 because of many conflicts.  
  
[1] [https://chromium-review.googlesource.com/c/v8/v8/+/5890288](<https://chromium-review.googlesource.com/c/v8/v8/+/5890288>)


---

**#36 — li...@gmail.com — Nov 28, 2024 11:33AM**

Thank you very much for your confirmation! This is my first award from Chrome VRP :)


---

**#37 — pg...@google.com — Dec 3, 2024 04:52AM**

Hello, reporter - how would you like to be credited for this report?


---

**#39 — li...@gmail.com — Dec 6, 2024 03:18PM**

Hi, may I ask if my comment [#38](<https://issues.chromium.org/issues/379009132#comment38>) is deleted by the developers for violating any rules, or it's deleted by me accidentally?


---

**#40 — cl...@chromium.org — Dec 6, 2024 05:39PM**

I can't see who removed it and why, but I restored it now.


---

**#41 — ap...@google.com — Jan 9, 2025 10:16PM**

Project: v8/v8  
Branch: main  
Author: Clemens Backes <[clemensb@chromium.org](<mailto:clemensb@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6162737](<https://chromium-review.googlesource.com/6162737>)

[wasm] Add regression tests for relative canonical type indexes

* * *

Expand for full commit details

```
[wasm] Add regression tests for relative canonical type indexes 
 
Add regression tests for four fixed bugs. 
 
Bug: 379009132, 380397544, 381696874, 382291459 
Change-Id: I7b50170a8e462204e1de54698e7c848d190689cd 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6162737 
Reviewed-by: Jakob Kummerow <jkummerow@chromium.org> 
Commit-Queue: Clemens Backes <clemensb@chromium.org> 
Cr-Commit-Position: refs/heads/main@{#98025}
```

* * *

Files:

  * A `test/mjsunit/regress/wasm/regress-379009132.js`
  * A `test/mjsunit/regress/wasm/regress-380397544.js`
  * A `test/mjsunit/regress/wasm/regress-381696874.js`
  * A `test/mjsunit/regress/wasm/regress-382291459.js`

* * *

Hash: ed5cd496163651ad81699424d2b95a77cffc8c32  
Date: Thu Jan 09 13:40:41 2025

* * *


---

**#42 — ch...@google.com — Feb 26, 2025 09:40PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.


---

**#43 — am...@chromium.org — May 6, 2025 03:12AM**

This issue was was discovered as under active ITW exploitation, and reported to us by a third-party as such on 2 May 2025, despite being long since resolved and the fix shipping in Stable Chrome back in December 2024.
