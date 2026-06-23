# Wasm type confusion due to custom descriptors spec ambiguity in `ref.get_desc` exactness typing

Issue URL: https://issues.chromium.org/issues/446124893
VRP-Reward: 55000
Date: Sep 19, 2025 10:58PM


## README

This is a Wasm spec-level unsoundness issue. Any runtime implementing the same spec faithfully will have the same bug. I am reporting this privately to Google Chrome/V8 as Google seems to be leading the spec work and implementation of custom descriptors the first and practically has the most affected users in the wild.

As this is a spec-level unsoundness which the Wasm community needs to know, I believe that the issue necessitates a quicker disclosure deadline than what is enforced by default by Chrome's disclosure policies. **It would be great if we can coordinate the disclosure within a week from the reported date** \- please contact me through email or through the comments. Unless otherwise coordinated, **the spec unsoundness issue is subject to a 14-day disclosure deadline after which the issue, without any specific mentions of Chrome/V8, will be disclosed publicly** on [https://github.com/WebAssembly/custom-descriptors/issues](<https://github.com/WebAssembly/custom-descriptors/issues>). The Chrome/V8 security team is allowed to responsibly disclose this to other vendors and personnel involved in WebAssembly work (at CG meetings or whatnot) under the conditions that 1. the reporter is credited, and 2. is given at least a day's advance notice.

### VULNERABILITY DETAILS

#### Summary

Wasm type confusion due to spec unsoundness around `ref.get_desc` exactness typing. [Spec](<https://github.com/WebAssembly/custom-descriptors/blob/main/proposals/custom-descriptors/Overview.md#new-instructions>) describes two different rules for `ref.get_desc`:

  * (Rule #1) Rule in the codeblock indicates that `ref.get_desc` must type the result as exact only when the stack type is a subtype of the exact encoded type (thus only allowing the exact encoded type). This rule is sound.
  * (Rule #2) Rule written in plain English indicates that _"If the provided reference is to an exact heap type, then the type of the custom descriptor is known precisely, so the result can be exact as well"_. In other words, the provided reference's exactness directly propagates to the result type. However, the result type in this case MUST be typed as the **provided reference's descriptor type** , not the **encoded immediate type's descriptor type**. This rule is also sound (if done right) but is different than the first rule.
  * However, mixing the two up yields an **unsound rule** , e.g. by propagating the provided reference's exactness to the result type (Rule #2), but taking the base result type from the encoded immediate type's descriptor (Rule #1). The spec is unsound in that it describes two completely different rules as if it is the same `ref.get_desc`.

V8 also gets confused and implements the unsound rule, transferring the exactness of the stack type to the result type while using the encoded immediate type's descriptor. This allows typing the resulting descriptor as an exact supertype, leading to type confusion.

Custom descriptors feature is exposed in the wild by default through Origin Trials from M141, which is currently at Beta and very soon reaches (Early) Stable. This bug is not caused by a recent code change and has existed from the very first feature implementation (approx. 6 months) due to an inherent spec unsoundness.

#### Details

[Spec](<https://github.com/WebAssembly/custom-descriptors/blob/main/proposals/custom-descriptors/Overview.md#new-instructions>) indicates that `ref.get_desc` must type the result as exact only when the stack type is a subtype of the exact sourcetype:

```
ref.get_desc typeidx

C |- ref.get_desc x : (ref null (exact_1 x)) -> (ref (exact_1 y))
-- C.types[x] ~ descriptor y ct
```

For example, take `x' <: x` with `C.types[x'] ~ descriptor y' ct'` where `C |- ¬(C.types[x'] ~ C.types[x])` \- that is, `x'` is a strict subtype of `x`. Due to subtyping rules on descriptors, `y' <: y` holds. If `ref exact x'` is passed to `ref.get_desc x`:

```
Stack: ref exact x'
Match: ref exact x' <: ref null x => exact_1 = inexact
=> ref.get_desc x (ref exact x') -> (ref y)
```

Since `¬(ref exact x' <: ref null exact x)`, `exact_1 = inexact` is the only suitable rule and the resulting descriptor type must be inexact.

However, the spec also describes this rule in plain English but with different typing rules:

> If the provided reference is to an exact heap type, then the type of the custom descriptor is known precisely, so the result can be exact as well. Otherwise, the subtyping rules described above ensure that there will be some custom descriptor value and that it will be a subtype of the custom descriptor type for `x`, so the result can be a non-null reference to the inexact descriptor type.

This may be interpreted as a weakened, unsound rule that translates to the below rule:

```
ref.get_desc? typeidx

C |- ref.get_desc? x : (ref null (exact_1 x')) -> (ref (exact_1 y))
-- C.types[x] ~ descriptor y ct
-- C.types[x'] ~ descriptor y' ct'
-- C |- x' <: x                                                                     // [!] (modified) subtype check
```

Note that we've subtly weakened the rule on the input type, effectively passing on the exactness of whatever was on the stack instead of typechecking `stacktype <: ref null exact x`. We also derive `y` from the encoded type `x`, not the provided type on the stack. This yields the results below:

```
Stack: ref exact x'
Match: (ref exact x' <: ref null exact x') ∧ (x' <: x) => exact_1 = exact
=> ref.get_desc? x (ref exact x') -> (ref exact y)
```

V8's implementation takes the weakened, unsound rule:

```
// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/function-body-decoder-impl.h;drc=43df3221d3b0c1ea8f7d54394a00cb8656204085;l=5994
      case kExprRefGetDesc: {
        // ...
        StructIndexImmediate imm(this, this->pc_ + opcode_length, validate);
        if (!this->Validate(this->pc_ + opcode_length, imm)) return 0;
        const TypeDefinition& type = this->module_->type(imm.index);
        if (!VALIDATE(type.has_descriptor())) {
          // ...
          return 0;
        }
        Value ref = Pop(ValueType::RefNull(imm.heap_type()));                       // [!] (modified) subtype check
        Value* desc =
            Push(ValueType::Ref(this->module_->heap_type(type.descriptor))
                     .AsExact(ref.type.exactness()));                               // [!] exactness directly from stack type (x')
        CALL_INTERFACE_IF_OK_AND_REACHABLE(RefGetDesc, ref, desc);
        return opcode_length + imm.length;
      }
```

Now we have `ref exact y'` typed as `ref exact y` where `y' <: y`. This pokes a hole in the type system exactly as described in the [proposal docs](<https://github.com/WebAssembly/custom-descriptors/blob/main/proposals/custom-descriptors/Overview.md#exact-types>), allowing attackers to invalidly type a descriptor `y'` into an exact supertype `y`, instantiate struct `x`, then invalidly cast down to `x'`. This leads to type confusion between arbitrary Wasm types.

This seems to be a very common misinterpretation of the spec. Development work on Binaryen [also shows](<https://github.com/WebAssembly/binaryen/pull/7886>) this misunderstanding: _"`ref.get_desc` inherits its input ref's exactness..."_ which is only true when the reference type's descriptor is used as the return type (which from a cursory glance may be what Binaryen's doing). This leads me to wonder if the spec was initially designed to represent something like Rule #1, but happened to be written down in a different thing described as Rule #2, and then things got messy? [Slides](<https://docs.google.com/presentation/d/1HtHw4WNEZ4DAt6ythWzhDiPHBc8_-GHT5qKAMlxfcYc/edit?slide=id.g35846d341e4_0_429#slide=id.g35846d341e4_0_429>) from CG meeting for Phase 2 advancement of the proposal also mix up the two, stating the formal rule as Rule #1 but uses the phrase "propagates exactness of references" which applies on Rule #2.

#### Bisect

Bug introduced by WebAssembly Custom Descriptors, on Origin Trials from M141 and onwards. More specifically, it is introduced in commit [2f4c043d](<https://crrev.com/c/6401033>) which implements `ref.get_desc`.

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

**#2 — dr...@chromium.org — Sep 20, 2025 02:15AM**

[security triage] `poc.js` reproduces for me in M140, but the flag is experimental. Setting High severity, Security_Impact-None, and triaging to WASM folks.


---

**#3 — dr...@chromium.org — Sep 20, 2025 02:57AM**

Since custom descriptors is in OT as of M141, this should be FoundIn M141.

And `rce.html` does reproduce the flag file read with `./chrome --enable-blink-features=WebAssemblyCustomDescriptors --no-sandbox b446124893/rce.html`


---

**#4 — cl...@chromium.org — Sep 20, 2025 03:03AM**

Setting FoundIn 141 because that's when the origin trial started.


---

**#5 — cl...@chromium.org — Sep 20, 2025 03:04AM**

Assigning all these custom descriptor vulnerabilities to Jakob for now.


---

**#6 — tl...@google.com — Sep 20, 2025 03:32AM**

We should improve the prose explanation of this typing rule in the proposal overview, but the formal typing rule is meant to be normative and is correct and sound, so we just need to update the V8 implementation here. If the type available on the stack is not a subtype of `(ref null (exact x))` but is a subtype of `(ref null x)`, then the result of `ref.get_desc x` should be `(ref y)`, not `(ref (exact y))`, even if the type on the stack is an exact reference.


---

**#7 — ch...@google.com — Sep 20, 2025 09:35PM**

Setting milestone because of s0/s1 severity.


---

**#8 — ch...@google.com — Sep 20, 2025 09:35PM**

This is a serious security regression. If you are not able to fix this quickly, please revert the change that introduced it.

If this doesn't affect a release branch, or has not been properly classified for severity, please update the Security Impact hotlist or the Severity field, and remove the ReleaseBlock hotlist.


---

**#9 — ch...@google.com — Sep 23, 2025 09:35PM**

This is a serious security regression. If you are not able to fix this quickly, please revert the change that introduced it.

If this doesn't affect a release branch, or has not been properly classified for severity, please update the Security Impact hotlist or the Severity field, and remove the ReleaseBlock hotlist.


---

**#10 — dx...@google.com — Sep 23, 2025 11:29PM**

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

**#11 — ch...@google.com — Sep 24, 2025 09:41PM**

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

**#12 — ya...@chromium.org — Sep 25, 2025 06:12AM**

Merge rejected/not needed, since the origin trial is disabled. Also, we are getting near stable cut, so there won't be much time for this to bake on Beta before stable promotion.


---

**#13 — sp...@google.com — Oct 8, 2025 04:56AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $55000.00 for this report.  
  
Rationale for this decision:  
High-quality report with demonstration of RCE in a sandboxed process  
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#14 — dr...@chromium.org — Nov 15, 2025 09:28AM**

Updating Security_Impact hotlist since the code changes didn't go out until M142. When we disabled the OT, users moved from vulnerable to safe after Chrome has been running long enough (order of hours, I believe), but there were M141 Stable users who were vulnerable.


---

**#15 — dx...@google.com — Dec 12, 2025 07:37AM**

Project: v8/v8  
Branch: main  
Author: Jakob Kummerow [jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)  
Link: [https://chromium-review.googlesource.com/7252949](<https://chromium-review.googlesource.com/7252949>)

[wasm-custom-desc][test] Add regression tests

* * *

Expand for full commit details

```
     
    This adds regression tests for a few issues fixed a while ago. 
     
    Bug: 446122633, 446124892, 446124893 
    Change-Id: I2c5542c716991636332fe4d1d27a7e190fbb7d91 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/7252949 
    Auto-Submit: Jakob Kummerow <jkummerow@chromium.org> 
    Commit-Queue: Jakob Kummerow <jkummerow@chromium.org> 
    Reviewed-by: Matthias Liedtke <mliedtke@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#104279}
```

* * *

Files:

  * A `test/mjsunit/regress/wasm/regress-446122633.js`
  * A `test/mjsunit/regress/wasm/regress-446124893.js`
  * M `test/mjsunit/wasm/exact-types.js`

* * *

Hash: [bc7d9e039115f99638df28bb4a1d330090cb1f8d](<https://chromiumdash.appspot.com/commit/bc7d9e039115f99638df28bb4a1d330090cb1f8d>)  
Date: Thu Dec 11 21:47:50 2025

* * *


---

**#16 — ch...@google.com — Dec 31, 2025 09:41PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
