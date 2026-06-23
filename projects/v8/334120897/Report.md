# V8 Sandbox Bypass: wasm function signature confusion leading to out of sandbox arbitrary read/write

Issue URL: https://issues.chromium.org/issues/334120897
VRP-Reward: 6000
Date: Apr 15, 2024 08:01AM


#### Description

ze...@gmail.com created issue [ #1](</issues/334120897#comment1>)

Apr 15, 2024 08:01AM

Security Bug  
  
Important: Please do not change the component of this bug manually.  
  
Please READ THIS FAQ before filing a bug: [https://chromium.googlesource.com/chromium/src/+/HEAD/docs/security/faq.md](<https://chromium.googlesource.com/chromium/src/+/HEAD/docs/security/faq.md>)  
  
Please see the following link for instructions on filing security bugs: [https://www.chromium.org/Home/chromium-security/reporting-security-bugs](<https://www.chromium.org/Home/chromium-security/reporting-security-bugs>)  
  
Reports may be eligible for reward payments under the Chrome VRP: [https://g.co/chrome/vrp](<https://g.co/chrome/vrp>)  
  
NOTE: Security bugs are normally made public once a fix has been widely deployed.  
  
\-------------------------  
  
VULNERABILITY DETAILS  
  
In webassembly, wasm module exported functions' signatures and function implementation (`call_target`) are not tightly connected. Swapping `call_targets` between functions with different signatures can lead to a 64-bit arbitrary read/write, which bypasses the v8 heap sandbox.  
  
When an exported function is invoked in JS, it (`Builtins_JSToWasmWrapper` and `Builtins_JSToWasmWrapperAsm`) will look for the call_target through Function=>shared_info=>function_data=>func_ref (in previous versions, it was `internal_data`) and retrieve an index inside a function table, mask it, and recover the real call target, then invoke the call target.  
Notice that, since the type check is performed in the builtins, v8 will directly pass the argument values as is to `call_target` (the JITed code).  
Now let's consider these two wasm functions:  
```  
(func $do_read (export "do_read")  
(param $offset i32) ;; Offset within memory  
(result i64)  
(i64.load  
(local.get $offset) ;; Get the memory offset  
)  
)  
(func $oob_read (export "oob_read")  
(param $var1 i64)  
(result i64)  
i64.const 0  
)  
```  
do_read will be compiled to be something like  
```  
mov QWORD PTR [rcx+rax*1], rdx  
```  
where `rcx` is the data_ptr of the buffer, `rax` is the offset argument, `rdx` is the value argument.   
Notice that since there is type check in the builtins, so `rax` is guaranteed to be a i32 variable, so the code works as intended.  
  
However, if now we assign `do_read`'s `call_target` to `oob_read`, when we invoke `oob_read` in JS, it will invoke   
```  
mov QWORD PTR [rcx+rax*1], rdx  
```  
as well. But this time, both `rax` and `rdx` are i64 (`oob_read`'s signature), so 64bit, which leads to 64bit OOB read/write. But notice that the offset is in i64, so it can underflow as well. Once we leak the data_ptr of the buffer (which is easy), we obtain arbitrary read/write in the full 64bit region, thus outside of the sandbox.  
  
Assigning call_target is possible because as I mentioned before, although the function table is in the trusted space, the func_ref is in the sandbox. And we don't need to forge anything, we can simply copy the `func_ref` of `do_read` to `oob_read`, then the call_target will be changed.  
  
  
VERSION  
V8 version: 12.5.0 (compiled from git)  
git log:  
```  
commit 1778ccde8eb86a01b4c16c34490a597235203b2d (HEAD -> main, origin/main, origin/HEAD)  
Author: Egor Pasko <[pasko@chromium.org](<mailto:pasko@chromium.org>)>  
Date: Fri Apr 12 15:52:42 2024 +0200  
```  
Operating System: Ubuntu 22.04  
  
REPRODUCTION CASE  
Please include a demonstration of the security bug, such as an attached HTML or binary file that reproduces the bug when loaded in Chrome. PLEASE make the file as small as possible and remove any content not required to demonstrate the bug, or any personal or confidential information.  
  
Please attach files directly, not in zip or other archive formats, and if you've created a demonstration site please also attach the files needed to reproduce the demonstration locally.  
  
HOW TO RUN THE POC  
```  
$ ./d8 --sandbox-testing ./pwn.js   
Sandbox testing mode is enabled. Write to the page starting at 0xb8b14d07000 (available from JavaScript as `Sandbox.targetPage`) to demonstrate a sandbox bypass.  
target_page @ 0xb8b14d07000  
js_heap_base @ 0xdae00000000  
func_addr: 0x19a990  
shared_addr: 0x19a960  
function_data: 0x19a934  
func_ref: 0x19a92c  
func_addr: 0x19a890  
shared_addr: 0x19a860  
function_data: 0x19a834  
func_ref: 0x19a82c  
func_addr: 0x19a910  
shared_addr: 0x19a8e0  
function_data: 0x19a8b4  
func_ref: 0x19a8ac  
func_addr: 0x19a810  
shared_addr: 0x19a7e0  
function_data: 0x19a7b4  
func_ref: 0x19a7ac  
wasm-function[2]:0x6c: RuntimeError: memory access out of bounds  
RuntimeError: memory access out of bounds  
at wasm://wasm/80260616:wasm-function[2]:0x6c  
at write64 (./pwn.js:127:12)  
at ./pwn.js:130:1  
```  
  
FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION  
Type of crash: v8 (tab?)  
Crash State: [see link above: stack trace *with symbols*, registers, exception record]  
  
CREDIT INFORMATION  
Externally reported security bugs may appear in Chrome release notes. If this bug is included, how would you like to be credited?  
Reporter credit: Kyle Zeng

crash.png 

336 KB [ View](<https://issues.chromium.org/action/issues/334120897/attachments/55482928?download=false>)[ Download](<https://issues.chromium.org/action/issues/334120897/attachments/55482928?download=true>)

args.gn 

244 B [ Download](<https://issues.chromium.org/action/issues/334120897/attachments/55482929?download=true>)

d8 

54 MB [ Download](<https://issues.chromium.org/action/issues/334120897/attachments/55482930?download=true>)

pwn.js 

3.8 KB [ View](<https://issues.chromium.org/action/issues/334120897/attachments/55482931?download=false>)[ Download](<https://issues.chromium.org/action/issues/334120897/attachments/55482931?download=true>)

snapshot_blob.bin 

302 KB [ Download](<https://issues.chromium.org/action/issues/334120897/attachments/55482932?download=true>)

exploit.wat 

653 B [ Download](<https://issues.chromium.org/action/issues/334120897/attachments/55482933?download=true>)


---

**#2 — ze...@gmail.com — Apr 15, 2024 08:03AM**

I think in the report, the assembly actually comes from `do_write` and `oob_write`. You can find their definition in exploit.wat


---

**#3 — cl...@appspot.gserviceaccount.com — Apr 16, 2024 03:33AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=4686856068202496](<https://clusterfuzz.com/testcase?key=4686856068202496>).


---

**#4 — ze...@gmail.com — Apr 16, 2024 03:44AM**

My poc uses the Sandbox API, so you might need to enable ` --sandbox-testing`.   
Notice that this is a sandbox bypass vulnerability, which cannot be directly invoked in the normal d8.  
The submission follows the `V8 Sandbox Bypass Rewards` rule from [https://bughunters.google.com/about/rules/5745167867576320/chrome-vulnerability-reward-program-rules](<https://bughunters.google.com/about/rules/5745167867576320/chrome-vulnerability-reward-program-rules>)


---

**#5 — cl...@appspot.gserviceaccount.com — Apr 16, 2024 03:48AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5920122372816896](<https://clusterfuzz.com/testcase?key=5920122372816896>).


---

**#6 — ze...@gmail.com — Apr 16, 2024 04:05AM**

It seems it is not fuzzed:  
```  
# The following harmless error was encountered: The sandbox testing mode is currently incompatible with AddressSanitizer  
```


---

**#7 — ze...@gmail.com — Apr 16, 2024 04:37AM**

Also, there might be a bug in the Sandbox API.  
My poc does not result in a "V8 sandbox violation detected!" message as said in the rule while it does write to the page as shown by GDB (as seen in the attached screenshot)  
I'm not sure how the Sandbox API differentiate between Sandbox escape crashes and normal crashes. But if it looks for registers, it won't detect my case.  
Specifically, in my case, the crashing instruction is `mov [rcx+rax], rdx` so the target page won't appear in the registers (rcx+rax == target_page)


---

**#8 — bb...@google.com — Apr 16, 2024 04:38AM**

Setting provisional p1 and passing over to v8


---

**#9 — sa...@google.com — Apr 16, 2024 05:16AM**

Excellent work, very nice bypass!

There is indeed another issue here: the [Wasm trap handler](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/trap-handler/handler-inside-posix.cc;l=118;drc=c08629b2fdd20ad796b868b21810b98a32c9fc86>) "eats" the SIGSEGV as it happens on a Wasm memory access and so the crash is never seen by the [sandbox crash filter](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/sandbox/testing.cc;l=447;drc=2c6318e0c0848d3d2b526cc00dafd2e36d847ec3>). We therefore don't get the "V8 sandbox violation detected!" but only a "RuntimeError: memory access out of bounds", which is misleading. This is kind of bad as it means that our fuzzers could never discover this sort of issue. I'll prepare a fix for this.

Clemens, you have more context around the state of Wasm sandboxing, and I remember you looked into ways to ensure that signatures and code pointers don't get desynchronized in other places. Could you take a first look at this? Happy to discuss options for fixing this!


---

**#10 — ap...@google.com — Apr 17, 2024 06:28AM**

Project: v8/v8  
Branch: main  
  
commit 33e4006f1ee2f61e701a94b9bde9c5e16add6891  
Author: Samuel Groß <[saelo@chromium.org](<mailto:saelo@chromium.org>)>  
Date: Tue Apr 16 10:33:53 2024  
  
[trap-handler] Only handle faults inside the V8 Sandbox  
  
Currently, when deciding whether to handle a segfault, the Wasm trap  
handler only looks at the PC of the faulting instruction. This is  
problematic as it means that the fault handler may hide bugs that lead  
to wild reads/writes originating from Wasm. Ideally, the trap handler  
would only handle invalid accesses in Wasm Memory objects. However, that  
would require recording the locations of all these objects. Instead,  
this CL takes a shortcut and changes the trap handler to only handle  
invalid accesses inside the V8 sandbox region, where all Wasm Memory  
objects must be located. In practice, this should be good enough.  
  
Bug: chromium:334120897  
Change-Id: Ife4af18697cbe921db5cb754301d037d84051652  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5453422](<https://chromium-review.googlesource.com/c/v8/v8/+/5453422>)  
Reviewed-by: Mark Mentovai <[mark@chromium.org](<mailto:mark@chromium.org>)>  
Commit-Queue: Samuel Groß <[saelo@chromium.org](<mailto:saelo@chromium.org>)>  
Reviewed-by: Andreas Haas <[ahaas@chromium.org](<mailto:ahaas@chromium.org>)>  
Cr-Commit-Position: refs/heads/main@{#93403}  
  
M src/sandbox/sandbox.cc  
M src/trap-handler/handler-inside-posix.cc  
M src/trap-handler/handler-inside.cc  
M src/trap-handler/handler-outside.cc  
M src/trap-handler/handler-shared.cc  
M src/trap-handler/trap-handler-internal.h  
M src/trap-handler/trap-handler.h  
M test/unittests/wasm/trap-handler-simulator-unittest.cc  
  
[https://chromium-review.googlesource.com/5453422](<https://chromium-review.googlesource.com/5453422>)


---

**#11 — cl...@appspot.gserviceaccount.com — Apr 17, 2024 05:30PM**

Detailed Report: [https://clusterfuzz.com/testcase?key=5467075087630336](<https://clusterfuzz.com/testcase?key=5467075087630336>)  
  
Fuzzer: None  
Job Type: linux_d8_sandbox_testing  
Platform Id: linux  
  
Crash Type: V8 sandbox violation  
Crash Address:   
Crash State:  
NULL  
Sanitizer: address (ASAN)  
  
Regressed: [https://clusterfuzz.com/revisions?job=linux_d8_sandbox_testing&range=93402:93403](<https://clusterfuzz.com/revisions?job=linux_d8_sandbox_testing&range=93402:93403>)  
  
Reproducer Testcase: [https://clusterfuzz.com/download?testcase_id=5467075087630336](<https://clusterfuzz.com/download?testcase_id=5467075087630336>)  
  
To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.   
  
If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.  
  
If you have any feedback on reproducing test cases, let us know at [https://forms.gle/Yh3qCYFveHj6E5jz5](<https://forms.gle/Yh3qCYFveHj6E5jz5>) so we can improve.


---

**#12 — sa...@google.com — Apr 18, 2024 04:52PM**

Looks like it reproduces properly now :)

After some offline discussion, I think the plan is now to move the `WasmExportedFunctionData` object into trusted space to ensure that all the information required for a function call stays consistent.

Jakob, since Clemens is OOO currently, could you take over this one? I wrote a document for how to migrate objects into trusted space some time ago: [https://docs.google.com/document/d/1kzlS8fXjdQtCCUZA2H_MIMWfhKMhnmUUIVWQ0ntNdi8/edit?usp=sharing](<https://docs.google.com/document/d/1kzlS8fXjdQtCCUZA2H_MIMWfhKMhnmUUIVWQ0ntNdi8/edit?usp=sharing>) Also happy to help out with that. In particular, I did a lot of refactoring in the SharedFunctionInfo, so I can deal with the SharedFunctionInfo->WasmExportedFunctionData reference once WasmExportedFunctionData is a trusted object.


---

**#13 — jk...@chromium.org — Apr 25, 2024 09:37PM**

Here is the fix sketched out in #12: [https://chromium-review.googlesource.com/c/v8/v8/+/5484107](<https://chromium-review.googlesource.com/c/v8/v8/+/5484107>)


---

**#14 — ap...@google.com — Apr 29, 2024 10:53PM**

Project: v8/v8  
Branch: main  
  
commit cf9373a0d6760146534b096cee60675a3ea09ad7  
Author: Jakob Kummerow <[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)>  
Date: Mon Apr 29 14:35:49 2024  
  
[wasm][sandbox] Make WasmFunctionData trusted  
  
This moves the WasmFunctionData object hierarchy to trusted space,  
which addresses some of the ways how Wasm functions can currently  
be used for escaping from a compromised V8 sandbox.  
  
Bug: 334120897  
Change-Id: I23aa5bc7b1205ff29d0b6dac6fe301494275565e  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5484107](<https://chromium-review.googlesource.com/c/v8/v8/+/5484107>)  
Reviewed-by: Michael Lippautz <[mlippautz@chromium.org](<mailto:mlippautz@chromium.org>)>  
Reviewed-by: Samuel Groß <[saelo@chromium.org](<mailto:saelo@chromium.org>)>  
Commit-Queue: Jakob Kummerow <[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)>  
Cr-Commit-Position: refs/heads/main@{#93633}  
  
M src/builtins/js-to-js.tq  
M src/builtins/js-to-wasm.tq  
M src/codegen/code-stub-assembler.h  
M src/compiler/wasm-compiler.cc  
M src/compiler/wasm-graph-assembler.cc  
M src/diagnostics/objects-printer.cc  
M src/heap/factory-base.cc  
M src/heap/factory.cc  
M src/heap/factory.h  
M src/heap/objects-visiting.h  
M src/logging/log.cc  
M src/objects/map.cc  
M src/objects/map.h  
M src/objects/object-list-macros.h  
M src/objects/objects-body-descriptors-inl.h  
M src/objects/shared-function-info-inl.h  
M src/objects/shared-function-info.h  
M src/objects/shared-function-info.tq  
M src/runtime/runtime-test-wasm.cc  
M src/sandbox/indirect-pointer-tag.h  
M src/wasm/c-api.cc  
M src/wasm/wasm-js.cc  
M src/wasm/wasm-objects-inl.h  
M src/wasm/wasm-objects.cc  
M src/wasm/wasm-objects.h  
M src/wasm/wasm-objects.tq  
M src/wasm/wrappers.cc  
M test/cctest/wasm/test-run-wasm-wrappers.cc  
M tools/dev/gm.py  
  
[https://chromium-review.googlesource.com/5484107](<https://chromium-review.googlesource.com/5484107>)


---

**#15 — jk...@chromium.org — Apr 29, 2024 11:49PM**

I believe #14 fixes the specific repro provided here, but I'm aware that there's a slightly different way to trigger the same end result, for which another fix is coming up here: [https://chromium-review.googlesource.com/c/v8/v8/+/5494364](<https://chromium-review.googlesource.com/c/v8/v8/+/5494364>).


---

**#16 — ap...@google.com — May 2, 2024 10:16PM**

Project: v8/v8  
Branch: main  
  
commit 5942a14103720910a8c6a0aebc67f4314dd8fdd9  
Author: Jakob Kummerow <[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)>  
Date: Thu May 02 14:39:02 2024  
  
[wasm][sandbox] Fix sandbox escapes via i32 high word  
  
In-sandbox corruption could cause i64 values to be passed to  
functions expecting an i32. This patch unconditionally zeros  
the high word of i32 register parameters to prevent that.  
  
Bug: 334120897  
Change-Id: Ia19925e5133b6c560ca8308fd84ae64ff0208b86  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5494364](<https://chromium-review.googlesource.com/c/v8/v8/+/5494364>)  
Reviewed-by: Matthias Liedtke <[mliedtke@chromium.org](<mailto:mliedtke@chromium.org>)>  
Commit-Queue: Jakob Kummerow <[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)>  
Cr-Commit-Position: refs/heads/main@{#93680}  
  
M src/wasm/baseline/arm64/liftoff-assembler-arm64-inl.h  
M src/wasm/baseline/liftoff-assembler-inl.h  
M src/wasm/baseline/liftoff-assembler.h  
M src/wasm/baseline/liftoff-compiler.cc  
M src/wasm/baseline/loong64/liftoff-assembler-loong64-inl.h  
M src/wasm/baseline/mips64/liftoff-assembler-mips64-inl.h  
M src/wasm/baseline/riscv/liftoff-assembler-riscv64-inl.h  
M src/wasm/baseline/x64/liftoff-assembler-x64-inl.h  
M src/wasm/turboshaft-graph-interface.cc  
M test/mjsunit/mjsunit.status  
A test/mjsunit/sandbox/regress/regress-334120897.js  
  
[https://chromium-review.googlesource.com/5494364](<https://chromium-review.googlesource.com/5494364>)


---

**#17 — jk...@chromium.org — May 2, 2024 10:46PM**

Marking this issue as Fixed now. We are aware that there are additional Wasm-related sandbox escapes that will be addressed by future work.


---

**#18 — pe...@google.com — May 2, 2024 10:57PM**

Dear owner, thanks for fixing this bug. We've reopened it because security bugs need the Severity (S0-S3) and the Found In set, which will enable the bots to request merges to the correct branches ( as well as helping out our vulnerability reward and CVE processes). Please consult with any Chrome security contact ([security@chromium.org](<mailto:security@chromium.org>)) to arrange to set these labels and then this bug can be marked closed again. Thank you! Severity guidelines: [https://chromium.googlesource.com/chromium/src/+/refs/heads/main/docs/security/severity-guidelines.md#severity-guidelines-for-security-issues](<https://chromium.googlesource.com/chromium/src/+/refs/heads/main/docs/security/severity-guidelines.md#severity-guidelines-for-security-issues>) FoundIn guidelines: [https://chromium.googlesource.com/chromium/src/+/main/docs/security/security-labels.md#labels-relevant-for-any-type_bug_security](<https://chromium.googlesource.com/chromium/src/+/main/docs/security/security-labels.md#labels-relevant-for-any-type_bug_security>) Thanks for your time!


---

**#19 — sa...@google.com — May 2, 2024 11:04PM**

We currently treat V8 Sandbox bypasses as low severity. Therefore, no backmerge should be required here. The broader issue of Wasm signature mismatches will be addressed in the parent issue ([issue 336507783](<https://issues.chromium.org/issues/336507783>)).


---

**#20 — sp...@google.com — May 9, 2024 10:56AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $6000.00 for this report.  
  
Rationale for this decision:  
Congratulations! This is the first V8 sandbox bypass rewarded since the launch of the V8 sandbox bypass reward. Thank you for this report. The Chrome VRP Panel has decided to extend to you a $1,000 bonus to the $5,000 bypass reward for this, but more importantly, for the additional contributions in the course of your report about how we could improve d8 detection capabilities.   
  
Thank you and great work!   
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. Two other things we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.  
* If you are already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have already registered, there is no need to repeat the process and you’ll automatically be paid soon. If you have any payment related questions or issues, please reach out to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>).


---

**#21 — pe...@google.com — Aug 10, 2024 12:42AM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
