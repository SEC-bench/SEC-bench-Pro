# V8 Sandbox Bypass: Code Pointer Table Index Confusion leading to Stack Corruption

Issue URL: https://issues.chromium.org/issues/344343031
VRP-Reward: 5000
Date: Jun 2, 2024 11:24PM


I have initially modified the component to V8 (<https://issues.chromium.org/issues/344128766>), seemingly making it publicly available for a brief amount of time. I could delete everything but the title and reported it and hope it can be removed ASAP. I am very sorry for this mistake.

* * *

# V8 Sandbox Bypass: Code Pointer Table Index Confusion leading to Stack Corruption

### VULNERABILITY DETAILS

The Code Pointer Table doesn't include signature information allowing one to confuse two functions with different signatures. When confusing optimized functions with different argument counts, the amount of arguments removed at the end of the function do not match the arguments pushed, leading in an increase/decrease in `rsp` that can be used to corrupt stack frames.

### EXPLOIT DESCRIPTION

We create two functions `f1` and `f2`, `f1` with a lot of arguments (119) and `f2` with a few (3). The difference will lead to a huge stack shift later on that will then allow us to overlap the stack frame of the caller with a callee 's stack frame and therefore corrupt the caller's stack frame.

As we want to control the stack frame that we overlap as much as possible, we needed to look into how we can put conrolled data on the stack. We discovered that local variables of WASM functions are stored on the stack and we can fully control their values. Thus, we create a function (`fill_stack`) that allocates many local variables and sets them to the value of an argument (this lets us choose their value from JS). To prevent this function being optimized as NOP, we call an external JS function that will immediately return.

We then create a function `call_f` that will call the functions passed as arguments as follows:

  * Call first argument `argf1` with no arguments - this will be the confused function
  * Call the second argument `argf2` with the `Sandbox.targetPage` as argument - this will be used to call the WASM code and fill the stack frame with the `targetPage` value
  * Access a global variable `global_var` \- this will be used to trigger deoptimization with the invalid stack frame leading to a write to `Sandbox.targetPage`

Lastly, we initialize `global_var` with a constant (`true`) and let TurboFan optimize `f1`, `f2`, `call_f`. Then, we copy the code pointer table index of `f1` to `f2`. To trigger the write to `Sandbox.targetPage` we now update `global_var` to cause a future deoptimization and afterwards call `call_f(f2, fill_stack)`, which will lead to a sandbox violation.

### VERSION

V8 Version: verified on first tag since Sandbox VRP (12.5.151) and latest tag (12.7.174)   
Operating System: verified on Linux, x64

### REPRODUCTION CASE

The PoC is attached as `poc.js`. The generator script for the WASM code is given in `create_wasm.py`. A `Dockerfile` for reproduction is also attached.

The `Dockerfile` uses the arguments and flags described by the Chrome VRP rules ( [https://bughunters.google.com/about/rules/chrome-friends/5745167867576320/chrome-vulnerability-reward-program-rules#v8-sandbox-bypass-rewards](<https://bughunters.google.com/about/rules/chrome-friends/5745167867576320/chrome-vulnerability-reward-program-rules#v8-sandbox-bypass-rewards>)).

The PoC is fully reliable and should work on all versions since the release of the sandbox testing mode. The only hardcoded offset in the PoC is the offset from a `JSFunction` object to its `code` attribute.

### CREDIT INFORMATION

Reporter credit: Fabian Kilger (fkil)


---

**#2 — za...@google.com — Jun 4, 2024 03:43AM**

Thanks for reporting. Can you please attach a POC for this bug. I don't see it in the bug. Thanks.


---

**#3 — ki...@sec.in.tum.de — Jun 4, 2024 03:46AM**

It seems I've forgotten the files when re-creating the issue, I'm sorry. Here they are:


---

**#4 — ki...@sec.in.tum.de — Jun 4, 2024 03:25PM**

It seems the `Comment` function deleted my text and only uploaded the file...

I've taken a closer look at the source of the problem and the problem is a big deeper than initially thought. It is related to the `formal_parameter_count` value of the `SharedFunctionInfo` object. This attribute is used to push enough arguments before the call. The problem now arises, if this value is changed or does not match up with the amount of arguments the compiled function expects.

As such, a potential fix would need to tackle the following problems:

  * The `formal_parameter_count` is still in the JS-Heap and thus can be modified leading to the same Bypass (see `poc2.js`)
  * One cannot mix a `SharedFunctionInfo` with function A with the `Code` object of another function B. A potential fix would be to protect all relevant fields by putting them in the same `CodePointerTable` entry, e.g. storing the trusted portion of `SharedFunctionInfo` in the table and using the same attribute to access the `Code` object and the `SharedFunctionInfo`


---

**#5 — cl...@appspot.gserviceaccount.com — Jun 4, 2024 05:23PM**

Detailed Report: [https://clusterfuzz.com/testcase?key=4827811603742720](<https://clusterfuzz.com/testcase?key=4827811603742720>)  
  
Fuzzer: None  
Job Type: linux_d8_sandbox_testing  
Platform Id: linux  
  
Crash Type: V8 sandbox violation  
Crash Address:   
Crash State:  
NULL  
Sanitizer: address (ASAN)  
  
Crash Revision: [https://clusterfuzz.com/revisions?job=linux_d8_sandbox_testing&revision=94221](<https://clusterfuzz.com/revisions?job=linux_d8_sandbox_testing&revision=94221>)  
  
Reproducer Testcase: [https://clusterfuzz.com/download?testcase_id=4827811603742720](<https://clusterfuzz.com/download?testcase_id=4827811603742720>)  
  
To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.   
  
If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.  
  
If you have any feedback on reproducing test cases, let us know at [https://forms.gle/Yh3qCYFveHj6E5jz5](<https://forms.gle/Yh3qCYFveHj6E5jz5>) so we can improve.


---

**#6 — sa...@chromium.org — Jun 4, 2024 09:58PM**

Awesome work, thanks a lot! Yes indeed, the issue ultimately is the SharedFunctionInfo::formal_parameter_count, which is considered "trusted" by some parts of the engine while it really isn't. We have an [open umbrella bug](<https://issues.chromium.org/issues/40931165>) for that which I've just now made public. I'll set that as parent bug. Your way of exploiting this issue is also very nice, and I've successfully reproduced it on Clusterfuzz!

We've tried some prototypes for fixing this. Currently, the most promising approach seems to be to entirely deprecate this field and replace it with the `parameter_count` on Code/BytecodeArray so that there cannot be a mismatch between the parameter count and the actual code that is executed anymore.


---

**#7 — ki...@sec.in.tum.de — Jun 5, 2024 01:16AM**

Great to hear back and that it's appreciated! I'm confused about making it public though. As it is a stack corruption, execution of arbitrary shellcode is possible. I've also now developed a PoC for Code Execution for V8 tag 12.7.174 that I could share to proof this. I believe it should be unaffected by the most recent changes as well and I could test later.


---

**#8 — sa...@chromium.org — Jun 5, 2024 01:29AM**

Yeah the issue is definitely exploitable, and not yet fixed, so we'll keep this report as type:vulnerability (and not duplicate it into the feature bug). We don't yet consider the sandbox fully functional and so for example still make "feature" bugs that are actively worked on public. Another example is [issue 40940619](<https://issues.chromium.org/issues/40940619>). Since all the WIP CLs (which describe the underlying issue in detail) are anyway publicly visible, this doesn't make too much of a difference but adds some transparency.


---

**#9 — 24...@project.gserviceaccount.com — Jun 13, 2024 04:38PM**

ClusterFuzz testcase 4827811603742720 is verified as fixed in [https://clusterfuzz.com/revisions?job=linux_d8_sandbox_testing&range=94415:94416](<https://clusterfuzz.com/revisions?job=linux_d8_sandbox_testing&range=94415:94416>)  
  
If this is incorrect, please add the hotlistid:5432646 and re-open the issue.


---

**#10 — ki...@sec.in.tum.de — Jun 13, 2024 09:43PM**

This seems incorrect to me, compiling the main branch on the corresponding commit and testing the PoC still leads to a sandbox violation. I don't think I can re-open the issue or add the hotlistid


---

**#11 — cl...@chromium.org — Jun 14, 2024 08:00PM**

Agreed, the bisection does not make sense (points to a revert of a change that just landed on 12th of June).

Re-opening.


---

**#12 — ti...@chromium.org — Jun 27, 2024 05:46PM**

Adding `ClusterFuzz-Ignore` hotlist to all `ClusterFuzz-Wrong` issues per [crbug.com/40285975](<http://crbug.com/40285975>).


---

**#13 — sa...@chromium.org — Oct 22, 2024 08:10PM**

This should now be fixed with [https://chromium-review.googlesource.com/c/v8/v8/+/5832362](<https://chromium-review.googlesource.com/c/v8/v8/+/5832362>) (with [https://chromium-review.googlesource.com/c/v8/v8/+/5844709](<https://chromium-review.googlesource.com/c/v8/v8/+/5844709>) and [https://chromium-review.googlesource.com/c/v8/v8/+/5906113](<https://chromium-review.googlesource.com/c/v8/v8/+/5906113>) fixing direct variants). We now store the parameter count (~= the signature) in the JSDispatchTable and can therefore make sure that callee and caller always agree on the signature. Other problems related to SFI::formal_parameter_count will be addressed as part of [issue 40931165](<https://issues.chromium.org/issues/40931165>).


---

**#14 — sp...@google.com — Nov 19, 2024 06:55AM**

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

**#15 — am...@chromium.org — Nov 19, 2024 07:00AM**

Congratulations Fabian! Thank you for this V8 sandbox bypass submission -- nice work!


---

**#16 — cl...@chromium.org — Jan 8, 2026 07:33PM**

Removing `Clusterfuzz-ignore` hotlist from some old bugs as it's preventing Clusterfuzz from filing similar bugs.
