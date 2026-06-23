# Wasm type confusion due to spec unsoundness in `cast_desc` operations

Issue URL: https://issues.chromium.org/issues/446113732
VRP-Reward: 55000
Date: Sep 19, 2025 10:58PM


...and a nail in the coffin for the custom descriptors proposal.

## README

This is a Wasm spec-level unsoundness issue. Any runtime implementing the same spec faithfully will have the same bug. I am reporting this privately to Google Chrome/V8 as Google seems to be leading the spec work and implementation of custom descriptors the first and practically has the most affected users in the wild.

As this is a spec-level unsoundness which the Wasm community needs to know, I believe that the issue necessitates a quicker disclosure deadline than what is enforced by default by Chrome's disclosure policies. **It would be great if we can coordinate the disclosure within a week from the reported date** \- please contact me through email or through the comments. Unless otherwise coordinated, **the spec unsoundness issue is subject to a 14-day disclosure deadline after which the issue, without any specific mentions of Chrome/V8, will be disclosed publicly** on [https://github.com/WebAssembly/custom-descriptors/issues](<https://github.com/WebAssembly/custom-descriptors/issues>). The Chrome/V8 security team is allowed to responsibly disclose this to other vendors and personnel involved in WebAssembly work (at CG meetings or whatnot) under the conditions that 1. the reporter is credited, and 2. is given at least a day's advance notice.

### VULNERABILITY DETAILS

#### Summary

Wasm type confusion due to fundamental spec unsoundness in custom descriptors. Described structs may be unrelated but have descriptors in subtyping relationship, where the descriptors' subtype relationship may be used to unsoundly cast between the described structs using `ref.cast_desc` or `br_on_cast_desc*`.

Custom descriptors feature is exposed in the wild by default through Origin Trials from M141, which is currently at Beta and very soon reaches (Early) Stable. This bug is not caused by a recent code change and has existed from the very first feature implementation (approx. 6 months) due to an inherent spec unsoundness.

> Note: Since the custom descriptors spec itself is unsound, discussing about other implementation bugs may be pointless. However, each and every one of the bugs that I've reported are independent and triggers even without `cast_desc`.

#### Details

WebAssembly Custom Descriptors proposal introduces descriptors and [descriptor-based type checks](<https://github.com/WebAssembly/custom-descriptors/blob/main/proposals/custom-descriptors/Overview.md#new-instructions>). These casts/checks require that the described struct has a descriptor that matches the given descriptor at runtime. By spec definition, these operations allow subtype descriptors. Take for example `ref.cast_desc`:

```
ref.cast_desc reftype

C |- ref.cast_desc rt : (ref null ht) (ref null (exact_1 y)) -> rt
-- rt = (ref null? (exact_1 x))
-- C |- C.types[x] <: ht
-- C.types[x] ~ descriptor y ct
```

In the above rule:

  * Descriptor on the stack is allowed to be any subtype of `(ref null (exact_1 y))`, the descriptor type of `rt`.
  * `ht` may also be chosen as `any`, allowing any references within the `anyref` hierarchy to be casted through this operation even without a direct subtype relationship between `rt`, the described type, given that the descriptor actually matches.

Let us revisit [subtyping rules on custom descriptors](<https://github.com/WebAssembly/custom-descriptors/blob/main/proposals/custom-descriptors/Overview.md#custom-descriptor-definitions>):

  * A declared supertype of a type with a `(descriptor $x)` clause must either not have a `descriptor` clause or have a `(descriptor $y)` clause, where `$y` is a declared supertype of `$x`.
  * A declared supertype of a type without a `descriptor` clause must also not have a `descriptor` clause.
  * **A declared supertype of a type with a`describes` clause must have a `describes` clause.**
  * **A declared supertype of a type without a`describes` clause must also not have a `describes` clause.**
  * With shared-everything-threads, ... (omitted)

...additionally with the following type validation rule:

  * **Descriptor and describes clauses must agree** , i.e. a describing type must have a describes clause referring to its described type, which in turn must have a descriptor clause referring to the describing type.

Note how `describes` clause are not subject to subtyping. Thus, a type definition as shown below is perfectly legal:

```
(rec
  (type $sup (sub (descriptor $sup.rtt (struct (field $sup-only i32)))))
  (type $sup.rtt (sub (describes $sup (struct))))

  (type $sub (sub (descriptor $sub.rtt (struct))))
  (type $sub.rtt (sub $sup.rtt (describes $sub (struct))))
)
```

We do not declare `$sub <: $sup` nor enforce it transitively through `$sub.rtt <: $sup.rtt` \-- `$sub` and `$sup` are unrelated. The spec also explicitly calls out such cases as legal, although with a broken example (`type $other` in the spec overview which lacks a matching `descriptor`). A non-broken example is in [Issue #29](<https://github.com/WebAssembly/custom-descriptors/pull/29/files#diff-27d9fc2e894c7423d5a93d49317d1d9c238632dec41f3e5ecea0e12ed04d9e44R21-R31>).

Now consider a case where we execute the following:

```
(func $unsound (result i32)
  (local $rtt (ref $sub.rtt))
  ;; Instantiate $sub.rtt => $rtt
  (local.set $rtt (struct.new $sub.rtt))
  ;; Instantiate $sub with $rtt
  (struct.new $sub (local.get $rtt))
  ;; Get $rtt again as the descriptor to compare on cast
  (local.get $rtt)
  ;; Cast $sub to $sup using $rtt. This will succeed because $sub.rtt <: $sup.rtt
  (ref.cast_desc (ref $sup))
  ;; Out-of-bounds read.
  (struct.get $sup $sup-only)
)
```

All of the steps are perfectly legal based on the current custom descriptor spec, but is obviously unsound. Essentially, `ref.cast_desc` as well as any `br_on_cast_desc*` variants transitively applies subtyping relationship of the descriptors to its described struct type. This trivially results in type confusion between unrelated described struct types.

* * *

I am unsure what the spec intends to do here as the formulation is fundamentally broken. Maybe the spec intended to enforce a `describes` declared subtype check in the modified subtyping rules -- but an example in the spec overview explicitly calls out against this idea. Maybe it needs a stricter typecheck against the value on the stack by only allowing subtypes of `rt` (in this case, checking if `(struct.new $sub (local.get $rtt))` is a subtyped object of `ref $sup`) -- but the spec overview explicitly relaxes this in [issue #37](<https://github.com/WebAssembly/custom-descriptors/issues/37>), and even before this `ref.cast_desc` was broken from the start. Either might be a valid fix but with wildly different semantics which I am uncertain what is even intended here.

But another concern is: Are there no formally verified version of this proposal, either through SpecTec or by manual work? What is the spec trying to model with custom descriptors, and what is V8 currently implementing? We got away in [b/365802567](<https://issues.chromium.org/issues/365802567>) by saying that it's just a terminology confict of the term _"match"_ across different proposal spec evolved independently, but in this case the spec is just flat out unsound. I can understand implementations and minor spec revisions being a trial-and-error process, but almost the entirety of the spec being unsound while going all the way through deployment into stable channel (albeit OT) is honestly a bit concerning. Or am I missing something?

#### Bisect

Bug introduced by WebAssembly Custom Descriptors, on Origin Trials from M141 and onwards. More specifically, it is introduced in commit [7cb98588](<https://crrev.com/c/6400936>) which implements `ref.cast_desc`.

### VERSION

Chrome Version: M141~  
Operating System: All

### REPRODUCTION CASE

Attached as `poc.js` which exploits this issue to alias two unrelated struct types, then uses this type confusion to trigger an arbitrary caged write within the sandbox.

Also attached is `rce.html` which exploits this issue, together with the `wrapper-wasmcpt-uaf` v8sbx bypass, to gain RCE and print out `/flag/flag` to stdout.

You might want to pass `--experimental-wasm-custom-descriptors` on d8 or `--enable-blink-features=WebAssemblyCustomDescriptors` on Chrome to simulate Origin Trials behavior.

### FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION

Type of crash: Renderer  
Crash State: Crashes on arbitrary caged write attempt from JIT-compiled Wasm function with `poc.js` / RCE with `rce.html`

### CREDIT INFORMATION

Reporter credit: Seunghyun Lee (@0x10n) of CMU CSD / CyLab


---

**#2 — dr...@chromium.org — Sep 20, 2025 01:55AM**

[security triage] `poc.js` reproduces the segfault in M141. Setting High severity and the corresponding FoundIn. I can't reproduce `rce.html`. I haven't dug too much into it, but I'm running it on a Linux host with just the flag `--enable-blink-features=WebAssemblyCustomDescriptors`. Is there more to it than that?  
  
This feature is still marked as experimental, so we do expect some security bugs at this stage. But given this is a spec unsoundness issue, I'll leave it to the V8 folks to decide how they want to handle visibility here.


---

**#3 — dr...@chromium.org — Sep 20, 2025 01:56AM**

ishell@ - as the current V8 shepherd, can you triage this further?


---

**#4 — dr...@chromium.org — Sep 20, 2025 01:58AM**

> the spec unsoundness issue is subject to a 14-day disclosure deadline after which the issue, without any specific mentions of Chrome/V8, will be disclosed publicly

I do also want to mention that spec issues are generally more complex to resolve than Chrome implementation issues due to the larger number of parties involved, so this timeline is very aggressive.


---

**#5 — is...@chromium.org — Sep 20, 2025 02:05AM**

Wasm folks, could you please help with finding the right owner?


---

**#6 — dr...@chromium.org — Sep 20, 2025 02:11AM**

Because this flag is experimental, it should be Security_Impact-None and classified as a vulnerability (the fact that it's in the spec is immaterial). Sorry for the noise.


---

**#7 — dr...@chromium.org — Sep 20, 2025 02:50AM**

> Bug introduced by WebAssembly Custom Descriptors, on Origin Trials from M141 and onwards

No, actually I was right the first time. This should not still be an experimental flag in V8 if we're shipping to actual users. Since we're in Origin Trial, this is going to actual users. I'll mark this back as FoundIn 141. WASM folks - can you please update the flag definition?

I was also able to reproduce the read of `/flag/flag` with `rce.html` by running `./chrome --enable-blink-features=WebAssemblyCustomDescriptors --no-sandbox b446113732/rce.html`.


---

**#8 — cl...@chromium.org — Sep 20, 2025 03:03AM**

Setting FoundIn 141 because that's when the origin trial started.


---

**#9 — cl...@chromium.org — Sep 20, 2025 03:03AM**

Assigning all these custom descriptor vulnerabilities to Jakob for now.


---

**#10 — se...@gmail.com — Sep 20, 2025 03:36AM**

Re #4: Yes, I understand that this is not in line with Google/Chrome's standard disclosure timeline. The 14-day disclosure deadline is suggested since the longer this spec is kept in an unsound state, the more work of any individuals and vendors working on implementing this gets redundant and would eventually need more work fixing up. The problem is that I do not know who is looking at the spec other than the generic "WebAssembly Community Group", and it is uncertain whether or not disclosing this to [1749 members of the CG](<https://www.w3.org/community/webassembly/participants>) is better than working on a solution transparently and publicly at [https://github.com/WebAssembly/custom-descriptors/issues](<https://github.com/WebAssembly/custom-descriptors/issues>).

That being said, I am wide open to any suggestions on how the spec issues should be handled (honestly, it would be best if I'm simply wrong about spec soundness and it reveals to be just a Chrome implementation issue). If Google/Chrome security would like to take over the responsibility of handling this that would be great, but Chrome VRP seems to prefer the reporter [_"[filing] a bug directly with the vendor or maintainer for that component"_](<https://chromium.googlesource.com/chromium/src/+/main/docs/security/vrp-faq.md#are-bugs-in-third_party-components-in-scope-and-eligible-for-vrp-rewards>), which in this case is... uh... the GitHub repo?

I would suggest two options here:

  * Google/Chrome/V8 security team takes on handling the spec issues. I have no problem with this, but please do keep in mind that these issues are only reported to Google as of now since it seems that Chrome is the only runtime that implements and exposes this feature in the wild. If Google chooses to takes this route, I am entrusting you to handle this issue fairly and punctually.
  * I handle the spec issue by myself, and Google/Chrome is relieved of any formal and informal obligations regarding handling the spec issue. In this case, I would argue that this needs to be reported within at most 30 days on [https://github.com/WebAssembly/custom-descriptors/issues](<https://github.com/WebAssembly/custom-descriptors/issues>) for the Wasm CG to collectively work on a solution. Even in this case I will not explicitly indicate that Chrome/V8 is affected.

Again, I am wide open to any suggestions from Google/Chrome's side on how to handle the issue.


---

**#11 — tl...@google.com — Sep 20, 2025 03:53AM**

Yep, this is just unsound. Very embarrassing :/

> But another concern is: Are there no formally verified version of this proposal, either through SpecTec or by manual work? What is the spec trying to model with custom descriptors, and what is V8 currently implementing? We got away in [b/365802567](<https://issues.chromium.org/issues/365802567>) by saying that it's just a terminology confict of the term "match" across different proposal spec evolved independently, but in this case the spec is just flat out unsound. I can understand implementations and minor spec revisions being a trial-and-error process, but almost the entirety of the spec being unsound while going all the way through deployment into stable channel (albeit OT) is honestly a bit concerning. Or am I missing something?

No, there is no formal verification of this proposal. The various academic groups that work on such verification typically lag behind both the spec process and industrial implementations, unless they happen to also be the ones championing the proposal. There are no requirements that a proposal be formally verified as part of the proposal advancement process. This is also just a phase 2 proposal, so it would not have met such requirements yet even if they existed.

Unfortunately SpecTec does not help here, since it does not on its own help prove anything about soundness.

The likely fix will be to add this validation rule:

  * A declared supertype of a type with a `(describes $x)` clause must have a `(describes $y)` clause, where `$y` is a declared supertype of `$x`.

The only reason we didn't already have this rule was that we didn't realize it was necessary for soundness.


---

**#12 — gd...@chromium.org — Sep 20, 2025 04:06AM**

For spec unsoundness issues originating from the custom descriptors proposal, as of now, this only affects Chrome as no other vendors have an implementation that is reasonably complete or available for experimentation externally. My reccommended next steps would be:   
  
(1) The spec is amended with the validation rule, or any follow up fixes required  
(2) VM implementations are informed by the Chrome team on Monday (with credits to the reporter, and with the requested advance notice)  
  
For general security issues, the right thing to do still seems to be notifying Browser VM implementors so we're able to fix security issues prior to public disclosure. We can bring this up in the CG without specifics and establish a process for security issues caused by the specification. In the short term, Proposal champions could be a good point of contact, and they can be found here: [https://github.com/WebAssembly/proposals?tab=readme-ov-file](<https://github.com/WebAssembly/proposals?tab=readme-ov-file>).


---

**#13 — se...@gmail.com — Sep 20, 2025 04:40AM**

Re #11: The added validation rule does seem to make operations sound. It may also fix V8-specific issues like [b/446124891](<https://issues.chromium.org/issues/446124891>), but extra care must be taken so that we don't inadvertently introduce an `.AsExact()` to the inferred struct type later on.

Re #12: Sounds good. Do we have an agreement on Chrome team handling the spec issue?

* * *

P.S. Sorry for the huge report dumps on Friday, but better late than never :)


---

**#14 — gd...@chromium.org — Sep 20, 2025 05:23AM**

I should have been more explicit, I'm representing the Chrome WebAssembly team - the spec issue, and disclosure to the VMs so (1) & (2) in #12 will be handled by the Chrome team.


---

**#15 — gd...@chromium.org — Sep 20, 2025 05:24AM**

Also, appreciate the high quality reports, whenever they come.


---

**#16 — ch...@google.com — Sep 20, 2025 09:35PM**

Setting milestone because of s0/s1 severity.


---

**#17 — ch...@google.com — Sep 20, 2025 09:35PM**

This is a serious security regression. If you are not able to fix this quickly, please revert the change that introduced it.

If this doesn't affect a release branch, or has not been properly classified for severity, please update the Security Impact hotlist or the Severity field, and remove the ReleaseBlock hotlist.


---

**#18 — tl...@google.com — Sep 23, 2025 05:34AM**

Hi [seunghyun3288@gmail.com](<mailto:seunghyun3288@gmail.com>),

I'm a member of @gd...@google.com's team and also the champion of the custom descriptors proposal in the Wasm CG. I wanted to let you know that I have notified representatives of WebKit, SpiderMonkey, and wasmtime of both this bug and <https://g-issues.chromium.org/issues/446113731> with credit to you. As soon as we hear back from the other engine implementers that it is safe to discuss publicly, I will kick off the discussion about fixing these bugs in the CG.

Thanks again for the great reports!


---

**#19 — se...@gmail.com — Sep 23, 2025 06:49AM**

Re [comment#18](<https://issues.chromium.org/issues/446113732#comment18>): Acknowledged, thanks for letting me know.


---

**#20 — ch...@google.com — Sep 23, 2025 09:35PM**

This is a serious security regression. If you are not able to fix this quickly, please revert the change that introduced it.

If this doesn't affect a release branch, or has not been properly classified for severity, please update the Security Impact hotlist or the Severity field, and remove the ReleaseBlock hotlist.


---

**#21 — dx...@google.com — Sep 23, 2025 11:29PM**

Project: v8/v8  
Branch: main  
Author: Jakob Kummerow [jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6973586](<https://chromium-review.googlesource.com/6973586>)

[wasm-custom-desc] Fix subtyping

* * *

Expand for full commit details

```
     
    This updates the restrictions on subtyping of descriptors, in 
    anticipation of upcoming spec changes: 
    - descriptors and described types must have matching subtyping 
    - ref.func for imported functions returns inexact types (for 
      now; long-term solution TBD) 
     
    And it fixes our implementation: 
    - `ProcessBranchOnTarget` erroneously still thought it could 
      compute reachability based on static types when Custom 
      Descriptors are in play 
    - `JSToWasmObject` was missing support for exact types 
    - `ref.get_desc` must not return an exact type when the actual 
      type on the stack is exact, but a non-trivial subtype of the 
      instruction's type immediate. 
     
    Bug: 403372470 
    Fixed: 446113731, 446113732, 446122633, 446124892, 446124893 
    Change-Id: Ic79ab08d906a2e21e66b76e9d96eebb4ebb7a8e5 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6973586 
    Commit-Queue: Jakob Kummerow <jkummerow@chromium.org> 
    Reviewed-by: Matthias Liedtke <mliedtke@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#102697}
```

* * *

Files:

  * M `src/compiler/turboshaft/wasm-gc-typed-optimization-reducer.cc`
  * M `src/compiler/turboshaft/wasm-gc-typed-optimization-reducer.h`
  * M `src/wasm/canonical-types.cc`
  * M `src/wasm/canonical-types.h`
  * M `src/wasm/constant-expression-interface.cc`
  * M `src/wasm/function-body-decoder-impl.h`
  * M `src/wasm/module-decoder-impl.h`
  * M `src/wasm/module-instantiate.cc`
  * M `src/wasm/wasm-objects.cc`
  * M `src/wasm/wasm-objects.h`
  * M `src/wasm/wasm-subtyping.cc`
  * M `test/mjsunit/wasm/custom-descriptors-validity.js`

* * *

Hash: [48c3551179299151b044b2c161566465497c0407](<https://chromiumdash.appspot.com/commit/48c3551179299151b044b2c161566465497c0407>)  
Date: Tue Sep 23 13:39:41 2025

* * *


---

**#22 — ch...@google.com — Sep 24, 2025 09:41PM**

Security Merge Request Consideration: This is sufficiently serious that it should be merged to beta. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M141. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately. Security Merge Request - Manual Review: Merge review required: no relevant commits could be automatically detected (via Git Watcher comments), sending to merge review for manual evaluation. If you have not already manually listed the relevant commits to be merged via a comment above, please do so ASAP.

Security Merge Request: Thank you for fixing this security bug! We aim to ship security fixes as quickly as possible, to limit their opportunity for exploitation as an "n-day" (that is, a bug where git fixes are developed into attacks before those fixes reach users).

We have determined this fix is necessary on milestone(s): [141].

Please answer the following questions so that we can safely process this merge request:

  1. Which CLs should be backmerged? (Please include Gerrit links.)
  2. Has this fix been verified on Canary to not pose any stability regressions?
  3. Does this fix pose any potential non-verifiable stability risks?
  4. Does this fix pose any known compatibility risks?
  5. Does it require manual verification by the test team? If so, please describe required testing.
  6. (no answer required) Please check the OS custom field to ensure all impacted OSes are checked!


---

**#23 — ya...@chromium.org — Sep 25, 2025 06:12AM**

Merge rejected/not needed, since the origin trial is disabled. Also, we are getting near stable cut, so there won't be much time for this to bake on Beta before stable promotion.


---

**#24 — se...@gmail.com — Oct 3, 2025 04:00PM**

"Disabling" OT is an insufficient mitigation, see [b/448972965](<https://issues.chromium.org/issues/448972965>). TL;DR:

  1. Wasm Custom Descriptor feature is now reachable in Stable with an OT token issued before the OT registration was disabled.
  2. "Disabling" OT does not prevent the use of an already issued OT token.
  3. Thus, users are now exposed to the bugs in Stable.

For example, I have an OT token issued to a domain that I control, and `evil.com` for v8CTF repro. Using this, I am able to attack the current v8CTF instance running M141 latest stable release in Linux ([b/449066130](<https://issues.chromium.org/issues/449066130>)).


---

**#25 — sp...@google.com — Oct 8, 2025 04:56AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $55000.00 for this report.  
  
Rationale for this decision:  
High-quality report with demonstration of RCE  
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#26 — tl...@google.com — Oct 8, 2025 07:30AM**

Thanks @se...@gmail.com. For the record, we had previously decided that halting registrations was a sufficient mitigation because of the extremely low number of registrations the trial had. However, we've now gone ahead and started the process of rolling out a component update to disable the trial on the client as well.


---

**#27 — se...@gmail.com — Oct 30, 2025 05:14AM**

Is this fixed in M142 and above even w/o the out-of-band component update? If so, are there plans to issue a CVE number for this (and also for the 4 other bugs)?


---

**#28 — ch...@google.com — Oct 30, 2025 09:44PM**

This V8 bug has been marked as either a release blocker or a vulnerability bug. V8 bugs affect all OSs supported by Chrome, so the OS field has been updated to reflect this. Please update the bug with the correct OS field if it only affects a subset of OSes.


---

**#29 — dr...@chromium.org — Nov 15, 2025 09:27AM**

Updating Security_Impact hotlist since the code changes didn't go out until M142. When we disabled the OT, users moved from vulnerable to safe after Chrome has been running long enough (order of hours, I believe), but there were M141 Stable users who were vulnerable.


---

**#30 — ch...@google.com — Dec 31, 2025 09:40PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
