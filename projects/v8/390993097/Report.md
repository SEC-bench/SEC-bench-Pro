# V8 Sandbox Bypass: Potential memory corruption due to BytecodeGenerator asyncness inconsistency

Issue URL: https://issues.chromium.org/issues/390993097
VRP-Reward: 5000
Date: Jan 20, 2025 02:29PM


### VULNERABILITY DETAILS

#### Summary

Potential out-of-sandbox memory corruption due to `BytecodeGenerator::BuildAsyncReturn()` `async`ness confusion. This results in an attempt to access an invalid register index, resulting in a pointer fetch from approximately -16GiB offset from zone-allocated register list. If an attacker manages to spray a controlled pointer on this offset, this leads to controlled address write.

#### Details

It is possible to run `BytecodeGenerator` with an "incompatible" `Script` flag, where inconsistency in async/non-asyncness causes `AsyncReturnStatement` to be emitted & attempted to be built with `BytecodeGenerator::BuildAsyncReturn()` but without `BytecodeGenerator::generator_object()` being properly set. This results in using the invalid register index `kInvalidIndex` (equivalent to `kMaxInt`) in `BytecodeArrayBuilder::MoveRegister()` resulting in out-of-bounds access from `BytecodeRegisterOptimizer::register_info_table` with a large offset of `-0x7ffffff8`:

```
// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/interpreter/bytecode-register-optimizer.h;drc=27d34700b83f381c62e3a348de2e6dfdc08364b8;l=63
  void DoMov(Register input, Register output) {
    RegisterInfo* input_info = GetRegisterInfo(input);         // [!] input = generator_object(), invalid
    RegisterInfo* output_info = GetRegisterInfo(output);
    RegisterTransfer(input_info, output_info);
  }

// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/interpreter/bytecode-register-optimizer.h;drc=27d34700b83f381c62e3a348de2e6dfdc08364b8;l=167
  RegisterInfo* GetRegisterInfo(Register reg) {
    size_t index = GetRegisterInfoTableIndex(reg);
    DCHECK_LT(index, register_info_table_.size());
    return register_info_table_[index];                        // [!] unguarded out-of-bounds access
  }
  // ...
  size_t GetRegisterInfoTableIndex(Register reg) const {
    return static_cast<size_t>(reg.index() + register_info_table_offset_);
  }
```

If an attacker manages to spray enough memory so that a valid attacker-controlled address is located on that offset, this potentially results in controlled address write inside `BytecodeRegisterOptimizer::RegisterTransfer()`.

The attached repro attempts to trigger this case by `eval()`ing an invalid code which attempts `new` operator on a non-constructor. While constructing the exception `RenderCallSite()` triggers an `InterpreterCompileJob` which runs the `BytecodeGenerator`. At the same time, a malicious thread tries to corrupt `Script::flags` as `0b101` (`compilation_type = CompilationType::kEval`, `is_repl_mode = true`) where REPL mode is suspected to cause the async return behavior.

Below is the call stack & register values on crash, where we see that the index in `rcx` is indeed set to `-0x7ffffff8`.

```
--------------------------------------------------------
rax     0x9
rbx     0x555557180518
rcx     0xffffffff80000008
rdx     0x2
rdi     0x555557185f38
rsi     0x80000008
r8      0x555557186290
r9      0x4
r10     0x5555557054d4
r11     0x555557185d56
r12     0x200000002
r13     0x2
r14     0x27
r15     0x2
rbp     0x7fffffffc860
rsp     0x7fffffffc820
rip     0x555555dc7ad9
--------------------------------------------------------
// mov    rsi, qword ptr [r8 + rcx*8]
0x555555dc7ad9 <v8::internal::interpreter::BytecodeArrayBuilder::MoveRegister(v8::internal::interpreter::Register, v8::internal::interpreter::Register)+69>
0x555555de5c23 <v8::internal::interpreter::BytecodeGenerator::BuildAsyncReturn(int)+103>
0x555555df298f <v8::internal::interpreter::BytecodeGenerator::ControlScopeForTopLevel::Execute(v8::internal::interpreter::BytecodeGenerator::ControlScope::Command, v8::internal::Statement*, int)+ff>
0x555555ddada2 <v8::internal::interpreter::BytecodeGenerator::VisitReturnStatement(v8::internal::ReturnStatement*)+1c2>
0x555555dd86bb <v8::internal::interpreter::BytecodeGenerator::VisitBlockDeclarationsAndStatements(v8::internal::Block*)+18b>
0x555555dd8989 <v8::internal::interpreter::BytecodeGenerator::VisitBlock(v8::internal::Block*)+179>
0x555555dd7bcb <v8::internal::interpreter::BytecodeGenerator::GenerateBodyStatementsWithoutImplicitFinalReturn(int)+29b>
0x555555dd7082 <v8::internal::interpreter::BytecodeGenerator::GenerateBodyStatements(int)+12>
0x555555dd5998 <v8::internal::interpreter::BytecodeGenerator::GenerateBytecode(unsigned long)+2f8>
0x555555df8f78 <v8::internal::interpreter::InterpreterCompilationJob::ExecuteJobImpl()+158>
0x555555b78efa <v8::internal::Compiler::CollectSourcePositions(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::SharedFunctionInfo>)+5ba>
0x555555fb3d77 <v8::internal::SharedFunctionInfo::EnsureSourcePositionsAvailable(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::SharedFunctionInfo>)+47>
0x555555c48a8d <v8::internal::(anonymous namespace)::ComputeLocation(v8::internal::Isolate*, v8::internal::MessageLocation*)+dd>
0x555555c48538 <v8::internal::(anonymous namespace)::RenderCallSite(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::MessageLocation*, v8::internal::CallPrinter::ErrorHint*)+28>
0x555555c495d8 <v8::internal::ErrorUtils::NewConstructedNonConstructable(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::Object>)+38>
0x5555560c3047 <v8::internal::Runtime_ThrowConstructedNonConstructable(int, unsigned long*, v8::internal::Isolate*)+37>
```

> Disclaimer: The exact root cause of the bypass and its potential exploitability has not been fully analyzed in depth.

### VERSION

V8: Tested on `linux_d8_sandbox_testing` revision `98188` (commit [4214050](<https://chromium-review.googlesource.com/c/v8/v8/+/6183513>)).

### REPRODUCTION CASE

Attached as `bytecodegen-async-confusion.js`, run with `./d8 --sandbox-testing` preferrably on a non-asan build.

The repro simply attempts to trigger the bug without further exploitation attempts (e.g. heap spray), which will result in a crash on an attempt to reference approximately -16GiB address offset from the native heap.

### FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION

Type of crash: Sandbox violation

### CREDIT INFORMATION

Reporter credit: Seunghyun Lee (@0x10n) of CMU CyLab

* * *

This was discovered during a test run of a WIP v8 sandbox fuzzer.  
Marking any potential VRP reward for this bug in advance to be processed for charity.


---

**#2 — cl...@appspot.gserviceaccount.com — Jan 20, 2025 04:35PM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5286063710863360](<https://clusterfuzz.com/testcase?key=5286063710863360>).


---

**#3 — cl...@appspot.gserviceaccount.com — Jan 20, 2025 07:37PM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5666761357590528](<https://clusterfuzz.com/testcase?key=5666761357590528>).


---

**#4 — ad...@google.com — Jan 20, 2025 07:38PM**

Setting default labels for V8 sandbox escapes and assigning to the current V8 shepherd.


---

**#5 — cl...@appspot.gserviceaccount.com — Jan 22, 2025 09:31PM**

Detailed Report: [https://clusterfuzz.com/testcase?key=4644019619430400](<https://clusterfuzz.com/testcase?key=4644019619430400>)  
  
Fuzzer: None  
Job Type: linux_d8_sandbox_testing  
Platform Id: linux  
  
Crash Type: V8 sandbox violation  
Crash Address:   
Crash State:  
NULL  
Sanitizer: address (ASAN)  
  
Crash Revision: [https://clusterfuzz.com/revisions?job=linux_d8_sandbox_testing&revision=98249](<https://clusterfuzz.com/revisions?job=linux_d8_sandbox_testing&revision=98249>)  
  
Reproducer Testcase: [https://clusterfuzz.com/download?testcase_id=4644019619430400](<https://clusterfuzz.com/download?testcase_id=4644019619430400>)  
  
To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.   
  
If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.  
  
If you have any feedback on reproducing test cases, let us know at [https://forms.gle/Yh3qCYFveHj6E5jz5](<https://forms.gle/Yh3qCYFveHj6E5jz5>) so we can improve.


---

**#6 — cf...@google.com — Jan 22, 2025 09:33PM**

Thanks for the report!  
ishell@, could you PTAL?


---

**#7 — ap...@google.com — Jan 30, 2025 09:36PM**

Project: v8/v8  
Branch: main  
Author: Igor Sheludko <[ishell@chromium.org](<mailto:ishell@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6192621](<https://chromium-review.googlesource.com/6192621>)

[bytecode-generator] Harden usages of static registers

* * *

Expand for full commit details

```
[bytecode-generator] Harden usages of static registers 
 
Ensure that incoming_new_target_or_generator_ and 
current_disposables_stack_ registers are initialized before use. 
 
Fixed: 390993097 
Change-Id: Ia8f76ec012589bdf580d40ae3764250e58429eef 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6192621 
Reviewed-by: Toon Verwaest <verwaest@chromium.org> 
Commit-Queue: Toon Verwaest <verwaest@chromium.org> 
Auto-Submit: Igor Sheludko <ishell@chromium.org> 
Cr-Commit-Position: refs/heads/main@{#98411}
```

* * *

Files:

  * M `src/interpreter/bytecode-generator.cc`
  * M `src/interpreter/bytecode-generator.h`

* * *

Hash: 20265548229c22a8795a563dac2629c6ddfc10f0  
Date: Thu Jan 23 13:14:02 2025

* * *


---

**#8 — is...@chromium.org — Jan 30, 2025 09:49PM**

Thank you for the report!

I'm not sure how exploitable it's going to be in practice, maybe security folks could chime in and update the severity of this issue.


---

**#9 — sr...@google.com — Jan 30, 2025 10:07PM**

> If an attacker manages to spray a controlled pointer on this offset, this leads to controlled address write.

We should assume that this is possible, let's consider this exploitable. So the current priority/severity looks fine.


---

**#10 — sp...@google.com — Feb 6, 2025 10:55AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $5000.00 for this report.  
  
Rationale for this decision:  
V8 sandbox bypass reward for demonstrating memory corruption outside the V8 heap sandbox   
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#11 — am...@chromium.org — Feb 6, 2025 11:12AM**

Congratulations, Seunghyun! Thank you for your efforts against the V8 sandbox and reporting this issue to us.


---

**#12 — ch...@google.com — May 9, 2025 09:38PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
