# Arbitrary Wasm type confusion due to transient canonical index truncation (integer overflow)

Issue URL: https://issues.chromium.org/issues/400086889
VRP-Reward: 62000
Date: Mar 2, 2025 09:39AM


### VULNERABILITY DETAILS

> Disclaimer: This bug is a regression introduced by a 3-day old commit [44171ac](<https://chromium-review.googlesource.com/c/v8/v8/+/6288535>). WasmGC fuzzers, under certain constraints, may be able to reach this bug as a `DCHECK()` due to failed `BitField::is_valid()` checks. Considering how this is a regression of what I've already pointed out in the past ([b/381696874#comment11](<https://issues.chromium.org/issues/381696874#comment11>)), I'm reporting it within the 7-day "grace period".

#### Summary

Arbitrary Wasm type confusion due to removed security-sensitive `CHECK()` at type canonicalization. `TypeCanonicalizer::CanonicalizeTypeDef()` can transiently generate a canonical index of over `kMaxCanonicalTypes` while requesting type canonicalization for a potentially new recursive group. This can result in type index truncation during `CanonicalEquality` check and a subsequent type confusion.

#### Details

`TypeCanonicalizer::CanonicalizeTypeDef()` canonicalizes types using a base index assuming a new recursion group type. **At this step relative indices can be canonicalized into absolute indices that overflow the`kMaxCanonicalTypes` limit**, since `CheckMaxCanonicalIndex()` is triggered only when the recursion group is confirmed to be new.

Prior to [44171ac](<https://chromium-review.googlesource.com/c/v8/v8/+/6288535>) this was implicitly prevented from causing security issues due to [`CHECK_LT() at CanonicalValueType::FromIndex()`](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/value-type.h;l=1073;drc=58fb75d86a0ad2642beec2d6c16b1e6c008e33cd>) which has also been pointed out in my previous reports as a _huge load-bearing check_ ([b/381696874#comment11](<https://issues.chromium.org/issues/381696874#comment11>)). The refactoring however removed the check, now enabling the transient overflow to not immediately result in a crash. On subsequent `CanonicalEquality` check this leads to type index truncation for indices larger than 20bits:

```
// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/canonical-types.h;drc=44171ac91e6a61c22ea8256ea8804b3955e4b5db;l=342
    bool EqualValueType(CanonicalValueType type1,
                        CanonicalValueType type2) const {
      const bool indexed = type1.has_index();
      if (indexed != type2.has_index()) return false;
      if (indexed) {
        return EqualTypeIndex(type1.ref_index(), type2.ref_index());
      }
      return type1 == type2;
    }

// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/value-type.h;drc=30200e13ddec41e3ea341c49ed1dff1878c743bd;l=1009
  constexpr CanonicalTypeIndex ref_index() const {
    return CanonicalTypeIndex{raw_index()};
  }

// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/value-type.h;drc=30200e13ddec41e3ea341c49ed1dff1878c743bd;l=689
  constexpr TypeIndex raw_index() const {
    DCHECK(has_index());
    return TypeIndex(value_type_impl::PayloadField::decode(bit_field_));         // [!] 20 bits
  }
```

This results in broken recursion group equality checks for recursion groups that transiently cross the `kMaxCanonicalTypes` boundary, potentially leading to two different recursion groups to be canonicalized into the same canonical index.

#### Exploitation

Canonicalization equality bugs have frequently been observed in the past - [b/380397544](<https://issues.chromium.org/issues/380397544>), [b/381696874](<https://issues.chromium.org/issues/381696874>), [b/382291459](<https://issues.chromium.org/issues/382291459>), etc. Again, as previously seen in the latter two reports this requires finding a hash collision to trigger the bug.

The bug gives us the primitive to cause a confusion between references to either an absolute reference of canonical index `N` vs. relative reference of canonical index `0x100000 + N` since the latter will be truncated into the former. Unfortunately in this case we cannot naively use birthday attack as we are not finding a hash collision between two groups with arbitrarily chosen sequence of pairs. Instead, we wish to find a specific sequence of pairs such that its hash value collides with its corresponding same-length sequence which has all of the indices truncated - thus, requiring a preimage attack against the latter hash value by only using the two pairs.

We make the following observations:

  * Even with a limited character set (of size 2, since we can choose either `N` or `0x100000 + N`) it is still theoretically possible to find a 64bit hash collision 
    * With 64 choices we have 2^64 hashes, which results in `1-(1-1/2^64)^(2^64) ~ 1-1/e ~ 63%` chance of finding a collision
    * This process can be repeated until we actually find one, e.g. with different leading prefix of struct fields, etc.
  * Under a chosen recursion group structure, we already know the target hash value to collide with 
    * ...which is just the hash value of the same structure but with all references to `0x100000 + N` replaced with `N`
  * **Thus, we can launch a meet-in-the-middle attack** , where for 64 choices: 
    * We generate 2^32 hash values by hashing up to first 32 choices, i.e. "forward hash values"
    * We generate 2^32 hash values by **inverting hash computation from the final target hash value until we have last 32 choices inverted** , i.e. "backward hash values" - MurmurHash64A allows us to do this!
    * Find a collision pair between the two 2^32 hash values, where the 32+32 choices together give us the preimage

Thus it is computationally feasible to find a hash collision.

The attached PoC has a precomputed hash-colliding recursion group that includes a struct type that uses either:

  * `ref null $abs`, where `$abs` is an absolute reference to canonical index `N`
  * `ref null $rel`, where `$rel` is a relative reference to canonical index `0x100000 + N`

...for its 64 fields types (excluding chosen prefix). This will hash into the same value with the same recursion group, but with all `ref null $rel` replaced with `ref null $abs`.

#### Bisect

Bug introduced by [44171ac](<https://chromium-review.googlesource.com/c/v8/v8/+/6288535>) that refactors `ValueType`.

### VERSION

Affects ToT.

Chrome Version: 135.0.7039.0 (Canary) ~  
Operating System: All

### REPRODUCTION CASE

Attached as `poc.js` which exploits the hash collision + type confusion to obtain in-sandbox exploit primitives, and then crashes on arbitrary caged write attempt.

Repro tested on [f5fba01](<https://chromium-review.googlesource.com/c/v8/v8/+/6306966>).

### FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION

Type of crash: Renderer  
Crash State: Crashes on arbitrary caged write attempt from JIT-compiled Wasm function (on d8, `poc.js`)

### CREDIT INFORMATION

Reporter credit: Seunghyun Lee (@0x10n) of CMU CyLab


---

**#2 — cl...@appspot.gserviceaccount.com — Mar 4, 2025 03:33AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=6522889301852160](<https://clusterfuzz.com/testcase?key=6522889301852160>).


---

**#3 — se...@gmail.com — Mar 4, 2025 04:22AM**

Re [comment#2](<https://issues.chromium.org/issues/400086889#comment2>): ClusterFuzz might need a bit more time due to repro creating a total of over 1000000 Wasm types. Locally it reproduces within 2s on the exact same build.


---

**#4 — cl...@appspot.gserviceaccount.com — Mar 4, 2025 04:24AM**

Detailed Report: [https://clusterfuzz.com/testcase?key=5277614771994624](<https://clusterfuzz.com/testcase?key=5277614771994624>)  
  
Fuzzer: None  
Job Type: linux_asan_d8_dbg  
Platform Id: linux  
  
Crash Type: DCHECK failure  
Crash Address:   
Crash State:  
is_valid(value) in bit-field.h  
v8::internal::wasm::TypeCanonicalizer::CanonicalizeTypeDef  
v8::internal::wasm::TypeCanonicalizer::AddRecursiveGroup  
  
Sanitizer: address (ASAN)  
  
Crash Revision: [https://clusterfuzz.com/revisions?job=linux_asan_d8_dbg&revision=99039](<https://clusterfuzz.com/revisions?job=linux_asan_d8_dbg&revision=99039>)  
  
Reproducer Testcase: [https://clusterfuzz.com/download?testcase_id=5277614771994624](<https://clusterfuzz.com/download?testcase_id=5277614771994624>)  
  
To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.   
  
If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.  
  
If you have any feedback on reproducing test cases, let us know at [https://forms.gle/Yh3qCYFveHj6E5jz5](<https://forms.gle/Yh3qCYFveHj6E5jz5>) so we can improve.


---

**#5 — am...@chromium.org — Mar 4, 2025 04:28AM**

This reproduced a bit more succinctly using a d8 dbg build and using --allow-natives-syntax


---

**#6 — jk...@chromium.org — Mar 4, 2025 05:07AM**

Thanks for the report! Excellent work, as usual. I was wondering where I might have screwed up in that large refactoring...

Fix: [https://chromium-review.googlesource.com/c/v8/v8/+/6316677](<https://chromium-review.googlesource.com/c/v8/v8/+/6316677>)


---

**#7 — se...@gmail.com — Mar 4, 2025 05:57AM**

A full exploit that runs `cat /etc/passwd`, tested exclusively on Linux Chrome for Testing 135.0.7047.0 (r1426902). V8sbx bypass part uses JSPI ([b/384553540](<https://issues.chromium.org/issues/384553540>)), so running the exploit on the exact same Chrome version with `./chrome --no-sandbox --enable-features=WebAssemblyExperimentalJSPI` will work.


---

**#8 — se...@gmail.com — Mar 4, 2025 06:04AM**

Re [comment#6](<https://issues.chromium.org/issues/400086889#comment6>): I'm sure that any future works will eventually reveal this issue too, but in the current state canonicalized reference fields do not have `IsSharedField` and `RefTypeKindField` initialized due to how type section first decodes the types & canonicalizes it, and then update the problematic fields only at second step. This might cause problems later on if any code decides to use the fields from canonicalized types, most likely with canonicalized signatures. Not sure if there's any problem in its current state though.


---

**#9 — ap...@google.com — Mar 4, 2025 06:45PM**

Project: v8/v8  
Branch: main  
Author: Jakob Kummerow <[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6316677](<https://chromium-review.googlesource.com/6316677>)

[wasm] Restore lost CHECK for max canonical type index

* * *

Expand for full commit details

```
[wasm] Restore lost CHECK for max canonical type index 
 
Follow-up to crrev.com/c/6288535 
 
Fixed: 400086889 
Change-Id: I6dd74e532419e6b31cbb13d3cfd26deda0f3fe85 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6316677 
Auto-Submit: Jakob Kummerow <jkummerow@chromium.org> 
Reviewed-by: Matthias Liedtke <mliedtke@chromium.org> 
Commit-Queue: Matthias Liedtke <mliedtke@chromium.org> 
Cr-Commit-Position: refs/heads/main@{#99046}
```

* * *

Files:

  * M `src/wasm/canonical-types.cc`
  * M `src/wasm/canonical-types.h`
  * M `src/wasm/value-type.h`

* * *

Hash: 700e9d09e4c916e7ea510b85f53e95e1f5ea2f93  
Date: Mon Mar 03 21:05:35 2025

* * *


---

**#10 — ch...@google.com — Mar 4, 2025 09:37PM**

Setting milestone because of s0/s1 severity.


---

**#11 — jk...@chromium.org — Mar 5, 2025 12:18AM**

Re #8: Good observation. The implementation of shared types is incomplete in a few places; that particular bit seems easy enough to fix right away.


---

**#12 — ch...@google.com — Mar 5, 2025 09:53PM**

Security Merge Request Consideration: This is sufficiently serious that it should be merged to dev. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M135. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately. **Merge approved:** your change passed merge requirements and is auto-approved for M135. Please go ahead and merge the CL to branch 7049 (refs/branch-heads/7049) manually. Please contact milestone owner if you have questions. Merge instructions: [https://chromium.googlesource.com/chromium/src.git/+/refs/heads/main/docs/process/merge_request.md](<https://chromium.googlesource.com/chromium/src.git/+/refs/heads/main/docs/process/merge_request.md>) Owners: alonbajayo (ChromeOS), pbommana (Desktop US), danielyip (Desktop EMEA), harrysouders (Mobile US), eakpobaro (Mobile EMEA) Security Merge Request: Thank you for fixing this security bug! We aim to ship security fixes as quickly as possible, to limit their opportunity for exploitation as an "n-day" (that is, a bug where git fixes are developed into attacks before those fixes reach users).

We have determined this fix is necessary on milestone(s): [135].

Please answer the following questions so that we can safely process this merge request:

  1. Which CLs should be backmerged? (Please include Gerrit links.)
  2. Has this fix been verified on Canary to not pose any stability regressions?
  3. Does this fix pose any potential non-verifiable stability risks?
  4. Does this fix pose any known compatibility risks?
  5. Does it require manual verification by the test team? If so, please describe required testing.
  6. (no answer required) Please check the OS custom field to ensure all impacted OSes are checked!


---

**#13 — ap...@google.com — Mar 6, 2025 12:19AM**

Project: v8/v8  
Branch: refs/branch-heads/13.5  
Author: Jakob Kummerow <[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6328302](<https://chromium-review.googlesource.com/6328302>)

Merged: [wasm] Restore lost CHECK for max canonical type index

* * *

Expand for full commit details

```
Merged: [wasm] Restore lost CHECK for max canonical type index 
 
Follow-up to crrev.com/c/6288535 
 
Fixed: 400086889 
(cherry picked from commit 700e9d09e4c916e7ea510b85f53e95e1f5ea2f93) 
 
Change-Id: Ia73b2a2994244d8219317dbee5f150c1f76b1ac4 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6328302 
Commit-Queue: Jakob Kummerow <jkummerow@chromium.org> 
Commit-Queue: Matthias Liedtke <mliedtke@chromium.org> 
Reviewed-by: Matthias Liedtke <mliedtke@chromium.org> 
Auto-Submit: Jakob Kummerow <jkummerow@chromium.org> 
Cr-Commit-Position: refs/branch-heads/13.5@{#2} 
Cr-Branched-From: c206c46cd0bd65b02e85abe5965d82e4beb7d453-refs/heads/13.5.212@{#1} 
Cr-Branched-From: af3cadca9bd27c08733f1635b554e8721a342668-refs/heads/main@{#99020}
```

* * *

Files:

  * M `src/wasm/canonical-types.cc`
  * M `src/wasm/canonical-types.h`
  * M `src/wasm/value-type.h`

* * *

Hash: 0b64e78f4158df523e5db03232c531257ccbbb71  
Date: Mon Mar 03 21:05:35 2025

* * *


---

**#14 — pe...@google.com — Mar 6, 2025 12:28AM**

LTS Milestone M132

This issue has been flagged as a merge candidate for Chrome OS' LTS channel. If selected, our merge team will handle any additional merges. To help us determine if this issue requires a merge to LTS, please answer this short questionnaire:

  1. Was this issue a regression for the milestone it was found in?
  2. Is this issue related to a change or feature merged after the latest LTS Milestone?


---

**#15 — jk...@chromium.org — Mar 6, 2025 01:17AM**

#14: M132 is not affected. (So yes, it was an M135 regression.)

#12: No further merges are necessary.


---

**#16 — qk...@google.com — Mar 6, 2025 10:00AM**

Labelling as not applicable for LTS 132 and LTS 126, because the suspected CL[1] isn't present in M132/M126 and [comment #15](<https://issues.chromium.org/issues/400086889#comment15>) said it was an M135 regression.  
  
[1] [https://chromium-review.googlesource.com/c/v8/v8/+/6288535](<https://chromium-review.googlesource.com/c/v8/v8/+/6288535>)


---

**#17 — se...@gmail.com — Mar 8, 2025 04:39AM**

Re #11: Wait, if I'm looking at this correctly [https://chromium-review.googlesource.com/c/v8/v8/+/6322473](<https://chromium-review.googlesource.com/c/v8/v8/+/6322473>) introduces a different vulnerability - canonical ids are needed to properly check `ValidSubtypeDefinition(...)`, but type canonicalization `type_canon->AddRecursiveGroup(...)` is now done after that. **This will result in any references within the same recursion group to canonicalize into the default value of`0` while checking subtype validity**. We've already resized `isorecursive_canonical_type_ids` so we won't even hit `DCHECK`s in `WasmModule::canonical_type_id()` and all subtype declarations will be accepted regardless of its reference fields' validity, i.e. this is really bad.


---

**#18 — jk...@chromium.org — Mar 8, 2025 06:47AM**

#17: Oops. Nice catch!

I'm shocked that we don't have a test case that would cover this.


---

**#19 — ch...@google.com — Mar 8, 2025 09:34PM**

This is a serious security regression. If you are not able to fix this quickly, please revert the change that introduced it.

If this doesn't affect a release branch, or has not been properly classified for severity, please update the Security Impact hotlist or the Severity field, and remove the ReleaseBlock hotlist.


---

**#20 — ap...@google.com — Mar 11, 2025 01:00AM**

Project: v8/v8  
Branch: main  
Author: Jakob Kummerow <[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6338547](<https://chromium-review.googlesource.com/6338547>)

[wasm] Fix recent type decoding fix

* * *

Expand for full commit details

```
[wasm] Fix recent type decoding fix 
 
crrev.com/c/6322473, while fixing one bug, introduced another; this 
follow-up fixes that. 
And it adds a bunch of tests for invalid subtypes. 
 
Bug: 400086889 
Change-Id: Iafddd4e5d92d2c76166239ec77c92283e1010d17 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6338547 
Auto-Submit: Jakob Kummerow <jkummerow@chromium.org> 
Commit-Queue: Jakob Kummerow <jkummerow@chromium.org> 
Reviewed-by: Matthias Liedtke <mliedtke@chromium.org> 
Commit-Queue: Matthias Liedtke <mliedtke@chromium.org> 
Cr-Commit-Position: refs/heads/main@{#99153}
```

* * *

Files:

  * M `src/wasm/module-decoder-impl.h`
  * A `test/mjsunit/wasm/subtyping-invalid.js`
  * M `tools/testrunner/local/variants.py`

* * *

Hash: 14a86378da47099bf9ee3e10528b73be11214ed8  
Date: Mon Mar 10 16:26:51 2025

* * *


---

**#21 — jk...@chromium.org — Mar 11, 2025 01:12AM**

We'll have to backmerge #20 as well.


---

**#22 — jk...@chromium.org — Mar 11, 2025 08:35PM**

Oh, I was confused. [https://chromium-review.googlesource.com/c/v8/v8/+/6322473](<https://chromium-review.googlesource.com/c/v8/v8/+/6322473>) never made it to 135, so its follow-up [https://chromium-review.googlesource.com/6338547](<https://chromium-review.googlesource.com/6338547>) doesn't need to get merged.


---

**#23 — sp...@google.com — Mar 21, 2025 10:55AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $62000.00 for this report.  
  
Rationale for this decision:  
$55,000 for report demonstrating RCE in a sandboxed process / the renderer + $7,000 for renderer memory corruption reward / bonus for identifying that the planned fix introduces a new vulnerability   
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#24 — am...@chromium.org — Mar 21, 2025 11:00AM**

Congratulations Seunghyun! Thank you for another excellent report of V8 in-sandbox renderer RCE and also for the amazing catch that the fix would introduce a new vulnerability. Thank for your excellent efforts here -- great work!


---

**#25 — ch...@google.com — Jun 17, 2025 09:39PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
