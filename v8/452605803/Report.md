# V8 Sandbox Bypass: WasmCPT handle UAF by import dispatch table corruption (multiple variants of b/446113730)

Issue URL: https://issues.chromium.org/issues/452605803
VRP-Reward: 20000
Date: Oct 17, 2025 01:28AM


### VULNERABILITY DETAILS

#### Summary

V8 sandbox bypass through WasmCPT handle UAF by corrupting `dispatch_table_for_imports` (either growing or overwriting entries) to drop import wrapper handle at `WasmDispatchTableData`. Entries in the original table are still indirectly reachable through `WasmInternalFunction` (i.e. `WasmFuncRef`) as it holds the same wrapper call target, but has wrapper refcnt holder transferred away. This leads to handle UAF and a subsequent type confusion between `WasmImportData` & `WasmTrustedInstanceData` after reclaiming the CPT entry with a native Wasm function.

This is a simple variant of [b/446113730](<https://issues.chromium.org/issues/446113730>).

#### Details

Everything is the same with [b/446113730](<https://issues.chromium.org/issues/446113730>), but just replace the indirect call with a ref call.

```
diff --git wrapper-wasmcpt-uaf/poc.js wrapper-wasmcpt-uaf-v2/poc.js
index 704a077..762b603 100644
--- a/wrapper-wasmcpt-uaf/poc.js
+++ b/wrapper-wasmcpt-uaf-v2/poc.js
@@ -2583,13 +2583,16 @@ let builder = new WasmModuleBuilder();
 let $s = builder.addStruct([makeField(kWasmI64, true)]);
 let $sig_ls_ll = builder.addType(makeSig([kWasmI64, kWasmI64], [kWasmI64, wasmRefNullType($s)]));
 let $fn = builder.addImport('import', 'fn', $sig_ls_ll);
+builder.addDeclarativeElementSegment([$fn]);
 let $call_fn = builder.addFunction('call_fn', $sig_ls_ll).addBody([
   kExprLocalGet, 0,
   kExprLocalGet, 1,
-  kExprCallFunction, $fn,   // indirect call through dispatch_table_for_imports()
+  kExprRefFunc, $fn,
+  kExprCallRef, $sig_ls_ll,
 ]).exportFunc();
 let instance = builder.instantiate({import: {fn: ()=>[42n, null]}});
 let {call_fn} = instance.exports;
+call_fn(0n, 0n);  // instantiate ref.func
 
 // marker 1 & 2
 let dummy_table1 = new WebAssembly.Table({initial: 1, maximum: 1, element: 'anyfunc'});
@@ -2625,7 +2628,7 @@ let tt = new WebAssembly.Table({initial: 0, maximum: 0x10, element: 'anyfunc'});
 // grow the transplanted table. this also clears out index 0 in the new WasmDispatchTable(Data)
 // this drops std::shared_ptr<WasmImportWrapperHandle> refcnt to 0, freeing the entry in WasmCPT
 // the original WasmDispatchTable is still very well alive
-let target_ofs = 0x5;
+let target_ofs = 0x7;
 console.log(`[*] using target_ofs = 0x${target_ofs.toString(16)}`);
 let h_target = h1 - h_stride * target_ofs;
 caged_write(addrof(tt) + kWasmTableObjectTrustedDispatchTableOffset, h_target);
```

`WasmInternalFunction` holds a reference to the import wrapper WasmCPT without holding the import wrapper handle under the assumption that holding `implicit_arg` is sufficient. This is generally OK when we do not have memory corruption as import table cannot be modified, and holding `implicit_arg` (in this case, a `WasmImportData`) also holds a reference to the instance. However, with memory corruption none of this holds.

* * *

Note that WasmCPT UAF is just one very specific and easily controllable/exploitable effect of being able to modify the import dispatch table. Obviously there are more to this:

  * What happens if we grow this table and add a js import to a non-imported function index? e.g. [https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/wasm-objects.cc;drc=f8449afd2a2736981d7851eb8fc6264a5bfa7c17;l=579](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/wasm-objects.cc;drc=f8449afd2a2736981d7851eb8fc6264a5bfa7c17;l=579>)
  * What happens if we modify an entry in this import table? e.g. [https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/wasm-js.cc;drc=78e70427ce2bfd87826f4b0810913a48fc1a1e93;l=2240](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/wasm-js.cc;drc=78e70427ce2bfd87826f4b0810913a48fc1a1e93;l=2240>), where we can confuse `WasmTrustedInstanceData` <-> `WasmImportData` by overwriting a js import to a wasm import and running `WebAssembly.promising(exported_jsfn)` on it 
    * **This example here is very likely a full v8sbx bypass on its own** , but I won't bother writing one :)
  * ...and so on, with various implicit assumptions invalidated under a v8sbx attacker model

### VERSION

V8: Tested on `d8-sandbox-testing-linux-release-v8-component-103170`

### REPRODUCTION CASE

Attached as `poc.js` which exploits this issue to trigger a fully arbitary write outside of the sandbox, run with `./d8 --sandbox-testing`.

Note that the repro depends on `target_ofs` constant representing the number of TPT entries created from `dispatch_table_for_imports` allocation until the completion of Wasm module instantiation. Around L2610 is a simple script to find the correct `target_ofs` for a given d8 build. The constant is currently set to `0x7` which works for most recent builds.

### FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION

Type of crash: Sandbox violation

### CREDIT INFORMATION

Reporter credit: Seunghyun Lee (@0x10n) of CMU CSD / CyLab


---

**#2 — cl...@appspot.gserviceaccount.com — Oct 18, 2025 01:56AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5153397200060416](<https://clusterfuzz.com/testcase?key=5153397200060416>).


---

**#3 — 24...@project.gserviceaccount.com — Oct 18, 2025 02:16AM**

Testcase 5153397200060416 failed to reproduce the crash. Please inspect the program output at [https://clusterfuzz.com/testcase?key=5153397200060416](<https://clusterfuzz.com/testcase?key=5153397200060416>).


---

**#4 — cl...@appspot.gserviceaccount.com — Oct 18, 2025 04:20AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5617966028619776](<https://clusterfuzz.com/testcase?key=5617966028619776>).


---

**#5 — se...@gmail.com — Oct 18, 2025 05:32AM**

Re [comment#4](<https://issues.chromium.org/issues/452605803#comment4>): For the specific build / flags used in the CF repro attempt, `target_ofs = 0x6` works. `--fuzzing` flag seems to be affecting the number of TPT entries created.


---

**#6 — dr...@chromium.org — Oct 18, 2025 05:43AM**

[security triage] Thank you for the report. The first failure was my fault (the clusterfuzz sandbox testing targets still need --sandbox-testing, which seems a little redundant...), but the second time Clusterfuzz ran into:

```
+----------------------------------------Release Build Stacktrace----------------------------------------+
Sandbox testing mode is enabled. Only sandbox violations will be reported, all other crashes will be ignored.
Sandbox bounds: [0x7e9200000000,0x7f9200000000)
[*] ExposedTrustedObject handle: stride = 0x200, newly created by wasm = 0x6
[*] using target_ofs = 0x7
wasm-function[3]:0x93: TypeError: type incompatibility when transforming from/to JS
TypeError: type incompatibility when transforming from/to JS
    at write64 (wasm://wasm/2ca4de0e:wasm-function[3]:0x93)
    at /mnt/scratch0/clusterfuzz/bot/inputs/fuzzer-testcases/poc1.js:2718:1
```

Am I missing something?


---

**#7 — se...@gmail.com — Oct 18, 2025 05:47AM**

Re [comment#6](<https://issues.chromium.org/issues/452605803#comment6>): You can either:

  1. Drop the `--fuzzing` flag and re-run the PoC as is.
  2. Keep the `--fuzzing` flag but modify the PoC such that `target_ofs = 0x7` is replaced with `target_ofs = 0x6`.


---

**#8 — pe...@google.com — Oct 18, 2025 05:58AM**

Thank you for providing more feedback. Adding the requester to the CC list.


---

**#9 — dr...@chromium.org — Oct 18, 2025 06:42AM**

Thanks! Dropping flags from clusterfuzz is not easy, so let me try the second one.


---

**#10 — cl...@appspot.gserviceaccount.com — Oct 18, 2025 06:44AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=6038859670290432](<https://clusterfuzz.com/testcase?key=6038859670290432>).


---

**#11 — dr...@chromium.org — Oct 21, 2025 05:54AM**

Alright, giving up on Clusterfuzz. This reproduces exactly as claimed if I just run the prebuilts as reported. `d8-sandbox-testing-linux-release-v8-component-101731` did not reproduce the issue:

```
Sandbox testing mode is enabled. Only sandbox violations will be reported, all other crashes will be ignored.
[*] ExposedTrustedObject handle: stride = 0x200, newly created by wasm = 0x47                                                                                                                                                                                                  
[*] using target_ofs = 0x7                                                                                                             
Safely terminating process due to CSA check failure                                                                                                                                                                                                                            
The following harmless failure was encountered: Torque assert '(paramType & kValueTypeIsRefBit) != 0' failed [src/builtins/wasm-to-js.tq:158]
```

But `d8-sandbox-testing-linux-release-v8-component-102149` did, so I'm marking FoundIn=141 and triaging to V8 folks.


---

**#12 — cl...@chromium.org — Oct 21, 2025 08:55PM**

Adjusting labels for sandbox bypass.


---

**#13 — cl...@chromium.org — Oct 23, 2025 05:58PM**

Jakob, I am still busy with [https://crbug.com/452605804](<https://crbug.com/452605804>), can you take a first look?  
  
Also, it's related to wrapper ref counts, so maybe more your area anyway.


---

**#14 — jk...@chromium.org — Oct 24, 2025 12:39AM**

After some thinking and offline discussion, the plan is to introduce a separate `IndirectPointerTag` for dispatch tables used for imports, to make swapping attacks between those and the dispatch tables of regular tables impossible. Seunghyun, do you think that would be enough to fix this class of problems, or are we (once again...) overlooking some way to sidestep that protection?

A possible optional follow-up would then be to also split the class definitions. A hypothetical `WasmDispatchTableForImports` class wouldn't need any of the functionality related to growing/importing/exporting it, nor would it need the `canonical_sig_index` field for each entry, so we'd save some memory.


---

**#15 — se...@gmail.com — Oct 24, 2025 09:20AM**

My intuition is that if we prevent modification of the dispatch table for imports it would be OK, with "modification" meaning any ways to modify its entries / swap the dispatch tables / drop its reference prematurely. Introducing a separate tag seems like a valid solution, and I am not aware of any outstanding issues that would lead to a bypass.


---

**#16 — ch...@google.com — Oct 24, 2025 09:45PM**

This V8 bug has been marked as a release blocker. V8 bugs affect all OSs supported by Chrome, so the OS field has been updated to reflect this. Please update the bug with the correct OS field if it only affects a subset of OSes.


---

**#17 — jk...@chromium.org — Oct 24, 2025 09:59PM**

#15: Thanks for confirming. A fix to that effect is in flight; it turned out to be really easy, we didn't even need a new tag. Of course, if you notice ways to break/exploit this later, you know where to file a bug :-)


---

**#18 — jk...@chromium.org — Oct 24, 2025 11:16PM**

Update: it turned out to _not_ be really easy. I'm trying to see if there's a slightly less easy quick fix, or if it makes more sense to do a proper class split right away.


---

**#19 — dx...@google.com — Oct 30, 2025 11:54PM**

Project: v8/v8  
Branch: main  
Author: Jakob Kummerow [jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)  
Link: [https://chromium-review.googlesource.com/7079175](<https://chromium-review.googlesource.com/7079175>)

[sandbox][wasm] Un-expose dispatch_table_for_imports

* * *

Expand for full commit details

```
     
    The WasmTrustedInstanceData's dispatch_table_for_imports reuses 
    the WasmDispatchTable class, but contrary to regular tables doesn't 
    expect any modifications to it after creation. To guard against 
    swapping attacks after in-sandbox corruption, which could cause 
    such unexpected modifications, this patch un-exposes that particular 
    dispatch table, making it unreachable from any in-sandbox object. 
     
    Fixed: 452605803 
    Change-Id: Ic8124ee952d9b64c20eb77002daf712c734b97ac 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/7079175 
    Commit-Queue: Jakob Kummerow <jkummerow@chromium.org> 
    Reviewed-by: Clemens Backes <clemensb@chromium.org> 
    Reviewed-by: Omer Katz <omerkatz@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#103422}
```

* * *

Files:

  * M `src/diagnostics/objects-debug.cc`
  * M `src/diagnostics/objects-printer.cc`
  * M `src/heap/factory.cc`
  * M `src/heap/factory.h`
  * M `src/heap/setup-heap-internal.cc`
  * M `src/objects/object-list-macros.h`
  * M `src/objects/objects-body-descriptors-inl.h`
  * M `src/objects/objects.cc`
  * M `src/roots/roots.h`
  * M `src/roots/static-roots-intl-wasm.h`
  * M `src/roots/static-roots-nointl-wasm.h`
  * M `src/runtime/runtime-test-wasm.cc`
  * M `src/runtime/runtime-wasm.cc`
  * M `src/wasm/baseline/liftoff-compiler.cc`
  * M `src/wasm/turboshaft-graph-interface-inl.h`
  * M `src/wasm/wasm-objects-inl.h`
  * M `src/wasm/wasm-objects.cc`
  * M `src/wasm/wasm-objects.h`
  * M `src/wasm/wasm-objects.tq`
  * M `test/mjsunit/sandbox/regress/regress-446113730.js`
  * A `test/mjsunit/sandbox/regress/regress-452605803.js`

* * *

Hash: [7a322570d2973af0abf7f3122eb0674334d3af0a](<https://chromiumdash.appspot.com/commit/7a322570d2973af0abf7f3122eb0674334d3af0a>)  
Date: Thu Oct 30 13:06:17 2025

* * *


---

**#20 — cl...@chromium.org — Oct 31, 2025 07:09PM**

This demonstrates an issue with the `Fixed:` footer again: The [revert](<https://crrev.com/c/7102482>) didn't link to this issue, and on the [reland](<https://crrev.com/c/7105440>) it needed to be added back manually.


---

**#21 — cl...@chromium.org — Oct 31, 2025 07:13PM**

I bumped [https://crbug.com/40917201](<https://crbug.com/40917201>) to P1 for this. It's dangerous if security issues do not get an update when the fix is reverted.


---

**#22 — dx...@google.com — Oct 31, 2025 08:18PM**

Project: v8/v8  
Branch: main  
Author: Jakob Kummerow [jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)  
Link: [https://chromium-review.googlesource.com/7105440](<https://chromium-review.googlesource.com/7105440>)

Reland "[sandbox][wasm] Un-expose dispatch_table_for_imports"

* * *

Expand for full commit details

```
     
    This is a reland of commit 7a322570d2973af0abf7f3122eb0674334d3af0a 
    Revert reason was a flake; relanding without modifications. 
     
    Original change's description: 
    > The WasmTrustedInstanceData's dispatch_table_for_imports reuses 
    > the WasmDispatchTable class, but contrary to regular tables doesn't 
    > expect any modifications to it after creation. To guard against 
    > swapping attacks after in-sandbox corruption, which could cause 
    > such unexpected modifications, this patch un-exposes that particular 
    > dispatch table, making it unreachable from any in-sandbox object. 
     
    Fixed: 452605803 
    Change-Id: I86e324ba268139276e6b0e774d7a5f2106807d33 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/7105440 
    Reviewed-by: Clemens Backes <clemensb@chromium.org> 
    Commit-Queue: Jakob Kummerow <jkummerow@chromium.org> 
    Reviewed-by: Omer Katz <omerkatz@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#103436}
```

* * *

Files:

  * M `src/diagnostics/objects-debug.cc`
  * M `src/diagnostics/objects-printer.cc`
  * M `src/heap/factory.cc`
  * M `src/heap/factory.h`
  * M `src/heap/setup-heap-internal.cc`
  * M `src/objects/object-list-macros.h`
  * M `src/objects/objects-body-descriptors-inl.h`
  * M `src/objects/objects.cc`
  * M `src/roots/roots.h`
  * M `src/roots/static-roots-intl-wasm.h`
  * M `src/roots/static-roots-nointl-wasm.h`
  * M `src/runtime/runtime-test-wasm.cc`
  * M `src/runtime/runtime-wasm.cc`
  * M `src/wasm/baseline/liftoff-compiler.cc`
  * M `src/wasm/turboshaft-graph-interface-inl.h`
  * M `src/wasm/wasm-objects-inl.h`
  * M `src/wasm/wasm-objects.cc`
  * M `src/wasm/wasm-objects.h`
  * M `src/wasm/wasm-objects.tq`
  * M `test/mjsunit/sandbox/regress/regress-446113730.js`
  * A `test/mjsunit/sandbox/regress/regress-452605803.js`

* * *

Hash: [58bdae122c0f44e427ee2ec7dda636620e7aade2](<https://chromiumdash.appspot.com/commit/58bdae122c0f44e427ee2ec7dda636620e7aade2>)  
Date: Thu Oct 30 13:06:17 2025

* * *


---

**#23 — jk...@chromium.org — Nov 5, 2025 12:31AM**

I think it'd be nice to backmerge this to the branch we just cut. While the patch is large, most of that is autogenerated (static roots), and I think the rest is sufficiently low-risk to be fine to merge so early in a branch's Beta period.

Patch to merge: [https://chromium-review.googlesource.com/7105440](<https://chromium-review.googlesource.com/7105440>)

Canary coverage since 144.0.7506.0


---

**#24 — ch...@google.com — Nov 5, 2025 12:44AM**

Merge review required: M143 is already shipping to beta.

Please answer the following questions so that we can safely process your merge request:

  1. Why does your merge fit within the merge criteria for these milestones?

  * Chrome Browser: [https://chromiumdash.appspot.com/branches](<https://chromiumdash.appspot.com/branches>)
  * Chrome OS: [https://goto.google.com/cros-release-branch-merge-guidelines](<https://goto.google.com/cros-release-branch-merge-guidelines>)

  2. What changes specifically would you like to merge? Please link to Gerrit.
  3. Have the changes been released and tested on canary?
  4. Is this a new feature? If yes, is it behind a Finch flag and are experiments active in any release channels?
  5. [Chrome OS only]: Was the change reviewed and approved by the Eng Prod Representative? [https://goto.google.com/cros-engprodcomponents](<https://goto.google.com/cros-engprodcomponents>)
  6. If this merge addresses a major issue in the stable channel, does it require manual verification by the test team? If so, please describe required testing.

Please contact the milestone owner if you have questions. Owners: lmenezes (ChromeOS), srinivassista (Desktop US), danielyip (Desktop EMEA), harrysouders (Mobile US), eakpobaro (Mobile EMEA)


---

**#25 — jk...@chromium.org — Nov 5, 2025 12:51AM**

#24:

  1. Security fix (V8 sandbox escape)
  2. [https://chromium-review.googlesource.com/7105440](<https://chromium-review.googlesource.com/7105440>) (I know it looks big, but most of it is auto-generated, see [comment #23](<https://issues.chromium.org/issues/452605803#comment23>))
  3. Yes, since 144.0.7506.0
  4. No, old feature.
  5. N/A
  6. No manual testing required.


---

**#26 — ya...@google.com — Nov 11, 2025 03:58AM**

Please proceed with the merge


---

**#27 — jk...@chromium.org — Nov 11, 2025 04:14AM**

#26: Thanks, merge in flight: [https://chromium-review.googlesource.com/c/v8/v8/+/7138939](<https://chromium-review.googlesource.com/c/v8/v8/+/7138939>)


---

**#28 — dx...@google.com — Nov 11, 2025 08:35PM**

Project: v8/v8  
Branch: refs/branch-heads/14.3  
Author: Jakob Kummerow [jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)  
Link: [https://chromium-review.googlesource.com/7138939](<https://chromium-review.googlesource.com/7138939>)

Merged: Reland "[sandbox][wasm] Un-expose dispatch_table_for_imports"

* * *

Expand for full commit details

```
     
    This is a reland of commit 7a322570d2973af0abf7f3122eb0674334d3af0a 
    Revert reason was a flake; relanding without modifications. 
     
    Original change's description: 
    > The WasmTrustedInstanceData's dispatch_table_for_imports reuses 
    > the WasmDispatchTable class, but contrary to regular tables doesn't 
    > expect any modifications to it after creation. To guard against 
    > swapping attacks after in-sandbox corruption, which could cause 
    > such unexpected modifications, this patch un-exposes that particular 
    > dispatch table, making it unreachable from any in-sandbox object. 
     
    Fixed: 452605803 
    (cherry picked from commit 58bdae122c0f44e427ee2ec7dda636620e7aade2) 
     
    Change-Id: If91d3c1a25091f0172c64b85c15efea7e579fd51 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/7138939 
    Reviewed-by: Anton Bikineev <bikineev@chromium.org> 
    Commit-Queue: Jakob Kummerow <jkummerow@chromium.org> 
    Reviewed-by: Clemens Backes <clemensb@chromium.org> 
    Cr-Commit-Position: refs/branch-heads/14.3@{#20} 
    Cr-Branched-From: 13c7e3135187c1b0c7344e42529fbc27ba0e47f1-refs/heads/14.3.127@{#1} 
    Cr-Branched-From: 01af089bd89645143fc60f0da72267f95645afb3-refs/heads/main@{#103352}
```

* * *

Files:

  * M `src/diagnostics/objects-debug.cc`
  * M `src/diagnostics/objects-printer.cc`
  * M `src/heap/factory.cc`
  * M `src/heap/factory.h`
  * M `src/heap/setup-heap-internal.cc`
  * M `src/objects/object-list-macros.h`
  * M `src/objects/objects-body-descriptors-inl.h`
  * M `src/objects/objects.cc`
  * M `src/roots/roots.h`
  * M `src/roots/static-roots-intl-wasm.h`
  * M `src/roots/static-roots-nointl-wasm.h`
  * M `src/runtime/runtime-test-wasm.cc`
  * M `src/runtime/runtime-wasm.cc`
  * M `src/wasm/baseline/liftoff-compiler.cc`
  * M `src/wasm/turboshaft-graph-interface-inl.h`
  * M `src/wasm/wasm-objects-inl.h`
  * M `src/wasm/wasm-objects.cc`
  * M `src/wasm/wasm-objects.h`
  * M `src/wasm/wasm-objects.tq`
  * M `test/mjsunit/sandbox/regress/regress-446113730.js`
  * A `test/mjsunit/sandbox/regress/regress-452605803.js`

* * *

Hash: [dda15a7a586d2be32dfa54cb2c2e73aa516e3b7e](<https://chromiumdash.appspot.com/commit/dda15a7a586d2be32dfa54cb2c2e73aa516e3b7e>)  
Date: Thu Oct 30 13:06:17 2025

* * *


---

**#29 — sp...@google.com — Nov 14, 2025 03:55AM**

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

**#30 — ch...@google.com — Feb 6, 2026 09:49PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
