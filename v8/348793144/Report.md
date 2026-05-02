# Abrt in Builtins_CEntry_Return1_ArgvOnStack_NoBuiltinExit

Issue URL: https://issues.chromium.org/issues/348793144
VRP-Reward: 8000
Date: Jun 23, 2024 12:07PM


VULNERABILITY DETAILS

## INTRODUCE

After bisect, it was determined that following commit caused this problem.

  * Commit Info 
    * Version: 93470
    * link: [https://crrev.com/125189fa267b75cc8b7d4db870daa98958ee11dd](<https://crrev.com/125189fa267b75cc8b7d4db870daa98958ee11dd>)
  * Commit Message

```
commit 125189fa267b75cc8b7d4db870daa98958ee11dd
Author: Thibaud Michaud <thibaudm@chromium.org>
Date:   Thu Apr 18 18:21:36 2024 +0200

    [wasm][jspi] Remove explicit suspender param in export wrapper
    
    Do not generate an additional explicit externref parameter for the newly
    allocated Suspender object in the WebAssembly.promising export wrapper.
    The import wrapper already uses the active suspender implicitly.
    
    R=ahaas@chromium.org
    
    Bug: v8:14722
    Change-Id: Ibcfe887dd343704f628a3cbb3931057331824da1
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/5464463
    Reviewed-by: Andreas Haas <ahaas@chromium.org>
    Commit-Queue: Thibaud Michaud <thibaudm@chromium.org>
    Cr-Commit-Position: refs/heads/main@{#93470}
```

## CRASH LOG

  * Debug output

```
# CMD: /tmp/d8-linux-debug-v8-component-94592/d8 --wasm-staging poc.js
# OUTPUT ==============================================================
abort: CSA_DCHECK failed: Torque assert 'paramKind == ValueKind::kRef || paramKind == ValueKind::kRefNull' failed [src/builtins/js-to-wasm.tq:669] [../../src/builtins/js-to-wasm.tq:786]

==== JS stack trace =========================================

    0: ExitFrame [pc: 0x7fc9d8aac87d]
    1: 17 [0x37520029c2c9] [wasm://wasm/eb46e57e:~1] [pc=0x7fc9d9015228](this=0x3752002816c9 <JSGlobalProxy>#0#)
    2: /* anonymous */ [0x37520029aad1] [output_poc.js:12] [bytecode=0x26eb00040065 offset=167](this=0x3752002816c9 <JSGlobalProxy>#0#)
    3: InternalFrame [pc: 0x7fc9d86d57dc]
    4: EntryFrame [pc: 0x7fc9d86d551f]

==== Details ================================================

[0]: ExitFrame [pc: 0x7fc9d8aac87d]
[1]: 17 [0x37520029c2c9] [wasm://wasm/eb46e57e:~1] [pc=0x7fc9d9015228](this=0x3752002816c9 <JSGlobalProxy>#0#) {
// optimized frame
--------- s o u r c e   c o d e ---------
<No Source>
-----------------------------------------
}
[2]: /* anonymous */ [0x37520029aad1] [output_poc.js:12] [bytecode=0x26eb00040065 offset=167](this=0x3752002816c9 <JSGlobalProxy>#0#) {
  // heap-allocated locals
  var kBuiltins = 0x37520004a8c5 <FixedArray[1]>#1#
  // expression stack (top to bottom)
  [07] : 0x3752002816c9 <JSGlobalProxy>#0#
  [06] : 0x375200000069 <undefined>
  [05] : 0x375200000069 <undefined>
  [04] : 0x375200000069 <undefined>
  [03] : 0x37520029c0f1 <JSFunction js-to-wasm:sii:i (sfi = 0x37520029c0c1)>#2#
  [02] : 0x37520029280d <WebAssembly map = 0x375200298e19>#3#
  [01] : 0x37520029c2c9 <JSFunction js-to-wasm:sii:i (sfi = 0x37520029c299)>#4#
  [00] : 0x375200000069 <undefined>
--------- s o u r c e   c o d e ---------
if ("d8" in this) {\x0a  d8.test.enableJSPI();\x0a  d8.test.installConditionalFeatures();\x0a}\x0avar wasm_code = new Uint8Array([0, 97, 115, 109, 1, 0, 0, 0, 1, 212, 129, 128, 128, 0, 22, 78, 1, 94, 120, 1, 78, 1, 94, 119, 1, 80, 0, 95, 4, 127, 0, 127, 0, 127, 0, 127, 0, 80, 1, 2, 95, 8, 127, 0, 127, 0, 127, 0...

-----------------------------------------
}

[3]: InternalFrame [pc: 0x7fc9d86d57dc]
[4]: EntryFrame [pc: 0x7fc9d86d551f]
-- ObjectCacheKey --

 #0# 0x3752002816c9: 0x3752002816c9 <JSGlobalProxy>
 #1# 0x37520004a8c5: 0x37520004a8c5 <FixedArray[1]>
                 0: 1
 #2# 0x37520029c0f1: 0x37520029c0f1 <JSFunction js-to-wasm:sii:i (sfi = 0x37520029c0c1)>
 #3# 0x37520029280d: 0x37520029280d <WebAssembly map = 0x375200298e19>
           compile: 0x37520028ee71 <JSFunction compile (sfi = 0x375200147759)>#5#
          validate: 0x37520028ee8d <JSFunction validate (sfi = 0x3752001477c1)>#6#
       instantiate: 0x37520028eea9 <JSFunction instantiate (sfi = 0x375200147829)>#7#
            Module: 0x37520028ef5d <JSFunction Module (sfi = 0x3752001479c9)>#8#
          Instance: 0x37520028f0ed <JSFunction Instance (sfi = 0x375200147a95)>#9#
             Table: 0x37520028f1d5 <JSFunction Table (sfi = 0x375200147bc9)>#10#
            Memory: 0x37520028f349 <JSFunction Memory (sfi = 0x375200147e35)>#11#
            Global: 0x37520028f459 <JSFunction Global (sfi = 0x375200147fd1)>#12#
               Tag: 0x37520028f585 <JSFunction Tag (sfi = 0x3752001481d5)>#13#
             JSTag: 0x37520029285d <Tag map = 0x37520028f5a5>#14#
         Exception: 0x37520028f639 <JSFunction Exception (sfi = 0x37520014829d)>#15#
      CompileError: 0x37520029288d <JSFunction CompileError (sfi = 0x37520027a5c9)>#16#
         LinkError: 0x3752002929bd <JSFunction LinkError (sfi = 0x37520027a5f9)>#17#
      RuntimeError: 0x375200292aed <JSFunction RuntimeError (sfi = 0x37520027a629)>#18#
          Function: 0x375200298721 <JSFunction Function (sfi = 0x3752002986f1)>#19#
         Suspender: 0x375200298a85 <JSFunction Suspender (sfi = 0x375200298a55)>#20#
        Suspending: 0x375200298c41 <JSFunction Suspending (sfi = 0x375200298c11)>#21#
         promising: 0x375200298dfd <JSFunction promising (sfi = 0x375200298dcd)>#22#
 #4# 0x37520029c2c9: 0x37520029c2c9 <JSFunction js-to-wasm:sii:i (sfi = 0x37520029c299)>
 #5# 0x37520028ee71: 0x37520028ee71 <JSFunction compile (sfi = 0x375200147759)>
 #6# 0x37520028ee8d: 0x37520028ee8d <JSFunction validate (sfi = 0x3752001477c1)>
 #7# 0x37520028eea9: 0x37520028eea9 <JSFunction instantiate (sfi = 0x375200147829)>
 #8# 0x37520028ef5d: 0x37520028ef5d <JSFunction Module (sfi = 0x3752001479c9)>
           imports: 0x37520028ef91 <JSFunction imports (sfi = 0x375200147891)>#23#
           exports: 0x37520028efad <JSFunction exports (sfi = 0x3752001478f9)>#24#
    customSections: 0x37520028efc9 <JSFunction customSections (sfi = 0x375200147961)>#25#
 #9# 0x37520028f0ed: 0x37520028f0ed <JSFunction Instance (sfi = 0x375200147a95)>
 #10# 0x37520028f1d5: 0x37520028f1d5 <JSFunction Table (sfi = 0x375200147bc9)>
 #11# 0x37520028f349: 0x37520028f349 <JSFunction Memory (sfi = 0x375200147e35)>
 #12# 0x37520028f459: 0x37520028f459 <JSFunction Global (sfi = 0x375200147fd1)>
 #13# 0x37520028f585: 0x37520028f585 <JSFunction Tag (sfi = 0x3752001481d5)>
 #14# 0x37520029285d: 0x37520029285d <Tag map = 0x37520028f5a5>
 #15# 0x37520028f639: 0x37520028f639 <JSFunction Exception (sfi = 0x37520014829d)>
 #16# 0x37520029288d: 0x37520029288d <JSFunction CompileError (sfi = 0x37520027a5c9)>
 #17# 0x3752002929bd: 0x3752002929bd <JSFunction LinkError (sfi = 0x37520027a5f9)>
 #18# 0x375200292aed: 0x375200292aed <JSFunction RuntimeError (sfi = 0x37520027a629)>
 #19# 0x375200298721: 0x375200298721 <JSFunction Function (sfi = 0x3752002986f1)>
 #20# 0x375200298a85: 0x375200298a85 <JSFunction Suspender (sfi = 0x375200298a55)>
 #21# 0x375200298c41: 0x375200298c41 <JSFunction Suspending (sfi = 0x375200298c11)>
 #22# 0x375200298dfd: 0x375200298dfd <JSFunction promising (sfi = 0x375200298dcd)>
 #23# 0x37520028ef91: 0x37520028ef91 <JSFunction imports (sfi = 0x375200147891)>
 #24# 0x37520028efad: 0x37520028efad <JSFunction exports (sfi = 0x3752001478f9)>
 #25# 0x37520028efc9: 0x37520028efc9 <JSFunction customSections (sfi = 0x375200147961)>
=====================
```

## Other

Please note to include the flags `--wasm-staging` for clusterfuzz classification.

VERSION Tested on v8 version: 12.6.0 - 12.8.0

REPRODUCTION CASE

  1. Download debug v8 from: gs://v8-asan/linux-debug/d8-linux-debug-v8-component-94592.zip
  2. Run: `d8 --wasm-staging poc.js`

FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION Type of crash: tab

CREDIT INFORMATION Reporter credit: Jerry


---

**#2 — cl...@appspot.gserviceaccount.com — Jun 25, 2024 09:42AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5912671508430848](<https://clusterfuzz.com/testcase?key=5912671508430848>).


---

**#3 — ri...@google.com — Jun 25, 2024 10:59AM**

Setting Security_Impact-None due to "--wasm-staging" flag


---

**#4 — ri...@google.com — Jun 25, 2024 11:05AM**

Thank you for the report. Assigning to the V8 shepherd for assignment after setting provisional severity and priority


---

**#5 — 24...@project.gserviceaccount.com — Jun 25, 2024 11:40AM**

Automatically applying components based on crash stacktrace and information from OWNERS files.  
  
If this is incorrect, please apply the hotlistid:4801165.


---

**#6 — 24...@project.gserviceaccount.com — Jun 25, 2024 11:41AM**

Detailed Report: [https://clusterfuzz.com/testcase?key=5912671508430848](<https://clusterfuzz.com/testcase?key=5912671508430848>)  
  
Fuzzer: None  
Job Type: linux_asan_d8_dbg  
Platform Id: linux  
  
Crash Type: Abrt  
Crash Address: 0x053900016b0b  
Crash State:  
Builtins_CEntry_Return1_ArgvOnStack_NoBuiltinExit  
Builtins_WasmPromising  
Builtins_InterpreterEntryTrampoline  
  
Sanitizer: address (ASAN)  
  
Regressed: [https://clusterfuzz.com/revisions?job=linux_asan_d8_dbg&range=94498:94499](<https://clusterfuzz.com/revisions?job=linux_asan_d8_dbg&range=94498:94499>)  
  
Reproducer Testcase: [https://clusterfuzz.com/download?testcase_id=5912671508430848](<https://clusterfuzz.com/download?testcase_id=5912671508430848>)  
  
To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.   
  
If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.  
  
If you have any feedback on reproducing test cases, let us know at [https://forms.gle/Yh3qCYFveHj6E5jz5](<https://forms.gle/Yh3qCYFveHj6E5jz5>) so we can improve.


---

**#7 — je...@gmail.com — Jun 25, 2024 11:55AM**

\--wasm-staging is not necessary; you can also trigger it, such as:

```
out/fuzzbuild/d8 poc.js --experimental-wasm-memory64 --experimental-wasm-imported-strings
```

but this vulnerability is actually unrelated to experimental-wasm-memory64 and experimental-wasm-imported-strings. It’s just that the fuzzed wasm code hasn't been further minimized. Therefore, I believe this should be classified as security-impact-head.


---

**#8 — je...@gmail.com — Jun 26, 2024 06:09AM**

please assign to @thibaudm，can you take a look？thanks


---

**#9 — 24...@project.gserviceaccount.com — Jun 26, 2024 04:28PM**

ClusterFuzz testcase 5912671508430848 is verified as fixed in [https://clusterfuzz.com/revisions?job=linux_asan_d8_dbg&range=94619:94620](<https://clusterfuzz.com/revisions?job=linux_asan_d8_dbg&range=94619:94620>)  
  
If this is incorrect, please add the hotlistid:5432646 and re-open the issue.


---

**#10 — je...@gmail.com — Jun 26, 2024 05:08PM**

```
d8-linux-debug-cache/d8-linux-debug-v8-component-94639/d8  --wasm-staging poc.js
[1]    3784006 trace trap  d8-linux-debug-cache/d8-linux-debug-v8-component-94639/d8 --wasm-staging 
```

I don't think this has been fixed, there seems to be an error in clusterfuzzer（range=94619:94620）


---

**#11 — am...@chromium.org — Jun 27, 2024 01:13AM**

It's not clear this would be exploitable, but it doesn't appear the commit that clusterfuzz has identified as a fix (which simply enabling the CSA pipeline for turboshaft) would resolve this; reopening this issue


---

**#12 — cf...@google.com — Jun 27, 2024 02:40AM**

@thibaudm, could you PTAL?


---

**#13 — ti...@chromium.org — Jun 27, 2024 05:46PM**

Adding `ClusterFuzz-Ignore` hotlist to all `ClusterFuzz-Wrong` issues per [crbug.com/40285975](<http://crbug.com/40285975>).


---

**#14 — je...@gmail.com — Jun 28, 2024 10:49AM**

hello, any update, thanks :)


---

**#15 — ap...@google.com — Jun 29, 2024 02:29AM**

Project: v8/v8  
Branch: main  
  
commit 96ce32ea56b320a738f82c6ab0bbc75234688aab  
Author: Thibaud Michaud <[thibaudm@chromium.org](<mailto:thibaudm@chromium.org>)>  
Date: Fri Jun 28 16:28:14 2024  
  
[wasm][jspi] Check JS-compatibility of promising export signatures  
  
R=[ahaas@chromium.org](<mailto:ahaas@chromium.org>)  
  
Fixed: 348793144  
Change-Id: I20cd088fc11b94edc23513938e9f5edbcb172bc5  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5666699](<https://chromium-review.googlesource.com/c/v8/v8/+/5666699>)  
Commit-Queue: Thibaud Michaud <[thibaudm@chromium.org](<mailto:thibaudm@chromium.org>)>  
Reviewed-by: Andreas Haas <[ahaas@chromium.org](<mailto:ahaas@chromium.org>)>  
Cr-Commit-Position: refs/heads/main@{#94719}  
  
M src/wasm/wasm-js.cc  
  
[https://chromium-review.googlesource.com/5666699](<https://chromium-review.googlesource.com/5666699>)


---

**#16 — sp...@google.com — Jul 4, 2024 06:55AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $8000.00 for this report.  
  
Rationale for this decision:  
$7,000 for report of memory corruption in a sandboxed process + $1,000 bisect bonus  
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#17 — am...@chromium.org — Jul 4, 2024 07:07AM**

Congratulations, Jerry -- thank you for your efforts and reporting this issue to us!


---

**#18 — pe...@google.com — Oct 6, 2024 12:39AM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.


---

**#19 — cl...@chromium.org — Jan 8, 2026 07:33PM**

Removing `Clusterfuzz-ignore` hotlist from some old bugs as it's preventing Clusterfuzz from filing similar bugs.
