# V8 Sandbox violation: UAF in DoHostImportModuleDynamically

Issue URL: https://issues.chromium.org/issues/442981541
VRP-Reward: BUG
Date: Sep 4, 2025 07:52PM


VULNERABILITY DETAILS

When importing a Module, it creates a CALLBACK_TASK_TYPE object on heap，including two foreign objects，pointing to callback function and data. If we can set two data objects of two callback task to the same one. It will cause a UAF in DoHostImportModuleDynamically.

```
// src/d8/d8.cc:1668
void Shell::DoHostImportModuleDynamically(void* import_data) {
  DynamicImportData* import_data_ =
      static_cast<DynamicImportData*>(import_data); // UAF

  Isolate* isolate(import_data_->isolate);
  Global<Context> global_realm;
  Global<Promise::Resolver> global_resolver;
  Global<Promise> global_result_promise;
  Global<Value> global_namespace_or_source;

  TryCatch try_catch(isolate);
  try_catch.SetVerbose(true);

  {
    HandleScope handle_scope(isolate);
    Local<Context> realm = import_data_->context.Get(isolate);
    Local<Value> referrer = import_data_->referrer.Get(isolate);
    Local<String> v8_specifier = import_data_->specifier.Get(isolate);
    ModuleImportPhase phase = import_data_->phase;
    Local<FixedArray> import_attributes =
        import_data_->import_attributes.Get(isolate);
    Local<Promise::Resolver> resolver = import_data_->resolver.Get(isolate);

    global_realm.Reset(isolate, realm);
    global_resolver.Reset(isolate, resolver);

    PerIsolateData* data = PerIsolateData::Get(isolate);
    data->DeleteDynamicImportData(import_data_);     // Delete here.
    ....
```

VERSION

v8:14.0.302

REPRODUCTION CASE

Build args:

```
is_debug=false
is_asan=true
dcheck_always_on=false
v8_static_library=true
v8_enable_verify_heap=true
v8_enable_i18n_support=true
is_component_build=false
target_cpu="x64"
v8_enable_sandbox=true
v8_enable_memory_corruption_api=true
```

Run args:

```
./d8 --sandbox-fuzzing poc.js
```

FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION Type of crash: heap-use-after-free Crash State:

```
==1921301==ERROR: AddressSanitizer: heap-use-after-free on address 0x7bcb882e2120 at pc 0x55c7da273179 bp 0x7ffe123a0150 sp 0x7ffe123a0148
READ of size 8 at 0x7bcb882e2120 thread T0
    #0 0x55c7da273178 in v8::Shell::DoHostImportModuleDynamically(void*) src/d8/d8.cc:1672:34
    #1 0x55c7dc0495e1 in __RT_impl_Runtime_RunMicrotaskCallback src/runtime/runtime-promise.cc:93:3
    #2 0x55c7dc0495e1 in v8::internal::Runtime_RunMicrotaskCallback(int, unsigned long*, v8::internal::Isolate*) src/runtime/runtime-promise.cc:83:1
    #3 0x55c7dfd35035 in Builtins_CEntry_Return1_ArgvOnStack_NoBuiltinExit setup-isolate-deserialize.cc
    #4 0x55c7dfcb81d7 in Builtins_RunMicrotasks setup-isolate-deserialize.cc
    #5 0x55c7dfc844aa in Builtins_JSRunMicrotasksEntry setup-isolate-deserialize.cc
    #6 0x55c7daadf678 in Call src/execution/simulator.h:212:12
    #7 0x55c7daadf678 in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:460:41
    #8 0x55c7daae3180 in v8::internal::(anonymous namespace)::InvokeWithTryCatch(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:502:18
    #9 0x55c7daae360b in v8::internal::Execution::TryRunMicrotasks(v8::internal::Isolate*, v8::internal::MicrotaskQueue*) src/execution/execution.cc:606:10
    #10 0x55c7dabd3e55 in v8::internal::MicrotaskQueue::RunMicrotasks(v8::internal::Isolate*) src/execution/microtask-queue.cc:185:22
    #11 0x55c7dabd3645 in v8::internal::MicrotaskQueue::PerformCheckpointInternal(v8::Isolate*) src/execution/microtask-queue.cc:129:3
    #12 0x55c7dab4dbf1 in PerformCheckpoint src/execution/microtask-queue.h:48:5
    #13 0x55c7dab4dbf1 in v8::internal::Isolate::FireCallCompletedCallbackInternal(v8::internal::MicrotaskQueue*) src/execution/isolate.cc:6533:44
    #14 0x55c7da66aa19 in FireCallCompletedCallback src/execution/isolate.h:1777:5
    #15 0x55c7da66aa19 in ~CallDepthScope src/api/api-inl.h:183:32
    #16 0x55c7da66aa19 in ~EnterV8InternalScope src/api/api-inl.h:259:20
    #17 0x55c7da66aa19 in v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) src/api/api.cc:1938:1
    #18 0x55c7da265ea0 in v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) src/d8/d8.cc:1033:44
    #19 0x55c7da2a7237 in v8::SourceGroup::Execute(v8::Isolate*) src/d8/d8.cc:5351:10
    #20 0x55c7da2b5768 in v8::Shell::RunMainIsolate(v8::Isolate*, bool) src/d8/d8.cc:6307:37
    #21 0x55c7da2b498e in v8::Shell::RunMain(v8::Isolate*, bool) src/d8/d8.cc:6215:18
    #22 0x55c7da2b99a9 in v8::Shell::Main(int, char**) src/d8/d8.cc:7100:18
    #23 0x7f6b8900cd79 in __libc_start_main csu/../csu/libc-start.c:308:16

0x7bcb882e2120 is located 0 bytes inside of 56-byte region [0x7bcb882e2120,0x7bcb882e2158)
freed by thread T0 here:
    #0 0x55c7da22a2d2 in operator delete(void*, unsigned long) (/home/user/v8_build/v8/out/release_asan_debug/d8+0x13c32d2) (BuildId: a18194e66e0b05f8)
    #1 0x55c7da2713d0 in v8::Shell::DoHostImportModuleDynamically(void*) src/d8/d8.cc:1695:11
    #2 0x55c7dc0495e1 in __RT_impl_Runtime_RunMicrotaskCallback src/runtime/runtime-promise.cc:93:3
    #3 0x55c7dc0495e1 in v8::internal::Runtime_RunMicrotaskCallback(int, unsigned long*, v8::internal::Isolate*) src/runtime/runtime-promise.cc:83:1
    #4 0x55c7dfd35035 in Builtins_CEntry_Return1_ArgvOnStack_NoBuiltinExit setup-isolate-deserialize.cc
    #5 0x55c7dfcb81d7 in Builtins_RunMicrotasks setup-isolate-deserialize.cc
    #6 0x55c7dfc844aa in Builtins_JSRunMicrotasksEntry setup-isolate-deserialize.cc
    #7 0x55c7daadf678 in Call src/execution/simulator.h:212:12
    #8 0x55c7daadf678 in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:460:41
    #9 0x55c7daae3180 in v8::internal::(anonymous namespace)::InvokeWithTryCatch(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:502:18
    #10 0x55c7daae360b in v8::internal::Execution::TryRunMicrotasks(v8::internal::Isolate*, v8::internal::MicrotaskQueue*) src/execution/execution.cc:606:10
    #11 0x55c7dabd3e55 in v8::internal::MicrotaskQueue::RunMicrotasks(v8::internal::Isolate*) src/execution/microtask-queue.cc:185:22
    #12 0x55c7dabd3645 in v8::internal::MicrotaskQueue::PerformCheckpointInternal(v8::Isolate*) src/execution/microtask-queue.cc:129:3
    #13 0x55c7dab4dbf1 in PerformCheckpoint src/execution/microtask-queue.h:48:5
    #14 0x55c7dab4dbf1 in v8::internal::Isolate::FireCallCompletedCallbackInternal(v8::internal::MicrotaskQueue*) src/execution/isolate.cc:6533:44
    #15 0x55c7da66aa19 in FireCallCompletedCallback src/execution/isolate.h:1777:5
    #16 0x55c7da66aa19 in ~CallDepthScope src/api/api-inl.h:183:32
    #17 0x55c7da66aa19 in ~EnterV8InternalScope src/api/api-inl.h:259:20
    #18 0x55c7da66aa19 in v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) src/api/api.cc:1938:1
    #19 0x55c7da265ea0 in v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) src/d8/d8.cc:1033:44
    #20 0x55c7da2a7237 in v8::SourceGroup::Execute(v8::Isolate*) src/d8/d8.cc:5351:10
    #21 0x55c7da2b5768 in v8::Shell::RunMainIsolate(v8::Isolate*, bool) src/d8/d8.cc:6307:37
    #22 0x55c7da2b498e in v8::Shell::RunMain(v8::Isolate*, bool) src/d8/d8.cc:6215:18
    #23 0x55c7da2b99a9 in v8::Shell::Main(int, char**) src/d8/d8.cc:7100:18
    #24 0x7f6b8900cd79 in __libc_start_main csu/../csu/libc-start.c:308:16

previously allocated by thread T0 here:
    #0 0x55c7da22966d in operator new(unsigned long) (/home/user/v8_build/v8/out/release_asan_debug/d8+0x13c266d) (BuildId: a18194e66e0b05f8)
    #1 0x55c7da2705fa in v8::Shell::HostImportModuleWithPhaseDynamically(v8::Local<v8::Context>, v8::Local<v8::Data>, v8::Local<v8::Value>, v8::Local<v8::String>, v8::ModuleImportPhase, v8::Local<v8::FixedArray>) src/d8/d8.cc:1573:9
    #2 0x55c7dab4e872 in v8::internal::Isolate::RunHostImportModuleDynamicallyCallback(v8::internal::MaybeDirectHandle<v8::internal::Script>, v8::internal::Handle<v8::internal::Object>, v8::ModuleImportPhase, v8::internal::MaybeDirectHandle<v8::internal::Object>) src/execution/isolate.cc:6667:9
    #3 0x55c7dc062bcf in __RT_impl_Runtime_DynamicImportCall src/runtime/runtime-module.cc:28:3
    #4 0x55c7dc062bcf in v8::internal::Runtime_DynamicImportCall(int, unsigned long*, v8::internal::Isolate*) src/runtime/runtime-module.cc:12:1
    #5 0x55c7dfd34eb0 in Builtins_CEntry_Return1_ArgvInRegister_NoBuiltinExit setup-isolate-deserialize.cc
    #6 0x55c7dfe3d647 in Builtins_CallRuntimeHandler setup-isolate-deserialize.cc
    #7 0x55c7dfc87934 in Builtins_InterpreterEntryTrampoline setup-isolate-deserialize.cc
    #8 0x55c7dfc87934 in Builtins_InterpreterEntryTrampoline setup-isolate-deserialize.cc
    #9 0x55c7dfc8455b in Builtins_JSEntryTrampoline setup-isolate-deserialize.cc
    #10 0x55c7dfc842aa in Builtins_JSEntry setup-isolate-deserialize.cc
    #11 0x55c7daadfe3d in Call src/execution/simulator.h:212:12
    #12 0x55c7daadfe3d in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:442:22
    #13 0x55c7daae2748 in v8::internal::Execution::CallScript(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>) src/execution/execution.cc:542:10
    #14 0x55c7da66a6e7 in v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) src/api/api.cc:1937:7
    #15 0x55c7da265ea0 in v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) src/d8/d8.cc:1033:44
    #16 0x55c7da2a7237 in v8::SourceGroup::Execute(v8::Isolate*) src/d8/d8.cc:5351:10
    #17 0x55c7da2b5768 in v8::Shell::RunMainIsolate(v8::Isolate*, bool) src/d8/d8.cc:6307:37
    #18 0x55c7da2b498e in v8::Shell::RunMain(v8::Isolate*, bool) src/d8/d8.cc:6215:18
    #19 0x55c7da2b99a9 in v8::Shell::Main(int, char**) src/d8/d8.cc:7100:18
    #20 0x7f6b8900cd79 in __libc_start_main csu/../csu/libc-start.c:308:16

SUMMARY: AddressSanitizer: heap-use-after-free src/d8/d8.cc:1672:34 in v8::Shell::DoHostImportModuleDynamically(void*)
Shadow bytes around the buggy address:
  0x7bcb882e1e80: 00 00 00 00 00 00 07 fa fa fa fa fa 00 00 00 00
  0x7bcb882e1f00: 00 00 00 00 fa fa fa fa fd fd fd fd fd fd fd fd
  0x7bcb882e1f80: fa fa fa fa fd fd fd fd fd fd fd fa fa fa fa fa
  0x7bcb882e2000: 00 00 00 00 00 00 00 fa fa fa fa fa 00 00 00 00
  0x7bcb882e2080: 00 00 00 fa fa fa fa fa 00 00 00 00 00 00 00 00
=>0x7bcb882e2100: fa fa fa fa[fd]fd fd fd fd fd fd fa fa fa fa fa
  0x7bcb882e2180: 00 00 00 00 00 00 00 00 fa fa fa fa fa fa fa fa
  0x7bcb882e2200: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x7bcb882e2280: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x7bcb882e2300: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x7bcb882e2380: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
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
==1921301==ABORTING

## V8 sandbox violation detected!
```

CREDIT INFORMATION

Reporter credit: Picasso


---

**#2 — cl...@appspot.gserviceaccount.com — Sep 5, 2025 06:13AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5643360811286528](<https://clusterfuzz.com/testcase?key=5643360811286528>).


---

**#3 — nh...@chromium.org — Sep 5, 2025 06:36AM**

[pawkra@google.com](<mailto:pawkra@google.com>), I'm triaging this as a V8 Sandbox bypass with a provisional severity and priority. If this is not a V8 Sandbox bypass and is instead a V8 bug, please remove the Security_Impact-None label.


---

**#4 — pa...@google.com — Sep 5, 2025 08:25PM**

I'm leaving the Security_Impact-None since this occurs only in debug build.

CYPTAL [nikolaos@chromium.org](<mailto:nikolaos@chromium.org>)

Last change in `DoHostImportModuleDynamically` function: [https://chromium-review.googlesource.com/c/v8/v8/+/5258097](<https://chromium-review.googlesource.com/c/v8/v8/+/5258097>)


---

**#5 — ni...@chromium.org — Sep 5, 2025 09:52PM**

This does not occur in debug builds, it's a UAF in d8-specific code.  
It seems that the entire issue is d8-specific.  
The abused object is of type `DynamicImportData` [1](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/d8/d8.cc;drc=e3ad182cacc3a02eb6a13091a867815fd17a129c;l=1468>), allocated [2](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/d8/d8.cc;drc=e3ad182cacc3a02eb6a13091a867815fd17a129c;l=1575>), freed [3](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/d8/d8.cc;drc=e3ad182cacc3a02eb6a13091a867815fd17a129c;l=2021>) and used [4](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/d8/d8.cc;drc=e3ad182cacc3a02eb6a13091a867815fd17a129c;l=1675>) inside d8.

As such, I think it should not be considered a vulnerability.


---

**#6 — dx...@google.com — Sep 8, 2025 09:36PM**

Project: v8/v8  
Branch: main  
Author: Nikolaos Papaspyrou [nikolaos@chromium.org](<mailto:nikolaos@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6917687](<https://chromium-review.googlesource.com/6917687>)

[d8] Guard against DynamicImportData abuses

* * *

Expand for full commit details

```
     
    This CL fixes a UAF in d8 that can occur with --sandbox-fuzzing, by 
    setting the same DynamicImportData object for two different imported 
    modules. 
     
    Bug: 442981541 
    Change-Id: Ifb2a42777d9ae58e2393b033543a06c4e3ebae88 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6917687 
    Reviewed-by: Michael Lippautz <mlippautz@chromium.org> 
    Commit-Queue: Nikolaos Papaspyrou <nikolaos@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#102321}
```

* * *

Files:

  * M `src/d8/d8.cc`
  * M `src/d8/d8.h`
  * A `test/mjsunit/sandbox/regress-442981541.js`

* * *

Hash: [2388032b518d067b8d5bbc4313c3c7d595f10e90](<https://chromiumdash.appspot.com/commit/2388032b518d067b8d5bbc4313c3c7d595f10e90>)  
Date: Fri Sep 5 16:19:18 2025

* * *


---

**#7 — ni...@chromium.org — Sep 8, 2025 09:51PM**

This should be fixed by the above.


---

**#8 — pi...@gmail.com — Sep 23, 2025 10:37PM**

Hello, I want to know if this bug is qualified for a VRP reward. Thanks.


---

**#9 — ch...@google.com — Dec 16, 2025 09:44PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
