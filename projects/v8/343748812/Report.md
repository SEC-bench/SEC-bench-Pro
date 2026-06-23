# Security: Debug check failed: offset == var.offset() (128 vs. 112).

Issue URL: https://issues.chromium.org/issues/343748812
VRP-Reward: 7000
Date: May 31, 2024 10:47AM


# Security Bug

Important: Please do not change the component of this bug manually.

Please READ THIS FAQ before filing a bug: [https://chromium.googlesource.com/chromium/src/+/HEAD/docs/security/faq.md](<https://chromium.googlesource.com/chromium/src/+/HEAD/docs/security/faq.md>)

Please see the following link for instructions on filing security bugs: [https://www.chromium.org/Home/chromium-security/reporting-security-bugs](<https://www.chromium.org/Home/chromium-security/reporting-security-bugs>)

Reports may be eligible for reward payments under the Chrome VRP: [https://g.co/chrome/vrp](<https://g.co/chrome/vrp>)

NOTE: Security bugs are normally made public once a fix has been widely deployed.

* * *

# VULNERABILITY DETAILS

DCHECK falling is because the calculated offset upper that the expected.

```
Expected offset: 80, Calculated offset: 80
Expected offset: 88, Calculated offset: 88
Expected offset: 112, Calculated offset: 112
Expected offset: 112, Calculated offset: 128

#ifdef ENABLE_SLOW_DCHECKS
bool LiftoffAssembler::ValidateCacheState() const {
  uint32_t register_use_count[kAfterMaxLiftoffRegCode] = {0};
  LiftoffRegList used_regs;
  int offset = StaticStackFrameSize();
  for (const VarState& var : cache_state_.stack_state) {
    // Check for continuous stack offsets.
    offset = NextSpillOffset(var.kind(), offset);
    // Add logging here
    std::cout << "Expected offset: " << var.offset() << ", Calculated offset: " << offset << std::endl;
    DCHECK_EQ(offset, var.offset());           // [1] 
    if (!var.is_reg()) continue;
    LiftoffRegister reg = var.reg();
    if ((kNeedI64RegPair || kNeedS128RegPair) && reg.is_pair()) {
[...]
```

the discrepancy occurs during the last `NextSpillOffset` calculation, where the Calculated offset becomes `128`, but the Expected offset remains `112`. This suggests that there might be an issue with the `NextSpillOffset` function

```
After NextSpillOffset: offset = 128, Expected offset: 112
Expected offset: 112, Calculated offset: 128
```

I also can't find what kind of `var.kind()` after running the poc. I think is not properly printed.

[1] [https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/baseline/liftoff-assembler.cc;drc=b2df50672c06c070ecb137570d1072a3835ac4ca;l=1096](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/baseline/liftoff-assembler.cc;drc=b2df50672c06c070ecb137570d1072a3835ac4ca;l=1096>)

* * *

VERSION Chrome Version: [x.x.x.x] + [stable, beta, or dev] Operating System: [Please indicate OS, version, and service pack level]

REPRODUCTION CASE

  1. Please use linux_asan_d8_v8_arm64_dbg or

```
is_asan = true
is_clang = true
is_component_build = true
is_debug = true
is_lsan = true
target_cpu = "x64"
v8_enable_backtrace = true
v8_enable_google_benchmark = true
v8_enable_slow_dchecks = true
v8_enable_test_features = true
v8_target_cpu = "arm64"
```

  2. run `./d8 --wasm-staging poc.js`

* * *

FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION

Type of crash: **v8**

```
#
# Fatal error in ../../src/wasm/baseline/liftoff-assembler.cc, line 1096
# Debug check failed: offset == var.offset() (128 vs. 112).
#
#
#
#FailureMessage Object: 0x7c724963e460
==== C stack trace ===============================

    /home/rheza/v8/v8/out/linux_asan_d8_v8_arm64_dbg/d8(___interceptor_backtrace+0x46) [0x59516e693b66]
    /home/rheza/v8/v8/out/linux_asan_d8_v8_arm64_dbg/libv8_libbase.so(v8::base::debug::StackTrace::StackTrace()+0x13) [0x7c724cde4c83]
    /home/rheza/v8/v8/out/linux_asan_d8_v8_arm64_dbg/libv8_libplatform.so(+0x3177a) [0x7c724cd3f77a]
    /home/rheza/v8/v8/out/linux_asan_d8_v8_arm64_dbg/libv8_libbase.so(V8_Fatal(char const*, int, char const*, ...)+0x288) [0x7c724cdaf3b8]
    /home/rheza/v8/v8/out/linux_asan_d8_v8_arm64_dbg/libv8_libbase.so(+0x514df) [0x7c724cdae4df]
    /home/rheza/v8/v8/out/linux_asan_d8_v8_arm64_dbg/libv8.so(v8::internal::wasm::LiftoffAssembler::ValidateCacheState() const+0x371) [0x7c7253f02011]
    /home/rheza/v8/v8/out/linux_asan_d8_v8_arm64_dbg/libv8.so(+0x7125a45) [0x7c7253f25a45]
    /home/rheza/v8/v8/out/linux_asan_d8_v8_arm64_dbg/libv8.so(+0x7112efe) [0x7c7253f12efe]
    /home/rheza/v8/v8/out/linux_asan_d8_v8_arm64_dbg/libv8.so(v8::internal::wasm::ExecuteLiftoffCompilation(v8::internal::wasm::CompilationEnv*, v8::internal::wasm::FunctionBody const&, v8::internal::wasm::LiftoffOptions const&)+0x954) [0x7c7253f0d7d4]
    /home/rheza/v8/v8/out/linux_asan_d8_v8_arm64_dbg/libv8.so(v8::internal::wasm::WasmCompilationUnit::ExecuteFunctionCompilation(v8::internal::wasm::CompilationEnv*, v8::internal::wasm::WireBytesStorage const*, v8::internal::Counters*, v8::internal::wasm::WasmFeatures*)+0xb00) [0x7c7254110ec0]
    /home/rheza/v8/v8/out/linux_asan_d8_v8_arm64_dbg/libv8.so(v8::internal::wasm::WasmCompilationUnit::ExecuteCompilation(v8::internal::wasm::CompilationEnv*, v8::internal::wasm::WireBytesStorage const*, v8::internal::Counters*, v8::internal::wasm::WasmFeatures*)+0x33f) [0x7c725410f6ff]
    /home/rheza/v8/v8/out/linux_asan_d8_v8_arm64_dbg/libv8.so(v8::internal::wasm::CompileLazy(v8::internal::Isolate*, v8::internal::Tagged<v8::internal::WasmTrustedInstanceData>, int)+0x858) [0x7c72541a8558]
    /home/rheza/v8/v8/out/linux_asan_d8_v8_arm64_dbg/libv8.so(+0x709faed) [0x7c7253e9faed]
    /home/rheza/v8/v8/out/linux_asan_d8_v8_arm64_dbg/libv8.so(v8::internal::Runtime_WasmCompileLazy(int, unsigned long*, v8::internal::Isolate*)+0x1da) [0x7c7253e9ecaa]
    /home/rheza/v8/v8/out/linux_asan_d8_v8_arm64_dbg/libv8.so(v8::internal::Simulator::DoRuntimeCall(v8::internal::Instruction*)+0x847) [0x7c72548b25f7]
    /home/rheza/v8/v8/out/linux_asan_d8_v8_arm64_dbg/libv8.so(v8::internal::Simulator::ExecuteInstruction()+0x213) [0x7c72548b0b53]
    /home/rheza/v8/v8/out/linux_asan_d8_v8_arm64_dbg/libv8.so(v8::internal::Simulator::Run()+0x288) [0x7c72548b0688]
    /home/rheza/v8/v8/out/linux_asan_d8_v8_arm64_dbg/libv8.so(v8::internal::Simulator::CheckPCSComplianceAndRun()+0x3de) [0x7c72548add0e]
    /home/rheza/v8/v8/out/linux_asan_d8_v8_arm64_dbg/libv8.so(v8::internal::Simulator::CallImpl(unsigned long, v8::internal::Simulator::CallArgument*)+0x607) [0x7c72548ad0b7]
    /home/rheza/v8/v8/out/linux_asan_d8_v8_arm64_dbg/libv8.so(+0x4649e3d) [0x7c7251449e3d]
    /home/rheza/v8/v8/out/linux_asan_d8_v8_arm64_dbg/libv8.so(v8::internal::Execution::CallScript(v8::internal::Isolate*, v8::internal::Handle<v8::internal::JSFunction>, v8::internal::Handle<v8::internal::Object>, v8::internal::Handle<v8::internal::Object>)+0x5fd) [0x7c725144da8d]
    /home/rheza/v8/v8/out/linux_asan_d8_v8_arm64_dbg/libv8.so(v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>)+0xb52) [0x7c7250997c02]
    /home/rheza/v8/v8/out/linux_asan_d8_v8_arm64_dbg/d8(v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*)+0xf9e) [0x59516e75e1ce]
    /home/rheza/v8/v8/out/linux_asan_d8_v8_arm64_dbg/d8(v8::SourceGroup::Execute(v8::Isolate*)+0x474) [0x59516e78bee4]
    /home/rheza/v8/v8/out/linux_asan_d8_v8_arm64_dbg/d8(v8::Shell::RunMainIsolate(v8::Isolate*, bool)+0x2fc) [0x59516e796afc]
    /home/rheza/v8/v8/out/linux_asan_d8_v8_arm64_dbg/d8(v8::Shell::RunMain(v8::Isolate*, bool)+0x2a5) [0x59516e795f55]
    /home/rheza/v8/v8/out/linux_asan_d8_v8_arm64_dbg/d8(v8::Shell::Main(int, char**)+0x176a) [0x59516e799d6a]
    /lib/x86_64-linux-gnu/libc.so.6(+0x29d90) [0x7c724b029d90]
    /lib/x86_64-linux-gnu/libc.so.6(__libc_start_main+0x80) [0x7c724b029e40]
    /home/rheza/v8/v8/out/linux_asan_d8_v8_arm64_dbg/d8(_start+0x2a) [0x59516e64f2ca]
AddressSanitizer:DEADLYSIGNAL
=================================================================
==1105290==ERROR: AddressSanitizer: TRAP on unknown address 0x000000000000 (pc 0x7c724cddfe2f bp 0x7ffc88e59af0 sp 0x7ffc88e59af0 T0)
SCARINESS: 10 (signal)
```

* * *

bisect: [https://chromium-review.googlesource.com/c/v8/v8/+/4224507](<https://chromium-review.googlesource.com/c/v8/v8/+/4224507>)


---

**#2 — rh...@gmail.com — Jun 1, 2024 04:29AM**

Hi,

I attached poc_minimize.js for easy debugging.

`./d8 --wasm-staging poc_minimize.js`


---

**#3 — cl...@appspot.gserviceaccount.com — Jun 1, 2024 04:56AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5403644881993728](<https://clusterfuzz.com/testcase?key=5403644881993728>).


---

**#4 — rh...@gmail.com — Jun 1, 2024 05:01AM**

Sorry, please use `arm64` or on CF pick `linux_asan_d8_v8_arm64_dbg`


---

**#5 — 24...@project.gserviceaccount.com — Jun 1, 2024 05:12AM**

Testcase 5403644881993728 failed to reproduce the crash. Please inspect the program output at [https://clusterfuzz.com/testcase?key=5403644881993728](<https://clusterfuzz.com/testcase?key=5403644881993728>).


---

**#6 — za...@google.com — Jun 1, 2024 05:21AM**

This seem to be a v8 bug. I have set the found-in to the current extended stable milestone, 124. Passing this bug to the v8 team to further triage. Thanks.


---

**#7 — pe...@google.com — Jun 2, 2024 12:36AM**

Setting milestone because of s0/s1 severity.


---

**#8 — pe...@google.com — Jun 2, 2024 12:37AM**

Setting Priority to P1 to match Severity s1. If this is incorrect, please reset the priority. The automation bot account won't make this change again.


---

**#9 — cl...@appspot.gserviceaccount.com — Jun 4, 2024 04:23PM**

Detailed Report: [https://clusterfuzz.com/testcase?key=6225066671931392](<https://clusterfuzz.com/testcase?key=6225066671931392>)  
  
Fuzzer: None  
Job Type: linux_asan_d8_v8_arm64_dbg  
Platform Id: linux  
  
Crash Type: DCHECK failure  
Crash Address:   
Crash State:  
offset == var.offset() in liftoff-assembler.cc  
v8::internal::wasm::LiftoffAssembler::ValidateCacheState  
v8::internal::wasm::LiftoffCompiler::NextInstruction  
  
Sanitizer: address (ASAN)  
  
Crash Revision: [https://clusterfuzz.com/revisions?job=linux_asan_d8_v8_arm64_dbg&revision=94219](<https://clusterfuzz.com/revisions?job=linux_asan_d8_v8_arm64_dbg&revision=94219>)  
  
Reproducer Testcase: [https://clusterfuzz.com/download?testcase_id=6225066671931392](<https://clusterfuzz.com/download?testcase_id=6225066671931392>)  
  
To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.   
  
If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.  
  
If you have any feedback on reproducing test cases, let us know at [https://forms.gle/Yh3qCYFveHj6E5jz5](<https://forms.gle/Yh3qCYFveHj6E5jz5>) so we can improve.


---

**#10 — sa...@google.com — Jun 4, 2024 05:26PM**

Managed to reproduce this on Clusterfuzz. It seems to bisect to [https://chromium.googlesource.com/v8/v8/+/50f8643de79d1c0db4efb41c24ed7c283a97bb7b](<https://chromium.googlesource.com/v8/v8/+/50f8643de79d1c0db4efb41c24ed7c283a97bb7b>) "[wasm-gc] Ship it!". Matthias, could you take a look? Thanks!


---

**#11 — jk...@chromium.org — Jun 4, 2024 09:54PM**

Since Matthias is out today, I'll take a look.


---

**#12 — jk...@chromium.org — Jun 5, 2024 12:06AM**

This was introduced in [https://chromium-review.googlesource.com/c/v8/v8/+/4272230](<https://chromium-review.googlesource.com/c/v8/v8/+/4272230>): no, we cannot exit the loop early, we have to shift all remaining elements in the array, i.e. still have to execute `*slot = *(slot + 1);` for all remaining slots.

The bug is in `LiftoffAssembler::DropExceptionValueAtOffset`. For example, when dropping the exception here:

```
slot 0: stack, $var0, offset 32
slot 1: stack, $var1, offset 40
slot 2: stack, $var2, offset 48
slot 3: register, exception, offset 56   <<<<<<<<<< to be dropped
slot 4: register, some reference value, offset 64
slot 5: register, some s128 value, offset 80
slot 6: register, some reference value, offset 88
```

we currently get into this state:

```
slot 0: (unchanged)
slot 1: (unchanged)
slot 2: (unchanged)
slot 3: register, some reference value, offset 56  (copied from slot 4, with adjusted offset)
slot 4: register, some s128 value, offset 80  (copied from slot 5; alignment of s128 values causes the offset to remain 80, triggering early exit)
slot 5: register, some s128 value, offset 80  (erroneously not overwritten with slot 6's contents due to early loop exit)
slot 6: register, some reference value, offset 88  (will be dropped, and is hence erroneously lost)
```

The fix is to keep looping: [https://chromium-review.googlesource.com/c/v8/v8/+/5596273](<https://chromium-review.googlesource.com/c/v8/v8/+/5596273>)


---

**#13 — ap...@google.com — Jun 5, 2024 12:45AM**

Project: v8/v8  
Branch: main  
  
commit 910cb91733dc47b8f4a3dc9f1ca640b728f97aad  
Author: Jakob Kummerow <[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)>  
Date: Tue Jun 04 17:04:29 2024  
  
[wasm][liftoff][arm64] Fix DropExceptionValueAtOffset  
  
We cannot exit the iteration early, we must update all entries  
in the cache state.  
  
Fixed: 343748812  
Change-Id: I8353acb7bd0edc4b979db92e44d24cb9028fd92b  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5596273](<https://chromium-review.googlesource.com/c/v8/v8/+/5596273>)  
Reviewed-by: Clemens Backes <[clemensb@chromium.org](<mailto:clemensb@chromium.org>)>  
Commit-Queue: Clemens Backes <[clemensb@chromium.org](<mailto:clemensb@chromium.org>)>  
Auto-Submit: Jakob Kummerow <[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)>  
Commit-Queue: Jakob Kummerow <[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)>  
Cr-Commit-Position: refs/heads/main@{#94244}  
  
M src/wasm/baseline/liftoff-assembler.cc  
M test/mjsunit/mjsunit.status  
A test/mjsunit/regress/wasm/regress-343748812.js  
  
[https://chromium-review.googlesource.com/5596273](<https://chromium-review.googlesource.com/5596273>)


---

**#14 — rh...@gmail.com — Jun 5, 2024 01:03AM**

Thank you so much for quick fixes jkummerow@.


---

**#15 — pe...@google.com — Jun 6, 2024 12:43AM**

This is sufficiently serious that it should be merged to extended stable. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M124. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately.  
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

**#16 — pe...@google.com — Jun 6, 2024 12:57AM**

Merge review required: M126 has already been cut for stable release.  
  
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

**#17 — pe...@google.com — Jun 6, 2024 12:57AM**

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

**#18 — pe...@google.com — Jun 6, 2024 12:57AM**

Merge review required: M124 is already shipping to stable.  
  
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
Owners: eakpobaro (Android), eakpobaro (iOS), obenedict (ChromeOS), danielyip (Desktop)


---

**#20 — jk...@chromium.org — Jun 6, 2024 09:41PM**

#15:

  1. [https://chromium-review.googlesource.com/c/v8/v8/+/5596273](<https://chromium-review.googlesource.com/c/v8/v8/+/5596273>)
  2. Yes, 127.0.6522.0
  3. No
  4. No
  5. No

#16/#17/#18:

  1. Security fix
  2. [https://chromium-review.googlesource.com/c/v8/v8/+/5596273](<https://chromium-review.googlesource.com/c/v8/v8/+/5596273>)
  3. Yes, 127.0.6522.0
  4. The bug was more than a year old. There is no flag and no experiments.
  5. N/A
  6. No

Note: as far as I'm aware, the bug affects ARM (both 32 and 64 bits), but not x86 (neither 32 nor 64 bits).


---

**#21 — sr...@google.com — Jun 8, 2024 01:14AM**

M126 RC for stable is already cut earlier this week, I am recutting RC due to Releaseblock stable issues for which i am taking the merge, If any of your issues is serious enough that we cannot promote M126 with out the fix, please reach out to me asap, if not we will review these merges for first planned re-spin.


---

**#22 — am...@chromium.org — Jun 11, 2024 07:03AM**

There are no further planned releases of M125 and M126, removing merge labels for those. This does not need to be included in M126 first release. Given the timing of when the fix was landed, the plan for this fix is to merge approve it after M126 Stable recut occurs later today for inclusion in the first respin of M126.


---

**#23 — am...@chromium.org — Jun 13, 2024 06:29AM**

[https://crrev.com/c/5596273](<https://crrev.com/c/5596273>) approved for merge; please merge to branch 12.6 at your earliest convenience / by EOD tomorrow, Thursday, 13 June so this fix can be included in the next M126 Stable update -- thanks!


---

**#24 — ap...@google.com — Jun 13, 2024 07:58PM**

Project: v8/v8  
Branch: refs/branch-heads/12.6  
  
commit ba6cab40612dc92bb27592d7da436961148e13bf  
Author: Jakob Kummerow <[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)>  
Date: Thu Jun 13 12:26:46 2024  
  
Merged: [wasm][liftoff][arm64] Fix DropExceptionValueAtOffset  
  
We cannot exit the iteration early, we must update all entries  
in the cache state.  
  
Fixed: 343748812  
(cherry picked from commit 910cb91733dc47b8f4a3dc9f1ca640b728f97aad)  
  
Change-Id: Ib342467f35360baaa14cd098b258bd1acf4189a7  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5626023](<https://chromium-review.googlesource.com/c/v8/v8/+/5626023>)  
Commit-Queue: Matthias Liedtke <[mliedtke@chromium.org](<mailto:mliedtke@chromium.org>)>  
Commit-Queue: Jakob Kummerow <[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)>  
Reviewed-by: Matthias Liedtke <[mliedtke@chromium.org](<mailto:mliedtke@chromium.org>)>  
Auto-Submit: Jakob Kummerow <[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)>  
Cr-Commit-Position: refs/branch-heads/12.6@{#32}  
Cr-Branched-From: 3c9fa12db3183a6f4ea53d2675adb66ea1194529-refs/heads/12.6.228@{#2}  
Cr-Branched-From: 981bb15ba4dbf9e2381dfc94ec2c4af0b9c6a0b6-refs/heads/main@{#93835}  
  
M src/wasm/baseline/liftoff-assembler.cc  
M test/mjsunit/mjsunit.status  
A test/mjsunit/regress/wasm/regress-343748812.js  
  
[https://chromium-review.googlesource.com/5626023](<https://chromium-review.googlesource.com/5626023>)


---

**#25 — sp...@google.com — Jun 14, 2024 05:56AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $7000.00 for this report.  
  
Rationale for this decision:  
$7,000 for report of memory corruption in a sandboxed process (the renderer)   
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#26 — am...@chromium.org — Jun 14, 2024 06:14AM**

Congratulations! Thank you for your efforts and reporting this issue to us -- nice work.


---

**#27 — rh...@gmail.com — Jun 14, 2024 06:19AM**

Thank you everyone!


---

**#28 — pe...@google.com — Sep 12, 2024 12:41AM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
