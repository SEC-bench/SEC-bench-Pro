# V8 Sandbox Bypass: heap-buffer-overflow third_party/libc++/src/include/__atomic/cxx_atomic_impl.h:311:10 in __cxx_atomic_load<long>

Issue URL: https://issues.chromium.org/issues/379591504
VRP-Reward: DUP
Date: Nov 18, 2024 10:22PM


#### Security Bug

Important: Please do not change the component of this bug manually.

Please READ THIS FAQ before filing a bug: [https://chromium.googlesource.com/chromium/src/+/HEAD/docs/security/faq.md](<https://chromium.googlesource.com/chromium/src/+/HEAD/docs/security/faq.md>)

Please see the following link for instructions on filing security bugs: [https://www.chromium.org/Home/chromium-security/reporting-security-bugs](<https://www.chromium.org/Home/chromium-security/reporting-security-bugs>)

Reports may be eligible for reward payments under the Chrome VRP: [https://g.co/chrome/vrp](<https://g.co/chrome/vrp>)

NOTE: Security bugs are normally made public once a fix has been widely deployed.

* * *

#### V8 VERSION

```
commit 8cf8962d3f8125a9a3d0fcab40a6b59582bbd349 (HEAD, origin/main, origin/lkgr, origin/HEAD, main)
Author: v8-ci-autoroll-builder <v8-ci-autoroll-builder@chops-service-accounts.iam.gserviceaccount.com>
Date:   Sat Nov 16 20:06:52 2024 -0800
```

* * *

#### REPRODUCTION CASE

  1. build args.gn

```
is_debug = false
dcheck_always_on = false
target_cpu = "x64"
v8_enable_memory_corruption_api = true
is_asan = true
```

  2. run d8 with following command

```
~/v8/v8/out/v8_sandbox/d8 --expose-gc --allow-natives-syntax --sandbox-testing ./poc.js
```

  3. or use `v8_helper.js` (v8_helper.js contents are mjsuint + wasm-module-builder)

```
~/v8/v8/out/v8_sandbox/d8 --expose-gc --allow-natives-syntax --sandbox-testing ./v8_helper.js ./poc.js
```

  4. In order to test on `clusterfuzz` please use `poc-clusterfuzz.js`

```
~/v8/v8/out/v8_sandbox/d8 --expose-gc --allow-natives-syntax --sandbox-testing ./poc-clusterfuzz.js
```

* * *

#### FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION

```
Sandbox testing mode is enabled. Only sandbox violations will be reported, all other crashes will be ignored.
=================================================================
==2455007==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x74283b2ddb68 at pc 0x5e9e2c906921 bp 0x7fffea7fca00 sp 0x7fffea7fc9f8
READ of size 8 at 0x74283b2ddb68 thread T0
    #0 0x5e9e2c906920 in __cxx_atomic_load<long> third_party/libc++/src/include/__atomic/cxx_atomic_impl.h:311:10
    #1 0x5e9e2c906920 in load third_party/libc++/src/include/__atomic/atomic_base.h:55:12
    #2 0x5e9e2c906920 in atomic_load_explicit<long> third_party/libc++/src/include/__atomic/atomic.h:327:15
    #3 0x5e9e2c906920 in Acquire_Load src/base/atomicops.h:352:10
    #4 0x5e9e2c906920 in Acquire_Load<heap::base::BasicSlotSet<4UL>::Bucket *> src/base/atomic-utils.h:80:9
    #5 0x5e9e2c906920 in LoadBucket<(heap::base::BasicSlotSet<4UL>::AccessMode)0> src/heap/base/basic-slot-set.h:407:14
    #6 0x5e9e2c906920 in LoadBucket<(heap::base::BasicSlotSet<4UL>::AccessMode)1> src/heap/base/basic-slot-set.h:413:12
    #7 0x5e9e2c906920 in Insert<(heap::base::BasicSlotSet<4UL>::AccessMode)1> src/heap/base/basic-slot-set.h:117:22
    #8 0x5e9e2c906920 in Insert<(v8::internal::AccessMode)1> src/heap/remembered-set.h:31:15
    #9 0x5e9e2c906920 in Insert<(v8::internal::AccessMode)1> src/heap/remembered-set.h:102:5
    #10 0x5e9e2c906920 in v8::internal::Heap::InsertIntoRememberedSetFromCode(v8::internal::MutablePageMetadata*, unsigned long) src/heap/heap.cc:6527:3
    #11 0x5e9e2ff5594f in Builtins_RecordWriteSaveFP setup-isolate-deserialize.cc
    #12 0x5e9e2ff6d3dc in Builtins_KeyedStoreIC_Megamorphic setup-isolate-deserialize.cc
    #13 0x5e9e300f5ace in Builtins_SetKeyedPropertyHandler setup-isolate-deserialize.cc
    #14 0x5e9e2ff62a0a in Builtins_InterpreterEntryTrampoline setup-isolate-deserialize.cc
    #15 0x5e9e2ff62a0a in Builtins_InterpreterEntryTrampoline setup-isolate-deserialize.cc
    #16 0x5e9e2ff62a0a in Builtins_InterpreterEntryTrampoline setup-isolate-deserialize.cc
    #17 0x5e9e2ff6061b in Builtins_JSEntryTrampoline setup-isolate-deserialize.cc
    #18 0x5e9e2ff6035e in Builtins_JSEntry setup-isolate-deserialize.cc
    #19 0x5e9e2c6e171b in Call src/execution/simulator.h:191:12
    #20 0x5e9e2c6e171b in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:417:22
    #21 0x5e9e2c6e2d46 in v8::internal::Execution::CallScript(v8::internal::Isolate*, v8::internal::Handle<v8::internal::JSFunction>, v8::internal::Handle<v8::internal::Object>, v8::internal::Handle<v8::internal::Object>) src/execution/execution.cc:514:10
    #22 0x5e9e2c2543fc in v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) src/api/api.cc:2151:7
    #23 0x5e9e2c1e03b3 in v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) src/d8/d8.cc:1012:44
    #24 0x5e9e2c20b6c3 in v8::SourceGroup::Execute(v8::Isolate*) src/d8/d8.cc:4914:10
    #25 0x5e9e2c21659e in v8::Shell::RunMainIsolate(v8::Isolate*, bool) src/d8/d8.cc:5858:37
    #26 0x5e9e2c215c96 in v8::Shell::RunMain(v8::Isolate*, bool) src/d8/d8.cc:5767:18
    #27 0x5e9e2c218c88 in v8::Shell::Main(int, char**) src/d8/d8.cc:6621:18
    #28 0x76d83c22a3b7 in __libc_start_call_main csu/../sysdeps/nptl/libc_start_call_main.h:58:16
    #29 0x76d83c22a47a in __libc_start_main csu/../csu/libc-start.c:360:3
    #30 0x5e9e2c0db029 in _start (/home/rheza/v8/v8/out/v8_sandbox/d8+0x10db029) (BuildId: 77884e24ad2fbb5c)

0x74283b2ddb68 is located 104 bytes after 512-byte region [0x74283b2dd900,0x74283b2ddb00)
allocated by thread T0 here:
    #0 0x5e9e2c17a757 in posix_memalign /b/s/w/ir/cache/builder/src/third_party/llvm/compiler-rt/lib/asan/asan_malloc_linux.cpp:139:3
    #1 0x5e9e2ca3d62f in AlignedAlloc src/base/platform/memory.h:94:7
    #2 0x5e9e2ca3d62f in Allocate src/heap/base/basic-slot-set.h:59:24
    #3 0x5e9e2ca3d62f in Allocate src/heap/slot-set.h:134:34
    #4 0x5e9e2ca3d62f in v8::internal::MutablePageMetadata::AllocateSlotSet(v8::internal::RememberedSetType) src/heap/mutable-page-metadata.cc:164:27
    #5 0x5e9e2c906844 in Insert<(v8::internal::AccessMode)1> src/heap/remembered-set.h:100:24
    #6 0x5e9e2c906844 in v8::internal::Heap::InsertIntoRememberedSetFromCode(v8::internal::MutablePageMetadata*, unsigned long) src/heap/heap.cc:6527:3
    #7 0x5e9e2ff5594f in Builtins_RecordWriteSaveFP setup-isolate-deserialize.cc
    #8 0x5e9e2ff6d3dc in Builtins_KeyedStoreIC_Megamorphic setup-isolate-deserialize.cc
    #9 0x5e9e300f5ace in Builtins_SetKeyedPropertyHandler setup-isolate-deserialize.cc
    #10 0x5e9e2ff62a0a in Builtins_InterpreterEntryTrampoline setup-isolate-deserialize.cc
    #11 0x5e9e2ff62a0a in Builtins_InterpreterEntryTrampoline setup-isolate-deserialize.cc
    #12 0x5e9e2ff62a0a in Builtins_InterpreterEntryTrampoline setup-isolate-deserialize.cc
    #13 0x5e9e2ff6061b in Builtins_JSEntryTrampoline setup-isolate-deserialize.cc
    #14 0x5e9e2ff6035e in Builtins_JSEntry setup-isolate-deserialize.cc
    #15 0x5e9e2c6e171b in Call src/execution/simulator.h:191:12
    #16 0x5e9e2c6e171b in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:417:22
    #17 0x5e9e2c6e2d46 in v8::internal::Execution::CallScript(v8::internal::Isolate*, v8::internal::Handle<v8::internal::JSFunction>, v8::internal::Handle<v8::internal::Object>, v8::internal::Handle<v8::internal::Object>) src/execution/execution.cc:514:10
    #18 0x5e9e2c2543fc in v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) src/api/api.cc:2151:7
    #19 0x5e9e2c1e03b3 in v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) src/d8/d8.cc:1012:44
    #20 0x5e9e2c20b6c3 in v8::SourceGroup::Execute(v8::Isolate*) src/d8/d8.cc:4914:10
    #21 0x5e9e2c21659e in v8::Shell::RunMainIsolate(v8::Isolate*, bool) src/d8/d8.cc:5858:37
    #22 0x5e9e2c215c96 in v8::Shell::RunMain(v8::Isolate*, bool) src/d8/d8.cc:5767:18
    #23 0x5e9e2c218c88 in v8::Shell::Main(int, char**) src/d8/d8.cc:6621:18
    #24 0x76d83c22a3b7 in __libc_start_call_main csu/../sysdeps/nptl/libc_start_call_main.h:58:16
    #25 0x76d83c22a47a in __libc_start_main csu/../csu/libc-start.c:360:3
    #26 0x5e9e2c0db029 in _start (/home/rheza/v8/v8/out/v8_sandbox/d8+0x10db029) (BuildId: 77884e24ad2fbb5c)

SUMMARY: AddressSanitizer: heap-buffer-overflow third_party/libc++/src/include/__atomic/cxx_atomic_impl.h:311:10 in __cxx_atomic_load<long>
Shadow bytes around the buggy address:
  0x74283b2dd880: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x74283b2dd900: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x74283b2dd980: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x74283b2dda00: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x74283b2dda80: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
=>0x74283b2ddb00: fa fa fa fa fa fa fa fa fa fa fa fa fa[fa]fa fa
  0x74283b2ddb80: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x74283b2ddc00: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x74283b2ddc80: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x74283b2ddd00: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x74283b2ddd80: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
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
==2455007==ABORTING

## V8 sandbox violation detected!
```

* * *


---

**#2 — cl...@appspot.gserviceaccount.com — Nov 18, 2024 11:12PM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=6349497277808640](<https://clusterfuzz.com/testcase?key=6349497277808640>).


---

**#3 — ah...@google.com — Nov 18, 2024 11:14PM**

[Primary Security Shepherd]

Setting a provisional severity of High (S1)

Setting a provisional Found In of the current Extended Stable (130).

Assigning to the current V8 Shepherd: [ishell@chromium.org](<mailto:ishell@chromium.org>)


---

**#4 — rh...@gmail.com — Nov 18, 2024 11:36PM**

re #c3

sorry, please use `linux_d8_sandbox_testing` on job type on CF. The current `job type: linux_asan_d8` on CF is missing sandbox API.


---

**#5 — sa...@chromium.org — Nov 18, 2024 11:38PM**

Thanks for the report! This is probably related to [issue 329345899](<https://issues.chromium.org/issues/329345899>), so assigning to Michael. Let's see if your CL fixes this as well.

Also note that the ASan log only shows an out-of-sandbox READ which is not necessarily sufficient to demonstrate memory corruption. See also [the README.md](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/sandbox/README.md;l=82;drc=19c5b5a8c4b3525aafadb70e9865439e5983180a>) for more information.


---

**#6 — rh...@gmail.com — Nov 18, 2024 11:42PM**

re #5  
  
ops, thank you for the info


---

**#7 — ap...@google.com — Nov 19, 2024 03:35AM**

Project: v8/v8  
Branch: main  
Author: Michael Lippautz <[mlippautz@chromium.org](<mailto:mlippautz@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6011212](<https://chromium-review.googlesource.com/6011212>)

[heap, builtins] Check bucket bounds for remembered set

* * *

Expand for full commit details

```
[heap, builtins] Check bucket bounds for remembered set 
 
SlotSet used to only store the number of allocated buckets in debug 
builds. This CL enables the counter also on release builds and also 
uses the counter in bottlenecks that compute bucket indicies. This 
solves a heap sandbox issue with OOB access on corrupted slot offsets. 
 
The CL reuses the existing debug counter for the CHECK. This already 
turns out to be neutral on competitive benchmarks. 
 
We can improve this by moving the counter next to the actual bucket 
array pointer. This would make SlotSet roughly similar to a vector 
(size + dynamic backing) and make sure that size is always in L1 this 
way. The refactoring is left for future work as this requires adopting 
how SlotSet works on background threads which currently only uses CAS 
on the SlotSet pointer (which at this point includes the bucket 
counter). 
 
Bug: 329345899, 379591504 
Change-Id: Iceb522f3313d7e9f57f511d1b60c8983502ed955 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6011212 
Commit-Queue: Michael Lippautz <mlippautz@chromium.org> 
Reviewed-by: Anton Bikineev <bikineev@chromium.org> 
Reviewed-by: Dominik Inführ <dinfuehr@chromium.org> 
Cr-Commit-Position: refs/heads/main@{#97247}
```

* * *

Files:

  * M `src/builtins/builtins-internal-gen.cc`
  * M `src/heap/base/basic-slot-set.h`
  * M `src/heap/cppgc/heap-page.cc`
  * M `src/heap/large-page-metadata.cc`
  * M `src/heap/minor-mark-sweep-inl.h`
  * M `src/heap/minor-mark-sweep.cc`
  * M `src/heap/mutable-page-metadata.cc`
  * M `src/heap/mutable-page-metadata.h`
  * M `src/heap/remembered-set.h`
  * A `test/mjsunit/sandbox/regress-329345899.js`
  * M `test/unittests/heap/base/basic-slot-set-unittest.cc`

* * *

Hash: 47c50e8013d9061ca113e66514568debc4dfb133  
Date: Mon Nov 18 18:50:46 2024

* * *


---

**#8 — ml...@chromium.org — Nov 19, 2024 03:35AM**

This is indeed the same issue as [issue 329345899](<https://issues.chromium.org/issues/329345899>). I will land the fix now and we can decide later if we want to merge it.


---

**#9 — sa...@chromium.org — Nov 19, 2024 05:08PM**

I wasn't able to reproduce this (yesterday, before the fix, see e.g. [https://clusterfuzz.com/testcase-detail/5870539704827904](<https://clusterfuzz.com/testcase-detail/5870539704827904>)) but since we're pretty confident that it's the same issue, I'll mark it as duplicate now.


---

**#10 — ch...@google.com — Feb 26, 2025 09:40PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
