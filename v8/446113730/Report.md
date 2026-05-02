# V8 Sandbox Bypass: WasmCPT handle UAF by import dispatch table growth

Issue URL: https://issues.chromium.org/issues/446113730
VRP-Reward: 20000
Date: Sep 19, 2025 10:57PM


### VULNERABILITY DETAILS

#### Summary

V8 sandbox bypass through WasmCPT handle UAF by growing `dispatch_table_for_imports` to transfer away its `WasmDispatchTableData`. Entries in the original table are still reachable through imported function calls but has wrapper refcnt holder transferred away. Triggering GC will free the wrappers' WasmCPT handles, leading to handle UAF and a subsequent type confusion between `WasmImportData` & `WasmTrustedInstanceData` after reclaiming the CPT entry with a native Wasm function.

#### Details

On `WasmTableObject` growth, its backing `WasmDispatchTable` may also grow. Below is the growth logic where 1. the original table entries are kept alive, while 2. its wrapper refcnt holding `WasmDispatchTableData` is transferred to the new dispatch table:

```
// static
DirectHandle<WasmDispatchTable> WasmDispatchTable::Grow(
    Isolate* isolate, DirectHandle<WasmDispatchTable> old_table,
    uint32_t new_length) {
  // [!] (omitted) compute new size, copy entries - original table entries still alive
  new_table->offheap_data()->wrappers_ =
      std::move(old_table->offheap_data()->wrappers_);         // [!] move away wrapper refcnt holder to new dispatch table
  // ...
}
```

Now, the original dispatch table entries do not hold their wrapper refcnt. After the new dispatch table gets freed, its wrapper references may also be freed leading to WasmCPT wrapper handle UAF. This can be used to target `dispatch_table_for_imports` and drop its `WasmDispatchTableData`, making its wrapper handles get freed. **This table does not have its instance wired up as a`uses` field since this is an internally managed dispatch table never meant to grow.**

Freed WasmCPT handles may be reclaimed by native Wasm functions. Calling the imported function will now result in calling the native Wasm function instead, with `WasmImportData` in place of `WasmTrustedInstanceData` which is obviously a big problem. An end-to-end exploit is surprisingly trivial as coincidentally `kMemory0StartOffset == kWasmImportDataSigOffset`, that is, the called Wasm function will now consider the `WasmImportData`'s `CanonicalSig*` as its `memory0_start`. This allows us to corrupt `CanonicalSig` (and of course, anything after that) simply by reading and writing to memory index 0 of the Wasm instance, which is convenient as this is shared between same-signature functions and is used for generic JS-Wasm wrappers. This leads to sandbox bypass as canonical signature type can be arbitrarily forged.

### VERSION

V8: Tested on `d8-sandbox-testing-linux-release-v8-component-102614`

### REPRODUCTION CASE

Attached as `poc.js` which exploits this issue to trigger a fully arbitary write outside of the sandbox, run with `./d8 --sandbox-testing`.

Note that the repro depends on `target_ofs` constant representing the number of TPT entries created from `dispatch_table_for_imports` allocation until the completion of Wasm module instantiation. Around L2610 is a simple script to find the correct `target_ofs` for a given d8 build. The constant is currently set to `0x5` which works for most recent builds.

### FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION

Type of crash: Sandbox violation

### CREDIT INFORMATION

Reporter credit: Seunghyun Lee (@0x10n) of CMU CSD / CyLab


---

**#2 — cl...@appspot.gserviceaccount.com — Sep 20, 2025 03:48AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=4986391540727808](<https://clusterfuzz.com/testcase?key=4986391540727808>).


---

**#3 — cl...@appspot.gserviceaccount.com — Sep 20, 2025 03:58AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5344565607202816](<https://clusterfuzz.com/testcase?key=5344565607202816>).


---

**#4 — dr...@chromium.org — Sep 20, 2025 06:21AM**

ClusterFuzz seems to have incorrectly marked this as a duplicate, but it's very clear about the control of the memory corruption:

```
+----------------------------------------Release Build Stacktrace----------------------------------------+
Sandbox testing mode is enabled. Only sandbox violations will be reported, all other crashes will be ignored.
Sandbox bounds: [0xa8c00000000,0xb8c00000000)
## V8 sandbox violation detected!
Received signal 11 SEGV_MAPERR 424242424242
==== C stack trace ===============================
```

It bisected the issue to [https://chromium-review.googlesource.com/c/v8/v8/+/6895241](<https://chromium-review.googlesource.com/c/v8/v8/+/6895241>), so assigning to the CL author.


---

**#5 — ch...@google.com — Sep 20, 2025 09:35PM**

Setting milestone because of s2 severity.


---

**#6 — ch...@google.com — Sep 20, 2025 09:35PM**

This is a serious security regression. If you are not able to fix this quickly, please revert the change that introduced it.

If this doesn't affect a release branch, or has not been properly classified for severity, please update the Security Impact hotlist or the Severity field, and remove the ReleaseBlock hotlist.


---

**#7 — ch...@google.com — Sep 20, 2025 09:37PM**

Setting Priority to P1 to match Severity s2. If this is incorrect, please reset the priority. The automation bot account won't make this change again.


---

**#8 — cl...@chromium.org — Sep 22, 2025 05:26PM**

Thanks for the report, Seunghyun!

Setting impact to None as for any sandbox escape.


---

**#9 — cl...@chromium.org — Sep 22, 2025 05:42PM**

FYI, the bisection in #4 is probably bogus. That CL changes some object sizes, we probably need to adjust the reproducer to bisect further back.

My guess for what introduced this would be [https://crrev.com/c/5783527](<https://crrev.com/c/5783527>).


---

**#10 — cl...@chromium.org — Sep 22, 2025 07:07PM**

Setting FoundIn to latest extended. This should be correct, but I didn't try to adapt the reproducer to reproduce there.


---

**#11 — cl...@chromium.org — Sep 22, 2025 07:12PM**

I would propose to fix this by clearing the old table on grow. This will lead to a crash when trying to use this table the next time. We would then load a `WasmCodePointer` of `-1`, which will crash when trying to use that for a call.


---

**#12 — cl...@chromium.org — Sep 22, 2025 07:39PM**

Interestingly, trying to call a code pointer of `-1` still leads to a reported sandbox violation, but only a read. The `-1` is shifted by four bits to the left, and that's used as an offset from the (global) wasm code pointer table. This is a segmented table with a 128MB reservation size (`kCodePointerTableReservationSize`). There is this comment:

```
 805 // The size of the virtual memory reservation for the code pointer table.
 806 // As with the other tables, a maximum table size in combination with shifted
 807 // indices allows omitting bounds checks.
 808 constexpr size_t kCodePointerTableReservationSize = 128 * MB;
```

It looks like we don't do such shifting for Wasm code pointers though...

Hence we get an OOB read when trying to call code pointer `-1`.

My current plan is:

  1. Clear the old table on grow.
  2. Open a separate issue about OOB access when trying to call the `WasmCodePointer` `-1`. We probably need to either store wasm code pointers shifted, or mask before using them.


---

**#13 — dx...@google.com — Sep 23, 2025 08:45PM**

Project: v8/v8  
Branch: main  
Author: Clemens Backes [clemensb@chromium.org](<mailto:clemensb@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6973457](<https://chromium-review.googlesource.com/6973457>)

[sandbox] Properly mask wasm code pointers to avoid OOB

* * *

Expand for full commit details

```
     
    Invalid wasm code pointers (like the `-1` sentinel used for invalid 
    pointers) would currently lead to OOB access of the 
    `WasmCodePointerTable`. 
    Thus mask the given target before using it to access into that table. 
     
    R=jkummerow@chromium.org 
    CC=sroettger@chromium.org 
     
    Bug: 446113730 
    Change-Id: I6df4d8fb37d8f7e8f4c99b00790fa8a0e1aa3d41 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6973457 
    Reviewed-by: Jakob Kummerow <jkummerow@chromium.org> 
    Commit-Queue: Clemens Backes <clemensb@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#102684}
```

* * *

Files:

  * M `src/codegen/arm64/macro-assembler-arm64.cc`
  * M `src/codegen/x64/macro-assembler-x64.cc`

* * *

Hash: [bf854e1d872f6815d3fe3547fe5a31294f29e04a](<https://chromiumdash.appspot.com/commit/bf854e1d872f6815d3fe3547fe5a31294f29e04a>)  
Date: Mon Sep 22 12:31:54 2025

* * *


---

**#14 — dx...@google.com — Sep 24, 2025 02:09AM**

Project: v8/v8  
Branch: main  
Author: Clemens Backes [clemensb@chromium.org](<mailto:clemensb@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6972023](<https://chromium-review.googlesource.com/6972023>)

[wasm] Clear old dispatch table on grow

* * *

Expand for full commit details

```
     
    We expect that all users are updated to the new table. Via in-sandbox 
    corruption, we might still see uses of the old table though. Clear all 
    entries to make the next call via the old table crash. 
     
    R=jkummerow@chromium.org 
     
    Bug: 446113730 
    Change-Id: I466cc5f80c99c37fb8f74232a84df24e34a78d96 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6972023 
    Commit-Queue: Clemens Backes <clemensb@chromium.org> 
    Reviewed-by: Jakob Kummerow <jkummerow@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#102705}
```

* * *

Files:

  * M `src/wasm/wasm-objects.cc`
  * A `test/mjsunit/sandbox/regress/regress-446113730.js`

* * *

Hash: [1d13848287a6e226862b1e1a90b6ae747c8a2ba2](<https://chromiumdash.appspot.com/commit/1d13848287a6e226862b1e1a90b6ae747c8a2ba2>)  
Date: Mon Sep 22 12:12:41 2025

* * *


---

**#15 — dx...@google.com — Sep 30, 2025 12:52AM**

Project: v8/v8  
Branch: main  
Author: Clemens Backes [clemensb@chromium.org](<mailto:clemensb@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6973393](<https://chromium-review.googlesource.com/6973393>)

[sandbox] Minor reformulation of printed output

* * *

Expand for full commit details

```
     
    I found the previous formulation hard to parse (we should at least have 
    printed "was a read" instead of "was read"). The new message is 
    hopefully more clear. 
     
    R=jkummerow@chromium.org 
     
    Bug: 446113730 
    Change-Id: Id7b7554637409ccd2500935bbac6fc6ea2c32a6a 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6973393 
    Reviewed-by: Jakob Kummerow <jkummerow@chromium.org> 
    Reviewed-by: Samuel Groß <saelo@chromium.org> 
    Commit-Queue: Samuel Groß <saelo@chromium.org> 
    Auto-Submit: Clemens Backes <clemensb@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#102831}
```

* * *

Files:

  * M `src/sandbox/testing.cc`

* * *

Hash: [b52621bc67598314591e8d0b614591433011ee60](<https://chromiumdash.appspot.com/commit/b52621bc67598314591e8d0b614591433011ee60>)  
Date: Tue Sep 23 18:00:58 2025

* * *


---

**#16 — dx...@google.com — Oct 2, 2025 06:06PM**

Project: v8/v8  
Branch: main  
Author: Clemens Backes [clemensb@chromium.org](<mailto:clemensb@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6988410](<https://chromium-review.googlesource.com/6988410>)

[codegen] Optimize code for calling via wasm code pointer

* * *

Expand for full commit details

```
     
    Masking of Wasm code pointers was implemented in 
    https://crrev.com/c/6973457. This CL optimizes the code sequence we use 
    by replacing the AND+SHL on x64 by SHR+SHL, and replacing AND+LSL by 
    UBFIZ on arm64. 
     
    R=jkummerow@chromium.org 
     
    Bug: 446113730, 446992084 
    Change-Id: I74e6ef1a5f9792f629858ee4027a62d373bcec20 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6988410 
    Reviewed-by: Jakob Kummerow <jkummerow@chromium.org> 
    Commit-Queue: Clemens Backes <clemensb@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#102889}
```

* * *

Files:

  * M `src/codegen/arm64/macro-assembler-arm64.cc`
  * M `src/codegen/x64/macro-assembler-x64.cc`

* * *

Hash: [93e92f067f8a2c0d933fff54f003b695f7d418e9](<https://chromiumdash.appspot.com/commit/93e92f067f8a2c0d933fff54f003b695f7d418e9>)  
Date: Fri Sep 26 13:49:49 2025

* * *


---

**#17 — sp...@google.com — Oct 28, 2025 01:55AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $20000.00 for this report.  
  
Rationale for this decision:  
v8 sandbox bypass with controllable write  
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#18 — ch...@google.com — Oct 28, 2025 09:43PM**

This V8 bug has been marked as either a release blocker or a vulnerability bug. V8 bugs affect all OSs supported by Chrome, so the OS field has been updated to reflect this. Please update the bug with the correct OS field if it only affects a subset of OSes.


---

**#19 — ch...@google.com — Jan 1, 2026 09:39PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
