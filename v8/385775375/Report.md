# V8 sandbox violation due to concurrent ArrayBuffer modifications during std::sort

Issue URL: https://issues.chromium.org/issues/385775375
VRP-Reward: 5000
Date: Dec 24, 2024 08:12PM


#### VULNERABILITY DETAILS

Changing the element type of an array before it is sorted may cause an out-of-bound write. I suspect this to be a double fetch bug since it required a background worker to be triggered.

**Please note that this causes an OOB read before it causes an OOB write. Please reach out if you need the LLVM patches I used to disable the instrumentation of reads.**

#### VERSION

V8 commit: 4715559d4fe2ce6e2c0f6de3c966347b6da6a489

#### REPRODUCTION CASE

The test case is mostly one shot but sometimes requires multiple runs.

Build args:

```
is_debug=false
is_asan=true
v8_enable_sandbox=true
v8_enable_memory_corruption_api=true
dcheck_always_on=false
v8_static_library=true
v8_fuzzilli=false
target_cpu="x64"
```

Shell args: `d8 --single-threaded --sandbox-fuzzing --allow-natives-syntax --expose-gc bug.js`

##### ASAN Report:

```
Sandbox testing mode is enabled. Only sandbox violations will be reported, all other crashes will be ignored.
Sandbox.base: 0x7ea100000000
ar: 0x4a540
ar map: 0x1848ed
bit_field2_addr: 0x1848f7
bit_field2_addr value: 0x5d
=================================================================
==683885==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x7fffbefff880 at pc 0x5555580788be bp 0x7fffffffd610 sp 0x7fffffffd608
WRITE of size 8 at 0x7fffbefff880 thread T0
    #0 0x5555580788bd in void v8::base::WriteUnalignedValue<double>(unsigned long, double) src/base/memory.h:43:3
    #1 0x5555580788bd in v8::internal::UnalignedSlot<double>::Reference::operator=(v8::internal::UnalignedSlot<double>::Reference const&) src/objects/slots.h:240:7
    #2 0x5555580788bd in void std::__Cr::__sift_down<std::__Cr::_ClassicAlgPolicy, bool (*&)(double, double), v8::internal::UnalignedSlot<double>>(v8::internal::UnalignedSlot<double>, bool (*&)(double, double), std::__Cr::iterator_traits<v8::internal::UnalignedSlot<double>>::difference_type, v8::internal::UnalignedSlot<double>) third_party/libc++/src/include/__algorithm/sift_down.h:61:14
    #3 0x5555580780b0 in void std::__Cr::__make_heap<std::__Cr::_ClassicAlgPolicy, bool (*&)(double, double), v8::internal::UnalignedSlot<double>>(v8::internal::UnalignedSlot<double>, v8::internal::UnalignedSlot<double>, bool (*&)(double, double)) third_party/libc++/src/include/__algorithm/make_heap.h:39:7
    #4 0x5555580780b0 in v8::internal::UnalignedSlot<double> std::__Cr::__partial_sort_impl<std::__Cr::_ClassicAlgPolicy, bool (*&)(double, double), v8::internal::UnalignedSlot<double>, v8::internal::UnalignedSlot<double>>(v8::internal::UnalignedSlot<double>, v8::internal::UnalignedSlot<double>, v8::internal::UnalignedSlot<double>, bool (*&)(double, double)) third_party/libc++/src/include/__algorithm/partial_sort.h:41:3
    #5 0x555558075971 in v8::internal::UnalignedSlot<double> std::__Cr::__partial_sort<std::__Cr::_ClassicAlgPolicy, bool (*&)(double, double), v8::internal::UnalignedSlot<double>, v8::internal::UnalignedSlot<double>>(v8::internal::UnalignedSlot<double>, v8::internal::UnalignedSlot<double>, v8::internal::UnalignedSlot<double>, bool (*&)(double, double)) third_party/libc++/src/include/__algorithm/partial_sort.h:65:7
    #6 0x555558075971 in void std::__Cr::__introsort<std::__Cr::_ClassicAlgPolicy, bool (*&)(double, double), v8::internal::UnalignedSlot<double>, false>(v8::internal::UnalignedSlot<double>, v8::internal::UnalignedSlot<double>, bool (*&)(double, double), std::__Cr::iterator_traits<v8::internal::UnalignedSlot<double>>::difference_type, bool) third_party/libc++/src/include/__algorithm/sort.h:767:7
    #7 0x55555805b67b in void std::__Cr::__sort_dispatch<std::__Cr::_ClassicAlgPolicy, v8::internal::UnalignedSlot<double>, bool (*)(double, double)>(v8::internal::UnalignedSlot<double>, v8::internal::UnalignedSlot<double>, bool (*&)(double, double)) third_party/libc++/src/include/__algorithm/sort.h:888:3
    #8 0x55555805b67b in void std::__Cr::__sort_impl<std::__Cr::_ClassicAlgPolicy, v8::internal::UnalignedSlot<double>, bool (*)(double, double)>(v8::internal::UnalignedSlot<double>, v8::internal::UnalignedSlot<double>, bool (*&)(double, double)) third_party/libc++/src/include/__algorithm/sort.h:953:5
    #9 0x55555805b67b in void std::__Cr::sort<v8::internal::UnalignedSlot<double>, bool (*)(double, double)>(v8::internal::UnalignedSlot<double>, v8::internal::UnalignedSlot<double>, bool (*)(double, double)) third_party/libc++/src/include/__algorithm/sort.h:961:3
    #10 0x55555805b67b in v8::internal::__RT_impl_Runtime_TypedArraySortFast(v8::internal::Arguments<(v8::internal::ArgumentsType)0>, v8::internal::Isolate*) src/runtime/runtime-typedarray.cc:185:5
    #11 0x55555805b67b in v8::internal::Runtime_TypedArraySortFast(int, unsigned long*, v8::internal::Isolate*) src/runtime/runtime-typedarray.cc:110:1
    #12 0x55555afea375 in Builtins_CEntry_Return1_ArgvOnStack_NoBuiltinExit setup-isolate-deserialize.cc
    #13 0x55555b0b3409 in Builtins_TypedArrayPrototypeSort setup-isolate-deserialize.cc
    #14 0x55555af3ea80 in Builtins_InterpreterEntryTrampoline setup-isolate-deserialize.cc
    #15 0x55555af3c69b in Builtins_JSEntryTrampoline setup-isolate-deserialize.cc
    #16 0x55555af3c3ea in Builtins_JSEntry setup-isolate-deserialize.cc
    #17 0x555556e0b572 in v8::internal::GeneratedCode<unsigned long, unsigned long, unsigned long, unsigned long, unsigned long, long, unsigned long**>::Call(unsigned long, unsigned long, unsigned long, unsigned long, long, unsigned long**) src/execution/simulator.h:191:12
    #18 0x555556e0b572 in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:436:22
    #19 0x555556e0d44c in v8::internal::Execution::CallScript(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>) src/execution/execution.cc:536:10
    #20 0x5555569b79e5 in v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) src/api/api.cc:2155:7
    #21 0x555556774dba in v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) src/d8/d8.cc:1013:44
    #22 0x5555567ac9c8 in v8::SourceGroup::Execute(v8::Isolate*) src/d8/d8.cc:4942:10
    #23 0x5555567b934e in v8::Shell::RunMainIsolate(v8::Isolate*, bool) src/d8/d8.cc:5886:37
    #24 0x5555567b87dd in v8::Shell::RunMain(v8::Isolate*, bool) src/d8/d8.cc:5795:18
    #25 0x5555567bd25c in v8::Shell::Main(int, char**) src/d8/d8.cc:6649:18
    #26 0x7fffbfb911c9 in __libc_start_call_main csu/../sysdeps/nptl/libc_start_call_main.h:58:16
    #27 0x7fffbfb9128a in __libc_start_main csu/../csu/libc-start.c:360:3
    #28 0x555556613029 in _start (/work/v8-build/v8/out/ReproductionSuppressReads/d8+0x10bf029) (BuildId: 313280bf0dd9443d)

0x7fffbefff880 is located 128 bytes after 524288-byte region [0x7fffbef7f800,0x7fffbefff800)
allocated by thread T0 here:
    #0 0x55555673ef08 in operator new(unsigned long) /work/llvm-project/compiler-rt/lib/asan/asan_new_delete.cpp:86:3
    #1 0x55555805ffff in void* std::__Cr::__libcpp_operator_new<unsigned long>(unsigned long) third_party/libc++/src/include/__new/allocate.h:35:10
    #2 0x55555805ffff in std::__Cr::__libcpp_allocate(unsigned long, unsigned long) third_party/libc++/src/include/__new/allocate.h:59:10
    #3 0x55555805ffff in std::__Cr::allocator<unsigned char>::allocate(unsigned long) third_party/libc++/src/include/__memory/allocator.h:105:32
    #4 0x55555805ffff in std::__Cr::__allocation_result<std::__Cr::allocator_traits<std::__Cr::allocator<unsigned char>>::pointer> std::__Cr::__allocate_at_least<std::__Cr::allocator<unsigned char>>(std::__Cr::allocator<unsigned char>&, unsigned long) third_party/libc++/src/include/__memory/allocate_at_least.h:41:19
    #5 0x55555805ffff in std::__Cr::__split_buffer<unsigned char, std::__Cr::allocator<unsigned char>&>::__split_buffer(unsigned long, unsigned long, std::__Cr::allocator<unsigned char>&) third_party/libc++/src/include/__split_buffer:325:25
    #6 0x55555805ffff in std::__Cr::vector<unsigned char, std::__Cr::allocator<unsigned char>>::__append(unsigned long) third_party/libc++/src/include/__vector/vector.h:921:49
    #7 0x55555805a40f in std::__Cr::vector<unsigned char, std::__Cr::allocator<unsigned char>>::resize(unsigned long) third_party/libc++/src/include/__vector/vector.h:1316:11
    #8 0x55555805a40f in v8::internal::__RT_impl_Runtime_TypedArraySortFast(v8::internal::Arguments<(v8::internal::ArgumentsType)0>, v8::internal::Isolate*) src/runtime/runtime-typedarray.cc:149:20
    #9 0x55555805a40f in v8::internal::Runtime_TypedArraySortFast(int, unsigned long*, v8::internal::Isolate*) src/runtime/runtime-typedarray.cc:110:1
    #10 0x55555afea375 in Builtins_CEntry_Return1_ArgvOnStack_NoBuiltinExit setup-isolate-deserialize.cc
    #11 0x55555b0b3409 in Builtins_TypedArrayPrototypeSort setup-isolate-deserialize.cc
    #12 0x55555af3ea80 in Builtins_InterpreterEntryTrampoline setup-isolate-deserialize.cc
    #13 0x55555af3c69b in Builtins_JSEntryTrampoline setup-isolate-deserialize.cc
    #14 0x55555af3c3ea in Builtins_JSEntry setup-isolate-deserialize.cc
    #15 0x555556e0b572 in v8::internal::GeneratedCode<unsigned long, unsigned long, unsigned long, unsigned long, unsigned long, long, unsigned long**>::Call(unsigned long, unsigned long, unsigned long, unsigned long, long, unsigned long**) src/execution/simulator.h:191:12
    #16 0x555556e0b572 in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:436:22
    #17 0x555556e0d44c in v8::internal::Execution::CallScript(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>) src/execution/execution.cc:536:10
    #18 0x5555569b79e5 in v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) src/api/api.cc:2155:7
    #19 0x555556774dba in v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) src/d8/d8.cc:1013:44
    #20 0x5555567ac9c8 in v8::SourceGroup::Execute(v8::Isolate*) src/d8/d8.cc:4942:10
    #21 0x5555567b934e in v8::Shell::RunMainIsolate(v8::Isolate*, bool) src/d8/d8.cc:5886:37
    #22 0x5555567b87dd in v8::Shell::RunMain(v8::Isolate*, bool) src/d8/d8.cc:5795:18
    #23 0x5555567bd25c in v8::Shell::Main(int, char**) src/d8/d8.cc:6649:18
    #24 0x7fffbfb911c9 in __libc_start_call_main csu/../sysdeps/nptl/libc_start_call_main.h:58:16
    #25 0x7fffbfb9128a in __libc_start_main csu/../csu/libc-start.c:360:3
    #26 0x555556613029 in _start (/work/v8-build/v8/out/ReproductionSuppressReads/d8+0x10bf029) (BuildId: 313280bf0dd9443d)

SUMMARY: AddressSanitizer: heap-buffer-overflow src/base/memory.h:43:3 in void v8::base::WriteUnalignedValue<double>(unsigned long, double)
Shadow bytes around the buggy address:
  0x7fffbefff600: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x7fffbefff680: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x7fffbefff700: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x7fffbefff780: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x7fffbefff800: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
=>0x7fffbefff880:[fa]fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x7fffbefff900: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x7fffbefff980: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x7fffbefffa00: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x7fffbefffa80: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x7fffbefffb00: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
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
==683885==ABORTING
```

#### CREDIT INFORMATION

Reporter credit: v8sbxfuzz


---

**#2 — cl...@appspot.gserviceaccount.com — Dec 27, 2024 03:15AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=6650934322987008](<https://clusterfuzz.com/testcase?key=6650934322987008>).


---

**#3 — me...@google.com — Dec 27, 2024 03:16AM**

Assigning to the v8 shepherd. Severity and FoundIn are provisional.


---

**#4 — am...@chromium.org — Dec 27, 2024 04:02AM**

The V8 heap sandbox is not considered a security boundary; updating to SI-none and adding the V8 sandbox tag


---

**#5 — cl...@appspot.gserviceaccount.com — Dec 27, 2024 04:05AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=6189923220520960](<https://clusterfuzz.com/testcase?key=6189923220520960>).


---

**#6 — 24...@project.gserviceaccount.com — Dec 27, 2024 04:25AM**

Testcase 6189923220520960 failed to reproduce the crash. Please inspect the program output at [https://clusterfuzz.com/testcase?key=6189923220520960](<https://clusterfuzz.com/testcase?key=6189923220520960>).


---

**#7 — v8...@gmail.com — Dec 30, 2024 12:28AM**

It seems like `v8_enable_memory_corruption_api=true` was not picked up. Is there anything I can do about that? I just noted that it did not add the `V8 Sandbox Bypass:` prefix to the bug title. I would appreciate it if someone could add it. Is there any way to get the privilege to edit posts?


---

**#8 — am...@chromium.org — Dec 31, 2024 01:43AM**

Hi there, it was clear this was a sandbox bypass report, it's been triaged to the V8 Sandbox component and also added to the `V8 sandbox` hotlist. It has just has not been picked up yet likely due to many folks being out for the holidays / winter festive season. I have updated the title, however.


---

**#9 — cl...@appspot.gserviceaccount.com — Dec 31, 2024 02:01AM**

Detailed Report: [https://clusterfuzz.com/testcase?key=5871979458396160](<https://clusterfuzz.com/testcase?key=5871979458396160>)  
  
Fuzzer: None  
Job Type: linux_asan_d8_sandbox_fuzzing  
Platform Id: linux  
  
Crash Type: V8 sandbox violation  
Crash Address: 0x7bed14fb7800  
Crash State:  
double v8::base::ReadUnalignedValue<double>  
v8::internal::Runtime_TypedArraySortFast  
Builtins_CEntry_Return1_ArgvOnStack_NoBuiltinExit  
  
Sanitizer: address (ASAN)  
  
Crash Revision: [https://clusterfuzz.com/revisions?job=linux_asan_d8_sandbox_fuzzing&revision=97927](<https://clusterfuzz.com/revisions?job=linux_asan_d8_sandbox_fuzzing&revision=97927>)  
  
Reproducer Testcase: [https://clusterfuzz.com/download?testcase_id=5871979458396160](<https://clusterfuzz.com/download?testcase_id=5871979458396160>)  
  
To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.   
  
If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.  
  
If you have any feedback on reproducing test cases, let us know at [https://forms.gle/Yh3qCYFveHj6E5jz5](<https://forms.gle/Yh3qCYFveHj6E5jz5>) so we can improve.


---

**#10 — cl...@appspot.gserviceaccount.com — Dec 31, 2024 02:02AM**

Detailed Report: [https://clusterfuzz.com/testcase?key=4746079551553536](<https://clusterfuzz.com/testcase?key=4746079551553536>)  
  
Fuzzer: None  
Job Type: linux_d8_sandbox_testing  
Platform Id: linux  
  
Crash Type: V8 sandbox violation  
Crash Address:   
Crash State:  
NULL  
Sanitizer: address (ASAN)  
  
Crash Revision: [https://clusterfuzz.com/revisions?job=linux_d8_sandbox_testing&revision=97927](<https://clusterfuzz.com/revisions?job=linux_d8_sandbox_testing&revision=97927>)  
  
Reproducer Testcase: [https://clusterfuzz.com/download?testcase_id=4746079551553536](<https://clusterfuzz.com/download?testcase_id=4746079551553536>)  
  
To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.   
  
If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.  
  
If you have any feedback on reproducing test cases, let us know at [https://forms.gle/Yh3qCYFveHj6E5jz5](<https://forms.gle/Yh3qCYFveHj6E5jz5>) so we can improve.


---

**#11 — 24...@project.gserviceaccount.com — Dec 31, 2024 02:29AM**

Automatically applying components based on crash stacktrace and information from OWNERS files.  
  
If this is incorrect, please apply the hotlistid:4801165.


---

**#12 — am...@chromium.org — Dec 31, 2024 02:31AM**

I'm not sure the bisect is to be trusted on repro that didn't repro as a duplicate. Adding additional folks for visibility when folks return after the new year.


---

**#13 — sa...@google.com — Jan 3, 2025 08:48PM**

Thanks for the report! I haven't looked too closely, but I'm guessing the issue here is that std::sort is unsafe if the input data can be concurrently modified. For SAB's we seem to deal with that by [making an additional copy](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/runtime/runtime-typedarray.cc;l=130;drc=08d82f4f0effa4fc84e6cbdbb40bfee08075dff7>) but probably it would be nice to avoid that. Maybe we need to switch to a different sorting algorithm? Marja could you take a look at this issue? Happy to discuss potential options for fixing this while I'm still in the office (I'll be OOO Jan 13th - Apr 13th)!


---

**#14 — sa...@google.com — Jan 3, 2025 09:10PM**

Ok nevermind, the issue is a different one: there's a straight-forward double-fetch issue when sorting shared ArrayBuffers that can cause the [length](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/runtime/runtime-typedarray.cc;l=127;drc=08d82f4f0effa4fc84e6cbdbb40bfee08075dff7>) (that will be used for sorting) and the [bytes count](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/runtime/runtime-typedarray.cc;l=142;drc=08d82f4f0effa4fc84e6cbdbb40bfee08075dff7>) (which will be used for allocating the temporary buffer to hold a copy of the data) to become inconsistent. If the length changes in between, then the two values are inconsistent and we run out of bounds. It should be enough to add a `SBXCHECK` that the values are as expected. Additionally, we could also consider allocating the temporary buffer inside the sandbox so that even if there are other OOB writes to it, they won't matter.

The concurrent modification during std::sort will also corrupt memory, but in that case, the sorted buffer will always be inside the sandbox, so memory corruption is fine.


---

**#15 — v8...@gmail.com — Jan 29, 2025 06:49PM**

Any update on this issue?


---

**#16 — ma...@chromium.org — Feb 14, 2025 10:34PM**

I started looking into this a bit. The repro is corrupting the bit_field_2 in the Map where ElementsKind is stored.

Looks like just fixing the byte_length double fetch (and adding a SBXCHECK that length is not bigger than byte_length) is not enough. I'm still getting some sandbox violations after that (though, they're now harder to trigger).

I think the bug described in comment 13 also exists. The "is this backed by SAB" property can also be modified concurrently, so, we might think it's not a SAB, go into the "don't copy" code path, and then restore the SAB-ness of the backing buffer. If we cannot trust anything from the heap, I don't know how we could figure out whether to copy or not copy in a safe way.


---

**#17 — ma...@chromium.org — Feb 14, 2025 10:54PM**

Ah, it's the array->type() that is now out of sync with the length we read.


---

**#18 — ap...@google.com — Feb 20, 2025 11:59PM**

Project: v8/v8  
Branch: main  
Author: Marja Hölttä <[marja@chromium.org](<mailto:marja@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6268383](<https://chromium-review.googlesource.com/6268383>)

[sandbox] Fix a sandbox escape related to sorting TypedArrays

* * *

Expand for full commit details

```
[sandbox] Fix a sandbox escape related to sorting TypedArrays 
 
Bug: 385775375 
Change-Id: I8314ffa2864ac40fbf09407b7cb7519c50bbab37 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6268383 
Reviewed-by: Stephen Röttger <sroettger@google.com> 
Commit-Queue: Marja Hölttä <marja@chromium.org> 
Cr-Commit-Position: refs/heads/main@{#98839}
```

* * *

Files:

  * M `src/runtime/runtime-typedarray.cc`
  * A `test/mjsunit/sandbox/regress-385775375.js`

* * *

Hash: 66bd3ee476b8be86faf209d13620b2f73024aa61  
Date: Thu Feb 20 15:23:44 2025

* * *


---

**#19 — sr...@google.com — Feb 21, 2025 01:43AM**

After this fix, we're still running std::sort on in-sandbox memory. I know this can lead to memory corruption, but I'm not sure if it leads to out-of-sbx memory corruption. Should we track this in a separate bug?


---

**#20 — sr...@google.com — Feb 21, 2025 01:46AM**

My initial thought is that it should just run out-of-bounds linearly in that case, which would be fine from the sbx pov.


---

**#21 — sp...@google.com — Mar 14, 2025 07:55AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $5000.00 for this report.  
  
Rationale for this decision:  
report of V8 sandbox bypass demonstrating memory corruption outside the V8 sandbox  
  
  
Important: This payment will be issued by Bugcrowd. You will receive an email from Bugcrowd in the next 24 hours which contains a submission you must claim to be rewarded.  
  
If you do not receive an email from them, please check your spam folder and then reach out to us via a comment here. For issues related to Bugcrowd itself, please contact them via [https://bugcrowd.com/support](<https://bugcrowd.com/support>).  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#22 — am...@chromium.org — Mar 14, 2025 08:09AM**

Congratulations v8sbxfuzz! Thank you for your efforts hunting in the V8 sandbox and reporting this issue to us!


---

**#23 — ch...@google.com — Jun 10, 2025 09:39PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.


---

**#24 — dx...@google.com — Sep 9, 2025 07:33PM**

Project: v8/v8  
Branch: main  
Author: Marja Hölttä [marja@chromium.org](<mailto:marja@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6918956](<https://chromium-review.googlesource.com/6918956>)

[rab/gsab] Handle GSABs growing during sorting gracefully

* * *

Expand for full commit details

```
     
    The previous sandbox hardening ( 
    https://chromium-review.googlesource.com/c/v8/v8/+/6268383 ) was not 
    correct; it didn't handle the case that the GSAB is grown by a 
    background thread gracefully. 
     
    The easiest fix is to avoid reading the length again and figure out how 
    many elements we need to sort based on the byte_length we already read. 
     
    Bug: 385775375 
    Change-Id: I70f0b051ffad61f1f80cd50f0dbdbd0fa7ab1287 
    Fixed: 439522866 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6918956 
    Reviewed-by: Anton Bikineev <bikineev@chromium.org> 
    Commit-Queue: Marja Hölttä <marja@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#102346}
```

* * *

Files:

  * M `src/runtime/runtime-typedarray.cc`
  * A `test/mjsunit/regress/regress-439522866.js`
  * M `test/mjsunit/sandbox/regress-385775375.js`

* * *

Hash: [3bbb4dcb340460be8ff9afe51290cfe94d7188ff](<https://chromiumdash.appspot.com/commit/3bbb4dcb340460be8ff9afe51290cfe94d7188ff>)  
Date: Fri Sep 5 10:46:03 2025

* * *
