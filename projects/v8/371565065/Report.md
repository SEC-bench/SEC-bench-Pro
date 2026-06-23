# Arbitrary WASM type confusion due to module confusion in wasm-to-js tier-up

Issue URL: https://issues.chromium.org/issues/371565065
VRP-Reward: 11000
Date: Oct 5, 2024 02:53PM


### VULNERABILITY DETAILS

#### Summary

Arbitrary WASM type confusion due to module confusion in wasm-to-js tier-up.

On [`Runtime_TierUpWasmToJSWrapper()`](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/runtime/runtime-wasm.cc;drc=0d15bbf1fb92f435e10c14f858d82d4cca851bf4;l=617>) triggered through function tables, the dispatch table's `WasmTrustedInstanceData` is used. However, the signature may be referring to another module's signature in case of an imported function that has been exported and re-imported as an element of a table. This results in arbitrary WASM type confusion as the wrapper compilation is using a signature with module-specfic `ValueType` from a different module.

#### Details

The following code in [`Runtime_TierUpWasmToJSWrapper()`](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/runtime/runtime-wasm.cc;drc=0d15bbf1fb92f435e10c14f858d82d4cca851bf4;l=617>) is triggered on wasm-to-js wrapper tier-up:

```
RUNTIME_FUNCTION(Runtime_TierUpWasmToJSWrapper) {
  HandleScope scope(isolate);
  DCHECK_EQ(1, args.length());
  DirectHandle<WasmImportData> import_data(Cast<WasmImportData>(args[0]),
                                           isolate);
  // ...
  const auto* sig = import_data->sig();                                           // [!] signature from module A (initial JS function importer, table exporter)
  // ...
  Handle<WasmTrustedInstanceData> trusted_data(import_data->instance_data(),
                                               isolate);
  if (IsTuple2(*origin)) {
    auto tuple = Cast<Tuple2>(origin);
    trusted_data =
        handle(Cast<WasmInstanceObject>(tuple->value1())->trusted_data(isolate),  // [!] module B (table importer)
               isolate);
    origin = direct_handle(tuple->value2(), isolate);
  }
  const wasm::WasmModule* module = trusted_data->module();                        // [!] module B
  // ...
  wasm::NativeModule* native_module = trusted_data->native_module();

  wasm::ResolvedWasmImport resolved({}, -1, callable, sig, canonical_sig_index,
                                    wasm::WellKnownImport::kUninstantiated);
  wasm::ImportCallKind kind = resolved.kind();
  callable = resolved.callable();  // Update to ultimate target.
  // ...
  wasm::WasmImportWrapperCache* cache = wasm::GetWasmImportWrapperCache();
  wasm::WasmCode* wasm_code =
      cache->MaybeGet(kind, canonical_sig_index, expected_arity, suspend);
  if (!wasm_code) {
    wasm_code = cache->CompileWasmImportCallWrapper(                              // [!] miscompilation
        isolate, native_module, kind, sig, canonical_sig_index, false,
        expected_arity, suspend);
  }
  // ...
}
```

Signature `sig` is from the following code in [`InstanceBuilder::InitializeImportedIndirectFunctionTable()`](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/module-instantiate.cc;drc=0d15bbf1fb92f435e10c14f858d82d4cca851bf4;l=2085>) in case of imported table:

```
    FunctionTargetAndImplicitArg entry(isolate_, target_instance_data,
                                       function_index);
    Handle<Object> implicit_arg = entry.implicit_arg();
    if (v8_flags.wasm_generic_wrapper && IsWasmImportData(*implicit_arg)) {
      auto orig_import_data = Cast<WasmImportData>(implicit_arg);
      Handle<WasmImportData> new_import_data =
          isolate_->factory()->NewWasmImportData(orig_import_data);               // [!] using signature from module A (table exporter)
      // TODO(42204563): Avoid crashing if the instance object is not available.
      CHECK(trusted_instance_data->has_instance_object());
      WasmImportData::SetCrossInstanceTableIndexAsCallOrigin(
          isolate_, new_import_data,
          direct_handle(trusted_instance_data->instance_object(), isolate_), i);
      implicit_arg = new_import_data;
    }
```

Through the following steps, we can cause a cross-module signature (and thus `ValueType`) confusion:

  1. Module A imports a JS function
  2. Module A creates a function table with imported function as an element
  3. Module A exports the function table
  4. Module B imports the function table from A 
     * `sig` is still from module A, but call origin is set to module B
  5. Module B triggers a tier-up 
     * `sig` is misused as a signature from module B, causing wrapper miscompilation

Exploitation with WASM type confusion primitives is trivial and has been presented multiple times. ([Pwn2Own Vancouver 2024](<https://www.zerodayinitiative.com/blog/2024/5/2/cve-2024-2887-a-pwn2own-winning-bug-in-google-chrome>), [TyphoonPWN 2024](<https://ssd-disclosure.com/ssd-advisory-google-chrome-rce/>), [v8CTF submission 8d4d57cb2258](<https://issuetracker.google.com/issues/347145602>), [b/360533914](<https://issues.chromium.org/issues/360533914>), [b/365802567](<https://issues.chromium.org/issues/365802567>), ...)

#### Bisect

Bug introduced by commit [2109613](<https://chromiumdash.appspot.com/commit/2109613ad4622028778a38fb418956fab8b478b6>) in M123 that attempted to fix a similar bug.

#### Suggested Fix

Apply the v8 sandbox bypass fix for [b/354408144](<https://issues.chromium.org/issues/354408144>) ([https://chromium-review.googlesource.com/c/v8/v8/+/589028](<https://chromium-review.googlesource.com/c/v8/v8/+/589028>)) to all affected version immediately, as this is not only a v8 sandbox bypass but a full-blown memory corruption bug. Alternatively, do a targeted fix by correctly referencing the module.

### VERSION

See bisect commit release info in Chromium Dash for more info: [https://chromiumdash.appspot.com/commit/2109613ad4622028778a38fb418956fab8b478b6](<https://chromiumdash.appspot.com/commit/2109613ad4622028778a38fb418956fab8b478b6>)

Chrome Version: 123.0.6301.0 ~ latest  
Operating System: All

### REPRODUCTION CASE

Attached as `poc.js` which exploits the type confusion to write 0x13371447 into tagged address 0x42424242, causing an access violation. Also attached is `exp.html` which pops shell on Windows x86-64 Chrome builds, tested on 129.0.6668.90 (latest stable) and 131.0.6757.0 (latest canary).

Note that this bug is capable to bypass v8 sandbox on its own without a separate bypass (see also [b/354408144](<https://issues.chromium.org/issues/354408144>)), but in `exp.html` I just opted to reuse the good old [b/350292240](<https://issues.chromium.org/issues/350292240>).

### FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION

Type of crash: Renderer  
Crash State: Crashes on JIT-compiled `caged_write()`.

### CREDIT INFORMATION

Reporter credit: Seunghyun Lee (@0x10n) of CMU CyLab


---

**#2 — se...@gmail.com — Oct 5, 2024 03:04PM**

See [b/371659495](<https://issues.chromium.org/issues/371659495>) for the corresponding v8CTF submission. Also, `exp.html` pops `calc` not shell :)


---

**#3 — se...@gmail.com — Oct 5, 2024 04:13PM**

### Updates

#### Vulnerabilty Details

Code snippets included above are based on commit 0d15bbf which has the aformentioned the v8 sandbox bypass fix included. While the corresponding code has the same meaning, the correct reference to the vulnerable code would be from commit 8973dee [`Runtime_TierUpWasmToJSWrapper()`](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/runtime/runtime-wasm.cc;l=637;drc=8973dee75aba5ade4f40eb47c4a14e2b3957f5ed>):

```
RUNTIME_FUNCTION(Runtime_TierUpWasmToJSWrapper) {
  HandleScope scope(isolate);
  DCHECK_EQ(1, args.length());
  DirectHandle<WasmImportData> import_data(Cast<WasmImportData>(args[0]),
                                           isolate);

  // ...
  std::unique_ptr<wasm::ValueType[]> reps;
  wasm::FunctionSig sig = wasm::SerializedSignatureHelper::DeserializeSignature(    // [!] signature from module A
      import_data->sig(), &reps);
  DirectHandle<Object> origin(import_data->call_origin(), isolate);
  // ...
}
```

The serialized signature comes from [`InstanceBuilder::ProcessImportedFunction()`](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/module-instantiate.cc;l=1872;drc=8973dee75aba5ade4f40eb47c4a14e2b3957f5ed>) -> [`ImportedFunctionEntry::SetGenericWasmToJs()`](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/wasm-objects.cc;l=1197;drc=8973dee75aba5ade4f40eb47c4a14e2b3957f5ed>):

```
// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/module-instantiate.cc;l=1872;drc=8973dee75aba5ade4f40eb47c4a14e2b3957f5ed
bool InstanceBuilder::ProcessImportedFunction(
    Handle<WasmTrustedInstanceData> trusted_instance_data, int import_index,
    int func_index, Handle<Object> value, WellKnownImport preknown_import) {
  // ...
  auto js_receiver = Cast<JSReceiver>(value);
  const FunctionSig* expected_sig = module_->functions[func_index].sig;             // [!] signature from module A
  // ...
  switch (kind) {
    // ...
    default: {
      // The imported function is a callable.
      if (UseGenericWasmToJSWrapper(kind, expected_sig, resolved.suspend())) {
        DCHECK(kind == ImportCallKind::kJSFunctionArityMatch ||
               kind == ImportCallKind::kJSFunctionArityMismatch);
        imported_entry.SetGenericWasmToJs(isolate_, js_receiver,
                                          resolved.suspend(), expected_sig);
        break;
      }
      // ...
    }
  // ...
}

// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/wasm-objects.cc;l=1197;drc=8973dee75aba5ade4f40eb47c4a14e2b3957f5ed
void ImportedFunctionEntry::SetGenericWasmToJs(
    Isolate* isolate, DirectHandle<JSReceiver> callable, wasm::Suspend suspend,
    const wasm::FunctionSig* sig) {
  // ...
  DirectHandle<WasmImportData> import_data =
      isolate->factory()->NewWasmImportData(
          callable, suspend, instance_data_,
          wasm::SerializedSignatureHelper::SerializeSignature(isolate, sig));       // [!] signature from module A, serialized as is w/ module-specific ValueType
  // ...
}
```

#### Bisect

Bisect is incorrect, bug is introduced in M117 at [153e577](<https://chromiumdash.appspot.com/commit/153e5773a8e655d664a73488f67fa77dc5bf0f8c>) which introduces wasm-to-js tier-up, but is exposed (by default) in M123 at [13b4b6d](<https://chromiumdash.appspot.com/commit/13b4b6d80f2c8eac43b85e972071e113a8369b86>) which enables generic wasm-to-js wrapper by default.

Thus, the bug affects (again, by default) Chrome version ranges [123.0.6283.0, 131.0.6758.0). See below "Note to triagers" section for more information.

#### Suggested Fix

Link to the v8 sandbox bypass fix was missing a trailing 8 - the link should be [https://crrev.com/c/5890288](<https://crrev.com/c/5890288>).

#### Reproduction Case

This bug may be insufficient to bypass v8 sandbox on its own due to how wasm-gc index `ValueType`s are being confused, but not between arbitrary `ValueType`s. This still grants all in-sandbox corruption primitives.

#### Note to triagers

**`poc.js` will not be reproducible on latest d8, specifically after the v8 sandbox bypass fix on [0d15bbf](<https://chromium-review.googlesource.com/c/v8/v8/+/5890288>)** as the bypass fix is a general improvement that also unwittingly fixes this bug. However, as this bug was unknown **the committed fix is only considered as a v8 sandbox bypass fix and not a security vulnerability capable of memory corruption, thus is only applied on v8 head and is not planned for any backmerges** (see also [b/354408144](<https://issues.chromium.org/issues/354408144>)). This bug should be considered as a separate memory corruption vulnerability on the renderer capable of easily achieving RCE on latest shipped Chrome versions (and potentially a few more release cycles - at least the full M130 + LTS cycle - without this report). My assumption is that as the bypass fix spans over multiple commits with line diffs reaching over 1k, it would be preferred to do a targeted fix.

To test the repro, either run `poc.js` on d8 before commit 0d15bbf or run the full RCE repro `exp.html` on any latest official Chrome builds before 131.0.6758.0 (running it on Linux will yield a null address read crash within Windows x64-specific shellcode).


---

**#4 — cl...@appspot.gserviceaccount.com — Oct 7, 2024 07:51PM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5120220326723584](<https://clusterfuzz.com/testcase?key=5120220326723584>).


---

**#5 — cl...@appspot.gserviceaccount.com — Oct 7, 2024 07:53PM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5865254428803072](<https://clusterfuzz.com/testcase?key=5865254428803072>).


---

**#6 — cl...@appspot.gserviceaccount.com — Oct 7, 2024 07:55PM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=4938079353634816](<https://clusterfuzz.com/testcase?key=4938079353634816>).


---

**#7 — ad...@google.com — Oct 7, 2024 07:56PM**

Thanks for the report - we'll start by seeing how far ClusterFuzz can get. I've uploaded the POC twice - once to HEAD V8 (which we expect to reproduce nothing) and once to a pre-0d15bbf version of V8 (if ClusterFuzz respects my wishes).


---

**#8 — ad...@google.com — Oct 7, 2024 07:57PM**

V8 sheriff: hello. Setting provisional FoundIn and severity, please adjust.


---

**#9 — cf...@google.com — Oct 7, 2024 08:00PM**

ahaas@, could you PTAL?


---

**#10 — 24...@project.gserviceaccount.com — Oct 7, 2024 10:17PM**

Automatically applying components based on crash stacktrace and information from OWNERS files.  
  
If this is incorrect, please apply the hotlistid:4801165.


---

**#11 — 24...@project.gserviceaccount.com — Oct 7, 2024 10:17PM**

Detailed Report: [https://clusterfuzz.com/testcase?key=4938079353634816](<https://clusterfuzz.com/testcase?key=4938079353634816>)  
  
Fuzzer: None  
Job Type: linux_asan_d8_dbg  
Platform Id: linux  
  
Crash Type: UNKNOWN WRITE  
Crash Address: 0x7a8d00000007  
Crash State:  
Builtins_JSToWasmWrapperAsm  
Builtins_JSToWasmWrapper  
Builtins_InterpreterEntryTrampoline  
  
Sanitizer: address (ASAN)  
  
Recommended Security Severity: High  
  
Regressed: [https://clusterfuzz.com/revisions?job=linux_asan_d8_dbg&range=89971:89972](<https://clusterfuzz.com/revisions?job=linux_asan_d8_dbg&range=89971:89972>)  
  
Reproducer Testcase: [https://clusterfuzz.com/download?testcase_id=4938079353634816](<https://clusterfuzz.com/download?testcase_id=4938079353634816>)  
  
To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.   
  
If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.  
  
If you have any feedback on reproducing test cases, let us know at [https://forms.gle/Yh3qCYFveHj6E5jz5](<https://forms.gle/Yh3qCYFveHj6E5jz5>) so we can improve.  
  
  
A recommended severity was added to this bug. Please change the severity if it is inaccurate.


---

**#12 — pe...@google.com — Oct 8, 2024 12:38AM**

Setting milestone because of s0/s1 severity.


---

**#13 — pe...@google.com — Oct 8, 2024 12:38AM**

Setting Priority to P1 to match Severity s1. If this is incorrect, please reset the priority. The automation bot account won't make this change again.


---

**#14 — cl...@chromium.org — Oct 8, 2024 07:43PM**

Thanks for this well-written report!

I think [https://crrev.com/c/5890288](<https://crrev.com/c/5890288>) fully fixes this, but unfortunately we cannot merge this to earlier versions. I also don't feel super comfortable with a fix that we _only_ apply to shipping channels, so I am unsure what to do about this :/


---

**#15 — se...@gmail.com — Oct 9, 2024 12:51AM**

Yeah, this seems like an unusual case. The bug is still present on versions up to M130 though, and the LTS channel just switched to M126 a few days ago so the bug will last at least 6 months more if not patched which I consider an unacceptable risk to take.

I was wondering if we could just get away with passing on `import_data->instance_data()->native_module()` to `WasmImportWrapperCache::CompileWasmImportCallWrapper()` instead of referencing it from the overwritten `trusted_data`? At least the below patch applied on 13.0 does not fail any `x64.optdebug.check` tests and also breaks the exploit, although there might be other implications that I'm not aware of:

```
diff --git a/src/runtime/runtime-wasm.cc b/src/runtime/runtime-wasm.cc
index 842bd57b816..1b9ab9ca36c 100644
--- a/src/runtime/runtime-wasm.cc
+++ b/src/runtime/runtime-wasm.cc
@@ -723,7 +723,7 @@ RUNTIME_FUNCTION(Runtime_TierUpWasmToJSWrapper) {
   wasm::Suspend suspend = static_cast<wasm::Suspend>(import_data->suspend());
   wasm::WasmCodeRefScope code_ref_scope;
 
-  wasm::NativeModule* native_module = trusted_data->native_module();
+  wasm::NativeModule* native_module = import_data->instance_data()->native_module();
 
   wasm::ResolvedWasmImport resolved({}, -1, callable, &sig, canonical_sig_index,
                                     wasm::WellKnownImport::kUninstantiated);
```


---

**#16 — ap...@google.com — Oct 10, 2024 09:32PM**

Project: v8/v8  
Branch: main  
Author: Andreas Haas <[ahaas@chromium.org](<mailto:ahaas@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/5921410](<https://chromium-review.googlesource.com/5921410>)

[wasm] Don't tier up wrapper if signature depends on other instance

* * *

Expand for full commit details

```
[wasm] Don't tier up wrapper if signature depends on other instance

The wasm-to-js wrapper tierup currently does not handle signatures with
indexed types correctly if the WebAssembly instance from which the
JavaScript function is called is different than the WebAssembly instance
that imported the JavaScript function initially. With this CL the
wrapper tierup gets disabled in that case until tierup gets fixed
eventually.

R=clemensb@chromium.org

Bug: 371565065
Change-Id: I75ddeced30defea332cbeb1636d0f249e8ef3083
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/5921410
Reviewed-by: Clemens Backes <clemensb@chromium.org>
Commit-Queue: Andreas Haas <ahaas@chromium.org>
Cr-Commit-Position: refs/heads/main@{#96513}
```

* * *

Files:

  * M `src/runtime/runtime-wasm.cc`
  * M `test/mjsunit/mjsunit.status`
  * A `test/mjsunit/regress/wasm/regress-371565065.js`

* * *

Hash: 5fcbf3954eb9f7f8221f068b5324e5b6f04b5839  
Date: Thu Oct 10 13:56:42 2024

* * *


---

**#17 — ah...@chromium.org — Oct 10, 2024 09:56PM**

[https://chromium-review.googlesource.com/5921410](<https://chromium-review.googlesource.com/5921410>) is a fix that can be merged to older versions. The original fix in [https://chromium-review.googlesource.com/c/v8/v8/+/5890288](<https://chromium-review.googlesource.com/c/v8/v8/+/5890288>) is actually better, but cannot be merged back. [https://chromium-review.googlesource.com/5921410](<https://chromium-review.googlesource.com/5921410>) lands now to get Canary coverage so that we can merge it back. However, after the merges we plan to revert it again.


---

**#18 — am...@chromium.org — Oct 11, 2024 01:00AM**

Thanks for the context. M130 Stable RC for release next week was already cut earlier this week. There are no further planned releases of M128 Extended or M129 Stable. Since the fix that can be merged back just landed today, merge review will need to be revisited on Monday and this fix will likely be shipped in the first respin of M130 Stable


---

**#19 — pe...@google.com — Oct 11, 2024 09:42PM**

Merge review required: M130 has already been cut for stable release.

Please answer the following questions so that we can safely process your merge request:

  1. Why does your merge fit within the merge criteria for these milestones?

  * Chrome Browser: [https://chromiumdash.appspot.com/branches](<https://chromiumdash.appspot.com/branches>)
  * Chrome OS: [https://goto.google.com/cros-release-branch-merge-guidelines](<https://goto.google.com/cros-release-branch-merge-guidelines>)

  2. What changes specifically would you like to merge? Please link to Gerrit.
  3. Have the changes been released and tested on canary?
  4. Is this a new feature? If yes, is it behind a Finch flag and are experiments active in any release channels?
  5. [Chrome OS only]: Was the change reviewed and approved by the Eng Prod Representative? [https://goto.google.com/cros-engprodcomponents](<https://goto.google.com/cros-engprodcomponents>)
  6. If this merge addresses a major issue in the stable channel, does it require manual verification by the test team? If so, please describe required testing.

Please contact the milestone owner if you have questions. Owners: eakpobaro (Android), eakpobaro (iOS), gmpritchard (ChromeOS), danielyip (Desktop)


---

**#20 — ah...@chromium.org — Oct 11, 2024 10:31PM**

1. The CL fixes an important security issue.
  2. [https://chromium-review.googlesource.com/c/v8/v8/+/5921410](<https://chromium-review.googlesource.com/c/v8/v8/+/5921410>)
  3. Not yet, see [https://chromiumdash.appspot.com/commit/5fcbf3954eb9f7f8221f068b5324e5b6f04b5839](<https://chromiumdash.appspot.com/commit/5fcbf3954eb9f7f8221f068b5324e5b6f04b5839>)
  4. No
  5. No
  6. No


---

**#21 — am...@chromium.org — Oct 12, 2024 03:23AM**

Since the fix is not yet on canary, it will be reviewed for merge Monday / early next week for inclusion in the first update of M130 Stable.


---

**#22 — am...@chromium.org — Oct 16, 2024 07:02PM**

[https://crrev.com/c/5921410](<https://crrev.com/c/5921410>) approved for merge to M130, please merge this fix to 13.0 by EOD tomorrow / Thursday 17 October so this fix can be included in the M130 Stable update next week


---

**#23 — ap...@google.com — Oct 16, 2024 11:56PM**

Project: v8/v8  
Branch: refs/branch-heads/13.0  
Author: Andreas Haas <[ahaas@chromium.org](<mailto:ahaas@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/5937800](<https://chromium-review.googlesource.com/5937800>)

[13.0][wasm] Don't tier up wrapper if signature depends on other instance

* * *

Expand for full commit details

```
[13.0][wasm] Don't tier up wrapper if signature depends on other instance

The wasm-to-js wrapper tierup currently does not handle signatures with
indexed types correctly if the WebAssembly instance from which the
JavaScript function is called is different than the WebAssembly instance
that imported the JavaScript function initially. With this CL the
wrapper tierup gets disabled in that case until tierup gets fixed
eventually.

R=clemensb@chromium.org

Bug: 371565065

(cherry picked from commit 5fcbf3954eb9f7f8221f068b5324e5b6f04b5839)

Change-Id: I43d8eff2d4ce4e3ec775b7346938ea26109f7045
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/5937800
Commit-Queue: Andreas Haas <ahaas@chromium.org>
Reviewed-by: Clemens Backes <clemensb@chromium.org>
Cr-Commit-Position: refs/branch-heads/13.0@{#33}
Cr-Branched-From: 4be854bd71ea878a25b236a27afcecffa2e29360-refs/heads/13.0.245@{#1}
Cr-Branched-From: 1f5183f7ad6cca21029fd60653d075730c644432-refs/heads/main@{#96103}
```

* * *

Files:

  * M `src/runtime/runtime-wasm.cc`
  * M `test/mjsunit/mjsunit.status`

* * *

Hash: 153d4e84e5d1f6c9a853808e933fd7ef18218f74  
Date: Thu Oct 10 13:56:42 2024

* * *


---

**#24 — pe...@google.com — Oct 16, 2024 11:59PM**

LTS Milestone M126

This issue has been flagged as a merge candidate for Chrome OS' LTS channel. If selected, our merge team will handle any additional merges. To help us determine if this issue requires a merge to LTS, please answer this short questionnaire:

  1. Was this issue a regression for the milestone it was found in?
  2. Is this issue related to a change or feature merged after the latest LTS Milestone?


---

**#25 — sp...@google.com — Oct 23, 2024 05:55AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $11000.00 for this report.  
  
Rationale for this decision:  
$10,000 for high quality report of memory corruption in a sandboxed process (in release channels prior to M131, RCE in 131 and new builds already previously known and resolved) + $1,000 bisect bonus  
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#26 — am...@chromium.org — Oct 23, 2024 06:12AM**

Congratulations on yet another one this week, Seunghyun! Thank you for your efforts and so clearly reporting this issue to us -- great work!


---

**#27 — se...@gmail.com — Oct 23, 2024 06:18AM**

Thanks! I have questions about the VRP decision though:

  * This report has demonstrated a V8 bug in Stable and older channel, including a PoC of an arbitrary code execution exploit in the renderer. I believe such cases are usually awarded $20,000?
  * It is true that the bug was already fixed in M131 and above (i.e. "previously resolved"), but was this bug a "previously known" issue? As far as my issue visibility goes, there seems to have been no indications of prior knowledge on the bug nor an attempt to fix this specific bug on any versions up to M130. Or is the "previously known" condition not a deciding factor for the final VRP decision?


---

**#28 — am...@chromium.org — Oct 23, 2024 06:37AM**

> This report has demonstrated a V8 bug in Stable and older channel, including a PoC of an arbitrary code execution exploit in the renderer. I believe such cases are usually awarded $20,000?

Yes, it is generally for when it is a wholly novel issue not resolved in any active release channels of Chrome. That's not really the case here. :)

The reason for that reward is to specifically incentivize the reporting of older bugs that we don't know about and wouldn't have any resolution for.

> It is true that the bug was already fixed in M131 and above (i.e. "previously resolved"), but was this bug a "previously known" issue?

Apologies for not being more clear here, it's more the case that it was already previously resolved. We can't really extend the full RCE reward or Stable bonus reward for an issue that is already resolved in some active release channels.


---

**#29 — se...@gmail.com — Oct 23, 2024 06:41AM**

Alright, thanks for the clarification!


---

**#30 — se...@gmail.com — Oct 31, 2024 12:49AM**

Hi, seems like I haven't added this for my recent reports so adding it in bulk - I'd like to donate the bounty through Benevity. Thanks!


---

**#31 — am...@chromium.org — Nov 5, 2024 03:31AM**

Thanks for letting us know! I've just returned from OOO so I've tagged this for donations processing. I'll try to get back to you with the benevity information for donation by EOW. Thanks for your patience!


---

**#32 — pe...@google.com — Nov 12, 2024 10:58AM**

This issue requires additional review before it can be merged to the LTS channel. Please answer the following questions to help us evaluate this merge:

  1. Number of CLs needed for this fix and links to them.
  2. Level of complexity (High, Medium, Low - Explain)
  3. Has this been merged to a stable release? beta release?
  4. Overall Recommendation (Yes, No)


---

**#33 — qk...@google.com — Nov 12, 2024 11:23AM**

1\. [https://chromium-review.googlesource.com/c/v8/v8/+/5938506](<https://chromium-review.googlesource.com/c/v8/v8/+/5938506>)  
2\. Medium, there were some conflicts. So we needed to modify the patch to adjust into M126.   
3\. 130  
4\. Yes


---

**#34 — gm...@google.com — Nov 12, 2024 11:13PM**

Merge Rejected as there are too many conflicts with 126.


---

**#35 — pe...@google.com — Jan 18, 2025 12:43AM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
