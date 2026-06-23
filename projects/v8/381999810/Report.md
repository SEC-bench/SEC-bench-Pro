# V8 Sandbox Bypass: Memory corruption outside the V8 sandbox

Issue URL: https://issues.chromium.org/issues/381999810
VRP-Reward: 5000
Date: Dec 4, 2024 02:08AM


## REPRODUCTION CASE

  1. build active release channel build of d8, version is: 13.1.201.9

```
git checkout 13.1.201.9
gclient sync
```

  * args.gn

```
is_component_build = false
is_debug = false
target_cpu = "x64"
v8_enable_sandbox = true
v8_enable_backtrace = true
v8_enable_disassembler = true
v8_enable_object_print = true
v8_enable_verify_heap = true
dcheck_always_on = false
v8_enable_memory_corruption_api = true
```

  2. Run PoC with: `out/x64.release/d8 --fuzzing --sandbox-fuzzing poc.js`

```
$ /usr/class/v8/v8/out/x64.release/d8 --fuzzing --sandbox-fuzzing ./poc_for_cf.js 
Sandbox fuzzing mode is enabled. Only sandbox violations will be reported, all other crashes will be ignored.

## V8 sandbox violation detected!

Received signal 11 SEGV_MAPERR 0005da94e153

==== C stack trace ===============================

 [0x55ee48315253]
 [0x55ee483151a2]
 [0x7f8844642520]
 [0x55ee47684624]
 [0x55ee47683be4]
 [0x55ee47683a5a]
 [0x55ee47683640]
 [0x55ee4772669b]
 [0x55ee47740535]
 [0x55ee480e07de]
[end of stack trace]
[1]    1349803 segmentation fault  /usr/class/v8/v8/out/x64.release/d8 --fuzzing --sandbox-fuzzing
```

## Backtrace in latest c3e48a7c58d9a88cb46848b59fb1f621c72a9606(#97510)

```
#0  v8::internal::wasm::Decoder::read_little_endian<unsigned int, v8::internal::wasm::Decoder::NoValidationTag> (this=<optimized out>, pc=0x5da94e153 <error: Cannot access memory at address 0x5da94e153>, msg=<optimized out>) at ../../src/wasm/decoder.h:470
#1  0x000055591c24bbc0 in v8::internal::wasm::Decoder::consume_little_endian<unsigned int, (v8::internal::wasm::Decoder::TraceFlag)0> (this=this@entry=0x7fff92b30bd0, name=0x5559193531af "wasm magic") at ../../src/wasm/decoder.h:481
#2  0x000055591c242ec1 in v8::internal::wasm::Decoder::consume_u32 (this=0x7fff92b30bd0, tracer=0x0, name=<optimized out>) at ../../src/wasm/decoder.h:247
#3  v8::internal::wasm::ModuleDecoderImpl::DecodeModuleHeader (this=this@entry=0x7fff92b30bd0, bytes=...) at ../../src/wasm/module-decoder-impl.h:330
#4  0x000055591c241b0a in v8::internal::wasm::ModuleDecoderImpl::DecodeModule (this=this@entry=0x7fff92b30bd0, validate_functions=true) at ../../src/wasm/module-decoder-impl.h:1713
#5  0x000055591c24162f in v8::internal::wasm::DecodeWasmModule (enabled_features=enabled_features@entry=..., wire_bytes=..., validate_functions=true, origin=origin@entry=v8::internal::wasm::kWasmOrigin, detected_features=0x7fff92b30ec4) at ./../../src/wasm/module-decoder.cc:125
#6  0x000055591c240ad6 in v8::internal::wasm::DecodeWasmModule (enabled_features=enabled_features@entry=..., wire_bytes=..., validate_functions=<optimized out>, origin=origin@entry=v8::internal::wasm::kWasmOrigin, counters=0x55591fef0768, metrics_recorder=..., context_id=..., decoding_method=v8::internal::wasm::DecodingMethod::kSync, detected_features=0x7fff92b30ec4) at ./../../src/wasm/module-decoder.cc:91
#7  0x000055591c310c99 in v8::internal::wasm::WasmEngine::SyncValidate (this=<optimized out>, isolate=0x55591fedf000, enabled=..., compile_imports=..., bytes=...) at ./../../src/wasm/wasm-engine.cc:578
#8  0x000055591c3598d1 in v8::(anonymous namespace)::WebAssemblyValidateImpl (info=...) at ./../../src/wasm/wasm-js.cc:905
#9  v8::internal::wasm::WebAssemblyValidate (info=...) at ./../../src/wasm/wasm-js.cc:3066
#10 0x000055591e01be6e in Builtins_CallApiCallbackGeneric ()
#11 0x00003f7e00000000 in ?? ()
```

## CREDIT INFORMATION

Reporter credit: Nan Wang(@eternalsakura13) and Zhenghang Xiao(@Kipreyyy)


---

**#2 — ja...@chromium.org — Dec 4, 2024 08:22AM**

Thanks for the bug report. I've confirmed that the poc_for_cf.js is the same as minipoc_for_manual.js but with wasm-module-builder.js in-lined ([https://source.chromium.org/chromium/chromium/src/+/main:v8/test/mjsunit/wasm/wasm-module-builder.js;drc=a8c7a2a6848e51a1942c248533668cb7a6bec78f](<https://source.chromium.org/chromium/chromium/src/+/main:v8/test/mjsunit/wasm/wasm-module-builder.js;drc=a8c7a2a6848e51a1942c248533668cb7a6bec78f>)). `diff -w -y poc_for_cf.js wasm-module-builder.js`.

Passing to clusterfuzz for analysis.


---

**#3 — cl...@appspot.gserviceaccount.com — Dec 4, 2024 08:24AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5637717849210880](<https://clusterfuzz.com/testcase?key=5637717849210880>).


---

**#4 — ja...@chromium.org — Dec 4, 2024 08:30AM**

This bug is the V8 Sandbox which is still under development and the guidelines say to provide a provisional severity of Medium (S2) and provisional priority of P1 -- these may change after further triage.

Passing this bug to the current security shepherd: saelo@.


---

**#5 — ja...@chromium.org — Dec 4, 2024 08:35AM**

[Security shepherd] Hi saelo@, can you please take a look and triage further? Thanks!


---

**#6 — cl...@appspot.gserviceaccount.com — Dec 4, 2024 05:17PM**

Detailed Report: [https://clusterfuzz.com/testcase?key=6261166980399104](<https://clusterfuzz.com/testcase?key=6261166980399104>)  
  
Fuzzer: None  
Job Type: linux_d8_sandbox_testing  
Platform Id: linux  
  
Crash Type: V8 sandbox violation  
Crash Address:   
Crash State:  
NULL  
Sanitizer: address (ASAN)  
  
Crash Revision: [https://clusterfuzz.com/revisions?job=linux_d8_sandbox_testing&revision=97471](<https://clusterfuzz.com/revisions?job=linux_d8_sandbox_testing&revision=97471>)  
  
Reproducer Testcase: [https://clusterfuzz.com/download?testcase_id=6261166980399104](<https://clusterfuzz.com/download?testcase_id=6261166980399104>)  
  
To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.   
  
If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.  
  
If you have any feedback on reproducing test cases, let us know at [https://forms.gle/Yh3qCYFveHj6E5jz5](<https://forms.gle/Yh3qCYFveHj6E5jz5>) so we can improve.


---

**#7 — sa...@chromium.org — Dec 5, 2024 01:09AM**

Thanks for the report! So the issue here is pretty simple: when we want to process the Wasm wire bytes from a TypedArray, we [take the backing store's Data() pointer and add the array's ByteOffset() to it](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/wasm-js.cc;l=225;drc=f69436f69d8c49ba31887a2ad7dcf255facc508c0>). However, the pointer can be nullptr and so this can end up accessing memory in the first 32GB of the address space. This particular use case is harmless because it's always just a read (we never write into the Wasm wire bytes while parsing them). I'll however check if this pattern occurs elsewhere where we might then write instead.


---

**#8 — ap...@google.com — Dec 5, 2024 09:36PM**

Project: v8/v8  
Branch: main  
Author: Samuel Groß <[saelo@chromium.org](<mailto:saelo@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6072811](<https://chromium-review.googlesource.com/6072811>)

[sandbox] Ensure BackingStore::buffer_start always points into the sandbox

* * *

Expand for full commit details

```
[sandbox] Ensure BackingStore::buffer_start always points into the sandbox 
 
An ArrayBuffer's buffer pointer must always point into the sandbox (e.g. 
because we'll reference it via an offset from the start of the sandbox). 
When the buffer is empty, we use a special EmptyBackingStoreBuffer() 
constant which points at the end of the sandbox, right before a huge 
guard region area. This way, any access to the "null" value will result 
in a harmless crash, even with the maximum possible index. However, we 
should also use the EmptyBackingStoreBuffer() when returning the backing 
buffer via the V8 API. Otherwise, if we return nullptr, a user of the 
API might compute `nullptr + array->ByteOffset()` which could result in 
an address in the first 32GB of the address space. This CL therefore 
changes the BackingStore::buffer_start() accessor to return the 
EmptyBackingStoreBuffer() constant if the buffer is empty. 
 
Bug: 381999810 
Change-Id: I5f1d909ed2cb458d406bbe133f12be1167141e56 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6072811 
Reviewed-by: Igor Sheludko <ishell@chromium.org> 
Commit-Queue: Samuel Groß <saelo@chromium.org> 
Cr-Commit-Position: refs/heads/main@{#97569}
```

* * *

Files:

  * M `src/objects/backing-store.h`
  * M `src/objects/js-array-buffer.cc`
  * M `src/sandbox/testing.cc`
  * M `test/cctest/test-api-array-buffer.cc`
  * A `test/mjsunit/sandbox/regress/regress-381999810.js`
  * M `test/mjsunit/sandbox/regress/regress-40070746.js`

* * *

Hash: 2f38832cd8c088b05ce6642c473521af9b6deeb8  
Date: Thu Dec 05 11:51:55 2024

* * *


---

**#9 — ap...@google.com — Dec 5, 2024 10:42PM**

Project: v8/v8  
Branch: main  
Author: Eva Herencsárová <[evih@chromium.org](<mailto:evih@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6074510](<https://chromium-review.googlesource.com/6074510>)

Revert "[sandbox] Ensure BackingStore::buffer_start always points into the sandbox"

* * *

Expand for full commit details

```
Revert "[sandbox] Ensure BackingStore::buffer_start always points into the sandbox" 
 
This reverts commit 2f38832cd8c088b05ce6642c473521af9b6deeb8. 
 
Reason for revert: fails on https://ci.chromium.org/ui/p/v8/builders/ci/V8%20Blink%20Linux/34481/overview  
 
Original change's description: 
> [sandbox] Ensure BackingStore::buffer_start always points into the sandbox 
> 
> An ArrayBuffer's buffer pointer must always point into the sandbox (e.g. 
> because we'll reference it via an offset from the start of the sandbox). 
> When the buffer is empty, we use a special EmptyBackingStoreBuffer() 
> constant which points at the end of the sandbox, right before a huge 
> guard region area. This way, any access to the "null" value will result 
> in a harmless crash, even with the maximum possible index. However, we 
> should also use the EmptyBackingStoreBuffer() when returning the backing 
> buffer via the V8 API. Otherwise, if we return nullptr, a user of the 
> API might compute `nullptr + array->ByteOffset()` which could result in 
> an address in the first 32GB of the address space. This CL therefore 
> changes the BackingStore::buffer_start() accessor to return the 
> EmptyBackingStoreBuffer() constant if the buffer is empty. 
> 
> Bug: 381999810 
> Change-Id: I5f1d909ed2cb458d406bbe133f12be1167141e56 
> Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6072811 
> Reviewed-by: Igor Sheludko <ishell@chromium.org> 
> Commit-Queue: Samuel Groß <saelo@chromium.org> 
> Cr-Commit-Position: refs/heads/main@{#97569} 
 
Bug: 381999810 
Change-Id: Ice54d501778609f62763a6e9e2b7b8f53cc41ca4 
No-Presubmit: true 
No-Tree-Checks: true 
No-Try: true 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6074510 
Bot-Commit: Rubber Stamper <rubber-stamper@appspot.gserviceaccount.com> 
Commit-Queue: Eva Herencsárová <evih@chromium.org> 
Owners-Override: Eva Herencsárová <evih@chromium.org> 
Cr-Commit-Position: refs/heads/main@{#97570}
```

* * *

Files:

  * M `src/objects/backing-store.h`
  * M `src/objects/js-array-buffer.cc`
  * M `src/sandbox/testing.cc`
  * M `test/cctest/test-api-array-buffer.cc`
  * D `test/mjsunit/sandbox/regress/regress-381999810.js`
  * M `test/mjsunit/sandbox/regress/regress-40070746.js`

* * *

Hash: 140ae5d27dd83aeeac4787b3fd41dea7e46485fc  
Date: Thu Dec 05 13:39:16 2024

* * *


---

**#10 — ap...@google.com — Dec 6, 2024 01:21AM**

Project: chromium/src  
Branch: main  
Author: Samuel Groß <[saelo@chromium.org](<mailto:saelo@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6074884](<https://chromium-review.googlesource.com/6074884>)

Fix BlinkTransferableMessageStructTraitsTest

* * *

Expand for full commit details

```
Fix BlinkTransferableMessageStructTraitsTest 
 
The V8 API does not specify that an empty/detached ArrayBuffer returns 
nullptr as data pointer. Historically, this used to be the case, but it 
is not fully compatible with the V8 Sandbox as an ArrayBuffer's backing 
store must always point into the sandbox. Instead, we use a special 
EmptyBackingStoreBuffer constant which points at the end of the sandbox 
at the start of a multi-gigabyte guard region. As such, this CL changes 
the BlinkTransferableMessageStructTraitsTest to no longer expect nullptr 
but to instead query the WasDetached method and the ByteLength. 
 
Bug: 381999810 
Change-Id: I605b2046c24ffa4fa39d54ce24c3097eb783ee61 
Reviewed-on: https://chromium-review.googlesource.com/c/chromium/src/+/6074884 
Reviewed-by: Camille Lamy <clamy@chromium.org> 
Commit-Queue: Samuel Groß <saelo@chromium.org> 
Cr-Commit-Position: refs/heads/main@{#1392309}
```

* * *

Files:

  * M `third_party/blink/renderer/core/messaging/blink_transferable_message_mojom_traits_test.cc`

* * *

Hash: 9d8e02a6e2cb11999a1f67727679360d053fd31b  
Date: Thu Dec 05 16:19:55 2024

* * *


---

**#11 — ap...@google.com — Dec 6, 2024 01:59AM**

Project: v8/v8  
Branch: main  
Author: Samuel Groß <[saelo@chromium.org](<mailto:saelo@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6074636](<https://chromium-review.googlesource.com/6074636>)

Reland "[sandbox] Ensure BackingStore::buffer_start always points into the sandbox"

* * *

Expand for full commit details

```
Reland "[sandbox] Ensure BackingStore::buffer_start always points into the sandbox" 
 
This is a reland of commit 2f38832cd8c088b05ce6642c473521af9b6deeb8 
 
Failing test has been fixed in crrev.com/c/6074884 
 
Original change's description: 
> [sandbox] Ensure BackingStore::buffer_start always points into the sandbox 
> 
> An ArrayBuffer's buffer pointer must always point into the sandbox (e.g. 
> because we'll reference it via an offset from the start of the sandbox). 
> When the buffer is empty, we use a special EmptyBackingStoreBuffer() 
> constant which points at the end of the sandbox, right before a huge 
> guard region area. This way, any access to the "null" value will result 
> in a harmless crash, even with the maximum possible index. However, we 
> should also use the EmptyBackingStoreBuffer() when returning the backing 
> buffer via the V8 API. Otherwise, if we return nullptr, a user of the 
> API might compute `nullptr + array->ByteOffset()` which could result in 
> an address in the first 32GB of the address space. This CL therefore 
> changes the BackingStore::buffer_start() accessor to return the 
> EmptyBackingStoreBuffer() constant if the buffer is empty. 
> 
> Bug: 381999810 
> Change-Id: I5f1d909ed2cb458d406bbe133f12be1167141e56 
> Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6072811 
> Reviewed-by: Igor Sheludko <ishell@chromium.org> 
> Commit-Queue: Samuel Groß <saelo@chromium.org> 
> Cr-Commit-Position: refs/heads/main@{#97569} 
 
Bug: 381999810 
Change-Id: I911d826f8b2f8290e37253ff957f0b7e71102f08 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6074636 
Commit-Queue: Samuel Groß <saelo@chromium.org> 
Reviewed-by: Igor Sheludko <ishell@chromium.org> 
Cr-Commit-Position: refs/heads/main@{#97583}
```

* * *

Files:

  * M `src/objects/backing-store.h`
  * M `src/objects/js-array-buffer.cc`
  * M `src/sandbox/testing.cc`
  * M `test/cctest/test-api-array-buffer.cc`
  * A `test/mjsunit/sandbox/regress/regress-381999810.js`
  * M `test/mjsunit/sandbox/regress/regress-40070746.js`

* * *

Hash: 12a53cc493f02f64f30dd08c0ec03a866ae45481  
Date: Thu Dec 05 11:51:55 2024

* * *


---

**#12 — sa...@chromium.org — Dec 6, 2024 07:05PM**

This should now be fixed with the above CL. As mentioned in [comment #7](<https://issues.chromium.org/issues/381999810#comment7>), this use and all other uses I could find in V8 itself are fine: we'll only ever read from that data. However I found some uses in Blink (e.g. [here](<https://source.chromium.org/chromium/chromium/src/+/main:gin/array_buffer.h;l=87;drc=5103ac6102b144aff2bb3b45fe525521ecf3320d>)) that look like they might also cause a write, so I'll leave this as Type-Vulnerability out of precaution.


---

**#13 — sp...@google.com — Dec 19, 2024 06:55AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $5000.00 for this report.  
  
Rationale for this decision:  
V8 sandbox bypass reward  
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#14 — am...@chromium.org — Dec 19, 2024 09:20AM**

Congratulations Nan and Zhenghang! Thank you for your efforts and reporting this V8 sandbox issue to us.


---

**#15 — ch...@google.com — Mar 15, 2025 09:40PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
