# Unexpected instance type encountered

Issue URL: https://issues.chromium.org/issues/359949835
VRP-Reward: 8000
Date: Aug 15, 2024 10:35AM


# Steps to reproduce the problem

  1. ./d8 --expose-gc --omit-quit --allow-natives-syntax --fuzzing --jit-fuzzing poc.js
  2.   3. 

# Problem Description

Unexpected instance type encountered

# Summary

Unexpected instance type encountered

# Custom Questions

#### Type of crash:

tab

#### Crash state:

==== JS stack trace =========================================

```
0: ExitFrame [pc: 0x7f6b1b3545bd]
1: StubFrame [pc: 0x7f6b1b91f378]
2: isCompatible [0xfd200301a5d] [/home/uuu/poc.js:698] [bytecode=0x30000c14d1 offset=4](this=0x0fd2002816fd <JSGlobalProxy>#0#,0)
3: /* anonymous */ [0xfd200301aa1] [/home/uuu/poc.js:193] [bytecode=0x30000c3e7d offset=21](this=0x0fd2002816fd <JSGlobalProxy>#0#)
4: findIndex [0xfd20028d151](this=0x0fd200300059 <JSArray[5]>#1#,0x0fd200301aa1 <JSFunction (sfi = 0xfd2002a0621)>#2#)
5: randomArgumentForReplacing [0xfd20007df45] [/home/uuu/poc.js:705] [bytecode=0x30000c141d offset=80](this=0x0fd20007dc19 <Object map = 0xfd2002be489>#3#,0,0x0fd200300021 <Arguments map = 0xfd200291d91>#4#)
6: exploreObject [0xfd200079ee5] [/home/uuu/poc.js:816] [bytecode=0x30000c29bd offset=186](this=0x0fd2002816fd <JSGlobalProxy>#0#,0x0fd200300021 <Arguments map = 0xfd200291d91>#4#)
7: exploreValue [0xfd200079fe1] [/home/uuu/poc.js:957] [bytecode=0x30000c22dd offset=12](this=0x0fd2002816fd <JSGlobalProxy>#0#,0x0fd20029b01d <String[3]: #v59>,0x0fd200300021 <Arguments map = 0xfd200291d91>#4#)
8: explore [0xfd20007a005] [/home/uuu/poc.js:1001] [bytecode=0x30000c21f1 offset=104](this=0x0fd2002816fd <JSGlobalProxy>#0#,0x0fd20029b01d <String[3]: #v59>,0x0fd200300021 <Arguments map = 0xfd200291d91>#4#,0x0fd2002816fd <JSGlobalProxy>#0#,0x0fd200300059 <JSArray[5]>#1#,63201)
9: exploreWithErrorHandling [0xfd20007a029] [/home/uuu/poc.js:1019] [bytecode=0x30000c20f5 offset=21](this=0x0fd2002816fd <JSGlobalProxy>#0#,0x0fd20029b01d <String[3]: #v59>,0x0fd200300021 <Arguments map = 0xfd200291d91>#4#,0x0fd2002816fd <JSGlobalProxy>#0#,0x0fd200300059 <JSArray[5]>#1#,63201)
```

10: f23 [0xfd2002a09bd] [/home/uuu/poc.js:1041] [bytecode=0x30000c43c9 offset=66](this=0x0fd2002816fd <JSGlobalProxy>#0#,0x0fd2002c01f1 <JSFunction js-to-wasm:n: (sfi = 0xfd2002c01c1)>#5#) 11: StubFrame [pc: 0x7f6b1b323850] 12: Wasm [wasm://wasm/31a10782], function #2 ('main'), pc=0x2171d6af38d5 (+0x95), pos=60 (+5) 13: JsToWasmFrame [pc: 0x7f6b1b32090a] 14: 2 [0xfd2002c01f1] [wasm://wasm/31a10782:~1] [pc=0x7f6b1b87a4c3](this=0x0fd2002816fd <JSGlobalProxy>#0#,0x0fd2002c01b1 <Other heap object (WASM_FUNC_REF_TYPE)>#6#) 15: /* anonymous */ [0xfd2002a07d1] [/home/uuu/poc.js:1052] [bytecode=0x3000000111 offset=320](this=0x0fd2002816fd <JSGlobalProxy>#0#) 16: InternalFrame [pc: 0x7f6b1afa1edc] 17: EntryFrame [pc: 0x7f6b1afa1c1f]

# Additional Data

Category: Security   
Chrome Channel: Stable   
Regression: N/A


---

**#2 — wh...@gmail.com — Aug 15, 2024 10:38AM**

please replace this line in poc.js  
```  
d8.file.execute("/home/uuu/wasm-module-builder.js");  
```  
to your local location


---

**#3 — wh...@gmail.com — Aug 15, 2024 10:54AM**

Bisect   
  
[wasm] Process parameters in the js-to-wasm wrapper in order  
  
So far all primitive-type parameters were processed before all  
reference-type parameters in the js-to-wasm wrapper to avoid problems  
with the GC. However, this out-of-order processing was observable if the  
conversion of reference-type parameters caused an exception.  
  
With this CL all parameters get processed in order. Reference-type  
parameters get written back to the parameter slot on the stack after  
they got processed, and in a second iteration they just get copied from  
the parameter slot to their destination slot.  
  
Drive-by changes:  
* Add some quality-of-life features to the torque-wrapper.js test.  
* Allow the js-to-wasm wrapper on systems with 32-bit Smis. This is  
possible now as also reference-type parameters are GC-safe.  
  
R=[tebbi@chromium.org](<mailto:tebbi@chromium.org>)  
  
Bug: chromium:1462142  
Change-Id: I0ef4bc91a9054128a1c73fc83148ab51f16aaed1  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/4765290](<https://chromium-review.googlesource.com/c/v8/v8/+/4765290>)  
Reviewed-by: Tobias Tebbi <[tebbi@chromium.org](<mailto:tebbi@chromium.org>)>  
Commit-Queue: Andreas Haas <[ahaas@chromium.org](<mailto:ahaas@chromium.org>)>  
Cr-Commit-Position: refs/heads/main@{#89581}


---

**#4 — wh...@gmail.com — Aug 15, 2024 11:41AM**

Hi, here is new PoC, and also please replace this line   
```  
d8.file.execute("/home/uuu/wasm-module-builder.js");  
```


---

**#5 — cl...@appspot.gserviceaccount.com — Aug 15, 2024 08:02PM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5195494496075776](<https://clusterfuzz.com/testcase?key=5195494496075776>).


---

**#6 — ad...@google.com — Aug 15, 2024 08:02PM**

Over to the V8 sheriff with a provisional severity and FoundIn set; to be adjusted. I've uploaded this to ClusterFuzz with an inlined copy of wasm_module_builder.js, hopefully that will do the trick.


---

**#7 — 24...@project.gserviceaccount.com — Aug 15, 2024 08:18PM**

Testcase 5195494496075776 failed to reproduce the crash. Please inspect the program output at [https://clusterfuzz.com/testcase?key=5195494496075776](<https://clusterfuzz.com/testcase?key=5195494496075776>).


---

**#8 — cl...@appspot.gserviceaccount.com — Aug 16, 2024 12:41AM**

Detailed Report: [https://clusterfuzz.com/testcase?key=5114564527980544](<https://clusterfuzz.com/testcase?key=5114564527980544>)  
  
Fuzzer: None  
Job Type: linux_asan_d8_dbg  
Platform Id: linux  
  
Crash Type: Abrt  
Crash Address: 0x0539000001fb  
Crash State:  
v8::internal::__RT_impl_Runtime_Abort  
v8::internal::Runtime_Abort  
Builtins_CEntry_Return1_ArgvOnStack_NoBuiltinExit  
  
Sanitizer: address (ASAN)  
  
Crash Revision: [https://clusterfuzz.com/revisions?job=linux_asan_d8_dbg&revision=95654](<https://clusterfuzz.com/revisions?job=linux_asan_d8_dbg&revision=95654>)  
  
Reproducer Testcase: [https://clusterfuzz.com/download?testcase_id=5114564527980544](<https://clusterfuzz.com/download?testcase_id=5114564527980544>)  
  
To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.   
  
If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.  
  
If you have any feedback on reproducing test cases, let us know at [https://forms.gle/Yh3qCYFveHj6E5jz5](<https://forms.gle/Yh3qCYFveHj6E5jz5>) so we can improve.


---

**#9 — pe...@google.com — Aug 16, 2024 12:42AM**

Setting milestone because of s0/s1 severity.


---

**#10 — pe...@google.com — Aug 16, 2024 12:42AM**

Setting Priority to P1 to match Severity s1. If this is incorrect, please reset the priority. The automation bot account won't make this change again.


---

**#11 — sa...@google.com — Aug 16, 2024 01:07AM**

Thanks! Managed to reproduce this on CF. Let's wait for the bisect to finish (will probably take a while to minimize the sample first).


---

**#12 — 24...@project.gserviceaccount.com — Aug 16, 2024 04:19AM**

Automatically applying components based on crash stacktrace and information from OWNERS files.  
  
If this is incorrect, please apply the hotlistid:4801165.


---

**#13 — cl...@appspot.gserviceaccount.com — Aug 20, 2024 12:57AM**

Detailed Report: [https://clusterfuzz.com/testcase?key=5203685334253568](<https://clusterfuzz.com/testcase?key=5203685334253568>)  
  
Fuzzer: None  
Job Type: linux_asan_d8  
Platform Id: linux  
  
Crash Type: Abrt  
Crash Address: 0x0539000001fb  
Crash State:  
v8::internal::Runtime_Abort  
Builtins_CEntry_Return1_ArgvOnStack_NoBuiltinExit  
Builtins_TypeOfHandler  
  
Sanitizer: address (ASAN)  
  
Crash Revision: [https://clusterfuzz.com/revisions?job=linux_asan_d8&revision=95690](<https://clusterfuzz.com/revisions?job=linux_asan_d8&revision=95690>)  
  
Reproducer Testcase: [https://clusterfuzz.com/download?testcase_id=5203685334253568](<https://clusterfuzz.com/download?testcase_id=5203685334253568>)  
  
To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.   
  
If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.  
  
If you have any feedback on reproducing test cases, let us know at [https://forms.gle/Yh3qCYFveHj6E5jz5](<https://forms.gle/Yh3qCYFveHj6E5jz5>) so we can improve.


---

**#14 — sa...@google.com — Aug 20, 2024 05:07PM**

For some reason Clusterfuzz seems unable to bisect this, so I ran a bisect locally and it confirms [https://chromium-review.googlesource.com/c/v8/v8/+/4765290](<https://chromium-review.googlesource.com/c/v8/v8/+/4765290>) as (likely) culprit. Andreas, could you take a look and help find an appropriate owner for this? Thanks!


---

**#15 — ah...@chromium.org — Aug 21, 2024 05:21PM**

The problem here is how the generic js-to-wasm wrapper handles reference parameters. The js-to-wasm wrapper maps all parameters from the js domain (e.g. JSObject, Number, ...) to the wasm domain (e.g. i32, funcref, ...). For reference parameters that have already been mapped, however, it is unclear where to store them. They have to be stored in a slot that is known to the GC, so that the GC can update them.

So far the generic js-to-wasm wrapper simply stores them in the same stack slot where the incoming parameter was stored in. This stack slot is typically unused, because the parameter that was stored there already got transformed anyways. However, JavaScript's `Function.prototype.arguments` also allows access to this stack slot, which means that a WebAssembly-internal object can leak into JavaScript.


---

**#16 — ap...@google.com — Aug 22, 2024 02:27PM**

Project: v8/v8  
Branch: main  
  
commit aa2cbd9e4ed70238694e07f1c525941aa1e04429  
Author: Andreas Haas <[ahaas@chromium.org](<mailto:ahaas@chromium.org>)>  
Date: Wed Aug 21 16:55:04 2024  
  
[wasm][wrapper] Don't store converted references in arguments  
  
When the generic js-to-wasm wrapper converts tagged parameters, it has  
to store the converted parameters somewhere to protect them from  
potential GCs. The existing implementation stored the converted  
parameters in the incoming arguments array. However, the incoming  
arguments array is observable from JavaScript through  
Function.prototype.arguments, which means that writing converted  
parameters (i.e. WebAssembly references) into the arguments array means  
that WebAssembly objects leak into JavaScript.  
  
With this CL the converted parameters are not written into the arguments  
array anymore, but instead a FixedArray is allocated to store converted  
parameters.  
  
R=[thibaudm@chromium.org](<mailto:thibaudm@chromium.org>)  
  
Bug: 359949835  
Change-Id: Icfa4f86456a00132b23b239db1f9aa66a270f7fd  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5804141](<https://chromium-review.googlesource.com/c/v8/v8/+/5804141>)  
Reviewed-by: Thibaud Michaud <[thibaudm@chromium.org](<mailto:thibaudm@chromium.org>)>  
Commit-Queue: Andreas Haas <[ahaas@chromium.org](<mailto:ahaas@chromium.org>)>  
Cr-Commit-Position: refs/heads/main@{#95757}  
  
M src/builtins/js-to-wasm.tq  
A test/mjsunit/regress/wasm/regress-359949835.js  
  
[https://chromium-review.googlesource.com/5804141](<https://chromium-review.googlesource.com/5804141>)


---

**#17 — ah...@chromium.org — Aug 22, 2024 06:17PM**

Changing the severity to S2, because as far as we can tell you would need at last a second bug to exploit this issue.


---

**#18 — am...@chromium.org — Aug 23, 2024 08:07AM**

Thank you for landing this fix; in the future please allow the bot to update the merge requests by simply closing the bug as fixed. :) Medium severity bugs don't generally classify for stable backmerge.

It looks there was a v8->chromium autoroller failure at the first roll attempt to get this into Chromium ([https://crrev.com/c/5806346](<https://crrev.com/c/5806346>)). It has made it into a subsequent successful roll ([https://crrev.com/c/5806569](<https://crrev.com/c/5806569>)) but did not make it into Canary build as of yet. We'll need to revisit this fix on Monday for review once there's sufficient Canary bake time to make a merge decision.


---

**#19 — am...@chromium.org — Aug 29, 2024 01:51AM**

[https://chromium-review.googlesource.com/c/v8/v8/+/5804141](<https://chromium-review.googlesource.com/c/v8/v8/+/5804141>) approved for merge to M129; please merge this fix to 12.9 at your earliest convenience so this fix can be included in the next M129 beta update


---

**#20 — ap...@google.com — Sep 2, 2024 05:35PM**

Project: v8/v8  
Branch: refs/branch-heads/12.9  
  
commit 56ab30a6160e3b0296e2f42bfad37b02632d830f  
Author: Andreas Haas <[ahaas@chromium.org](<mailto:ahaas@chromium.org>)>  
Date: Wed Aug 21 16:55:04 2024  
  
M129 Merged: [wasm][wrapper] Don't store converted references in arguments  
  
When the generic js-to-wasm wrapper converts tagged parameters, it has  
to store the converted parameters somewhere to protect them from  
potential GCs. The existing implementation stored the converted  
parameters in the incoming arguments array. However, the incoming  
arguments array is observable from JavaScript through  
Function.prototype.arguments, which means that writing converted  
parameters (i.e. WebAssembly references) into the arguments array means  
that WebAssembly objects leak into JavaScript.  
  
With this CL the converted parameters are not written into the arguments  
array anymore, but instead a FixedArray is allocated to store converted  
parameters.  
  
R=[thibaudm@chromium.org](<mailto:thibaudm@chromium.org>)  
  
Bug: 359949835  
  
(cherry picked from commit aa2cbd9e4ed70238694e07f1c525941aa1e04429)  
  
Change-Id: I3493954ef20dc2c03b38d3e47aaf7b0bc61962c8  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5830783](<https://chromium-review.googlesource.com/c/v8/v8/+/5830783>)  
Reviewed-by: Thibaud Michaud <[thibaudm@chromium.org](<mailto:thibaudm@chromium.org>)>  
Commit-Queue: Andreas Haas <[ahaas@chromium.org](<mailto:ahaas@chromium.org>)>  
Cr-Commit-Position: refs/branch-heads/12.9@{#16}  
Cr-Branched-From: 64a21d7ad7fca1ddc73a9264132f703f35000b69-refs/heads/12.9.202@{#1}  
Cr-Branched-From: da4200b2cfe6eb1ad73c457ed27cf5b7ff32614f-refs/heads/main@{#95679}  
  
M src/builtins/js-to-wasm.tq  
A test/mjsunit/regress/wasm/regress-359949835.js  
  
[https://chromium-review.googlesource.com/5830783](<https://chromium-review.googlesource.com/5830783>)


---

**#21 — pe...@google.com — Sep 3, 2024 12:37AM**

This issue has been approved for a merge. Please merge the fix to any appropriate branches as soon as possible!

If all merges have been completed, please remove any remaining Merge-Approved labels from this issue.

Thanks for your time! To disable nags, add Disable-Nags (case sensitive) to the Chromium Labels custom field.


---

**#22 — sp...@google.com — Sep 13, 2024 08:56AM**

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

**#23 — am...@chromium.org — Sep 13, 2024 09:03AM**

Congratulations Ganjiang! Thank you for your efforts and reporting this issue to us.


---

**#24 — pe...@google.com — Sep 14, 2024 11:13AM**

LTS Milestone M126

This issue has been flagged as a merge candidate for Chrome OS' LTS channel. If selected, our merge team will handle any additional merges. To help us determine if this issue requires a merge to LTS, please answer this short questionnaire:

  1. Was this issue a regression for the milestone it was found in?
  2. Is this issue related to a change or feature merged after the latest LTS Milestone?


---

**#25 — ah...@chromium.org — Sep 16, 2024 02:28PM**

The issue was introduced in 118.


---

**#26 — pe...@google.com — Sep 20, 2024 12:27AM**

This issue requires additional review before it can be merged to the LTS channel. Please answer the following questions to help us evaluate this merge:

  1. Number of CLs needed for this fix and links to them.
  2. Level of complexity (High, Medium, Low - Explain)
  3. Has this been merged to a stable release? beta release?
  4. Overall Recommendation (Yes, No)


---

**#27 — qk...@google.com — Sep 20, 2024 09:54AM**

1\. [https://chromium-review.googlesource.com/c/v8/v8/+/5874951](<https://chromium-review.googlesource.com/c/v8/v8/+/5874951>)  
2\. Low, no conflicts  
3\. 129  
4\. Yes


---

**#28 — ap...@google.com — Oct 10, 2024 04:31PM**

Project: v8/v8  
Branch: refs/branch-heads/12.6  
Author: Andreas Haas <[ahaas@chromium.org](<mailto:ahaas@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/5874951](<https://chromium-review.googlesource.com/5874951>)

[M126-LTS][wasm][wrapper] Don't store converted references in arguments

* * *

Expand for full commit details

```
[M126-LTS][wasm][wrapper] Don't store converted references in arguments

When the generic js-to-wasm wrapper converts tagged parameters, it has
to store the converted parameters somewhere to protect them from
potential GCs. The existing implementation stored the converted
parameters in the incoming arguments array. However, the incoming
arguments array is observable from JavaScript through
Function.prototype.arguments, which means that writing converted
parameters (i.e. WebAssembly references) into the arguments array means
that WebAssembly objects leak into JavaScript.

With this CL the converted parameters are not written into the arguments
array anymore, but instead a FixedArray is allocated to store converted
parameters.

R=thibaudm@chromium.org

(cherry picked from commit aa2cbd9e4ed70238694e07f1c525941aa1e04429)

Bug: 359949835
Change-Id: Icfa4f86456a00132b23b239db1f9aa66a270f7fd
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/5804141
Reviewed-by: Thibaud Michaud <thibaudm@chromium.org>
Commit-Queue: Andreas Haas <ahaas@chromium.org>
Cr-Original-Commit-Position: refs/heads/main@{#95757}
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/5874951
Commit-Queue: Gyuyoung Kim (xWF) <qkim@google.com>
Reviewed-by: Andreas Haas <ahaas@chromium.org>
Cr-Commit-Position: refs/branch-heads/12.6@{#70}
Cr-Branched-From: 3c9fa12db3183a6f4ea53d2675adb66ea1194529-refs/heads/12.6.228@{#2}
Cr-Branched-From: 981bb15ba4dbf9e2381dfc94ec2c4af0b9c6a0b6-refs/heads/main@{#93835}
```

* * *

Files:

  * M `src/builtins/js-to-wasm.tq`
  * A `test/mjsunit/regress/wasm/regress-359949835.js`

* * *

Hash: 77a4fa1eb196387d3f010efe64039cbbb2d2f0c0  
Date: Wed Aug 21 16:55:04 2024

* * *


---

**#29 — pe...@google.com — Nov 30, 2024 12:42AM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
