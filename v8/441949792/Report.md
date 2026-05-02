# V8 Sandbox Bypass: Argument count inconsistency due to bound args double-fetch in Generate_PushBoundArguments

Issue URL: https://issues.chromium.org/issues/441949792
VRP-Reward: 5000
Date: Aug 30, 2025 01:13AM


### VULNERABILITY DETAILS

#### Summary

(A likely) V8 sandbox bypass, argument count inconsistency due to bound arguments count double-fetch. `Generate_PushBoundArguments()` generates code which double-fetches bound arguments count which allows an attacker to push one additional argument while not updating the arguments count register. This leads to an invalid stack state where code may return back without popping the correct number of arguments, resulting in a shifted stack state (and PC control and whatnot).

This report also includes a flaw in the current `--sandbox-tracing` crash filter that makes discovery of this bug difficult (plus issues with ASAN hindering sandbox violation detection even further).

#### Details

##### The Bug

`Generate_PushBoundArguments()` double-fetches bound argument length. This leads to executing code that expects a non-zero argument length, allowing an attacker to push one argument on the stack while keeping the tracked argument count in the register same.

```
// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/builtins/x64/builtins-x64.cc;drc=5eb0af01e72f8733241dd5597c7926db3c6ee24a;l=2668
void Generate_PushBoundArguments(MacroAssembler* masm) {
  // ----------- S t a t e -------------
  //  -- rax : the number of arguments
  //  -- rdx : new.target (only in case of [[Construct]])
  //  -- rdi : target (checked to be a JSBoundFunction)
  // -----------------------------------

  // Load [[BoundArguments]] into rcx and length of that into rbx.
  Label no_bound_arguments;
  __ LoadTaggedField(rcx,
                     FieldOperand(rdi, JSBoundFunction::kBoundArgumentsOffset));  // [!] fetch #1
  __ SmiUntagFieldUnsigned(rbx,
                           FieldOperand(rcx, offsetof(FixedArray, length_)));
  __ testl(rbx, rbx);
  __ j(zero, &no_bound_arguments);
  {
    // (omitted) stack overflow check

    // Save Return Address and Receiver into registers.
    __ Pop(r8);
    __ Pop(r10);

    // Push [[BoundArguments]] to the stack.
    {
      Label loop;
      __ LoadTaggedField(
          rcx, FieldOperand(rdi, JSBoundFunction::kBoundArgumentsOffset));        // [!] fetch #2
      __ SmiUntagFieldUnsigned(
          rbx, FieldOperand(rcx, offsetof(FixedArray, length_)));
      // [!] rbx may be zero, but the loop still executes once, pushing a single argument that is not tracked in the args count.
      __ addq(rax, rbx);  // Adjust effective number of arguments.
      __ bind(&loop);
      // Instead of doing decl(rbx) here subtract kTaggedSize from the header
      // offset in order to be able to move decl(rbx) right before the loop
      // condition. This is necessary in order to avoid flags corruption by
      // pointer decompression code.
      __ LoadTaggedField(
          r12, FieldOperand(rcx, rbx, times_tagged_size,
                            OFFSET_OF_DATA_START(FixedArray) - kTaggedSize));
      __ Push(r12);
      __ decl(rbx);
      __ j(greater, &loop);
    }

    // Recover Receiver and Return Address.
    __ Push(r10);
    __ Push(r8);
  }
  __ bind(&no_bound_arguments);
}
```

Callee might then use the tracked argument count to pop arguments, which will pop one less arguments than the stack actually holds. This results in the stack to shift down by one, resulting in [returning to saved frame pointer instead of return address based on frame layouts](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/execution/frame-constants.h;l=36;drc=5eb0af01e72f8733241dd5597c7926db3c6ee24a>). Although this does not trigger a sandbox violation in the current crash filter, with sufficient coordination via chained bound functions (`fn.bind(...).bind(...)...`) the race should allow pushing arbitrary number of arguments that is untracked in the register count, potentially leading to controlled stack state.

##### Issues with Sandbox Crash Filter & ASAN

The current sandbox crash filter is highly heuristic, where its memory permission violation heuristic is overly lenient on marking crashes as non-violations. This presents significant problems in sandbox violation detection, often exacerbated with ASAN.

Case 1 (this bug). PC points to a valid non-executable address, or SP points to a valid non-RWable address. This is obviously a very bad state, and in most cases likely exploitable. Crash filter does not care and marks it as a non-violation as this is a "memory permission violation".

Case 2. Read/Write access faults on a random non-readable/writable address. Whether or not this address is allowed to fault in the sandbox perspective or not (e.g. faulting on a SegmentedTable oob access is expected while faulting on a write to d8's .rodata is definitely not), this is marked as a non-violation too.

Case 2 is especially an offending issue with ASAN as it allocates a ton of guard regions everywhere. In fact, if you take [b/390639820](<https://issues.chromium.org/issues/390639820>) and try to reproduce it with ASAN its repro rate sharply decreases, and without custom heuristics to detect Case 1 it's even harder. This somewhat explains why some fuzzers, including several different configuration of mine that I've experimented with, fails to discover / reproduce some very "shallow" bugs (in the perspective of fuzzers). This bug is also a great example - without custom heuristics to detect Case 1, the fuzzer will have near-zero chance of triggering any "sandbox violations" when the bug itself is glaringly obvious that it's definitely violating sandbox policy.

### VERSION

V8: Tested on CF asan sandbox-testing d8 @ revision 101960.

### REPRODUCTION CASE

Attached as `bound-args-shift.js`, run with `./d8 --sandbox-testing`.

The repro attempts to trigger this bug. If successful, this results in pushing one more argument that is not tracked in the argument counts, which causes the callee to return to saved frame pointer instead of return address.

DISCLAIMER: The repro itself will not trigger a sandbox violation, but instead exit with a `Caught harmless memory access violation (memory permission violation). Exiting process...`. See the details above, "Issues with Sandbox Crash Filter & ASAN" section.

### FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION

Type of crash: Sandbox violation

### CREDIT INFORMATION

Reporter credit: Seunghyun Lee (@0x10n) of CMU CyLab

* * *

This was discovered with a v8 sandbox fuzzer.  
Marking any rewards for charity in advance.


---

**#2 — se...@gmail.com — Aug 30, 2025 01:16AM**

Errata: `--sandbox-tracing` -> `--sandbox-testing`, "repro rate" -> "fuzzer crash rate"


---

**#3 — cl...@appspot.gserviceaccount.com — Aug 30, 2025 02:06AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5243277695451136](<https://clusterfuzz.com/testcase?key=5243277695451136>).


---

**#4 — ma...@google.com — Aug 30, 2025 02:11AM**

Setting provisional FoundIn and Severity Low (V8 Sandbox Bypas), and assigning to current V8 sheriff.


---

**#5 — ch...@google.com — Aug 30, 2025 09:34PM**

Setting Priority to P2 to match Severity s3. If this is incorrect, please reset the priority. The automation bot account won't make this change again.


---

**#6 — is...@chromium.org — Sep 16, 2025 08:57PM**

Thank you for the report! Unfortunately, I don't think this issue has real security implications.

While there is an unnecessary double fetching of arguments here (which we should fix), what really matters here is that we properly update the number of arguments pushed to the stack (which we do) in order to let the `Call` or `Construct` builtin properly handle incoming number of arguments when calling the actual target function.

So the worst but still harmless thing that could happen in this scenario is that the POC

  1. will push too many arguments to the stack causing SEGFAULT upon stack overflow,
  2. will push some random values as arguments (but still pointing into the V8 Sandbox area).


---

**#7 — dx...@google.com — Sep 16, 2025 10:10PM**

Project: v8/v8  
Branch: main  
Author: Igor Sheludko [ishell@chromium.org](<mailto:ishell@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6954286](<https://chromium-review.googlesource.com/6954286>)

[builtins][x64] Streamline Generate_PushBoundArguments

* * *

Expand for full commit details

```
     
    ... and avoid unnecessary double-fetching of bound arguments array. 
     
    Fixed: 441949792 
    Change-Id: I66e00420b681fb77bba2133f0c631d2721c7dfac 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6954286 
    Commit-Queue: Victor Gomes <victorgomes@chromium.org> 
    Reviewed-by: Victor Gomes <victorgomes@chromium.org> 
    Auto-Submit: Igor Sheludko <ishell@chromium.org> 
    Commit-Queue: Igor Sheludko <ishell@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#102523}
```

* * *

Files:

  * M `src/builtins/x64/builtins-x64.cc`

* * *

Hash: [36dda0d20d17529bc239deb05fc3708793346d83](<https://chromiumdash.appspot.com/commit/36dda0d20d17529bc239deb05fc3708793346d83>)  
Date: Tue Sep 16 12:34:33 2025

* * *


---

**#8 — se...@gmail.com — Sep 16, 2025 11:31PM**

Re #6: I might be wrong on this so take it with a grain of salt, but I'm curious if you've tried running the PoC? If you just run it on x64 in a debugger or with `--expose-memory-corruption-api`, you'll immediately see a crash due to an access violation on the stack which is NOT a stack overflow nor some kind of in-sandbox argument access or whatever - the RIP is literally on the stack. My analysis in the report explains why this happens, why this is a v8sbx violation, and why this is handled by the crash filter as a "harmless crash" (and why this is a significant problem with the use of ASAN). Do we have a disagreement on this, or am I misunderstanding something?

Update: The repro is flaky and works around 50% of the time. Since failures don't crash, just wrapping the PoC in a retry loop suffices to increase the success rate. I don't think this would be a blocker to repro the bug though.

* * *

The biggest confusion seems to be this part:

> [...] what really matters here is that we properly update the number of arguments pushed to the stack (which we do)

We don't. If the second fetch returns 0, it "updates" the number of arguments by adding 0 but still pushes 1 random value as an argument.


---

**#9 — is...@chromium.org — Sep 17, 2025 12:22AM**

You are right. Thanks for pointing this out.

Indeed it's a V8 Sandbox vulnerability. Resetting issue type back to Vulnerability.


---

**#10 — sp...@google.com — Sep 30, 2025 06:56AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $5000.00 for this report.  
  
Rationale for this decision:  
v8 sandbox bypass only demonstrating a read  
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#11 — ch...@google.com — Dec 24, 2025 09:40PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.


---

**#12 — ch...@google.com — Dec 24, 2025 09:42PM**

This V8 bug has been marked as either a release blocker or a vulnerability bug. V8 bugs affect all OSs supported by Chrome, so the OS field has been updated to reflect this. Please update the bug with the correct OS field if it only affects a subset of OSes.
