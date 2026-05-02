# Sandbox violation: Still UAF in RemoveFromAsyncWaiterQueueList

Issue URL: https://issues.chromium.org/issues/447307165
VRP-Reward: 5000
Date: Sep 25, 2025 08:43PM


## VULNERABILITY DETAILS

This is a bypass of the fix of [issue/443182220](<https://issuetracker.google.com/issues/443182220>).

### Fix Analysis

```
static void RemoveFromAsyncWaiterQueueList(Isolate* requester,
                                             AsyncWaiterQueueNode<T>* node) {
    auto erased =
        std::erase_if(requester->async_waiter_queue_nodes(),
                      [requester, node](std::unique_ptr<WaiterQueueNode>& n) {
                        if (n.get() == node) {
                          SBXCHECK_EQ(requester, node->requester_);
                          return true;
                        }
                        return false;
                      });
    SBXCHECK_EQ(1, erased);
  }
```

The delete helper now:

  1. Takes the current Isolate* requester as an explicit argument.
  2. Ensures the node being deleted belongs to that isolate.
  3. Asserts that exactly one element was removed from the isolate-owned list.

The unlock pathway still trusts a Foreign<kWaiterQueueForeignTag> to resolve a native pointer purely by tag, with no ownership or queue-membership revalidation at dereference time.

### Bypass

Use a single mutex; call lockAsync twice.

  1. First call acquires the lock and schedules its unlock reaction to run first.
  2. Second call contends, goes slow-path, and creates a node that is enqueued in the mutex’s waiter ring.
  3. Overwrite the Foreign handle in the first reaction with the handle from the second reaction.

When the first unlock-reaction runs, it resolves the Foreign<kWaiterQueueForeignTag> to the second (still-enqueued) node and deletes it from the isolate’s async_waiter_queue_nodes list (passing both SBXCHECKs), but the mutex’s ring still holds the raw pointer to this node.

Subsequently, ring operations perform writes through dangling pointers (write-after-free) in native memory outside the sandbox.

## VERSION

V8: 14.2.204

## REPRODUCTION CASE

Run:

```
./d8 --sandbox-fuzzing --harmony-struct poc.js
```

### Type of crash:

UAF

### Crash State:

```
==1606834==ERROR: AddressSanitizer: heap-use-after-free on address 0x7bd4bb2e0520 at pc 0x563f15073574 bp 0x7ffe27a04710 sp 0x7ffe27a04708
READ of size 8 at 0x7bd4bb2e0520 thread T0
    #0 0x563f15073573 in DequeueMatching src/objects/waiter-queue-node.cc
    #1 0x563f15073573 in v8::internal::detail::WaiterQueueNode::Dequeue(v8::internal::detail::WaiterQueueNode**) src/objects/waiter-queue-node.cc:101:10
    #2 0x563f14d1a546 in v8::internal::JSAtomicsMutex::UnlockSlowPath(v8::internal::Isolate*, std::__Cr::atomic<unsigned int>*) src/objects/js-atomics-synchronization.cc:810:31
    #3 0x563f13d3cbb7 in v8::internal::(anonymous namespace)::UnlockAsyncLockedMutexFromPromiseHandler(v8::internal::Isolate*) src/builtins/builtins-atomics-synchronization.cc:40:13
    #4 0x563f13d377a8 in v8::internal::Builtin_Impl_AtomicsMutexAsyncUnlockResolveHandler(v8::internal::BuiltinArguments, v8::internal::Isolate*) src/builtins/builtins-atomics-synchronization.cc:237:7
    #5 0x563f19762e35 in Builtins_CEntry_Return1_ArgvOnStack_BuiltinExit setup-isolate-deserialize.cc
    #6 0x563f197e0769 in Builtins_PromiseFulfillReactionJob setup-isolate-deserialize.cc
    #7 0x563f196e7906 in Builtins_RunMicrotasks setup-isolate-deserialize.cc
    #8 0x563f196b37ea in Builtins_JSRunMicrotasksEntry setup-isolate-deserialize.cc
    #9 0x563f14018176 in Call src/execution/simulator.h:212:12
    #10 0x563f14018176 in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:460:41
    #11 0x563f1401b850 in v8::internal::(anonymous namespace)::InvokeWithTryCatch(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:502:18
    #12 0x563f1401bcdb in v8::internal::Execution::TryRunMicrotasks(v8::internal::Isolate*, v8::internal::MicrotaskQueue*) src/execution/execution.cc:606:10
    #13 0x563f1410ebf5 in v8::internal::MicrotaskQueue::RunMicrotasks(v8::internal::Isolate*) src/execution/microtask-queue.cc:185:22
    #14 0x563f1410e3e5 in v8::internal::MicrotaskQueue::PerformCheckpointInternal(v8::Isolate*) src/execution/microtask-queue.cc:129:3
    #15 0x563f14087ee1 in PerformCheckpoint src/execution/microtask-queue.h:48:5
    #16 0x563f14087ee1 in v8::internal::Isolate::FireCallCompletedCallbackInternal(v8::internal::MicrotaskQueue*) src/execution/isolate.cc:6609:44
    #17 0x563f13bfa09c in FireCallCompletedCallback src/execution/isolate.h:1782:5
    #18 0x563f13bfa09c in v8::CallDepthScope<true>::~CallDepthScope() src/api/api-inl.h:183:17
    #19 0x563f13ba5de7 in ~EnterV8InternalScope src/api/api-inl.h:259:20
    #20 0x563f13ba5de7 in v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) src/api/api.cc:1954:1
    #21 0x563f1379bb4f in v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) src/d8/d8.cc:1036:44
    #22 0x563f137df8a7 in v8::SourceGroup::Execute(v8::Isolate*) src/d8/d8.cc:5488:10
    #23 0x563f137edc98 in v8::Shell::RunMainIsolate(v8::Isolate*, bool) src/d8/d8.cc:6444:37
    #24 0x563f137ecebe in v8::Shell::RunMain(v8::Isolate*, bool) src/d8/d8.cc:6352:18
    #25 0x563f137f1ea8 in v8::Shell::Main(int, char**) src/d8/d8.cc:7242:18
    #26 0x7f24bbd6ed79 in __libc_start_main csu/../csu/libc-start.c:308:16

0x7bd4bb2e0520 is located 16 bytes inside of 104-byte region [0x7bd4bb2e0510,0x7bd4bb2e0578)
freed by thread T0 here:
    #0 0x563f13760d82 in operator delete(void*, unsigned long) (/home/user/v8_build/v8/out/release_asan_14_2_204/d8+0x13d3d82) (BuildId: 14c013b31915d377)
    #1 0x563f14d25fab in operator() gen/third_party/libc++/src/include/__memory/unique_ptr.h:77:5
    #2 0x563f14d25fab in reset gen/third_party/libc++/src/include/__memory/unique_ptr.h:290:7
    #3 0x563f14d25fab in ~unique_ptr gen/third_party/libc++/src/include/__memory/unique_ptr.h:259:71
    #4 0x563f14d25fab in __destroy_at<std::__Cr::unique_ptr<v8::internal::detail::WaiterQueueNode, std::__Cr::default_delete<v8::internal::detail::WaiterQueueNode> >, 0> gen/third_party/libc++/src/include/__memory/construct_at.h:61:11
    #5 0x563f14d25fab in destroy<std::__Cr::unique_ptr<v8::internal::detail::WaiterQueueNode, std::__Cr::default_delete<v8::internal::detail::WaiterQueueNode> >, 0> gen/third_party/libc++/src/include/__memory/allocator_traits.h:313:5
    #6 0x563f14d25fab in __delete_node gen/third_party/libc++/src/include/list:590:5
    #7 0x563f14d25fab in clear gen/third_party/libc++/src/include/list:655:7
    #8 0x563f14d25fab in ~__list_imp gen/third_party/libc++/src/include/list:642:3
    #9 0x563f14d25fab in unsigned long std::__Cr::list<std::__Cr::unique_ptr<v8::internal::detail::WaiterQueueNode, std::__Cr::default_delete<v8::internal::detail::WaiterQueueNode>>, std::__Cr::allocator<std::__Cr::unique_ptr<v8::internal::detail::WaiterQueueNode, std::__Cr::default_delete<v8::internal::detail::WaiterQueueNode>>>>::remove_if<v8::internal::detail::AsyncWaiterQueueNode<v8::internal::JSAtomicsMutex>::RemoveFromAsyncWaiterQueueList(v8::internal::Isolate*, v8::internal::detail::AsyncWaiterQueueNode<v8::internal::JSAtomicsMutex>*)::'lambda'(std::__Cr::unique_ptr<v8::internal::detail::WaiterQueueNode, std::__Cr::default_delete<v8::internal::detail::WaiterQueueNode>>&)>(v8::internal::detail::AsyncWaiterQueueNode<v8::internal::JSAtomicsMutex>::RemoveFromAsyncWaiterQueueList(v8::internal::Isolate*, v8::internal::detail::AsyncWaiterQueueNode<v8::internal::JSAtomicsMutex>*)::'lambda'(std::__Cr::unique_ptr<v8::internal::detail::WaiterQueueNode, std::__Cr::default_delete<v8::internal::detail::WaiterQueueNode>>&)) gen/third_party/libc++/src/include/list:1596:1
    #10 0x563f14d1cd30 in erase_if<std::__Cr::unique_ptr<v8::internal::detail::WaiterQueueNode, std::__Cr::default_delete<v8::internal::detail::WaiterQueueNode> >, std::__Cr::allocator<std::__Cr::unique_ptr<v8::internal::detail::WaiterQueueNode, std::__Cr::default_delete<v8::internal::detail::WaiterQueueNode> > >, (lambda at ../../src/objects/js-atomics-synchronization.cc:352:23)> gen/third_party/libc++/src/include/list:1792:14
    #11 0x563f14d1cd30 in RemoveFromAsyncWaiterQueueList src/objects/js-atomics-synchronization.cc:351:9
    #12 0x563f14d1cd30 in v8::internal::JSAtomicsMutex::UnlockAsyncLockedMutex(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::Foreign>) src/objects/js-atomics-synchronization.cc:966:3
    #13 0x563f13d3cbb7 in v8::internal::(anonymous namespace)::UnlockAsyncLockedMutexFromPromiseHandler(v8::internal::Isolate*) src/builtins/builtins-atomics-synchronization.cc:40:13
    #14 0x563f13d377a8 in v8::internal::Builtin_Impl_AtomicsMutexAsyncUnlockResolveHandler(v8::internal::BuiltinArguments, v8::internal::Isolate*) src/builtins/builtins-atomics-synchronization.cc:237:7
    #15 0x563f19762e35 in Builtins_CEntry_Return1_ArgvOnStack_BuiltinExit setup-isolate-deserialize.cc
    #16 0x563f197e0769 in Builtins_PromiseFulfillReactionJob setup-isolate-deserialize.cc
    #17 0x563f196e7906 in Builtins_RunMicrotasks setup-isolate-deserialize.cc
    #18 0x563f196b37ea in Builtins_JSRunMicrotasksEntry setup-isolate-deserialize.cc
    #19 0x563f14018176 in Call src/execution/simulator.h:212:12
    #20 0x563f14018176 in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:460:41
    #21 0x563f1401b850 in v8::internal::(anonymous namespace)::InvokeWithTryCatch(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:502:18
    #22 0x563f1401bcdb in v8::internal::Execution::TryRunMicrotasks(v8::internal::Isolate*, v8::internal::MicrotaskQueue*) src/execution/execution.cc:606:10
    #23 0x563f1410ebf5 in v8::internal::MicrotaskQueue::RunMicrotasks(v8::internal::Isolate*) src/execution/microtask-queue.cc:185:22
    #24 0x563f1410e3e5 in v8::internal::MicrotaskQueue::PerformCheckpointInternal(v8::Isolate*) src/execution/microtask-queue.cc:129:3
    #25 0x563f14087ee1 in PerformCheckpoint src/execution/microtask-queue.h:48:5
    #26 0x563f14087ee1 in v8::internal::Isolate::FireCallCompletedCallbackInternal(v8::internal::MicrotaskQueue*) src/execution/isolate.cc:6609:44
    #27 0x563f13bfa09c in FireCallCompletedCallback src/execution/isolate.h:1782:5
    #28 0x563f13bfa09c in v8::CallDepthScope<true>::~CallDepthScope() src/api/api-inl.h:183:17
    #29 0x563f13ba5de7 in ~EnterV8InternalScope src/api/api-inl.h:259:20
    #30 0x563f13ba5de7 in v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) src/api/api.cc:1954:1
    #31 0x563f1379bb4f in v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) src/d8/d8.cc:1036:44
    #32 0x563f137df8a7 in v8::SourceGroup::Execute(v8::Isolate*) src/d8/d8.cc:5488:10
    #33 0x563f137edc98 in v8::Shell::RunMainIsolate(v8::Isolate*, bool) src/d8/d8.cc:6444:37
    #34 0x563f137ecebe in v8::Shell::RunMain(v8::Isolate*, bool) src/d8/d8.cc:6352:18
    #35 0x563f137f1ea8 in v8::Shell::Main(int, char**) src/d8/d8.cc:7242:18
    #36 0x7f24bbd6ed79 in __libc_start_main csu/../csu/libc-start.c:308:16

previously allocated by thread T0 here:
    #0 0x563f1376017d in operator new(unsigned long) (/home/user/v8_build/v8/out/release_asan_14_2_204/d8+0x13d317d) (BuildId: 14c013b31915d377)
    #1 0x563f14d1cabf in v8::internal::detail::AsyncWaiterQueueNode<v8::internal::JSAtomicsMutex>::NewAsyncWaiterStoredInIsolate(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSAtomicsMutex>, v8::internal::Handle<v8::internal::JSPromise>, v8::internal::MaybeHandle<v8::internal::JSPromise>) src/objects/js-atomics-synchronization.cc:277:50
    #2 0x563f14d1c778 in v8::internal::JSAtomicsMutex::LockAsyncSlowPath(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSAtomicsMutex>, std::__Cr::atomic<unsigned int>*, v8::internal::Handle<v8::internal::JSPromise>, v8::internal::MaybeHandle<v8::internal::JSPromise>, v8::internal::detail::AsyncWaiterQueueNode<v8::internal::JSAtomicsMutex>**, std::__Cr::optional<v8::base::TimeDelta>) src/objects/js-atomics-synchronization.cc:927:7
    #3 0x563f14d24d8e in v8::internal::JSAtomicsMutex::LockAsync(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSAtomicsMutex>, v8::internal::Handle<v8::internal::JSPromise>, v8::internal::MaybeHandle<v8::internal::JSPromise>, v8::internal::detail::AsyncWaiterQueueNode<v8::internal::JSAtomicsMutex>**, std::__Cr::optional<v8::base::TimeDelta>)::$_0::operator()(std::__Cr::atomic<unsigned int>*) const src/objects/js-atomics-synchronization.cc:879:16
    #4 0x563f14d1b4d1 in LockImpl<(lambda at ../../src/objects/js-atomics-synchronization.cc:878:43), std::__Cr::enable_if<true, void> > src/objects/js-atomics-synchronization-inl.h:173:14
    #5 0x563f14d1b4d1 in LockAsync src/objects/js-atomics-synchronization.cc:878:7
    #6 0x563f14d1b4d1 in v8::internal::JSAtomicsMutex::LockOrEnqueuePromise(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSAtomicsMutex>, v8::internal::DirectHandle<v8::internal::Object>, std::__Cr::optional<v8::base::TimeDelta>) src/objects/js-atomics-synchronization.cc:850:17
    #7 0x563f13d36d1e in v8::internal::Builtin_Impl_AtomicsMutexLockAsync(v8::internal::BuiltinArguments, v8::internal::Isolate*) src/builtins/builtins-atomics-synchronization.cc:223:3
    #8 0x563f19762e35 in Builtins_CEntry_Return1_ArgvOnStack_BuiltinExit setup-isolate-deserialize.cc
    #9 0x563f196b6ae9 in Builtins_InterpreterEntryTrampoline setup-isolate-deserialize.cc
    #10 0x563f196b6ae9 in Builtins_InterpreterEntryTrampoline setup-isolate-deserialize.cc
    #11 0x563f196b389b in Builtins_JSEntryTrampoline setup-isolate-deserialize.cc
    #12 0x563f196b35ea in Builtins_JSEntry setup-isolate-deserialize.cc
    #13 0x563f1401853e in Call src/execution/simulator.h:212:12
    #14 0x563f1401853e in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:442:22
    #15 0x563f1401ae18 in v8::internal::Execution::CallScript(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>) src/execution/execution.cc:542:10
    #16 0x563f13ba5cc0 in v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) src/api/api.cc:1953:7
    #17 0x563f1379bb4f in v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) src/d8/d8.cc:1036:44
    #18 0x563f137df8a7 in v8::SourceGroup::Execute(v8::Isolate*) src/d8/d8.cc:5488:10
    #19 0x563f137edc98 in v8::Shell::RunMainIsolate(v8::Isolate*, bool) src/d8/d8.cc:6444:37
    #20 0x563f137ecebe in v8::Shell::RunMain(v8::Isolate*, bool) src/d8/d8.cc:6352:18
    #21 0x563f137f1ea8 in v8::Shell::Main(int, char**) src/d8/d8.cc:7242:18
    #22 0x7f24bbd6ed79 in __libc_start_main csu/../csu/libc-start.c:308:16

SUMMARY: AddressSanitizer: heap-use-after-free src/objects/waiter-queue-node.cc in DequeueMatching
Shadow bytes around the buggy address:
  0x7bd4bb2e0280: 00 00 00 00 00 00 00 fa fa fa fa fa fa fa fa fa
  0x7bd4bb2e0300: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 fa fa
  0x7bd4bb2e0380: fa fa fa fa fa fa 00 00 00 00 00 00 00 00 00 00
  0x7bd4bb2e0400: 00 00 00 fa fa fa fa fa fa fa fa fa 00 00 00 00
  0x7bd4bb2e0480: 00 00 00 00 00 00 00 00 00 fa fa fa fa fa fa fa
=>0x7bd4bb2e0500: fa fa fd fd[fd]fd fd fd fd fd fd fd fd fd fd fa
  0x7bd4bb2e0580: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x7bd4bb2e0600: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x7bd4bb2e0680: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x7bd4bb2e0700: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x7bd4bb2e0780: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
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
==1606834==ABORTING

## V8 sandbox violation detected!
```

## CREDIT INFORMATION

Reporter credit: Picasso


---

**#2 — cl...@appspot.gserviceaccount.com — Sep 26, 2025 11:46PM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5481558756491264](<https://clusterfuzz.com/testcase?key=5481558756491264>).


---

**#3 — hc...@google.com — Sep 26, 2025 11:51PM**

setting status as per V8 sandbox bypass:

  * Set a provisional severity of Medium (S2).
  * Set a provisional priority of P1.
  * Assign to the current V8 Shepherd (ishell@)
  * Apply the Security_Impact-None hotlist (hotlistID:5433277).
  * Apply the V8 Sandbox hotlist (hotlistID:4802478).

Also cced [nikolaos@chromium.org](<mailto:nikolaos@chromium.org>) as assignee of issue/443182220


---

**#4 — dx...@google.com — Oct 3, 2025 01:55AM**

Project: v8/v8  
Branch: main  
Author: Nikolaos Papaspyrou [nikolaos@chromium.org](<mailto:nikolaos@chromium.org>)  
Link: [https://chromium-review.googlesource.com/7003792](<https://chromium-review.googlesource.com/7003792>)

[shared-struct] Guard against Atomics.Mutex.lockAsync abuses, part 2

* * *

Expand for full commit details

```
     
    This CL fixes a UAF that can occur with --sandbox-fuzzing, by setting 
    the same WaitAsyncWaiterQueueNode for two different mutex lock tasks. 
     
    Bug: 447307165 
    Change-Id: I8e0f3fef294076b426f97bf81c5780a36eaf8717 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/7003792 
    Commit-Queue: Nikolaos Papaspyrou <nikolaos@chromium.org> 
    Reviewed-by: Michael Lippautz <mlippautz@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#102916}
```

* * *

Files:

  * M `src/objects/waiter-queue-node.cc`
  * M `src/objects/waiter-queue-node.h`
  * M `test/mjsunit/sandbox/regress-443182220.js`
  * A `test/mjsunit/sandbox/regress-447307165.js`

* * *

Hash: [b0157a634e584163cbe6004db3161dc16dea20f9](<https://chromiumdash.appspot.com/commit/b0157a634e584163cbe6004db3161dc16dea20f9>)  
Date: Thu Oct 2 14:30:38 2025

* * *


---

**#5 — ni...@chromium.org — Oct 6, 2025 04:28PM**

This should be fixed by the above.  
Thank you for reporting!


---

**#6 — sp...@google.com — Nov 14, 2025 02:55AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $5000.00 for this report.  
  
Rationale for this decision:  
v8 sandbox escape without demonstrating a controllable write  
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#7 — ch...@google.com — Jan 13, 2026 09:42PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
