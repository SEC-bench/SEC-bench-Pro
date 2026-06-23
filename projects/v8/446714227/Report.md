# V8 Sandbox Bypass: OOB write in maglev::VirtualObject::set

Issue URL: https://issues.chromium.org/issues/446714227
VRP-Reward: CRN
Date: Sep 23, 2025 06:11PM


#### VULNERABILITY DETAILS

Concurrently modifying the instance size of an Array map triggers an OOB write when maglev is constructing the IR graph. The mutated value is read here:

```
#7  0x000055555c98da6a in v8::internal::Map::instance_size_in_words (this=<optimized out>) at ../../src/objects/map-inl.h:289
#8  0x000055555d1299f4 in v8::internal::Map::GetInObjectProperties (this=<optimized out>) at ../../src/objects/map-inl.h:343
#9  0x0000555562a4d5bb in v8::internal::compiler::MapData::MapData (this=<optimized out>, broker=<optimized out>, storage=<optimized out>, object=..., kind=<optimized out>) at ./../../src/compiler/heap-refs.cc:913
#10 0x0000555562a5e113 in v8::internal::Zone::New<v8::internal::compiler::MapData, v8::internal::compiler::JSHeapBroker*, v8::internal::compiler::ObjectData**, v8::internal::Handle<v8::internal::Map>, v8::internal::compiler::ObjectDataKind> (
    this=<optimized out>, args=<optimized out>, args=<optimized out>, args=<optimized out>, args=<optimized out>) at ../../src/zone/zone.h:111
#11 0x0000555562a45468 in v8::internal::compiler::JSHeapBroker::TryGetOrCreateData (this=<optimized out>, object=..., flags=...) at ./../../src/compiler/heap-refs.cc:1097
#12 0x0000555562ad0f96 in v8::internal::compiler::JSHeapBroker::GetOrCreateData (this=<optimized out>, object=..., flags=...) at ./../../src/compiler/js-heap-broker.cc:146
#13 0x0000555562a3eb6f in v8::internal::compiler::HeapObjectData::HeapObjectData (this=<optimized out>, broker=<optimized out>, storage=<optimized out>, object=..., kind=<optimized out>) at ./../../src/compiler/heap-refs.cc:791
#14 0x0000555562a5b453 in v8::internal::Zone::New<v8::internal::compiler::JSArrayData, v8::internal::compiler::JSHeapBroker*, v8::internal::compiler::ObjectData**, v8::internal::Handle<v8::internal::JSArray>, v8::internal::compiler::ObjectDataKind> (
    this=<optimized out>, args=<optimized out>, args=<optimized out>, args=<optimized out>, args=<optimized out>) at ../../src/zone/zone.h:111
#15 0x0000555562a4151f in v8::internal::compiler::JSHeapBroker::TryGetOrCreateData (this=<optimized out>, object=..., flags=...) at ./../../src/compiler/heap-refs.cc:1097
#16 0x0000555562aa96a2 in v8::internal::compiler::TryMakeRef<v8::internal::JSObject>(v8::internal::compiler::JSHeapBroker*, v8::internal::Tagged<v8::internal::JSObject>, v8::base::Flags<v8::internal::compiler::GetOrCreateDataFlag, int, int>) requires is_subtype_v<v8::internal::JSObject, v8::internal::Object> (broker=<optimized out>, object=..., flags=...) at ../../src/compiler/js-heap-broker.h:603
#17 0x0000555562aa949b in v8::internal::compiler::AllocationSiteRef::boilerplate (this=<optimized out>, broker=<optimized out>) at ./../../src/compiler/heap-refs.cc:2302
#18 0x00005555609f62f3 in v8::internal::maglev::MaglevGraphBuilder::TryBuildFastCreateObjectOrArrayLiteral (this=<optimized out>, feedback=...) at ./../../src/maglev/maglev-graph-builder.cc:14038
#19 0x00005555609f5e9e in v8::internal::maglev::MaglevGraphBuilder::VisitCreateArrayLiteral (this=<optimized out>) at ./../../src/maglev/maglev-graph-builder.cc:13095
#20 0x000055556096dbaa in v8::internal::maglev::MaglevGraphBuilder::VisitSingleBytecode (this=<optimized out>) at ./../../src/maglev/maglev-graph-builder.cc:16185
#21 0x000055556099365e in v8::internal::maglev::MaglevGraphBuilder::BuildBody (this=<optimized out>) at ./../../src/maglev/maglev-graph-builder.cc:15777
#22 0x0000555560a1b1c8 in v8::internal::maglev::MaglevGraphBuilder::Build (this=<optimized out>) at ./../../src/maglev/maglev-graph-builder.cc:15756
#23 0x000055555ff5e3c9 in v8::internal::maglev::MaglevCompiler::Compile (local_isolate=<optimized out>, compilation_info=<optimized out>) at ./../../src/maglev/maglev-compiler.cc:104
#24 0x000055555ff48902 in v8::internal::maglev::MaglevCompilationJob::ExecuteJobImpl (this=<optimized out>, stats=<optimized out>, local_isolate=<optimized out>) at ./../../src/maglev/maglev-concurrent-dispatcher.cc:132
#25 0x000055555d42c936 in v8::internal::OptimizedCompilationJob::ExecuteJob (this=<optimized out>, stats=<optimized out>, local_isolate=<optimized out>) at ./../../src/codegen/compiler.cc:451
#26 0x000055555d491a75 in v8::internal::(anonymous namespace)::CompileMaglev (isolate=<optimized out>, function=..., mode=<optimized out>, osr_offset=..., result_behavior=<optimized out>) at ./../../src/codegen/compiler.cc:1302
#27 0x000055555d4511d9 in v8::internal::(anonymous namespace)::GetOrCompileOptimized (isolate=<optimized out>, function=..., mode=<optimized out>, code_kind=<optimized out>, osr_offset=..., result_behavior=<optimized out>)
    at ./../../src/codegen/compiler.cc:1404
#28 0x000055555d44fdcf in v8::internal::Compiler::CompileOptimized (isolate=<optimized out>, function=..., mode=<optimized out>, code_kind=<optimized out>) at ./../../src/codegen/compiler.cc:3175
#29 0x000055555f9d312f in v8::internal::(anonymous namespace)::CompileOptimized (function=..., mode=<optimized out>, target_kind=<optimized out>, isolate=<optimized out>) at ./../../src/runtime/runtime-compiler.cc:185
#30 0x000055555f9bec5a in v8::internal::__RT_impl_Runtime_OptimizeMaglevEager (args=..., isolate=<optimized out>) at ./../../src/runtime/runtime-compiler.cc:217
#31 v8::internal::Runtime_OptimizeMaglevEager (args_length=<optimized out>, args_object=<optimized out>, isolate=<optimized out>) at ./../../src/runtime/runtime-compiler.cc:212
#32 0x0000555566c7320d in Builtins_CEntry_Return1_ArgvOnStack_NoBuiltinExit ()
#33 0x0000555566915c22 in Builtins_OptimizeMaglevEager ()
```

#### VERSION

V8 Git Commit: 51c277a84683b54a8ca62c6388849616f307a46c (Mon Sep 22 17:45:13 2025 +0200)

#### REPRODUCTION CASE

The test case may require multiple tries to trigger.

```
d8 --fuzzing --sandbox-fuzzing --allow-natives-syntax --expose-gc  --jit-fuzzing --single-threaded bug.js
```

**ASan Report**

```
Sandbox bounds: [0x7abe00000000,0x7bbe00000000)
=================================================================
==2879338==ERROR: AddressSanitizer: use-after-poison on address 0x7e8ff746afc0 at pc 0x555558978977 bp 0x7fffffffcba0 sp 0x7fffffffcb98
WRITE of size 8 at 0x7e8ff746afc0 thread T0
    #0 0x555558978976 in v8::internal::maglev::VirtualObject::set(unsigned int, v8::internal::maglev::ValueNode*) src/maglev/maglev-ir.h:6451:57
    #1 0x5555589faa91 in v8::internal::maglev::MaglevGraphBuilder::TryReadBoilerplateForFastLiteral(v8::internal::compiler::JSObjectRef, v8::internal::AllocationType, int, int*) src/maglev/maglev-graph-builder.cc:13288:19
    #2 0x5555589f95f4 in v8::internal::maglev::MaglevGraphBuilder::TryBuildFastCreateObjectOrArrayLiteral(v8::internal::compiler::LiteralFeedback const&) src/maglev/maglev-graph-builder.cc:14045:47
    #3 0x5555589f8f8c in v8::internal::maglev::MaglevGraphBuilder::VisitCreateArrayLiteral() src/maglev/maglev-graph-builder.cc:13095:7
    #4 0x555558988971 in v8::internal::maglev::MaglevGraphBuilder::VisitSingleBytecode() src/maglev/maglev-graph-builder.cc:16185:5
    #5 0x5555589ae1c8 in v8::internal::maglev::MaglevGraphBuilder::BuildBody() src/maglev/maglev-graph-builder.cc:15777:9
    #6 0x555558a1cace in v8::internal::maglev::MaglevGraphBuilder::Build() src/maglev/maglev-graph-builder.cc:15756:3
    #7 0x5555584cf7c8 in v8::internal::maglev::MaglevCompiler::Compile(v8::internal::LocalIsolate*, v8::internal::maglev::MaglevCompilationInfo*) src/maglev/maglev-compiler.cc:104:26
    #8 0x5555584c58d8 in v8::internal::maglev::MaglevCompilationJob::ExecuteJobImpl(v8::internal::RuntimeCallStats*, v8::internal::LocalIsolate*) src/maglev/maglev-concurrent-dispatcher.cc:132:8
    #9 0x555556eb2deb in ExecuteJob src/codegen/compiler.cc:451:22
    #10 0x555556eb2deb in v8::internal::(anonymous namespace)::CompileMaglev(v8::internal::Isolate*, v8::internal::Handle<v8::internal::JSFunction>, v8::internal::ConcurrencyMode, v8::internal::BytecodeOffset, v8::internal::(anonymous namespace)::CompileResultBehavior) src/codegen/compiler.cc:1302:14
    #11 0x555556e9ad0b in v8::internal::(anonymous namespace)::GetOrCompileOptimized(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::ConcurrencyMode, v8::internal::CodeKind, v8::internal::BytecodeOffset, v8::internal::(anonymous namespace)::CompileResultBehavior) src/codegen/compiler.cc:1404:12
    #12 0x555556e9994a in v8::internal::Compiler::CompileOptimized(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::ConcurrencyMode, v8::internal::CodeKind) src/codegen/compiler.cc:3175:7
    #13 0x5555581c5d5b in v8::internal::(anonymous namespace)::CompileOptimized(v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::ConcurrencyMode, v8::internal::CodeKind, v8::internal::Isolate*) src/runtime/runtime-compiler.cc:185:3
    #14 0x5555581b874a in __RT_impl_Runtime_OptimizeMaglevEager src/runtime/runtime-compiler.cc:217:3
    #15 0x5555581b874a in v8::internal::Runtime_OptimizeMaglevEager(int, unsigned long*, v8::internal::Isolate*) src/runtime/runtime-compiler.cc:212:1
    #16 0x55555b939b75 in Builtins_CEntry_Return1_ArgvOnStack_NoBuiltinExit setup-isolate-deserialize.cc
    #17 0x55555b88ff41 in Builtins_OptimizeMaglevEager setup-isolate-deserialize.cc
    #18 0x5555bb88bc89  (<unknown module>)
    #19 0x55555b88b55b in Builtins_JSEntryTrampoline setup-isolate-deserialize.cc
    #20 0x55555b88b2aa in Builtins_JSEntry setup-isolate-deserialize.cc
    #21 0x555557056072 in Call src/execution/simulator.h:212:12
    #22 0x555557056072 in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:442:22
    #23 0x5555570575f8 in v8::internal::Execution::CallScript(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>) src/execution/execution.cc:542:10
    #24 0x555556cd78fd in v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) src/api/api.cc:1955:7
    #25 0x555556928ad6 in v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) src/d8/d8.cc:1036:44
    #26 0x55555696094d in v8::SourceGroup::Execute(v8::Isolate*) src/d8/d8.cc:5487:10
    #27 0x55555696c743 in v8::Shell::RunMainIsolate(v8::Isolate*, bool) src/d8/d8.cc:6443:37
    #28 0x55555696bb75 in v8::Shell::RunMain(v8::Isolate*, bool) src/d8/d8.cc:6351:18
    #29 0x55555696f27c in v8::Shell::Main(int, char**) src/d8/d8.cc:7241:18
    #30 0x7ffff7c8f1c9 in __libc_start_call_main csu/../sysdeps/nptl/libc_start_call_main.h:58:16
    #31 0x7ffff7c8f28a in __libc_start_main csu/../csu/libc-start.c:360:3
    #32 0x55555681b029 in _start (v8/out/vanilla/d8+0x12c7029) (BuildId: a5fc47c21b51396e)

0x7e8ff746afc0 is located 7616 bytes inside of 16480-byte region [0x7e8ff7469200,0x7e8ff746d260)
allocated by thread T0 here:
    #0 0x5555568bcdb4 in malloc (v8/out/vanilla/d8+0x1368db4) (BuildId: a5fc47c21b51396e)
    #1 0x555558382051 in Malloc src/base/platform/memory.h:44:10
    #2 0x555558382051 in AllocateAtLeast<char> src/base/platform/memory.h:146:34
    #3 0x555558382051 in v8::internal::AllocAtLeastWithRetry(unsigned long) src/utils/allocation.cc:138:14
    #4 0x55555838d02d in v8::internal::AccountingAllocator::AllocateSegment(unsigned long) src/zone/accounting-allocator.cc:101:14
    #5 0x55555838dd23 in v8::internal::Zone::Expand(unsigned long) src/zone/zone.cc:178:34
    #6 0x55555838dbfa in v8::internal::Zone::AsanNew(unsigned long) src/zone/zone.cc:52:5
    #7 0x555559960b9f in UpdateLiveness<true> src/compiler/bytecode-analysis.cc:414:5
    #8 0x555559960b9f in v8::internal::compiler::BytecodeAnalysis::BytecodeAnalysisImpl::Analyze() src/compiler/bytecode-analysis.cc:680:7
    #9 0x555559979bdb in v8::internal::compiler::BytecodeAnalysis::BytecodeAnalysis(v8::internal::Handle<v8::internal::BytecodeArray>, v8::internal::Zone*, v8::internal::BytecodeOffset, bool) src/compiler/bytecode-analysis.cc:1191:12
    #10 0x55555894ff08 in v8::internal::maglev::MaglevGraphBuilder::MaglevGraphBuilder(v8::internal::LocalIsolate*, v8::internal::maglev::MaglevCompilationUnit*, v8::internal::maglev::Graph*, v8::internal::maglev::MaglevCallerDetails*) src/maglev/maglev-graph-builder.cc:1121:7
    #11 0x5555584cf7c0 in v8::internal::maglev::MaglevCompiler::Compile(v8::internal::LocalIsolate*, v8::internal::maglev::MaglevCompilationInfo*) src/maglev/maglev-compiler.cc:102:26
    #12 0x5555584c58d8 in v8::internal::maglev::MaglevCompilationJob::ExecuteJobImpl(v8::internal::RuntimeCallStats*, v8::internal::LocalIsolate*) src/maglev/maglev-concurrent-dispatcher.cc:132:8
    #13 0x555556eb2deb in ExecuteJob src/codegen/compiler.cc:451:22
    #14 0x555556eb2deb in v8::internal::(anonymous namespace)::CompileMaglev(v8::internal::Isolate*, v8::internal::Handle<v8::internal::JSFunction>, v8::internal::ConcurrencyMode, v8::internal::BytecodeOffset, v8::internal::(anonymous namespace)::CompileResultBehavior) src/codegen/compiler.cc:1302:14
    #15 0x555556e9ad0b in v8::internal::(anonymous namespace)::GetOrCompileOptimized(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::ConcurrencyMode, v8::internal::CodeKind, v8::internal::BytecodeOffset, v8::internal::(anonymous namespace)::CompileResultBehavior) src/codegen/compiler.cc:1404:12
    #16 0x555556e9994a in v8::internal::Compiler::CompileOptimized(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::ConcurrencyMode, v8::internal::CodeKind) src/codegen/compiler.cc:3175:7
    #17 0x5555581c5d5b in v8::internal::(anonymous namespace)::CompileOptimized(v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::ConcurrencyMode, v8::internal::CodeKind, v8::internal::Isolate*) src/runtime/runtime-compiler.cc:185:3
    #18 0x5555581b874a in __RT_impl_Runtime_OptimizeMaglevEager src/runtime/runtime-compiler.cc:217:3
    #19 0x5555581b874a in v8::internal::Runtime_OptimizeMaglevEager(int, unsigned long*, v8::internal::Isolate*) src/runtime/runtime-compiler.cc:212:1
    #20 0x55555b939b75 in Builtins_CEntry_Return1_ArgvOnStack_NoBuiltinExit setup-isolate-deserialize.cc
    #21 0x55555b88ff41 in Builtins_OptimizeMaglevEager setup-isolate-deserialize.cc
    #22 0x5555bb88bc89  (<unknown module>)
    #23 0x55555b88b55b in Builtins_JSEntryTrampoline setup-isolate-deserialize.cc
    #24 0x55555b88b2aa in Builtins_JSEntry setup-isolate-deserialize.cc
    #25 0x555557056072 in Call src/execution/simulator.h:212:12
    #26 0x555557056072 in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:442:22
    #27 0x5555570575f8 in v8::internal::Execution::CallScript(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>) src/execution/execution.cc:542:10
    #28 0x555556cd78fd in v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) src/api/api.cc:1955:7
    #29 0x555556928ad6 in v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) src/d8/d8.cc:1036:44
    #30 0x55555696094d in v8::SourceGroup::Execute(v8::Isolate*) src/d8/d8.cc:5487:10
    #31 0x55555696c743 in v8::Shell::RunMainIsolate(v8::Isolate*, bool) src/d8/d8.cc:6443:37
    #32 0x55555696bb75 in v8::Shell::RunMain(v8::Isolate*, bool) src/d8/d8.cc:6351:18
    #33 0x55555696f27c in v8::Shell::Main(int, char**) src/d8/d8.cc:7241:18
    #34 0x7ffff7c8f1c9 in __libc_start_call_main csu/../sysdeps/nptl/libc_start_call_main.h:58:16
    #35 0x7ffff7c8f28a in __libc_start_main csu/../csu/libc-start.c:360:3

SUMMARY: AddressSanitizer: use-after-poison src/maglev/maglev-ir.h:6451:57 in v8::internal::maglev::VirtualObject::set(unsigned int, v8::internal::maglev::ValueNode*)
Shadow bytes around the buggy address:
  0x7e8ff746ad00: f7 f7 f7 00 00 00 f7 f7 f7 00 00 f7 f7 f7 00 00
  0x7e8ff746ad80: 00 00 f7 f7 f7 00 00 f7 f7 f7 00 00 00 00 00 f7
  0x7e8ff746ae00: f7 f7 00 00 00 f7 f7 f7 00 00 00 00 00 f7 f7 f7
  0x7e8ff746ae80: 00 00 f7 f7 f7 00 00 00 00 f7 f7 f7 00 00 00 00
  0x7e8ff746af00: 00 00 f7 f7 f7 00 00 00 00 00 00 00 00 00 00 00
=>0x7e8ff746af80: 00 f7 f7 f7 00 00 00 00[f7]f7 f7 00 00 00 f7 f7
  0x7e8ff746b000: f7 00 00 00 00 00 00 f7 f7 f7 00 00 00 00 f7 f7
  0x7e8ff746b080: f7 00 00 00 00 00 00 f7 f7 f7 00 00 00 f7 f7 f7
  0x7e8ff746b100: 00 00 00 00 00 00 f7 f7 f7 00 00 00 00 00 00 00
  0x7e8ff746b180: 00 00 00 00 00 f7 f7 f7 00 00 00 00 00 00 00 00
  0x7e8ff746b200: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
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

NOTE: the stack trace above identifies the code that *accessed* the poisoned memory.
To identify the code that *poisoned* the memory, try the experimental setting ASAN_OPTIONS=poison_history_size=<size>.
==2879338==ABORTING

## V8 sandbox violation detected!
```


---

**#2 — vs...@gmail.com — Sep 23, 2025 06:30PM**

gn args:

```
v8_enable_partition_alloc = false
is_debug = false
dcheck_always_on = false
is_asan = true
v8_enable_sandbox = true
v8_enable_memory_corruption_api = true
v8_static_library = true
target_cpu = "x64"
```


---

**#3 — wf...@chromium.org — Sep 24, 2025 01:23AM**

Ty for your report. Setting a provisional severity of Medium and provisional priority of P1 and Sec Impact None.


---

**#4 — is...@chromium.org — Oct 7, 2025 02:04AM**

Assigning to mlippautz@ until we find a better owner for this class of issues.


---

**#5 — jg...@chromium.org — Oct 7, 2025 07:29PM**

This was already fixed and merged to 142. See [https://chromium-review.googlesource.com/c/v8/v8/+/6993031](<https://chromium-review.googlesource.com/c/v8/v8/+/6993031>), relevant bug: [https://issues.chromium.org/issues/447693720](<https://issues.chromium.org/issues/447693720>).


---

**#6 — ml...@chromium.org — Oct 7, 2025 07:32PM**

Thanks for the help here!

Okay, [issue 447693720](<https://issues.chromium.org/issues/447693720>) was filed after this one. I will not merge the bugs but merely mark them as fixed and set the relevant code change.


---

**#7 — vs...@gmail.com — Nov 5, 2025 09:27PM**

Will this be considered by the VRP panel? As far as I understand, the colliding issue was reported after this one?


---

**#8 — ch...@google.com — Nov 5, 2025 09:42PM**

This V8 bug has been marked as either a release blocker or a vulnerability bug. V8 bugs affect all OSs supported by Chrome, so the OS field has been updated to reflect this. Please update the bug with the correct OS field if it only affects a subset of OSes.


---

**#9 — wf...@chromium.org — Nov 14, 2025 02:52AM**

Thank you for your report but this was determined by the panel to be churn at head revision. See the rules which state "Reports for issues resulting from newly landed commits on head that are seven (7) or fewer days old are not likely to be eligible for a VRP reward. ", so the panel declined to reward.


---

**#10 — ch...@google.com — Jan 14, 2026 09:47PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
