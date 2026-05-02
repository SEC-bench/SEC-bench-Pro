# DCHECK failure in size() > index in small-vector.h

Issue URL: https://issues.chromium.org/issues/348598133
VRP-Reward: 11000
Date: Jun 22, 2024 09:07AM


#### Description

ki...@gmail.com created issue [ #1](</issues/348598133#comment1>)

Jun 22, 2024 09:07AM

VULNERABILITY DETAILS  
## INTRODUCE  
After bisect, it was determined that following commit caused this problem.  
  
\- Commit Info  
\- Version: 92983  
\- link: [https://crrev.com/0c2b15100d997a8f1b74fcc448da319c75f2e045](<https://crrev.com/0c2b15100d997a8f1b74fcc448da319c75f2e045>)   
\- Commit Message  
  
```  
commit 0c2b15100d997a8f1b74fcc448da319c75f2e045  
Author: Adam Klein <[adamk@chromium.org](<mailto:adamk@chromium.org>)>  
Date: Thu Mar 21 13:36:59 2024 -0700  
  
[wasm][jspi][d8] Add ability to test runtime-enabling of JSPI  
  
This adds an `enableJSPI` function to the d8 test runner which  
allows simulating the way the JSPI Origin Trial in Chrome enables JSPI.  
  
Then it makes a copy of the JSPI mjsunit test to use this approach,  
rather than using a commandline flag.  
  
Bug: v8:14576  
Change-Id: I637972dcf7de288d42b1325355b08c6b1b86d9ef  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5385244](<https://chromium-review.googlesource.com/c/v8/v8/+/5385244>)  
Reviewed-by: Francis McCabe <[fgm@chromium.org](<mailto:fgm@chromium.org>)>  
Commit-Queue: Adam Klein <[adamk@chromium.org](<mailto:adamk@chromium.org>)>  
Cr-Commit-Position: refs/heads/main@{#92983}  
  
```  
  
## CRASH LOG  
\- Debug output  
  
```bash  
# CMD: /tmp/d8-linux-debug-v8-component-94592/d8 --allow-natives-syntax poc.js  
# OUTPUT ==============================================================  
  
  
#  
# Fatal error in ../../src/base/small-vector.h, line 140  
# Debug check failed: size() > index (7 vs. 7).  
#  
#  
#  
#FailureMessage Object: 0x7fff325f4130  
==== C stack trace ===============================  
  
/tmp/d8-linux-debug-v8-component-94592/libv8_libbase.so(v8::base::debug::StackTrace::StackTrace()+0x13) [0x7f6eb1b19113]  
/tmp/d8-linux-debug-v8-component-94592/libv8_libplatform.so(+0x190ad) [0x7f6eb1ac20ad]  
/tmp/d8-linux-debug-v8-component-94592/libv8_libbase.so(V8_Fatal(char const*, int, char const*, ...)+0x194) [0x7f6eb1afa224]  
/tmp/d8-linux-debug-v8-component-94592/libv8_libbase.so(+0x2bc45) [0x7f6eb1af9c45]  
/tmp/d8-linux-debug-v8-component-94592/libv8.so(+0x4b5e304) [0x7f6eb0f5e304]  
/tmp/d8-linux-debug-v8-component-94592/libv8.so(v8::internal::compiler::CompileWasmToJSWrapper(v8::internal::Isolate*, v8::internal::wasm::WasmModule const*, v8::internal::Signature<v8::internal::wasm::ValueType> const*, v8::internal::wasm::ImportCallKind, int, v8::internal::wasm::Suspend)+0x33c) [0x7f6eb0f5816c]  
/tmp/d8-linux-debug-v8-component-94592/libv8.so(v8::internal::WasmJSFunction::New(v8::internal::Isolate*, v8::internal::Signature<v8::internal::wasm::ValueType> const*, v8::internal::Handle<v8::internal::JSReceiver>, v8::internal::wasm::Suspend)+0x9a2) [0x7f6eb06158d2]  
/tmp/d8-linux-debug-v8-component-94592/libv8.so(+0x41d579a) [0x7f6eb05d579a]  
/tmp/d8-linux-debug-v8-component-94592/libv8.so(v8::internal::FunctionCallbackArguments::CallOrConstruct(v8::internal::Tagged<v8::internal::FunctionTemplateInfo>, bool)+0x191) [0x7f6eaeb8c841]  
/tmp/d8-linux-debug-v8-component-94592/libv8.so(+0x278ae6c) [0x7f6eaeb8ae6c]  
/tmp/d8-linux-debug-v8-component-94592/libv8.so(+0x2788b84) [0x7f6eaeb88b84]  
/tmp/d8-linux-debug-v8-component-94592/libv8.so(v8::internal::Builtin_HandleApiConstruct(int, unsigned long*, v8::internal::Isolate*)+0x7d) [0x7f6eaeb881ad]  
/tmp/d8-linux-debug-v8-component-94592/libv8.so(+0x1eac77d) [0x7f6eae2ac77d]  
  
```  
  
## Other  
Please note to include the flags `--allow-natives-syntax` for clusterfuzz classification.  
  
VERSION  
Tested on v8 version: 12.5.0 - 12.8.0  
  
REPRODUCTION CASE  
1\. Download debug v8 from: gs://v8-asan/linux-debug/d8-linux-debug-v8-component-94592.zip  
2\. Run: `d8 --allow-natives-syntax poc.js`  
  
FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION  
Type of crash: tab  
  
CREDIT INFORMATION  
Reporter credit: Zhenghang Xiao (@Kipreyyy)   

output_poc.js 

302 B [ View](<https://issues.chromium.org/action/issues/348598133/attachments/57367003?download=false>)[ Download](<https://issues.chromium.org/action/issues/348598133/attachments/57367003?download=true>)


---

**#2 — ki...@gmail.com — Jun 22, 2024 06:47PM**

## Root Cause Analysis

When executing POC, during the execution of `BuildWasmToJSWrapper` by v8, `wasm_count` is equal to 0 [1] and `suspender_count` is equal to 0 [2].

However, when preparing space for the array to store arguments, the calculated value of the variable `pushed_count` is the maximum of `expected_arity` and `wasm_count - suspender_count`, where the former is **0** and the latter results in **-1** , making the final value of pushed_count to be **0.** Therefore, the length of variable `args` is equal to 7. [3]

However, the for loop at [4] starts from **-1** and ends at **0**. This results in an additional parameter being added to the args array. Consequently, when adding the last parameter to the args array at [5], it causes an out-of-bounds write.

```
// For wasm-to-js wrappers, parameter 0 is a WasmApiFunctionRef.
bool BuildWasmToJSWrapper(wasm::ImportCallKind kind, int expected_arity,
                          wasm::Suspend suspend,
                          const wasm::WasmModule* module) {
  int wasm_count = static_cast<int>(sig_->parameter_count()); // <---- [1]
  int suspender_count = suspend == wasm::kSuspendWithSuspender ? 1 : 0; // <--- [2]

  // Build the start and the parameter nodes.
  Start(wasm_count + 3);
  ...

  Node* old_sp = BuildSwitchToTheCentralStackIfNeeded(callable_node);

  Node* undefined_node = UndefinedValue();
  Node* call = nullptr;
  // Clear the ThreadInWasm flag.
  BuildModifyThreadInWasmFlag(false);
  switch (kind) {
    // =======================================================================
    // === JS Functions with matching arity ==================================
    // =======================================================================
    ...
    case wasm::ImportCallKind::kJSFunctionArityMismatch: {
      int pushed_count =
          std::max(expected_arity, wasm_count - suspender_count); // <---- [3]
      base::SmallVector<Node*, 16> args(pushed_count + 7);
      int pos = 0;

      args[pos++] = callable_node;  // target callable.
      // Determine receiver at runtime.
      args[pos++] =
          BuildReceiverNode(callable_node, native_context, undefined_node);

      // Convert wasm numbers to JS values.
      pos = AddArgumentNodes(base::VectorOf(args), pos, wasm_count, sig_,
                             native_context, suspender_count);
      for (int i = wasm_count - suspender_count; i < expected_arity; ++i) { // <---- [4]
        args[pos++] = undefined_node;
      }
      args[pos++] = undefined_node;  // new target
      args[pos++] = Int32Constant(
          JSParameterCount(wasm_count - suspender_count));  // argument count

      Node* function_context =
          gasm_->LoadContextFromJSFunction(callable_node);
      args[pos++] = function_context;
      args[pos++] = effect();
      args[pos++] = control();  // <------- [5]

      auto call_descriptor = Linkage::GetJSCallDescriptor(
          graph()->zone(), false, pushed_count + 1, CallDescriptor::kNoFlags);
      call = gasm_->Call(call_descriptor, pos, args.begin());
      break;
    }
```

To summarize, the issue is that v8 assumes that the WasmFunction being created will include a Suspender as part of its parameters, but it does not specifically check for this. This allows a user to break this assumption by creating a WasmFunction with no function parameters, thereby triggering the vulnerability.

It is important to note that this issue is not limited to the BuildWasmToJSWrapper function; the `WasmJSFunction::New` function also has a similar code pattern [6].

```
Handle<WasmJSFunction> WasmJSFunction::New(Isolate* isolate,
                                           const wasm::FunctionSig* sig,
                                           Handle<JSReceiver> callable,
                                           wasm::Suspend suspend) {
  ...

  // Now set the call_target or code object for calls from Wasm.
  if (WasmExportedFunction::IsWasmExportedFunction(*callable)) {
    Address call_target =
        Cast<WasmExportedFunction>(*callable)->GetWasmCallTarget();
    internal_function->set_call_target(call_target);
  } else if (!wasm::IsJSCompatibleSignature(sig)) {
    internal_function->set_call_target(
        Builtins::EntryOf(Builtin::kWasmToJsWrapperInvalidSig, isolate));
  } else if (UseGenericWasmToJSWrapper(wasm::kDefaultImportCallKind, sig,
                                       suspend)) {
    internal_function->set_call_target(
        Builtins::EntryOf(Builtin::kWasmToJsWrapperAsm, isolate));
  } else {
    int suspender_count = suspend == wasm::kSuspendWithSuspender ? 1 : 0;
    int expected_arity = parameter_count - suspender_count; // <--- [6]
    ... 
```


---

**#3 — ki...@gmail.com — Jun 22, 2024 07:11PM**

## Detailed Bisection

  1. [https://crrev.com/5c02c29097eaedab2bc6b10198fdf780ac8c29d1](<https://crrev.com/5c02c29097eaedab2bc6b10198fdf780ac8c29d1>)

```
commit	5c02c29097eaedab2bc6b10198fdf780ac8c29d1	[log] [tgz]
author	Thibaud Michaud <thibaudm@chromium.org>	Tue Jul 19 14:18:53 2022
committer	V8 LUCI CQ <v8-scoped@luci-project-accounts.iam.gserviceaccount.com>	Tue Jul 19 15:43:31 2022
tree	3e288d4161f396c7c139be5dc02a15a823d87a30
parent	f7a73d8ba86f9feddfd190c66f0850345d44c541 [diff]
[wasm] Drop suspender param in wasm-to-JS wrapper

The suspender is only needed by the wrapper, do not forward it to the JS
import.

R=ahaas@chromium.org

Bug: v8:12191
Change-Id: Id8e9a820491588b40fffb5dfd8706e85a16b8b23
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/3768410
Reviewed-by: Andreas Haas <ahaas@chromium.org>
Commit-Queue: Thibaud Michaud <thibaudm@chromium.org>
Cr-Commit-Position: refs/heads/main@{#81818}
```

  2. [https://crrev.com/5539e74015969a542571c8697134c7f42ff1efa4](<https://crrev.com/5539e74015969a542571c8697134c7f42ff1efa4>)

```
commit	5539e74015969a542571c8697134c7f42ff1efa4	[log] [tgz]
author	Thibaud Michaud <thibaudm@chromium.org>	Wed Feb 21 11:59:20 2024
committer	V8 LUCI CQ <v8-scoped@luci-project-accounts.iam.gserviceaccount.com>	Wed Feb 21 14:02:02 2024
tree	d99c5ac0c91ec68960335a7fab97b7ac8278eea1
parent	393e32fa96a32e35d32d3405f540c9b191ce97a5 [diff]
[wasm][cleanup] Simplify wasm-to-js wrapper

In the wasm-to-js graph builder, the "arity match" branch is just a
special case of the "arity mismatch" branch. Merge the two cases into
one.
In the "arity match" case, we did not use the {expected_arity} argument.
Use it to check that the arity does match in debug mode, which is
required now for correctness, and fix some places where we forgot to
take JSPI into account.

R=ahaas@chromium.org

Change-Id: I430582215f6ccf9a7f3cd52bd83115bdf4504788
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/5309905
Reviewed-by: Andreas Haas <ahaas@chromium.org>
Commit-Queue: Thibaud Michaud <thibaudm@chromium.org>
Cr-Commit-Position: refs/heads/main@{#92449}
```


---

**#4 — cl...@appspot.gserviceaccount.com — Jun 25, 2024 05:45AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5218637785792512](<https://clusterfuzz.com/testcase?key=5218637785792512>).


---

**#5 — ki...@gmail.com — Jun 25, 2024 09:48AM**

I can reproduce this vulnerability on head, @th...@chromium.org I believe you are the owner of this issue, could you take a look?


---

**#6 — am...@chromium.org — Jun 25, 2024 10:37AM**

Thanks for the minimized POC, Zhenghang. I was able to get that to repro pretty quickly in head. I wasn't able to repro this in an older d8 build I had available, so I am not sure I can go by either of the commits in the "detailed bisection"; the original bisect provided is simply enabling JSPI so that can't be used either.


---

**#7 — am...@chromium.org — Jun 25, 2024 10:40AM**

Setting as 128 for now; assigning to thibaudm@ and cc'ing jkummerow@ based on JSPI / wasm-to-js wrappers and stack switching


---

**#8 — cl...@appspot.gserviceaccount.com — Jun 25, 2024 10:41AM**

Detailed Report: [https://clusterfuzz.com/testcase?key=5792063994920960](<https://clusterfuzz.com/testcase?key=5792063994920960>)  
  
Fuzzer: None  
Job Type: linux_asan_d8_dbg  
Platform Id: linux  
  
Crash Type: DCHECK failure  
Crash Address:   
Crash State:  
size() > index in small-vector.h  
v8::internal::compiler::WasmWrapperGraphBuilder::BuildWasmToJSWrapper  
v8::internal::compiler::CompileWasmToJSWrapper  
  
Sanitizer: address (ASAN)  
  
Crash Revision: [https://clusterfuzz.com/revisions?job=linux_asan_d8_dbg&revision=94614](<https://clusterfuzz.com/revisions?job=linux_asan_d8_dbg&revision=94614>)  
  
Reproducer Testcase: [https://clusterfuzz.com/download?testcase_id=5792063994920960](<https://clusterfuzz.com/download?testcase_id=5792063994920960>)  
  
To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.   
  
If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.  
  
If you have any feedback on reproducing test cases, let us know at [https://forms.gle/Yh3qCYFveHj6E5jz5](<https://forms.gle/Yh3qCYFveHj6E5jz5>) so we can improve.


---

**#9 — am...@chromium.org — Jun 25, 2024 10:42AM**

while I was doing all this, I also got clusterfuzz to repro this as well. I'll stop my attempts to bisect this and hopefully CF can come up with the culprit sooner than I would have.


---

**#10 — 24...@project.gserviceaccount.com — Jun 25, 2024 11:08AM**

Automatically applying components based on crash stacktrace and information from OWNERS files.  
  
If this is incorrect, please apply the hotlistid:4801165.


---

**#11 — ki...@gmail.com — Jun 25, 2024 11:43AM**

Hi, I think I can explain to you that previously jspi could not be used directly by v8, but it is available in Chrome through OT.

So, after discovering the vulnerability, through source code analysis, I finally pinpointed the detailed bisect point.

This is indeed a rather unique vulnerability, so the minimized PoC I provided is only applicable to header versions (12.5.0 - 12.8.0), but it actually dates back even earlier.

Note that you need `d8.test.installConditionalFeatures();` to bisect to 12.5, such as:

```
d8.test.enableJSPI();
d8.test.installConditionalFeatures();
```


---

**#12 — th...@chromium.org — Jun 25, 2024 10:45PM**

Thank you for the report,  
It seems that we are indeed missing a signature check when we first create the WebAssembly.Function, to make sure that it is a well-formed JSPI signature before attempting to generate the wrapper graph.  
IIUC this allows overwriting at most 1 element past the end of the arguments array, and only with the Control node [5]? This seems pretty limited, especially since the Control node address is not user-controlled.  
+cffsmith@, could you help me assess if this should be classified as a security issue given the info above?  
In any case, I'll prepare the fix.


---

**#13 — pe...@google.com — Jun 26, 2024 12:37AM**

Setting milestone because of s0/s1 severity.


---

**#14 — pe...@google.com — Jun 26, 2024 12:38AM**

This is a serious security regression. If you are not able to fix this quickly, please revert the change that introduced it.

If this doesn't affect a release branch, or has not been properly classified for severity, please update the Security Impact hotlist or the Severity field, and remove the ReleaseBlock hotlist.


---

**#15 — ki...@gmail.com — Jun 27, 2024 09:56AM**

hello, any update? :)


---

**#16 — ap...@google.com — Jun 27, 2024 06:05PM**

Project: v8/v8  
Branch: main  
  
commit 53d1ddc4ff30d73d15b0b2c1cfe7da04b1a4f906  
Author: Thibaud Michaud <[thibaudm@chromium.org](<mailto:thibaudm@chromium.org>)>  
Date: Thu Jun 27 09:13:34 2024  
  
[wasm][jspi] Add missing type check for suspending WebAssembly.Function  
  
R=[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)  
  
Fixed: 348598133  
Change-Id: I130d504f38e5f76b7b73362e3f311184cfd84a16  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5662577](<https://chromium-review.googlesource.com/c/v8/v8/+/5662577>)  
Reviewed-by: Jakob Kummerow <[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)>  
Commit-Queue: Thibaud Michaud <[thibaudm@chromium.org](<mailto:thibaudm@chromium.org>)>  
Cr-Commit-Position: refs/heads/main@{#94673}  
  
M src/wasm/wasm-js.cc  
  
[https://chromium-review.googlesource.com/5662577](<https://chromium-review.googlesource.com/5662577>)


---

**#17 — sp...@google.com — Jul 4, 2024 06:55AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $11000.00 for this report.  
  
Rationale for this decision:  
$10,000 for high quality report of memory corruption in a sandboxed process + $1,000 bisect bonus  
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#18 — am...@chromium.org — Jul 4, 2024 07:11AM**

Congratulations Zhenghang and nice work! Thank you for your efforts and reporting this issue to us.


---

**#19 — pe...@google.com — Jul 25, 2024 12:45AM**

This is sufficiently serious that it should be merged to dev. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M128. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately. **Merge approved:** your change passed merge requirements and is auto-approved for M128. Please go ahead and merge the CL to branch 6613 (refs/branch-heads/6613) manually. Please contact milestone owner if you have questions. Merge instructions: [https://chromium.googlesource.com/chromium/src.git/+/refs/heads/main/docs/process/merge_request.md](<https://chromium.googlesource.com/chromium/src.git/+/refs/heads/main/docs/process/merge_request.md>) Owners: harrysouders (Android), harrysouders (iOS), obenedict (ChromeOS), pbommana (Desktop) Thank you for fixing this security bug! We aim to ship security fixes as quickly as possible, to limit their opportunity for exploitation as an "n-day" (that is, a bug where git fixes are developed into attacks before those fixes reach users).

We have determined this fix is necessary on milestone(s): [128].

Please answer the following questions so that we can safely process this merge request:

  1. Which CLs should be backmerged? (Please include Gerrit links.)
  2. Has this fix been verified on Canary to not pose any stability regressions?
  3. Does this fix pose any potential non-verifiable stability risks?
  4. Does this fix pose any known compatibility risks?
  5. Does it require manual verification by the test team? If so, please describe required testing.


---

**#20 — pe...@google.com — Jul 30, 2024 12:37AM**

This issue has been approved for a merge. Please merge the fix to any appropriate branches as soon as possible!

If all merges have been completed, please remove any remaining Merge-Approved labels from this issue.

Thanks for your time! To disable nags, add Disable-Nags (case sensitive) to the Chromium Labels custom field.


---

**#21 — pb...@google.com — Jul 30, 2024 05:59AM**

[Bulk Update] Please get your approve CL merged to M128 branch asap, All the changes which are merged on or before 2PM PST tomorrow i.e., 07/30/2024 will be part of this weeks Beta release. We recommend to get the CL's merged sooner so that they can get much bake time in Beta please. Thank you.


---

**#22 — jk...@chromium.org — Jul 30, 2024 07:09PM**

#19: Go home, bot, you're drunk. The fix (#16) has landed long before the 128 branch point, no backmerge necessary.


---

**#23 — pe...@google.com — Oct 5, 2024 12:41AM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
