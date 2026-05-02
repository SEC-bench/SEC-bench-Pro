# Debug check failed: IsWasmDispatchTable(table)

Issue URL: https://issues.chromium.org/issues/325878101
VRP-Reward: 12000
Date: Feb 20, 2024 12:56AM


## Title:

Debug check failed: IsWasmDispatchTable(table)

## VULNERABILITY DETAILS

see [comment #2](<https://issues.chromium.org/issues/325878101#comment2>).


---

**#2 — jo...@gmail.com — Feb 20, 2024 12:57AM**

## Component:

Blink>JavaScript>Runtime

## Description:

While auditing codes related to the newly shipped generic wasm-to-js wrapper, I found this vulnerability in the tier-up logic.

This is a type confusion: take as a `WasmDispatchTable` during `Runtime_TierUpWasmToJSWrapper`.

It crashed on the type cast line, both '[https://source.chromium.org/chromium/chromium/src/+/main:v8/src/runtime/runtime-wasm.cc;l=616](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/runtime/runtime-wasm.cc;l=616>)' and '[https://source.chromium.org/chromium/chromium/src/+/main:v8/src/runtime/runtime-wasm.cc;l=687](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/runtime/runtime-wasm.cc;l=687>)'. Like:

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
          trusted_data->dispatch_table(table_index);// ---> [1]
      if (table->ref(entry_index) == *ref) {
        table->SetTarget(entry_index, wasm_code->instruction_start());
        // {ref} is used in at most one table.
        break;
      }
    }
  }
```

The main root cause is that not every element in `trusted_data->dispatch_tables()` is filled with `WasmDispatchTable`, only table with funcref type satisfies that.

But `Runtime_TierUpWasmToJSWrapper` failed to check this condition first before type cast. It should be treated like '[https://source.chromium.org/chromium/chromium/src/+/main:v8/src/runtime/runtime-test-wasm.cc;l=166](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/runtime/runtime-test-wasm.cc;l=166>)'. Like:

```
  for (int table_index = 0; table_index < table_count; ++table_index) {
    if (dispatch_tables->get(table_index) == Smi::zero()) continue;// ---> [2]
    Tagged<WasmDispatchTable> table =
        Tagged<WasmDispatchTable>::cast(dispatch_tables->get(table_index));
    int table_size = table->length();
    for (int entry_index = 0; entry_index < table_size; ++entry_index) {
      if (table->target(entry_index) == wrapper_start) ++result;
    }
  }
```

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
# Fatal error in ..\..\src\wasm\wasm-objects-inl.h, line 280
# Debug check failed: IsWasmDispatchTable(table).
#
#
#
#FailureMessage Object: 000000AF271FD330
==== C stack trace ===============================

        v8::base::debug::StackTrace::StackTrace [0x00007FF890FB5FF5+37]
        v8::platform::`anonymous namespace'::PrintStackTrace [0x00007FF890E2AD29+57]
        V8_Fatal [0x00007FF890F86ED7+295]
        v8::base::`anonymous namespace'::DefaultDcheckHandler [0x00007FF890F868AC+44]
        V8_Dcheck [0x00007FF890F86FC6+86]
        v8::internal::WasmTrustedInstanceData::dispatch_table [0x00007FF8031A2A95+181]
        v8::internal::__RT_impl_Runtime_TierUpWasmToJSWrapper [0x00007FF803188929+3369]
        v8::internal::Runtime_TierUpWasmToJSWrapper [0x00007FF8031878FF+383]
        Builtins_WasmCEntry [0x00007FF805C0E9B5+181]
        Builtins_WasmToJsWrapperCSA [0x00007FF805BD9538+696]
        (No symbol) [0x0000032371A418F1]
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

Check the condition first.

```
--- a/src/runtime/runtime-wasm.cc
+++ b/src/runtime/runtime-wasm.cc
@@ -612,6 +612,7 @@ RUNTIME_FUNCTION(Runtime_TierUpWasmToJSWrapper) {
     int table_count = trusted_data->dispatch_tables()->length();
     // We have to find the table which contains the correct entry.
     for (int table_index = 0; table_index < table_count; ++table_index) {
+      if (trusted_data->dispatch_tables()->get(table_index) == Smi::zero()) continue;
       Tagged<WasmDispatchTable> table =
           trusted_data->dispatch_table(table_index);
       if (table->ref(entry_index) == *ref) {
@@ -683,6 +684,7 @@ RUNTIME_FUNCTION(Runtime_TierUpWasmToJSWrapper) {
     int table_count = trusted_data->dispatch_tables()->length();
     // We have to find the table which contains the correct entry.
     for (int table_index = 0; table_index < table_count; ++table_index) {
+      if (trusted_data->dispatch_tables()->get(table_index) == Smi::zero()) continue;
       Tagged<WasmDispatchTable> table =
           trusted_data->dispatch_table(table_index);
       if (table->ref(entry_index) == *ref) {
```

## CREDIT:

5fceb6172bbf7e2c5a948183b53565b9


---

**#4 — jo...@gmail.com — Feb 20, 2024 02:26AM**

upload `poc.js`


---

**#5 — cl...@appspot.gserviceaccount.com — Feb 20, 2024 04:36AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5137890769567744](<https://clusterfuzz.com/testcase?key=5137890769567744>).


---

**#6 — dr...@chromium.org — Feb 20, 2024 11:20AM**

Sorry, I didn't catch that this was a DCHECK. ClusterFuzz doesn't think there's consequences in a regular build, but I'll try a debug build to see if it can reproduce the DCHECK failure.


---

**#7 — cl...@appspot.gserviceaccount.com — Feb 20, 2024 11:21AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5335676530130944](<https://clusterfuzz.com/testcase?key=5335676530130944>).


---

**#8 — jo...@gmail.com — Feb 20, 2024 12:11PM**

Sorry, I think you need to repo it with a local debug build in the dir `v8/`. Because the poc needs the `test/mjsunit/wasm/wasm-module-builder.js` test file in the corresponding position, also flag `--wasm-wrapper-tiering-budget=1` should be passed to d8.


---

**#9 — jo...@gmail.com — Feb 20, 2024 01:45PM**

I learned to construct the testcase poc from commit [https://chromium-review.googlesource.com/c/v8/v8/+/5291374](<https://chromium-review.googlesource.com/c/v8/v8/+/5291374>). It is suitable for regress and the flag is used to trigger the tier-up easily.

I also prepared a version of poc that includes the wasm-module-builder.js and has no relies. I think it can run anywhere. You can verify it.

Just `d8.exe poc-full.js` is ok.

Also tested on `https://commondatastorage.googleapis.com/v8-asan/index.html?prefix=win64-debug/`, file `d8-asan-win64-debug-v8-component-92412.zip`.


---

**#10 — ah...@google.com — Feb 20, 2024 08:34PM**

Thanks for the report!  
Setting a provisional severity of High (S1)  
Setting a provisional Found In of the current Extended Stable (120).  
Assigning to the current V8 sheriff.


---

**#11 — cl...@appspot.gserviceaccount.com — Feb 20, 2024 10:04PM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5143637838462976](<https://clusterfuzz.com/testcase?key=5143637838462976>).


---

**#12 — 24...@project.gserviceaccount.com — Feb 21, 2024 12:16AM**

Automatically applying components based on crash stacktrace and information from OWNERS files.  
  
If this is incorrect, please apply the hotlistid:4801165.


---

**#13 — 24...@project.gserviceaccount.com — Feb 21, 2024 12:16AM**

Detailed Report: [https://clusterfuzz.com/testcase?key=5143637838462976](<https://clusterfuzz.com/testcase?key=5143637838462976>)  
  
Fuzzer: None  
Job Type: linux_asan_d8_dbg  
Platform Id: linux  
  
Crash Type: DCHECK failure  
Crash Address:   
Crash State:  
IsWasmDispatchTable(table) in wasm-objects-inl.h  
v8::internal::WasmTrustedInstanceData::dispatch_table  
v8::internal::__RT_impl_Runtime_TierUpWasmToJSWrapper  
  
Sanitizer: address (ASAN)  
  
Regressed: [https://clusterfuzz.com/revisions?job=linux_asan_d8_dbg&range=92233:92234](<https://clusterfuzz.com/revisions?job=linux_asan_d8_dbg&range=92233:92234>)  
  
Reproducer Testcase: [https://clusterfuzz.com/download?testcase_id=5143637838462976](<https://clusterfuzz.com/download?testcase_id=5143637838462976>)  
  
To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.   
  
If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.  
  
If you have any feedback on reproducing test cases, let us know at [https://forms.gle/Yh3qCYFveHj6E5jz5](<https://forms.gle/Yh3qCYFveHj6E5jz5>) so we can improve.


---

**#14 — pe...@google.com — Feb 21, 2024 12:42AM**

Setting milestone because of s0/s1 severity.


---

**#15 — pe...@google.com — Feb 21, 2024 12:42AM**

Setting Priority to P1 to match Severity s1. If this is incorrect, please reset the priority. The automation bot account won't make this change again.


---

**#16 — cl...@chromium.org — Feb 22, 2024 01:14AM**

This was introduced in M123 only.


---

**#17 — ap...@google.com — Feb 22, 2024 06:30PM**

Project: v8/v8  
Branch: main  
  
commit ca1b752554f3426afbc7d8b48f9260c2a433266d  
Author: Clemens Backes <[clemensb@chromium.org](<mailto:clemensb@chromium.org>)>  
Date: Wed Feb 21 18:12:00 2024  
  
[wasm] Check for missing dispatch tables  
  
Wrapper tier up iterates all dispatch tables to find the relevant entry.  
Not all tables also allocate dispatch tables though. We need to skip  
non-existing ones.  
  
R=[ahaas@chromium.org](<mailto:ahaas@chromium.org>)  
  
Fixed: 325878101  
Change-Id: I52266ddb23563cee9e5eee3537173ca98792b933  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5314660](<https://chromium-review.googlesource.com/c/v8/v8/+/5314660>)  
Reviewed-by: Andreas Haas <[ahaas@chromium.org](<mailto:ahaas@chromium.org>)>  
Commit-Queue: Clemens Backes <[clemensb@chromium.org](<mailto:clemensb@chromium.org>)>  
Cr-Commit-Position: refs/heads/main@{#92470}  
  
M src/runtime/runtime-wasm.cc  
M src/wasm/wasm-objects-inl.h  
M src/wasm/wasm-objects.h  
A test/mjsunit/regress/wasm/regress-325878101.js  
  
[https://chromium-review.googlesource.com/5314660](<https://chromium-review.googlesource.com/5314660>)


---

**#18 — pe...@google.com — Feb 23, 2024 06:43PM**

Merge approved: your change passed merge requirements and is auto-approved for M123. Please go ahead and merge the CL to branch 6312 (refs/branch-heads/6312) manually. Please contact milestone owner if you have questions.  
Merge instructions: [https://chromium.googlesource.com/chromium/src.git/+/refs/heads/main/docs/process/merge_request.md](<https://chromium.googlesource.com/chromium/src.git/+/refs/heads/main/docs/process/merge_request.md>)  
Owners: govind (Android), govind (iOS), dgagnon (ChromeOS), srinivassista (Desktop)


---

**#19 — ap...@google.com — Feb 23, 2024 07:22PM**

Project: v8/v8  
Branch: refs/branch-heads/12.3  
  
commit 604c9e6679198a4895392792ce56369db00e231c  
Author: Clemens Backes <[clemensb@chromium.org](<mailto:clemensb@chromium.org>)>  
Date: Wed Feb 21 18:12:00 2024  
  
Merged: [wasm] Check for missing dispatch tables  
  
Wrapper tier up iterates all dispatch tables to find the relevant entry.  
Not all tables also allocate dispatch tables though. We need to skip  
non-existing ones.  
  
R=[ahaas@chromium.org](<mailto:ahaas@chromium.org>)  
  
(cherry picked from commit ca1b752554f3426afbc7d8b48f9260c2a433266d)  
  
Bug: 325878101  
Change-Id: Ic3bf02dcf32ae2d1e73693f5e57d1dbc565c2b5b  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5319672](<https://chromium-review.googlesource.com/c/v8/v8/+/5319672>)  
Commit-Queue: Clemens Backes <[clemensb@chromium.org](<mailto:clemensb@chromium.org>)>  
Reviewed-by: Andreas Haas <[ahaas@chromium.org](<mailto:ahaas@chromium.org>)>  
Cr-Commit-Position: refs/branch-heads/12.3@{#6}  
Cr-Branched-From: a86e1971579f4165123467fa6ad378e552536b43-refs/heads/12.3.219@{#1}  
Cr-Branched-From: 21869f7f6f3e8f5a58a0b2e61e0f7412480230b1-refs/heads/main@{#92385}  
  
M src/runtime/runtime-wasm.cc  
M src/wasm/wasm-objects-inl.h  
M src/wasm/wasm-objects.h  
A test/mjsunit/regress/wasm/regress-325878101.js  
  
[https://chromium-review.googlesource.com/5319672](<https://chromium-review.googlesource.com/5319672>)


---

**#20 — pe...@google.com — Feb 23, 2024 07:34PM**

LTS Milestone M120  
  
This issue has been flagged as a merge candidate for Chrome OS' LTS channel. If selected, our merge team will handle any additional merges. To help us determine if this issue requires a merge to LTS, please answer this short questionnaire:  
1\. Was this issue a regression for the milestone it was found in?  
2\. Is this issue related to a change or feature merged after the latest LTS Milestone?


---

**#21 — am...@google.com — Feb 29, 2024 10:04AM**

*** Boilerplate reminders! ***  
Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.  
******************************


---

**#22 — am...@chromium.org — Feb 29, 2024 10:11AM**

Congratulations on another one, OP! The Chrome VRP Panel has decided to award you $10,000 for this high quality report of a renderer process memory corruption + $1,000 bisect bonus + $1,000 patch bonus. A member of the Google p2p-vrp@ will be in contact with you soon to arrange payment. In the meantime, please let us know what name or tag/pseudonym would like us to use in acknowledging you for this finding. Thank you for your efforts and reporting this issue to us -- great work!

(Kind reminder, in your future reports, please remember of provide technical details in the original report (description block) rather than as comments.)


---

**#23 — jo...@gmail.com — Mar 4, 2024 10:06PM**

Re [comment #22](<https://issues.chromium.org/issues/325878101#comment22>): Got it, thanks! Credit: 5fceb6172bbf7e2c5a948183b53565b9


---

**#24 — vo...@google.com — Mar 26, 2024 01:38PM**

Marking as not applicable to M120 LTS because --wasm-to-js-generic-wrapper only became default in M123.


---

**#25 — pe...@google.com — Jun 1, 2024 12:43AM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
