# V8 Sandbox Bypass: AAW/PC control via JSDispatchEntry UAF

Issue URL: https://issues.chromium.org/issues/443772809
VRP-Reward: 20000
Date: Sep 9, 2025 07:04AM


### VULNERABILITY DETAILS

#### Details

The issue seems to be that the GC can sometimes rely exclusively on in-sandbox references to the dispatch entry to decide the aliveness of said entry. Even if, for example, a function containing the dispatch handle were to be executing presently. Thus, one can change the underlying data in the entry by:

  1. Using in-sandbox memory corruption to remove all in-sandbox dispatch handle references to some target entry.
  2. Trigger GC to free the target dispatch entry.
  3. Build a new function that reuses the dispatch entry with different data this time.

This can be then be used to exploit any stale JITed code that relied on the dispatch entry having a specific parameter count, to imbalance the stack. Or, it might be used to resurrect old double fetch race bugs (eg. [b/430960844](<https://issues.chromium.org/issues/430960844>)?) without needing an actual double fetch this time.

For the PoC, the former was done. Maglev generates JITed code that call functions via the dispatch handle with the necessary amount of parameters per the dispatch entry data at the time of compilation. So, the dispatch entry was freed and reused to construct a function with a larger parameter count to imbalance the stack and gain RIP control.

* * *

As an aside:

To be honest, I expected needing to do something like the latter for the PoC (eg. race some tail call to update the dispatch entry) and was surprised to see Maglev actually work. I would've thought the `RelocInfo` in the `Code` object (both of which are trusted?) would be enough to mark the dispatch entry as still alive and prevent it from being sweeped:

  * [https://source.chromium.org/chromium/chromium/src/+/main:v8/src/codegen/reloc-info-inl.h;l=35;drc=4128411589187a396829a827f59a655bed876aa7](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/codegen/reloc-info-inl.h;l=35;drc=4128411589187a396829a827f59a655bed876aa7>)
  * [https://source.chromium.org/chromium/chromium/src/+/main:v8/src/heap/marking-visitor-inl.h;l=323;drc=4128411589187a396829a827f59a655bed876aa7](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/heap/marking-visitor-inl.h;l=323;drc=4128411589187a396829a827f59a655bed876aa7>)

Is there a bug somewhere, or am I just looking at the wrong thing.

### VERSION

V8 commit: b5aa4c8b718d75f9cf4d4afd635ffd217f0acb38

#### REPRODUCTION CASE

**Build args** :

```
is_debug=false
is_asan=true
v8_enable_sandbox=true
v8_enable_memory_corruption_api=true
dcheck_always_on=false
target_cpu="x64"
```

**Shell args** : `--allow-natives-syntax --expose-gc --sandbox-testing dispatch-entry-uaf.js`

**Sample output (using GDB to show RIP)** :

```
Sandbox testing mode is enabled. Only sandbox violations will be reported, all other crashes will be ignored.
Sandbox bounds: [0x7eb000000000,0x7fb000000000)

Thread 1 "d8" received signal SIGSEGV, Segmentation fault.
0x0000424242424242 in ?? ()
LEGEND: STACK | HEAP | CODE | DATA | WX | RODATA
─────────────────────────────────────[ REGISTERS / show-flags off / show-compact-regs off ]─────────────────────────────────────
 RAX  0x7eb000000011 ◂— 4
 RBX  0x7eb000000011 ◂— 4
 RCX  2
 RDX  0x424242424242
 RDI  0
 RSI  0
 R8   1
 R9   0
 R10  0x5fbab93800e4 ◂— movabs rax, 0x7eb00005f341 /* 0x7eb00005f341b848 */
 R11  0x7fffeb302ea9 ◂— 0x800004242424242 /* 'BBBBB' */
 R12  0x7fffeb302dc8 ◂— 0x424242424242 /* 'BBBBBB' */
 R13  0x7893742e1080 —▸ 0x5fbae474ea80 (Builtins_EphemeronKeyBarrierSaveFP) ◂— push rbp
 R14  0x7eb000000000 ◂— 0x40 /* '@' */
 R15  0x7813742e0309 ◂— 0x1000001710000017
 RBP  0x7fffeb302ee0 ◂— 0
 RSP  0x7fffeb3030d8 ◂— 0x424242424242 /* 'BBBBBB' */
 RIP  0x424242424242
──────────────────────────────────────────────[ DISASM / x86-64 / set emulate on ]──────────────────────────────────────────────
Invalid address 0x424242424242
```

### FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION

Type of crash: Sandbox violation

### CREDIT INFORMATION

Reporter credit: Krishna Ravishankar (@krsh732)


---

**#2 — kr...@gmail.com — Sep 9, 2025 09:34PM**

> I would've thought the RelocInfo in the Code object (both of which are trusted?) would be enough to mark the dispatch entry as still alive and prevent it from being sweeped:
> 
>   * [https://source.chromium.org/chromium/chromium/src/+/main:v8/src/codegen/reloc-info-inl.h;l=35;drc=4128411589187a396829a827f59a655bed876aa7](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/codegen/reloc-info-inl.h;l=35;drc=4128411589187a396829a827f59a655bed876aa7>)
>   * [https://source.chromium.org/chromium/chromium/src/+/main:v8/src/heap/marking-visitor-inl.h;l=323;drc=4128411589187a396829a827f59a655bed876aa7](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/heap/marking-visitor-inl.h;l=323;drc=4128411589187a396829a827f59a655bed876aa7>)
> 

It looks like the dispatch handle `RelocInfo` won't get visited by the marking visitor due to the [reloc mode mask used by the reloc info iterator](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/objects/objects-body-descriptors-inl.h;l=1323-1332;drc=845d2024791ea649a25c4074bf25263b1f648ff9>):

```
  static constexpr int kRelocModeMask =
      RelocInfo::ModeMask(RelocInfo::CODE_TARGET) |
      RelocInfo::ModeMask(RelocInfo::RELATIVE_CODE_TARGET) |
      RelocInfo::ModeMask(RelocInfo::FULL_EMBEDDED_OBJECT) |
      RelocInfo::ModeMask(RelocInfo::COMPRESSED_EMBEDDED_OBJECT) |
      RelocInfo::ModeMask(RelocInfo::EXTERNAL_REFERENCE) |
      RelocInfo::ModeMask(RelocInfo::INTERNAL_REFERENCE) |
      RelocInfo::ModeMask(RelocInfo::INTERNAL_REFERENCE_ENCODED) |
      RelocInfo::ModeMask(RelocInfo::OFF_HEAP_TARGET) |
      RelocInfo::ModeMask(RelocInfo::WASM_STUB_CALL);
```


---

**#3 — cl...@appspot.gserviceaccount.com — Sep 10, 2025 04:26AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5631136898154496](<https://clusterfuzz.com/testcase?key=5631136898154496>).


---

**#4 — kr...@gmail.com — Sep 10, 2025 04:44AM**

Looks like #3 failed because of the file name repeating twice: `--sandbox-testing dispatch-entry-uaf.js /mnt/scratch0/clusterfuzz/bot/inputs/fuzzer-testcases/dispatch-entry-uaf.js`. The latter of the two is probably the right one for ClusterFuzz. Sorry for the confusion!


---

**#5 — cl...@appspot.gserviceaccount.com — Sep 10, 2025 05:51AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5555844007526400](<https://clusterfuzz.com/testcase?key=5555844007526400>).


---

**#6 — kr...@gmail.com — Sep 10, 2025 06:12AM**

#5 failed because `v8_enable_memory_corruption_api = true` was missing from the gn args (interesting that it prints "Sandbox testing mode is enabled..." though). Perhaps a job type of `linux_d8_sandbox_testing` with `--allow-natives-syntax --expose-gc --sandbox-testing` would hopefully it get to reproduce on CF?


---

**#7 — cl...@appspot.gserviceaccount.com — Sep 10, 2025 10:49PM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=6584307715866624](<https://clusterfuzz.com/testcase?key=6584307715866624>).


---

**#8 — sk...@google.com — Sep 10, 2025 11:17PM**

It looks like clusterfuzz verified the problem. Assigning to the current V8 shepherd, note the severity and FoundIn are provisional!


---

**#9 — kr...@gmail.com — Sep 11, 2025 12:21AM**

FWIW, I wouldn't trust the regression range in #7, as I was able to reproduce in builds from April/May such as [d8-sandbox-testing-linux-release-v8-component-100000](<https://storage.cloud.google.com/v8-asan/linux-release/d8-sandbox-testing-linux-release-v8-component-100000.zip>) (randomly chosen). Though it did require a slight modification (hardcode `kDispatchHandleOffset = 0xc;`) as "JS_FUNCTION" seems to have not been present Sandbox API's instance type map back then.


---

**#10 — ml...@chromium.org — Sep 11, 2025 05:55PM**

From talking to Toon:

  * JSFunction's DH guards the usage in a non-sandbox world
  * With the sandbox model this link is broken in the POC

We already clear the dispatch handles when marking a code object for deopt since [1](<https://chromium-review.googlesource.com/c/v8/v8/+/6372240>).

What's missing for full weak treatment is:

  * Add the dispatch handle to the iteration mask
  * Make sure that the marker treats it as weak from the reloc info


---

**#11 — dx...@google.com — Sep 16, 2025 08:54PM**

Project: v8/v8  
Branch: main  
Author: Michael Lippautz [mlippautz@chromium.org](<mailto:mlippautz@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6939390](<https://chromium-review.googlesource.com/6939390>)

[heap] Fix processing of JSDispatch handle through RelocInfo

* * *

Expand for full commit details

```
     
    Before this patch any dispatch handles contained in RelocInfo were assumed to 
    be kept alive by their corresponding JSFunctions. This was fine as: 
    - RelocInfo treated the corresponding JSFunction weakly which meant 
      that the Code would be deoptimized if the JSFunction went away. 
    - The top most frame was always strongified all references in case it 
      could not be deoptimized. This meant that JSFunction and the dispatch 
      handle (and instrunction stream) were marked this way. 
     
    In a world with sandbox corruptions assuming a liveness witness does 
    not hold anymore as attackers can break the link from JSFunction to 
    dispatch handle (and thus instructon stream). 
     
    This patch implements proper weak handling in RelocInfo's dispatch handles: 
    - For regular processing the handles are treated weakly and 
      discovering a dead handle leads to deoptimization of the code objects. 
    - For the top most frame the dispatch handle and the instruction 
      stream are strongified. 
     
    Despite fixing the sandbox problem this also better follows the 
    principle of treating edges individually (weak or strong) without 
    considering other liveness witnesses which generally leads to more 
    robust code. 
     
    Fixed: 443772809 
    Change-Id: I4608cc830019c5267dfe49539867a7f0bbb0a144 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6939390 
    Reviewed-by: Leszek Swirski <leszeks@chromium.org> 
    Commit-Queue: Michael Lippautz <mlippautz@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#102520}
```

* * *

Files:

  * M `src/codegen/reloc-info-inl.h`
  * M `src/codegen/reloc-info.cc`
  * M `src/codegen/reloc-info.h`
  * M `src/deoptimizer/x64/deoptimizer-x64.cc`
  * M `src/diagnostics/disassembler.cc`
  * M `src/heap/mark-compact-inl.h`
  * M `src/heap/mark-compact.cc`
  * M `src/heap/mark-compact.h`
  * M `src/heap/marking-visitor-inl.h`
  * M `src/heap/weak-object-worklists.h`
  * M `src/objects/code-inl.h`
  * M `src/objects/code.h`
  * M `src/objects/objects-body-descriptors-inl.h`
  * M `src/profiler/heap-snapshot-generator.cc`
  * M `src/sandbox/js-dispatch-table-inl.h`
  * M `src/sandbox/js-dispatch-table.cc`
  * M `src/sandbox/js-dispatch-table.h`
  * A `test/mjsunit/sandbox/regress-443772809.js`

* * *

Hash: [51b324c6d189eeca06b84200d1acbdfba85f5c9b](<https://chromiumdash.appspot.com/commit/51b324c6d189eeca06b84200d1acbdfba85f5c9b>)  
Date: Mon Sep 15 09:45:03 2025

* * *


---

**#12 — sp...@google.com — Sep 30, 2025 06:56AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $20000.00 for this report.  
  
Rationale for this decision:  
v8 sandbox bypass  
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#13 — ch...@google.com — Dec 24, 2025 09:40PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.


---

**#14 — ch...@google.com — Dec 24, 2025 09:42PM**

This V8 bug has been marked as either a release blocker or a vulnerability bug. V8 bugs affect all OSs supported by Chrome, so the OS field has been updated to reflect this. Please update the bug with the correct OS field if it only affects a subset of OSes.
