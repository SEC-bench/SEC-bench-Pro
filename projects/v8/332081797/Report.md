# Type confusion in v8 wasm

Issue URL: https://issues.chromium.org/issues/332081797
VRP-Reward: 11500
Date: Apr 1, 2024 02:23AM


# Steps to reproduce the problem

/

# Problem Description

VULNERABILITY DETAILS

## INTRODUCE

After bisect, it was determined that following commit caused this problem.

  * Commit Info 
    * Version: 92487
    * link: [https://crrev.com/d09f312a14717fccc5ee0c4e8613bc83db4874d9](<https://crrev.com/d09f312a14717fccc5ee0c4e8613bc83db4874d9>)
  * Commit Message

```
commit	d09f312a14717fccc5ee0c4e8613bc83db4874d9	[log] [tgz]
author	Thibaud Michaud <thibaudm@chromium.org>	Wed Feb 21 14:04:05 2024
committer	V8 LUCI CQ <v8-scoped@luci-project-accounts.iam.gserviceaccount.com>	Thu Feb 22 17:46:47 2024

[wasm][exnref] Add kNoExnCode

https://github.com/WebAssembly/exception-handling/pull/298

R=manoskouk@chromium.org

Bug: v8:14398
Change-Id: I71800778370b6146685c16b45130be6e4947c526
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/5313520
Commit-Queue: Thibaud Michaud <thibaudm@chromium.org>
Reviewed-by: Manos Koukoutos <manoskouk@chromium.org>
Cr-Commit-Position: refs/heads/main@{#92487}
```

## reproduce

```
./d8 --experimental-wasm-exnref --allow-natives-syntax poc.js
```

## root cause

[0] In the DefaultValueForType function within src/wasm/constant-expression-interface.cc, when setting the default value for RefNull, if the type is kWasmExternRef, kWasmNullExternRef, or kWasmExnRef, it is set to null_value; otherwise, it is set to wasm_null.

```
case kRefNull:
    return WasmValue(
        type == kWasmExternRef || type == kWasmNullExternRef ||
                type == kWasmExnRef
            ? Handle<Object>::cast(isolate->factory()->null_value())
            : Handle<Object>::cast(isolate->factory()->wasm_null()), // ==> [0]
        type);
```

[1] However, elsewhere, pointers of type kWasmNullExnRef also use null_value as the basis for determining whether the pointer is null, such as in the LoadNullValue function within src/wasm/compiler/liftoff-compiler.cc.

```
void LoadNullValue(Register null, ValueType type) {
  __ LoadFullPointer(
      null, kRootRegister,
      type == kWasmExternRef || type == kWasmNullExternRef ||
              type == kWasmExnRef || type == kWasmNullExnRef // ==> [1]
          ? IsolateData::root_slot_offset(RootIndex::kNullValue)
          : IsolateData::root_slot_offset(RootIndex::kWasmNull));
}
```

[2] The inconsistency between assigning and checking for null pointers before and after could potentially lead to type confusion.

## CRASH LOG

  * Debug output **When executing the POC with debug-v8, it triggers a DCHECK error due to potential type confusion.**

```
$ ./out.gn/x64.debug/d8 --experimental-wasm-exnref --allow-natives-syntax poc.js
abort: CSA_DCHECK failed: Torque assert 'Is<A>(o)' failed [src/builtins/cast.tq:846] [../../src/builtins/js-to-wasm.tq:740] [../../src/builtins/js-to-wasm.tq:800]

==== JS stack trace =========================================

    0: ExitFrame [pc: 0x7f1bb70742bd]
    1: StubFrame [pc: 0x7f1bb764dd8e]
    2: JsToWasmFrame [pc: 0x7f1bb703af3c]
    3: 0 [0x270d002ae8e9] [wasm://wasm/2519ddea:~1] [pc=0x7f1bb7647c9b](this=0x270d00068ac1 <Object map = 0x270d002ae92d>#0#)
    4: /* anonymous */ [0x270d00298bc9] [poc.js:20] [bytecode=0x35f400040091 offset=300](this=0x270d002816c9 <JSGlobalProxy>#1#)
    5: InternalFrame [pc: 0x7f1bb6c54e9c]
    6: EntryFrame [pc: 0x7f1bb6c54bc7]

==== Details ================================================
......
```

  * release output **When executing the poc with release-v8, the wasm internal wasm null objects will be erroneously leaked to the JavaScript layer, enabling attackers to obtain them.**

```
./out.gn/x64.release/d8 --experimental-wasm-exnref --allow-natives-syntax poc.js
0x3dd40000fffd <Other heap object (WASM_NULL_TYPE)>
```

## Other

Please note to include the flags `--experimental-wasm-exnref --allow-natives-syntax` for clusterfuzz classification.

VERSION Tested on v8 version: 12.4.0 - 12.5.0

REPRODUCTION CASE

  1. Download release v8 from: gs://v8-asan/linux-release/d8-linux-release-v8-component-93098.zip or gs://v8-asan/linux-debug/d8-asan-linux-debug-v8-component-93098.zip
  2. Run: `d8 --experimental-wasm-exnref --allow-natives-syntax poc.js`

FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION Type of crash: tab

CREDIT INFORMATION Reporter credit:Jerry

# Summary

Type confusion in v8 wasm

# Additional Data

Category: Security   
Chrome Channel: Not sure   
Regression: N/A


---

**#2 — je...@gmail.com — Apr 1, 2024 02:27AM**

Here is the poc and crash.log


---

**#3 — je...@gmail.com — Apr 1, 2024 12:15PM**

The method to fix this vulnerability is similar to the RCE vulnerability I submitted previously ([https://issues.chromium.org/issues/40067712](<https://issues.chromium.org/issues/40067712>)). It only requires adding the corresponding case judgment to ensure it returns the correct null type.  
  
I have checked other potential inconsistencies and found no other vulnerabilities. Please apply my patch; I believe this fix is trivial.


---

**#4 — je...@gmail.com — Apr 1, 2024 10:36PM**

Since the POC I constructed will not crash in release, it will leak a wasm internal object to js.

If you use clusterfuzz sorting, please use **the debug version v8** and poc.js


---

**#5 — cl...@appspot.gserviceaccount.com — Apr 2, 2024 03:04AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=6391404753780736](<https://clusterfuzz.com/testcase?key=6391404753780736>).


---

**#6 — cl...@appspot.gserviceaccount.com — Apr 2, 2024 03:05AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=6227948331270144](<https://clusterfuzz.com/testcase?key=6227948331270144>).


---

**#7 — 24...@project.gserviceaccount.com — Apr 2, 2024 03:58AM**

Automatically applying components based on crash stacktrace and information from OWNERS files.  
  
If this is incorrect, please apply the hotlistid:4801165.


---

**#8 — 24...@project.gserviceaccount.com — Apr 2, 2024 03:58AM**

Automatically assigning owner based on suspected regression changelist [https://chromium.googlesource.com/v8/v8/+/d09f312a14717fccc5ee0c4e8613bc83db4874d9](<https://chromium.googlesource.com/v8/v8/+/d09f312a14717fccc5ee0c4e8613bc83db4874d9>) ([wasm][exnref] Add kNoExnCode).  
  
If this is incorrect, please let us know why and apply the hotlistid:5433122. If you aren't the correct owner for this issue, please unassign yourself as soon as possible so it can be re-triaged.


---

**#9 — 24...@project.gserviceaccount.com — Apr 2, 2024 03:58AM**

Detailed Report: [https://clusterfuzz.com/testcase?key=6227948331270144](<https://clusterfuzz.com/testcase?key=6227948331270144>)  
  
Fuzzer: None  
Job Type: linux_asan_d8_dbg  
Platform Id: linux  
  
Crash Type: Abrt  
Crash Address: 0x053900001364  
Crash State:  
Builtins_CEntry_Return1_ArgvOnStack_NoBuiltinExit  
Builtins_JSToWasmHandleReturns  
Builtins_JSToWasmWrapperAsm  
  
Sanitizer: address (ASAN)  
  
Regressed: [https://clusterfuzz.com/revisions?job=linux_asan_d8_dbg&range=92486:92487](<https://clusterfuzz.com/revisions?job=linux_asan_d8_dbg&range=92486:92487>)  
  
Reproducer Testcase: [https://clusterfuzz.com/download?testcase_id=6227948331270144](<https://clusterfuzz.com/download?testcase_id=6227948331270144>)  
  
To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.   
  
If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.  
  
If you have any feedback on reproducing test cases, let us know at [https://forms.gle/Yh3qCYFveHj6E5jz5](<https://forms.gle/Yh3qCYFveHj6E5jz5>) so we can improve.


---

**#10 — ca...@chromium.org — Apr 2, 2024 06:26AM**

Tentatively assigning high severity and cc-ing the V8 sheriff to change severity if necessary.


---

**#11 — pe...@google.com — Apr 3, 2024 12:39AM**

Setting milestone because of s0/s1 severity.


---

**#12 — pe...@google.com — Apr 3, 2024 12:39AM**

This is a serious security regression. If you are not able to fix this quickly, please revert the change that introduced it.  
  
If this doesn't affect a release branch, or has not been properly classified for severity, please update the Security Impact hotlist or the Severity field, and remove the ReleaseBlock hotlist.


---

**#13 — pe...@google.com — Apr 3, 2024 12:39AM**

Setting Priority to P1 to match Severity s1. If this is incorrect, please reset the priority. The automation bot account won't make this change again.


---

**#14 — th...@chromium.org — Apr 4, 2024 01:06AM**

This was fixed here today: [https://chromium-review.googlesource.com/c/v8/v8/+/5402583](<https://chromium-review.googlesource.com/c/v8/v8/+/5402583>)  
This requires enabling a staged feature so I removed the impact and release block labels, and this does not require a backmerge.


---

**#15 — pe...@google.com — Apr 5, 2024 12:42AM**

This is sufficiently serious that it should be merged to beta. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M124. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately.  
Merge review required: no relevant commits could be automatically detected (via Git Watcher comments), sending to merge review for manual evaluation. If you have not already manually listed the relevant commits to be merged via a comment above, please do so ASAP.  
  
  
Thank you for fixing this security bug! We aim to ship security fixes as quickly as possible, to limit their opportunity for exploitation as an "n-day" (that is, a bug where git fixes are developed into attacks before those fixes reach users).  
  
We have determined this fix is necessary on milestone(s): [124].  
  
Please answer the following questions so that we can safely process this merge request:  
1\. Which CLs should be backmerged? (Please include Gerrit links.)  
2\. Has this fix been verified on Canary to not pose any stability regressions?  
3\. Does this fix pose any potential non-verifiable stability risks?  
4\. Does this fix pose any known compatibility risks?  
5\. Does it require manual verification by the test team? If so, please describe required testing.


---

**#16 — am...@chromium.org — Apr 5, 2024 05:45AM**

updating as SI-none and removing merge labels since this issue is specific to --experimental-wasm-exnref


---

**#17 — 24...@project.gserviceaccount.com — Apr 11, 2024 01:13AM**

ClusterFuzz testcase 6227948331270144 is still reproducing on the latest available build r93280.  
  
Please re-test your fix against this testcase and if the fix was incorrect or incomplete, please re-open the bug. Otherwise, ignore this notification and add the hotlistid:5432646.


---

**#18 — ap...@google.com — Apr 11, 2024 05:37PM**

Project: v8/v8  
Branch: main  
  
commit cf03d55db2a0b7c5ff62e08ff5ad52312f6da0b4  
Author: Thibaud Michaud <[thibaudm@chromium.org](<mailto:thibaudm@chromium.org>)>  
Date: Wed Apr 10 19:36:55 2024  
  
[wasm][exnref] Fix default value for null exnref  
  
R=[manoskouk@chromium.org](<mailto:manoskouk@chromium.org>)  
  
Bug: 332081797  
Change-Id: Ied777935946c880a78e2011040a4d9ab19a4ddd2  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5444544](<https://chromium-review.googlesource.com/c/v8/v8/+/5444544>)  
Reviewed-by: Manos Koukoutos <[manoskouk@chromium.org](<mailto:manoskouk@chromium.org>)>  
Commit-Queue: Thibaud Michaud <[thibaudm@chromium.org](<mailto:thibaudm@chromium.org>)>  
Cr-Commit-Position: refs/heads/main@{#93310}  
  
M src/wasm/constant-expression-interface.cc  
  
[https://chromium-review.googlesource.com/5444544](<https://chromium-review.googlesource.com/5444544>)


---

**#19 — th...@chromium.org — Apr 11, 2024 05:56PM**

The actual fix was still missing, it has landed now (see last comment).  
This is still behind the --experimental-wasm-exnref flag, so it does not impact any release and does not require a backmerge.  
The feature is "staged" though, i.e. it's not considered experimental anymore, which AFAIK means that it still qualifies for VRP.


---

**#20 — am...@google.com — Apr 12, 2024 06:01AM**

*** Boilerplate reminders! ***  
Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.  
******************************


---

**#21 — am...@chromium.org — Apr 12, 2024 06:10AM**

Congratulations Jerry! The Chrome VRP Panel has decided to award you $10,000 for this high-quality report of memory corruption in a sandboxed process + $1,000 bisect bonus. Thank you for your efforts in reporting this issue to us -- great work!


---

**#22 — je...@gmail.com — Apr 12, 2024 07:49AM**

Thank you Chrome VRP, but I'd like to remind you that the fix for this vulnerability (#c18) is identical to the patch I provided in #c3, so can I still receive patch reward? :)


---

**#23 — am...@chromium.org — Apr 16, 2024 04:47PM**

It looks like a couple of changes were responsible for resolving this issue, which is why we did not issue a patch reward. thibaudm@ can you confirm if / that the supplied patch in c#3 would have solely resolved this issue?


---

**#24 — je...@gmail.com — Apr 16, 2024 05:47PM**

Hi Amy, as per [#comment17](<https://issues.chromium.org/issues/332081797#comment17>), clusterfuzz has mentioned that the patch from [#comment14](<https://issues.chromium.org/issues/332081797#comment14>) did not solve any issues.


---

**#25 — th...@google.com — Apr 16, 2024 05:53PM**

Please ignore [#comment14](<https://issues.chromium.org/issues/332081797#comment14>), I confused this with another fix.  
The proper fix was [#comment18](<https://issues.chromium.org/issues/332081797#comment18>), which is the same as what was suggested in [#comment3](<https://issues.chromium.org/issues/332081797#comment3>).


---

**#26 — je...@gmail.com — Apr 16, 2024 06:03PM**

Thank you for your confirmation :)


---

**#27 — am...@chromium.org — Apr 22, 2024 05:42PM**

Congratulations! The Chrome VRP Panel has decided to award you a $500 patch reward. Thank you for your patch submission as well as your patience while we got it through the reassessment process.


---

**#28 — pe...@google.com — Jul 14, 2024 12:52AM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
