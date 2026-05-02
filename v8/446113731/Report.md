# Wasm type confusion due to custom descriptors spec unsoundness on `ref.func` exact typing

Issue URL: https://issues.chromium.org/issues/446113731
VRP-Reward: 55000
Date: Sep 19, 2025 10:58PM


## README

This is _potentially_ a Wasm spec-level unsoundness issue. However, there seem to be no public spec documenting how `ref.func` and other operations that yield references work in conjunction with custom descriptors. I am reporting this privately to Google Chrome/V8 as Google seems to be leading the spec work and implementation of custom descriptors the first and practically has the most affected users in the wild.

As this _might_ be a spec-level unsoundness which the Wasm community needs to know, I believe that the issue necessitates a quicker disclosure deadline than what is enforced by default by Chrome's disclosure policies. **It would be great if we can coordinate the disclosure within a week from the reported date** \- please contact me through email or through the comments. Unless otherwise coordinated, **the spec unsoundness issue is subject to a 14-day disclosure deadline after which the issue, without any specific mentions of Chrome/V8, will be disclosed publicly** on [https://github.com/WebAssembly/custom-descriptors/issues](<https://github.com/WebAssembly/custom-descriptors/issues>). The Chrome/V8 security team is allowed to responsibly disclose this to other vendors and personnel involved in WebAssembly work (at CG meetings or whatnot) under the conditions that 1. the reporter is credited, and 2. is given at least a day's advance notice.

### VULNERABILITY DETAILS

#### Summary

Wasm type confusion due to invalidly typing `ref.func` function types as exact. Imported functions are allowed to be subtypes of the declared function type, and `ref.func` returns the original reference for equivalence with the original import. However, `ref.func` is typed as exact based on its declared function type which is unsound. By abusing `WasmGCTypeAnalyzer` reachability analysis, this may be pivoted into arbitrary Wasm type confusion.

Custom descriptors feature is exposed in the wild by default through Origin Trials from M141, which is currently at Beta and very soon reaches (Early) Stable. This bug is not caused by a recent code change and has existed from the very first feature implementation (approx. 6 months) due to a likely inherent spec unsoundness.

> This bug is notable in that `ref.func` operation itself is completely unrelated to custom descriptors, yet the addition of exactness introduces unsoundness.

#### Details

WebAssembly Custom Descriptors proposal introduces exactness as part of heaptype. An object may only be typed as exact if it is exactly an instance of that type, but not for its subtypes. Most importantly, this is not only valid for struct types but for all indexed types including function types.

Currently, V8 types `ref.func` as exact types of its declared function type:

```
// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/function-body-decoder-impl.h;drc=43df3221d3b0c1ea8f7d54394a00cb8656204085;l=4240
  DECODE(RefFunc) {
    this->detected_->add_reftypes();
    IndexImmediate imm(this, this->pc_ + 1, "function index", validate);
    if (!this->ValidateFunction(this->pc_ + 1, imm)) return 0;
    ModuleTypeIndex index = this->module_->functions[imm.index].sig_index;
    const TypeDefinition& type_def = this->module_->type(index);
    Value* value =
        Push(ValueType::Ref(index, type_def.is_shared, RefTypeKind::kFunction)
                 .AsExactIfEnabled(this->enabled_));                                // [!] typed as exact based on declared function type
    CALL_INTERFACE_IF_OK_AND_REACHABLE(RefFunc, imm.index, value);
    return 1 + imm.length;
  }
```

Other decoders, e.g. `ModuleDecoderImpl::consume_init_expr()`, `ConstantExpressionInterface::RefFunc()`, also does the same and types it as exact.

However, imported functions may very well be subtypes of the declared type based on Wasm spec. Importing a subtyped function does not violate any JS-Wasm boundary type checks and is perfectly legal:

```
// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/module-instantiate.cc;drc=e75b1ba2a99aa352048745d44754c5de8be273d8;l=733
ImportCallKind ResolvedWasmImport::ComputeKind(
    DirectHandle<WasmTrustedInstanceData> trusted_instance_data, int func_index,
    const wasm::CanonicalSig* expected_sig, CanonicalTypeIndex expected_sig_id,
    WellKnownImport preknown_import) {
  // ...
  if (!trusted_function_data_.is_null()) {
    if (Tagged<WasmExportedFunctionData> data;
        TryCast(*trusted_function_data_, &data)) {
      if (!data->MatchesSignature(expected_sig_id)) {                               // [!] allows subtype
        return ImportCallKind::kLinkError;
      }
      uint32_t function_index = static_cast<uint32_t>(data->function_index());
      if (function_index >=
          data->instance_data()->module()->num_imported_functions) {
        return ImportCallKind::kWasmToWasm;
      }
      // ...
    }
  }
  // ...
}

// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/wasm-objects.cc;drc=e75b1ba2a99aa352048745d44754c5de8be273d8;l=3085
bool WasmExportedFunctionData::MatchesSignature(
    wasm::CanonicalTypeIndex other_canonical_type_index) {
  return wasm::GetTypeCanonicalizer()->IsCanonicalSubtype(                          // [!] allows subtype
      sig_index(), other_canonical_type_index);
}
```

Plus, imported functions preserve their reference for equivalence.

```
// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/module-instantiate.cc;drc=e75b1ba2a99aa352048745d44754c5de8be273d8;l=2335
bool InstanceBuilder::ProcessImportedFunction(
    DirectHandle<WasmTrustedInstanceData> trusted_instance_data,
    int import_index, int func_index, DirectHandle<Object> value,
    WellKnownImport preknown_import) {
  // ...
  // Store any {WasmExternalFunction} callable in the instance before the call
  // is resolved to preserve its identity. This handles exported functions as
  // well as functions constructed via other means (e.g. WebAssembly.Function).
  if (WasmExternalFunction::IsWasmExternalFunction(*value)) {
    trusted_instance_data->func_refs()->set(                                        // [!] stores imported function, later returned for ref.func
        func_index, Cast<WasmExternalFunction>(*value)->func_ref());
  }
  // ...
}
```

This indicates that `ref.func` must NOT be typed as an exact type, at the very least for imported functions, as its actual type may be a subtype. However, it is statically typed as an exact (super)type. Consider the following case:

  * We have function types `f2 <: f1`
  * Module 1 exports `fn : f2`.
  * Module 2 imports it as `fn : f1`. This is legal.
  * Module 2 executes `ref.func $fn`, yielding type `ref exact $f1`. This is obviously wrong as its real exact type is `ref exact $f2`, but the next line will show it even more obviously.
  * Module 2 executes `ref.cast $f1` \+ `ref.cast $f2` on the object. This results in `ref exact $f1 -> ref $f1 -> ref $f2` casting, which succeeds because the first is a static upcast and the second succeeds dynamically. However, the two types `ref exact $f1` and `ref $f2` are unrelated in subtyping hierarchy; the cast should never have succeeded. 
    * Note that without custom descriptors and thus without exactness, the cast should succeed!

So how is this exploitable? Enter `WasmGCTypeAnalyzer` again, which I have first demonstrated that it can be used to pivot seemingly unexploitable Wasm type confusions into attacker-chosen, arbitrary type confusions ([b/372269618](<https://issues.chromium.org/issues/372269618>), [b/373703277](<https://issues.chromium.org/issues/373703277>), [b/374790906](<https://issues.chromium.org/issues/374790906>), [b/377620832](<https://issues.chromium.org/issues/377620832>), ...). After a series of exploits `WasmGCTypeAnalyzer` has been hardened such that most operations that lead to an unreachable state are replaced to trap or otherwise conform with the statically reachable case unconditionally. But we can still run around the mitigations and exploit subtle discrepancies as shown in the below Wasm code, pulled out from the repro (replace `v = f1, v2 = f2, imp = fn`):

```
  kExprBlock, kWasmVoid,
    // make typer track function type as ref v2
    kExprRefFunc, $imp,                                 // decoder: ref exact v (mistyped!), typer: ref v
    kExprLocalTee, 3,
    kGCPrefix, kExprRefCast, $sig_v_v,                  // decoder: ref v (upcast), typer: ref v
    kGCPrefix, kExprRefCast, $sig_v_v2,                 // decoder: ref v2, typer: ref v2, runtime: cast succeed
    kExprDrop,

    // now refine it with ref exact v
    kExprLocalGet, 3,                                   // decoder: ref exact v, typer: ref v2
    kGCPrefix, kExprRefCastNull, kWasmExact, $sig_v_v,  // decoder: ref null exact v (upcast), typer: ref v2

    // exploit implicit type refinement w/ inconsistent types from decoder
    kExprBrOnNonNull, 0,                                // typer: (ref exact v) & (ref v2) = bot on branch taken, runtime: branch taken
    kExprUnreachable,
  kExprEnd,
```

`kExprBrOnNonNull` leads to ` RefineTypeKnowledge(is_null.object(), is_null.type.AsNonNull(), branch)`, where `is_null.type` is taken from the decoder's static typing information. The typer already tracks the object's type as `ref v2`, and as `(ref exact v) & (ref v2) = bot` following code is marked as statically unreachable while it is in fact reached dynamically. Note that both sides of the branch is typed as unreachable, and that there is no statically "reachability compliant" result of `IsNull` that the operation should get reduced into (aside from replacing it with an unconditional trap).

Exploiting such reachability analysis bug has been shown to be possible in prior reports via loop reprocessing bypass, and thus is omitted.

* * *

Although I cannot find a spec that describes how `ref.func` should be typed with custom descriptors, it seems that there is enough brokenness across other implementations potentially indicating a spec issue (again, if a spec even exists). Binaryen also documents that they implement this exactness typing rule in [PR #7600](<https://github.com/WebAssembly/binaryen/pull/7600>).

#### Bisect

Bug introduced by WebAssembly Custom Descriptors, on Origin Trials from M141 and onwards. More specifically, it is introduced in commit [25a0fc85](<https://crrev.com/c/6415951>) and [dc8cec44](<https://crrev.com/c/6504002>) which makes `ref.func` exact.

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

**#2 — dr...@chromium.org — Sep 20, 2025 02:04AM**

[security triage] `poc.js` reproduced for me in M140, setting High severity and the corresponding FoundIn. Again, I can't reproduce `rce.html`. Let me know if it should require more than just running `chrome --enable-blink-features=WebAssemblyCustomDescriptors b446113731/rce.html`. This flag is still marked as experimental, so we do expect security vulnerabilities at this stage. But given you note that this is a spec unsoundness issue, I'll leave it to the V8 folks to decide how they want to handle disclosure. I will note that a 14-day disclosure timeline is very aggressive, and not in line with Chrome's usual processes for security vulnerabilities.


---

**#3 — is...@chromium.org — Sep 20, 2025 02:07AM**

Wasm folks, could you please help with finding the right owner?


---

**#4 — dr...@chromium.org — Sep 20, 2025 02:12AM**

Because this flag is experimental, it should be Security_Impact-None and still treated as a vulnerability (the fact that it's in the spec is immaterial). Sorry for the noise.


---

**#5 — dr...@chromium.org — Sep 20, 2025 02:51AM**

Customer descriptors is in Origin Trial as of M141, so the experimental annotation on the flag is incorrect. Updating FoundIn.

Also a note that I was able to reproduce `rce.html` reading `/flag/flag` with `./chrome --enable-blink-features=WebAssemblyCustomDescriptors --no-sandbox b446113731/rce.html`


---

**#6 — cl...@chromium.org — Sep 20, 2025 03:03AM**

Setting FoundIn 141 because that's when the origin trial started.


---

**#7 — cl...@chromium.org — Sep 20, 2025 03:04AM**

Assigning all these custom descriptor vulnerabilities to Jakob for now.


---

**#8 — tl...@google.com — Sep 20, 2025 03:21AM**

Thanks for the report. I can confirm that this is a soundness issue in the current proposal spec. We will have to discuss how to properly fix this with the Wasm CG, but in the short term, typing ref.func of function imports as inexact would be a good fix.


---

**#9 — ch...@google.com — Sep 20, 2025 09:35PM**

Setting milestone because of s0/s1 severity.


---

**#10 — ch...@google.com — Sep 20, 2025 09:35PM**

This is a serious security regression. If you are not able to fix this quickly, please revert the change that introduced it.

If this doesn't affect a release branch, or has not been properly classified for severity, please update the Security Impact hotlist or the Severity field, and remove the ReleaseBlock hotlist.


---

**#12 — ch...@google.com — Sep 23, 2025 09:35PM**

This is a serious security regression. If you are not able to fix this quickly, please revert the change that introduced it.

If this doesn't affect a release branch, or has not been properly classified for severity, please update the Security Impact hotlist or the Severity field, and remove the ReleaseBlock hotlist.


---

**#13 — dx...@google.com — Sep 23, 2025 11:29PM**

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

**#14 — ch...@google.com — Sep 24, 2025 09:41PM**

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

**#15 — ya...@chromium.org — Sep 25, 2025 06:12AM**

Merge rejected/not needed, since the origin trial is disabled. Also, we are getting near stable cut, so there won't be much time for this to bake on Beta before stable promotion.


---

**#16 — sp...@google.com — Oct 8, 2025 04:56AM**

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

**#17 — dr...@chromium.org — Nov 15, 2025 09:26AM**

Updating Security_Impact hotlist since the code changes didn't go out until M142. When we disabled the OT, users moved from vulnerable to safe after Chrome has been running long enough (order of hours, I believe), but there were M141 Stable users who were vulnerable.


---

**#18 — ch...@google.com — Dec 31, 2025 09:40PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
