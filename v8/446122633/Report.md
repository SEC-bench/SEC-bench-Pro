# Wasm type confusion due to wrong reachability analysis in `WasmGCTypeAnalyzer::ProcessBranchOnTarget()` with custom descriptor casts

Issue URL: https://issues.chromium.org/issues/446122633
VRP-Reward: 55000
Date: Sep 19, 2025 10:58PM


### VULNERABILITY DETAILS

#### Summary

Wasm type confusion due to wrong reachability analysis on `WasmGCTypeAnalyzer::ProcessBranchOnTarget()` with descriptor checks. Analyzer wrongly assumes that same-type casts always succeed, although with custom descriptors exactly matching casts might still fail. This can be pivoted into arbitary Wasm type confusion.

Custom descriptors feature is exposed in the wild by default through Origin Trials from M141, which is currently at Beta and very soon reaches (Early) Stable. This bug is not caused by a recent code change and has existed from the very first feature implementation (approx. 6 months).

#### Details

WebAssembly Custom Descriptors proposal introduces descriptors, and [descriptor-based type checks](<https://github.com/WebAssembly/custom-descriptors/blob/main/proposals/custom-descriptors/Overview.md#new-instructions>). These casts/checks require that the described struct has a descriptor that matches the given descriptor at runtime, regardless of whether the types match or not. However, `WasmGCTypeAnalyzer::ProcessBranchOnTarget()` fails to acknowledge this and assumes that any "upcasts", based purely on static types, always succeed:

```
void WasmGCTypeAnalyzer::ProcessBranchOnTarget(const BranchOp& branch,
                                               const Block& target) {
  DCHECK_EQ(current_block_, &target);
  const Operation& condition = graph_.Get(branch.condition());
  switch (condition.opcode) {
    case Opcode::kWasmTypeCheck: {
      const WasmTypeCheckOp& check = condition.Cast<WasmTypeCheckOp>();
      if (branch.if_true == &target) {
        // It is known from now on that the type is at least the checked one.
        RefineTypeKnowledge(check.object(), check.config.to, branch);
      } else {
        DCHECK_EQ(branch.if_false, &target);
        if (wasm::IsSubtypeOf(GetResolvedType(check.object()), check.config.to,
                              module_)) {
          // The type check always succeeds, the target is impossible to be            // [!] this is not true with custom descriptors.
          // reached.
          DCHECK_EQ(target.PredecessorCount(), 1);
          block_is_unreachable_.Add(target.index().id());                              // [!] this might actually be reachable at runtime.
          TRACE(
              "[b%uu] Block unreachable as #%u(%s) used in #%u(%s) is always "
              "true\n",
              target.index().id(), branch.condition().id(),
              OpcodeName(condition.opcode), graph_.Index(branch).id(),
              OpcodeName(branch.opcode));
        }
      }
    } break;
    case Opcode::kIsNull: {
      // ...
    } break;
    default:
      break;
  }
}
```

Interestingly, `WasmGCTypedOptimizationReducer` does acknowledge this and avoids statically eliding the type check, fixed at commit [e8bdb12b](<https://crrev.com/c/6722276>):

```
  V<Word32> REDUCE_INPUT_GRAPH(WasmTypeCheck)(
      V<Word32> op_idx, const WasmTypeCheckOp& type_check) {
    // ...
    if (type != wasm::ValueType()) {
      // ...
      bool to_nullable = type_check.config.to.is_nullable();
      if (wasm::IsHeapSubtypeOf(type.heap_type(),
                                type_check.config.to.heap_type(), module_) &&
          // When checking for a particular custom descriptor, static types
          // cannot guarantee success.
          !(IsCastToCustomDescriptor(type_check.config))) {                            // [!] acknowledges custom descriptor casts
        if (to_nullable || type.is_non_nullable()) {
          // The inferred type is guaranteed to be a subtype of the checked
          // type.
          return __ Word32Constant(1);
        } else {
          // The inferred type is guaranteed to be a subtype of the checked
          // type if it is not null.
          return __ Word32Equal(
              __ IsNull(__ MapToNewGraph(type_check.object()), type), 0);
        }
      }
      // ...
    }
    // ...
  }
```

This leads to yet another bug where reachability analysis mistakenly marks a reachable code (false-side branch of the typecheck) as statically unreachable when the branch depends on an exact descriptor check.

Exploiting such reachability analysis bug has been shown to be possible in prior reports via loop reprocessing bypass, and thus is omitted. ([b/372269618](<https://issues.chromium.org/issues/372269618>), [b/373703277](<https://issues.chromium.org/issues/373703277>), [b/374790906](<https://issues.chromium.org/issues/374790906>), [b/377620832](<https://issues.chromium.org/issues/377620832>), ...)

#### Bisect

Bug introduced by WebAssembly Custom Descriptors, on Origin Trials from M141 and onwards. More specifically, it existed from commit [26b78962](<https://crrev.com/c/6402494>) which implements `br_on_cast_desc`, but likely has only been exposed after commit [e8bdb12b](<https://crrev.com/c/6722276>) which fixes the broken cast always succeeds/fails optimization on descriptor type cast/check (which itself would have been an exploitable bug).

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

**#2 — dr...@chromium.org — Sep 20, 2025 02:10AM**

[security triage] `poc.js` does reproduce for me as far back as M140, but since this flag is still marked experimental, setting High severity and Security_Impact-None (I was wrong about the handling of vulnerabilities in experimental flags previously, apologies). Triaging to WASM folks.


---

**#3 — dr...@chromium.org — Sep 20, 2025 02:54AM**

Since custom descriptors is in OT as of M141, this should be FoundIn M141.

And `rce.html` does reproduce the flag file read as with `./chrome --enable-blink-features=WebAssemblyCustomDescriptors --no-sandbox b446122633/rce.html`


---

**#4 — cl...@chromium.org — Sep 20, 2025 03:03AM**

Setting FoundIn 141 because that's when the origin trial started.


---

**#5 — cl...@chromium.org — Sep 20, 2025 03:04AM**

Assigning all these custom descriptor vulnerabilities to Jakob for now.


---

**#6 — ch...@google.com — Sep 20, 2025 09:35PM**

Setting milestone because of s0/s1 severity.


---

**#7 — ch...@google.com — Sep 20, 2025 09:35PM**

This is a serious security regression. If you are not able to fix this quickly, please revert the change that introduced it.

If this doesn't affect a release branch, or has not been properly classified for severity, please update the Security Impact hotlist or the Severity field, and remove the ReleaseBlock hotlist.


---

**#8 — ch...@google.com — Sep 23, 2025 09:35PM**

This is a serious security regression. If you are not able to fix this quickly, please revert the change that introduced it.

If this doesn't affect a release branch, or has not been properly classified for severity, please update the Security Impact hotlist or the Severity field, and remove the ReleaseBlock hotlist.


---

**#9 — dx...@google.com — Sep 23, 2025 11:29PM**

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

**#10 — ch...@google.com — Sep 24, 2025 09:41PM**

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

**#11 — ya...@chromium.org — Sep 25, 2025 06:08AM**

Merge rejected, since we are getting near stable cut, so there won't be much time for this to bake on Beta before stable promotion. Since the origin trial is disabled, we're not in as much of a rush. Please make sure this is merged if needed when the origin trial is re-enabled.


---

**#12 — sp...@google.com — Oct 8, 2025 04:56AM**

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

**#13 — dr...@chromium.org — Nov 15, 2025 09:27AM**

Updating Security_Impact hotlist since the code changes didn't go out until M142. When we disabled the OT, users moved from vulnerable to safe after Chrome has been running long enough (order of hours, I believe), but there were M141 Stable users who were vulnerable.


---

**#14 — dx...@google.com — Dec 12, 2025 07:37AM**

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

**#15 — ch...@google.com — Dec 31, 2025 09:41PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
