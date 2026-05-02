# V8 Sandbox Bypass: OOB write to controlled address

Issue URL: https://issues.chromium.org/issues/443475183
VRP-Reward: 5000
Date: Sep 8, 2025 01:50AM


#### VULNERABILITY DETAILS

It looks like `partition_alloc` stores raw pointers in the heap sandbox and then uses them without any sanitization. This allows overwriting the head of a free list when a backing store for an `ArrayBuffer` is allocated.

The value (the freelist head) from the heap sandbox is read here:

```
#10 0x00005555591adf54 in partition_alloc::internal::SlotSpanMetadata::get_freelist_head (this=0x7ac000001020) at ../../third_party/partition_alloc/src/partition_alloc/partition_page.h:224
#11 partition_alloc::PartitionRoot::AllocFromBucket<(partition_alloc::internal::AllocFlags)15> (this=<optimized out>, bucket=<optimized out>, raw_size=<optimized out>, slot_span_alignment=<optimized out>, is_already_zeroed=<optimized out>, 
    usable_size=<optimized out>, slot_size=<optimized out>) at ../../third_party/partition_alloc/src/partition_alloc/partition_root.h:1235
#12 partition_alloc::PartitionRoot::RawAlloc<(partition_alloc::internal::AllocFlags)15> (this=<optimized out>, bucket=<optimized out>, raw_size=<optimized out>, slot_span_alignment=<optimized out>, is_already_zeroed=<optimized out>, 
    usable_size=<optimized out>, slot_size=<optimized out>) at ../../third_party/partition_alloc/src/partition_alloc/partition_root.h:2266
#13 partition_alloc::PartitionRoot::AllocInternalNoHooks<(partition_alloc::internal::AllocFlags)15> (this=<optimized out>, requested_size=<optimized out>, slot_span_alignment=<optimized out>)
    at ../../third_party/partition_alloc/src/partition_alloc/partition_root.h:2167
#14 partition_alloc::PartitionRoot::AllocInternal<(partition_alloc::internal::AllocFlags)15> (this=<optimized out>, requested_size=<optimized out>, slot_span_alignment=<optimized out>, type_name=<optimized out>)
    at ../../third_party/partition_alloc/src/partition_alloc/partition_root.h:2083
#15 partition_alloc::PartitionRoot::AllocInline<(partition_alloc::internal::AllocFlags)15> (this=<optimized out>, requested_size=<optimized out>, type_name=<optimized out>) at ../../third_party/partition_alloc/src/partition_alloc/partition_root.h:538
#16 v8::internal::PABackedSandboxedArrayBufferAllocator::Impl::AllocateInternal<(partition_alloc::internal::AllocFlags)3> (this=<optimized out>, length=<optimized out>) at ./../../src/init/isolate-group.cc:620
#17 0x0000555558b400c5 in std::__Cr::__function::__policy_func<void* (unsigned long)>::operator()(unsigned long&&) const (this=0x7bfff5a9a020, __args=<optimized out>) at gen/third_party/libc++/src/include/__functional/function.h:502
#18 std::__Cr::function<void* (unsigned long)>::operator()(unsigned long) const (this=0x7bfff5a9a020, __arg=0x57) at gen/third_party/libc++/src/include/__functional/function.h:754
#19 v8::internal::Heap::AllocateExternalBackingStore(std::__Cr::function<void* (unsigned long)> const&, unsigned long) (this=<optimized out>, allocate=..., byte_length=<optimized out>) at ./../../src/heap/heap.cc:3151
#20 0x000055555963a3a9 in v8::internal::BackingStore::Allocate (isolate=<optimized out>, byte_length=<optimized out>, shared=<optimized out>, initialized=<optimized out>) at ./../../src/objects/backing-store.cc:231
#21 0x000055555809bd8e in v8::internal::(anonymous namespace)::TryAllocateBackingStore (isolate=<optimized out>, shared=<optimized out>, resizable=<optimized out>, length=..., max_length=..., initialized=<optimized out>)
    at ./../../src/builtins/builtins-arraybuffer.cc:68
#22 v8::internal::(anonymous namespace)::ConstructBuffer (isolate=<optimized out>, target=..., new_target=..., length=..., max_length=..., initialized=<optimized out>) at ./../../src/builtins/builtins-arraybuffer.cc:119
#23 0x00005555580935d7 in v8::internal::Builtin_Impl_ArrayBufferConstructor (args=..., isolate=<optimized out>) at ./../../src/builtins/builtins-arraybuffer.cc:186
#24 0x0000555561033f36 in Builtins_CEntry_Return1_ArgvOnStack_BuiltinExit ()
#25 0x0000555560f89273 in Builtins_InterpreterPushArgsThenFastConstructFunction ()
```

Before the actual OOB writes happen, several reads are performed; thus, the provided reproducer fails with an OOB read if an address is provided that can not be read. If the reads succeeded, `memset` is called for the controlled address here:

```
#1  0x00005555568a450b in __asan_memset ()
#2  0x000055555758fb49 in AllocInternalNoHooks<(partition_alloc::internal::AllocFlags)15> () at ../../third_party/partition_alloc/src/partition_alloc/partition_root.h:2238
#3  AllocInternal<(partition_alloc::internal::AllocFlags)15> () at ../../third_party/partition_alloc/src/partition_alloc/partition_root.h:2083
#4  AllocInline<(partition_alloc::internal::AllocFlags)15> () at ../../third_party/partition_alloc/src/partition_alloc/partition_root.h:538
#5  AllocateInternal<(partition_alloc::internal::AllocFlags)3> () at ../../src/init/isolate-group.cc:620
#6  0x0000555557243abf in operator() () at gen/third_party/libc++/src/include/__functional/function.h:502
#7  operator() () at gen/third_party/libc++/src/include/__functional/function.h:754
#8  AllocateExternalBackingStore () at ../../src/heap/heap.cc:3151
#9  0x00005555577d9aac in Allocate () at ../../src/objects/backing-store.cc:231
#10 0x0000555556d511de in TryAllocateBackingStore () at ../../src/builtins/builtins-arraybuffer.cc:68
#11 ConstructBuffer () at ../../src/builtins/builtins-arraybuffer.cc:119
#12 0x0000555556d4c3c8 in Builtin_Impl_ArrayBufferConstructor () at ../../src/builtins/builtins-arraybuffer.cc:186
#13 0x000055555b6fad36 in Builtins_CEntry_Return1_ArgvOnStack_BuiltinExit ()
#14 0x000055555b650073 in Builtins_InterpreterPushArgsThenFastConstructFunction ()

x/4i $pc
=> 0x7ffff7dfe3c9 <__memset_evex_unaligned_erms+137>:	vmovdqu64 YMMWORD PTR [rdi],ymm16
   0x7ffff7dfe3cf <__memset_evex_unaligned_erms+143>:	vmovdqu64 YMMWORD PTR [rdi+0x20],ymm16
   0x7ffff7dfe3d6 <__memset_evex_unaligned_erms+150>:	cmp    rdx,0x80
   0x7ffff7dfe3dd <__memset_evex_unaligned_erms+157>:	jbe    0x7ffff7dfe368 <__memset_evex_unaligned_erms+40>
```

The easiest way for me to observe the behaviour shown above was to run the reproducer using `gdb` once, and then get the address of the JIT mapping:

```
0x00005555bb640000 0x00005555db640000 0x0000000000000000 rwx 
```

And putting the value in the `setBigUint64` call within the reproduce:

```
sbx_mem.setBigUint64(addr, BigInt(0x00005555bb640000), true);
```

If this can be improved, please don't hesitate to reach out. Also, I would appreciate it if you could tell me whether this counts as "controlled write", or if the written value must be under control as well?

#### VERSION

V8 Git Commit: b5aa4c8b718d75f9cf4d4afd635ffd217f0acb38 (Sat Sep 6 21:01:45 2025 -0700)

#### REPRODUCTION CASE

```
d8  --fuzzing --sandbox-fuzzing --single-threaded bug.js
```

**ASan Report** I was not able to get a nice ASan report for the release build, but this is the one on my fuzzing build.

```
==2394399==ERROR: AddressSanitizer: unknown-crash on address 0x040012345678 at pc 0x55555783d8d0 bp 0x7fffffffd1b0 sp 0x7fffffffd188
WRITE of size 112 at 0x040012345678 thread T0
    #0 0x55555783d8cf in __asan_memset compiler-rt/lib/asan/asan_interceptors_memintrinsics.cpp:67:3
    #1 0x5555591ad864 in void* v8::internal::PABackedSandboxedArrayBufferAllocator::Impl::AllocateInternal<(partition_alloc::internal::AllocFlags)3>(unsigned long) third_party/partition_alloc/src/partition_alloc/partition_root.h:2238:5
    #2 0x555558b400c4 in v8::internal::Heap::AllocateExternalBackingStore(std::__Cr::function<void* (unsigned long)> const&, unsigned long) gen/third_party/libc++/src/include/__functional/function.h:502:12
    #3 0x55555963a3a8 in v8::internal::BackingStore::Allocate(v8::internal::Isolate*, unsigned long, v8::internal::SharedFlag, v8::internal::InitializedFlag) src/objects/backing-store.cc:231:37
    #4 0x55555809bd8d in v8::internal::(anonymous namespace)::ConstructBuffer(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::DirectHandle<v8::internal::JSReceiver>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::InitializedFlag) src/builtins/builtins-arraybuffer.cc:68:11
    #5 0x5555580935d6 in v8::internal::Builtin_Impl_ArrayBufferConstructor(v8::internal::BuiltinArguments, v8::internal::Isolate*) src/builtins/builtins-arraybuffer.cc:186:10
    #6 0x555561033f35 in Builtins_CEntry_Return1_ArgvOnStack_BuiltinExit setup-isolate-deserialize.cc
    #7 0x555560f89272 in Builtins_InterpreterPushArgsThenFastConstructFunction setup-isolate-deserialize.cc
    #8 0x55556113855d in Builtins_ConstructHandler setup-isolate-deserialize.cc
    #9 0x555560f889a9 in Builtins_InterpreterEntryTrampoline setup-isolate-deserialize.cc
    #10 0x555560f8575b in Builtins_JSEntryTrampoline setup-isolate-deserialize.cc
    #11 0x555560f854aa in Builtins_JSEntry setup-isolate-deserialize.cc
    #12 0x55555869bfeb in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/simulator.h:212:12
    #13 0x55555869f3e7 in v8::internal::Execution::CallScript(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>) src/execution/execution.cc:542:10
    #14 0x555557f03c56 in v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) src/api/api.cc:1964:7
    #15 0x5555578d4c25 in v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) src/d8/d8.cc:1040:44
    #16 0x555557947f28 in v8::SourceGroup::Execute(v8::Isolate*) src/d8/d8.cc:5502:10
    #17 0x55555795e60e in v8::Shell::RunMainIsolate(v8::Isolate*, bool) src/d8/d8.cc:6458:37
    #18 0x55555795d125 in v8::Shell::RunMain(v8::Isolate*, bool) src/d8/d8.cc:6366:18
    #19 0x555557964989 in v8::Shell::Main(int, char**) src/d8/d8.cc:7310:18
    #20 0x7ffff796e1c9 in __libc_start_call_main csu/../sysdeps/nptl/libc_start_call_main.h:58:16
    #21 0x7ffff796e28a in __libc_start_main csu/../csu/libc-start.c:360:3
    #22 0x5555577db029 in _start (/work/v8-build/v8/out/FuzzingSuppressReadsO1/d8+0x2287029) (BuildId: ba8fbe419f72dad4)

Address 0x040012345678 is located in the high shadow area.
SUMMARY: AddressSanitizer: unknown-crash third_party/partition_alloc/src/partition_alloc/partition_root.h:2238:5 in void* v8::internal::PABackedSandboxedArrayBufferAllocator::Impl::AllocateInternal<(partition_alloc::internal::AllocFlags)3>(unsigned long)
==2394399==ABORTING
```

On a release build, I am getting this error after setting the target address (`0x5555bb640000`) to the JIT RWX mapping.

```
> d8 --fuzzing --sandbox-fuzzing --single-threaded bug.js
Sandbox testing mode is enabled. Only sandbox violations will be reported, all other crashes will be ignored.
Sandbox bounds: [0x7abe00000000,0x7bbe00000000)

## V8 sandbox violation detected!

Received signal 11 <unknown> 5555bb640000

==== C stack trace ===============================

./v8/out/vanilla/d8(__interceptor_backtrace+0x46)[0x55555684c8a6]
./v8/out/vanilla/d8(+0x173d5e2)[0x555556c915e2]
/lib/x86_64-linux-gnu/libc.so.6(+0x45330)[0x7ffff7caa330]
/lib/x86_64-linux-gnu/libc.so.6(+0x1993c9)[0x7ffff7dfe3c9]
./v8/out/vanilla/d8(__asan_memset+0x7b)[0x5555568a450b]
./v8/out/vanilla/d8(+0x203bb49)[0x55555758fb49]
./v8/out/vanilla/d8(+0x1cefabf)[0x555557243abf]
./v8/out/vanilla/d8(+0x2285aac)[0x5555577d9aac]
./v8/out/vanilla/d8(+0x17fd1de)[0x555556d511de]
./v8/out/vanilla/d8(+0x17f83c8)[0x555556d4c3c8]
./v8/out/vanilla/d8(+0x61a6d36)[0x55555b6fad36]
[end of stack trace]
[1]    2401885 segmentation fault  ./v8/out/vanilla/d8 --fuzzing --sandbox-fuzzing --single-threaded 
```


---

**#2 — cl...@appspot.gserviceaccount.com — Sep 8, 2025 10:17PM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=6044431668936704](<https://clusterfuzz.com/testcase?key=6044431668936704>).


---

**#3 — cl...@appspot.gserviceaccount.com — Sep 8, 2025 10:33PM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5489349692948480](<https://clusterfuzz.com/testcase?key=5489349692948480>).


---

**#4 — 24...@project.gserviceaccount.com — Sep 8, 2025 11:16PM**

Automatically applying components based on crash stacktrace and information from OWNERS files.  
  
If this is incorrect, please apply the hotlistid:4801165.


---

**#5 — 24...@project.gserviceaccount.com — Sep 8, 2025 11:16PM**

Automatically assigning owner based on suspected regression changelist [https://chromium.googlesource.com/v8/v8/+/613d0a73d1846efb37ea9b995ee5036e03be4de9](<https://chromium.googlesource.com/v8/v8/+/613d0a73d1846efb37ea9b995ee5036e03be4de9>) (d8: Reenable PartitionAlloc  
  
Now that PA was fixed in the configuration with tsan and dchecks,  
(see c001374914bffb3db6ed024a521f3a38f11d0911A), PA should be safe  
to be reenabled.  
  
Note to sherrifs:  
There are performance regressions expected (and perhaps timeouts!),  
but this will anyway get us to the baseline (Chrome).  
There are some ongoing changes (e.g. managed zone memory) that  
will significantly alleviate many regressions.  
  
Bug: 392817524  
Change-Id: I346e5a393651e2af7852b3228f3b59d6e70e504e  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/6919646](<https://chromium-review.googlesource.com/c/v8/v8/+/6919646>)  
Commit-Queue: Anton Bikineev <[bikineev@chromium.org](<mailto:bikineev@chromium.org>)>  
Commit-Queue: Michael Lippautz <[mlippautz@chromium.org](<mailto:mlippautz@chromium.org>)>  
Reviewed-by: Michael Lippautz <[mlippautz@chromium.org](<mailto:mlippautz@chromium.org>)>  
Auto-Submit: Anton Bikineev <[bikineev@chromium.org](<mailto:bikineev@chromium.org>)>  
Cr-Commit-Position: refs/heads/main@{#102282}  
).  
  
If this is incorrect, please let us know why and apply the hotlistid:5433122. If you aren't the correct owner for this issue, please unassign yourself as soon as possible so it can be re-triaged.


---

**#6 — 24...@project.gserviceaccount.com — Sep 8, 2025 11:16PM**

Detailed Report: [https://clusterfuzz.com/testcase?key=5489349692948480](<https://clusterfuzz.com/testcase?key=5489349692948480>)  
  
Fuzzer: None  
Job Type: linux_asan_d8_sandbox_testing  
Platform Id: linux  
  
Crash Type: V8 sandbox violation  
Crash Address: 0x5555bb640000  
Crash State:  
void* v8::internal::PABackedSandboxedArrayBufferAllocator::Impl::AllocateInterna  
v8::internal::Heap::AllocateExternalBackingStore  
v8::internal::BackingStore::Allocate  
  
Sanitizer: address (ASAN)  
  
Regressed: [https://clusterfuzz.com/revisions?job=linux_asan_d8_sandbox_testing&range=102281:102282](<https://clusterfuzz.com/revisions?job=linux_asan_d8_sandbox_testing&range=102281:102282>)  
  
Reproducer Testcase: [https://clusterfuzz.com/download?testcase_id=5489349692948480](<https://clusterfuzz.com/download?testcase_id=5489349692948480>)  
  
To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.  
  
If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.  
  
If you have any feedback on reproducing test cases, let us know at [https://forms.gle/Yh3qCYFveHj6E5jz5](<https://forms.gle/Yh3qCYFveHj6E5jz5>) so we can improve.


---

**#7 — th...@chromium.org — Sep 8, 2025 11:32PM**

[security shepherd]  
Triaging as V8 sandbox bypass:  
\- Set a provisional severity of Medium (S2).  
\- Set a provisional priority of P1.  
\- Assign to the current V8 Shepherd. --> replacing this with cc-ing V8 shepherd since there is already an assignee.  
\- Apply the Security_Impact-None hotlist (hotlistID:5433277).  
\- If possible, please also apply the V8 Sandbox hotlist (hotlistID:4802478).


---

**#8 — bi...@chromium.org — Sep 10, 2025 05:51PM**

PA should have SlotSpan metadata stored outside of the superpage extent entry. However, the address of the SlotSpanMetadata (this=0x7ac000001020) suggests that it may actually be stored inline. A question to the reporter: what GN flags were used to reproduce the issue?


---

**#9 — vs...@gmail.com — Sep 10, 2025 06:08PM**

These are the GN args:

```
is_debug = false
dcheck_always_on = false
is_asan = true
v8_enable_sandbox = true
v8_enable_memory_corruption_api = true
v8_static_library = true
target_cpu = "x64"
```

Also, it looks like clusterfuzz hits the same code path as in my report, but fails because the page is not mapped RW. Probably it would be beneficial to have some `Sandbox.rw_page` address exposed via the memory corruption API to ease the process of reporting such an issue.


---

**#10 — bi...@chromium.org — Sep 11, 2025 11:29PM**

Looks like the bug happens when the ABAllocator gets initialized before any malloc allocation occurs in d8. If this happens, then the offset to the metadata is set to be "inlined":  
[https://source.chromium.org/chromium/chromium/src/+/main:base/allocator/partition_allocator/src/partition_alloc/partition_address_space.cc;l=284;drc=48d6f7175422b2c969c14258f9f8d5b196c28d18;bpv=1;bpt=1](<https://source.chromium.org/chromium/chromium/src/+/main:base/allocator/partition_allocator/src/partition_alloc/partition_address_space.cc;l=284;drc=48d6f7175422b2c969c14258f9f8d5b196c28d18;bpv=1;bpt=1>)  
This is unlikely to happen in Chrome though, however, possible for d8 now.


---

**#11 — dx...@google.com — Sep 12, 2025 01:04AM**

Project: v8/v8  
Branch: main  
Author: Anton Bikineev [bikineev@chromium.org](<mailto:bikineev@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6938258](<https://chromium-review.googlesource.com/6938258>)

AB: Fix possiblity of PA metadata being stored inlined

* * *

Expand for full commit details

```
     
    This may happen when ABAllocator gets initialized before any malloc 
    happens in d8, which would initiliaze PartitionAddressSpace. 
     
    Bug: 443475183 
    Change-Id: I13f86c6986946b951815cb2241b1d7992c17c0c4 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6938258 
    Reviewed-by: Michael Lippautz <mlippautz@chromium.org> 
    Commit-Queue: Anton Bikineev <bikineev@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#102423}
```

* * *

Files:

  * M `src/init/isolate-group.cc`

* * *

Hash: [8398f9aa445af42c44d52a771e2fd3a9605b3573](<https://chromiumdash.appspot.com/commit/8398f9aa445af42c44d52a771e2fd3a9605b3573>)  
Date: Thu Sep 11 14:36:02 2025

* * *


---

**#12 — vs...@gmail.com — Sep 13, 2025 12:57AM**

The heap metadata still seems to be stored in the sandbox. I can still trigger the controlled write with the provided reproducer on `a5f18bb86c3b97b9bfc8f95a0926812a1282ad7c`.


---

**#13 — bi...@chromium.org — Sep 22, 2025 07:14PM**

This should be fixed by now on ToT by [https://chromium-review.googlesource.com/c/chromium/src/+/6964115](<https://chromium-review.googlesource.com/c/chromium/src/+/6964115>).


---

**#14 — wf...@chromium.org — Sep 27, 2025 05:28AM**

Hi thanks for the bug, the VRP panel decided to reward $5000 for this issue as it did not demonstrate a full control of write both address and value - but if you are able to demonstrate this we would be happy to reconsider this for the full v8 sandbox bypass. Please add any further info to this bug and one of the team will make sure to fully triage any additional comments.


---

**#15 — sp...@google.com — Sep 27, 2025 06:01AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $5000.00 for this report.  
  
Rationale for this decision:  
v8 sandbox bypass with not fully control of value written  
  
  
Important: This payment will be issued by Bugcrowd. You will receive an email from Bugcrowd in the next 24 hours which contains a submission you must claim to be rewarded.  
  
If you do not receive an email from them, please check your spam folder and then reach out to us via a comment here. For issues related to Bugcrowd itself, please contact them via [https://bugcrowd.com/support](<https://bugcrowd.com/support>).  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#16 — ch...@google.com — Dec 30, 2025 09:40PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.


---

**#17 — ch...@google.com — Dec 30, 2025 09:42PM**

This V8 bug has been marked as either a release blocker or a vulnerability bug. V8 bugs affect all OSs supported by Chrome, so the OS field has been updated to reflect this. Please update the bug with the correct OS field if it only affects a subset of OSes.
