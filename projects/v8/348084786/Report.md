# V8 Sandbox Bypass: with Shared Function Info

Issue URL: https://issues.chromium.org/issues/348084786
VRP-Reward: 5000
Date: Jun 19, 2024 07:03PM


# Steps to reproduce the problem

at (1). `shared_function_info` stored inside heap so we can control `length` field, with `popCount` we can manipulate stack address to anywhere we want.

```
 let popCount = arguments.length;
  const declaredArgCount =
      Convert<intptr>(Convert<int32>(target.shared_function_info.length)); (1)
  if (declaredArgCount > popCount) {
    popCount = declaredArgCount;
  }
   // Also pop the receiver.
  PopAndReturn(popCount + 1, result);
```

So we controlled it to make it call to `v8::internal::Histogram::AddSample(` and with controlled argument we can hijack RIP.

[https://source.chromium.org/chromium/chromium/src/+/main:v8/src/builtins/js-to-wasm.tq;l=760](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/builtins/js-to-wasm.tq;l=760>)

# Problem Description

Environment tested:

```
commit cdbc1d9684a3602c77c39d23b4e95a8522a0cc90 (HEAD, origin/main, origin/HEAD)
Author: Darius Mercadier <dmercadier@chromium.org>
Date:   Tue Jun 18 16:10:26 2024 +0200

cat out/r/args.gn 
is_debug = false
dcheck_always_on = false
target_cpu = "x64"
v8_enable_memory_corruption_api = true

./out/r/d8 --expose-gc --allow-natives-syntax --sandbox-testing    --experimental-wasm-memory64 /util/sbx_fuzz/ppp.js 
Sandbox testing mode is enabled. Write to the page starting at 0x97d8d31b000 (available from JavaScript as `Sandbox.targetPage`) to demonstrate a sandbox bypass.
[*] Leak sandbox base address
heap_addr: 0x1d8d00000000
target_page: 0x97d8d31b000
1d8d00200000
offset_base: 0x200171

## V8 sandbox violation detected!

Received signal 11 SEGV_ACCERR 097d8d31b000

==== C stack trace ===============================

 [0x618bb6608857]
 [0x7c0376242520]
 [0x097d8d31b000]
[end of stack trace]
Segmentation fault
```

# Summary

V8 Sandbox Bypass: with Shared Function Info

# Additional Data

Category: Security   
Chrome Channel: Not sure   
Regression: N/A


---

**#2 — d8...@gmail.com — Jun 20, 2024 05:54PM**

I modified testcase a bit to avoid some uneccessary flags:  
```bash  
./out/r/d8 --sandbox-testing ppp1.js   
Sandbox testing mode is enabled. Write to the page starting at 0x1f30aa8d6000 (available from JavaScript as `Sandbox.targetPage`) to demonstrate a sandbox bypass.  
[*] Leak sandbox base address  
heap_addr: 0x26e300000000  
target_page: 0x1f30aa8d6000  
26e300200000  
offset_base: 0x200171  
  
## V8 sandbox violation detected!  
  
Received signal 11 SEGV_ACCERR 1f30aa8d6000  
  
==== C stack trace ===============================  
  
[0x5c227daa2857]  
[0x7d811e442520]  
[0x1f30aa8d6000]  
[end of stack trace]  
```


---

**#3 — pe...@google.com — Jun 21, 2024 12:40AM**

Setting milestone because of s2 severity.


---

**#4 — sa...@chromium.org — Jun 24, 2024 06:20PM**

Ah very nice, thanks for the report! I guess this is related to [issue 40931165](<https://issues.chromium.org/issues/40931165>). I wonder if that code snippet ([https://source.chromium.org/chromium/chromium/src/+/main:v8/src/builtins/js-to-wasm.tq;l=760](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/builtins/js-to-wasm.tq;l=760>)) should actually be using .formal_parameter_count instead of .length, since that's the number of declared parameters for the purpose of argument adaption (which we're doing here). In any case I'll keep this as a separate issue since it's not clear that our current approach for [issue 40931165](<https://issues.chromium.org/issues/40931165>) would also fix this issue here (since we're using the .length property).


---

**#5 — cl...@appspot.gserviceaccount.com — Oct 24, 2024 12:05AM**

Detailed Report: [https://clusterfuzz.com/testcase?key=5690248654684160](<https://clusterfuzz.com/testcase?key=5690248654684160>)  
  
Fuzzer: None  
Job Type: linux_asan_d8_sandbox_fuzzing  
Platform Id: linux  
  
Crash Type: V8 sandbox violation  
Crash Address: 0x7ffcc079d7e8  
Crash State:  
Builtins_JSToWasmWrapper  
Builtins_JSEntryTrampoline  
Builtins_JSEntry  
  
Sanitizer: address (ASAN)  
  
Regressed: [https://clusterfuzz.com/revisions?job=linux_asan_d8_sandbox_fuzzing&range=96441:96442](<https://clusterfuzz.com/revisions?job=linux_asan_d8_sandbox_fuzzing&range=96441:96442>)  
  
Reproducer Testcase: [https://clusterfuzz.com/download?testcase_id=5690248654684160](<https://clusterfuzz.com/download?testcase_id=5690248654684160>)  
  
To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.   
  
If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.  
  
If you have any feedback on reproducing test cases, let us know at [https://forms.gle/Yh3qCYFveHj6E5jz5](<https://forms.gle/Yh3qCYFveHj6E5jz5>) so we can improve.


---

**#6 — sa...@chromium.org — Oct 24, 2024 12:07AM**

I think we now finally have the infrastructure ([Leaptiering](<https://docs.google.com/document/d/1WkyEynMluvIr0LBmrapyF7MiE8wIHFHnlP5B6FFhQuA/edit?usp=sharing>)) in place to properly fix this. I'l prepare a fix.


---

**#7 — 24...@project.gserviceaccount.com — Oct 24, 2024 12:16AM**

Automatically applying components based on crash stacktrace and information from OWNERS files.  
  
If this is incorrect, please apply the hotlistid:4801165.


---

**#8 — ap...@google.com — Oct 25, 2024 11:37PM**

Project: v8/v8  
Branch: main  
Author: Samuel Groß <[saelo@chromium.org](<mailto:saelo@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/5956412](<https://chromium-review.googlesource.com/5956412>)

[sandbox] Introduce "dynamic" parameter counts in code assembler

* * *

Expand for full commit details

```
[sandbox] Introduce "dynamic" parameter counts in code assembler 
 
All Code assembled through the CodeStubAssembler always has a "static" 
parameter count as defined by its call descriptor. However, certain 
special builtins also have a "dynamic" parameter count: they are defined 
as varargs builtins (the static parameter count is zero) but they can be 
installed on JSFunctions with different parameter counts. In those 
cases, the builtins previously had to manually determine the correct 
parameter count to determine the total number of arguments (including 
padding) to be able to remove them from the stack in the epilogue. For 
that, they relied on the SFI::formal_parameter_count, and so this was 
not sandbox-compatible. 
 
With this CL, we now introduce the concept of "dynamic" parameter counts 
in the code assembler and allow these builtins to express that they 
support that (via SetSupportsDynamicParameterCount()). The actual 
parameter count is then loaded via the dispatch table and so is 
guaranteed to be correct. Then, CodeStubArguments::PopAndReturn takes 
this into account to properly remove all arguments. 
 
This CL then migrates the InstantiateAsmJs builtin to use the new 
approach for handling padding arguments. A follow-up CL will do the same 
for torque builtins. 
 
Bug: 40931165, 348084786 
Change-Id: I33f189e4e44de3bbaa17111d870da845e08eb3a5 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/5956412 
Reviewed-by: Nico Hartmann <nicohartmann@chromium.org> 
Commit-Queue: Samuel Groß <saelo@chromium.org> 
Reviewed-by: Igor Sheludko <ishell@chromium.org> 
Cr-Commit-Position: refs/heads/main@{#96835}
```

* * *

Files:

  * M `src/builtins/builtins-internal-gen.cc`
  * M `src/codegen/code-stub-assembler.cc`
  * M `src/codegen/code-stub-assembler.h`
  * M `src/compiler/code-assembler.cc`
  * M `src/compiler/code-assembler.h`
  * M `src/compiler/raw-machine-assembler.cc`
  * M `src/compiler/raw-machine-assembler.h`
  * M `src/sandbox/js-dispatch-table-inl.h`

* * *

Hash: b4e2df91ba38537c97b6257f931ad6f8b0dd9989  
Date: Fri Oct 25 11:14:35 2024

* * *


---

**#9 — ap...@google.com — Oct 26, 2024 12:06AM**

Project: v8/v8  
Branch: main  
Author: Samuel Groß <[saelo@chromium.org](<mailto:saelo@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/5965733](<https://chromium-review.googlesource.com/5965733>)

[sandbox] Use dynamic parameter count in generic JSToX wrapper builtins

* * *

Expand for full commit details

```
[sandbox] Use dynamic parameter count in generic JSToX wrapper builtins 
 
This is a follow-up for crrev.com/c/5956412 that now migrates the 
generic JSToWasm and JSToJS wrappers to use the new dynamic parameter 
count feature instead of manually obtaining the formal parameter count 
of their function to perform a PopAndReturn. 
 
Bug: 40931165, 348084786 
Change-Id: Ied8d2b2887c597c4d3e6382a54bd49c1d4aeaf68 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/5965733 
Commit-Queue: Samuel Groß <saelo@chromium.org> 
Reviewed-by: Igor Sheludko <ishell@chromium.org> 
Reviewed-by: Nico Hartmann <nicohartmann@chromium.org> 
Cr-Commit-Position: refs/heads/main@{#96836}
```

* * *

Files:

  * M `src/builtins/base.tq`
  * M `src/builtins/js-to-js.tq`
  * M `src/builtins/js-to-wasm.tq`
  * M `src/sandbox/testing.cc`
  * M `src/torque/constants.h`
  * M `src/torque/implementation-visitor.cc`
  * M `src/torque/type-oracle.h`
  * A `test/mjsunit/sandbox/regress/regress-348084786.js`

* * *

Hash: 081a631e8f1dc140d48fcce617c1ca2d87e25db4  
Date: Fri Oct 25 11:26:21 2024

* * *


---

**#10 — 24...@project.gserviceaccount.com — Oct 26, 2024 12:20AM**

ClusterFuzz testcase 5690248654684160 is verified as fixed in [https://clusterfuzz.com/revisions?job=linux_asan_d8_sandbox_fuzzing&range=96835:96836](<https://clusterfuzz.com/revisions?job=linux_asan_d8_sandbox_fuzzing&range=96835:96836>)  
  
If this is incorrect, please add the hotlistid:5433040 and re-open the issue.


---

**#11 — sp...@google.com — Nov 19, 2024 06:55AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $5000.00 for this report.  
  
Rationale for this decision:  
V8 sandbox bypass reward  
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#12 — am...@chromium.org — Nov 19, 2024 07:02AM**

Congratulations! Thank you for your efforts and submitting this V8 sandbox bypass to us -- nice work!


---

**#13 — pe...@google.com — Feb 2, 2025 12:45AM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
