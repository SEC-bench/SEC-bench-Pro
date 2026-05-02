# Debug check failed: !type.is_uninhabited(). in v8

Issue URL: https://issues.chromium.org/issues/324747822
VRP-Reward: 8000
Date: Feb 12, 2024 07:55PM


VULNERABILITY DETAILS

## INTRODUCE

After bisect, it was determined that following commit caused this problem.

  * Commit Info 
    * Version: 92242
    * link: [https://crrev.com/3f2471d0abe711c92ddb3d6fe17bc22d9955f2b8](<https://crrev.com/3f2471d0abe711c92ddb3d6fe17bc22d9955f2b8>)
  * Commit Message

```
commit 3f2471d0abe711c92ddb3d6fe17bc22d9955f2b8
Author: Matthias Liedtke <mliedtke@chromium.org>
Date:   Wed Feb 7 16:34:41 2024 +0100

    [turboshaft][wasm] WasmGCTypeReducer: Check for uninhabited, not bottom
    
    wasm::Type::AsNonNull() converts `ref null T` to `ref T`.
    For any T in {none, nofunc, noextern} this will result in types which
    do not have a valid value, i.e. cannot occur in reachable code.
    
    Therefore we should check for `type.is_uninhabited()` instead of
    `type == kWasmBottom` in all cases where we care about "invalid" types.
    
    Bug: v8:14108
    Change-Id: I2ab7c542527938535bcb6eb9ac29d7a8748209d5
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/5277240
    Auto-Submit: Matthias Liedtke <mliedtke@chromium.org>
    Commit-Queue: Jakob Kummerow <jkummerow@chromium.org>
    Reviewed-by: Jakob Kummerow <jkummerow@chromium.org>
    Cr-Commit-Position: refs/heads/main@{#92242}
```

## CRASH LOG

  * Debug output

```
# CMD: /tmp/d8-linux32-debug-v8-component-92272/d8 --allow-natives-syntax --expose-gc --future --fuzzing --jit-fuzzing --harmony --omit-quit --js-staging --wasm-staging --no-wasm-loop-unrolling --no-wasm-loop-peeling poc.js
# OUTPUT ==============================================================

#
# Fatal error in ../../src/compiler/turboshaft/wasm-gc-type-reducer.cc, line 396
# Debug check failed: !type.is_uninhabited().
#
#
#
#FailureMessage Object: 0xe17f9d90
==== C stack trace ===============================

    /tmp/d8-linux32-debug-v8-component-92272/libv8_libbase.so(v8::base::debug::StackTrace::StackTrace()+0x1f) [0xf7ecb19f]
    /tmp/d8-linux32-debug-v8-component-92272/libv8_libplatform.so(+0x16274) [0xf7e77274]
    /tmp/d8-linux32-debug-v8-component-92272/libv8_libbase.so(V8_Fatal(char const*, int, char const*, ...)+0xf7) [0xf7eaa5a7]
    /tmp/d8-linux32-debug-v8-component-92272/libv8_libbase.so(+0x26fa6) [0xf7ea9fa6]
    /tmp/d8-linux32-debug-v8-component-92272/libv8_libbase.so(V8_Dcheck(char const*, int, char const*)+0x31) [0xf7eaa5f1]
    /tmp/d8-linux32-debug-v8-component-92272/libv8.so(v8::internal::compiler::turboshaft::WasmGCTypeAnalyzer::CreateMergeSnapshot(v8::base::Vector<v8::internal::compiler::turboshaft::SnapshotTable<v8::internal::wasm::ValueType, v8::internal::compiler::turboshaft::NoKeyData>::Snapshot const>, v8::base::Vector<bool const>)+0x53a) [0xf730e0ca]
    /tmp/d8-linux32-debug-v8-component-92272/libv8.so(v8::internal::compiler::turboshaft::WasmGCTypeAnalyzer::Run()+0x3a5) [0xf730d585]
    /tmp/d8-linux32-debug-v8-component-92272/libv8.so(void v8::internal::compiler::turboshaft::GraphVisitor<v8::internal::compiler::turboshaft::ReducerStack<v8::internal::compiler::turboshaft::Assembler<v8::internal::compiler::turboshaft::reducer_list<v8::internal::compiler::turboshaft::TurboshaftAssemblerOpInterface, v8::internal::compiler::turboshaft::GraphVisitor, v8::internal::compiler::turboshaft::WasmLoadEliminationReducer, v8::internal::compiler::turboshaft::WasmGCTypeReducer, v8::internal::compiler::turboshaft::TSReducerBase>>, false, v8::internal::compiler::turboshaft::WasmLoadEliminationReducer, v8::internal::compiler::turboshaft::WasmGCTypeReducer, v8::internal::compiler::turboshaft::TSReducerBase>>::VisitGraph<false>()+0x4d) [0xf72d393d]
    /tmp/d8-linux32-debug-v8-component-92272/libv8.so(v8::internal::compiler::turboshaft::CopyingPhaseImpl<v8::internal::compiler::turboshaft::WasmLoadEliminationReducer, v8::internal::compiler::turboshaft::WasmGCTypeReducer>::Run(v8::internal::compiler::turboshaft::Graph&, v8::internal::Zone*, bool)+0xf4) [0xf72d37b4]
    /tmp/d8-linux32-debug-v8-component-92272/libv8.so(v8::internal::compiler::turboshaft::WasmGCOptimizePhase::Run(v8::internal::Zone*)+0xb4) [0xf72c1774]
    /tmp/d8-linux32-debug-v8-component-92272/libv8.so(auto v8::internal::compiler::PipelineImpl::Run<v8::internal::compiler::turboshaft::WasmGCOptimizePhase>()+0xd0) [0xf7116af0]
    /tmp/d8-linux32-debug-v8-component-92272/libv8.so(v8::internal::compiler::Pipeline::GenerateWasmCodeFromTurboshaftGraph(v8::internal::OptimizedCompilationInfo*, v8::internal::wasm::CompilationEnv*, v8::internal::compiler::WasmCompilationData&, v8::internal::compiler::MachineGraph*, v8::internal::wasm::WasmFeatures*, v8::internal::compiler::CallDescriptor*)+0x78d) [0xf711577d]
    /tmp/d8-linux32-debug-v8-component-92272/libv8.so(v8::internal::compiler::turboshaft::ExecuteTurboshaftWasmCompilation(v8::internal::wasm::CompilationEnv*, v8::internal::compiler::WasmCompilationData&, v8::internal::wasm::WasmFeatures*)+0x317) [0xf73dea27]
    /tmp/d8-linux32-debug-v8-component-92272/libv8.so(v8::internal::wasm::WasmCompilationUnit::ExecuteFunctionCompilation(v8::internal::wasm::CompilationEnv*, v8::internal::wasm::WireBytesStorage const*, v8::internal::Counters*, v8::internal::wasm::WasmFeatures*)+0x727) [0xf68effa7]
    /tmp/d8-linux32-debug-v8-component-92272/libv8.so(v8::internal::wasm::WasmCompilationUnit::ExecuteCompilation(v8::internal::wasm::CompilationEnv*, v8::internal::wasm::WireBytesStorage const*, v8::internal::Counters*, v8::internal::wasm::WasmFeatures*)+0x18a) [0xf68ef48a]
    /tmp/d8-linux32-debug-v8-component-92272/libv8.so(+0x334cc9c) [0xf694cc9c]
    /tmp/d8-linux32-debug-v8-component-92272/libv8.so(+0x334c599) [0xf694c599]
    /tmp/d8-linux32-debug-v8-component-92272/libv8_libplatform.so(v8::platform::DefaultJobWorker::Run()+0xcb) [0xf7e75e9b]
    /tmp/d8-linux32-debug-v8-component-92272/libv8_libplatform.so(v8::platform::DefaultWorkerThreadsTaskRunner::WorkerThread::Run()+0x9f) [0xf7e7862f]
    /tmp/d8-linux32-debug-v8-component-92272/libv8_libbase.so(+0x46dbe) [0xf7ec9dbe]
    /lib/i386-linux-gnu/libc.so.6(+0x86c01) [0xf2c86c01]
    /lib/i386-linux-gnu/libc.so.6(+0x12372c) [0xf2d2372c]
Received signal 6
```

## Other

Please note to include the flags `--allow-natives-syntax --expose-gc --future --fuzzing --jit-fuzzing --harmony --omit-quit --js-staging --wasm-staging --no-wasm-loop-unrolling --no-wasm-loop-peeling` for clusterfuzz classification.

VERSION Tested on v8 version: 12.3.0 - 12.3.0

REPRODUCTION CASE

  1. Download debug v8 from: gs://v8-asan/linux32-debug/d8-linux32-debug-v8-component-92272.zip
  2. Run: `d8 --allow-natives-syntax --expose-gc --future --fuzzing --jit-fuzzing --harmony --omit-quit --js-staging --wasm-staging --no-wasm-loop-unrolling --no-wasm-loop-peeling poc.js`

FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION Type of crash: tab

CREDIT INFORMATION Reporter credit: Jerry


---

**#2 — je...@gmail.com — Feb 12, 2024 08:04PM**

This error was discovered during the optimization process of V8's Turboshaft compiler, especially in the handling of WebAssembly's Garbage Collection (GC) type system.

## Bug Description

  * File Location: ../../src/compiler/turboshaft/wasm-gc-type-reducer.cc, line 396
  * Error Type: Debug check failed: !type.is_uninhabited(). This indicates that at this point in the code, there is a situation that was not expected to occur: the existence of an "uninhabited" type (i.e., a type that has no valid values). In WebAssembly, a type is considered uninhabited if it cannot represent any value, for example, a reference type that cannot possibly exist.

## Possible Causes

  * Type Conversion Logic Error: During the conversion process in wasm::Type::AsNonNull(), converting ref null T to ref T might not have been correctly handled for specific types (such as none, nofunc, noextern), resulting in the creation of uninhabited types.

  * Insufficient Type Checking: In some code paths, there was not enough checking for types that should be considered invalid or impossible, leading to these types being used in places they should not appear.

## Suggested Solutions

  * Correct Type Conversion Logic: Carefully review the implementation of AsNonNull and related functions to ensure all possible types are correctly handled, especially those cases that might lead to uninhabited types.

  * Enhance Type Checking: Introduce stricter checks in the code that handles types, particularly before using types for critical decisions or optimizations, to ensure the types are not uninhabited.


---

**#3 — cl...@appspot.gserviceaccount.com — Feb 13, 2024 07:17AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=6240535737466880](<https://clusterfuzz.com/testcase?key=6240535737466880>).


---

**#4 — wf...@chromium.org — Feb 13, 2024 07:18AM**

Severity and Found In are provisional. Assigning to current v8 triage team


---

**#5 — 24...@project.gserviceaccount.com — Feb 13, 2024 07:44AM**

Testcase 6240535737466880 failed to reproduce the crash. Please inspect the program output at [https://clusterfuzz.com/testcase?key=6240535737466880](<https://clusterfuzz.com/testcase?key=6240535737466880>).


---

**#6 — je...@gmail.com — Feb 13, 2024 08:31AM**

Please use 32-bits debug d8 to run clusterfuzzer


---

**#7 — cl...@appspot.gserviceaccount.com — Feb 13, 2024 08:57AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=6216599381409792](<https://clusterfuzz.com/testcase?key=6216599381409792>).


---

**#8 — ml...@chromium.org — Feb 13, 2024 06:17PM**

Thanks for the bug report.  
Assigning to me as I introduced that DCHECK. I will take a look.


---

**#9 — ml...@chromium.org — Feb 13, 2024 08:42PM**

Attached is the minimal repro needed to reproduce tha successfully finishes if the bug wasn't there (or when only running liftoff).  
The fix should be trivial.  
I am not sure yet if this can lead to any observable behavior differences in release builds or if it exposes a security vulnerability.


---

**#10 — pe...@google.com — Feb 14, 2024 12:41AM**

Setting milestone because of s0/s1 severity.


---

**#11 — pe...@google.com — Feb 14, 2024 12:41AM**

Setting Priority to P1 to match Severity s1. If this is incorrect, please reset the priority. The automation bot account won't make this change again.


---

**#12 — ml...@chromium.org — Feb 16, 2024 12:24AM**

The fix: [https://chromium-review.googlesource.com/c/v8/v8/+/5293801](<https://chromium-review.googlesource.com/c/v8/v8/+/5293801>)  
  
This is a special kind of type confusion that happens for wasm's "js-string-builtins".  
This is a new proposal behind an Origin Trial flag that is meant to replace the older "stringref" wasm proposal (also behind an OT) which didn't reach consensus to advance further in the standardization process.  
As V8 supports both experimentally and they both handle strings, both experiments share a common implementation in the compilers.  
However, they use different type hierarchies in wasm (for stringref the string type is a subtype of "anyref", for js-string-builtins the string values are typed as "externref"). To refine types during optimizations, we re-used the string type from the stringref proposal as an internal type to represent "externref" values that we know are always strings. Our typer however would then compare types from different hierarchies with each other which is not meant to happen and therefore lead to errors.  
  
While a type confusion sounds like offering a lot of possibilities to abuse this, it might actually be quite difficult:  
An externref can be null, a Smi, some heap object that WebAssembly doesn't care about or a string. We can now cause type confusions between these cases but what can be done with such a value is rather limited (because the confusion is limited to the externref hierarchy in wasm).  
For externref, wasm can't do much with it. So the best attack option is probably to make the typer think that something is a string while it is actually some JavaScript object.  
This should give read-only access to the heap. Strings itself aren't writable. Wasm has operations that flatten a string if it is a non-flattened string. I am not familiar enough with the string handling to assess if this offers options to corrupt the heap.  
  
The fix doesn't need to be downported as the code in question is not exposed in production yet.  
  
Thanks a lot for reporting the issue!


---

**#13 — pe...@google.com — Feb 16, 2024 12:45AM**

This is sufficiently serious that it should be merged to extended stable. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M120. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately.  
This is sufficiently serious that it should be merged to other stable. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M121. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately.  
This is sufficiently serious that it should be merged to stable. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M122. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately.  
Merge review required: no relevant commits could be automatically detected (via Git Watcher comments), sending to merge review for manual evaluation. If you have not already manually listed the relevant commits to be merged via a comment above, please do so ASAP.  
  
  
Merge review required: no relevant commits could be automatically detected (via Git Watcher comments), sending to merge review for manual evaluation. If you have not already manually listed the relevant commits to be merged via a comment above, please do so ASAP.  
  
  
Merge review required: no relevant commits could be automatically detected (via Git Watcher comments), sending to merge review for manual evaluation. If you have not already manually listed the relevant commits to be merged via a comment above, please do so ASAP.  
  
  
Thank you for fixing this security bug! We aim to ship security fixes as quickly as possible, to limit their opportunity for exploitation as an "n-day" (that is, a bug where git fixes are developed into attacks before those fixes reach users).  
  
We have determined this fix is necessary on milestone(s): [120, 121, 122].  
  
Please answer the following questions so that we can safely process this merge request:  
1\. Which CLs should be backmerged? (Please include Gerrit links.)  
2\. Has this fix been verified on Canary to not pose any stability regressions?  
3\. Does this fix pose any potential non-verifiable stability risks?  
4\. Does this fix pose any known compatibility risks?  
5\. Does it require manual verification by the test team? If so, please describe required testing.


---

**#14 — ml...@chromium.org — Feb 16, 2024 12:53AM**

No merge required. I removed the Merge labels.


---

**#15 — je...@gmail.com — Feb 16, 2024 01:23AM**

[https://issues.chromium.org/u/1/issues/325310949](<https://issues.chromium.org/u/1/issues/325310949>)  
Thank you for your response. I can indeed construct an example of type confusion. Please have the Chrome VRP team review this report as supplementary material.


---

**#16 — pe...@google.com — Feb 16, 2024 11:47AM**

This high+ V8 security issue with stable impact requires a lightweight post mortem. Please take some time to answer questions asked in this form [1] to help us improve V8 security. [1] [https://docs.google.com/forms/d/e/1FAIpQLSdSMCiEpIFLLFkMbgtulK1sf1B-idQmkFaA4XP2Rz5mN1cqWg/viewform?usp=pp_url&entry.307501673=324747822&entry.364066060=jerrylulu7@gmail.com&entry.958145677=Android](<https://docs.google.com/forms/d/e/1FAIpQLSdSMCiEpIFLLFkMbgtulK1sf1B-idQmkFaA4XP2Rz5mN1cqWg/viewform?usp=pp_url&entry.307501673=324747822&entry.364066060=jerrylulu7@gmail.com&entry.958145677=Android>), Linux, Mac, Windows, Lacros, ChromeOS&entry.763880440=Extended&entry.1678852700=High&entry.763402679=Blink>JavaScript, Blink>JavaScript>Compiler>Turbofan&entry.975983575=[mliedtke@chromium.org](<mailto:mliedtke@chromium.org>) Please ensure to copy the full link, as otherwise some issue meta data might not be populated automatically.


---

**#17 — ml...@chromium.org — Feb 16, 2024 07:23PM**

@Amy: This bug is marked with the hotlist `Security_Impact-Extended`.  
It's a finched feature only (it was also marked as `FoundIn 120` which I removed.  
Can I change this label similar to how it was done previously to something like `Security_Impact-None`?


---

**#18 — am...@chromium.org — Feb 17, 2024 04:41AM**

mliedtke@ thank you for the detailed analysis in c#12 as well as the note in c#17. I've updated the hotlist from SI-Extended to SI-None based on this information, which should result in stopping the merge review tags from being added.


---

**#19 — ap...@google.com — Feb 19, 2024 08:18PM**

Project: v8/v8  
Branch: main  
  
commit 66be05befa301325fa11dd13b2242e0ccf794b71  
Author: Matthias Liedtke <[mliedtke@chromium.org](<mailto:mliedtke@chromium.org>)>  
Date: Mon Feb 19 11:48:28 2024  
  
[test] Add missing reproducer for imported string bug  
  
[https://crrev.com/c/5293801](<https://crrev.com/c/5293801>) missed the repro test case.  
This CL also removes an unused import.  
  
Bug: 324747822  
Change-Id: Ibcca8291a47a95a8c43513632628bac73e7c6a64  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5306935](<https://chromium-review.googlesource.com/c/v8/v8/+/5306935>)  
Reviewed-by: Jakob Kummerow <[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)>  
Commit-Queue: Matthias Liedtke <[mliedtke@chromium.org](<mailto:mliedtke@chromium.org>)>  
Commit-Queue: Jakob Kummerow <[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)>  
Auto-Submit: Matthias Liedtke <[mliedtke@chromium.org](<mailto:mliedtke@chromium.org>)>  
Cr-Commit-Position: refs/heads/main@{#92397}  
  
M src/wasm/well-known-imports.cc  
A test/mjsunit/regress/wasm/regress-324747822.js  
  
[https://chromium-review.googlesource.com/5306935](<https://chromium-review.googlesource.com/5306935>)


---

**#20 — ap...@google.com — Feb 19, 2024 08:18PM**

Project: v8/v8  
Branch: main  
  
commit 66be05befa301325fa11dd13b2242e0ccf794b71  
Author: Matthias Liedtke <[mliedtke@chromium.org](<mailto:mliedtke@chromium.org>)>  
Date: Mon Feb 19 11:48:28 2024  
  
[test] Add missing reproducer for imported string bug  
  
[https://crrev.com/c/5293801](<https://crrev.com/c/5293801>) missed the repro test case.  
This CL also removes an unused import.  
  
Bug: 324747822  
Change-Id: Ibcca8291a47a95a8c43513632628bac73e7c6a64  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5306935](<https://chromium-review.googlesource.com/c/v8/v8/+/5306935>)  
Reviewed-by: Jakob Kummerow <[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)>  
Commit-Queue: Matthias Liedtke <[mliedtke@chromium.org](<mailto:mliedtke@chromium.org>)>  
Commit-Queue: Jakob Kummerow <[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)>  
Auto-Submit: Matthias Liedtke <[mliedtke@chromium.org](<mailto:mliedtke@chromium.org>)>  
Cr-Commit-Position: refs/heads/main@{#92397}  
  
M src/wasm/well-known-imports.cc  
A test/mjsunit/regress/wasm/regress-324747822.js  
  
[https://chromium-review.googlesource.com/5306935](<https://chromium-review.googlesource.com/5306935>)


---

**#21 — je...@gmail.com — Feb 20, 2024 10:58AM**

Hi @mliedtke, Can you take a look [Issue 325756545](<https://issues.chromium.org/issues/325756545>), which should be a new type.is_uninhabited case :)  
Thanks


---

**#22 — am...@google.com — Feb 23, 2024 07:05AM**

*** Boilerplate reminders! ***  
Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.  
******************************


---

**#23 — am...@chromium.org — Feb 23, 2024 07:16AM**

Congratulations on another one, Jerry! The Chrome VRP Panel has decided to award you $7,000 for this report of renderer process memory corruption + $1,000 bisect bonus. Thank you for your efforts and reporting this issue to us!


---

**#24 — ap...@google.com — Mar 8, 2024 11:40PM**

Project: v8/v8  
Branch: refs/branch-heads/12.2  
  
commit 8f1c8131bd1766368e9d006d0bc6b6210dd96303  
Author: Jakob Kummerow <[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)>  
Date: Mon Mar 04 16:50:53 2024  
  
Merged: [wasm-imported-strings][turbofan] Use HeapType::kExternString  
  
and: [wasm] Introduce new heap type 'imported string'  
  
(cherry picked from commit cfe1cccfb86ca4c21e21cff47712894c2a83c61a)  
(cherry picked from commit 841c7c1117f8f40cf17fb24a33255f05477d315a)  
  
Fixed: [b/326091470](<https://issues.chromium.org/issues/326091470>), [b/324747822](<https://issues.chromium.org/issues/324747822>)  
Change-Id: Ia7ad389697b6a75d0af6d0130942b572e0243d73  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5339904](<https://chromium-review.googlesource.com/c/v8/v8/+/5339904>)  
Reviewed-by: Darius Mercadier <[dmercadier@chromium.org](<mailto:dmercadier@chromium.org>)>  
Commit-Queue: Jakob Kummerow <[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)>  
Cr-Commit-Position: refs/branch-heads/12.2@{#42}  
Cr-Branched-From: 6eb5a9616aa6f8c705217aeb7c7ab8c037a2f676-refs/heads/12.2.281@{#1}  
Cr-Branched-From: 44cf56d850167c6988522f8981730462abc04bcc-refs/heads/main@{#91934}  
  
M src/compiler/turboshaft/wasm-gc-type-reducer.h  
M src/compiler/turboshaft/wasm-lowering-reducer.h  
M src/compiler/wasm-compiler.cc  
M src/compiler/wasm-gc-lowering.cc  
M src/compiler/wasm-gc-operator-reducer.cc  
M src/wasm/graph-builder-interface.cc  
M src/wasm/turboshaft-graph-interface.cc  
M src/wasm/value-type.h  
M src/wasm/wasm-subtyping.cc  
M src/wasm/wasm-subtyping.h  
A test/mjsunit/regress/wasm/regress-326091470.js  
M test/unittests/wasm/subtyping-unittest.cc  
  
[https://chromium-review.googlesource.com/5339904](<https://chromium-review.googlesource.com/5339904>)


---

**#25 — pe...@google.com — Mar 9, 2024 12:15AM**

LTS Milestone M120  
  
This issue has been flagged as a merge candidate for Chrome OS' LTS channel. If selected, our merge team will handle any additional merges. To help us determine if this issue requires a merge to LTS, please answer this short questionnaire:  
1\. Was this issue a regression for the milestone it was found in?  
2\. Is this issue related to a change or feature merged after the latest LTS Milestone?


---

**#26 — am...@chromium.org — Mar 9, 2024 10:11AM**

There is an on-going blintz issue blocking fixed security issues from being automatically opened to security-notify (tracked and worked in [b/327524177](<https://issues.chromium.org/issues/327524177>)). There were issues with one of the fixes preventing this from being resolved as of yet.

As such, manually opening some impactful issues to ensure visibility.


---

**#27 — pe...@google.com — May 25, 2024 12:53AM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
