# V8 Sandbox Bypass: AAW/PC control via DebugBreakTrampoline

Issue URL: https://issues.chromium.org/issues/445966259
VRP-Reward: 20000
Date: Sep 19, 2025 08:39AM


### VULNERABILITY DETAILS

#### Details

It's possible to tail call into any builtin from DebugBreakTrampoline regardless of linkage, allowing an attacker to escape the sandbox.

The crux of the issue can be seen in [DebugBreakTrampoline](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/builtins/builtins-internal-gen.cc;l=111-118;drc=6749ee535fe656b4e0d47e6a5e7e62d93693dd02>):

```
TF_BUILTIN(DebugBreakTrampoline, CodeStubAssembler) {
  // ...snipped...
  CallRuntime(Runtime::kDebugBreakAtEntry, context, function);
  Goto(&tailcall_to_shared);

  BIND(&tailcall_to_shared);
  // Tail call into code object on the SharedFunctionInfo.
  TNode<Code> code = GetSharedFunctionInfoCode(shared);

  // [!!!] Linkage was not validated

  // TailCallJSCode will take care of parameter count validation between the
  // code and dispatch handle.
  TailCallJSCode(code, context, function, new_target, arg_count,
                 dispatch_handle);
}
```

There is no linkage validation after retrieving the code from the SharedFunctionInfo. Thus, one can store builtins such as `CEntry_Return1_ArgvOnStack_NoBuiltinExit` and/or `MemCopyUint8Uint8` within the SharedFunctionInfo to obtain PC control/AAW.

For the PoC, the `CEntry_Return1_ArgvOnStack_NoBuiltinExit` builtin was abused similar to [crbug/445209324](<https://crbug.com/445209324>) to obtain PC control.

**Suggested Fix:** Validate linkage before tail-calling, as presumably this trampoline is meant to only be used for JS linkage functions.

### VERSION

V8 commit: 3d0f462a17ffa08869805874ac46726783512fef

#### REPRODUCTION CASE

**NOTE (for the shepherd):** To reproduce in CF, the `linux_d8_sandbox_testing` job type with the below shell args should hopefully do the trick.

**Shell args** : `--allow-natives-syntax --sandbox-testing`

**Build args** :

```
is_debug=false
is_asan=true
v8_enable_sandbox=true
v8_enable_memory_corruption_api=true
dcheck_always_on=false
target_cpu="x64"
```

**Sample output (`--disable-in-process-stack-traces` used to show PC)**:

```
Sandbox testing mode is enabled. Only sandbox violations will be reported, all other crashes will be ignored.
Sandbox bounds: [0x745500000000,0x755500000000)

## V8 sandbox violation detected!

Access type was read though which is technically not a sandbox violation. This requires manual investigation.
AddressSanitizer:DEADLYSIGNAL
=================================================================
==152308==ERROR: AddressSanitizer: SEGV on unknown address 0x424242424242 (pc 0x424242424242 bp 0x7ffd64b8e4f0 sp 0x7ffd64b8e4d8 T0)
==152308==The signal is caused by a READ memory access.
    #0 0x424242424242  (<unknown module>)
    #1 0x5b4cc710023e  (<unknown module>)
    #2 0x5b4c671287a9 in Builtins_InterpreterEntryTrampoline setup-isolate-deserialize.cc
    #3 0x5b4c6712555b in Builtins_JSEntryTrampoline setup-isolate-deserialize.cc
    #4 0x5b4c671252aa in Builtins_JSEntry setup-isolate-deserialize.cc
    #5 0x5b4c62b7a3a2 in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/simulator.h:212:12
    #6 0x5b4c62b7b928 in v8::internal::Execution::CallScript(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>) src/execution/execution.cc:542:10
    #7 0x5b4c627071ad in v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) src/api/api.cc:1955:7
    #8 0x5b4c6242fad6 in v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) src/d8/d8.cc:1036:44
    #9 0x5b4c6246794d in v8::SourceGroup::Execute(v8::Isolate*) src/d8/d8.cc:5487:10
    #10 0x5b4c62473743 in v8::Shell::RunMainIsolate(v8::Isolate*, bool) src/d8/d8.cc:6443:37
    #11 0x5b4c62472b75 in v8::Shell::RunMain(v8::Isolate*, bool) src/d8/d8.cc:6351:18
    #12 0x5b4c6247627c in v8::Shell::Main(int, char**) src/d8/d8.cc:7241:18
    #13 0x79964562a1c9 in __libc_start_call_main csu/../sysdeps/nptl/libc_start_call_main.h:58:16
    #14 0x79964562a28a in __libc_start_main csu/../csu/libc-start.c:360:3
    #15 0x5b4c62322029 in _start (/home/krish/chrome/v8/v8/out/asan_no_dcheck/d8+0x1f92029) (BuildId: 4f9566aef8cd1e75)

==152308==Register values:
rax = 0x0000000000000001  rbx = 0x0000424242424242  rcx = 0x00005b4c671d3d40  rdx = 0x000078a644ae1000  
rdi = 0x0000000000000001  rsi = 0x00007ffd64b8e500  rbp = 0x00007ffd64b8e4f0  rsp = 0x00007ffd64b8e4d8  
 r8 = 0x00007455000c0671   r9 = 0x0000000000000000  r10 = 0x0000759600c64000  r11 = 0x0000000000000000  
r12 = 0x0000744bf0000000  r13 = 0x000078a644ae1080  r14 = 0x0000745500000000  r15 = 0x00007ffd64b8e500  
AddressSanitizer can not provide additional info.
SUMMARY: AddressSanitizer: SEGV (<unknown module>) 
==152308==ABORTING
```

### FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION

Type of crash: Sandbox violation

### CREDIT INFORMATION

Reporter credit: Krishna Ravishankar (@krsh732)


---

**#2 — cl...@appspot.gserviceaccount.com — Sep 19, 2025 01:30PM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5544244676591616](<https://clusterfuzz.com/testcase?key=5544244676591616>).


---

**#3 — is...@chromium.org — Sep 20, 2025 12:43AM**

Thank you for the report!

This is a duplicate of an umbrella sandbox [issue 435630464](<https://issues.chromium.org/issues/435630464>) (setting JSFunction's code to a random builtin causes tons of various issues). `Sandbox.setFunctionCodeToBuiltin()` was introduced specifically to ease the fuzzing of such cases.

Please hold on with filing similar reports until we fix this whole class of issues.


---

**#4 — kr...@gmail.com — Sep 20, 2025 12:55AM**

Ah, I see, sounds good. ~~Should I abandon/delete[ https://chromium-review.googlesource.com/c/v8/v8/+/6965514](<https://chromium-review.googlesource.com/c/v8/v8/+/6965514>)?~~

Edit: Deleted it.


---

**#5 — dr...@chromium.org — Sep 20, 2025 07:05AM**

[security triage] ishell@ - if this is a duplicate of [https://crbug.com/435630464](<https://crbug.com/435630464>) as you note in [#comment3](<https://issues.chromium.org/issues/445966259#comment3>), can we close this out and retarget [https://crrev.com/c/6965029](<https://crrev.com/c/6965029>) to point to the canonical bug?


---

**#6 — dx...@google.com — Sep 22, 2025 06:59PM**

Project: v8/v8  
Branch: main  
Author: Igor Sheludko [ishell@chromium.org](<mailto:ishell@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6965029](<https://chromium-review.googlesource.com/6965029>)

[sandbox] Introduce kCEntryEntrypointTag for CEntry builtins

* * *

Expand for full commit details

```
     
    ... which are not compatible with JS calling convention. 
     
    Bug: 435630464 
    Change-Id: I1cb765047236fe6a970b64e4313267502e3e8fad 
    Fixed: 445966259 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6965029 
    Auto-Submit: Igor Sheludko <ishell@chromium.org> 
    Commit-Queue: Michael Lippautz <mlippautz@chromium.org> 
    Reviewed-by: Michael Lippautz <mlippautz@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#102658}
```

* * *

Files:

  * M `src/codegen/interface-descriptors.h`
  * M `src/compiler/linkage.cc`
  * M `src/sandbox/code-entrypoint-tag.h`
  * A `test/mjsunit/sandbox/regress/regress-435630464-centry.js`

* * *

Hash: [a622c3686d9b0eeb6fbf38c949252479460b967a](<https://chromiumdash.appspot.com/commit/a622c3686d9b0eeb6fbf38c949252479460b967a>)  
Date: Fri Sep 19 16:25:05 2025

* * *


---

**#7 — ch...@google.com — Sep 22, 2025 06:59PM**

Dear owner, thanks for fixing this bug. We've reopened it because:

  * Security bugs need the Severity (S0-S3) and the Found In set, which will enable the bots to request merges to the correct branches (as well as helping out our vulnerability reward and CVE processes). Please consult with any Chrome security contact ([security@chromium.org](<mailto:security@chromium.org>)) to arrange to set these labels. Severity guidelines: [https://chromium.googlesource.com/chromium/src/+/refs/heads/main/docs/security/severity-guidelines.md#severity-guidelines-for-security-issues](<https://chromium.googlesource.com/chromium/src/+/refs/heads/main/docs/security/severity-guidelines.md#severity-guidelines-for-security-issues>) FoundIn guidelines: [https://chromium.googlesource.com/chromium/src/+/main/docs/security/security-labels.md#labels-relevant-for-any-type_bug_security](<https://chromium.googlesource.com/chromium/src/+/main/docs/security/security-labels.md#labels-relevant-for-any-type_bug_security>) After resolving the above issue(s), this bug can be marked closed again. Thanks for your time!


---

**#8 — is...@chromium.org — Sep 22, 2025 07:59PM**

Let's not mark it as a duplicate of [issue 435630464](<https://issues.chromium.org/issues/435630464>) yet because it describes a bigger issue than just replacement of Code objects.


---

**#9 — 24...@project.gserviceaccount.com — Sep 23, 2025 04:44PM**

ClusterFuzz testcase 5544244676591616 is verified as fixed in [https://clusterfuzz.com/revisions?job=linux_d8_sandbox_testing&range=102657:102658](<https://clusterfuzz.com/revisions?job=linux_d8_sandbox_testing&range=102657:102658>)  
  
If this is incorrect, please add the hotlistid:5433040 and re-open the issue.


---

**#10 — ch...@google.com — Dec 10, 2025 09:44PM**

This V8 bug has been marked as either a release blocker or a vulnerability bug. V8 bugs affect all OSs supported by Chrome, so the OS field has been updated to reflect this. Please update the bug with the correct OS field if it only affects a subset of OSes.


---

**#11 — sp...@google.com — Dec 11, 2025 10:09AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $20000.00 for this report.  
  
Rationale for this decision:  
V8 sandbox escape with PC control  
  
  
Important: This payment will be issued by Bugcrowd. You will receive an email from Bugcrowd in the next 24 hours which contains a submission you must claim to be rewarded.  
  
If you do not receive an email from them, please check your spam folder and then reach out to us via a comment here. For issues related to Bugcrowd itself, please contact them via [https://bugcrowd.com/support](<https://bugcrowd.com/support>).  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#12 — ch...@google.com — Dec 30, 2025 09:40PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
