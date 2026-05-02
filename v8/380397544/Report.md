# Arbitrary WASM type confusion due to improper fix of b/379009132

Issue URL: https://issues.chromium.org/issues/380397544
VRP-Reward: 55000
Date: Nov 23, 2024 09:56AM


### VULNERABILITY DETAILS

#### Summary

Arbitrary WASM type confusion due to improper fix of [b/379009132](<https://issues.chromium.org/issues/379009132>) that introduces confusion between recursive group index vs. canonical type index.

#### Details

[b/379009132](<https://issues.chromium.org/issues/379009132>) (or maybe [b/379612177](<https://issues.chromium.org/issues/379612177>)?) points out that the `CanonicalSig` approach taken in [0d15bbf](<https://chromiumdash.appspot.com/commit/0d15bbf1fb92f435e10c14f858d82d4cca851bf4>) is too naive, as it simply exposes and uses the internal types used for canonicalization. This includes recursive-group-based relative type indices which were confused as canonical type indices, resulting in yet another easily exploitable WASM type confusion as demonstrated in [b/380383794](<https://issues.chromium.org/issues/380383794>).

The fix for this, [20d9a7f](<https://chromiumdash.appspot.com/commit/20d9a7f760c018183c836283017a321638b66810>), attempts to solve this by removing the use of recursive group indices in the canonicalized types. The use of recursive group indices are still required for recursive group comparison and thus the canonical indices are converted back to recursive group indices if its index is within the current recursive group index range via [`RecursionGroupRange`](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/canonical-types.h;drc=bf92ca53a7a11f1d82a75aa7fce1040d91db648b;l=171>):

```
  // Define the range of a recursion group; for use in {CanonicalHashing} and
  // {CanonicalEquality}.
  struct RecursionGroupRange {
    const CanonicalTypeIndex first;
    const CanonicalTypeIndex last;

    bool Contains(CanonicalTypeIndex index) const {
      return base::IsInRange(index.index, first.index, last.index);
    }

    CanonicalTypeIndex RelativeIndex(CanonicalTypeIndex index) const {
      return Contains(index)
                 // Make the value_type relative within the recursion group.
                 ? CanonicalTypeIndex{index.index - first.index}
                 : index;
    }

    CanonicalValueType RelativeType(CanonicalValueType type) const {
      return type.has_index()
                 ? CanonicalValueType::FromIndex(
                       type.kind(), RelativeIndex(type.ref_index()))
                 : type;
    }
  };
```

However, this approach is also broken as the notion of relative indices are completely removed from the comparison - (relative) recursive group indices are indistinguishable from (absolute) canonical type indices.

This is quite easily seen in the above code, where the two sides of `RelativeIndex()` ternary operator are immediately indistinguishable as `CanonicalTypeIndex` does not store any information that the index is a recursive group relative index.

Thus, recursive groups refering to completely different types may be canonicalized into the same base index, resulting in arbitrary type confusion between WASM types.

Exploitation with such primitives is trivial and has been presented multiple times. ([Pwn2Own Vancouver 2024](<https://www.zerodayinitiative.com/blog/2024/5/2/cve-2024-2887-a-pwn2own-winning-bug-in-google-chrome>), [TyphoonPWN 2024](<https://ssd-disclosure.com/ssd-advisory-google-chrome-rce/>), [v8CTF submission 8d4d57cb2258](<https://issuetracker.google.com/issues/347145602>), ...)

#### Bisect

Bug introduced by commit [20d9a7f](<https://chromiumdash.appspot.com/commit/20d9a7f760c018183c836283017a321638b66810>) in M133 that attempts to fix [b/379009132](<https://issues.chromium.org/issues/379009132>) by removing relative indices from canonical types.

### VERSION

See bisect commit release info in Chromium Dash for more info: [https://chromiumdash.appspot.com/commit/20d9a7f760c018183c836283017a321638b66810](<https://chromiumdash.appspot.com/commit/20d9a7f760c018183c836283017a321638b66810>)

Chrome Version: 133.0.6848.0 ~ latest  
Operating System: All

### REPRODUCTION CASE

Attached as `poc.js` which exploits the type confusion to obtain in-sandbox exploit primitives, and crashes on arbitrary caged write attempt.

Also attached is yet another full exploit `exp.html` that pops `calc` on Windows x64 Chrome, tested against Canary 133.0.6853.0.

### FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION

Type of crash: Renderer  
Crash State: Crashes on arbitrary caged write attempt from JIT-compiled Wasm function (on d8, `poc.js`), arbitrary code execution (on Chrome, `exp.html`)

### CREDIT INFORMATION

Reporter credit: Seunghyun Lee (@0x10n) of CMU CyLab


---

**#2 — cl...@appspot.gserviceaccount.com — Nov 26, 2024 06:49AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=4669250304147456](<https://clusterfuzz.com/testcase?key=4669250304147456>).


---

**#3 — am...@chromium.org — Nov 26, 2024 06:51AM**

Thanks for the report, Seunghuyun. I've uploaded the testcase to clusterfuzz, but am going to also ship this over to clemensb@ as owner since he landed the fix for [crbug/379009132](<https://crbug.com/379009132>) to look at this sooner than later since that fix has not yet been backmerged.


---

**#4 — 24...@project.gserviceaccount.com — Nov 26, 2024 07:19AM**

ClusterFuzz testcase 4669250304147456 appears to be flaky, updating reproducibility hotlist.


---

**#5 — se...@gmail.com — Nov 26, 2024 07:31AM**

If the fix for [b/379009132](<https://issues.chromium.org/issues/379009132>) can be backmerged for tomorrow's M131 release, it might be better if the fix is backmerged and the fix for this is backmerged later on - function types in Wasm recursion groups are completely broken in its current state on M131, and that fix makes things a bit less broken. I'm even surprised that the bug is not wreaking havoc in prod, I can easily imagine real-world Wasm code that has all types within a large recursion group which will break all exported/imported Wasm functions using module-defined types in its signature?

Regarding CF I have absolutely no idea why it's flaky, there should be no non-determinism in theory.


---

**#6 — cl...@chromium.org — Nov 26, 2024 04:08PM**

Thanks for this report, I agree that it's pretty obviously broken. I am also slightly embarrassed :/

As always, it's concerning that we do not have good fuzzer for these bugs.

I'll cook up a fix.


---

**#7 — ap...@google.com — Nov 26, 2024 09:28PM**

Project: v8/v8  
Branch: main  
Author: Clemens Backes <[clemensb@chromium.org](<mailto:clemensb@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6048961](<https://chromium-review.googlesource.com/6048961>)

[wasm] Fix comparison of relative type indexes

* * *

Expand for full commit details

```
[wasm] Fix comparison of relative type indexes 
 
Compare relative type indexes more explicitly to avoid confusing them 
with absolute indexes. 
 
Drive-by: Move two hash_value functions into the respecitive class. 
 
R=jkummerow@chromium.org 
 
Fixed: 380397544 
Change-Id: I2895bac22c6ace6655c9b41ccc8e18be7c609aa8 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6048961 
Reviewed-by: Jakob Kummerow <jkummerow@chromium.org> 
Commit-Queue: Clemens Backes <clemensb@chromium.org> 
Cr-Commit-Position: refs/heads/main@{#97408}
```

* * *

Files:

  * M `src/wasm/canonical-types.h`
  * M `src/wasm/value-type.h`

* * *

Hash: 0f2e4bf2b22ee367a02c9bc6b7ab26a1f4411f5d  
Date: Tue Nov 26 11:40:50 2024

* * *


---

**#8 — cl...@chromium.org — Nov 26, 2024 09:43PM**

This obviously has no Canary coverage yet, but we should also merge it to M-131 and M-132 once it has it (and before Friday, so it can be included in next week's release).


---

**#9 — se...@gmail.com — Nov 26, 2024 09:55PM**

Re #6: FYI, my simple testcase mutation script that I've been working on did hit that bug ([b/379009132](<https://issues.chromium.org/issues/379009132>)) - it was just that the bug triggered and broke every mutated testcases, and I only recently triaged it to find out that it wasn't my mutations that were broken but the actual code... It's hard (or rather just too laborious) to determine whether a test failure is due to a potential bug, or just that my mutations aren't complete enough to preserve code semantics. Anyways, hope I can at some point demonstrate this :)


---

**#10 — pe...@google.com — Nov 27, 2024 12:39AM**

Setting milestone because of s0/s1 severity.


---

**#11 — pe...@google.com — Nov 27, 2024 09:31PM**

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

**#12 — pe...@google.com — Nov 27, 2024 09:31PM**

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

**#13 — cl...@chromium.org — Nov 28, 2024 12:52AM**

1. Why does your merge fit within the merge criteria for these milestones?

Fixes a security vulnerability that was introduced by another fix (for [https://crbug.com/379009132](<https://crbug.com/379009132>)). Since that fix is backmerged to M-131 and M-132, also this follow-up fix will need to be backmerged.

  2. What changes specifically would you like to merge? Please link to Gerrit.

[https://crrev.com/c/6048961](<https://crrev.com/c/6048961>)

  3. Have the changes been released and tested on canary?

Yes, since 133.0.6862.0.

  4. Is this a new feature? If yes, is it behind a Finch flag and are experiments active in any release channels?

Not a new feature.

  5. [Chrome OS only]: Was the change reviewed and approved by the Eng Prod Representative? [https://goto.google.com/cros-engprodcomponents](<https://goto.google.com/cros-engprodcomponents>)

n/a

  6. If this merge addresses a major issue in the stable channel, does it require manual verification by the test team? If so, please describe required testing.

No manual testing required.


---

**#14 — sp...@google.com — Nov 28, 2024 09:55AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $55000.00 for this report.  
  
Rationale for this decision:  
high quality report of demonstrated RCE in a sandboxed process / the renderer   
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#15 — am...@chromium.org — Nov 28, 2024 10:00AM**

Congratulations Seunghyun! Thank you for your efforts and reporting this issue to us -- great work!


---

**#16 — am...@chromium.org — Nov 28, 2024 11:44AM**

[https://crrev.com/c/6048961](<https://crrev.com/c/6048961>) has had just over 36 hours of bake time on canary; I'm not seeing any issues and looking at the fix I'm going to go ahead and approve merge to M131 Stable and M132 Beta. Since the turnaround on this is rather short and we're back merging to Stable, please double-check to confirm there's been no new issues before merging. Once confirmed, please proceed with merging to 13.1 and 13.2 by EOD Friday so this can be in next week's updates.


---

**#17 — cl...@chromium.org — Nov 28, 2024 08:32PM**

Thanks, I checked for crashes again and did some manual testing of web pages known to use Wasm. It's all looking good, so I'll prepare the merges.


---

**#18 — ap...@google.com — Nov 29, 2024 12:29AM**

Project: v8/v8  
Branch: refs/branch-heads/13.2  
Author: Clemens Backes <[clemensb@chromium.org](<mailto:clemensb@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6054730](<https://chromium-review.googlesource.com/6054730>)

Merged: [wasm] Fix comparison of relative type indexes

* * *

Expand for full commit details

```
Merged: [wasm] Fix comparison of relative type indexes 
 
Compare relative type indexes more explicitly to avoid confusing them 
with absolute indexes. 
 
Drive-by: Move two hash_value functions into the respecitive class. 
 
R=jkummerow@chromium.org 
 
Bug: 380397544 
(cherry picked from commit 0f2e4bf2b22ee367a02c9bc6b7ab26a1f4411f5d) 
 
Change-Id: I9f898237a256ae32974ed23ab506ed0571ce93cd 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6054730 
Commit-Queue: Clemens Backes <clemensb@chromium.org> 
Reviewed-by: Jakob Kummerow <jkummerow@chromium.org> 
Cr-Commit-Position: refs/branch-heads/13.2@{#26} 
Cr-Branched-From: 24068c59cedad9ee976ddc05431f5f497b1ebd71-refs/heads/13.2.152@{#1} 
Cr-Branched-From: 6054ba94db0969220be4f94dc1677fc4696bdc4f-refs/heads/main@{#97085}
```

* * *

Files:

  * M `src/wasm/canonical-types.h`
  * M `src/wasm/value-type.h`

* * *

Hash: 66e97acee84487c8009e467c06828211f95725a9  
Date: Thu Nov 28 15:54:20 2024

* * *


---

**#19 — ap...@google.com — Nov 29, 2024 12:31AM**

Project: v8/v8  
Branch: refs/branch-heads/13.1  
Author: Clemens Backes <[clemensb@chromium.org](<mailto:clemensb@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6054989](<https://chromium-review.googlesource.com/6054989>)

Merged: [wasm] Fix comparison of relative type indexes

* * *

Expand for full commit details

```
Merged: [wasm] Fix comparison of relative type indexes 
 
Compare relative type indexes more explicitly to avoid confusing them 
with absolute indexes. 
 
Drive-by: Move two hash_value functions into the respecitive class. 
 
R=jkummerow@chromium.org 
 
Bug: 380397544 
(cherry picked from commit 0f2e4bf2b22ee367a02c9bc6b7ab26a1f4411f5d) 
 
Change-Id: I36973618d62c10588da59135933979dca808e4b7 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6054989 
Commit-Queue: Clemens Backes <clemensb@chromium.org> 
Reviewed-by: Jakob Kummerow <jkummerow@chromium.org> 
Cr-Commit-Position: refs/branch-heads/13.1@{#28} 
Cr-Branched-From: 7998da66cb2883ef9734743857713b1194212d9a-refs/heads/13.1.201@{#1} 
Cr-Branched-From: 5e9af2a913539cf67091def99b62f49afece6f56-refs/heads/main@{#96554}
```

* * *

Files:

  * M `src/wasm/canonical-types.h`
  * M `src/wasm/value-type.h`

* * *

Hash: a4a402d30ad3544e98f0dcf1c8dee0c9bd1402a3  
Date: Thu Nov 28 15:55:37 2024

* * *


---

**#20 — ap...@google.com — Nov 29, 2024 12:32AM**

Project: v8/v8  
Branch: main  
Author: Clemens Backes <[clemensb@chromium.org](<mailto:clemensb@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6055121](<https://chromium-review.googlesource.com/6055121>)

[wasm] Fix typo in hashing

* * *

Expand for full commit details

```
[wasm] Fix typo in hashing 
 
We were producing suboptimal hashes by using a boolean operator instead 
of a bitwise operator. 
 
R=jkummerow@chromium.org 
 
Bug: 380397544 
Change-Id: Ifda2ff082dcd1fc7d34afa974d1e440951019488 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6055121 
Reviewed-by: Jakob Kummerow <jkummerow@chromium.org> 
Commit-Queue: Clemens Backes <clemensb@chromium.org> 
Cr-Commit-Position: refs/heads/main@{#97471}
```

* * *

Files:

  * M `src/wasm/canonical-types.h`

* * *

Hash: 592f1915dbe12bf8d6abf680e2ba029e23eeed4b  
Date: Thu Nov 28 15:58:16 2024

* * *


---

**#21 — pe...@google.com — Nov 29, 2024 12:43AM**

LTS Milestone M126

This issue has been flagged as a merge candidate for Chrome OS' LTS channel. If selected, our merge team will handle any additional merges. To help us determine if this issue requires a merge to LTS, please answer this short questionnaire:

  1. Was this issue a regression for the milestone it was found in?
  2. Is this issue related to a change or feature merged after the latest LTS Milestone?


---

**#22 — qk...@google.com — Nov 29, 2024 05:27PM**

Labeling as LTS-NotApplicable-126 because the improper fix[1] of the bug(([b/379009132](<https://issues.chromium.org/issues/379009132>)) was not merged to M126 LTS. So it looks like we don't need to merge the new fix[1] to M126 LTS.  
  
[1] [https://chromium-review.googlesource.com/c/v8/v8/+/6048961](<https://chromium-review.googlesource.com/c/v8/v8/+/6048961>)


---

**#23 — se...@gmail.com — Dec 2, 2024 12:40PM**

The fix revealed to be broken again - see [b/381696874](<https://issues.chromium.org/issues/381696874>). The bug is simple, but triggering it is harder (and likely much harder for fuzzers) due to hash collision constraint.


---

**#24 — se...@gmail.com — Dec 6, 2024 02:27AM**

Re [comment#14](<https://issues.chromium.org/issues/380397544#comment14>): Thanks! I would like to donate the reward as done with my recent previous reports.


---

**#25 — ap...@google.com — Jan 9, 2025 10:16PM**

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

**#26 — ch...@google.com — Mar 11, 2025 09:41PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
