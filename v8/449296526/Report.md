# V8 Sandbox Bypass:

Issue URL: https://issues.chromium.org/issues/449296526
VRP-Reward: DUP (`329781444`)
Date: Oct 4, 2025 07:38PM


Hi and hope this report finds you well!

**VULNERABILITY DETAILS**

V8 Sandbox Escape in latest ASAN-built V8.

**VERSION**

V8: v8@b0157a634e584163cbe6004db3161dc16dea20f9

Operating System: Ubuntu 22.04

Built args:

```
is_component_build = false
v8_use_external_startup_data = false
is_debug = false
is_asan = true
dcheck_always_on = false
v8_static_library = true
v8_enable_verify_heap = false
v8_fuzzilli = true
sanitizer_coverage_flags = "trace-pc-guard"
target_cpu = "x64"
v8_enable_sandbox = true
v8_enable_memory_corruption_api = true
```

Log:

```
[COV] no shared memory bitmap available, skipping
[COV] edge counters initialized. Shared memory: (null) with 957360 edges
Sandbox testing mode is enabled. Only sandbox violations will be reported, all other crashes will be ignored.
Sandbox bounds: [0x7e9d00000000,0x7f9d00000000)
Corrupting memory starting from object at 0x80d3bc with RNG seed 1032026359
  Corrupting object at 0x80d3bc of type UINT8_TYPED_ARRAY_CONSTRUCTOR_TYPE
  Recursively corrupting object referenced through pointer at offset 0
    Corrupting object at 0x81d1ac of type MAP_TYPE
    Recursively corrupting neighboring object at offset 616
      Corrupting object at 0x81d414 of type EXTERNAL_ONE_BYTE_STRING_TYPE
      Corrupted 16-bit field at offset 8. Old value: 0x1b, new value: 0x45d2
=================================================================
==136222==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x78b2f9de0208 at pc 0x5f6dddc5966b bp 0x7ffce4997f20 sp 0x7ffce4997f18
READ of size 1 at 0x78b2f9de0208 thread T0
    #0 0x5f6dddc5966a in void v8::internal::CalculateLineEndsImpl<unsigned char>(v8::base::SmallVector<int, 32ul, std::__Cr::allocator<int>>*, v8::base::Vector<unsigned char const>, bool) src/objects/string.cc:1148:23
    #1 0x5f6dddc58885 in v8::base::SmallVector<int, 32ul, std::__Cr::allocator<int>> v8::internal::String::CalculateLineEndsVector<v8::internal::Isolate>(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::String>, bool) src/objects/string.cc:1177:7
    #2 0x5f6dddc59d72 in v8::internal::Handle<v8::internal::FixedArray> v8::internal::String::CalculateLineEnds<v8::internal::Isolate>(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::String>, bool) src/objects/string.cc:1197:7
    #3 0x5f6dddc033ac in void v8::internal::Script::InitLineEndsInternal<v8::internal::Isolate>(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::Script>) src/objects/script.cc:112:9
    #4 0x5f6dddc057fb in InitLineEnds src/objects/script-inl.h:201:3
    #5 0x5f6dddc057fb in v8::internal::Script::GetPositionInfo(v8::internal::DirectHandle<v8::internal::Script>, int, v8::internal::Script::PositionInfo*, v8::internal::Script::OffsetFlag) src/objects/script.cc:149:3
    #6 0x5f6ddd577824 in v8::internal::ExistingCodeLogger::LogExistingFunction(v8::internal::DirectHandle<v8::internal::SharedFunctionInfo>, v8::internal::DirectHandle<v8::internal::AbstractCode>, v8::internal::LogEventListener::CodeTag) src/logging/log.cc:2697:5
    #7 0x5f6ddd55ff58 in v8::internal::ExistingCodeLogger::LogCompiledFunctions(bool) src/logging/log.cc:2673:5
    #8 0x5f6ddde3a75b in v8::internal::ProfilingScope::ProfilingScope(v8::internal::Isolate*, v8::internal::ProfilerListener*) src/profiler/cpu-profiler.cc:94:16
    #9 0x5f6ddde3fa76 in v8::internal::CpuProfiler::EnableLogging() src/profiler/cpu-profiler.cc:594:11
    #10 0x5f6ddde413e8 in v8::internal::CpuProfiler::StartProcessorIfNotStarted() src/profiler/cpu-profiler.cc:704:5
    #11 0x5f6ddde40d4e in v8::internal::CpuProfiler::StartProfiling(char const*, v8::CpuProfilingOptions, std::__Cr::unique_ptr<v8::DiscardedSamplesDelegate, std::__Cr::default_delete<v8::DiscardedSamplesDelegate>>) src/profiler/cpu-profiler.cc:658:5
    #12 0x5f6ddde4193b in v8::internal::CpuProfiler::StartProfiling(v8::internal::Tagged<v8::internal::String>, v8::CpuProfilingOptions, std::__Cr::unique_ptr<v8::DiscardedSamplesDelegate, std::__Cr::default_delete<v8::DiscardedSamplesDelegate>>) src/profiler/cpu-profiler.cc:692:10
    #13 0x5f6ddc8e524b in Start src/api/api.cc:11588:51
    #14 0x5f6ddc8e524b in v8::CpuProfiler::StartProfiling(v8::Local<v8::String>, v8::CpuProfilingOptions, std::__Cr::unique_ptr<v8::DiscardedSamplesDelegate, std::__Cr::default_delete<v8::DiscardedSamplesDelegate>>) src/api/api.cc:11614:10
    #15 0x5f6ddc448679 in v8::D8Console::Profile(v8::debug::ConsoleCallArguments const&, v8::debug::ConsoleContext const&) src/d8/d8-console.cc:115:14
    #16 0x5f6ddc979336 in v8::internal::(anonymous namespace)::ConsoleCall(v8::internal::Isolate*, v8::internal::BuiltinArguments const&, void (v8::debug::ConsoleDelegate::*)(v8::debug::ConsoleCallArguments const&, v8::debug::ConsoleContext const&)) src/builtins/builtins-console.cc:170:3
    #17 0x5f6ddc96ea1d in Builtin_Impl_ConsoleProfile src/builtins/builtins-console.cc:197:1
    #18 0x5f6ddc96ea1d in v8::internal::Builtin_ConsoleProfile(int, unsigned long*, v8::internal::Isolate*) src/builtins/builtins-console.cc:197:1
    #19 0x5f6de2392ff5 in Builtins_CEntry_Return1_ArgvOnStack_BuiltinExit setup-isolate-deserialize.cc
    #20 0x5f6de22e77a9 in Builtins_InterpreterEntryTrampoline setup-isolate-deserialize.cc
    #21 0x5f6de22e455b in Builtins_JSEntryTrampoline setup-isolate-deserialize.cc
    #22 0x5f6de22e42aa in Builtins_JSEntry setup-isolate-deserialize.cc
    #23 0x5f6ddccd79f2 in Call src/execution/simulator.h:212:12
    #24 0x5f6ddccd79f2 in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:442:22
    #25 0x5f6ddccda228 in v8::internal::Execution::CallScript(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>) src/execution/execution.cc:542:10
    #26 0x5f6ddc8957a0 in v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) src/api/api.cc:1953:7
    #27 0x5f6ddc475daf in v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) src/d8/d8.cc:1044:44
    #28 0x5f6ddc4bb187 in v8::SourceGroup::Execute(v8::Isolate*) src/d8/d8.cc:5543:10
    #29 0x5f6ddc4c9418 in v8::Shell::RunMainIsolate(v8::Isolate*, bool) src/d8/d8.cc:6503:37
    #30 0x5f6ddc4c863e in v8::Shell::RunMain(v8::Isolate*, bool) src/d8/d8.cc:6411:18
    #31 0x5f6ddc4cd628 in v8::Shell::Main(int, char**) src/d8/d8.cc:7301:18
    #32 0x7c02faa29d8f in __libc_start_call_main csu/../sysdeps/nptl/libc_start_call_main.h:58:16

0x78b2f9de0208 is located 0 bytes after 104-byte region [0x78b2f9de01a0,0x78b2f9de0208)
allocated by thread T0 here:
    #0 0x5f6ddc43a15d in operator new(unsigned long) (/home/loru/research/v8_latest/v8/out/fuzzbuild_standalone/d8+0x140215d) (BuildId: 3785720456c0a123)
    #1 0x5f6ddd2cf3b1 in make_unique<v8::internal::FuzzilliExtension, const char (&)[9], 0> gen/third_party/libc++/src/include/__memory/unique_ptr.h:759:26
    #2 0x5f6ddd2cf3b1 in v8::internal::Bootstrapper::InitializeOncePerProcess() src/init/bootstrapper.cc:163:25
    #3 0x5f6ddd341715 in v8::internal::V8::Initialize() src/init/v8.cc:228:3
    #4 0x5f6ddc8c5815 in v8::V8::Initialize(int) src/api/api.cc:6466:3
    #5 0x5f6ddc4cb735 in Initialize include/v8-initialization.h:127:12
    #6 0x5f6ddc4cb735 in v8::Shell::Main(int, char**) src/d8/d8.cc:7098:3
    #7 0x7c02faa29d8f in __libc_start_call_main csu/../sysdeps/nptl/libc_start_call_main.h:58:16

SUMMARY: AddressSanitizer: heap-buffer-overflow src/objects/string.cc:1148:23 in void v8::internal::CalculateLineEndsImpl<unsigned char>(v8::base::SmallVector<int, 32ul, std::__Cr::allocator<int>>*, v8::base::Vector<unsigned char const>, bool)
Shadow bytes around the buggy address:
  0x78b2f9ddff80: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x78b2f9de0000: fa fa fa fa fa fa fa fa 00 00 00 00 00 00 00 00
  0x78b2f9de0080: 00 00 00 00 00 00 fa fa fa fa fa fa fa fa 00 00
  0x78b2f9de0100: 00 00 00 00 00 00 00 00 00 00 00 fa fa fa fa fa
  0x78b2f9de0180: fa fa fa fa 00 00 00 00 00 00 00 00 00 00 00 00
=>0x78b2f9de0200: 00[fa]fa fa fa fa fa fa fa fa 00 00 00 00 00 00
  0x78b2f9de0280: 00 00 00 00 00 00 00 fa fa fa fa fa fa fa fa fa
  0x78b2f9de0300: 00 00 00 00 00 00 00 00 00 00 00 00 00 fa fa fa
  0x78b2f9de0380: fa fa fa fa fa fa 00 00 00 00 00 00 00 00 00 00
  0x78b2f9de0400: 00 00 00 00 fa fa fa fa fa fa fa fa 00 00 00 00
  0x78b2f9de0480: 00 00 00 00 00 00 00 00 00 fa fa fa fa fa fa fa
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
==136222==ABORTING

## V8 sandbox violation detected!
```

This escape is found via Fuzzilli, and the attached `poc.js` is generated by Fuzzilli during fuzzing.

Reproduce with: `./d8 --sandbox-testing poc.js`

I do not have my research PC with me now, so I am not sure how this escape happened. From the PoC, it seems to be related to `console.profile()`. I will return and provide more details on the cause of this bypass if I find anything interesting later.

Thanks for reviewing my report!

CREDIT INFORMATION Reporter credit: rogerace


---

**#2 — lo...@gmail.com — Oct 4, 2025 08:06PM**

Oops, sorry I missed the title of this report. Please help me update it accordingly to reflect the content of this report.

Thanks for your help!

Best,

Rogerace


---

**#3 — lo...@gmail.com — Oct 6, 2025 01:09PM**

Hi,

I tried to reproduce this with other build flags, and it seems that this vulnerability only got triggered when `v8_fuzzilli=true` is set. Based on the ASAN logs, it also seems that part of the exploit chain of this vuln is:

```
    #1 0x5f6ddd2cf3b1 in make_unique<v8::internal::FuzzilliExtension, const char (&)[9], 0> gen/third_party/libc++/src/include/__memory/unique_ptr.h:759:26
```

What I am not sure is whether this can be reproduced by tweaking the Fuzzilli-generated PoC so that it can be triggered without the Fuzzilli flag. After all, in my provided PoC, we (de-facto) only have 2 lines and there is nothing special that relies on this Fuzzilli flag:

```
corrupt(Uint8Array, 1032026359);
this.console.profile();
```

I am trying to pinpoint why this vuln triggers when Fuzzilli flag is set and try to reproduce without it. I will let you know if I find something.

Lastly, I am quite new to v8, so if I did anything wrong, or you find this bug is definitely non-triggerable without the Fuzzilli flag, please let me know.

Thanks for your time!

Best,

Rogerace


---

**#4 — lo...@gmail.com — Oct 8, 2025 09:22PM**

Hi,

Upon closer investigation, here is my updated view on this vuln:

  1. Based on ASAN log and my research, this might be a READ-ONLY sandbox escape. The issue is in the following, `src.length()` is within SBX and can be corrupted, causing this OOB-read:

```
static void CalculateLineEndsImpl(String::LineEndsVector* line_ends,
                                  base::Vector<const SourceChar> src,
                                  bool include_ending_line) {
  const int src_len = src.length(); //can be polluted
  for (int i = 0; i < src_len - 1; i++) {
    SourceChar current = src[i];
    SourceChar next = src[i + 1];
    if (IsLineTerminatorSequence(current, next)) line_ends->push_back(i);
  }

  if (src_len > 0 && IsLineTerminatorSequence(src[src_len - 1], 0)) {
    line_ends->push_back(src_len - 1);
  }
  if (include_ending_line) {
    // Include one character beyond the end of script. The rewriter uses that
    // position for the implicit return statement.
    line_ends->push_back(src_len);
  }
}
```

  2. I am aware that OOB-Read is not technically sandbox violation, and I am looking for ways to escalate it to OOB-write. But I am quite new to V8, so it may take me days to find one (or to realize that it is not possible). So feel free to close this report if you agree that this is only OOB-read and choose to not fix it. I will just submit another report if I managed to turn this into an OOB-write.

Thanks for your help!

Best,

Rogerace


---

**#5 — pa...@google.com — Oct 9, 2025 07:55PM**

Reassigning to the current Shepherd


---

**#6 — bi...@google.com — Oct 15, 2025 06:16PM**

The POC modifies the length of the externalized string, this is a known bug.


---

**#7 — ch...@google.com — Jan 22, 2026 09:39PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.


---

**#8 — ch...@google.com — Jan 22, 2026 09:42PM**

This V8 bug has been marked as either a release blocker or a vulnerability bug. V8 bugs affect all OSs supported by Chrome, so the OS field has been updated to reflect this. Please update the bug with the correct OS field if it only affects a subset of OSes.
