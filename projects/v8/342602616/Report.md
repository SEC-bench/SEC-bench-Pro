# Security: Debug check failed: !type.is_uninhabited()

Issue URL: https://issues.chromium.org/issues/342602616
VRP-Reward: 7000
Date: May 25, 2024 02:59AM


# Security Bug

Important: Please do not change the component of this bug manually.

Please READ THIS FAQ before filing a bug: [https://chromium.googlesource.com/chromium/src/+/HEAD/docs/security/faq.md](<https://chromium.googlesource.com/chromium/src/+/HEAD/docs/security/faq.md>)

Please see the following link for instructions on filing security bugs: [https://www.chromium.org/Home/chromium-security/reporting-security-bugs](<https://www.chromium.org/Home/chromium-security/reporting-security-bugs>)

Reports may be eligible for reward payments under the Chrome VRP: [https://g.co/chrome/vrp](<https://g.co/chrome/vrp>)

NOTE: Security bugs are normally made public once a fix has been widely deployed.

* * *

## VULNERABILITY DETAILS

Similar to issue <https://issues.chromium.org/issues/324747822>, I think the fix is not complete.

## VERSION

Chrome Version: V8 version 12.7.0 (candidate)

Operating System: Linux64

## REPRODUCTION CASE

  1. Download latest d8-component on `gs://v8-asan/linux-debug/d8-linux-debug-v8-component-94084.zip`
  2. run with `./d8 helper2.js --future --jit-fuzzing /path/original.wasm`

## FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION

```
#
# Fatal error in ../../src/compiler/turboshaft/wasm-gc-typed-optimization-reducer.cc, line 405
# Debug check failed: !type.is_uninhabited().
#
#
#
#FailureMessage Object: 0x7dace67f99f0
==== C stack trace ===============================

    /home/rheza/prebuild_chromium/v8/d8-linux-debug-v8-component-94084/libv8_libbase.so(v8::base::debug::StackTrace::StackTrace()+0x13) [0x7dad22afbe53]
    /home/rheza/prebuild_chromium/v8/d8-linux-debug-v8-component-94084/libv8_libplatform.so(+0x18e3d) [0x7dad1d5f3e3d]
    /home/rheza/prebuild_chromium/v8/d8-linux-debug-v8-component-94084/libv8_libbase.so(V8_Fatal(char const*, int, char const*, ...)+0x17d) [0x7dad22add04d]
    /home/rheza/prebuild_chromium/v8/d8-linux-debug-v8-component-94084/libv8_libbase.so(+0x2ba95) [0x7dad22adca95]
    /home/rheza/prebuild_chromium/v8/d8-linux-debug-v8-component-94084/libv8.so(v8::internal::compiler::turboshaft::WasmGCTypeAnalyzer::CreateMergeSnapshot(v8::base::Vector<v8::internal::compiler::turboshaft::SnapshotTable<v8::internal::wasm::ValueType, v8::internal::compiler::turboshaft::NoKeyData>::Snapshot const>, v8::base::Vector<bool const>)+0x5c8) [0x7dad21f153c8]
    /home/rheza/prebuild_chromium/v8/d8-linux-debug-v8-component-94084/libv8.so(v8::internal::compiler::turboshaft::WasmGCTypeAnalyzer::Run()+0x31c) [0x7dad21f1489c]
    /home/rheza/prebuild_chromium/v8/d8-linux-debug-v8-component-94084/libv8.so(void v8::internal::compiler::turboshaft::GraphVisitor<v8::internal::compiler::turboshaft::ReducerStack<v8::internal::compiler::turboshaft::Assembler<v8::internal::compiler::turboshaft::reducer_list<v8::internal::compiler::turboshaft::TurboshaftAssemblerOpInterface, v8::internal::compiler::turboshaft::GraphVisitor, v8::internal::compiler::turboshaft::WasmLoadEliminationReducer, v8::internal::compiler::turboshaft::WasmGCTypedOptimizationReducer, v8::internal::compiler::turboshaft::TSReducerBase>>, false, v8::internal::compiler::turboshaft::WasmLoadEliminationReducer, v8::internal::compiler::turboshaft::WasmGCTypedOptimizationReducer, v8::internal::compiler::turboshaft::TSReducerBase>>::VisitGraph<false>()+0x46) [0x7dad21ed7476]
    /home/rheza/prebuild_chromium/v8/d8-linux-debug-v8-component-94084/libv8.so(v8::internal::compiler::turboshaft::CopyingPhase<v8::internal::compiler::turboshaft::WasmLoadEliminationReducer, v8::internal::compiler::turboshaft::WasmGCTypedOptimizationReducer>::Run(v8::internal::compiler::turboshaft::PipelineData*, v8::internal::Zone*)+0x105) [0x7dad21ec50e5]
    /home/rheza/prebuild_chromium/v8/d8-linux-debug-v8-component-94084/libv8.so(v8::internal::compiler::turboshaft::WasmGCOptimizePhase::Run(v8::internal::compiler::turboshaft::PipelineData*, v8::internal::Zone*)+0x76) [0x7dad21ec4f56]
    /home/rheza/prebuild_chromium/v8/d8-linux-debug-v8-component-94084/libv8.so(auto v8::internal::compiler::turboshaft::Pipeline::Run<v8::internal::compiler::turboshaft::WasmGCOptimizePhase>()+0xda) [0x7dad21d6889a]
    /home/rheza/prebuild_chromium/v8/d8-linux-debug-v8-component-94084/libv8.so(v8::internal::compiler::Pipeline::GenerateWasmCodeFromTurboshaftGraph(v8::internal::OptimizedCompilationInfo*, v8::internal::wasm::CompilationEnv*, v8::internal::compiler::WasmCompilationData&, v8::internal::compiler::MachineGraph*, v8::internal::wasm::WasmFeatures*, v8::internal::compiler::CallDescriptor*)+0x677) [0x7dad21d671f7]
    /home/rheza/prebuild_chromium/v8/d8-linux-debug-v8-component-94084/libv8.so(v8::internal::compiler::turboshaft::ExecuteTurboshaftWasmCompilation(v8::internal::wasm::CompilationEnv*, v8::internal::compiler::WasmCompilationData&, v8::internal::wasm::WasmFeatures*)+0x2b1) [0x7dad21ff0631]
    /home/rheza/prebuild_chromium/v8/d8-linux-debug-v8-component-94084/libv8.so(v8::internal::wasm::WasmCompilationUnit::ExecuteFunctionCompilation(v8::internal::wasm::CompilationEnv*, v8::internal::wasm::WireBytesStorage const*, v8::internal::Counters*, v8::internal::wasm::WasmFeatures*)+0x67a) [0x7dad214e906a]
    /home/rheza/prebuild_chromium/v8/d8-linux-debug-v8-component-94084/libv8.so(v8::internal::wasm::WasmCompilationUnit::ExecuteCompilation(v8::internal::wasm::CompilationEnv*, v8::internal::wasm::WireBytesStorage const*, v8::internal::Counters*, v8::internal::wasm::WasmFeatures*)+0x140) [0x7dad214e85e0]
    /home/rheza/prebuild_chromium/v8/d8-linux-debug-v8-component-94084/libv8.so(+0x3f46f13) [0x7dad21546f13]
    /home/rheza/prebuild_chromium/v8/d8-linux-debug-v8-component-94084/libv8.so(+0x3f46795) [0x7dad21546795]
    /home/rheza/prebuild_chromium/v8/d8-linux-debug-v8-component-94084/libv8_libplatform.so(v8::platform::DefaultJobWorker::Run()+0xd3) [0x7dad1d5f2be3]
    /home/rheza/prebuild_chromium/v8/d8-linux-debug-v8-component-94084/libv8_libplatform.so(v8::platform::DefaultWorkerThreadsTaskRunner::WorkerThread::Run()+0xcc) [0x7dad1d5f501c]
    /home/rheza/prebuild_chromium/v8/d8-linux-debug-v8-component-94084/libv8_libbase.so(+0x49b98) [0x7dad22afab98]
    /lib/x86_64-linux-gnu/libc.so.6(+0x94ac3) [0x7dad1ce94ac3]
    /lib/x86_64-linux-gnu/libc.so.6(+0x126850) [0x7dad1cf26850]
Trace/breakpoint trap (core dumped)
```

* * *

## Bisect

Maybe similar from [https://crrev.com/3f2471d0abe711c92ddb3d6fe17bc22d9955f2b8](<https://crrev.com/3f2471d0abe711c92ddb3d6fe17bc22d9955f2b8>)


---

**#2 — rh...@gmail.com — May 25, 2024 03:15AM**

Please use new helper1.js for test on clusterfuzz.

run with `./d8 helper1.js --future --jit-fuzzing -- original.wasm`


---

**#3 — rh...@gmail.com — May 28, 2024 09:14PM**

Sorry for the ping, is it possible to get an update for this bug?

Can someone triage this bug please?


---

**#4 — cl...@appspot.gserviceaccount.com — May 29, 2024 07:17AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=4846563716169728](<https://clusterfuzz.com/testcase?key=4846563716169728>).


---

**#5 — 24...@project.gserviceaccount.com — May 29, 2024 07:35AM**

Testcase 4846563716169728 failed to reproduce the crash. Please inspect the program output at [https://clusterfuzz.com/testcase?key=4846563716169728](<https://clusterfuzz.com/testcase?key=4846563716169728>).


---

**#6 — cl...@appspot.gserviceaccount.com — May 29, 2024 09:58AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=6035474417123328](<https://clusterfuzz.com/testcase?key=6035474417123328>).


---

**#7 — cl...@appspot.gserviceaccount.com — May 29, 2024 10:00AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5368171329421312](<https://clusterfuzz.com/testcase?key=5368171329421312>).


---

**#8 — am...@chromium.org — May 29, 2024 10:02AM**

Thank you for the report. There was a holiday weekend in the US, and bugs are not triaged over weekend and holidays so we are looking into this now. I'm unable to reproduce this manually, so I'm retrying clusterfuzz with the helper1.js POC. Are there other flags that are needed here than what has been presented in the repro steps?


---

**#9 — am...@chromium.org — May 29, 2024 10:12AM**

I was unsuccessful in reproducing this issue with a dbg build or with clusterfuzz. Handing off to saelo@, V8 shepherd in the interim, but more information here from OP would be preferred, so needs-feedback has been set.


---

**#10 — 24...@project.gserviceaccount.com — May 29, 2024 10:15AM**

Testcase 6035474417123328 failed to reproduce the crash. Please inspect the program output at [https://clusterfuzz.com/testcase?key=6035474417123328](<https://clusterfuzz.com/testcase?key=6035474417123328>).


---

**#11 — rh...@gmail.com — May 29, 2024 12:31PM**

Hello,

Thank you for triaging and sorry if this hard to repro.

I tested with latest `win64-debug_d8-asan-win64-debug-v8-component-94142.zip` on windows, and unfortunately I'm still able to repro.

> > Are there other flags that are needed here than what has been presented in the repro steps

On my test, the `--future --jit-fuzzing` is being used.

I was checking the clusterfuzz report:

[https://clusterfuzz.com/testcase-detail/5368171329421312](<https://clusterfuzz.com/testcase-detail/5368171329421312>)

[https://clusterfuzz.com/testcase-detail/6035474417123328](<https://clusterfuzz.com/testcase-detail/6035474417123328>)

`[Command line] /mnt/scratch0/clusterfuzz/bot/builds/v8-asan_linux-release_dd2f90e18dce5d8550461e387b6dcf5a476ceb72/revisions/d8 --fuzzing --fuzzing --expose-gc --allow-natives-syntax --debug-code --harmony --disable-abortjs --omit-quit --disable-in-process-stack-traces --invoke-weak-callbacks --enable-slow-asserts --verify-heap --future --jit-fuzzing /mnt/scratch0/clusterfuzz/bot/inputs/fuzzer-testcases/poc_342602616.js`

```
+----------------------------------------Debug Build Stacktrace----------------------------------------+
/mnt/scratch0/clusterfuzz/bot/inputs/fuzzer-testcases/poc_342602616.js:20: Error: Error reading file
    binary = new Uint8Array(readbuffer(wasmFilePath));
                            ^
Error: Error reading file
    at /mnt/scratch0/clusterfuzz/bot/inputs/fuzzer-testcases/poc_342602616.js:20:29
```

this mean the file wasn't uploaded to d8 and we are almost to get there. Would it possible if you run with `./d8 helper1.js --arguments -- original.wasm` on the CF?

the args.gn for `\win64-debug_d8-asan-win64-debug-v8-component-94142`

```
PS X:\prebuild_chromium\v8\win64-debug_d8-asan-win64-debug-v8-component-94142> cat .\args.gn
dcheck_always_on = true
is_asan = true
is_clang = true
is_component_build = false
is_debug = false
target_cpu = "x64"
use_remoteexec = true
v8_enable_google_benchmark = true
v8_enable_slow_dchecks = true
v8_enable_test_features = true
v8_enable_verify_heap = true
```


---

**#12 — pe...@google.com — May 29, 2024 12:42PM**

Thank you for providing more feedback. Adding the requester to the CC list.


---

**#13 — cl...@appspot.gserviceaccount.com — May 30, 2024 11:23PM**

Detailed Report: [https://clusterfuzz.com/testcase?key=5406631578763264](<https://clusterfuzz.com/testcase?key=5406631578763264>)  
  
Fuzzer: None  
Job Type: linux_asan_d8_dbg  
Platform Id: linux  
  
Crash Type: DCHECK failure  
Crash Address:   
Crash State:  
!type.is_uninhabited() in wasm-gc-typed-optimization-reducer.cc  
v8::internal::compiler::turboshaft::WasmGCTypeAnalyzer::CreateMergeSnapshot  
v8::internal::compiler::turboshaft::WasmGCTypeAnalyzer::Run  
  
Sanitizer: address (ASAN)  
  
Crash Revision: [https://clusterfuzz.com/revisions?job=linux_asan_d8_dbg&revision=94166](<https://clusterfuzz.com/revisions?job=linux_asan_d8_dbg&revision=94166>)  
  
Reproducer Testcase: [https://clusterfuzz.com/download?testcase_id=5406631578763264](<https://clusterfuzz.com/download?testcase_id=5406631578763264>)  
  
To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.   
  
If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.  
  
If you have any feedback on reproducing test cases, let us know at [https://forms.gle/Yh3qCYFveHj6E5jz5](<https://forms.gle/Yh3qCYFveHj6E5jz5>) so we can improve.


---

**#14 — sa...@google.com — May 30, 2024 11:24PM**

I guess the problem is that Clusterfuzz only supports uploading a single file, so I now inlined the Wasm module bytes into the JavaScript code as Uint8Array literal, and now it reproes.


---

**#15 — rh...@gmail.com — May 31, 2024 03:50AM**

re#14:

Thanks for helping


---

**#16 — mp...@google.com — May 31, 2024 10:58AM**

Setting a provisional severity of S1, and rerunning some clusterfuzz tasks so hopefully it can set FoundIn for us.


---

**#17 — 24...@project.gserviceaccount.com — May 31, 2024 11:23AM**

Automatically applying components based on crash stacktrace and information from OWNERS files.  
  
If this is incorrect, please apply the hotlistid:4801165.


---

**#18 — sa...@google.com — May 31, 2024 05:23PM**

The crash bisects to [https://chromium.googlesource.com/v8/v8/+/6d26d2b5f88fbb3e3ea7020c2ec16e47ed1aceb6%5E%21/](<https://chromium.googlesource.com/v8/v8/+/6d26d2b5f88fbb3e3ea7020c2ec16e47ed1aceb6%5E%21/>) "[wasm][fuzzing] Add jit_fuzzing implication for wasm" which isn't super useful, apart from pointing at turbofan/turboshaft for the root cause, which we already know from the DCHECK failure :) I briefly tried bisecting past that, but without success, probably because the new `v8_flags.wasm_inlining_ignore_call_counts` is important. Matthias, could you take a look?


---

**#19 — ml...@chromium.org — May 31, 2024 05:59PM**

I can reproduce the issue.

It crashes in function #322 which has two nested loops which we have also seen in previous crashes in this `DCHECK`.

This could either be a harmless optimization bug in missing that a predecessor is actually unreachable or a real type confusion.


---

**#20 — ml...@chromium.org — May 31, 2024 10:04PM**

Attached is my reduced reproducer case. This took probably the longest to just get it down to a small-ish test case as the optimizations in the type reducer aren't very easy to debug, so it isn't easy to do it on such large wasm modules.

Here is what is happening: We have a `struct.get` that loads an `i16` from a struct. `i16` is a "packed" type in WebAssembly, when loading a value of such type, the result type is `i32`.

The type reducer missed this "integer promotion"-like behavior and mis-typed it. The reproducer has a phi that takes this loaded value on one side and an `i32` on the other side. The result type of that phi is `union(i32, i16)`. This union returns an uninhabited type.

For the numeric value itself, this bug isn't a big issue as we don't do any optimization based on integral types. However, when seeing an uninhabited type, the optimization says "Great, there is an impossible type, this means the control flow from here is now considered unreachable, we cannot have impossible types in reachable code", thus marking this control flow as unreachable: [https://source.chromium.org/chromium/chromium/src/+/main:v8/src/compiler/turboshaft/wasm-gc-typed-optimization-reducer.cc;l=429](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/compiler/turboshaft/wasm-gc-typed-optimization-reducer.cc;l=429>)

The following pseudo-code might help explain my understanding of how this could possibly be exploited:

```
$0 = struct.new<Struct1>()
$cond = ...
if $cond:
  $cond2 = ...
  if $cond2:
    $1 = 4
  else
    $2 = struct.get<Struct1>(0) // assume this returns i16
  endif
  $3 = phi($1, $2) // this wrongly resolves to kWasmBottom / an uninhabited type, marking the block as unreachable from now on.
  $1 = struct.new<Struct2>()
endif
$4 = phi($0, $1) // This should be union(Struct1, Struct2), the bug causes this to be typed Struct1 as the other branch is treated as unreachable leading to type confusions for $4 from now on.
```

Note that I didn't spend any time verifying that this type confusion is indeed possible.


---

**#21 — ap...@google.com — May 31, 2024 10:19PM**

Project: v8/v8  
Branch: main  
  
commit 3b037e1756d366e0a6aa8467da9af0d44af84ffb  
Author: Matthias Liedtke <[mliedtke@chromium.org](<mailto:mliedtke@chromium.org>)>  
Date: Fri May 31 14:37:06 2024  
  
[turboshaft][wasm-gc] Unpack i8 and i16 to i32 in type optimizations  
  
Fixed: 342602616  
Change-Id: Ib82e19241c5b3562db3f86a31b6e3be56e77cadd  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5587860](<https://chromium-review.googlesource.com/c/v8/v8/+/5587860>)  
Reviewed-by: Eva Herencsárová <[evih@chromium.org](<mailto:evih@chromium.org>)>  
Auto-Submit: Matthias Liedtke <[mliedtke@chromium.org](<mailto:mliedtke@chromium.org>)>  
Commit-Queue: Eva Herencsárová <[evih@chromium.org](<mailto:evih@chromium.org>)>  
Cr-Commit-Position: refs/heads/main@{#94179}  
  
M src/compiler/turboshaft/wasm-gc-typed-optimization-reducer.cc  
  
[https://chromium-review.googlesource.com/5587860](<https://chromium-review.googlesource.com/5587860>)


---

**#22 — pe...@google.com — May 31, 2024 10:27PM**

Dear owner, thanks for fixing this bug. We've reopened it because security bugs need the Severity (S0-S3) and the Found In set, which will enable the bots to request merges to the correct branches ( as well as helping out our vulnerability reward and CVE processes). Please consult with any Chrome security contact ([security@chromium.org](<mailto:security@chromium.org>)) to arrange to set these labels and then this bug can be marked closed again. Thank you! Severity guidelines: [https://chromium.googlesource.com/chromium/src/+/refs/heads/main/docs/security/severity-guidelines.md#severity-guidelines-for-security-issues](<https://chromium.googlesource.com/chromium/src/+/refs/heads/main/docs/security/severity-guidelines.md#severity-guidelines-for-security-issues>) FoundIn guidelines: [https://chromium.googlesource.com/chromium/src/+/main/docs/security/security-labels.md#labels-relevant-for-any-type_bug_security](<https://chromium.googlesource.com/chromium/src/+/main/docs/security/security-labels.md#labels-relevant-for-any-type_bug_security>) Thanks for your time!


---

**#23 — ml...@chromium.org — May 31, 2024 10:36PM**

Setting the `Found in` to 125. The bug is much older than that but the Turboshaft wasm experiment is only used starting on version 125.


---

**#24 — ml...@chromium.org — May 31, 2024 11:09PM**

As I'm out of office next Monday and Tuesday, Jakob, could you be so kind and request the backmerge once it has reached Canary?


---

**#25 — pe...@google.com — Jun 1, 2024 12:38AM**

Setting milestone because of s0/s1 severity.


---

**#26 — pe...@google.com — Jun 1, 2024 12:44AM**

This is sufficiently serious that it should be merged to stable. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M125. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately.  
This is sufficiently serious that it should be merged to beta. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M126. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately.  
Thank you for fixing this security bug! We aim to ship security fixes as quickly as possible, to limit their opportunity for exploitation as an "n-day" (that is, a bug where git fixes are developed into attacks before those fixes reach users).  
  
We have determined this fix is necessary on milestone(s): [].  
  
Please answer the following questions so that we can safely process this merge request:  
1\. Which CLs should be backmerged? (Please include Gerrit links.)  
2\. Has this fix been verified on Canary to not pose any stability regressions?  
3\. Does this fix pose any potential non-verifiable stability risks?  
4\. Does this fix pose any known compatibility risks?  
5\. Does it require manual verification by the test team? If so, please describe required testing.


---

**#27 — pe...@google.com — Jun 1, 2024 10:27PM**

Merge review required: M126 is already shipping to beta.  
  
Please answer the following questions so that we can safely process your merge request:  
1\. Why does your merge fit within the merge criteria for these milestones?  
\- Chrome Browser: [https://chromiumdash.appspot.com/branches](<https://chromiumdash.appspot.com/branches>)  
\- Chrome OS: [https://goto.google.com/cros-release-branch-merge-guidelines](<https://goto.google.com/cros-release-branch-merge-guidelines>)  
2\. What changes specifically would you like to merge? Please link to Gerrit.  
3\. Have the changes been released and tested on canary?  
4\. Is this a new feature? If yes, is it behind a Finch flag and are experiments active in any release channels?  
5\. [Chrome OS only]: Was the change reviewed and approved by the Eng Prod Representative? [https://goto.google.com/cros-engprodcomponents](<https://goto.google.com/cros-engprodcomponents>)  
6\. If this merge addresses a major issue in the stable channel, does it require manual verification by the test team? If so, please describe required testing.  
  
Please contact the milestone owner if you have questions.  
Owners: govind (Android), govind (iOS), ceb (ChromeOS), srinivassista (Desktop)


---

**#28 — pe...@google.com — Jun 1, 2024 10:27PM**

Merge review required: M125 is already shipping to stable.  
  
Please answer the following questions so that we can safely process your merge request:  
1\. Why does your merge fit within the merge criteria for these milestones?  
\- Chrome Browser: [https://chromiumdash.appspot.com/branches](<https://chromiumdash.appspot.com/branches>)  
\- Chrome OS: [https://goto.google.com/cros-release-branch-merge-guidelines](<https://goto.google.com/cros-release-branch-merge-guidelines>)  
2\. What changes specifically would you like to merge? Please link to Gerrit.  
3\. Have the changes been released and tested on canary?  
4\. Is this a new feature? If yes, is it behind a Finch flag and are experiments active in any release channels?  
5\. [Chrome OS only]: Was the change reviewed and approved by the Eng Prod Representative? [https://goto.google.com/cros-engprodcomponents](<https://goto.google.com/cros-engprodcomponents>)  
6\. If this merge addresses a major issue in the stable channel, does it require manual verification by the test team? If so, please describe required testing.  
  
Please contact the milestone owner if you have questions.  
Owners: govind (Android), govind (iOS), matthewjoseph (ChromeOS), pbommana (Desktop)


---

**#29 — rh...@gmail.com — Jun 3, 2024 09:35AM**

matthias@,

Thank you for the detailed explanation and the quick fixes for issues #20 and #21. I appreciate it a lot.


---

**#30 — ml...@chromium.org — Jun 5, 2024 05:44PM**

Answers for [comment #27](<https://issues.chromium.org/issues/342602616#comment27>), [comment #28](<https://issues.chromium.org/issues/342602616#comment28>):

  1. The bug may be exploitable.
  2. [https://chromium-review.googlesource.com/c/v8/v8/+/5587860](<https://chromium-review.googlesource.com/c/v8/v8/+/5587860>)
  3. Yes, included in [127.0.6515.0](<https://chromiumdash.appspot.com/commit/3b037e1756d366e0a6aa8467da9af0d44af84ffb>).
  4. It's part of wasm-gc which was shipped September 2023. Still, usage for this feature is slowly increasing (not all browsers support it fully yet), so the risk of merging the fix is low.
  5. `-`
  6. No.


---

**#31 — pg...@google.com — Jun 6, 2024 12:30AM**

Merge approved for M126! Please merge the fix to branch 12.6 by Thursday June 13th EOD MTV time to get this fix into the next stable respin

There are no more scheduled releases for M125 - removing label


---

**#32 — sp...@google.com — Jun 6, 2024 04:56AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $7000.00 for this report.  
  
Rationale for this decision:  
report of renderer process memory corruption   
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#33 — am...@chromium.org — Jun 6, 2024 04:59AM**

Congratulations! Thank you for your efforts and reporting this issue to us!


---

**#34 — ap...@google.com — Jun 6, 2024 06:19PM**

Project: v8/v8  
Branch: refs/branch-heads/12.6  
  
commit 24dd499f7cba1f8c930bbb25078af8da64920b16  
Author: Matthias Liedtke <[mliedtke@chromium.org](<mailto:mliedtke@chromium.org>)>  
Date: Fri May 31 14:37:06 2024  
  
Merged: [turboshaft][wasm-gc] Unpack i8 and i16 to i32 in type optimizations  
  
Fixed: 342602616  
(cherry picked from commit 3b037e1756d366e0a6aa8467da9af0d44af84ffb)  
  
Change-Id: I25d2c40c4b9f6a111b730ba88bca3af7a7cbb122  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5602673](<https://chromium-review.googlesource.com/c/v8/v8/+/5602673>)  
Auto-Submit: Matthias Liedtke <[mliedtke@chromium.org](<mailto:mliedtke@chromium.org>)>  
Reviewed-by: Eva Herencsárová <[evih@chromium.org](<mailto:evih@chromium.org>)>  
Commit-Queue: Eva Herencsárová <[evih@chromium.org](<mailto:evih@chromium.org>)>  
Cr-Commit-Position: refs/branch-heads/12.6@{#20}  
Cr-Branched-From: 3c9fa12db3183a6f4ea53d2675adb66ea1194529-refs/heads/12.6.228@{#2}  
Cr-Branched-From: 981bb15ba4dbf9e2381dfc94ec2c4af0b9c6a0b6-refs/heads/main@{#93835}  
  
M src/compiler/turboshaft/wasm-gc-typed-optimization-reducer.cc  
  
[https://chromium-review.googlesource.com/5602673](<https://chromium-review.googlesource.com/5602673>)


---

**#35 — pe...@google.com — Jun 10, 2024 11:46AM**

This issue has been approved for a merge. Please merge the fix to any appropriate branches as soon as possible!  
  
If all merges have been completed, please remove any remaining Merge-Approved labels from this issue.  
  
Thanks for your time! To disable nags, add Disable-Nags (case sensitive) to the Chromium Labels custom field.


---

**#36 — pe...@google.com — Sep 8, 2024 12:41AM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.


---

**#37 — ap...@google.com — Oct 15, 2024 12:18AM**

Project: v8/v8  
Branch: main  
Author: Matthias Liedtke <[mliedtke@chromium.org](<mailto:mliedtke@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/5928649](<https://chromium-review.googlesource.com/5928649>)

[test][wasm] Add testcase for mistyping on packed element types i8/i16

* * *

Expand for full commit details

```
[test][wasm] Add testcase for mistyping on packed element types i8/i16

Bug: 342602616
Change-Id: Iee351da8029ac892c19ef3dcbfcc242ccab95cf6
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/5928649
Auto-Submit: Matthias Liedtke <mliedtke@chromium.org>
Commit-Queue: Matthias Liedtke <mliedtke@chromium.org>
Reviewed-by: Jakob Kummerow <jkummerow@chromium.org>
Cr-Commit-Position: refs/heads/main@{#96578}
```

* * *

Files:

  * A `test/mjsunit/regress/wasm/regress-342602616.js`

* * *

Hash: 94fbb073890d8706c69a16cacbcf8c93ab3614f3  
Date: Mon Oct 14 16:42:51 2024

* * *
