# V8 Sandbox violation: UAF in RemoveFromAsyncWaiterQueueList

Issue URL: https://issues.chromium.org/issues/443182220
VRP-Reward: 5000
Date: Sep 5, 2025 08:39PM


VULNERABILITY DETAILS

We can forges two PromiseReaction/Context objects to share the same Foreign pointer that wraps a native LockAsyncWaiterQueueNode (by copying the foreign field from one reaction’s context to another). This makes two separate async-unlock paths operate on the same C++ waiter node.

On the first unlock, JSAtomicsMutex::UnlockAsyncLockedMutex removes the node from the isolate’s async_waiter_queue_nodes list, destroying the unique_ptr and freeing the node. On the second unlock, the code attempts to remove the same node again.

RemoveFromAsyncWaiterQueueList first dereferences the freed node to read node->requester_ in order to access the isolate’s list, causing a use-after-free read; remove_if then proceeds with list operations based on that stale pointer, leading to the UAF.

VERSION

V8:14.0.302

REPRODUCTION CASE

Run: ./d8 --sandbox-fuzzing --harmony-struct poc.js

FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION

Type of crash: uaf

Crash State:

```
==3919591==ERROR: AddressSanitizer: heap-use-after-free on address 0x7c38103e0468 at pc 0x55c46f72fdcf bp 0x7fffc5f12fe0 sp 0x7fffc5f12fd8
READ of size 8 at 0x7c38103e0468 thread T0
    #0 0x55c46f72fdce in RemoveFromAsyncWaiterQueueList src/objects/js-atomics-synchronization.cc:349:11
    #1 0x55c46f72fdce in v8::internal::JSAtomicsMutex::UnlockAsyncLockedMutex(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::Foreign>) src/objects/js-atomics-synchronization.cc:957:3
    #2 0x55c46e734b87 in v8::internal::(anonymous namespace)::UnlockAsyncLockedMutexFromPromiseHandler(v8::internal::Isolate*) src/builtins/builtins-atomics-synchronization.cc:40:13
    #3 0x55c46e72f778 in v8::internal::Builtin_Impl_AtomicsMutexAsyncUnlockResolveHandler(v8::internal::BuiltinArguments, v8::internal::Isolate*) src/builtins/builtins-atomics-synchronization.cc:237:7
    #4 0x55c473c65f75 in Builtins_CEntry_Return1_ArgvOnStack_BuiltinExit setup-isolate-deserialize.cc
    #5 0x55c473ce50e9 in Builtins_PromiseFulfillReactionJob setup-isolate-deserialize.cc
    #6 0x55c473be92bb in Builtins_RunMicrotasks setup-isolate-deserialize.cc
    #7 0x55c473bb54aa in Builtins_JSRunMicrotasksEntry setup-isolate-deserialize.cc
    #8 0x55c46ea10678 in Call src/execution/simulator.h:212:12
    #9 0x55c46ea10678 in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:460:41
    #10 0x55c46ea14180 in v8::internal::(anonymous namespace)::InvokeWithTryCatch(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:502:18
    #11 0x55c46ea1460b in v8::internal::Execution::TryRunMicrotasks(v8::internal::Isolate*, v8::internal::MicrotaskQueue*) src/execution/execution.cc:606:10
    #12 0x55c46eb04e55 in v8::internal::MicrotaskQueue::RunMicrotasks(v8::internal::Isolate*) src/execution/microtask-queue.cc:185:22
    #13 0x55c46eb04645 in v8::internal::MicrotaskQueue::PerformCheckpointInternal(v8::Isolate*) src/execution/microtask-queue.cc:129:3
    #14 0x55c46ea7ebf1 in PerformCheckpoint src/execution/microtask-queue.h:48:5
    #15 0x55c46ea7ebf1 in v8::internal::Isolate::FireCallCompletedCallbackInternal(v8::internal::MicrotaskQueue*) src/execution/isolate.cc:6533:44
    #16 0x55c46e59ba19 in FireCallCompletedCallback src/execution/isolate.h:1777:5
    #17 0x55c46e59ba19 in ~CallDepthScope src/api/api-inl.h:183:32
    #18 0x55c46e59ba19 in ~EnterV8InternalScope src/api/api-inl.h:259:20
    #19 0x55c46e59ba19 in v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) src/api/api.cc:1938:1
    #20 0x55c46e196ea0 in v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) src/d8/d8.cc:1033:44
    #21 0x55c46e1d8237 in v8::SourceGroup::Execute(v8::Isolate*) src/d8/d8.cc:5351:10
    #22 0x55c46e1e6768 in v8::Shell::RunMainIsolate(v8::Isolate*, bool) src/d8/d8.cc:6307:37
    #23 0x55c46e1e598e in v8::Shell::RunMain(v8::Isolate*, bool) src/d8/d8.cc:6215:18
    #24 0x55c46e1ea9a9 in v8::Shell::Main(int, char**) src/d8/d8.cc:7100:18
    #25 0x7f88110c2d79 in __libc_start_main csu/../csu/libc-start.c:308:16

0x7c38103e0468 is located 8 bytes inside of 104-byte region [0x7c38103e0460,0x7c38103e04c8)
freed by thread T0 here:
    #0 0x55c46e15b2d2 in operator delete(void*, unsigned long) (/home/user/v8_build/v8/out/release_asan_debug/d8+0x13c32d2) (BuildId: a18194e66e0b05f8)
    #1 0x55c46f738eab in operator() third_party/libc++/src/include/__memory/unique_ptr.h:77:5
    #2 0x55c46f738eab in reset third_party/libc++/src/include/__memory/unique_ptr.h:290:7
    #3 0x55c46f738eab in ~unique_ptr third_party/libc++/src/include/__memory/unique_ptr.h:259:71
    #4 0x55c46f738eab in __destroy_at<std::__Cr::unique_ptr<v8::internal::detail::WaiterQueueNode, std::__Cr::default_delete<v8::internal::detail::WaiterQueueNode> >, 0> third_party/libc++/src/include/__memory/construct_at.h:61:11
    #5 0x55c46f738eab in destroy<std::__Cr::unique_ptr<v8::internal::detail::WaiterQueueNode, std::__Cr::default_delete<v8::internal::detail::WaiterQueueNode> >, 0> third_party/libc++/src/include/__memory/allocator_traits.h:313:5
    #6 0x55c46f738eab in __delete_node third_party/libc++/src/include/list:590:5
    #7 0x55c46f738eab in clear third_party/libc++/src/include/list:655:7
    #8 0x55c46f738eab in ~__list_imp third_party/libc++/src/include/list:642:3
    #9 0x55c46f738eab in unsigned long std::__Cr::list<std::__Cr::unique_ptr<v8::internal::detail::WaiterQueueNode, std::__Cr::default_delete<v8::internal::detail::WaiterQueueNode>>, std::__Cr::allocator<std::__Cr::unique_ptr<v8::internal::detail::WaiterQueueNode, std::__Cr::default_delete<v8::internal::detail::WaiterQueueNode>>>>::remove_if<v8::internal::detail::AsyncWaiterQueueNode<v8::internal::JSAtomicsMutex>::RemoveFromAsyncWaiterQueueList(v8::internal::detail::AsyncWaiterQueueNode<v8::internal::JSAtomicsMutex>*)::'lambda'(std::__Cr::unique_ptr<v8::internal::detail::WaiterQueueNode, std::__Cr::default_delete<v8::internal::detail::WaiterQueueNode>>&)>(v8::internal::detail::AsyncWaiterQueueNode<v8::internal::JSAtomicsMutex>::RemoveFromAsyncWaiterQueueList(v8::internal::detail::AsyncWaiterQueueNode<v8::internal::JSAtomicsMutex>*)::'lambda'(std::__Cr::unique_ptr<v8::internal::detail::WaiterQueueNode, std::__Cr::default_delete<v8::internal::detail::WaiterQueueNode>>&)) third_party/libc++/src/include/list:1596:1
    #10 0x55c46f72fc56 in RemoveFromAsyncWaiterQueueList src/objects/js-atomics-synchronization.cc:349:50
    #11 0x55c46f72fc56 in v8::internal::JSAtomicsMutex::UnlockAsyncLockedMutex(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::Foreign>) src/objects/js-atomics-synchronization.cc:957:3
    #12 0x55c46e734b87 in v8::internal::(anonymous namespace)::UnlockAsyncLockedMutexFromPromiseHandler(v8::internal::Isolate*) src/builtins/builtins-atomics-synchronization.cc:40:13
    #13 0x55c46e72f778 in v8::internal::Builtin_Impl_AtomicsMutexAsyncUnlockResolveHandler(v8::internal::BuiltinArguments, v8::internal::Isolate*) src/builtins/builtins-atomics-synchronization.cc:237:7
    #14 0x55c473c65f75 in Builtins_CEntry_Return1_ArgvOnStack_BuiltinExit setup-isolate-deserialize.cc
    #15 0x55c473ce50e9 in Builtins_PromiseFulfillReactionJob setup-isolate-deserialize.cc
    #16 0x55c473be92bb in Builtins_RunMicrotasks setup-isolate-deserialize.cc
    #17 0x55c473bb54aa in Builtins_JSRunMicrotasksEntry setup-isolate-deserialize.cc
    #18 0x55c46ea10678 in Call src/execution/simulator.h:212:12
    #19 0x55c46ea10678 in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:460:41
    #20 0x55c46ea14180 in v8::internal::(anonymous namespace)::InvokeWithTryCatch(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:502:18
    #21 0x55c46ea1460b in v8::internal::Execution::TryRunMicrotasks(v8::internal::Isolate*, v8::internal::MicrotaskQueue*) src/execution/execution.cc:606:10
    #22 0x55c46eb04e55 in v8::internal::MicrotaskQueue::RunMicrotasks(v8::internal::Isolate*) src/execution/microtask-queue.cc:185:22
    #23 0x55c46eb04645 in v8::internal::MicrotaskQueue::PerformCheckpointInternal(v8::Isolate*) src/execution/microtask-queue.cc:129:3
    #24 0x55c46ea7ebf1 in PerformCheckpoint src/execution/microtask-queue.h:48:5
    #25 0x55c46ea7ebf1 in v8::internal::Isolate::FireCallCompletedCallbackInternal(v8::internal::MicrotaskQueue*) src/execution/isolate.cc:6533:44
    #26 0x55c46e59ba19 in FireCallCompletedCallback src/execution/isolate.h:1777:5
    #27 0x55c46e59ba19 in ~CallDepthScope src/api/api-inl.h:183:32
    #28 0x55c46e59ba19 in ~EnterV8InternalScope src/api/api-inl.h:259:20
    #29 0x55c46e59ba19 in v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) src/api/api.cc:1938:1
    #30 0x55c46e196ea0 in v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) src/d8/d8.cc:1033:44
    #31 0x55c46e1d8237 in v8::SourceGroup::Execute(v8::Isolate*) src/d8/d8.cc:5351:10
    #32 0x55c46e1e6768 in v8::Shell::RunMainIsolate(v8::Isolate*, bool) src/d8/d8.cc:6307:37
    #33 0x55c46e1e598e in v8::Shell::RunMain(v8::Isolate*, bool) src/d8/d8.cc:6215:18
    #34 0x55c46e1ea9a9 in v8::Shell::Main(int, char**) src/d8/d8.cc:7100:18
    #35 0x7f88110c2d79 in __libc_start_main csu/../csu/libc-start.c:308:16

previously allocated by thread T0 here:
    #0 0x55c46e15a66d in operator new(unsigned long) (/home/user/v8_build/v8/out/release_asan_debug/d8+0x13c266d) (BuildId: a18194e66e0b05f8)
    #1 0x55c46f72e825 in v8::internal::detail::AsyncWaiterQueueNode<v8::internal::JSAtomicsMutex>::NewLockedAsyncWaiterStoredInIsolate(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSAtomicsMutex>) src/objects/js-atomics-synchronization.cc:291:9
    #2 0x55c46f72e14d in v8::internal::JSAtomicsMutex::LockOrEnqueuePromise(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSAtomicsMutex>, v8::internal::DirectHandle<v8::internal::Object>, std::__Cr::optional<v8::base::TimeDelta>) src/objects/js-atomics-synchronization.cc:847:19
    #3 0x55c46e72ecee in v8::internal::Builtin_Impl_AtomicsMutexLockAsync(v8::internal::BuiltinArguments, v8::internal::Isolate*) src/builtins/builtins-atomics-synchronization.cc:223:3
    #4 0x55c473c65f75 in Builtins_CEntry_Return1_ArgvOnStack_BuiltinExit setup-isolate-deserialize.cc
    #5 0x55c473bb8934 in Builtins_InterpreterEntryTrampoline setup-isolate-deserialize.cc
    #6 0x55c473bb8934 in Builtins_InterpreterEntryTrampoline setup-isolate-deserialize.cc
    #7 0x55c473bb555b in Builtins_JSEntryTrampoline setup-isolate-deserialize.cc
    #8 0x55c473bb52aa in Builtins_JSEntry setup-isolate-deserialize.cc
    #9 0x55c46ea10e3d in Call src/execution/simulator.h:212:12
    #10 0x55c46ea10e3d in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:442:22
    #11 0x55c46ea13748 in v8::internal::Execution::CallScript(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>) src/execution/execution.cc:542:10
    #12 0x55c46e59b6e7 in v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) src/api/api.cc:1937:7
    #13 0x55c46e196ea0 in v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) src/d8/d8.cc:1033:44
    #14 0x55c46e1d8237 in v8::SourceGroup::Execute(v8::Isolate*) src/d8/d8.cc:5351:10
    #15 0x55c46e1e6768 in v8::Shell::RunMainIsolate(v8::Isolate*, bool) src/d8/d8.cc:6307:37
    #16 0x55c46e1e598e in v8::Shell::RunMain(v8::Isolate*, bool) src/d8/d8.cc:6215:18
    #17 0x55c46e1ea9a9 in v8::Shell::Main(int, char**) src/d8/d8.cc:7100:18
    #18 0x7f88110c2d79 in __libc_start_main csu/../csu/libc-start.c:308:16

SUMMARY: AddressSanitizer: heap-use-after-free src/objects/js-atomics-synchronization.cc:349:11 in RemoveFromAsyncWaiterQueueList
Shadow bytes around the buggy address:
  0x7c38103e0180: fa fa fa fa 00 00 00 00 00 00 00 00 00 00 00 00
  0x7c38103e0200: 00 fa fa fa fa fa fa fa fa fa 00 00 00 00 00 00
  0x7c38103e0280: 00 00 00 00 00 00 00 fa fa fa fa fa fa fa fa fa
  0x7c38103e0300: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 fa fa
  0x7c38103e0380: fa fa fa fa fa fa 00 00 00 00 00 00 00 00 00 00
=>0x7c38103e0400: 00 00 00 fa fa fa fa fa fa fa fa fa fd[fd]fd fd
  0x7c38103e0480: fd fd fd fd fd fd fd fd fd fa fa fa fa fa fa fa
  0x7c38103e0500: fa fa 00 00 00 00 00 00 00 00 00 00 00 00 00 fa
  0x7c38103e0580: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x7c38103e0600: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x7c38103e0680: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
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
==3919591==ABORTING

## V8 sandbox violation detected!
```

CREDIT INFORMATION

Reporter credit: Picasso


---

**#2 — th...@chromium.org — Sep 6, 2025 12:18AM**

[security shepherd]  
Triaging this as a V8 Sandbox bypass:  
\- Set a provisional severity of Medium (S2).  
\- Set a provisional priority of P1.  
\- Assign to the current V8 Shepherd.  
\- Apply the Security_Impact-None hotlist (hotlistID:5433277).  
\- If possible, please also apply the V8 Sandbox hotlist (hotlistID:4802478).


---

**#3 — pa...@google.com — Sep 8, 2025 08:46PM**

CYPTAL?

Related changes:

  * [https://chromium-review.googlesource.com/c/v8/v8/+/5507046](<https://chromium-review.googlesource.com/c/v8/v8/+/5507046>)
  * [https://chromium-review.googlesource.com/c/v8/v8/+/6001666](<https://chromium-review.googlesource.com/c/v8/v8/+/6001666>)


---

**#4 — dx...@google.com — Sep 9, 2025 11:37PM**

Project: v8/v8  
Branch: main  
Author: Nikolaos Papaspyrou [nikolaos@chromium.org](<mailto:nikolaos@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6929545](<https://chromium-review.googlesource.com/6929545>)

[shared-struct] Guard against Atomics.Mutex.lockAsync abuses

* * *

Expand for full commit details

```
     
    This CL fixes a UAF that can occur with --sandbox-fuzzing, by setting 
    the same WaitAsyncWaiterQueueNode for two different mutexes. 
     
    Bug: 443182220 
    Change-Id: Ic48fa48fe2dd628cf1b3c11becd4915afe828bb6 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6929545 
    Reviewed-by: Michael Lippautz <mlippautz@chromium.org> 
    Commit-Queue: Nikolaos Papaspyrou <nikolaos@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#102355}
```

* * *

Files:

  * M `src/objects/js-atomics-synchronization.cc`
  * A `test/mjsunit/sandbox/regress-443182220.js`

* * *

Hash: [df48074d0e652501f234ab26ff919fe8b05b84a1](<https://chromiumdash.appspot.com/commit/df48074d0e652501f234ab26ff919fe8b05b84a1>)  
Date: Tue Sep 9 12:48:34 2025

* * *


---

**#5 — ni...@chromium.org — Sep 9, 2025 11:37PM**

This should be fixed by the above.  
Thanks for reporting!


---

**#6 — sp...@google.com — Sep 20, 2025 04:56AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $5000.00 for this report.  
  
Rationale for this decision:  
v8 sandbox bypass with uncontrolled read  
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#7 — ch...@google.com — Dec 17, 2025 09:45PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.


---

**#8 — ch...@google.com — Dec 18, 2025 09:44PM**

This V8 bug has been marked as either a release blocker or a vulnerability bug. V8 bugs affect all OSs supported by Chrome, so the OS field has been updated to reflect this. Please update the bug with the correct OS field if it only affects a subset of OSes.
