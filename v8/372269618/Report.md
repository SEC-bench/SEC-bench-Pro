# Type confusion due to DefaultReferenceValue() `undefined` default value for kNoExtern

Issue URL: https://issues.chromium.org/issues/372269618
VRP-Reward: 55000
Date: Oct 9, 2024 05:50PM


### VULNERABILITY DETAILS

#### Summary

Note: Bug split out from [b/372285204](<https://issuetracker.google.com/issues/372285204>) as this is technically a different bug.

[`DefaultReferenceValue()`](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/wasm-js.cc;drc=cf19534baf3ebba000e3cfaeba535e80d4806886;l=1383>) returns `undefined` value as a default value for externref (`kExtern`) and nullexternref (`kNoExtern`). This is a violation of wasm-gc spec as [only null values are allowed for reference types](<https://webassembly.github.io/spec/core/exec/runtime.html#:~:text=default%20value>). This results in type confusion due to inconsistencies from nullity checks being bypassed.

#### Details

[`DefaultReferenceValue()`](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/wasm-js.cc;drc=cf19534baf3ebba000e3cfaeba535e80d4806886;l=1383>) returns `undefined` value as a default value for `externref` (i.e. `kExtern`) and `nullexternref` (i.e. `kNoExtern`):

```
i::Handle<i::HeapObject> DefaultReferenceValue(i::Isolate* isolate,
                                               i::wasm::ValueType type) {
  DCHECK(type.is_object_reference());
  // Use undefined for JS type (externref) but null for wasm types as wasm does
  // not know undefined.
  if (type.heap_representation() == i::wasm::HeapType::kExtern ||
      type.heap_representation() == i::wasm::HeapType::kNoExtern) {
    return isolate->factory()->undefined_value();                     // [!] undefined, not null
  }
  return isolate->factory()->wasm_null();
}
```

This results in type confusion as the only allowed value for a nullexternref is a JS null.

The bug has multiple potential problems:

  1. Optimizing compilers (turbofan, turboshaft) may falsely optimize out code as unreachable, resulting in typer problems
  2. `kNoExtern` but `undefined` value may be confused into other types like `kExternString`

Attached PoC is a repro of #2.

#### Bisect

Bug introduced by commit [2e357c4](<https://chromiumdash.appspot.com/commit/2e357c4814954c6d83c336655209e14aa53911d4>) in M112 that introduced wasm null.

#### Suggested Fix

Change default reference value of extern & exn types to JS null.

### VERSION

See bisect commit release info in Chromium Dash for more info: [https://chromiumdash.appspot.com/commit/2e357c4814954c6d83c336655209e14aa53911d4](<https://chromiumdash.appspot.com/commit/2e357c4814954c6d83c336655209e14aa53911d4>)

Chrome Version: 112.0.5579.0 ~ latest  
Operating System: All

### REPRODUCTION CASE

Attached PoC which confuses `undefined` value into `kExternString` type, resulting in a fake string of length `0x7ff80000`. `charCodeAt` is continuously called which results in reading characters from `undefined` (near 0x68) up to `0x10000` where it finally hits a guard page and segfaults as below:

```
undefined
0 0
1 0
2 0
3 0
4 0
5 0
6 99
7 9
8 0
...
9c7c 0
9c7d 0
9c7e 35
9c7f 20
9c80 0
9c81 0
Received signal 11 SEGV_ACCERR 3b2400010000
Segmentation fault (core dumped)
```

### FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION

Type of crash: Renderer  
Crash State: Crashes on invalid memory access on WASM string-builtins `charCodeAt`

### CREDIT INFORMATION

Reporter credit: Seunghyun Lee (@0x10n) of CMU CyLab


---

**#2 — ph...@chromium.org — Oct 9, 2024 10:24PM**

Setting provisional FoundIn 128 and Severity High. I was able to reproduce the crash on M131, but on M128 I got

```
../372269618/poc (1).js:2219: TypeError: WebAssembly.Instance(): Import #0 "wasm:js-string": module is not an object or function
    let instance = new WebAssembly.Instance(module, ffi);
                   ^
TypeError: WebAssembly.Instance(): Import #0 "wasm:js-string": module is not an object or function
    at WasmModuleBuilder.instantiate (../372269618/poc (1).js:2219:20)
    at ../372269618/poc (1).js:2392:24
```

Assigned to V8 sheriff.


---

**#3 — se...@gmail.com — Oct 9, 2024 10:30PM**

WasmNull itself is introduced in M112, but the attached PoC uses [imported strings proposal](<https://github.com/WebAssembly/js-string-builtins>) shipped in M130: [https://crrev.com/c/5837501](<https://crrev.com/c/5837501>)

The bug itself does not depend on the proposal, but I'm struggling with turbofan/turboshaft and its unreachability analysis to emit an exploitable jit compiled code :(


---

**#4 — pe...@google.com — Oct 10, 2024 12:36AM**

Setting milestone because of s0/s1 severity.


---

**#5 — pe...@google.com — Oct 10, 2024 12:36AM**

Setting Priority to P1 to match Severity s1. If this is incorrect, please reset the priority. The automation bot account won't make this change again.


---

**#6 — se...@gmail.com — Oct 10, 2024 04:18AM**

Hi, I've found a way to exploit these patterns of type confusion. Will upload a PoC shortly, but note that every one of these types of patterns will be exploitable - this means that **all cases where a non-null value resides in a nullable bottom (`none`, `noextern`, `noexn`) type are exploitable**. This has quite a bit of an implication as AFAICT there were many such cases, e.g. [b/372285204](<https://issues.chromium.org/issues/372285204>), [https://crrev.com/c/5854179](<https://crrev.com/c/5854179>), etc.


---

**#7 — se...@gmail.com — Oct 10, 2024 05:28AM**

Attached PoC that obtains arbitrary WASM type confusion primitive and uses this to write to `0x42424242` resulting in a crash. Run the code with `--turboshaft-wasm` flag to repro, on versions >= 120.0.6090.0.

* * *

Key idea is as described in #1: Optimizing compilers (in this case, Turboshaft) may falsely optimize out code as unreachable, resulting in various typer problems. I have not checked whether or not Turbofan is exploitable as it is scheduled to be replaced with Turboshaft soon ([b/362191724](<https://issues.chromium.org/issues/362191724>)).

An overview of how type confusion is achieved is as the following pseudocode (FYI the PoC code is also well-commented):

  1. Set `$global : ref null noextern = undefined` using this bug
  2. Set `$local2 : ref any = dummy` where `dummy : ref $s2` of any WASM struct type
  3. Run `ref.as_non_null (global.get $global)`
     * `WasmGCTypeAnalyzer::ProcessAssertNotNull() -> WasmGCTypeAnalyzer::RefineTypeKnowledge()` computes [`wasm::Intersection()`](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/wasm-subtyping.cc;l=824>) of `ref null noextern` and `ref noextern`, which invalid and thus returns `kWasmBottom`
     * **Statically:`WasmGCTypeAnalyzer` now knows that this type is `is_uninhabited()` and thus following operations are marked as unreachable (but not DCE'd)**
     * **Runtime: As`$global != null`, `ref.as_non_null` successfully executes w/o trapping**
  4. Outer loop: 
     1. Inner loop: 
        1. `ref.cast $s2 (local.get $local2)`
           * **Typer currently tracks`$local2` type as `ref $s2`, thus the cast statically succeeds**
        2. Return the casted value (on second run)
        3. Dummy branch back to inner loop (not taken in runtime) 
           * This effectively creates a loop phi
     2. Set `$local2 = attacker-controlled $s1`
        * Now typer knows that `$local2 : wasm::Union(ref $s1, ref $s2)`
        * **This should trigger[ loop reprocessing](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/compiler/turboshaft/wasm-gc-typed-optimization-reducer.cc;l=24>) ([https://crrev.com/c/4958777](<https://crrev.com/c/4958777>)). However, as both the loops are considered unreachable this is not triggered.**
     3. Branch back to outer loop 
        * **As loop reprocessing has not occured, inner loop still tracks`$local2 : ref $s2`**

This results in arbitrary WASM type confusion as `ref $s1` is confused into `ref $s2`.

Again, it's worth emphasizing that **any type confusion, however subtle and seemingly useless it is as in this case, may be subject to this type of exploit through optimizing compilers**. [b/342602616#comment20](<https://issues.chromium.org/issues/342602616#comment20>) mentions that "nested loops" and mis-typing may possibly be exploitable but did not provide a concrete proof - this PoC indeed proves it to be exploitable. This shows that not only are non-null values in `none` types exploitable (which trivially are, as casts to any concrete wasm-gc types are possible), non-null values in opaque null-only types (`noextern`, `noexn`) are also exploitable.

I've verified that [https://crrev.com/c/5870231](<https://crrev.com/c/5870231>) \+ [https://crrev.com/c/5877013](<https://crrev.com/c/5877013>) which introduces top type does not prevent this exploit technique. This is because the typer is legitimately verifying that `ref.as_non_null (ref null none/noextern/noexn)` always traps, but due to type confusion that has already happened the conversion fails to trap on runtime. Mitigation for this may be to replace a potentially trapping operation to an explicit trap when the operation is statically determined to always trap so that even when some code that is analyzed to be statically unreachable can indeed be reached dynamically, we hit a trap instead of executing some stray code that has been ill-verified.


---

**#8 — se...@gmail.com — Oct 10, 2024 05:42AM**

As explained in #6, bugs like [https://crrev.com/c/5854179](<https://crrev.com/c/5854179>) are now all exploitable in the same way - the only change required is to receive a non-null `ref noextern` value from JS. The attached PoC achieves this by simply replacing `transfer()` to receive a non-null `ref noextern` and uses this value to confuse the typer.

```
let $glob = builder.addGlobal(kWasmNullExternRef, true).exportAs('global');
// ...
builder.addFunction('transfer', makeSig([wasmRefType(kWasmNullExternRef)], [])).addBody([
  kExprLocalGet, 0,
  kExprGlobalSet, $glob.index,
]).exportFunc();
// ...
// global = "some non-null value" (literally)
transfer("some non-null value");
```


---

**#9 — se...@gmail.com — Oct 10, 2024 05:55AM**

This is a crude patch that I've used to track the behavior of `WasmGCTypeAnalyzer`. `log_unreachable.txt` is the original log from the attached PoC in #7 and `log_normal.txt` is the log with `...typer_unreachable,` part commented out.


---

**#10 — se...@gmail.com — Oct 10, 2024 11:58AM**

Exploit that pops `calc` on a `--enable-features=WebAssemblyTurboshaft --no-sandbox` renderer in Windows x64, tested on `129.0.6668.90`. Also attached is the same exploit that uses [https://crrev.com/c/5854179](<https://crrev.com/c/5854179>) ([b/364917763](<https://issues.chromium.org/issues/364917763>)) to demonstrate the effectiveness of this technique, tested on the same version.

Other similar bugs like [https://crrev.com/c/5867409](<https://crrev.com/c/5867409>) may also work in the same way.


---

**#11 — cf...@google.com — Oct 10, 2024 06:26PM**

Great work!

mliedtke@, could you PTAL?


---

**#12 — ap...@google.com — Oct 11, 2024 05:35PM**

Project: v8/v8  
Branch: main  
Author: Thibaud Michaud <[thibaudm@chromium.org](<mailto:thibaudm@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/5922878](<https://chromium-review.googlesource.com/5922878>)

[wasm] Fix default externref/exnref reference

* * *

Expand for full commit details

```
[wasm] Fix default externref/exnref reference

- The default nullexternref should be null instead of undefined
- The default exnref/nullexnref should be null instead of wasm_null

R=mliedtke@chromium.org

Fixed: 372285204,372269618
Change-Id: Id5addce2b196f7ba81aac3c2dd9447a91ed2ce2b
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/5922878
Commit-Queue: Thibaud Michaud <thibaudm@chromium.org>
Reviewed-by: Matthias Liedtke <mliedtke@chromium.org>
Cr-Commit-Position: refs/heads/main@{#96531}
```

* * *

Files:

  * M `src/wasm/wasm-js.cc`

* * *

Hash: e7ccf0af1bdddd20dc58e1790a94739dba0209a3  
Date: Thu Oct 10 18:54:04 2024

* * *


---

**#13 — ml...@chromium.org — Oct 11, 2024 05:51PM**

Thanks a lot for the amazing analysis!

As Thibaud took over fixing the bug with the wrong default value for the null-types, I'll follow-up here on the other topics covered in this bug, mainly:

  1. Missing tracing for the `WasmGCTypeAnalyzer`.
  2. Reducing the risk of allowing logic bugs (like the `undefined` in a `nullexternref` to become a type confusion thanks to type optimizations.

See [comment #7](<https://issues.chromium.org/issues/372269618#comment7>):

> Mitigation for this may be to replace a potentially trapping operation to an explicit trap when the operation is statically determined to always trap so that even when some code that is analyzed to be statically unreachable can indeed be reached dynamically, we hit a trap instead of executing some stray code that has been ill-verified.

I think this is a good mitigation strategy. Right now, we don't get this for free as the analyzer doesn't store the information anywhere that operation `x` always traps if the result type of `x` results in `bottom`, it only tracks the incoming type. So `RefineTypeKnowledge` should probably not only return the known input type but also a bool whether the result was `bottom` / uninhabited which we can then store in a separate vector, similar to `input_type_map_`.


---

**#14 — ap...@google.com — Oct 12, 2024 12:33AM**

Project: v8/v8  
Branch: main  
Author: Matthias Liedtke <[mliedtke@chromium.org](<mailto:mliedtke@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/5925262](<https://chromium-review.googlesource.com/5925262>)

[turboshaft][wasm] Add tracing for WasmGCTypeAnalyzer

* * *

Expand for full commit details

```
[turboshaft][wasm] Add tracing for WasmGCTypeAnalyzer

Bug: 372269618
Change-Id: I49dd09a4b0fbe5bbd8d39e0fd21addc8537f45a4
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/5925262
Reviewed-by: Thibaud Michaud <thibaudm@chromium.org>
Commit-Queue: Matthias Liedtke <mliedtke@chromium.org>
Cr-Commit-Position: refs/heads/main@{#96545}
```

* * *

Files:

  * M `src/compiler/turboshaft/wasm-gc-typed-optimization-reducer.cc`
  * M `src/compiler/turboshaft/wasm-gc-typed-optimization-reducer.h`

* * *

Hash: 0df9105b154dc5627d81595b9aa379208d119fc2  
Date: Fri Oct 11 16:25:53 2024

* * *


---

**#15 — pe...@google.com — Oct 12, 2024 12:57AM**

Security Merge Request Consideration: This is sufficiently serious that it should be merged to extended stable. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M128. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately. Security Merge Request Consideration: This is sufficiently serious that it should be merged to other stable. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M129. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately. Security Merge Request Consideration: This is sufficiently serious that it should be merged to stable. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M130. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately. Security Merge Request: Thank you for fixing this security bug! We aim to ship security fixes as quickly as possible, to limit their opportunity for exploitation as an "n-day" (that is, a bug where git fixes are developed into attacks before those fixes reach users).

We have determined this fix is necessary on milestone(s): [].

Please answer the following questions so that we can safely process this merge request:

  1. Which CLs should be backmerged? (Please include Gerrit links.)
  2. Has this fix been verified on Canary to not pose any stability regressions?
  3. Does this fix pose any potential non-verifiable stability risks?
  4. Does this fix pose any known compatibility risks?
  5. Does it require manual verification by the test team? If so, please describe required testing.
  6. (no answer required) Please check the OS custom field to ensure all impacted OSes are checked!


---

**#16 — am...@chromium.org — Oct 12, 2024 03:22AM**

There are no further planned releases of M128 Extended or M129 Stable. Since this fix just landed today, it can be reviewed for merge on Monday / early next week and the fix will need to ship in the first respin of M130 Stable, planned for 22 October.


---

**#17 — se...@gmail.com — Oct 12, 2024 04:36AM**

Re #10: As expected, [b/366635354](<https://issues.chromium.org/issues/366635354>) also works with something like below:

```
let $glob = builder.addGlobal(wasmRefType(kWasmExternRef), true, false, [
  // any placeholder non-null extern
]).exportAs('global');

let typer_unreachable = [
  kExprGlobalGet, $glob.index,                      // decoder: ref extern, typer: ref extern
  kGCPrefix, kExprRefCastNull, kExternRefCode,      // decoder: ref null extern, typer: ref extern
  kGCPrefix, kExprRefCastNull, kNullExternRefCode,  // decoder: ref null noextern, typer: bot, runtime: IsNull passes
  kExprDrop,
];

// use the bug to write `global : ref extern = null`, then tier-up code with `typer_unreachable`
```

* * *

This closes up the exploitability analysis on the inverse case, `null -> non-null` confusion. It would be safe to assume that ANY type inconsistencies are exploitable with the current Turboshaft typer optimizations as it's smart enough to detect and optimize out analysis on many kinds of unreachable states. Below are some of the examples:

  * Nullability issues 
    * Non-null value in null-only type (`ref null no*`) 
      * Wasm-native type (`none`): Trivially exploitable - `ref.cast` into wasm-gc type and access it
      * Wasm-opaque type (`noextern`, `noexn`): Exploitable as shown in [comment#7](<https://issues.chromium.org/issues/372269618#comment7>) \- `ref.as_non_null`
        * [b/372269618](<https://issues.chromium.org/issues/372269618>), [b/372285204](<https://issues.chromium.org/issues/372285204>), [b/364917763](<https://issues.chromium.org/issues/364917763>)
    * Null value in non-null type (`ref`) 
      * `ref T`: Exploitable as shown in this comment - `ref.cast (ref null T) -> ref.cast (ref null null_T)` where `null_T := ToNullSentinel(T)`
        * [b/366635354](<https://issues.chromium.org/issues/366635354>)
  * Other typer bugs 
    * `br_on_cast*` typing issues in [b/352720899](<https://issues.chromium.org/issues/352720899>)?
    * Packed integer issues in [b/342602616](<https://issues.chromium.org/issues/342602616>), although top type patch in `wasm::Union` may block this
    * Implicit `kExternString` conversion issues in [b/324747822](<https://issues.chromium.org/issues/324747822>), where this report proves that wasm (or more specifically, Turboshaft compiler) can in fact pivot type inconsistencies in opaque type hierarchies (`externref`, and even `exnref`) further into exploitable confusions in wasm type hierarchy

I'm not sure if similar can be done with Turbofan as it has different typer optimizations. Creation of uninhabitable type (`kBottom`) is easily possible but there should be some optimization phases that either skips some type widening steps based on uninhabitable types as reachability, or is not skipped resulting in mistyped inputs propagating through optimizations (e.g. `IsSubtypeOf()` on a `kBottom` for type casts). But as the problem itself is evident I'm not going to dig down this rabbit hole anymore :)


---

**#18 — pe...@google.com — Oct 13, 2024 12:43AM**

Merge review required: M130 has already been cut for stable release.

Please answer the following questions so that we can safely process your merge request:

  1. Why does your merge fit within the merge criteria for these milestones?

  * Chrome Browser: [https://chromiumdash.appspot.com/branches](<https://chromiumdash.appspot.com/branches>)
  * Chrome OS: [https://goto.google.com/cros-release-branch-merge-guidelines](<https://goto.google.com/cros-release-branch-merge-guidelines>)

  2. What changes specifically would you like to merge? Please link to Gerrit.
  3. Have the changes been released and tested on canary?
  4. Is this a new feature? If yes, is it behind a Finch flag and are experiments active in any release channels?
  5. [Chrome OS only]: Was the change reviewed and approved by the Eng Prod Representative? [https://goto.google.com/cros-engprodcomponents](<https://goto.google.com/cros-engprodcomponents>)
  6. If this merge addresses a major issue in the stable channel, does it require manual verification by the test team? If so, please describe required testing.

Please contact the milestone owner if you have questions. Owners: eakpobaro (Android), eakpobaro (iOS), gmpritchard (ChromeOS), danielyip (Desktop)


---

**#19 — ml...@chromium.org — Oct 14, 2024 05:14PM**

1. It's a security vulnerability.
  2. [https://chromium-review.googlesource.com/c/v8/v8/+/5922878](<https://chromium-review.googlesource.com/c/v8/v8/+/5922878>)
  3. Yes, [https://chromiumdash.appspot.com/commit/e7ccf0af1bdddd20dc58e1790a94739dba0209a3](<https://chromiumdash.appspot.com/commit/e7ccf0af1bdddd20dc58e1790a94739dba0209a3>)
  4. No.
  5. `-`
  6. No.


---

**#20 — ap...@google.com — Oct 14, 2024 08:08PM**

Project: v8/v8  
Branch: main  
Author: Matthias Liedtke <[mliedtke@chromium.org](<mailto:mliedtke@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/5928643](<https://chromium-review.googlesource.com/5928643>)

[turboshaft][wasm] WasmGCTypedOptimizationReducer: Emit unconditional traps

* * *

Expand for full commit details

```
[turboshaft][wasm] WasmGCTypedOptimizationReducer: Emit unconditional traps

This enforces code to be unreachable when the analyzer came to the
conclusion that they were unreachable, even if that wasn't the case
(e.g. due to logic bugs).

Bug: 42204049, 372269618
Change-Id: I19f8e2161372d1dcff6838999b8cef7435373d65
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/5928643
Reviewed-by: Jakob Kummerow <jkummerow@chromium.org>
Commit-Queue: Matthias Liedtke <mliedtke@chromium.org>
Auto-Submit: Matthias Liedtke <mliedtke@chromium.org>
Cr-Commit-Position: refs/heads/main@{#96564}
```

* * *

Files:

  * M `src/compiler/turboshaft/assembler.h`
  * M `src/compiler/turboshaft/wasm-gc-typed-optimization-reducer.cc`
  * M `src/compiler/turboshaft/wasm-gc-typed-optimization-reducer.h`

* * *

Hash: be8ace6daaea44550f89355ca429811bfecca1d5  
Date: Mon Oct 14 12:10:23 2024

* * *


---

**#21 — am...@chromium.org — Oct 16, 2024 10:22PM**

[https://crrev.com/c/5922878](<https://crrev.com/c/5922878>) approved for merge to M130, please merge to 13.0 at your earliest convenience / before EOD tomorrow 17 October so this fix can be included in the next Stable channel update -- thanks!


---

**#22 — ap...@google.com — Oct 16, 2024 10:44PM**

Project: v8/v8  
Branch: main  
Author: Matthias Liedtke <[mliedtke@chromium.org](<mailto:mliedtke@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/5937805](<https://chromium-review.googlesource.com/5937805>)

[turboshaft-wasm] Use uninhabited instead of bottom type for unconditional trap paths

* * *

Expand for full commit details

```
[turboshaft-wasm] Use uninhabited instead of bottom type for unconditional trap paths

`ref none` is the same as `unreachable` for the wasm-gc type
reductions, however we do not normalize these types, so we should
always use is_uninhabited() instead of comparison with bottom.

Bug: 42204049, 372269618
Change-Id: I0fdbd5c8d90dfb6d905ef4c0820cda9bee19e0d9
Fixed: 373702823
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/5937805
Reviewed-by: Jakob Kummerow <jkummerow@chromium.org>
Commit-Queue: Jakob Kummerow <jkummerow@chromium.org>
Auto-Submit: Matthias Liedtke <mliedtke@chromium.org>
Cr-Commit-Position: refs/heads/main@{#96624}
```

* * *

Files:

  * M `src/compiler/turboshaft/wasm-gc-typed-optimization-reducer.h`
  * A `test/mjsunit/regress/wasm/regress-373702823.js`

* * *

Hash: 160612a75397f9048e3824d5177ed702742f22ff  
Date: Wed Oct 16 13:48:58 2024

* * *


---

**#23 — ap...@google.com — Oct 17, 2024 12:12AM**

Project: v8/v8  
Branch: refs/branch-heads/13.0  
Author: Thibaud Michaud <[thibaudm@chromium.org](<mailto:thibaudm@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/5937812](<https://chromium-review.googlesource.com/5937812>)

Merged: [wasm] Fix default externref/exnref reference

* * *

Expand for full commit details

```
Merged: [wasm] Fix default externref/exnref reference

- The default nullexternref should be null instead of undefined
- The default exnref/nullexnref should be null instead of wasm_null

(cherry picked from commit e7ccf0af1bdddd20dc58e1790a94739dba0209a3)

Change-Id: I5b32e80f2eb59b29113232f9e2f59a8803915cb3
Fixed: 372285204,372269618
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/5937812
Reviewed-by: Thibaud Michaud <thibaudm@chromium.org>
Auto-Submit: Matthias Liedtke <mliedtke@chromium.org>
Commit-Queue: Thibaud Michaud <thibaudm@chromium.org>
Cr-Commit-Position: refs/branch-heads/13.0@{#35}
Cr-Branched-From: 4be854bd71ea878a25b236a27afcecffa2e29360-refs/heads/13.0.245@{#1}
Cr-Branched-From: 1f5183f7ad6cca21029fd60653d075730c644432-refs/heads/main@{#96103}
```

* * *

Files:

  * M `src/wasm/wasm-js.cc`

* * *

Hash: d9893f4856af26e78ba5021063ee2b1c61a3023b  
Date: Thu Oct 10 18:54:04 2024

* * *


---

**#24 — pe...@google.com — Oct 17, 2024 12:19AM**

LTS Milestone M126

This issue has been flagged as a merge candidate for Chrome OS' LTS channel. If selected, our merge team will handle any additional merges. To help us determine if this issue requires a merge to LTS, please answer this short questionnaire:

  1. Was this issue a regression for the milestone it was found in?
  2. Is this issue related to a change or feature merged after the latest LTS Milestone?


---

**#25 — pe...@google.com — Oct 21, 2024 02:45PM**

This issue requires additional review before it can be merged to the LTS channel. Please answer the following questions to help us evaluate this merge:

  1. Number of CLs needed for this fix and links to them.
  2. Level of complexity (High, Medium, Low - Explain)
  3. Has this been merged to a stable release? beta release?
  4. Overall Recommendation (Yes, No)


---

**#26 — ml...@chromium.org — Oct 21, 2024 05:22PM**

1. 1, [https://chromium-review.googlesource.com/c/v8/v8/+/5922878](<https://chromium-review.googlesource.com/c/v8/v8/+/5922878>)
  2. Low, the change is very local and only changes the default value for specific wasm-gc types in wasm objects (e.g. Table) exposed via the JS API. These types (nulltypes, similar to `nullptr_t`) can only hold a single possible value, their use in a table is therefore not very useful (i.e. any real application would not have a good reason to even use this type as a table element type.
  3. Yes, merged to 130.
  4. Yes, this fixes a security vulnerability.


---

**#27 — qk...@google.com — Oct 21, 2024 05:27PM**

1\. [https://chromium-review.googlesource.com/c/v8/v8/+/5937253](<https://chromium-review.googlesource.com/c/v8/v8/+/5937253>)  
2\. Low, no conflict  
3\. 130  
4\. Yes, because the bug was introduced in 2e357c4 in M112 according to the description, so it could happen on the latest version.


---

**#28 — sp...@google.com — Oct 23, 2024 05:55AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $55000.00 for this report.  
  
Rationale for this decision:  
$55,000 for high quality report of demonstrated RCE in a sandboxed process / the renderer  
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#29 — am...@chromium.org — Oct 23, 2024 06:08AM**

Congratulations Seunghyun! Thank you for your efforts on another great report demonstrating RCE in V8 with an exploit -- excellent work!


---

**#30 — se...@gmail.com — Oct 23, 2024 06:58AM**

Thanks for going through all the reports :D

I still do think that [b/372285204](<https://issues.chromium.org/issues/372285204>) is technically a different bug as there are two independent problems, just fixed in a single CL:

  1. Missing case for `exn` type hierarchy leading to `wasm_null` leakage - adding `exn` to the conditional would still have caused the latter problem
  2. Misuse of `undefined` value for host type hierarchies - changing it to `null` would still have caused the former problem

I don't have strong opinions on this decision - especically since the fix is indeed local in terms of code - but I do think neither bug implies the other, especially from [b/372285204](<https://issues.chromium.org/issues/372285204>) to this bug. But yeah, I thought this would score a "novelty bonus" for the first demonstrated & RCA'd Turboshaft typer exploit technique but instead landed a dup which is a bit discouraging ;_;


---

**#31 — se...@gmail.com — Oct 31, 2024 12:50AM**

Hi, seems like I haven't added this for my recent reports so adding it in bulk - I'd like to donate the bounty through Benevity. Thanks!


---

**#32 — am...@chromium.org — Nov 5, 2024 03:28AM**

re c#31 -- thank you for the heads up. I'm just returning from OOO so I've tagged this for donation processing. I'll try to get back to you with your benevity donation information by EOW. Thanks for your patience!


---

**#33 — ap...@google.com — Nov 7, 2024 09:42PM**

Project: v8/v8  
Branch: refs/branch-heads/12.6  
Author: Thibaud Michaud <[thibaudm@chromium.org](<mailto:thibaudm@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/5937253](<https://chromium-review.googlesource.com/5937253>)

[M126-LTS][wasm] Fix default externref/exnref reference

* * *

Expand for full commit details

```
[M126-LTS][wasm] Fix default externref/exnref reference 
 
- The default nullexternref should be null instead of undefined 
- The default exnref/nullexnref should be null instead of wasm_null 
 
R=mliedtke@chromium.org 
 
(cherry picked from commit e7ccf0af1bdddd20dc58e1790a94739dba0209a3) 
 
Fixed: 372285204,372269618 
Change-Id: Id5addce2b196f7ba81aac3c2dd9447a91ed2ce2b 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/5922878 
Commit-Queue: Thibaud Michaud <thibaudm@chromium.org> 
Reviewed-by: Matthias Liedtke <mliedtke@chromium.org> 
Cr-Original-Commit-Position: refs/heads/main@{#96531} 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/5937253 
Reviewed-by: Clemens Backes <clemensb@chromium.org> 
Commit-Queue: Gyuyoung Kim (xWF) <qkim@google.com> 
Cr-Commit-Position: refs/branch-heads/12.6@{#80} 
Cr-Branched-From: 3c9fa12db3183a6f4ea53d2675adb66ea1194529-refs/heads/12.6.228@{#2} 
Cr-Branched-From: 981bb15ba4dbf9e2381dfc94ec2c4af0b9c6a0b6-refs/heads/main@{#93835}
```

* * *

Files:

  * M `src/wasm/wasm-js.cc`

* * *

Hash: e379c539eac7ade505e8625116f35b1288572959  
Date: Thu Oct 10 18:54:04 2024

* * *


---

**#34 — pe...@google.com — Jan 19, 2025 12:43AM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
