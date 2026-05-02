# V8 Sandbox Bypass: AAW/PC control by dispatching CEntry and CCall functions

Issue URL: https://issues.chromium.org/issues/445209324
VRP-Reward: 5000
Date: Sep 16, 2025 11:45AM


### VULNERABILITY DETAILS

#### Summary

Builtins such as `CEntry_Return1_ArgvOnStack_NoBuiltinExit` and `MemCopyUint8Uint8` are installable on JS dispatch entries and dispatchable when they likely should not be. As, these can be used to perform attacker controlled control-flow hijacks and/or arbitrary writes.

**Suggested Fix:** Prevent them from being dispatchable, maybe by changing their tags.

#### Details

Per [JSDispatchTable::IsCompatibleCode](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/sandbox/js-dispatch-table-inl.h;l=338-351;drc=e8dda6d37a03884df888e021881e203e9b180f39>), as long as the code has a `kJSEntrypointTag` and the same parameter count it should be fine to install the code onto the dispatch entry:

```
bool JSDispatchTable::IsCompatibleCode(Tagged<Code> code,
                                       uint16_t parameter_count) {
  if (code->entrypoint_tag() != kJSEntrypointTag) {
    // Target code doesn't use JS linkage. This cannot be valid.
    return false;
  }
  if (code->parameter_count() == parameter_count) {
    DCHECK_IMPLIES(code->is_builtin(),
                   parameter_count ==
                       Builtins::GetFormalParameterCount(code->builtin_id()));
    // Dispatch entry and code have the same signature. This is correct.
    return true;
  }
  // ...
}
```

Also, notice how `kJSEntrypointTag` is the same as `kDefaultCodeEntryPointTag` per [the CodeEntryPointTag definition](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/sandbox/code-entrypoint-tag.h;l=36-40;drc=48d6f7175422b2c969c14258f9f8d5b196c28d18>):

```
enum CodeEntrypointTag : uint64_t {
  // TODO(saelo): eventually, we'll probably want to remove the default tag.
  kDefaultCodeEntrypointTag = 0,
  // TODO(saelo): give these unique tags.
  kJSEntrypointTag = kDefaultCodeEntrypointTag,
  // ...
}
```

Since `CCall` and `CEntryDummy` [descriptors specify a kDefaultCodeEntryPointTag](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/codegen/interface-descriptors.h;l=833-854;drc=0a91fc6f342076067be3ddfbac77574c1a3eec2f0>), their functions would be installable onto a dispatch entry:

```
class CCallDescriptor : public StaticCallInterfaceDescriptor<CCallDescriptor> {
 public:
  SANDBOX_EXPOSED_DESCRIPTOR(kDefaultCodeEntrypointTag)
  // ...
};

// TODO(jgruber): Consider filling in the details here; however, this doesn't
// make too much sense as long as the descriptor isn't used or verified.
class CEntryDummyDescriptor
    : public StaticCallInterfaceDescriptor<CEntryDummyDescriptor> {
 public:
  SANDBOX_EXPOSED_DESCRIPTOR(kDefaultCodeEntrypointTag)
  // ...
};
```

Thus, these functions (exhuastively at the time of the report) are callable at will by an attacker:

  * `CEntry_Return1_ArgvOnStack_NoBuiltinExit` (`CEntryDummy`)
  * `CEntry_Return2_ArgvOnStack_BuiltinExit` (`CEntryDummy`)
  * `CEntry_Return2_ArgvOnStack_NoBuiltinExit` (`CEntryDummy`)
  * `WasmCEntry` (`CEntryDummy`)
  * `DirectCEntry` (`CEntryDummy`)
  * `MemCopyUint8Uint8` (`CCall`)
  * `MemMove` (`CCall`)

These are functions that make indirect calls or copy arbitrary memory using caller-passed arguments leading trivially to their respective vulnerabilities.

In the PoC, `CEntry_Return1_ArgvOnStack_NoBuiltinExit` is exploited as an example to show that the PC can be set to wherever an attacker wants. In the case of this particular function in x64, [an indirect call to `rbx` is made](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/builtins/x64/builtins-x64.cc;l=4288;drc=48d6f7175422b2c969c14258f9f8d5b196c28d18>), so as long as an attacker controls it they can hijack control flow to wherever is desired.

### VERSION

V8 commit: 17e54fe092d2454daa9c91b56fca39ff51ae8589

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
Sandbox bounds: [0x6df800000000,0x6ef800000000)

## V8 sandbox violation detected!

Access type was read though which is technically not a sandbox violation. This requires manual investigation.
AddressSanitizer:DEADLYSIGNAL
=================================================================
==199888==ERROR: AddressSanitizer: SEGV on unknown address 0x424242424242 (pc 0x424242424242 bp 0x7ffc4afba440 sp 0x7ffc4afba428 T0)
==199888==The signal is caused by a READ memory access.
    #0 0x424242424242  (<unknown module>)
    #1 0x5b8ce000067e  (<unknown module>)
    #2 0x5b8c8305b7a9 in Builtins_InterpreterEntryTrampoline setup-isolate-deserialize.cc
    #3 0x5b8c8305855b in Builtins_JSEntryTrampoline setup-isolate-deserialize.cc
    #4 0x5b8c830582aa in Builtins_JSEntry setup-isolate-deserialize.cc
    #5 0x5b8c7ec1a2e2 in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/simulator.h:212:12
    #6 0x5b8c7ec1b868 in v8::internal::Execution::CallScript(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>) src/execution/execution.cc:542:10
    #7 0x5b8c7e7a720d in v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) src/api/api.cc:1964:7
    #8 0x5b8c7e4cfad6 in v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) src/d8/d8.cc:1036:44
    #9 0x5b8c7e507a2d in v8::SourceGroup::Execute(v8::Isolate*) src/d8/d8.cc:5498:10
    #10 0x5b8c7e513823 in v8::Shell::RunMainIsolate(v8::Isolate*, bool) src/d8/d8.cc:6454:37
    #11 0x5b8c7e512c55 in v8::Shell::RunMain(v8::Isolate*, bool) src/d8/d8.cc:6362:18
    #12 0x5b8c7e51635c in v8::Shell::Main(int, char**) src/d8/d8.cc:7252:18
    #13 0x73399ba2a1c9 in __libc_start_call_main csu/../sysdeps/nptl/libc_start_call_main.h:58:16
    #14 0x73399ba2a28a in __libc_start_main csu/../csu/libc-start.c:360:3
    #15 0x5b8c7e3c2029 in _start (/home/krish/chrome/v8/v8/out/asan_no_dcheck/d8+0x1f93029) (BuildId: bb373f7468777334)

==199888==Register values:
rax = 0x0000000000000001  rbx = 0x0000424242424242  rcx = 0x00005b8c83106cc0  rdx = 0x000072499aee1000  
rdi = 0x0000000000000001  rsi = 0x00007ffc4afba450  rbp = 0x00007ffc4afba440  rsp = 0x00007ffc4afba428  
 r8 = 0x00006f391b004000   r9 = 0x00007eae008003b9  r10 = 0x00006f39470dc000  r11 = 0x00006df800840000  
r12 = 0x00007eae008000fd  r13 = 0x000072499aee1080  r14 = 0x00006df800000000  r15 = 0x00007ffc4afba450  
AddressSanitizer can not provide additional info.
SUMMARY: AddressSanitizer: SEGV (<unknown module>) 
==199888==ABORTING
```

### FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION

Type of crash: Sandbox violation

### CREDIT INFORMATION

Reporter credit: Krishna Ravishankar (@krsh732)


---

**#2 — cl...@appspot.gserviceaccount.com — Sep 16, 2025 12:40PM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=4720594134171648](<https://clusterfuzz.com/testcase?key=4720594134171648>).


---

**#3 — kr...@gmail.com — Sep 16, 2025 09:38PM**

> Suggested Fix: Prevent them from being dispatchable, maybe by changing their tags.

Alternatively, maybe `JSDispatchTable::IsCompatibleCode` should use [`Builtins::HasJSLinkage`](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/builtins/builtins.cc;l=227;drc=48d6f7175422b2c969c14258f9f8d5b196c28d18>) to check if the builtin really has JS linkage. ie.

```
bool JSDispatchTable::IsCompatibleCode(Tagged<Code> code,
                                       uint16_t parameter_count) {
  if (code->is_builtin()) {
    if (!Builtins::HasJSLinkage(code->builtin_id())) {
        // Builtin code doesn't use JS linkage. This cannot be valid.
        return false;
      }
  } else if (code->entrypoint_tag() != kJSEntrypointTag) {
    // Target code doesn't use JS linkage. This cannot be valid.
    return false;
  }
  // ...
}
```


---

**#4 — kr...@gmail.com — Sep 16, 2025 10:22PM**

I'll try and put up a CL based on #3 for review.


---

**#5 — dx...@google.com — Sep 17, 2025 03:36PM**

Project: v8/v8  
Branch: main  
Author: Krishna Ravishankar [krishna.ravi732@gmail.com](<mailto:krishna.ravi732@gmail.com>)  
Link: [https://chromium-review.googlesource.com/6955106](<https://chromium-review.googlesource.com/6955106>)

[sandbox] Ensure only JS linkage builtins are added to dispatch tables

* * *

Expand for full commit details

```
     
    Fixed: 445209324 
    Change-Id: Ide965ed03736799ec820ad0ba6aa153c8eb7e662 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6955106 
    Auto-Submit: Krishna Ravishankar <krishna.ravi732@gmail.com> 
    Reviewed-by: Igor Sheludko <ishell@chromium.org> 
    Reviewed-by: Michael Lippautz <mlippautz@chromium.org> 
    Commit-Queue: Michael Lippautz <mlippautz@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#102533}
```

* * *

Files:

  * M `AUTHORS`
  * M `src/sandbox/js-dispatch-table-inl.h`
  * A `test/mjsunit/sandbox/regress/regress-445209324.js`

* * *

Hash: [581bca24327d088eaa5d6689a1428aa4cf28fbb3](<https://chromiumdash.appspot.com/commit/581bca24327d088eaa5d6689a1428aa4cf28fbb3>)  
Date: Tue Sep 16 15:38:54 2025

* * *


---

**#6 — 24...@project.gserviceaccount.com — Sep 17, 2025 04:33PM**

ClusterFuzz testcase 4720594134171648 is verified as fixed in [https://clusterfuzz.com/revisions?job=linux_d8_sandbox_testing&range=102532:102533](<https://clusterfuzz.com/revisions?job=linux_d8_sandbox_testing&range=102532:102533>)  
  
If this is incorrect, please add the hotlistid:5433040 and re-open the issue.


---

**#7 — is...@chromium.org — Sep 20, 2025 12:59AM**

Thank you for the report!

This is a duplicate of an umbrella sandbox [issue 435630464](<https://issues.chromium.org/issues/435630464>) (setting JSFunction's code to a random builtin causes tons of various issues). Sandbox.setFunctionCodeToBuiltin() was introduced specifically to ease the fuzzing of such cases.

Please hold on with filing similar reports until we fix this whole class of issues.


---

**#8 — is...@chromium.org — Oct 13, 2025 05:46PM**

The [issue 435630464](<https://issues.chromium.org/issues/435630464>) should be fixed as of [https://crrev.com/c/7003083](<https://crrev.com/c/7003083>). Feel free to file new reports if you find something.


---

**#9 — kr...@gmail.com — Oct 13, 2025 07:21PM**

Thanks for the heads up. Filed [crbug/451355210](<https://crbug.com/451355210>) which wasn't covered by these patches.


---

**#10 — sp...@google.com — Nov 14, 2025 02:55AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $5000.00 for this report.  
  
Rationale for this decision:  
v8 sandbox bypass without demonstrating a controlled write  
  
  
Important: This payment will be issued by Bugcrowd. You will receive an email from Bugcrowd in the next 24 hours which contains a submission you must claim to be rewarded.  
  
If you do not receive an email from them, please check your spam folder and then reach out to us via a comment here. For issues related to Bugcrowd itself, please contact them via [https://bugcrowd.com/support](<https://bugcrowd.com/support>).  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#11 — ch...@google.com — Dec 25, 2025 09:40PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
