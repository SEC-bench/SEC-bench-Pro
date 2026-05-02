# Wasm type confusion due to DefaultReferenceValue() JS null for noexn type

Issue URL: https://issues.chromium.org/issues/377620832
VRP-Reward: 55000
Date: Nov 6, 2024 10:55PM


### VULNERABILITY DETAILS

#### Summary

Equivalent to [b/372285204](<https://issues.chromium.org/issues/372285204>) but in "backwards", now with `null` being a problem instead of `wasm_null`. [b/374790906](<https://issues.chromium.org/issues/374790906>) "internalized" `exn` type hierarchy to use `wasm_null` for null value, but `DefaultReferenceValue()` still uses JS `null` value resulting in type confusion of having JS `null` value for `ref null noexn` types. This also results in type nullability confusion issue exploitable through Turboshaft optimization even with the recent mitigations in place.

Triggering this bug requires a staged Wasm feature, `--experimental-wasm-exnref`.

#### Details

[b/374790906](<https://issues.chromium.org/issues/374790906>) "internalized" `exn` type hierarchy to use `wasm_null` for null value due to nullability issues, specifically with JS `null` thrown as an exception from JS side. Thus, the only valid value for a `ref null noexn` type should be `wasm_null` instead of a JS `null` \- however, `DefaultReferenceValue()` used in Wasm JS APIs still use `null` for `exn` type hierarchy since it does not use `ValueTypeBase::use_wasm_null()` and instead has its own implementation:

```
i::Handle<i::HeapObject> DefaultReferenceValue(i::Isolate* isolate,
                                               i::wasm::ValueType type) {
  DCHECK(type.is_object_reference());
  // Use undefined for JS type (externref) but null for wasm types as wasm does
  // not know undefined.
  if (type.heap_representation() == i::wasm::HeapType::kExtern) {
    return isolate->factory()->undefined_value();
  } else if (type.heap_representation() == i::wasm::HeapType::kNoExtern ||
             type.heap_representation() == i::wasm::HeapType::kExn ||
             type.heap_representation() == i::wasm::HeapType::kNoExn) {     // [!] exn type hierarchy should use wasm_null
    return isolate->factory()->null_value();
  }
  return isolate->factory()->wasm_null();
}
```

This results in a type confusion, which we can see that this is equivalent to [b/372285204](<https://issues.chromium.org/issues/372285204>) but in backwards. It is not immediately obvious what to do with a `null` value in a `ref null noexn` type, but prior reports demonstrated that such inconsistencies can be pivoted into arbitrary Wasm type confusion via Turboshaft typer optimizations ([b/372269618#comment7](<https://issues.chromium.org/issues/372269618#comment7>), [b/373703277#comment13](<https://issues.chromium.org/issues/373703277#comment13>)).

Even with all the additional mitigation (by reducing to trap or by not branching into unreachable state) implemented in Turboshaft, we note that it is not enough - we can simply return an uninhabited type from Liftoff-compiled function, especially for this "non-null value in null-only type" case (`ref noexn`). This type is inherently uninhabited and any functions that return such typed values should have never returned (i.e. trapped), but Liftoff understandably does not care.

It is unclear what is at fault especially considering that the type confusion has already occured - function body decoder as it let the interface generate code for uninhabited types? Liftoff as it should have forced a trap instead of emitting code that result in an uninhabited typed value? Turboshaft as this receives the uninhabited type and decides to do the problematic typer optimizations? But whatever is at fault, there still remains the problem of being able to pivot a useless type confusion into arbitrary type confusion.

Not directly related to this problem is another problem where `ValueTypeBase::is_uninhabited()` does not include `ref noexn` which would also be worth fixing:

```
  constexpr bool is_uninhabited() const {
    return is_bottom() ||
           (is_non_nullable() && (is_reference_to(HeapType::kNone) ||
                                  is_reference_to(HeapType::kNoExtern) ||
                                  is_reference_to(HeapType::kNoFunc) ||
                                  is_reference_to(HeapType::kNoneShared) ||
                                  is_reference_to(HeapType::kNoExternShared) ||
                                  is_reference_to(HeapType::kNoFuncShared)));
  }
```

Note that due to this unrelated issue, the exploit is slightly harder as the returned type of `ref noexn` is not immediately uninhabited. This can be sidestepped by passing the type through `RefineTypeKnowledge()` as `wasm::Intersection()` does consider `ref noexn` to be a bottom type, but without directly triggering any trapping mitigations. The attached repros use `BrOnCastFailImpl()` -> `AnnotateWasmType()` to achieve this goal.

#### Bisect

Bug introduced by commit [9997fc0](<https://chromiumdash.appspot.com/commit/9997fc01395257cffd7231f14bb4d9fa7eaa9665>) that internalizes `exn` type hierarchy to use `wasm_null` for null values.

#### Suggested Fix

  * Use `wasm_null()` for `exn` type hierarchy. **To prevent further confusion and inconsistencies in code, change`DefaultReferenceValue()` to use `ValueTypeBase::use_wasm_null()` to determine what values to return.**
  * Add `ref noexn` case in `ValueTypeBase::is_uninhabited()`. This is however unrelated to the underlying problem.

### VERSION

See bisect commit release info in Chromium Dash for more info: [https://chromiumdash.appspot.com/commit/9997fc01395257cffd7231f14bb4d9fa7eaa9665](<https://chromiumdash.appspot.com/commit/9997fc01395257cffd7231f14bb4d9fa7eaa9665>)

Chrome Version: 132.0.6795.0 (V8 commit [9997fc0](<https://chromiumdash.appspot.com/commit/9997fc01395257cffd7231f14bb4d9fa7eaa9665>)) ~ latest  
Operating System: All

Again, triggering this bug requires a staged Wasm feature `--experimental-wasm-exnref`.

### REPRODUCTION CASE

Attached as `poc.js` which exploits the type confusion via Turboshaft to obtain in-sandbox exploit primitives, and crashes on arbitrary caged write attempt. Run d8 with `--experimental-wasm-exnref` flags.

Also attached is yet another full exploit `exp.html` that pops `calc` on Windows x64 Chrome releases on canary/dev versions 132.0.6795.0 ~ latest. Run Chrome with `--js-flags=--experimental-wasm-exnref --no-sandbox` flags.

Note that the repros are written in a way to dynamically detect tier-up compilation. This would succeed in most reasonable environments, but is still technically racy and can fail. For a deterministic repro replace `for (let i = 0; i < 100000; i++) { ... }` loop with `%WasmTierUpFunction(confuser);` to force tier-up compilation.

### FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION

Type of crash: Renderer  
Crash State: Crashes on arbitrary caged write attempt from JIT-compiled Wasm function (on d8), arbitrary code execution (on Chrome)

### CREDIT INFORMATION

Reporter credit: Seunghyun Lee (@0x10n) of CMU CyLab


---

**#2 — me...@google.com — Nov 7, 2024 03:53AM**

thibaudm: Could you PTAL since this is similar to [bug 372285204](<https://issues.chromium.org/issues/372285204>)?


---

**#3 — jk...@chromium.org — Nov 7, 2024 05:08AM**

Ha, great catch. I just stumbled upon that `DefaultReferenceValue` implementation myself yesterday, as part of the work on sandboxifying `WasmTableObject`. I'll come up with a short-term fix for this tomorrow (I agree that this should use `type.use_wasm_null()`).


---

**#4 — me...@google.com — Nov 7, 2024 07:37AM**

Assigning tentative sseverity and FoundIn labels.


---

**#5 — ap...@google.com — Nov 9, 2024 12:54AM**

Project: v8/v8  
Branch: main  
Author: Jakob Kummerow <[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6000165](<https://chromium-review.googlesource.com/6000165>)

[wasm] Use ValueType::use_wasm_null() helper consistently

* * *

Expand for full commit details

```
[wasm] Use ValueType::use_wasm_null() helper consistently 
 
This is a follow-up to crrev.com/c/5953226: exnref now uses Wasm null, 
and the DefaultReferenceValue() helper must comply with that. 
 
Drive-by 1: fix ValueType::is_uninhabited() for (ref noexn). 
Drive-by 2: make Liftoff code crash when a function attempts to 
return a value of uninhabitable type. We might want more such checks 
in other places; this seems like a good start. 
 
Fixed: 377620832 
Change-Id: Ib8f6f50176044859f77e13bcf3e6f41fa6b5a209 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6000165 
Reviewed-by: Matthias Liedtke <mliedtke@chromium.org> 
Auto-Submit: Jakob Kummerow <jkummerow@chromium.org> 
Commit-Queue: Jakob Kummerow <jkummerow@chromium.org> 
Cr-Commit-Position: refs/heads/main@{#97064}
```

* * *

Files:

  * M `src/codegen/bailout-reason.h`
  * M `src/wasm/baseline/liftoff-compiler.cc`
  * M `src/wasm/value-type.h`
  * M `src/wasm/wasm-js.cc`
  * A `test/mjsunit/regress/wasm/regress-377620832.js`

* * *

Hash: 47fb21842c13e750da83db884589b207a44bca70  
Date: Fri Nov 08 14:34:39 2024

* * *


---

**#6 — sp...@google.com — Nov 14, 2024 09:55AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $55000.00 for this report.  
  
Rationale for this decision:  
high-quality report of demonstrated RCE in a sandboxed process / the renderer  
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#7 — am...@chromium.org — Nov 14, 2024 10:05AM**

Congratulations Seunghyun! Excellent work on another solid high-quality report. Thank you for your efforts and reporting this issue to us! (Also, please let me know if you would like to donate this reward, similar to your recent past rewards. I'll work with you off bug to get you your donation info this week.)


---

**#8 — se...@gmail.com — Nov 18, 2024 11:10AM**

Thanks! I would like to donate the reward as done with my recent previous reports.


---

**#9 — ph...@google.com — Feb 17, 2025 11:27PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
