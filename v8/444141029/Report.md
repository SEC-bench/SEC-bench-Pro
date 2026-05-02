# 444141029

Issue URL: https://issuetracker.google.com/issues/444141029
VRP-Reward: INT
Date: Sep 10, 2025 05:46PM


_Publishing the original report in line with the disclosure policy._

* * *

We are tracking this issue with the public ID BIGSLEEP-444141029. Please use this identifier for reference in any future communication.

# Vulnerability Details

The Maglev compiler represents computation nodes using classes derived from `maglev::NodeBase` [1]. This class uses a 16 bit bitfield to store the number of input values it receives [2]. When encoding this bitfield [3] there is no check that the number fits into 16 bit, potentially allowing for integer truncation issues.

One place where this can happen in practice is in the `GeneratorStore` operation [4], which requires one input for each local variable that needs to be stored in the generator state [5]. As such, if a sufficiently large generator function is compiled, this will lead to an integer truncation issue as demonstrated by the testcase below. In debug builds, the testcase will lead to a DCHECK failure when setting the bitfield value (`"Debug check failed: is_valid(value)"` in bit-field.h). In release builds, the issue leads to a mismatch between the input count stored in the node and the actual number of values flowing into this node. This mismatch can lead to other issues later on during compilation. Specifically, it appears that it can lead to memory corruption during register allocation, as can be seen in the attached ASan report.

[1] [https://source.chromium.org/chromium/chromium/src/+/main:v8/src/maglev/maglev-ir.h;l=2276;drc=c049b3c5fea34a05e9cc0b15e896cddc85f6a98a](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/maglev/maglev-ir.h;l=2276;drc=c049b3c5fea34a05e9cc0b15e896cddc85f6a98a>)   
[2] [https://source.chromium.org/chromium/chromium/src/+/main:v8/src/maglev/maglev-ir.h;l=2282;drc=c049b3c5fea34a05e9cc0b15e896cddc85f6a98a](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/maglev/maglev-ir.h;l=2282;drc=c049b3c5fea34a05e9cc0b15e896cddc85f6a98a>)   
[3] [https://source.chromium.org/chromium/chromium/src/+/main:v8/src/maglev/maglev-ir.h;l=2661;drc=c049b3c5fea34a05e9cc0b15e896cddc85f6a98a](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/maglev/maglev-ir.h;l=2661;drc=c049b3c5fea34a05e9cc0b15e896cddc85f6a98a>)   
[4] [https://source.chromium.org/chromium/chromium/src/+/main:v8/src/maglev/maglev-ir.h;l=5446;drc=c049b3c5fea34a05e9cc0b15e896cddc85f6a98a](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/maglev/maglev-ir.h;l=5446;drc=c049b3c5fea34a05e9cc0b15e896cddc85f6a98a>)   
[5] [https://source.chromium.org/chromium/chromium/src/+/main:v8/src/maglev/maglev-graph-builder.cc;l=15427;drc=c049b3c5fea34a05e9cc0b15e896cddc85f6a98a](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/maglev/maglev-graph-builder.cc;l=15427;drc=c049b3c5fea34a05e9cc0b15e896cddc85f6a98a>)

# Affected Version(s)

The issue has been successfully reproduced:

  * at HEAD (commit c049b3c5fea34a05e9cc0b15e896cddc85f6a98a)
  * in stable release 14.0.365.4 (commit fdb12b460f148895f6af2ff0e0d870ff8889f154)

# Reproduction

### Test Case

```
const kNumRegs = 65534;
let body = [];
for (let i = 0; i < kNumRegs; ++i) {
  body.push(`  let r${i} = ${i};`);
}
let f = eval(`(function*() {\n${body.join('\n')}})`);

%PrepareFunctionForOptimization(f);
f();
%OptimizeMaglevOnNextCall(f);
f();
```

### Build Instructions

Follow the instructions at [https://v8.dev/docs/build](<https://v8.dev/docs/build>). The crash was verified on a debug build and a release build with is_asan=true:

```
gm.py x64.debug
```

### Command

```
./out/x64.debug/d8 --allow-natives-syntax crash.js
```

### ASan Report

```
=================================================================                                                                                                                                                                                                                                                                                                                                                           14:34:11 [3/356]
==1397773==ERROR: AddressSanitizer: use-after-poison on address 0x7e7a0da4dc20 at pc 0x7fa9a604dffd bp 0x7ffdf8c0ba30 sp 0x7ffdf8c0ba28                                                                               
WRITE of size 8 at 0x7e7a0da4dc20 thread T0                                                                
    #0 0x7fa9a604dffc in v8::internal::maglev::GeneratorStore::SetValueLocationConstraints() src/maglev/maglev-regalloc-node-info.h:32:14                                                                             
    #1 0x7fa9a5bc5a1e in v8::internal::maglev::ProcessResult v8::internal::maglev::NodeMultiProcessor<v8::internal::maglev::DeadNodeSweepingProcessor, v8::internal::maglev::ValueLocationConstraintProcessor, v8::internal::maglev::MaxCallDepthProcessor, v8::internal::maglev::LiveRangeAndNextUseProcessor, v8::internal::maglev::DecompressedUseMarkingProcessor>::Process<v8::internal::maglev::GeneratorStore>(v8::internal::maglev::
GeneratorStore*, v8::internal::maglev::ProcessingState const&) src/maglev/maglev-pre-regalloc-codegen-processors.h:62:3                                                                                               
    #2 0x7fa9a5a4c7a6 in v8::internal::maglev::GraphProcessor<v8::internal::maglev::NodeMultiProcessor<v8::internal::maglev::DeadNodeSweepingProcessor, v8::internal::maglev::ValueLocationConstraintProcessor, v8::internal::maglev::MaxCallDepthProcessor, v8::internal::maglev::LiveRangeAndNextUseProcessor, v8::internal::maglev::DecompressedUseMarkingProcessor>>::ProcessGraph(v8::internal::maglev::Graph*) src/maglev/maglev-graph
-processor.h:184:32                                                                                                                                                                                                   
    #3 0x7fa9a5a46bae in v8::internal::maglev::MaglevCompiler::Compile(v8::internal::LocalIsolate*, v8::internal::maglev::MaglevCompilationInfo*) src/maglev/maglev-compiler.cc:190:17                                
    #4 0x7fa9a5caa838 in v8::internal::maglev::MaglevCompilationJob::ExecuteJobImpl(v8::internal::RuntimeCallStats*, v8::internal::LocalIsolate*) src/maglev/maglev-concurrent-dispatcher.cc:132:8                    
    #5 0x7fa9a4212a2b in v8::internal::(anonymous namespace)::CompileMaglev(v8::internal::Isolate*, v8::internal::Handle<v8::internal::JSFunction>, v8::internal::ConcurrencyMode, v8::internal::BytecodeOffset, v8::internal::(anonymous namespace)::CompileResultBehavior) src/codegen/compiler.cc:451:22
    #6 0x7fa9a41f9192 in v8::internal::(anonymous namespace)::GetOrCompileOptimized(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::ConcurrencyMode, v8::internal::CodeKind, v8::internal::BytecodeOffset, v8::internal::(anonymous namespace)::CompileResultBehavior) src/codegen/compiler.cc:1404:12
    #7 0x7fa9a41f7d5f in v8::internal::Compiler::CompileOptimized(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::ConcurrencyMode, v8::internal::CodeKind) src/codegen/compiler.cc:3175:7
    #8 0x7fa9a5578871 in v8::internal::(anonymous namespace)::CompileOptimized(v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::ConcurrencyMode, v8::internal::CodeKind, v8::internal::Isolate*) src/runtime/runtime-compiler.cc:185:3
    #9 0x7fa9a556b0ea in v8::internal::Runtime_OptimizeMaglevEager(int, unsigned long*, v8::internal::Isolate*) src/runtime/runtime-compiler.cc:217:3                                                                 
    #10 0x7fa9a3defcb5 in Builtins_CEntry_Return1_ArgvOnStack_NoBuiltinExit setup-isolate-deserialize.cc                                                                                                              
    #11 0x7fa9a3d39c01 in Builtins_OptimizeMaglevEager setup-isolate-deserialize.cc                        
    #12 0x7fa9a3d38429 in Builtins_InterpreterEntryTrampoline setup-isolate-deserialize.cc                 
    #13 0x7fa9a3d34d9b in Builtins_JSEntryTrampoline setup-isolate-deserialize.cc                          
    #14 0x7fa9a3d34aea in Builtins_JSEntry setup-isolate-deserialize.cc                                    
    #15 0x7fa9a4409596 in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/simulator.h:212:12                              
    #16 0x7fa9a440ab48 in v8::internal::Execution::CallScript(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>) src/execution/execution.cc:542:10
    #17 0x7fa9a3f6ac89 in v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) src/api/api.cc:1964:7                                                                                                          
    #18 0x56171d849507 in v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) src/d8/d8.cc:1036:44                              
    #19 0x56171d8840d3 in v8::SourceGroup::Execute(v8::Isolate*) src/d8/d8.cc:5498:10                      
    #20 0x56171d8908a4 in v8::Shell::RunMainIsolate(v8::Isolate*, bool) src/d8/d8.cc:6454:37               
    #21 0x56171d88fdc4 in v8::Shell::RunMain(v8::Isolate*, bool) src/d8/d8.cc:6362:18                      
    #22 0x56171d89330b in v8::Shell::Main(int, char**) src/d8/d8.cc:7252:18                                
    #23 0x7fa9a0633ca7 in __libc_start_call_main csu/../sysdeps/nptl/libc_start_call_main.h:58:16          
                                                                                                           
0x7e7a0da4dc20 is located 6176 bytes inside of 32768-byte region [0x7e7a0da4c400,0x7e7a0da54400)           
allocated by thread T0 here:                                                                               
    #0 0x56171d7dd4e4 in malloc (v8/v8/out/x64.asan/d8+0x1774e4) (BuildId: 32aafb03462a3d3f)                                                                                   
    #1 0x7fa9a58201e1 in v8::internal::AllocAtLeastWithRetry(unsigned long) src/base/platform/memory.h:44:10                                                                                                          
    #2 0x7fa9a582c11d in v8::internal::AccountingAllocator::AllocateSegment(unsigned long) src/zone/accounting-allocator.cc:101:14                                                                                    
    #3 0x7fa9a582d086 in v8::internal::Zone::Expand(unsigned long) src/zone/zone.cc:178:34                 
    #4 0x7fa9a582cf68 in v8::internal::Zone::AsanNew(unsigned long) src/zone/zone.cc:52:5                  
    #5 0x7fa9a60a52ac in std::__Cr::deque<v8::internal::compiler::turboshaft::SnapshotTable<v8::internal::maglev::ValueNode*, v8::internal::compiler::turboshaft::NoKeyData>::SnapshotData, v8::internal::RecyclingZoneAllocator<v8::internal::compiler::turboshaft::SnapshotTable<v8::internal::maglev::ValueNode*, v8::internal::compiler::turboshaft::NoKeyData>::SnapshotData>>::__add_back_capacity() src/zone/zone.h:57:12
    #6 0x7fa9a60a4bf4 in v8::internal::compiler::turboshaft::SnapshotTable<v8::internal::maglev::ValueNode*, v8::internal::compiler::turboshaft::NoKeyData>::SnapshotData& std::__Cr::deque<v8::internal::compiler::turboshaft::SnapshotTable<v8::internal::maglev::ValueNode*, v8::internal::compiler::turboshaft::NoKeyData>::SnapshotData, v8::internal::RecyclingZoneAllocator<v8::internal::compiler::turboshaft::SnapshotTable<v8::int
ernal::maglev::ValueNode*, v8::internal::compiler::turboshaft::NoKeyData>::SnapshotData>>::emplace_back<v8::internal::compiler::turboshaft::SnapshotTable<v8::internal::maglev::ValueNode*, v8::internal::compiler::turboshaft::NoKeyData>::SnapshotData*&, unsigned long>(v8::internal::compiler::turboshaft::SnapshotTable<v8::internal::maglev::ValueNode*, v8::internal::compiler::turboshaft::NoKeyData>::SnapshotData*&, unsigned long
&&) gen/third_party/libc++/src/include/deque:1621:5                                                        
    #7 0x7fa9a6096988 in v8::internal::maglev::MaglevPhiRepresentationSelector::MaglevPhiRepresentationSelector(v8::internal::maglev::Graph*) src/compiler/turboshaft/snapshot-table.h:292:23                         
    #8 0x7fa9a5a46300 in v8::internal::maglev::MaglevCompiler::Compile(v8::internal::LocalIsolate*, v8::internal::maglev::MaglevCompilationInfo*) src/maglev/maglev-graph-processor.h:106:9                           
    #9 0x7fa9a5caa838 in v8::internal::maglev::MaglevCompilationJob::ExecuteJobImpl(v8::internal::RuntimeCallStats*, v8::internal::LocalIsolate*) src/maglev/maglev-concurrent-dispatcher.cc:132:8                    
    #10 0x7fa9a4212a2b in v8::internal::(anonymous namespace)::CompileMaglev(v8::internal::Isolate*, v8::internal::Handle<v8::internal::JSFunction>, v8::internal::ConcurrencyMode, v8::internal::BytecodeOffset, v8::internal::(anonymous namespace)::CompileResultBehavior) src/codegen/compiler.cc:451:22
    #11 0x7fa9a41f9192 in v8::internal::(anonymous namespace)::GetOrCompileOptimized(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::ConcurrencyMode, v8::internal::CodeKind, v8::internal::BytecodeOffset, v8::internal::(anonymous namespace)::CompileResultBehavior) src/codegen/compiler.cc:1404:12
    #12 0x7fa9a41f7d5f in v8::internal::Compiler::CompileOptimized(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::ConcurrencyMode, v8::internal::CodeKind) src/codegen/compiler.cc:3175:7
    #13 0x7fa9a5578871 in v8::internal::(anonymous namespace)::CompileOptimized(v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::ConcurrencyMode, v8::internal::CodeKind, v8::internal::Isolate*) src/runtime/runtime-compiler.cc:185:3
    #14 0x7fa9a556b0ea in v8::internal::Runtime_OptimizeMaglevEager(int, unsigned long*, v8::internal::Isolate*) src/runtime/runtime-compiler.cc:217:3                                                                
    #15 0x7fa9a3defcb5 in Builtins_CEntry_Return1_ArgvOnStack_NoBuiltinExit setup-isolate-deserialize.cc                                                                                                              
    #16 0x7fa9a3d39c01 in Builtins_OptimizeMaglevEager setup-isolate-deserialize.cc                        
    #17 0x7fa9a3d38429 in Builtins_InterpreterEntryTrampoline setup-isolate-deserialize.cc                 
    #18 0x7fa9a3d34d9b in Builtins_JSEntryTrampoline setup-isolate-deserialize.cc                          
    #19 0x7fa9a3d34aea in Builtins_JSEntry setup-isolate-deserialize.cc                                    
    #20 0x7fa9a4409596 in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/simulator.h:212:12                              
    #21 0x7fa9a440ab48 in v8::internal::Execution::CallScript(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>) src/execution/execution.cc:542:10
    #22 0x7fa9a3f6ac89 in v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) src/api/api.cc:1964:7                                                                                                          
    #23 0x56171d849507 in v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) src/d8/d8.cc:1036:44                              
    #24 0x56171d8840d3 in v8::SourceGroup::Execute(v8::Isolate*) src/d8/d8.cc:5498:10                      
    #25 0x56171d8908a4 in v8::Shell::RunMainIsolate(v8::Isolate*, bool) src/d8/d8.cc:6454:37               
    #26 0x56171d88fdc4 in v8::Shell::RunMain(v8::Isolate*, bool) src/d8/d8.cc:6362:18                      
    #27 0x56171d89330b in v8::Shell::Main(int, char**) src/d8/d8.cc:7252:18                                
    #28 0x7fa9a0633ca7 in __libc_start_call_main csu/../sysdeps/nptl/libc_start_call_main.h:58:16          

SUMMARY: AddressSanitizer: use-after-poison src/maglev/maglev-regalloc-node-info.h:32:14 in v8::internal::maglev::GeneratorStore::SetValueLocationConstraints()                                                       
Shadow bytes around the buggy address:                                                                     
  0x7e7a0da4d980: f7 f7 f7 00 00 f7 f7 f7 00 00 00 00 f7 f7 f7 00                                          
  0x7e7a0da4da00: 00 00 00 00 00 00 00 f7 f7 f7 00 00 f7 f7 f7 00                                          
  0x7e7a0da4da80: 00 00 00 00 00 00 00 f7 f7 f7 00 00 f7 f7 f7 00                                          
  0x7e7a0da4db00: 00 f7 f7 f7 00 00 f7 f7 f7 00 00 00 00 00 00 00                                          
  0x7e7a0da4db80: 00 f7 f7 f7 00 00 00 00 00 00 f7 f7 f7 00 00 f7                                          
=>0x7e7a0da4dc00: f7 f7 00 00[f7]f7 f7 00 00 f7 f7 f7 00 00 f7 f7                                          
  0x7e7a0da4dc80: f7 00 00 00 00 00 00 00 00 f7 f7 f7 00 00 f7 f7                                          
  0x7e7a0da4dd00: f7 00 00 00 00 00 00 00 00 f7 f7 f7 00 00 00 00                                          
  0x7e7a0da4dd80: f7 f7 f7 00 00 00 00 00 00 00 00 f7 f7 f7 00 00                                          
  0x7e7a0da4de00: f7 f7 f7 00 00 00 00 00 00 00 00 f7 f7 f7 00 00                                          
  0x7e7a0da4de80: f7 f7 f7 00 00 00 00 00 00 00 00 f7 f7 f7 00 00                                          
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
```

# Reporter Credit

Google Big Sleep

# Disclosure Policy

This bug is subject to a 90-day disclosure deadline. If a fix for this issue is made available to users before the end of the 90-day deadline, this bug report will become public 30 days after the fix was made available. Otherwise, this bug report will become public at the deadline. The scheduled deadline is 2025-12-09. For more information, visit [https://goo.gle/bigsleep](<https://goo.gle/bigsleep>)


---

**#2 — gl...@google.com — Sep 30, 2025 05:18AM**

Fixed in: [https://chromereleases.googleblog.com/2025/09/stable-channel-update-for-desktop_23.html](<https://chromereleases.googleblog.com/2025/09/stable-channel-update-for-desktop_23.html>)
