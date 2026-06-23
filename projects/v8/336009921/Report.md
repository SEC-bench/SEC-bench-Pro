# V8 Sandbox Bypass: wrapper and call target mismatch in wasm

Issue URL: https://issues.chromium.org/issues/336009921
VRP-Reward: 5000
Date: Apr 22, 2024 01:11AM


## RCA

When calling a wasm function from JS, there exists 3 stages.

```
JS -> JS-to-Wasm Wrapper -> Wasm Internal Function
```

The `JS-to-Wasm` Wrapper exists in fucntion object but in a format of code wrapper. The wasm internal function can only be fetched from `SharedFunctionInfo->function_data`. We cannot directly modify the code object but there's no checking on if the `JS function`, `wrapper` and the `internal function` are matched or not. Exchanging `code wrapper`s or `function_data`s between functions won't trigger any violations.

As we know the wrapper is not for general purpose. Functions share same wrapper only when their sigs match. So, if the sigs of wrapper and the internal function are not matched, there's a chance that we could read and write on stack and cause arbitrary code execution.

In details, if the `wrapper`'s arguments count is larger than the `JS`'s, the `wrapper` will pass unexpected data on stack to internal function leading to oob read on stack. Similarly if the `internal function`'s return count is larger than the `wrapper`'s, the `internal function` would write unexpected data on stack leading to oob write on stack.

With oob read, we can pass an address in text section to the internal function to calculate the code base and further calculate the addresses of gadgets. With oob write, we can write rop chains on stack to execute arbitrary code.

## POC

For the VRP rules, I will attach an example poc just writing into `Sandbox.targetPage`.

The poc is based on commit `75884e3ab36afbc7503aa7e4dfa37cb4e8df181b` which is the latest when testing.

The d8 binary was compiled with the following flags:

```
is_debug = false
dcheck_always_on = false
target_cpu = "x64"
v8_enable_memory_corruption_api = true
```

This poc uses `--sandbox-testing` and the `wasm-module-builder.js`. It does not rely on any other flags and local apis. As for the `d8.file.execute` api, it can be easily avoided by adding the content of `wasm-module-builder.js` into this poc or turns the module into an array and replace the bytes when needed.

The address and offsets remain unchanged for a certain binary and the base are dynamically calculated. An array is used in the poc to make sure a valid write in `wrapper` to avoid segment fault. So the bypass is really stable.

Result:

```
➜  x64.release git:(main) ✗ ./d8 --sandbox-testing poc.js
Sandbox testing mode is enabled. Write to the page starting at 0xa5e7f80a000 (available from JavaScript as `Sandbox.targetPage`) to demonstrate a sandbox bypass.

## V8 sandbox violation detected!

Received signal 11 SEGV_ACCERR 0a5e7f80a000
[1]    2698688 segmentation fault (core dumped)  ./d8 --sandbox-testing poc.js
```


---

**#2 — sa...@google.com — Apr 23, 2024 09:38PM**

Very nice! Thank you for this great report!

I'm so far unable to reproduce this locally or on Clusterfuzz, probably because the hardcoded offsets are different for some reason. That said, the issue is definitely real. @Reporter, could you try changing your PoC to instead simply return into the target page? That should not require the use of any offsets, and our crash filter should also treat the resulting segfault as a sandbox bypass :)

I will also create a parent bug for dealing with the issue of insecure JS -> Wasm calls as mismatching the signatures can also cause other issues and be caused in other ways as well.


---

**#3 — ry...@gmail.com — Apr 24, 2024 01:35AM**

I tried to make a full exploit in my poc and thus made it hard to reproduce. Sorry for that inconvenience. I'm providing more details and simpified pocs now.

In fact, there are chances that a memory corruption happend before return. We have to satisfy some constraints in the wrapper code after return from the internal function. Here is the code from a fresh release build for commit `0379746345d071adf30b4e084183734999b7aede` with the same build flags in the report. (I also noticed that different build flags would cause different code generation, like, in a debug build, there are more checks here.)

```
   0x5575b22c0084:      movabs rdi,0x7f3effffffffffff
   0x5575b22c008e:      and    rdi,QWORD PTR [rcx+rbx*1]
   0x5575b22c0092:      mov    rbx,QWORD PTR [rdi+0x13]
   0x5575b22c0096:      mov    esi,DWORD PTR [rdi+0x7]
   0x5575b22c0099:      or     rsi,QWORD PTR [r13+0x1e0]
   0x5575b22c00a0:      mov    QWORD PTR [rbp-0x20],rdx
   0x5575b22c00a4:      call   rbx
   0x5575b22c00a6:      mov    rbx,QWORD PTR [rbp-0x20]
   0x5575b22c00aa:      mov    DWORD PTR [rbx],0x0
   0x5575b22c00b0:      movabs rax,0x1db000000069
   0x5575b22c00ba:      mov    rcx,QWORD PTR [rbp-0x18]
   0x5575b22c00be:      mov    rsp,rbp
   0x5575b22c00c1:      pop    rbp
   0x5575b22c00c2:      cmp    rcx,0x1
   0x5575b22c00c6:      jg     0x5575b22c00cb
   0x5575b22c00c8:      ret    0x8
   0x5575b22c00cb:      pop    r10
   0x5575b22c00cd:      lea    rsp,[rsp+rcx*8]
   0x5575b22c00d1:      push   r10
   0x5575b22c00d3:      ret 
```

First constraint, address at `rbp-0x20` should be a writable address so the code `mov rbx,QWORD PTR [rbp-0x20]; mov DWORD PTR [rbx],0x0;` would not result in a invalid memory access.

Second constraint, value at `rbp-0x18` should be 0 or a small one, so `lea rsp,[rsp+rcx*8]` will not exceed our padding data.

`poc.js` is a simplified poc based on the stack layout of my local build.

```
➜  x64.release git:(main) ./d8 --sandbox-testing poc.js                                     
Sandbox testing mode is enabled. Write to the page starting at 0x3882456cb000 (available from JavaScript as `Sandbox.targetPage`) to demonstrate a sandbox bypass.

## V8 sandbox violation detected!

Received signal 11 SEGV_ACCERR 3882456cb000

==== C stack trace ===============================

 [0x5644286660b7]
 [0x7f914e0bf420]
 [0x3882456cb000]
[end of stack trace]
[1]    2512366 segmentation fault (core dumped)  ./d8 --sandbox-testing poc.js
```

However, I can still provide a **tricky** one `tricky_poc.js`. I simply pad stack with the target address. This will cause `mov rbx,QWORD PTR [rbp-0x20]; mov DWORD PTR [rbx],0x0;` directly write into the target address and cause sandbox violation.

```
➜  x64.release git:(main) ./d8 --sandbox-testing tricky_poc.js 
Sandbox testing mode is enabled. Write to the page starting at 0x3793393a3000 (available from JavaScript as `Sandbox.targetPage`) to demonstrate a sandbox bypass.

## V8 sandbox violation detected!

Received signal 11 SEGV_ACCERR 3793393a3000
[1]    3263185 segmentation fault (core dumped)  ./d8 --sandbox-testing tricky_poc.js
```

If I'm lucky enough this time, the only thing to do to reproduce is changing the path of `wasm-module-builder.js` now.


---

**#4 — cl...@appspot.gserviceaccount.com — Apr 24, 2024 07:48PM**

Detailed Report: [https://clusterfuzz.com/testcase?key=6606977074397184](<https://clusterfuzz.com/testcase?key=6606977074397184>)  
  
Fuzzer: None  
Job Type: linux_d8_sandbox_testing  
Platform Id: linux  
  
Crash Type: V8 sandbox violation  
Crash Address:   
Crash State:  
NULL  
Sanitizer: address (ASAN)  
  
Crash Revision: [https://clusterfuzz.com/revisions?job=linux_d8_sandbox_testing&revision=93551](<https://clusterfuzz.com/revisions?job=linux_d8_sandbox_testing&revision=93551>)  
  
Reproducer Testcase: [https://clusterfuzz.com/download?testcase_id=6606977074397184](<https://clusterfuzz.com/download?testcase_id=6606977074397184>)  
  
To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.   
  
If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.  
  
If you have any feedback on reproducing test cases, let us know at [https://forms.gle/Yh3qCYFveHj6E5jz5](<https://forms.gle/Yh3qCYFveHj6E5jz5>) so we can improve.


---

**#5 — sa...@chromium.org — Apr 24, 2024 07:50PM**

Excellent, thank you! With that, it reproduces reliably on Clusterfuzz and locally (I used poc.js now from [comment #3](<https://issues.chromium.org/issues/336009921#comment3>) and pre-pended the content of wasm-module-builder.js)


---

**#6 — ap...@google.com — Jun 12, 2024 02:38AM**

Project: v8/v8  
Branch: main  
  
commit e25efe6cf28b8a7dfc6de89ac16fd2a77f5e281d  
Author: Jakob Kummerow <[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)>  
Date: Tue Jun 11 19:32:24 2024  
  
[wasm][sandbox] Verify signatures in js-to-wasm wrappers  
  
This ports the recently introduced signature verification from  
call_ref to compiled (i.e. non-generic) js-to-wasm wrappers, to  
prevent escaping from a corrupted sandbox by calling broken Wasm  
functions from JS.  
  
Bug: 336507783  
Change-Id: I2946424b39ca345ab6f6d31ad8308327cd5be1e5  
Fixed: 336009921  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5622490](<https://chromium-review.googlesource.com/c/v8/v8/+/5622490>)  
Commit-Queue: Jakob Kummerow <[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)>  
Reviewed-by: Thibaud Michaud <[thibaudm@chromium.org](<mailto:thibaudm@chromium.org>)>  
Cr-Commit-Position: refs/heads/main@{#94382}  
  
M src/wasm/turboshaft-graph-interface.cc  
M src/wasm/turboshaft-graph-interface.h  
M src/wasm/wrappers.cc  
  
[https://chromium-review.googlesource.com/5622490](<https://chromium-review.googlesource.com/5622490>)


---

**#7 — 24...@project.gserviceaccount.com — Jun 19, 2024 02:48AM**

ClusterFuzz testcase 6606977074397184 is still reproducing on the latest available build r94494.  
  
Please re-test your fix against this testcase and if the fix was incorrect or incomplete, please re-open the bug. Otherwise, ignore this notification and add the hotlistid:5432646.


---

**#8 — sp...@google.com — Jun 28, 2024 09:55AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $5000.00 for this report.  
  
Rationale for this decision:  
V8 heap sandbox bypass reward  
  
  
Important: This payment will be issued by Bugcrowd. You will receive an email from Bugcrowd in the next 24 hours which contains a submission you must claim to be rewarded.  
  
If you do not receive an email from them, please check your spam folder and then reach out to us via a comment here. For issues related to Bugcrowd itself, please contact them via [https://bugcrowd.com/support](<https://bugcrowd.com/support>).  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#9 — am...@chromium.org — Jun 28, 2024 09:58AM**

Congratulations! Thank you for your efforts and reporting this issue to us!


---

**#10 — ry...@gmail.com — Aug 26, 2024 11:07AM**

Recently, I discovered that the PoC still works on the latest commit. After some investigation, I found that the fix only adds signature verification in the Turboshaft Wasm wrapper, which isn't enabled by default. Additionally, there's still no check to ensure that the signatures between the wrapper and the actual call target in function_data match. I hope someone can notice and fix this issue.


---

**#11 — am...@chromium.org — Aug 26, 2024 12:31PM**

Hi -- thanks for letting us know about this. I've re-opened. jkummerow@ can you please take a look?


---

**#12 — sa...@chromium.org — Sep 9, 2024 08:42PM**

Ah, I think this is probably expected as Turbofan is about to be deprecated. [Issue 362191724](<https://issues.chromium.org/issues/362191724>) documents the current situation. I'll still leave this open for Jakob to take another look and confirm this though.


---

**#13 — jk...@chromium.org — Sep 16, 2024 07:33PM**

Correct, we do not spend time on implementing new features in Turbofan any more. All Sandbox related improvements will ship with Turboshaft.
