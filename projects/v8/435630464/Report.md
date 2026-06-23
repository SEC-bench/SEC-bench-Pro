# V8 Sandbox Bypass: In-sandbox corruption allows execution of dangerous / experimental code

Issue URL: https://issues.chromium.org/issues/435630464
VRP-Reward: 20000
Date: Aug 2, 2025 09:53AM


### VULNERABILITY DETAILS

#### README

**This bug report is a meta-report on a class of V8 sandbox bypasses**. I will not be filing bugs for every single discovered bypasses of these types as it just adds noise, but if you want to see more of these let me know. As I expect much more of these problematic cases in many insufficiently tested code, I recommend a catch-all solution for these issues.

#### Summary

An attacker may exploit in-sandbox corruption primitives to unlock a vast amount of dangerous or experimental code that is not fully verified or tested. By exploiting these code paths, an attacker may easily discover and exploit V8 sandbox violations in such code.

#### Details

Summary is a great TL;DR on the issue - in this section I will explain more on concrete examples on how to achieve this. In this report we specifically look into the [JavaScript Structs proposal](<https://github.com/tc39/proposal-structs>) in a three-step, bottom-up manner: we first identify the offending code in V8, find paths to reach it, then exploit the bug.

##### V8 sandbox violation in Structs Proposal

This proposal adds some synchronization primitives such as mutexes and condition variables. Both the types inherit from [`JSSynchronizationPrimitive`](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/objects/js-atomics-synchronization.tq>) holding a `waiter_queue_head: ExternalPointer`, which simply points to the head of a doubly linked list that is waiting on some sync event.

When a request cannot be immediately served (in the fast path), waiters may be enqueued in these lists. One example is on `Atomics.Condition.wait(cv, mtx, timeout)` where a thread may wait for a condition variable to trigger for a certain timeout. This is handled in [`JSAtomicsCondition::WaitFor()`](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/objects/js-atomics-synchronization.cc;drc=d32f634388f26f8c7bbb98c82fa9718d30636b1e;l=1177>) where the code does the following in sequence:

  1. Enqueues the current thread into condition variable via `JSAtomicsCondition::QueueWaiter(requester, cv, &this_waiter)`
     * `this_waiter` is allocated on the stack.
  2. Unlocks the mutex
  3. Waits for condition variable to trigger for a certain timeout
  4. If timed out, remove itself from the waiter queue via `DequeueExplicit(...)`

4 assures that the queue node allocated on the stack in 1 cannot be alive after exiting the function. However, with an attacker that can corrupt the condition variable this no longer holds, as the condition variable may be corrupted to a state as if a notifying thread already removed the current thread from the waiter. This may leave `this_waiter` enqueued in the waiter queue, where following uses will lead to a stack use-after-return. Exploiting this condition to an arbitrary address write is easily achievable by spraying the stack with Wasm locals.

##### Reviving Structs Proposal (or really, anything `kJSEntrypointTag`ged)

Structs proposal is guarded behind `--harmony-struct`, currently disabled by default. The relevant objects and functions are thus not installed in [`Genesis::InitializeGlobal_harmony_struct()`](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/init/bootstrapper.cc;drc=02c0091bfcefaf4523de1db788cac8dd88b102de;l=5598>).

The key idea to bypass this is that these builtins still exist in the code - their `Code` objects exist, they are in the builtins table, and so on. They just aren't installed in a readily available dispatch table handle. In short, we can just find a code path that fetches `sfi->GetCode()`, and then installs this into a dispatch table handle through e.g. `function->UpdateCode()`.

Turns out that this is in fact common, or even a standard way of installing Code into dispatch tables. `Runtime_CompileLazy()` => `Compiler::Compile()` is the simplest example:

```
// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/codegen/compiler.cc;drc=f9bdd5ea89d8748ea9ecb024c769f6df8121a1fd;l=3001
bool Compiler::Compile(Isolate* isolate, DirectHandle<JSFunction> function,
                       ClearExceptionFlag flag,
                       IsCompiledScope* is_compiled_scope) {
  // ...
  DirectHandle<Code> code(shared_info->GetCode(isolate), isolate);
  function->UpdateCode(isolate, *code);
  // ...
}
```

Unfortunately this is difficult to use for certain functions that hold `kDontAdaptArgumentsSentinel` (=0) as its argument count, as most JS functions hold argument counts of `kJSArgcReceiverSlots` (=1) or above. AFAICT it is difficult to install a code handle with a `Builtins_CompileLazy` and a `kDontAdaptArgumentsSentinel` argument count. We can race this window and install a victim handle that suits this constraint, but racy exploits are no good.

We thus use another code path [`CreateDynamicFunction()`](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/builtins/builtins-function.cc;drc=6ce9796895924f752107e144b20406e31bea2367;l=23>) which handles `new Function()` and its variants. When a function is created it is put into a compilation cache so that future instantiations of the same scope and string can use the same function. This guarantees that we have the same `SharedFunctionInfo` of the generated function which is passed through `Runtime_NewClosure()`. Exploitation is then simple:

  1. Acquire `SharedFunctionInfo` from the first generated function
  2. Corrupt it to point to our desired builtins
  3. Set up a compatible `FeedbackCell.dispatch_handle`
  4. Create the function

`JSFunctionBuilder()` will install the builtin code on the compatible dispatch handle, then set this dispatch handle on the returned `JSFunction`. Repeat this to create any builtins that you wish to call, given that they are `kJSEntrypointTag`-compatible.

##### Exploitation

Exploiting this is really a non-issue. Although we cannot directly create `JSAtomicMutex` or `JSAtomicCondition` from its constructors due to the absence of the shared space allocator, we can simply corrupt a random object's map and make it one. Call `AtomicsMutexLock()` -> `AtomicsConditionWait()` while a worker thread concurrently corrupts condition variable state as if it's unlocked, then we have a dangling waiter queue node underneath the stack. Spray it with wasm, then trigger another enqueue/dequeue to obtain arbitrary controlled address write.

### VERSION

V8: Tested on `d8-sandbox-testing-linux-release-v8-component-101728`

### REPRODUCTION CASE

Attached as `v8sbx-unlock-sharedstruct.js`, run with `./d8 --sandbox-testing`.

> The repro already has `SharedFunctionInfo` and `Map` dumps matching that of the tested version hardcoded inside. To repro this in another version, run with `--harmony-struct` added and then copy the dumps over to the else-branch.

The repro attempts a controlled address write near the address `0x133714470000`. Other call sites also allow vtable calls although not presented in this repro.

### FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION

Type of crash: Sandbox violation

### CREDIT INFORMATION

Reporter credit: Seunghyun Lee (@0x10n) of CMU CyLab

* * *

This was discovered with a v8 sandbox fuzzer.  
Marking any rewards for charity in advance.


---

**#2 — ja...@chromium.org — Aug 5, 2025 04:48AM**

[security shepherd] Thanks for the report. I'll work on reproducing the provided example. For now I'll:

  * set provisional severity medium
  * set provisional priority p1
  * assign to the v8 shepherd
  * applying security_impact-none
  * adding v8-sandbox hotlist


---

**#3 — cl...@appspot.gserviceaccount.com — Aug 5, 2025 05:12AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=6023749543329792](<https://clusterfuzz.com/testcase?key=6023749543329792>).


---

**#4 — ja...@chromium.org — Aug 5, 2025 05:20AM**

[security shepherd]

Provisionally adding the JS Sandbox as the component.


---

**#5 — ja...@chromium.org — Aug 5, 2025 07:45AM**

Provisionally setting OS to desktop and Android.


---

**#6 — 24...@project.gserviceaccount.com — Aug 6, 2025 12:05AM**

Detailed Report: [https://clusterfuzz.com/testcase?key=6023749543329792](<https://clusterfuzz.com/testcase?key=6023749543329792>)  
  
Fuzzer: None  
Job Type: linux_asan_d8_sandbox_testing  
Platform Id: linux  
  
Crash Type: V8 sandbox violation  
Crash Address: 0x76f8b1580358  
Crash State:  
v8::internal::detail::WaiterQueueNode::Enqueue  
v8::internal::JSAtomicsCondition::QueueWaiter  
v8::internal::JSAtomicsCondition::WaitFor  
  
Sanitizer: address (ASAN)  
  
Regressed: [https://clusterfuzz.com/revisions?job=linux_asan_d8_sandbox_testing&range=100493:100494](<https://clusterfuzz.com/revisions?job=linux_asan_d8_sandbox_testing&range=100493:100494>)  
  
Reproducer Testcase: [https://clusterfuzz.com/download?testcase_id=6023749543329792](<https://clusterfuzz.com/download?testcase_id=6023749543329792>)  
  
To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.  
  
If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.  
  
If you have any feedback on reproducing test cases, let us know at [https://forms.gle/Yh3qCYFveHj6E5jz5](<https://forms.gle/Yh3qCYFveHj6E5jz5>) so we can improve.


---

**#7 — 24...@project.gserviceaccount.com — Aug 6, 2025 12:19AM**

Automatically applying components based on crash stacktrace and information from OWNERS files.  
  
If this is incorrect, please apply the hotlistid:4801165.


---

**#8 — ch...@google.com — Aug 6, 2025 09:36PM**

This is a serious security regression. If you are not able to fix this quickly, please revert the change that introduced it.

If this doesn't affect a release branch, or has not been properly classified for severity, please update the Security Impact hotlist or the Severity field, and remove the ReleaseBlock hotlist.


---

**#9 — ch...@google.com — Aug 6, 2025 09:42PM**

This issue is marked as a release blocker with no milestone associated. Please add an appropriate milestone.

All release blocking issues should have milestones associated to it, so that the issue can tracked and the fixes can be pushed promptly.

Thanks for your time! To disable nags, add Disable-Nags (case sensitive) to the Chromium Labels custom field.


---

**#10 — is...@chromium.org — Aug 21, 2025 11:17PM**

Thank you for the report! Nice catch!


---

**#11 — dx...@google.com — Aug 22, 2025 12:25AM**

Project: v8/v8  
Branch: main  
Author: Igor Sheludko [ishell@chromium.org](<mailto:ishell@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6871495](<https://chromium-review.googlesource.com/6871495>)

[sandbox] Add helpers for setting function's entry to a builtin

* * *

Expand for full commit details

```
     
    Namely: 
     - Sandbox.getBuiltinNames() returns an array of all builtin names, 
     - Sandbox.setFunctionCodeToBuiltin() sets function's entry point to 
       given builtin's entry point. 
     
    Bug: 435630464 
    Change-Id: I64151c92ea03746e100288dab796fd957db976dd 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6871495 
    Reviewed-by: Samuel Groß <saelo@chromium.org> 
    Commit-Queue: Igor Sheludko <ishell@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#101975}
```

* * *

Files:

  * M `src/sandbox/testing.cc`
  * M `test/mjsunit/sandbox/memory-corruption-api.js`

* * *

Hash: [35c92a8bed12445e63a99fe12ff953cbb172f27e](<https://chromiumdash.appspot.com/commit/35c92a8bed12445e63a99fe12ff953cbb172f27e>)  
Date: Thu Aug 21 14:49:59 2025

* * *


---

**#12 — 24...@project.gserviceaccount.com — Sep 3, 2025 04:29PM**

ClusterFuzz testcase 6023749543329792 is verified as fixed in [https://clusterfuzz.com/revisions?job=linux_asan_d8_sandbox_testing&range=102192:102193](<https://clusterfuzz.com/revisions?job=linux_asan_d8_sandbox_testing&range=102192:102193>)  
  
If this is incorrect, please add the hotlistid:5433040 and re-open the issue.


---

**#13 — se...@gmail.com — Sep 17, 2025 03:45AM**

Bump, any updates on this? It's been over a month since the report, I see the sandbox API addition and several recent fixes that are just individual instances of this issue, e.g. [https://crrev.com/c/6929545](<https://crrev.com/c/6929545>) which my fuzzer also frequently hits and [https://crrev.com/c/6955106](<https://crrev.com/c/6955106>), but I don't see any broad fixes or even a fix for the specific path used in this report. At least we can replace the v8_flags DCHECKs with CHECKs (and add any on missing paths) as a starter, then try handling issues around other `kJSEntrypointTag`ged builtins?


---

**#14 — is...@chromium.org — Sep 17, 2025 05:51PM**

Thanks for pinging. Developers were OOO for some time, but we are getting back to this issue.


---

**#15 — dx...@google.com — Sep 20, 2025 12:49AM**

Project: v8/v8  
Branch: main  
Author: Igor Sheludko [ishell@chromium.org](<mailto:ishell@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6965028](<https://chromium-review.googlesource.com/6965028>)

[sandbox] Disallow builtins with CCallDescriptor as function's code

* * *

Expand for full commit details

```
     
    This is not an issue yet because the only two such builtins we 
    have safely crash by tail calling kIllegal builtin (these builtins 
    do useful things only on arm/ia32 architectures). 
     
    This CL makes sure that even if we accidentally add such a bulitin in 
    the future the code verification machinery will catch it. 
     
    Bug: 435630464 
    Change-Id: Ib53af95255fd8a6aa6d7e6bbd199c5b2530513d3 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6965028 
    Reviewed-by: Michael Lippautz <mlippautz@chromium.org> 
    Auto-Submit: Igor Sheludko <ishell@chromium.org> 
    Commit-Queue: Igor Sheludko <ishell@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#102645}
```

* * *

Files:

  * M `src/codegen/interface-descriptors.h`
  * A `test/mjsunit/sandbox/regress/regress-435630464-ccall.js`

* * *

Hash: [a55b9c4c885c7802118b9e883f1f0c345d76968e](<https://chromiumdash.appspot.com/commit/a55b9c4c885c7802118b9e883f1f0c345d76968e>)  
Date: Fri Sep 19 13:52:52 2025

* * *


---

**#16 — dx...@google.com — Sep 22, 2025 06:52PM**

Project: v8/v8  
Branch: main  
Author: Igor Sheludko [ishell@chromium.org](<mailto:ishell@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6969063](<https://chromium-review.googlesource.com/6969063>)

[builtins] Remove unused kCEntry_Return2_ArgvOnStack_BuiltinExit builtin

* * *

Expand for full commit details

```
     
    CEntry with BuiltinExit has JS calling convention because it's used 
    for CPP builtins. On the other hand, JS calling convention allows 
    returning only one value, so this CEntry variant will never be needed. 
     
    Bug: 435630464 
    Change-Id: I5ae174a374dc7743dccd75fba44e678587b2019a 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6969063 
    Reviewed-by: Michael Lippautz <mlippautz@chromium.org> 
    Commit-Queue: Michael Lippautz <mlippautz@chromium.org> 
    Auto-Submit: Igor Sheludko <ishell@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#102657}
```

* * *

Files:

  * M `src/builtins/builtins-definitions.h`
  * M `src/builtins/builtins-inl.h`
  * M `src/builtins/builtins-internal-gen.cc`
  * M `src/debug/debug-evaluate.cc`

* * *

Hash: [c4e030495d8b5ffb1ff89d2fe02e83563ed0aba4](<https://chromiumdash.appspot.com/commit/c4e030495d8b5ffb1ff89d2fe02e83563ed0aba4>)  
Date: Fri Sep 19 13:04:44 2025

* * *


---

**#17 — dx...@google.com — Sep 22, 2025 06:59PM**

Project: v8/v8  
Branch: main  
Author: Igor Sheludko [ishell@chromium.org](<mailto:ishell@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6965029](<https://chromium-review.googlesource.com/6965029>)

[sandbox] Introduce kCEntryEntrypointTag for CEntry builtins

* * *

Expand for full commit details

```
     
    ... which are not compatible with JS calling convention. 
     
    Bug: 435630464 
    Change-Id: I1cb765047236fe6a970b64e4313267502e3e8fad 
    Fixed: 445966259 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6965029 
    Auto-Submit: Igor Sheludko <ishell@chromium.org> 
    Commit-Queue: Michael Lippautz <mlippautz@chromium.org> 
    Reviewed-by: Michael Lippautz <mlippautz@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#102658}
```

* * *

Files:

  * M `src/codegen/interface-descriptors.h`
  * M `src/compiler/linkage.cc`
  * M `src/sandbox/code-entrypoint-tag.h`
  * A `test/mjsunit/sandbox/regress/regress-435630464-centry.js`

* * *

Hash: [a622c3686d9b0eeb6fbf38c949252479460b967a](<https://chromiumdash.appspot.com/commit/a622c3686d9b0eeb6fbf38c949252479460b967a>)  
Date: Fri Sep 19 16:25:05 2025

* * *


---

**#18 — dx...@google.com — Sep 25, 2025 12:04AM**

Project: v8/v8  
Branch: main  
Author: Igor Sheludko [ishell@chromium.org](<mailto:ishell@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6976541](<https://chromium-review.googlesource.com/6976541>)

[sandbox] Remove kDefaultCodeEntrypointTag, pt.1

* * *

Expand for full commit details

```
     
    This is a step towards making code entrypoint tag verification strict. 
     
    This CL 
     - introduces kCodeEntrypointTagForTesting, 
     - introduces CodeKind::FOR_TESTING_JS in addition to existing 
       CodeKind::FOR_TESTING in order to assign them different code 
       entrypoint tags (kJSEntrypointTag for the former and 
       kCodeEntrypointTagForTesting for the latter), 
     - add SBXCHECK for Code object's entrypoint tags when generating calls 
       and tail calls to compile-time known Code objects, 
     - introduce Linkage::GetCPPBuiltinCallDescriptor() - a CEntry call 
       descriptor customized for CPP builtins, 
     - replaces some of the kDefaultCodeEntrypointTag usages with correct 
       tags, 
     - fixes usages of entrypoint tags in various code generation unit 
       tests. 
     
    Drive-by: 
     - assign proper descriptor for GenericJSToWasmInterpreterWrapper 
       builtin, 
     - make Builtins::CallInterfaceDescriptorFor() work for bytecode 
       handlers, 
     - make switches over CodeKind values case-complete. 
     
    Bug: 435630464 
    Change-Id: I2e34666df5314b0cd4e604a4deaf74e2f0de6f1a 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6976541 
    Commit-Queue: Igor Sheludko <ishell@chromium.org> 
    Reviewed-by: Darius Mercadier <dmercadier@chromium.org> 
    Reviewed-by: Leszek Swirski <leszeks@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#102733}
```

* * *

Files:

  * M `src/builtins/builtins-definitions.h`
  * M `src/builtins/builtins.cc`
  * M `src/codegen/interface-descriptors.h`
  * M `src/codegen/optimized-compilation-info.cc`
  * M `src/compiler/backend/arm64/code-generator-arm64.cc`
  * M `src/compiler/backend/x64/code-generator-x64.cc`
  * M `src/compiler/c-linkage.cc`
  * M `src/compiler/js-call-reducer.cc`
  * M `src/compiler/js-typed-lowering.cc`
  * M `src/compiler/linkage.cc`
  * M `src/compiler/linkage.h`
  * M `src/compiler/pipeline.cc`
  * M `src/diagnostics/objects-debug.cc`
  * M `src/diagnostics/objects-printer.cc`
  * M `src/execution/frames.cc`
  * M `src/heap/mark-compact.cc`
  * M `src/logging/log.cc`
  * M `src/objects/code-inl.h`
  * M `src/objects/code-kind.h`
  * M `src/sandbox/code-entrypoint-tag.h`
  * M `src/sandbox/js-dispatch-table-inl.h`
  * M `src/tracing/perfetto-logger.cc`
  * M `test/cctest/compiler/function-tester.cc`
  * M `test/cctest/compiler/function-tester.h`
  * M `test/cctest/compiler/test-code-generator.cc`
  * M `test/cctest/compiler/test-run-machops.cc`
  * M `test/cctest/compiler/test-run-native-calls.cc`
  * M `test/cctest/test-code-stub-assembler.cc`
  * M `test/cctest/test-descriptor-array.cc`
  * M `test/common/code-assembler-tester.h`
  * M `test/unittests/compiler/backend/instruction-selector-unittest.h`
  * M `test/unittests/compiler/backend/turboshaft-instruction-selector-unittest.h`
  * M `test/unittests/compiler/function-tester.cc`
  * M `test/unittests/compiler/function-tester.h`
  * M `test/unittests/compiler/linkage-tail-call-unittest.cc`
  * M `test/unittests/compiler/run-tail-calls-unittest.cc`
  * M `test/unittests/logging/log-unittest.cc`

* * *

Hash: [d4cd2e644631e03218d1e8507e78351d4b7a67b7](<https://chromiumdash.appspot.com/commit/d4cd2e644631e03218d1e8507e78351d4b7a67b7>)  
Date: Wed Sep 24 14:32:05 2025

* * *


---

**#19 — dx...@google.com — Sep 25, 2025 04:49PM**

Project: v8/v8  
Branch: main  
Author: Igor Sheludko [ishell@chromium.org](<mailto:ishell@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6980144](<https://chromium-review.googlesource.com/6980144>)

[sandbox] Remove kDefaultCodeEntrypointTag, pt.2

* * *

Expand for full commit details

```
     
    This is a step towards making code entrypoint tag verification strict. 
     
    This CL 
     - introduces kUninitializedEntrypointTag to be used for uninitialized 
       code pointer table entries and thus making the pointer value 
       unusable until the entry is initialized for real by 
       CodePointerTable::SetEntrypoint(), 
     - uses kInvalidEntrypointTag as default value for 
       MacroAssembler::LoadCodeInstructionStart() on architectures 
       not supporting V8 Sandbox, 
     - removes kDefaultCodeEntrypointTag. 
     
    Bug: 435630464 
    Change-Id: Iec109648c37fad54e30f4463f83f2470b0da67b9 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6980144 
    Reviewed-by: Leszek Swirski <leszeks@chromium.org> 
    Commit-Queue: Igor Sheludko <ishell@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#102747}
```

* * *

Files:

  * M `src/codegen/arm/macro-assembler-arm.h`
  * M `src/codegen/ia32/macro-assembler-ia32.h`
  * M `src/codegen/ppc/macro-assembler-ppc.h`
  * M `src/codegen/riscv/macro-assembler-riscv.h`
  * M `src/codegen/s390/macro-assembler-s390.h`
  * M `src/sandbox/code-entrypoint-tag.h`
  * M `src/sandbox/indirect-pointer-inl.h`
  * M `src/sandbox/js-dispatch-table-inl.h`

* * *

Hash: [c176120bdcbae851e45a0e64390e7c724fb784fe](<https://chromiumdash.appspot.com/commit/c176120bdcbae851e45a0e64390e7c724fb784fe>)  
Date: Wed Sep 24 16:30:48 2025

* * *


---

**#20 — dx...@google.com — Oct 2, 2025 11:52PM**

Project: v8/v8  
Branch: main  
Author: Igor Sheludko [ishell@chromium.org](<mailto:ishell@chromium.org>)  
Link: [https://chromium-review.googlesource.com/7003082](<https://chromium-review.googlesource.com/7003082>)

[sandbox] Don't allow to use disabled builtins, pt.1

* * *

Expand for full commit details

```
     
    ... i.e. the ones that belong to features that are not currently enabled. 
     
    This CL adds machinery that ensures that a newly added builtin is 
    either mandatory JS language builtin (always enabled and available) or 
    forces developer to update Builtins::GetJSBuiltinState() accordingly. 
     
    This machinery is not yet used for disabling builtins for real. 
     
    Drive-by: fix AccessorTest.WrapFunctionTemplateSetNativeDataProperty test. 
     
    Bug: 435630464 
    Change-Id: I04629f9584c5f8be3c4ecbd2eb939da4fa1bc503 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/7003082 
    Reviewed-by: Michael Lippautz <mlippautz@chromium.org> 
    Reviewed-by: Leszek Swirski <leszeks@chromium.org> 
    Commit-Queue: Igor Sheludko <ishell@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#102905}
```

* * *

Files:

  * M `src/builtins/builtins.cc`
  * M `src/builtins/builtins.h`
  * M `src/execution/isolate.cc`
  * M `src/flags/flag-definitions.h`
  * M `src/runtime/runtime-test.cc`
  * M `src/runtime/runtime.h`
  * M `test/cctest/test-api.cc`
  * M `test/cctest/test-debug.cc`
  * A `test/mjsunit/harmony/builtins-harmony-off.js`
  * A `test/mjsunit/harmony/builtins-harmony-on.js`
  * A `test/mjsunit/harmony/experimental-regexp-engine-builtins.js`
  * A `test/mjsunit/harmony/shadowrealm-builtins.js`
  * M `test/mjsunit/mjsunit.status`
  * A `test/mjsunit/regress/regress-435630464-verification-failure.js`
  * A `test/mjsunit/regress/regress-435630464-verification-ok.js`
  * A `test/mjsunit/shared-memory/builtins.js`
  * M `test/unittests/api/accessor-unittest.cc`
  * M `test/unittests/test-utils.h`

* * *

Hash: [72715e2c109eb9d190d347fbe244fc49ab65c8a5](<https://chromiumdash.appspot.com/commit/72715e2c109eb9d190d347fbe244fc49ab65c8a5>)  
Date: Thu Oct 2 14:05:31 2025

* * *


---

**#21 — is...@chromium.org — Oct 3, 2025 12:01AM**

Reporter, could you please create another issue for the `V8 sandbox violation in Structs Proposal` part assuming `--harmony-struct` is available?

We are about to fix the `meta-report on a class of V8 sandbox bypasses` part and we'd like to close this issue without fixing the Structs Proposal part.

Feel free to use `Sandbox.setFunctionCodeToBuiltin()`!


---

**#22 — se...@gmail.com — Oct 3, 2025 01:38AM**

Re [comment#21](<https://issues.chromium.org/issues/435630464#comment21>): Issue split out to [b/448679390](<https://issues.chromium.org/issues/448679390>).


---

**#23 — dx...@google.com — Oct 6, 2025 08:17PM**

Project: v8/v8  
Branch: main  
Author: Igor Sheludko [ishell@chromium.org](<mailto:ishell@chromium.org>)  
Link: [https://chromium-review.googlesource.com/7003083](<https://chromium-review.googlesource.com/7003083>)

[sandbox] Don't allow to use disabled builtins, pt.2

* * *

Expand for full commit details

```
     
    ... i.e. the ones that belong to features that are not currently enabled. 
     
    This CL: 
     - adds kDisabledBuiltinEntrypointTag, 
     - adds Code::is_disabled_builtin() flag which is set during RO heap 
       deserialization for disabled JS builtins, 
     - disables builtins by using kDisabledBuiltinEntrypointTag for them 
       instead of kJSEntrypointTag, 
     - initializes preallocated dispatch table entries for disabled 
       builtins with Illegal builtin's Code. 
     
    Drive-by: 
     - add TEST_WITH_FLAG macro for cctests which need to change flag 
       values before initializing the Isolate, 
     - fixed respective cctests. 
     
    Bug: 435630464 
    Change-Id: Ibfd8f66ede06210e79184fde027331775c80634b 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/7003083 
    Reviewed-by: Leszek Swirski <leszeks@chromium.org> 
    Commit-Queue: Igor Sheludko <ishell@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#102936}
```

* * *

Files:

  * M `src/builtins/builtins-internal.cc`
  * M `src/builtins/builtins.h`
  * M `src/diagnostics/objects-printer.cc`
  * M `src/execution/isolate.cc`
  * M `src/objects/code-inl.h`
  * M `src/objects/code.h`
  * M `src/sandbox/code-entrypoint-tag.h`
  * M `src/sandbox/js-dispatch-table-inl.h`
  * M `src/sandbox/testing.cc`
  * M `src/snapshot/read-only-deserializer.cc`
  * M `src/snapshot/read-only-serializer.cc`
  * M `test/cctest/cctest.cc`
  * M `test/cctest/cctest.h`
  * M `test/cctest/test-api.cc`
  * A `test/mjsunit/sandbox/regress/regress-435630464-disabled.js`

* * *

Hash: [792c326e896020f74533e0d7b629b9a1b35e555a](<https://chromiumdash.appspot.com/commit/792c326e896020f74533e0d7b629b9a1b35e555a>)  
Date: Mon Oct 6 10:27:29 2025

* * *


---

**#24 — dx...@google.com — Oct 6, 2025 08:41PM**

Project: v8/v8  
Branch: main  
Author: Igor Sheludko [ishell@chromium.org](<mailto:ishell@chromium.org>)  
Link: [https://chromium-review.googlesource.com/7009810](<https://chromium-review.googlesource.com/7009810>)

[sandbox] Make %VerifyGetJSBuiltinState() a no-op with --fuzzing

* * *

Expand for full commit details

```
     
    Fixed: 448972605 
    Bug: 435630464 
    Change-Id: I1131abf83725dfba0c15cb7037b02f3c36d32a7f 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/7009810 
    Reviewed-by: Leszek Swirski <leszeks@chromium.org> 
    Commit-Queue: Igor Sheludko <ishell@chromium.org> 
    Auto-Submit: Igor Sheludko <ishell@chromium.org> 
    Commit-Queue: Leszek Swirski <leszeks@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#102938}
```

* * *

Files:

  * M `src/runtime/runtime-test.cc`
  * M `test/mjsunit/mjsunit.status`

* * *

Hash: [28e10666727ff84684d2c5386c51cc35e9fddb13](<https://chromiumdash.appspot.com/commit/28e10666727ff84684d2c5386c51cc35e9fddb13>)  
Date: Mon Oct 6 11:07:06 2025

* * *


---

**#25 — is...@chromium.org — Oct 6, 2025 08:53PM**

Once CL from [#comment23](<https://issues.chromium.org/issues/435630464#comment23>) sticks the meta-issue about swapping builtins and using disabled builtins should be solved now.

Feel free to create new reports if you find something.


---

**#26 — sp...@google.com — Oct 15, 2025 02:56AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $20000.00 for this report.  
  
Rationale for this decision:  
thank you for pointing out a class of issues here  
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#27 — cl...@chromium.org — Jan 8, 2026 07:33PM**

Removing `Clusterfuzz-ignore` hotlist from some old bugs as it's preventing Clusterfuzz from filing similar bugs.


---

**#28 — ch...@google.com — Jan 13, 2026 09:42PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
