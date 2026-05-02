# Wasm type nullability confusion due to non-nullable exnref in catch(_all)_ref

Issue URL: https://issues.chromium.org/issues/374790906
VRP-Reward: 55000
Date: Oct 22, 2024 05:42AM


Another round of subtle nullability issues in opaque types exploitable through Turboshaft. The commit that introduces this issue is less than seven days old, but I've decided not to hold on to it for a week as it seems that **the exception handling spec itself might have a soundness issue** that could also affect any other engines that depend on it as ground truth.

* * *

### VULNERABILITY DETAILS

#### Summary

Wasm type nullability confusion due to allowing non-nullable exn in `catch_ref` / `catch_all_ref`. These operations can catch any non-trap exceptions, including `null` that could be thrown from JS. However, the catch type is allowed to be non-nullable, resulting in type nullability confusion issue that is exploitable through Turboshaft optimization (as also demonstrated in [b/372269618#comment7](<https://issues.chromium.org/issues/372269618#comment7>) and [b/373703277#comment13](<https://issues.chromium.org/issues/373703277#comment13>)).

Triggering this bug requires a staged Wasm feature, `--experimental-wasm-exnref`.

#### Details

From commit [7cb6188](<https://chromiumdash.appspot.com/commit/7cb6188cf9132d43e6c631befb0584a47a0e7d69>), it is now possible to have a non-nullable exnref catch type in `catch_ref` / `catch_all_ref` as the pushed exception is assumed to have type `ref exn`:

```
      if (catch_case.kind == kCatchRef || catch_case.kind == kCatchAllRef) {
        stack_.EnsureMoreCapacity(1, this->zone_);
        Push(ValueType::Ref(HeapType::kExn));         // [!] non-nullable ref exn type
        push_count += 1;
      }
```

However, an imported JS function can throw anything including `null` which can be caught by such operations, leading to a type nullability confusion issue - "null value in non-null type" case, exploitable as per [b/373703277#comment13](<https://issues.chromium.org/issues/373703277#comment13>).

Note that this change is likely based on the spec discussion in [https://github.com/WebAssembly/exception-handling/issues/336](<https://github.com/WebAssembly/exception-handling/issues/336>), which indicates that there might be either a spec unsoundness issue or a broken exception catching mechanism in Chrome.

#### Bisect

Bug introduced by commit [7cb6188](<https://chromiumdash.appspot.com/commit/7cb6188cf9132d43e6c631befb0584a47a0e7d69>) that allows non-nullable exn catch type.

#### Suggested Fix

Revisit the spec discussion in [https://github.com/WebAssembly/exception-handling/issues/336](<https://github.com/WebAssembly/exception-handling/issues/336>), and decide on one of the following:

  * Commit [7cb6188](<https://chromiumdash.appspot.com/commit/7cb6188cf9132d43e6c631befb0584a47a0e7d69>) should be reverted, i.e. `null` exceptions can be catched in Wasm
  * `null` exceptions should be considered as a type of trap that cannot be caught in Wasm
  * Add an implicit `AssertNotNull` after catching the exception to trap on `null` exceptions, effectively preventing null exceptions from being propagated into Wasm code

### VERSION

See bisect commit release info in Chromium Dash for more info: [https://chromiumdash.appspot.com/commit/7cb6188cf9132d43e6c631befb0584a47a0e7d69](<https://chromiumdash.appspot.com/commit/7cb6188cf9132d43e6c631befb0584a47a0e7d69>)

Chrome Version: 132.0.6785.0 (V8 commit [7cb6188](<https://chromiumdash.appspot.com/commit/7cb6188cf9132d43e6c631befb0584a47a0e7d69>)) ~ latest  
Operating System: All

### REPRODUCTION CASE

Attached as `poc.js` which exploits the type confusion via Turboshaft to obtain in-sandbox exploit primitives, and crashes on arbitrary caged write attempt. Run d8 with `--turboshaft-wasm --experimental-wasm-exnref` flags.

Also attached is yet another full exploit `exp.html` that pops `calc` on Windows x64 Chrome releases on canary versions 132.0.6785.0 ~ latest. Run Chrome with `--enable-features=WebAssemblyTurboshaft --js-flags=--experimental-wasm-exnref --no-sandbox` flags.

### FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION

Type of crash: Renderer  
Crash State: Crashes on arbitrary caged write attempt from JIT-compiled Wasm function (on d8), arbitrary code execution (on Chrome)

### CREDIT INFORMATION

Reporter credit: Seunghyun Lee (@0x10n) of CMU CyLab


---

**#2 — ps...@google.com — Oct 22, 2024 06:18AM**

Thank you for the report.   
  
Passing off to V8 Shepard and adding CL owner to CC list. clemensb@ I am setting tentative severity and priority, feel free to adjust as you see fit.


---

**#3 — se...@gmail.com — Oct 22, 2024 07:28AM**

Seems that this is more of a Chrome-specific problem, similar issues have been discussed in:

  * [https://github.com/WebAssembly/exception-handling/issues/282](<https://github.com/WebAssembly/exception-handling/issues/282>)
  * [https://github.com/WebAssembly/exception-handling/pull/269#issuecomment-2006814205](<https://github.com/WebAssembly/exception-handling/pull/269#issuecomment-2006814205>)

Theoretically all exceptions caught must be a `WA.Exception` object, even for non-`WA.Exception` JS exceptions as they must have been transparently wrapped into a `WA.Exception` of tag `WA.JSTag`. However, Chrome seems to elide the wrap-unwrap operation with `WA.JSTag` in the hopes that this operation will be unobservable - in fact, any `exnref` that crosses the Wasm-to-JS boundary needs to cross it through `throw_ref` which would unwrap this and thus make the wrap-unwrap operation effectively unobservable (and `WA.JSTag` cannot be used to create a `WA.Exception` via JS API, which completes the "unobservability" part AFAICT).

The spec is correct that any caught exceptions are allowed to be typed as non-null, because it should be a valid non-null `WA.Exception`. However, by eliding the `WA.Exception` wrapping we are effectively allowing an illegal value of `null` in `ref exn` which results in Turboshaft typer optimization problems as seen here.

Thus, a proper fix would be to actually do the `WA.Exception` wrap-unwrap in Wasm-JS boundary. An alternative approach might be to fully "internalize" the `exn` type and use `wasm_null` instead for the null sentinel.


---

**#4 — th...@chromium.org — Oct 22, 2024 05:31PM**

Oof, that's quite annoying. Thanks for (yet another) great analysis.  
Yes, that issue is specific to our implementation. According to the spec, the null value (or any thrown JS value) should be wrapped in a `WA.Exception`.  
I think we still need to try and avoid doing the wrapping/unwrapping exactly when the spec says (at language boundary), because this requires allocating an object during stack unwinding which would be tricky (GC is not allowed there).  
But I think we can get away with doing the wrapping/unwrapping when we catch/rethrow the exception.


---

**#5 — pe...@google.com — Oct 23, 2024 12:39AM**

Setting milestone because of s0/s1 severity.


---

**#6 — pe...@google.com — Oct 23, 2024 12:39AM**

This is a serious security regression. If you are not able to fix this quickly, please revert the change that introduced it.

If this doesn't affect a release branch, or has not been properly classified for severity, please update the Security Impact hotlist or the Severity field, and remove the ReleaseBlock hotlist.


---

**#7 — th...@chromium.org — Oct 23, 2024 07:22PM**

I decided to go with the "wasm_null" option in the end:  
[https://chromium-review.googlesource.com/c/v8/v8/+/5953226](<https://chromium-review.googlesource.com/c/v8/v8/+/5953226>)  
This addresses the main issue which is the confusion between JS null and exnref null, while still avoiding the unnecessary wrapping/unwrapping.


---

**#8 — ap...@google.com — Oct 23, 2024 11:49PM**

Project: v8/v8  
Branch: main  
Author: Thibaud Michaud <[thibaudm@chromium.org](<mailto:thibaudm@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/5953226](<https://chromium-review.googlesource.com/5953226>)

[wasm][exnref] Use wasm_null for exnref

* * *

Expand for full commit details

```
[wasm][exnref] Use wasm_null for exnref 
 
A JS null caught in wasm as an exnref with catch_(all_)ref should be 
observably different from a null exnref: a JS null should behave like a 
regular JS exception with null as the externref package, while a null 
exnref is the actual null value for this type. In particular, a JS 
null exception can be rethrown while a null exnref cannot. 
Represent null exnrefs with wasm_null instead of JS null to avoid the 
confusion. 
 
R=jkummerow@chromium.org 
 
Fixed: 374790906 
Change-Id: If9f16a24407ee7d1399613255c3f14e0a6ebef9e 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/5953226 
Reviewed-by: Jakob Kummerow <jkummerow@chromium.org> 
Commit-Queue: Thibaud Michaud <thibaudm@chromium.org> 
Cr-Commit-Position: refs/heads/main@{#96782}
```

* * *

Files:

  * M `src/builtins/wasm.tq`
  * M `src/compiler/turboshaft/builtin-call-descriptors.h`
  * M `src/compiler/wasm-compiler.cc`
  * M `src/compiler/wasm-compiler.h`
  * M `src/wasm/baseline/liftoff-compiler.cc`
  * M `src/wasm/graph-builder-interface.cc`
  * M `src/wasm/turboshaft-graph-interface.cc`
  * M `src/wasm/value-type.h`
  * M `src/wasm/wasm-builtin-list.h`
  * M `src/wasm/wrappers.cc`
  * M `test/mjsunit/wasm/gc-casts-exnref.js`

* * *

Hash: 9997fc01395257cffd7231f14bb4d9fa7eaa9665  
Date: Wed Oct 23 15:27:44 2024

* * *


---

**#9 — sp...@google.com — Nov 14, 2024 09:55AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $55000.00 for this report.  
  
Rationale for this decision:  
high-quality report with demonstration of RCE in the renderer  
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#10 — am...@chromium.org — Nov 14, 2024 10:08AM**

Congratulations on another great report, Seunghyun! Thank you for your efforts and reporting this issue to us -- nice work.


---

**#11 — se...@gmail.com — Nov 18, 2024 11:09AM**

Thanks! I would like to donate the reward as done with my recent previous reports.


---

**#12 — pe...@google.com — Jan 31, 2025 12:42AM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
