# Security: Signal SIGSEGV in v8

Issue URL: https://issues.chromium.org/issues/325866363
VRP-Reward: 7000
Date: Feb 20, 2024 12:36AM


#### Description

je...@gmail.com created issue [ #1](</issues/325866363#comment1>)

Feb 20, 2024 12:36AM

VULNERABILITY DETAILS  
## INTRODUCE  
After bisect, it was determined that following commit caused this problem.  
  
\- Commit Info  
\- Version: 92235  
\- link: [https://crrev.com/a8ebbdaa7682de435750db680d3e127c441c2d68](<https://crrev.com/a8ebbdaa7682de435750db680d3e127c441c2d68>)   
\- Commit Message  
  
```  
commit a8ebbdaa7682de435750db680d3e127c441c2d68  
Author: Clemens Backes <[clemensb@chromium.org](<mailto:clemensb@chromium.org>)>  
Date: Wed Feb 7 15:07:13 2024 +0100  
  
[wasm] Remove indirect function tables from instance data  
  
All compilers are switched to use the WasmDispatchTable. Hence the  
fields are unused and can be removed.  
  
A follow-up CL will remove the whole WasmIndirectFunctionTable class.  
  
R=[ahaas@chromium.org](<mailto:ahaas@chromium.org>)  
  
Bug: v8:14564  
Change-Id: I06469401ab6aa1b565cd8552e98b749b96f5985d  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5272234](<https://chromium-review.googlesource.com/c/v8/v8/+/5272234>)  
Reviewed-by: Andreas Haas <[ahaas@chromium.org](<mailto:ahaas@chromium.org>)>  
Commit-Queue: Clemens Backes <[clemensb@chromium.org](<mailto:clemensb@chromium.org>)>  
Cr-Commit-Position: refs/heads/main@{#92235}  
  
```  
  
## CRASH LOG  
\- Debug output  
  
```bash  
# CMD: /tmp/d8-linux-debug-v8-component-92403/d8 --allow-natives-syntax --expose-gc --future --fuzzing --harmony --omit-quit --js-staging --wasm-staging poc.js  
# OUTPUT ==============================================================  
Received signal 11 SEGV_MAPERR 5b0000000000  
  
==== C stack trace ===============================  
  
[0x7ffff7faf873]  
[0x7ffff7faf7c2]  
[0x7ffff2642520]  
[0x7ffff5a4feaa]  
[0x7ffff5b4da52]  
[0x7ffff5846a4e]  
[0x7ffff5862cc9]  
[0x7ffff5a45da6]  
[0x7ffff5b4930f]  
[0x7ffff5a3f5f9]  
[0x7ffff5a3df6d]  
[0x7ffff5a696b8]  
[0x7ffff5a69146]  
[0x7ffff6e9643b]  
[end of stack trace]  
  
```  
  
```  
Thread 1 "d8" received signal SIGSEGV, Segmentation fault.  
0x000020ff8b22557d in ?? ()  
LEGEND: STACK | HEAP | CODE | DATA | RWX | RODATA  
──────────────────────────────────────────────────────────────────────────[ REGISTERS / show-flags off / show-compact-regs off ]───────────────────────────────────────────────────────────────────────────  
*RAX 0x117b80000000 ◂— 0x0  
RBX 0x0  
*RCX 0x2  
*RDX 0x5447c888  
*RDI 0x555559de9510 (__start___sancov_guards+3621040) ◂— 0x2e073000403b3  
*RSI 0x12df00042269 ◂— 0xf90040040000001f  
R8 0x0  
R9 0x0  
*R10 0x20ff8b225567 ◂— mov qword ptr [r13 + 0x70], 0 /* 0x7045c749 */  
*R11 0x246  
*R12 0x174594  
*R13 0x55555a6ed080 —▸ 0x5555597b6800 (Builtins_AdaptorWithBuiltinExitFrame) ◂— mov ecx, dword ptr [rdi + 0xf]  
*R14 0x117800000000 ◂— 0x10240  
*R15 0x59b00234  
*RBP 0x7fffffffcde0 —▸ 0x7fffffffce18 —▸ 0x7fffffffcfe8 —▸ 0x7fffffffd088 —▸ 0x7fffffffd0e8 ◂— ...  
*RSP 0x7fffffffcbd8 —▸ 0x55555a6ed280 —▸ 0x117800000941 ◂— 0x326000000000004  
*RIP 0x20ff8b22557d ◂— movzx ecx, byte ptr [rax + rdx + 0x2b2b] /* 0x2b2b108cb60f */  
───────────────────────────────────────────────────────────────────────────────────[ DISASM / x86-64 / set emulate on ]────────────────────────────────────────────────────────────────────────────────────  
► 0x20ff8b22557d movzx ecx, byte ptr [rax + rdx + 0x2b2b]  
0x20ff8b225585 mov edx, dword ptr [rbp - 0xe4]  
0x20ff8b22558b mov r10, rsp  
0x20ff8b22558e sub rsp, 8  
0x20ff8b225592 and rsp, 0xfffffffffffffff0  
0x20ff8b225596 mov qword ptr [rsp], r10  
0x20ff8b22559a mov esi, ecx  
0x20ff8b22559c mov edi, edx  
0x20ff8b22559e mov rax, qword ptr [rip - 0x1536]  
0x20ff8b2255a5 lea r10, [rip + 0xa]  
0x20ff8b2255ac mov qword ptr [r13 + 0x78], r10  
─────────────────────────────────────────────────────────────────────────────────────────────────[ STACK ]─────────────────────────────────────────────────────────────────────────────────────────────────  
00:0000│ rsp 0x7fffffffcbd8 —▸ 0x55555a6ed280 —▸ 0x117800000941 ◂— 0x326000000000004  
01:0008│-200 0x7fffffffcbe0 —▸ 0x7fffffffcc20 —▸ 0x7fffffffccc0 —▸ 0x55555a6ed280 —▸ 0x117800000941 ◂— ...  
02:0010│-1f8 0x7fffffffcbe8 —▸ 0x555557d7aad3 (v8::internal::(anonymous namespace)::ClearThreadInWasmScope::~ClearThreadInWasmScope()+467) ◂— mov dword ptr [rbx], 1  
03:0018│-1f0 0x7fffffffcbf0 —▸ 0x55555a5d91c0 (__afl_area_initial) ◂— 0x0  
04:0020│-1e8 0x7fffffffcbf8 —▸ 0x55555a6ed000 —▸ 0x117800000000 ◂— 0x10240  
05:0028│-1e0 0x7fffffffcc00 —▸ 0x555559a66000 (v8::internal::v8_flags) ◂— 0x100000000000000  
06:0030│-1d8 0x7fffffffcc08 —▸ 0x55555a7600c0 —▸ 0x55555a6ec1e8 ◂— 0x0  
07:0038│-1d0 0x7fffffffcc10 —▸ 0x1178001d5d91 ◂— 0xfd0000fffd0000ff  
───────────────────────────────────────────────────────────────────────────────────────────────[ BACKTRACE ]───────────────────────────────────────────────────────────────────────────────────────────────  
► 0 0x20ff8b22557d  
1 0x55555a6ed280  
2 0x7fffffffcc20  
3 0x555557d7aad3 v8::internal::(anonymous namespace)::ClearThreadInWasmScope::~ClearThreadInWasmScope()+467  
4 0x555557d7aad3 v8::internal::(anonymous namespace)::ClearThreadInWasmScope::~ClearThreadInWasmScope()+467  
5 0x555559869c4a Builtins_JSToWasmWrapperAsm+138  
6 0x55555998fbd3 Builtins_JSToWasmWrapper+2835  
7 0x5555597c672d Builtins_InterpreterEntryTrampoline+301  
──────────────────────────────────────────────────────────────────────────────────────────[ THREADS (49 TOTAL) ]───────────────────────────────────────────────────────────────────────────────────────────  
► 1 "d8" stopped: 0x20ff8b22557d  
2 "V8 DefaultWorke" stopped: 0x7ffff7c91117 <__futex_abstimed_wait_cancelable64+231>   
3 "V8 DefaultWorke" stopped: 0x7ffff7c91117 <__futex_abstimed_wait_cancelable64+231>   
4 "V8 DefaultWorke" stopped: 0x7ffff7c91117 <__futex_abstimed_wait_cancelable64+231>   
Not showing 45 thread(s). Use set context-max-threads <number of threads> to change this.  
───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────  
pwndbg> bt  
#0 0x000020ff8b22557d in ?? ()  
#1 0x000055555a6ed280 in ?? ()  
#2 0x00007fffffffcc20 in ?? ()  
#3 0x0000555557d7aad3 in v8::internal::trap_handler::SetThreadInWasm () at ../../src/trap-handler/trap-handler.h:164  
#4 v8::internal::(anonymous namespace)::ClearThreadInWasmScope::~ClearThreadInWasmScope (this=<optimized out>) at ./../../src/runtime/runtime-wasm.cc:111  
#5 0x0000555559869c4a in Builtins_JSToWasmWrapperAsm ()  
#6 0x000055555998fbd3 in Builtins_JSToWasmWrapper ()  
#7 0x00005555597c672d in Builtins_InterpreterEntryTrampoline ()  
#8 0x0000117800143891 in ?? ()  
#9 0x0000117800000061 in ?? ()  
#10 0x0000117800000061 in ?? ()  
#11 0x0000117800000061 in ?? ()  
#12 0x000011780016a5e5 in ?? ()  
#13 0x000011780016a5f5 in ?? ()  
#14 0x000011780016a63d in ?? ()  
#15 0x0000117800169df1 in ?? ()  
#16 0x0000117800168b9d in ?? ()  
#17 0x000011780016a659 in ?? ()  
#18 0x000011780016a5e5 in ?? ()  
#19 0x000011780016a5f5 in ?? ()  
#20 0x0000117800000061 in ?? ()  
#21 0x00000000000000de in ?? ()  
#22 0x000012df000421dd in ?? ()  
#23 0x0000000000000001 in ?? ()  
#24 0x000011780016811d in ?? ()  
#25 0x00001178001438ed in ?? ()  
#26 0x00007fffffffd0e8 in ?? ()  
#27 0x00005555597c672d in Builtins_InterpreterEntryTrampoline ()  
#28 0x0000117800143891 in ?? ()  
#29 0x00001178001680e5 in ?? ()  
#30 0x000011780016811d in ?? ()  
#31 0x0000117800000061 in ?? ()  
#32 0x0000117800000061 in ?? ()  
#33 0x000000000000006c in ?? ()  
#34 0x000012df00042151 in ?? ()  
#35 0x0000000000000002 in ?? ()  
#36 0x00001178001680e5 in ?? ()  
#37 0x00001178001438ed in ?? ()  
#38 0x00007fffffffd118 in ?? ()  
#39 0x00005555597c381c in Builtins_JSEntryTrampoline ()  
#40 0x0000117800143891 in ?? ()  
#41 0x000011780016a66d in ?? ()  
#42 0x00001178001680e5 in ?? ()  
#43 0x000000000000002c in ?? ()  
#44 0x00007fffffffd180 in ?? ()  
#45 0x00005555597c3547 in Builtins_JSEntry ()  
```  
  
## Other  
Please note to include the flags `--allow-natives-syntax --expose-gc --future --fuzzing --harmony --omit-quit --js-staging --wasm-staging` for clusterfuzz classification.  
  
VERSION  
Tested on v8 version: 12.3.0 - 12.4.0  
  
REPRODUCTION CASE  
1\. Download debug v8 from: gs://v8-asan/linux-debug/d8-linux-debug-v8-component-92403.zip  
2\. Run: `d8 --allow-natives-syntax --expose-gc --future --fuzzing --harmony --omit-quit --js-staging --wasm-staging poc.js`  
  
FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION  
Type of crash: tab  
  
CREDIT INFORMATION  
Reporter credit: Jerry

poc.js 

46 KB [ View](<https://issues.chromium.org/action/issues/325866363/attachments/53733989?download=false>)[ Download](<https://issues.chromium.org/action/issues/325866363/attachments/53733989?download=true>)


---

**#3 — cl...@appspot.gserviceaccount.com — Feb 20, 2024 04:34AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5072973144195072](<https://clusterfuzz.com/testcase?key=5072973144195072>).


---

**#4 — 24...@project.gserviceaccount.com — Feb 20, 2024 04:55AM**

Testcase 5072973144195072 failed to reproduce the crash. Please inspect the program output at [https://clusterfuzz.com/testcase?key=5072973144195072](<https://clusterfuzz.com/testcase?key=5072973144195072>).


---

**#5 — je...@gmail.com — Feb 20, 2024 08:15AM**

Please use Linux debug version d8 to run clusterfuzzer.  
If still failed to reproduce, please manually test it.


---

**#6 — dr...@chromium.org — Feb 20, 2024 11:17AM**

I don't see any indication that the SEGV is related to debug-only code, but it's worth a try.


---

**#7 — cl...@appspot.gserviceaccount.com — Feb 20, 2024 11:18AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=4821457208541184](<https://clusterfuzz.com/testcase?key=4821457208541184>).


---

**#8 — je...@gmail.com — Feb 20, 2024 11:27AM**

I suggest that you can manually reproduce it.  
Because I think that this maybe a race condition case.


---

**#9 — je...@gmail.com — Feb 20, 2024 04:25PM**

I can simply reproduce it in another machine, please try it :)


---

**#10 — ah...@google.com — Feb 20, 2024 08:27PM**

Thanks for the report!  
Setting a provisional severity of High (S1)  
Setting a provisional Found In of the current Extended Stable (120).  
Assigning to the current V8 sheriff.


---

**#11 — cl...@appspot.gserviceaccount.com — Feb 20, 2024 10:09PM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=6224798681595904](<https://clusterfuzz.com/testcase?key=6224798681595904>).


---

**#12 — pe...@google.com — Feb 21, 2024 12:42AM**

Setting milestone because of s0/s1 severity.


---

**#13 — pe...@google.com — Feb 21, 2024 12:42AM**

Setting Priority to P1 to match Severity s1. If this is incorrect, please reset the priority. The automation bot account won't make this change again.


---

**#14 — cl...@chromium.org — Feb 21, 2024 12:57AM**

It reproduces a bit nondeterministically for me. I'll bisect locally, and trigger another Clusterfuzz run with more trials.


---

**#15 — cl...@appspot.gserviceaccount.com — Feb 21, 2024 12:58AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5116682254614528](<https://clusterfuzz.com/testcase?key=5116682254614528>).


---

**#16 — je...@gmail.com — Feb 21, 2024 02:19PM**

hello, any update? :)


---

**#17 — cl...@chromium.org — Feb 21, 2024 07:21PM**

I can reproduce locally, and it's indeed my CL that introduced it (so your bisection was correct).  
  
I couldn't diagnose the problem yet.


---

**#18 — cl...@chromium.org — Feb 21, 2024 09:43PM**

This fails during stack iteration:

```
#0  v8::internal::MemoryChunkHeader::GetFlags (this=0x5b0000000000) at ../../src/heap/memory-chunk-header.h:176
#1  0x0000563d5a075e4d in v8::internal::MemoryChunkHeader::InYoungGeneration (this=0x5b0000000000) at ../../src/heap/memory-chunk-header.h:165
#2  0x00007f4fce7e91e9 in v8::internal::Heap::InYoungGeneration (heap_object=...) at ../../src/heap/heap-inl.h:293
#3  0x00007f4fce9dd553 in v8::internal::Heap::InYoungGeneration (object=...) at ../../src/heap/heap-inl.h:280
#4  0x00007f4fceb47b8c in v8::internal::RootScavengeVisitor::ScavengePointer (this=0x7fff2180a6a8, p=...) at ../../src/heap/scavenger.cc:934
#5  0x00007f4fceb47a81 in v8::internal::RootScavengeVisitor::VisitRootPointer (this=0x7fff2180a6a8, root=v8::internal::Root::kStackRoots, description=0x0, p=...)
    at ../../src/heap/scavenger.cc:918
#6  0x00007f4fce704d61 in v8::internal::(anonymous namespace)::VisitSpillSlot (isolate=0x563d5a7ff000, v=0x7fff2180a6a8, spill_slot=...) at ../../src/execution/frames.cc:1368
#7  0x00007f4fce7042cf in v8::internal::(anonymous namespace)::VisitSpillSlots (isolate=0x563d5a7ff000, v=0x7fff2180a6a8, first_slot_offset=..., tagged_slots=...)
    at ../../src/execution/frames.cc:1388
#8  0x00007f4fce7040bc in v8::internal::WasmFrame::Iterate (this=0x7fff21808e50, v=0x7fff2180a6a8) at ../../src/execution/frames.cc:1514
#9  0x00007f4fce72b6f4 in v8::internal::Isolate::Iterate (this=0x563d5a7ff000, v=0x7fff2180a6a8, thread=0x563d5a7ff110) at ../../src/execution/isolate.cc:621
#10 0x00007f4fce72b7b0 in v8::internal::Isolate::Iterate (this=0x563d5a7ff000, v=0x7fff2180a6a8) at ../../src/execution/isolate.cc:627
#11 0x00007f4fce9b5f51 in v8::internal::Heap::IterateStackRoots (this=0x563d5a80cdc8, v=0x7fff2180a6a8) at ../../src/heap/heap.cc:4868
#12 0x00007f4fce9b2293 in v8::internal::Heap::IterateRoots (this=0x563d5a80cdc8, v=0x7fff2180a6a8, options=..., roots_mode=v8::internal::Heap::IterateRootsMode::kMainIsolate)
    at ../../src/heap/heap.cc:4758
#13 0x00007f4fceb43a43 in v8::internal::ScavengerCollector::CollectGarbage (this=0x563d5a8562e0) at ../../src/heap/scavenger.cc:379
#14 0x00007f4fce9abc65 in v8::internal::Heap::Scavenge (this=0x563d5a80cdc8) at ../../src/heap/heap.cc:2796
#15 0x00007f4fce9aa8fa in v8::internal::Heap::PerformGarbageCollection (this=0x563d5a80cdc8, collector=v8::internal::GarbageCollector::SCAVENGER, 
    gc_reason=v8::internal::GarbageCollectionReason::kAllocationFailure, collector_reason=0x0) at ../../src/heap/heap.cc:2399
```


---

**#19 — cl...@chromium.org — Feb 21, 2024 10:56PM**

Ok, one step further: We are trying to throw a WasmRuntimeError for an OOB memory access. The instruction that triggered this is registered as a protected instruction, but for some reason we don't have a safepoint table entry for it. So we use the safepoint entry that was registered at a previous location, and that has a bit set for a spill slot that does not make sense here.  
  
The problem seems to be that we do not register safepoints for protected instructions because the frame will be unwound anyway, but then we find another safepoint and use that instead.  
I'll upload a fix to not try to use another safepoint for protected instructions.


---

**#20 — ap...@google.com — Feb 22, 2024 12:35AM**

Project: v8/v8  
Branch: main  
  
commit 955d1972ef0a32cf44fc27cd32d055a7ddc30fcf  
Author: Clemens Backes <[clemensb@chromium.org](<mailto:clemensb@chromium.org>)>  
Date: Wed Feb 21 15:14:49 2024  
  
[wasm] Ensure empty safepoints for protected instructions  
  
Protected instructions do not emit a safepoint, except in debug code.  
Hence we should not use a previously defined safepoint which might have  
tagged spill slots which are not valid any more at the protected  
instruction.  
  
R=[ahaas@chromium.org](<mailto:ahaas@chromium.org>)  
  
Fixed: 325866363  
Change-Id: I2f301def79a4532738b45ee08596f71d2f8cd499  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5309911](<https://chromium-review.googlesource.com/c/v8/v8/+/5309911>)  
Reviewed-by: Andreas Haas <[ahaas@chromium.org](<mailto:ahaas@chromium.org>)>  
Commit-Queue: Clemens Backes <[clemensb@chromium.org](<mailto:clemensb@chromium.org>)>  
Cr-Commit-Position: refs/heads/main@{#92453}  
  
M src/wasm/wasm-code-manager.cc  
  
[https://chromium-review.googlesource.com/5309911](<https://chromium-review.googlesource.com/5309911>)


---

**#21 — pe...@google.com — Feb 22, 2024 11:47AM**

This high+ V8 security issue with stable impact requires a lightweight post mortem. Please take some time to answer questions asked in this form [1] to help us improve V8 security. [1] [https://docs.google.com/forms/d/e/1FAIpQLSdSMCiEpIFLLFkMbgtulK1sf1B-idQmkFaA4XP2Rz5mN1cqWg/viewform?usp=pp_url&entry.307501673=325866363&entry.364066060=jerrylulu7@gmail.com&entry.958145677=&entry.763880440=Extended&entry.1678852700=High&entry.763402679=Blink](<https://docs.google.com/forms/d/e/1FAIpQLSdSMCiEpIFLLFkMbgtulK1sf1B-idQmkFaA4XP2Rz5mN1cqWg/viewform?usp=pp_url&entry.307501673=325866363&entry.364066060=jerrylulu7@gmail.com&entry.958145677=&entry.763880440=Extended&entry.1678852700=High&entry.763402679=Blink>)>JavaScript>WebAssembly&entry.975983575=[clemensb@chromium.org](<mailto:clemensb@chromium.org>) Please ensure to copy the full link, as otherwise some issue meta data might not be populated automatically.


---

**#22 — je...@gmail.com — Feb 22, 2024 01:27PM**

Please set found-in to 123, which not affect stable, don't need post mortem


---

**#23 — cl...@chromium.org — Feb 22, 2024 06:35PM**

Right, thanks, forgot to update this.


---

**#24 — cl...@chromium.org — Feb 22, 2024 06:37PM**

Wait, no, I didn't have my coffee yet. The bisection is bogus I think. The bug actually existed for much longer.


---

**#25 — cl...@chromium.org — Feb 22, 2024 06:42PM**

I filled the V8 postmortem.


---

**#26 — cl...@chromium.org — Feb 22, 2024 06:45PM**

I think the bug exists since this CL: [https://crrev.com/c/5008112](<https://crrev.com/c/5008112>)  
ea2045f [wasm] Don't record empty safepoints for protected instructions by Andreas Haas · 4 months ago  
  
This landed in M121.


---

**#27 — pe...@google.com — Feb 23, 2024 12:36AM**

Setting milestone because of s0/s1 severity.


---

**#28 — pe...@google.com — Feb 23, 2024 12:42AM**

This is sufficiently serious that it should be merged to stable. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M122. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately.  
This is sufficiently serious that it should be merged to beta. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M123. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately.  
Merge review required: M122 is already shipping to stable.  
  
  
Merge approved: your change passed merge requirements and is auto-approved for M123. Please go ahead and merge the CL to branch 6312 (refs/branch-heads/6312) manually. Please contact milestone owner if you have questions.  
Merge instructions: [https://chromium.googlesource.com/chromium/src.git/+/refs/heads/main/docs/process/merge_request.md](<https://chromium.googlesource.com/chromium/src.git/+/refs/heads/main/docs/process/merge_request.md>)  
Owners: govind (Android), govind (iOS), dgagnon (ChromeOS), srinivassista (Desktop)  
Thank you for fixing this security bug! We aim to ship security fixes as quickly as possible, to limit their opportunity for exploitation as an "n-day" (that is, a bug where git fixes are developed into attacks before those fixes reach users).  
  
We have determined this fix is necessary on milestone(s): [122, 123].  
  
Please answer the following questions so that we can safely process this merge request:  
1\. Which CLs should be backmerged? (Please include Gerrit links.)  
2\. Has this fix been verified on Canary to not pose any stability regressions?  
3\. Does this fix pose any potential non-verifiable stability risks?  
4\. Does this fix pose any known compatibility risks?  
5\. Does it require manual verification by the test team? If so, please describe required testing.


---

**#29 — ea...@google.com — Feb 23, 2024 12:53AM**

Please appropriate OSs label ASAP so it gets reviewed by respective release TPM for M122


---

**#30 — cl...@chromium.org — Feb 23, 2024 01:19AM**

1\. Which CLs should be backmerged? (Please include Gerrit links.)  
[https://crrev.com/c/5309911](<https://crrev.com/c/5309911>)  
  
2\. Has this fix been verified on Canary to not pose any stability regressions?  
Yes, since 124.0.6315.0.  
  
3\. Does this fix pose any potential non-verifiable stability risks?  
No  
  
4\. Does this fix pose any known compatibility risks?  
No  
  
5\. Does it require manual verification by the test team? If so, please describe required testing.  
No


---

**#31 — pe...@google.com — Feb 23, 2024 11:46AM**

This high+ V8 security issue with stable impact requires a lightweight post mortem. Please take some time to answer questions asked in this form [1] to help us improve V8 security. [1] [https://docs.google.com/forms/d/e/1FAIpQLSdSMCiEpIFLLFkMbgtulK1sf1B-idQmkFaA4XP2Rz5mN1cqWg/viewform?usp=pp_url&entry.307501673=325866363&entry.364066060=jerrylulu7@gmail.com&entry.958145677=Android](<https://docs.google.com/forms/d/e/1FAIpQLSdSMCiEpIFLLFkMbgtulK1sf1B-idQmkFaA4XP2Rz5mN1cqWg/viewform?usp=pp_url&entry.307501673=325866363&entry.364066060=jerrylulu7@gmail.com&entry.958145677=Android>), Fuchsia, Linux, Mac, Windows, Lacros, ChromeOS&entry.763880440=Extended&entry.1678852700=High&entry.763402679=Blink>JavaScript>WebAssembly&entry.975983575=[clemensb@chromium.org](<mailto:clemensb@chromium.org>) Please ensure to copy the full link, as otherwise some issue meta data might not be populated automatically.


---

**#32 — cl...@chromium.org — Feb 23, 2024 04:37PM**

Postmortem is already filed, see #c25.


---

**#33 — ap...@google.com — Feb 23, 2024 04:40PM**

Project: v8/v8  
Branch: refs/branch-heads/12.3  
  
commit 817316414172b0cb08f001630b7a2d70c3cf2aa1  
Author: Clemens Backes <[clemensb@chromium.org](<mailto:clemensb@chromium.org>)>  
Date: Wed Feb 21 15:14:49 2024  
  
Merged: [wasm] Ensure empty safepoints for protected instructions  
  
Protected instructions do not emit a safepoint, except in debug code.  
Hence we should not use a previously defined safepoint which might have  
tagged spill slots which are not valid any more at the protected  
instruction.  
  
R=[ahaas@chromium.org](<mailto:ahaas@chromium.org>)  
  
(cherry picked from commit 955d1972ef0a32cf44fc27cd32d055a7ddc30fcf)  
  
Bug: 325866363  
Change-Id: Ic261203cec4139400e3b8540db6e746961109f3e  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5317577](<https://chromium-review.googlesource.com/c/v8/v8/+/5317577>)  
Commit-Queue: Clemens Backes <[clemensb@chromium.org](<mailto:clemensb@chromium.org>)>  
Reviewed-by: Andreas Haas <[ahaas@chromium.org](<mailto:ahaas@chromium.org>)>  
Cr-Commit-Position: refs/branch-heads/12.3@{#4}  
Cr-Branched-From: a86e1971579f4165123467fa6ad378e552536b43-refs/heads/12.3.219@{#1}  
Cr-Branched-From: 21869f7f6f3e8f5a58a0b2e61e0f7412480230b1-refs/heads/main@{#92385}  
  
M src/wasm/wasm-code-manager.cc  
  
[https://chromium-review.googlesource.com/5317577](<https://chromium-review.googlesource.com/5317577>)


---

**#34 — pe...@google.com — Feb 23, 2024 04:48PM**

LTS Milestone M120  
  
This issue has been flagged as a merge candidate for Chrome OS' LTS channel. If selected, our merge team will handle any additional merges. To help us determine if this issue requires a merge to LTS, please answer this short questionnaire:  
1\. Was this issue a regression for the milestone it was found in?  
2\. Is this issue related to a change or feature merged after the latest LTS Milestone?


---

**#35 — pe...@google.com — Feb 26, 2024 11:46AM**

This issue has been approved for a merge. Please merge the fix to any appropriate branches as soon as possible!  
  
If all merges have been completed, please remove any remaining Merge-Approved labels from this issue.  
  
Thanks for your time! To disable nags, add Disable-Nags (case sensitive) to the Chromium Labels custom field.


---

**#36 — am...@chromium.org — Feb 27, 2024 06:17AM**

[https://crrev.com/c/5309911](<https://crrev.com/c/5309911>) approved for merge to M122 Stable, please merge this fix to l2.2-lkgr by EOD Thursday, 29 February so this fix can be included in the next M122 Stable update


---

**#37 — ap...@google.com — Feb 27, 2024 10:25PM**

Project: v8/v8  
Branch: refs/branch-heads/12.2  
  
commit fcd22671087044700933c47149b87af3b9e92149  
Author: Clemens Backes <[clemensb@chromium.org](<mailto:clemensb@chromium.org>)>  
Date: Wed Feb 21 15:14:49 2024  
  
Merged: [wasm] Ensure empty safepoints for protected instructions  
  
Protected instructions do not emit a safepoint, except in debug code.  
Hence we should not use a previously defined safepoint which might have  
tagged spill slots which are not valid any more at the protected  
instruction.  
  
R=[ahaas@chromium.org](<mailto:ahaas@chromium.org>)  
  
(cherry picked from commit 955d1972ef0a32cf44fc27cd32d055a7ddc30fcf)  
Bug: 325866363  
  
Change-Id: I67e3dd8489bd4d61a63764dac32b4bb9e5c28828  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5317578](<https://chromium-review.googlesource.com/c/v8/v8/+/5317578>)  
Reviewed-by: Andreas Haas <[ahaas@chromium.org](<mailto:ahaas@chromium.org>)>  
Commit-Queue: Clemens Backes <[clemensb@chromium.org](<mailto:clemensb@chromium.org>)>  
Cr-Commit-Position: refs/branch-heads/12.2@{#40}  
Cr-Branched-From: 6eb5a9616aa6f8c705217aeb7c7ab8c037a2f676-refs/heads/12.2.281@{#1}  
Cr-Branched-From: 44cf56d850167c6988522f8981730462abc04bcc-refs/heads/main@{#91934}  
  
M src/wasm/wasm-code-manager.cc  
  
[https://chromium-review.googlesource.com/5317578](<https://chromium-review.googlesource.com/5317578>)


---

**#38 — am...@google.com — Feb 29, 2024 10:04AM**

*** Boilerplate reminders! ***  
Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.  
******************************


---

**#39 — am...@chromium.org — Feb 29, 2024 10:12AM**

Congratulations Jerry! The Chrome VRP Panel has decided to award you $7,000 for this report of renderer process memory corruption. Thank you for your efforts and reporting this issue to us!


---

**#40 — pe...@google.com — May 31, 2024 01:00AM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
