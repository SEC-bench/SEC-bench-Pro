# V8 Sandbox Bypass: Attacker manipulation of ArrayBufferSweeper linked lists results in dangling ArrayBufferExtension pointers

Issue URL: https://issues.chromium.org/issues/384186547
VRP-Reward: 20000
Date: Dec 16, 2024 12:21PM


`ArrayBufferExtension`s are a datastructure responsible for holding an `ArrayBuffer`'s `BackingStore` / accounting metadata, among other things. `JSArrayBuffer`s then reference these extensions through the external pointer table. Notably, while extensions are allocated and first initialized by `JSArrayBuffer`s, they are not freed by them; instead this is done by a separate `ArrayBufferSweeper`, which maintains two linked lists of `ArrayBufferExtension`s to be visited after every GC; `JSArrayBuffer::Setup` / `JSArrayBuffer::Attach` inserts the `ArrayBuffer`'s extension into these lists (after allocating one if the buffer didn't have an assigned extension before this).

This process can be abused by an attacker with control over the sandbox. While they are unable to directly interfere with the contents of `ArrayBufferExtension`s, they are able to insert a single `ArrayBufferExtension` into the sweeper's list multiple times by overwriting the `extension` field of a `JSArrayBuffer` before its backing store is attached, causing said extension to be registered a second time. If the extension is inserted into both the young and old generation tracking lists at the same time, then it will become dangling after a young-generation GC, which will free the extension, but not remove it from the old generation's list of extensions. An attacker can then manipulate the heap to control the contents of the dangling `ArrayBufferExtension` and proceed to escape the V8 sandbox.

To actually perform this attack, an attacker needs to win a race condition between `JSArrayBuffer::Setup`, which allocates the `ArrayBufferExtension` (overwriting any preexisting one), and `JSArrayBuffer::Attach`, which registers the extension with the `ArrayBufferSweeper`. Winning this race is trivial in practice though by simply writing to this address in an infinite loop; an attacker has unlimited attempts, and the race window is quite big since there is a non-insignificant amount of logic in both methods.

See attached a proof-of-concept exploit which demonstrates an attacker controlled write using this vulnerability. It was tested on optdebug and release builds of D8 `80f2beddcf2e43a5f937196639ca37938553649a`, using the `--sandbox-testing --expose-gc --single-threaded` flags, on system running glibc 2.40. A successful run of the exploit will result in a write to address `0x13371337000`, demonstrating that the POC has successfully escaped the sandbox. I am currently working on an exploit variant targeting Chromium / PartitionAlloc.

Performing the required heap manipulation to turn this vulnerability into a controlled write is rather tricky; an attacker needs to precisely manipulate the heap and its various caches to ensure that the dangling `ArrayBufferExtension` isn't immediately reused by other allocations, and to subsequently gain control over its contents themselves. As such the provided POC isn't 100% reliable; in my own testing, the POC reproduces almost all of the time on optdebug builds, but fails some of the time on release builds (the `--single-threaded` has little to no impact on this); as such I recommend running this POC on debug builds. Even if the heap manipulation fails, the exploit still usually triggers the V8 sandbox testing mode's sandbox violation condition, or crashes from an abort inside of glibc's allocator code, demonstrating that memory corruption outside of the sandbox has occurred. However, it is feasible that for these reasons, the exploit fails to demonstrate a controlled write on Google's own infrastructure. If this happens, I am willing to try to adjust the exploit / find other ways of demonstrating a controlled write.

Fixing this issue probably consists of two individual fixes: first of all, the race window should be closed; this can be done by merging the call to `init_extension()` in `JSArrayBuffer::Setup` with the call to `EnsureExtension()` in `JSArrayBuffer::Attach`. Secondly, `CHECK`s could be added to `ArrayBufferSweeper::Append` / `ArrayBufferList::Append` to ensure a `ArrayBufferExtension` may only be part of a single list at any given time.

Reporter Credit: if applicable, please credit my pseudonym Popax21 in regards to this report.


---

**#2 — pu...@gmail.com — Dec 16, 2024 12:23PM**

I just noticed that I accidentally used the wrong Email address while submitting this issue; would it be possible to move this to my main Email which opened [issue 383356864](<https://issues.chromium.org/issues/383356864>), [issue 365376497](<https://issues.chromium.org/issues/365376497>) and [issue 361862752](<https://issues.chromium.org/issues/361862752>)?


---

**#3 — an...@chromium.org — Dec 17, 2024 12:20AM**

[security shepherd]: Thank you for the report. Reporter has been set and sending it over to current V8 shepherd.


---

**#4 — pe...@google.com — Dec 17, 2024 12:40AM**

Setting milestone because of s0/s1 severity.


---

**#5 — pe...@google.com — Dec 17, 2024 12:41AM**

Setting Priority to P1 to match Severity s1. If this is incorrect, please reset the priority. The automation bot account won't make this change again.


---

**#6 — pu...@gmail.com — Dec 17, 2024 01:18AM**

> I just noticed that I accidentally used the wrong Email address while submitting this issue; would it be possible to move this to my main Email which opened [issue 383356864](<https://issues.chromium.org/issues/383356864>), [issue 365376497](<https://issues.chromium.org/issues/365376497>) and [issue 361862752](<https://issues.chromium.org/issues/361862752>)?

Thanks for editing the reporter field; would it be possible to add said Email to the CC list as well, so that my original account gains access to this issue? (sorry for the hassle caused by this mishap)


---

**#7 — cl...@appspot.gserviceaccount.com — Dec 17, 2024 06:52PM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=6000038203293696](<https://clusterfuzz.com/testcase?key=6000038203293696>).


---

**#8 — cl...@appspot.gserviceaccount.com — Dec 17, 2024 06:53PM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5333229380763648](<https://clusterfuzz.com/testcase?key=5333229380763648>).


---

**#9 — sa...@google.com — Dec 18, 2024 02:54AM**

Great report, thanks a lot! I wasn't able to reproduce this on Clusterfuzz, but I did manage to trigger it locally (although also fairly unreliably, but I was also using a release build, not an optdebug build). I'll be OOO starting tomorrow more or less until the start of January, so I might only get a chance to really look into this once I'm back. Michael, it might make sense for someone on your team to also look into this since it seems related to the ArrayBufferSweeper. I think longer term, it would be nice to get rid of the ArrayBufferSweeper entirely and instead let the ExternalPointerTable free managed resources (as described [here](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/sandbox/external-pointer-table.h;l=381;drc=acf6173ec5a544f282d7b31acda14595cef71db3>)). But I'm not sure if we want to do this now or ship an independent fix for this issue in the meantime.


---

**#10 — ml...@chromium.org — Dec 18, 2024 02:57AM**

ABSweeper exists because of performance issues with handling free directly in the atomic pause as it's just too slow in certain workloads. I don't think just using the table with synchronous free would work. We would need some parallelization there which I am unsure whether we want in first place.


---

**#11 — ma...@gmail.com — Dec 18, 2024 09:02AM**

I've now been able to finish the exploit variant for PartitionAlloc / Chromium; based of my testing, it is much more reliable, escaping the sandbox and even achieving RCE in around 9/10 runs. However, since I do not have access to a Chromium build with the memory corruption API enabled, this requires piggy-backing of an existing memory corruption vulnerability, in my case [issue 383356864](<https://issues.chromium.org/issues/383356864>). See <https://issues.chromium.org/issues/383356864#comment32> for more details regarding this exploit variant.


---

**#12 — sa...@google.com — Jan 3, 2025 10:43PM**

Great work! Note that we recently added a linux_asan_chrome_v8_sandbox_testing job on Clusterfuzz, i.e. a chromium build with ASan and the memory corruption API available, so it should be possible to reproduce this bug in Chrome with just the memory corruption API :)


---

**#13 — ma...@gmail.com — Jan 5, 2025 01:45AM**

Neat! Do you happen to know if there's any documentation regarding usage / availability of `SharredArrayBuffer`s within this target? Accessing them usually requires some special HTTP headers to be set, and my exploit needs those to coordinate between some `Worker`s. If they are available though, then I can try to create another PoC based of my full Chromium renderer exploit chain and the memory corruption API, which should hopefully improve reliability greatly compared to my original POC.


---

**#14 — sa...@google.com — Jan 6, 2025 06:45PM**

How do you run your PoC locally? I would assume that there's a chromium flag (or v8 flag) that we can set to expose SharedArrayBuffers. In that case, we can also pass that flag to Clusterfuzz.

Michael, I don't think I'll be able to get to this issue this week, and I'll be OOO until April 13th starting next week. Could someone on your side look into this? It sounded like the immediate fix (checking for duplicate entries in those lists) should be fairly easy once you know where to look. I still think we should try to make the EPT the sole source of truth for managing the lifetime of external objects and not have two separate mechanisms. We could certainly implement something like delayed freeing if freeing during the atomic pause is a problem. But also happy to discuss more when I'm back!


---

**#15 — ma...@gmail.com — Jan 7, 2025 12:31PM**

Locally I use a small development HTTP server which hosts my POCs while also setting all required headers. However, I've briefly skimmed the code paths responsible for controlling access to SABs, and it seems like there is a [Chromium feature which can be used to bypass the usual header requirements](<https://source.chromium.org/chromium/chromium/src/+/main:content/public/common/content_features.cc;l=975>). I imagine that this feature can probably controlled through command-line flags, however I do not have any experience with enabling SABs in this manner.


---

**#16 — sa...@google.com — Jan 7, 2025 05:18PM**

Ah excellent, I _think_ then it should just work if we pass `--enable-features=SharedArrayBuffer` (which will also work on Clusterfuzz). If it's not too much work, it would be nice to have a reproducer for Clusterfuzz. But if that turns out to be tricky then we should also manage with the original testcase


---

**#17 — ma...@gmail.com — Jan 8, 2025 06:21AM**

I've tried to create a POC variant which makes a controlled write within the confines of Chromium; see the attached file (note that I have been unable to test it locally since I currently lack a functional Chromium build setup). It's a bit convoluted and more complicated than needed since it's based on the full RCE chain I linked earlier with little modification, which means that it does more than what's strictly necessary to just demonstrate such a write. However, I still hope that it will be more reliable than my original POC. If it turns out that this POC runs into too many issues / is too unreliable though, I'll spend some more time to create a new minimal POC based on this one.


---

**#18 — ml...@chromium.org — Jan 8, 2025 05:42PM**

fwiw, the exploirt is well understood and a fix is in [1] I believe. We basically make sure we always create a new extension objects and only add that to the list. There's no read of possibly corrupted data. This is an older area of V8 that was definitely not aware of the new attack model. At the same time the spec here is unfortunate as it requires us to create the AB before the backing which can then throw. This is why the 2-stage initialization existed initially.

[1] [https://chromium-review.googlesource.com/c/v8/v8/+/6149097](<https://chromium-review.googlesource.com/c/v8/v8/+/6149097>)


---

**#19 — cl...@appspot.gserviceaccount.com — Jan 9, 2025 01:08AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5031277862256640](<https://clusterfuzz.com/testcase?key=5031277862256640>).


---

**#20 — ap...@google.com — Jan 9, 2025 02:42AM**

Project: v8/v8  
Branch: main  
Author: Michael Lippautz <[mlippautz@chromium.org](<mailto:mlippautz@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6149097](<https://chromium-review.googlesource.com/6149097>)

[runtime] Fix ArrayBuffer creation attaching extension objects

* * *

Expand for full commit details

```
[runtime] Fix ArrayBuffer creation attaching extension objects 
 
ArrayBufferExtension objects are witness objects to track BackingStore 
objects. The are attached to JSABs in a 1:1 fashion. The initial setup 
through builtins is convoluted as AB creation is observable and should 
preceed the actual backing store creation. Since the backing store 
creation can fail this leads to a half initialized temporary state 
where an AB is present but no backing store is attached and thus no 
extension objects is present. 
 
The current code works on the assumption of a well-behaving program. 
 
In a world where we follow sandbox rules malloced state is trusted and 
always has to be verified when being read from the heap. In order to 
avoid verification, the code is refactored to only a have a single 
setup phase. This allows us to work with the extension when it's 
initially allocated and prevents the mutator from reusing the object 
and tinkering with the lists it is contained in. 
 
Change-Id: I9d2f23f3ad141aea8b1543ac0d071ecc688e173b 
Bug: 384186547 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6149097 
Commit-Queue: Michael Lippautz <mlippautz@chromium.org> 
Reviewed-by: Dominik Inführ <dinfuehr@chromium.org> 
Cr-Commit-Position: refs/heads/main@{#98001}
```

* * *

Files:

  * M `src/builtins/builtins-arraybuffer.cc`
  * M `src/heap/array-buffer-sweeper.cc`
  * M `src/heap/array-buffer-sweeper.h`
  * M `src/heap/heap.cc`
  * M `src/heap/heap.h`
  * M `src/objects/js-array-buffer.cc`
  * M `src/objects/js-array-buffer.h`
  * M `test/unittests/heap/heap-unittest.cc`

* * *

Hash: 1d7b6d2d2d1c3fb18739405b6fd58ce801844f57  
Date: Wed Jan 08 16:07:42 2025

* * *


---

**#21 — ma...@gmail.com — Jan 9, 2025 02:51AM**

Seems like I made a small mistake when porting the POC to the memory corruption API, which causes it to not reproduce on ClusterFuzz (I assumed `Sandbox.base` was a `BigInt`, even though it is a regular `Number`). I've attached a fixed version of the POC below.


---

**#22 — cl...@appspot.gserviceaccount.com — Jan 9, 2025 03:33AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=4696351547785216](<https://clusterfuzz.com/testcase?key=4696351547785216>).


---

**#23 — 24...@project.gserviceaccount.com — Jan 9, 2025 07:53AM**

Detailed Report: [https://clusterfuzz.com/testcase?key=4696351547785216](<https://clusterfuzz.com/testcase?key=4696351547785216>)  
  
Fuzzer: None  
Job Type: linux_asan_chrome_v8_sandbox_testing  
Platform Id: linux  
  
Crash Type: V8 sandbox violation  
Crash Address: 0x78e33b94e9e0  
Crash State:  
v8::internal::ArrayBufferSweeper::SweepingState::SweepingJob::SweepListFull  
v8::internal::ArrayBufferSweeper::SweepingState::SweepingJob::Sweep  
v8::internal::ArrayBufferSweeper::SweepingState::SweepingJob::Run  
  
Sanitizer: address (ASAN)  
  
Crash Revision: [https://clusterfuzz.com/revisions?job=linux_asan_chrome_v8_sandbox_testing&revision=1403645](<https://clusterfuzz.com/revisions?job=linux_asan_chrome_v8_sandbox_testing&revision=1403645>)  
  
Reproducer Testcase: [https://clusterfuzz.com/download?testcase_id=4696351547785216](<https://clusterfuzz.com/download?testcase_id=4696351547785216>)  
  
To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.   
  
If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.  
  
If you have any feedback on reproducing test cases, let us know at [https://forms.gle/Yh3qCYFveHj6E5jz5](<https://forms.gle/Yh3qCYFveHj6E5jz5>) so we can improve.


---

**#24 — 24...@project.gserviceaccount.com — Jan 9, 2025 08:31AM**

Automatically applying components based on crash stacktrace and information from OWNERS files.  
  
If this is incorrect, please apply the hotlistid:4801165.


---

**#25 — sa...@google.com — Jan 9, 2025 06:44PM**

Thanks for creating the new PoC, looks like that worked! :)


---

**#26 — 24...@project.gserviceaccount.com — Jan 9, 2025 06:51PM**

Detailed Report: [https://clusterfuzz.com/testcase?key=4696351547785216](<https://clusterfuzz.com/testcase?key=4696351547785216>)  
  
Fuzzer: None  
Job Type: linux_asan_chrome_v8_sandbox_testing  
Platform Id: linux  
  
Crash Type: V8 sandbox violation  
Crash Address: 0x78e33b94e9e0  
Crash State:  
v8::internal::ArrayBufferSweeper::SweepingState::SweepingJob::SweepListFull  
v8::internal::ArrayBufferSweeper::SweepingState::SweepingJob::Sweep  
v8::internal::ArrayBufferSweeper::SweepingState::SweepingJob::Run  
  
Sanitizer: address (ASAN)  
  
Crash Revision: [https://clusterfuzz.com/revisions?job=linux_asan_chrome_v8_sandbox_testing&revision=1403645](<https://clusterfuzz.com/revisions?job=linux_asan_chrome_v8_sandbox_testing&revision=1403645>)  
  
Reproducer Testcase: [https://clusterfuzz.com/download?testcase_id=4696351547785216](<https://clusterfuzz.com/download?testcase_id=4696351547785216>)  
  
To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.   
  
If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.  
  
If you have any feedback on reproducing test cases, let us know at [https://forms.gle/Yh3qCYFveHj6E5jz5](<https://forms.gle/Yh3qCYFveHj6E5jz5>) so we can improve.


---

**#27 — sp...@google.com — Jan 18, 2025 01:57AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $20000.00 for this report.  
  
Rationale for this decision:  
V8 Sandbox Bypass reward: demonstration of controlled write outside the V8 sandbox   
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#28 — am...@chromium.org — Jan 18, 2025 02:02AM**

Congratulations Popax21! Thank you for your efforts in the V8 sandbox and this excellent report -- nice work!


---

**#29 — ch...@google.com — Apr 18, 2025 09:43PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
