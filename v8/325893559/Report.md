# Debug check failed: index < length() (2 vs. 1)

Issue URL: https://issues.chromium.org/issues/325893559
VRP-Reward: 12000
Date: Feb 20, 2024 02:10AM


## Title:

Debug check failed: index < length() (2 vs. 1)

## Component:

Blink>JavaScript>Runtime

## Description:

While auditing codes related to the newly shipped generic wasm-to-js wrapper, I found this vulnerability in the tier-up logic.

This is an OOB vulnerability during getting the ref of indirect function from `WasmDispatchTable` in `Runtime_TierUpWasmToJSWrapper`.

Crashed lines: both '[https://source.chromium.org/chromium/chromium/src/+/main:v8/src/runtime/runtime-wasm.cc;l=617](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/runtime/runtime-wasm.cc;l=617>)' and '[https://source.chromium.org/chromium/chromium/src/+/main:v8/src/runtime/runtime-wasm.cc;l=688](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/runtime/runtime-wasm.cc;l=688>)'. Like:

```
  if (WasmApiFunctionRef::CallOriginIsImportIndex(origin)) {
    int func_index = WasmApiFunctionRef::CallOriginAsIndex(origin);
    ImportedFunctionEntry entry(instance_object, func_index);
    entry.set_target(wasm_code->instruction_start());
  } else {
    // Indirect function table index.
    int entry_index = WasmApiFunctionRef::CallOriginAsIndex(origin);
    int table_count = trusted_data->dispatch_tables()->length();
    // We have to find the table which contains the correct entry.
    for (int table_index = 0; table_index < table_count; ++table_index) {
      Tagged<WasmDispatchTable> table =
          trusted_data->dispatch_table(table_index);
      if (table->ref(entry_index) == *ref) { // ---> [1]
        table->SetTarget(entry_index, wasm_code->instruction_start());
        // {ref} is used in at most one table.
        break;
      }
    }
  }
```

The main root cause is that in [1], `Runtime_TierUpWasmToJSWrapper` wants to use the `entry_index` to directly get the function ref from **each** WasmDispatchTable.

However, tables may have different sizes. If we use a large `entry_index` that exceeds the length of one WasmDispatchTable, the OOB will occur.

The `for` loop starts with the table that has a small index. So we may arrange two tables like that:

```
  builder.addTable(kWasmFuncRef, 1, 1)
  builder.addTable(kWasmFuncRef, 3, 3)
```

And then tier-up the 3rd function in the 2nd table.

As a result, the `for` loop will first get the 3rd function ref of the 1st table, whose length is 1. Thus an OOB will occur.

I wrote a testcase to stably trigger this vulnerability.

build on latest commit:

`6d26d2b5f88fbb3e3ea7020c2ec16e47ed1aceb6`

build command:

`python3 tools\dev\gm.py x64.debug`

run command (under `v8`, cause it needs the `test/mjsunit/wasm/wasm-module-builder.js`):

`out\x64.debug\d8.exe --wasm-wrapper-tiering-budget=1 poc.js`

Crash Log:

```
#
# Fatal error in ..\..\src\wasm\wasm-objects-inl.h, line 335
# Debug check failed: index < length() (2 vs. 1).
#
#
#
#FailureMessage Object: 0000001B533FD160
==== C stack trace ===============================

        v8::base::debug::StackTrace::StackTrace [0x00007FF890FB5FF5+37]
        v8::platform::`anonymous namespace'::PrintStackTrace [0x00007FF8B4F6AD29+57]
        V8_Fatal [0x00007FF890F86ED7+295]
        v8::base::`anonymous namespace'::DefaultDcheckHandler [0x00007FF890F868AC+44]
        V8_Dcheck [0x00007FF890F86FC6+86]
        v8::internal::WasmDispatchTable::ref [0x00007FF8015DA06A+154]
        v8::internal::__RT_impl_Runtime_TierUpWasmToJSWrapper [0x00007FF803188A28+3624]
        v8::internal::Runtime_TierUpWasmToJSWrapper [0x00007FF8031878FF+383]
        Builtins_WasmCEntry [0x00007FF805C0EA75+181]
        Builtins_WasmToJsWrapperCSA [0x00007FF805BD95F8+696]
        (No symbol) [0x00000114643C18F4]
```

## VERSION

Chrome Version: Tested on v8 12.3.0

Operating System: Tested on Windows 11

## BISECT:

I think the commit that shipped the generic wasm-to-js wrapper is the latest bisect for this vulnerability. Before this commit, we may need an experimental flag: `--wasm-to-js-generic-wrapper`.

[https://chromium-review.googlesource.com/c/v8/v8/+/5259577](<https://chromium-review.googlesource.com/c/v8/v8/+/5259577>)

```
[wasm] Enable generic wasm-to-js wrapper by default

Bug: v8:14035, chromium:1489280
Change-Id: I6b45d6c1b88d76591be913a8798722ec0eadb4e2
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/5259577
Commit-Queue: Andreas Haas <ahaas@chromium.org>
Reviewed-by: Clemens Backes <clemensb@chromium.org>
Cr-Commit-Position: refs/heads/main@{#92183
```

But the root commit that introduced this vulnerability should be:

[https://chromium-review.googlesource.com/c/v8/v8/+/4738319](<https://chromium-review.googlesource.com/c/v8/v8/+/4738319>)

```
Reland "[wasm] Wrapper tierup for the generic wasm-to-js wrapper"

This is a reland of commit 20c285f21c83ac2b37617d772618657e20beb0f8

Fixes:
The CL got reverted because of a failing isolate test. Like other
tier-up tests the new test does not work for isolate tests, therefore
I skip the test now for isolate tests.

Other changes:
I added one more flag guard, and I removed CHECKs which were actually
not necessary. Maybe this is what caused the performance regression?

...

Bug: v8:14035
Change-Id: Ia2965e1e6f95fd098c614fb44bda0a3cfd7d782c
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/4738319
Reviewed-by: Thibaud Michaud <thibaudm@chromium.org>
Commit-Queue: Andreas Haas <ahaas@chromium.org>
Cr-Commit-Position: refs/heads/main@{#89310}
```

## FIX PATCH:

Check the bound of the table first.

```
--- a/src/runtime/runtime-wasm.cc
+++ b/src/runtime/runtime-wasm.cc
@@ -614,7 +614,7 @@ RUNTIME_FUNCTION(Runtime_TierUpWasmToJSWrapper) {
     for (int table_index = 0; table_index < table_count; ++table_index) {
       Tagged<WasmDispatchTable> table =
           trusted_data->dispatch_table(table_index);
-      if (table->ref(entry_index) == *ref) {
+      if (entry_index < table->length() && table->ref(entry_index) == *ref) {
         canonical_sig_index = table->sig(entry_index);
         break;
       }
@@ -685,7 +685,7 @@ RUNTIME_FUNCTION(Runtime_TierUpWasmToJSWrapper) {
     for (int table_index = 0; table_index < table_count; ++table_index) {
       Tagged<WasmDispatchTable> table =
           trusted_data->dispatch_table(table_index);
-      if (table->ref(entry_index) == *ref) {
+      if (entry_index < table->length() && table->ref(entry_index) == *ref) {
         table->SetTarget(entry_index, wasm_code->instruction_start());
         // {ref} is used in at most one table.
         break;
```

## CREDIT:

5fceb6172bbf7e2c5a948183b53565b9


---

**#2 — jo...@gmail.com — Feb 20, 2024 02:17AM**

## Component:

Blink>JavaScript>Runtime

## Description:

While auditing codes related to the newly shipped generic wasm-to-js wrapper, I found this vulnerability in the tier-up logic.

This is an OOB vulnerability during getting the ref of indirect function from `WasmDispatchTable` in `Runtime_TierUpWasmToJSWrapper`.

Crashed lines: both '[https://source.chromium.org/chromium/chromium/src/+/main:v8/src/runtime/runtime-wasm.cc;l=617](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/runtime/runtime-wasm.cc;l=617>)' and '[https://source.chromium.org/chromium/chromium/src/+/main:v8/src/runtime/runtime-wasm.cc;l=688](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/runtime/runtime-wasm.cc;l=688>)'. Like:

```
  if (WasmApiFunctionRef::CallOriginIsImportIndex(origin)) {
    int func_index = WasmApiFunctionRef::CallOriginAsIndex(origin);
    ImportedFunctionEntry entry(instance_object, func_index);
    entry.set_target(wasm_code->instruction_start());
  } else {
    // Indirect function table index.
    int entry_index = WasmApiFunctionRef::CallOriginAsIndex(origin);
    int table_count = trusted_data->dispatch_tables()->length();
    // We have to find the table which contains the correct entry.
    for (int table_index = 0; table_index < table_count; ++table_index) {
      Tagged<WasmDispatchTable> table =
          trusted_data->dispatch_table(table_index);
      if (table->ref(entry_index) == *ref) { // ---> [1]
        table->SetTarget(entry_index, wasm_code->instruction_start());
        // {ref} is used in at most one table.
        break;
      }
    }
  }
```

The main root cause is that in [1], `Runtime_TierUpWasmToJSWrapper` wants to use the `entry_index` to directly get the function ref from **each** WasmDispatchTable.

However, tables may have different sizes. If we use a large `entry_index` that exceeds the length of one WasmDispatchTable, the OOB will occur.

The `for` loop starts with the table that has a small index. So we may arrange two tables like that:

```
  builder.addTable(kWasmFuncRef, 1, 1)
  builder.addTable(kWasmFuncRef, 3, 3)
```

And then tier-up the 3rd function in the 2nd table.

As a result, the `for` loop will first get the 3rd function ref of the 1st table, whose length is 1. Thus an OOB will occur.

I wrote a testcase to stably trigger this vulnerability.

build on latest commit:

`6d26d2b5f88fbb3e3ea7020c2ec16e47ed1aceb6`

build command:

`python3 tools\dev\gm.py x64.debug`

run command (under `v8`, cause it needs the `test/mjsunit/wasm/wasm-module-builder.js`):

`out\x64.debug\d8.exe --wasm-wrapper-tiering-budget=1 poc.js`

Crash Log:

```
#
# Fatal error in ..\..\src\wasm\wasm-objects-inl.h, line 335
# Debug check failed: index < length() (2 vs. 1).
#
#
#
#FailureMessage Object: 0000001B533FD160
==== C stack trace ===============================

        v8::base::debug::StackTrace::StackTrace [0x00007FF890FB5FF5+37]
        v8::platform::`anonymous namespace'::PrintStackTrace [0x00007FF8B4F6AD29+57]
        V8_Fatal [0x00007FF890F86ED7+295]
        v8::base::`anonymous namespace'::DefaultDcheckHandler [0x00007FF890F868AC+44]
        V8_Dcheck [0x00007FF890F86FC6+86]
        v8::internal::WasmDispatchTable::ref [0x00007FF8015DA06A+154]
        v8::internal::__RT_impl_Runtime_TierUpWasmToJSWrapper [0x00007FF803188A28+3624]
        v8::internal::Runtime_TierUpWasmToJSWrapper [0x00007FF8031878FF+383]
        Builtins_WasmCEntry [0x00007FF805C0EA75+181]
        Builtins_WasmToJsWrapperCSA [0x00007FF805BD95F8+696]
        (No symbol) [0x00000114643C18F4]
```

## VERSION

Chrome Version: Tested on v8 12.3.0

Operating System: Tested on Windows 11

## BISECT:

I think the commit that shipped the generic wasm-to-js wrapper is the latest bisect for this vulnerability. Before this commit, we may need an experimental flag: `--wasm-to-js-generic-wrapper`.

[https://chromium-review.googlesource.com/c/v8/v8/+/5259577](<https://chromium-review.googlesource.com/c/v8/v8/+/5259577>)

```
[wasm] Enable generic wasm-to-js wrapper by default

Bug: v8:14035, chromium:1489280
Change-Id: I6b45d6c1b88d76591be913a8798722ec0eadb4e2
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/5259577
Commit-Queue: Andreas Haas <ahaas@chromium.org>
Reviewed-by: Clemens Backes <clemensb@chromium.org>
Cr-Commit-Position: refs/heads/main@{#92183
```

But the root commit that introduced this vulnerability should be:

[https://chromium-review.googlesource.com/c/v8/v8/+/4738319](<https://chromium-review.googlesource.com/c/v8/v8/+/4738319>)

```
Reland "[wasm] Wrapper tierup for the generic wasm-to-js wrapper"

This is a reland of commit 20c285f21c83ac2b37617d772618657e20beb0f8

Fixes:
The CL got reverted because of a failing isolate test. Like other
tier-up tests the new test does not work for isolate tests, therefore
I skip the test now for isolate tests.

Other changes:
I added one more flag guard, and I removed CHECKs which were actually
not necessary. Maybe this is what caused the performance regression?

...

Bug: v8:14035
Change-Id: Ia2965e1e6f95fd098c614fb44bda0a3cfd7d782c
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/4738319
Reviewed-by: Thibaud Michaud <thibaudm@chromium.org>
Commit-Queue: Andreas Haas <ahaas@chromium.org>
Cr-Commit-Position: refs/heads/main@{#89310}
```

## FIX PATCH:

Check the bound of the table first.

```
--- a/src/runtime/runtime-wasm.cc
+++ b/src/runtime/runtime-wasm.cc
@@ -614,7 +614,7 @@ RUNTIME_FUNCTION(Runtime_TierUpWasmToJSWrapper) {
     for (int table_index = 0; table_index < table_count; ++table_index) {
       Tagged<WasmDispatchTable> table =
           trusted_data->dispatch_table(table_index);
-      if (table->ref(entry_index) == *ref) {
+      if (entry_index < table->length() && table->ref(entry_index) == *ref) {
         canonical_sig_index = table->sig(entry_index);
         break;
       }
@@ -685,7 +685,7 @@ RUNTIME_FUNCTION(Runtime_TierUpWasmToJSWrapper) {
     for (int table_index = 0; table_index < table_count; ++table_index) {
       Tagged<WasmDispatchTable> table =
           trusted_data->dispatch_table(table_index);
-      if (table->ref(entry_index) == *ref) {
+      if (entry_index < table->length() && table->ref(entry_index) == *ref) {
         table->SetTarget(entry_index, wasm_code->instruction_start());
         // {ref} is used in at most one table.
         break;
```

## CREDIT:

5fceb6172bbf7e2c5a948183b53565b9


---

**#3 — jo...@gmail.com — Feb 20, 2024 02:17AM**

upload `poc.js`


---

**#4 — cl...@appspot.gserviceaccount.com — Feb 20, 2024 04:37AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5138084848402432](<https://clusterfuzz.com/testcase?key=5138084848402432>).


---

**#5 — dr...@chromium.org — Feb 20, 2024 11:21AM**

Sorry, I didn't catch that this was a DCHECK. ClusterFuzz doesn't think there's consequences in a regular build, but I'll try a debug build to see if it can reproduce the DCHECK failure.


---

**#6 — cl...@appspot.gserviceaccount.com — Feb 20, 2024 11:22AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5152302129676288](<https://clusterfuzz.com/testcase?key=5152302129676288>).


---

**#7 — 24...@project.gserviceaccount.com — Feb 20, 2024 11:40AM**

Testcase 5152302129676288 failed to reproduce the crash. Please inspect the program output at [https://clusterfuzz.com/testcase?key=5152302129676288](<https://clusterfuzz.com/testcase?key=5152302129676288>).


---

**#8 — jo...@gmail.com — Feb 20, 2024 12:11PM**

Sorry, I think you need to repo it with a local debug build in the dir `v8/`. Because the poc needs the `test/mjsunit/wasm/wasm-module-builder.js` test file in the corresponding position, also flag `--wasm-wrapper-tiering-budget=1` should be passed to d8.


---

**#9 — jo...@gmail.com — Feb 20, 2024 01:41PM**

I learned to construct the testcase poc from commit [https://chromium-review.googlesource.com/c/v8/v8/+/5291374](<https://chromium-review.googlesource.com/c/v8/v8/+/5291374>). It is suitable for regress and the flag is used to trigger the tier-up easily.

I also prepared a version of poc that includes the wasm-module-builder.js and has no relies. I think it can run anywhere. You can verify it.

Just `d8.exe poc-full.js` is ok.

Also tested on `https://commondatastorage.googleapis.com/v8-asan/index.html?prefix=win64-debug/`, file `d8-asan-win64-debug-v8-component-92412.zip`.


---

**#10 — ah...@google.com — Feb 20, 2024 08:45PM**

[primary security shepherd]  
Rerouting to v8 security shepherd.  
Setting a provisional severity of High (S1)  
Setting a provisional Found In of the current Extended Stable (120).  
Assigning to the current V8 sheriff.


---

**#11 — cl...@chromium.org — Feb 20, 2024 10:00PM**

Thanks for the great analysis! The fix should be easy.  
Andreas, as this is your code, can you upload the fix and then later the regression test (once the fix has shipped)?  
  
I'll also try uploading to Clusterfuzz in the meantime.


---

**#12 — cl...@appspot.gserviceaccount.com — Feb 20, 2024 10:02PM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=6485086853070848](<https://clusterfuzz.com/testcase?key=6485086853070848>).


---

**#13 — pe...@google.com — Feb 21, 2024 12:42AM**

Setting milestone because of s0/s1 severity.


---

**#14 — pe...@google.com — Feb 21, 2024 12:42AM**

Setting Priority to P1 to match Severity s1. If this is incorrect, please reset the priority. The automation bot account won't make this change again.


---

**#15 — ap...@google.com — Feb 21, 2024 08:02PM**

Project: v8/v8  
Branch: main  
  
commit 7330f46163e8a2c10a3d40ecbf554656f0ac55e8  
Author: Andreas Haas <[ahaas@chromium.org](<mailto:ahaas@chromium.org>)>  
Date: Tue Feb 20 16:27:22 2024  
  
[wasm] Add bounds check in tier-up of wasm-to-js wrapper  
  
The entry index in the WasmApiFunctionRef was used to look for the given  
WasmApiFunctionRef in the indirect function tables, but it was not  
considered that the indirect function tables can have different lengths.  
  
R=[clemensb@chromium.org](<mailto:clemensb@chromium.org>)  
  
Bug: 325893559  
Change-Id: I0497c7a769515345d586d250cc71e0dfc7c70394  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5309898](<https://chromium-review.googlesource.com/c/v8/v8/+/5309898>)  
Reviewed-by: Clemens Backes <[clemensb@chromium.org](<mailto:clemensb@chromium.org>)>  
Commit-Queue: Andreas Haas <[ahaas@chromium.org](<mailto:ahaas@chromium.org>)>  
Cr-Commit-Position: refs/heads/main@{#92442}  
  
M src/runtime/runtime-wasm.cc  
  
[https://chromium-review.googlesource.com/5309898](<https://chromium-review.googlesource.com/5309898>)


---

**#16 — pe...@google.com — Feb 22, 2024 08:14PM**

Merge review required: M122 is already shipping to stable.  
  
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
Owners: eakpobaro (Android), eakpobaro (iOS), ceb (ChromeOS), pbommana (Desktop)


---

**#17 — ah...@chromium.org — Feb 23, 2024 12:10AM**

1\. Why does your merge fit within the merge criteria for these milestones?  
I'm not sure if an how this bug can be exploited. It is quite easy to construct an OOB read. If the OOB read results in a specific bit pattern, then there would also be an OOB write. However, the attacker does not have full control over the value that is written. The value is the instruction start of a newly compiled V8 builtin. If the attacker can control where the V8 builtin gets allocated, then they can control the value that gets written.  
2\. What changes specifically would you like to merge? Please link to Gerrit.  
[https://chromium-review.googlesource.com/c/v8/v8/+/5309898](<https://chromium-review.googlesource.com/c/v8/v8/+/5309898>)  
3\. Have the changes been released and tested on canary?  
Yes, in 124.0.6315.0  
4\. Is this a new feature? If yes, is it behind a Finch flag and are experiments active in any release channels?  
The feature was shipped with Finch in 121.0.6143.0  
5\. [Chrome OS only]: Was the change reviewed and approved by the Eng Prod Representative? [https://goto.google.com/cros-engprodcomponents](<https://goto.google.com/cros-engprodcomponents>)  
6\. If this merge addresses a major issue in the stable channel, does it require manual verification by the test team? If so, please describe required testing.  
No


---

**#18 — ea...@google.com — Feb 23, 2024 12:54AM**

Please appropriate OSs label ASAP so it gets reviewed by respective release TPM for M122


---

**#19 — am...@chromium.org — Feb 23, 2024 04:01AM**

Security issues should be closed as fixed when the resolving CLs are landed. This allows the bot to update this issue with appropriate security and merge tags. There is no need to manually update security issues with merge requests :) This fix was landed on 124 and requires merge review for 123 as well. Adding that tag in the meantime of the fix getting a bit more bake time.


---

**#20 — pe...@google.com — Feb 23, 2024 11:46AM**

This high+ V8 security issue with stable impact requires a lightweight post mortem. Please take some time to answer questions asked in this form [1] to help us improve V8 security. [1] [https://docs.google.com/forms/d/e/1FAIpQLSdSMCiEpIFLLFkMbgtulK1sf1B-idQmkFaA4XP2Rz5mN1cqWg/viewform?usp=pp_url&entry.307501673=325893559&entry.364066060=johnshoopshell@gmail.com&entry.958145677=Android](<https://docs.google.com/forms/d/e/1FAIpQLSdSMCiEpIFLLFkMbgtulK1sf1B-idQmkFaA4XP2Rz5mN1cqWg/viewform?usp=pp_url&entry.307501673=325893559&entry.364066060=johnshoopshell@gmail.com&entry.958145677=Android>), Fuchsia, Linux, Mac, Windows, Lacros, ChromeOS&entry.763880440=Extended&entry.1678852700=High&entry.763402679=Blink>JavaScript>WebAssembly&entry.975983575=[ahaas@chromium.org](<mailto:ahaas@chromium.org>) Please ensure to copy the full link, as otherwise some issue meta data might not be populated automatically.


---

**#21 — am...@chromium.org — Feb 27, 2024 06:03AM**

I had approved this originally before seeing the flags required in the original report, then upon a secondary review see this feature was finched in 121, so re-approving for M123 and M122 merges.

Please merge [https://crrev.com/c/5309898](<https://crrev.com/c/5309898>) to M123 Beta by EOD Tuesday, 27 February, and M122 Stable by EOD, Thursday, 29 February so this fix can be included in their next respective updates -- thank you and apologies for all the email pings that would have resulted from all my tag changes.


---

**#22 — ap...@google.com — Feb 27, 2024 06:50PM**

Project: v8/v8  
Branch: refs/branch-heads/12.2  
  
commit 5578c6dd3a12dd66a85d075c599a6816efe68904  
Author: Andreas Haas <[ahaas@chromium.org](<mailto:ahaas@chromium.org>)>  
Date: Tue Feb 20 16:27:22 2024  
  
Merged: [wasm] Add bounds check in tier-up of wasm-to-js wrapper  
  
The entry index in the WasmApiFunctionRef was used to look for the given  
WasmApiFunctionRef in the indirect function tables, but it was not  
considered that the indirect function tables can have different lengths.  
  
R=[clemensb@chromium.org](<mailto:clemensb@chromium.org>)  
  
Bug: 325893559  
  
(cherry picked from commit 7330f46163e8a2c10a3d40ecbf554656f0ac55e8)  
  
Change-Id: I52355890e21490c75566216985680c64e0b0db75  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5323850](<https://chromium-review.googlesource.com/c/v8/v8/+/5323850>)  
Commit-Queue: Andreas Haas <[ahaas@chromium.org](<mailto:ahaas@chromium.org>)>  
Reviewed-by: Thibaud Michaud <[thibaudm@chromium.org](<mailto:thibaudm@chromium.org>)>  
Cr-Commit-Position: refs/branch-heads/12.2@{#38}  
Cr-Branched-From: 6eb5a9616aa6f8c705217aeb7c7ab8c037a2f676-refs/heads/12.2.281@{#1}  
Cr-Branched-From: 44cf56d850167c6988522f8981730462abc04bcc-refs/heads/main@{#91934}  
  
M src/runtime/runtime-wasm.cc  
  
[https://chromium-review.googlesource.com/5323850](<https://chromium-review.googlesource.com/5323850>)


---

**#23 — pe...@google.com — Feb 27, 2024 07:00PM**

LTS Milestone M120  
  
This issue has been flagged as a merge candidate for Chrome OS' LTS channel. If selected, our merge team will handle any additional merges. To help us determine if this issue requires a merge to LTS, please answer this short questionnaire:  
1\. Was this issue a regression for the milestone it was found in?  
2\. Is this issue related to a change or feature merged after the latest LTS Milestone?


---

**#24 — ap...@google.com — Feb 27, 2024 07:16PM**

Project: v8/v8  
Branch: refs/branch-heads/12.3  
  
commit ef0aebab74101c97dcb4537146c32f63c9e2b8aa  
Author: Andreas Haas <[ahaas@chromium.org](<mailto:ahaas@chromium.org>)>  
Date: Tue Feb 20 16:27:22 2024  
  
Merged: [wasm] Add bounds check in tier-up of wasm-to-js wrapper  
  
The entry index in the WasmApiFunctionRef was used to look for the given  
WasmApiFunctionRef in the indirect function tables, but it was not  
considered that the indirect function tables can have different lengths.  
  
R=[clemensb@chromium.org](<mailto:clemensb@chromium.org>)  
  
Bug: 325893559  
(cherry picked from commit 7330f46163e8a2c10a3d40ecbf554656f0ac55e8)  
  
Change-Id: I160dce22dc468b8dc87dd71c7c24873523e3ca9c  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5324391](<https://chromium-review.googlesource.com/c/v8/v8/+/5324391>)  
Commit-Queue: Andreas Haas <[ahaas@chromium.org](<mailto:ahaas@chromium.org>)>  
Reviewed-by: Thibaud Michaud <[thibaudm@chromium.org](<mailto:thibaudm@chromium.org>)>  
Cr-Commit-Position: refs/branch-heads/12.3@{#8}  
Cr-Branched-From: a86e1971579f4165123467fa6ad378e552536b43-refs/heads/12.3.219@{#1}  
Cr-Branched-From: 21869f7f6f3e8f5a58a0b2e61e0f7412480230b1-refs/heads/main@{#92385}  
  
M src/runtime/runtime-wasm.cc  
  
[https://chromium-review.googlesource.com/5324391](<https://chromium-review.googlesource.com/5324391>)


---

**#25 — ah...@chromium.org — Feb 27, 2024 08:45PM**

This issue has been flagged as a merge candidate for Chrome OS' LTS channel. If selected, our merge team will handle any additional merges. To help us determine if this issue requires a merge to LTS, please answer this short questionnaire:  
1\. Was this issue a regression for the milestone it was found in?  
2\. Is this issue related to a change or feature merged after the latest LTS Milestone?  
  
The feature this issue was found in shipped with finch after M120.


---

**#26 — am...@google.com — Feb 29, 2024 10:04AM**

*** Boilerplate reminders! ***  
Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.  
******************************


---

**#27 — am...@chromium.org — Feb 29, 2024 10:10AM**

Congratulations! The Chrome VRP Panel has decided to award you $10,000 for this high quality report of a renderer process memory corruption + $1,000 bisect bonus + $1,000 patch bonus. A member of the Google p2p-vrp@ will be in contact with you soon to arrange payment. In the meantime, please let us know what name or tag/pseudonym would like us to use in acknowledging you for this finding. Thank you for your efforts and reporting this issue to us -- great work!

(Kind reminder, in your future reports, please remember of provide technical details in the original report (description block) rather than as comments.)


---

**#28 — jo...@gmail.com — Mar 4, 2024 09:57PM**

Re [comment #27](<https://issues.chromium.org/issues/325893559#comment27>): Got it, thanks! Credit: 5fceb6172bbf7e2c5a948183b53565b9


---

**#29 — pe...@google.com — Apr 3, 2024 02:31AM**

This issue requires additional review before it can be merged to the LTS channel. Please answer the following questions to help us evaluate this merge:  
  
1\. Number of CLs needed for this fix and links to them.  
2\. Level of complexity (High, Medium, Low - Explain)  
3\. Has this been merged to a stable release? beta release?  
4\. Overall Recommendation (Yes, No)


---

**#30 — rz...@google.com — Apr 3, 2024 02:34AM**

1. [https://crrev.com/c/5410369](<https://crrev.com/c/5410369>)
  2. Low, only a few simple conflicts
  3. 122, 123
  4. Yes


---

**#31 — ah...@chromium.org — Apr 3, 2024 05:04PM**

The finch trial for the feature that contains the issue started in M121, so I think a merge to M120 is not necessary.


---

**#32 — rz...@google.com — Apr 16, 2024 02:18AM**

Thanks ahaas@. Labelling this bug as not applicable for M120.


---

**#33 — pe...@google.com — Jun 1, 2024 12:43AM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
