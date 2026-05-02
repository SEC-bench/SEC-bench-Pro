# V8 Sandbox Bypass: control-flow hijacking via WASM Table Indirect call

Issue URL: https://issues.chromium.org/issues/343407073
VRP-Reward: 5000
Date: May 30, 2024 01:52AM


# VULNERABILITY DETAILS

Hi V8 team - we noticed that the patch related to the fix of our V8 Sandbox Escape technique demonstrated at Pwn2Own Vancouver 2024 was not sufficient to fully fix the issue.

The patch: [https://chromium-review.googlesource.com/c/v8/v8/+/5401857](<https://chromium-review.googlesource.com/c/v8/v8/+/5401857>)

Our Pwn2Own umbrella ticket: <https://issues.chromium.org/issues/330759707>

**Quick description of the technique** : WebAssembly (WASM) modules confusion and dispatch table call target manipulation leads to control-flow hijacking inside the WASM RWX memory region. Internally, WASM export functions have a function index which is used to compute their call target stored in the internal dispatch table when they are set in a WASM Table. The main idea of this technique is to manipulate the function index of a WASM export function, which is stored inside the V8 sandbox, and confuse two WASM modules to avoid out-of-bounds failures, then thanks to that we can manipulate the call target stored in the dispatch table when the export function is set into a WASM Table. When this export function is called indirectly (via the dispatch table), we can hijack the execution flow as we control the call target.

**The detailed write-up of the V8 Sandbox Escape technique can be found in the`v8_sandbox_escape_writeup.pdf` file attached.**

## VERSION

V8 Version: `12.5.227.9`

V8 Commit: `8c46911f080ea752530fb12b4c796e86f9884554`

## REPRODUCTION CASE

V8 was built with `v8_enable_memory_corruption_api = true` via `tools/dev/gm.py x64.release`.

To reproduce, please run the `poc_release.js` file on the proper V8 version as follows:

```
./d8  --sandbox-testing poc_release.js
```

It should grant you a shell as demonstrated in the `v8_sandbox_escape.mov` video.

The other attached files are only intended to help you understand how the technique works.

## CREDIT INFORMATION

Reporter credit: Edouard Bochin (@le_douds) and Tao Yan (@Ga1ois) of Palo Alto Networks


---

**#2 — ed...@gmail.com — May 30, 2024 02:36AM**

As mentioned in the [Pwn2Own umbrella issue](<https://issues.chromium.org/issues/330759707#comment24>), we will be presenting the research we demonstrated at Pwn2Own 2024 at Black Hat USA 2024 (August 7-8, 2024). So, as with the Pwn2Own umbrella issue and its child issues, we'd like to embargo this issue once the fix has been made, and disclose it publicly after our presentation.


---

**#3 — am...@chromium.org — May 30, 2024 04:22AM**

Thanks for this report. I'm going to go ahead and pass this over to saelo@ since this is a V8 sandbox bypass.

sev-low and SI-None since the V8 sandbox is not considered a security boundary at this time

embargo and next action date of 9 August based on request in c#2


---

**#4 — sa...@chromium.org — May 30, 2024 06:16PM**

Great, thanks for this report! Amazing writeup! There is a broader effort currently underway to properly sandboxify the Wasm function call machinery, which is not fully sandbox compatible yet. So I'll set this as child bug of the umbrella bug.

Jakob, could you take a look at this report? I know you had already done some refactoring to prevent "Module desynchronization" in other places.


---

**#5 — cl...@appspot.gserviceaccount.com — May 30, 2024 10:22PM**

Detailed Report: [https://clusterfuzz.com/testcase?key=6001763923460096](<https://clusterfuzz.com/testcase?key=6001763923460096>)  
  
Fuzzer: None  
Job Type: linux_d8_sandbox_testing  
Platform Id: linux  
  
Crash Type: V8 sandbox violation  
Crash Address:   
Crash State:  
NULL  
Sanitizer: address (ASAN)  
  
Crash Revision: [https://clusterfuzz.com/revisions?job=linux_d8_sandbox_testing&revision=93350](<https://clusterfuzz.com/revisions?job=linux_d8_sandbox_testing&revision=93350>)  
Fixed: [https://clusterfuzz.com/revisions?job=linux_d8_sandbox_testing&range=93632:93633](<https://clusterfuzz.com/revisions?job=linux_d8_sandbox_testing&range=93632:93633>)  
  
Reproducer Testcase: [https://clusterfuzz.com/download?testcase_id=6001763923460096](<https://clusterfuzz.com/download?testcase_id=6001763923460096>)  
  
To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.   
  
If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.  
  
If you have any feedback on reproducing test cases, let us know at [https://forms.gle/Yh3qCYFveHj6E5jz5](<https://forms.gle/Yh3qCYFveHj6E5jz5>) so we can improve.


---

**#6 — 24...@project.gserviceaccount.com — May 30, 2024 10:25PM**

ClusterFuzz testcase 6001763923460096 is verified as fixed in [https://clusterfuzz.com/revisions?job=linux_d8_sandbox_testing&range=93632:93633](<https://clusterfuzz.com/revisions?job=linux_d8_sandbox_testing&range=93632:93633>)  
  
If this is incorrect, please add the hotlistid:5432646 and re-open the issue.


---

**#7 — sa...@chromium.org — May 30, 2024 10:27PM**

I rewrote the reproducer a bit to make it pass our v8 sandbox bypass criteria (crash on a write or exec on the target page). Basically, it now simply does a `jmp rax` in the shellcode, and rax happens to be the first parameter, which is now an i64 containing the address of the `Sandbox.targetPage`. I've attached the new testcase and uploaded it to Clusterfuzz. According to Clusterfuzz, the crash no longer reproduces after [https://chromium.googlesource.com/v8/v8/+/cf9373a0d6760146534b096cee60675a3ea09ad7](<https://chromium.googlesource.com/v8/v8/+/cf9373a0d6760146534b096cee60675a3ea09ad7>) "[wasm][sandbox] Make WasmFunctionData trusted". I guess that makes sense, since this testcase directly corrupts a WasmFunctionData object. However, I'm not sure if the same can be achieved by for example swapping one valid WasmFunctionData for another from a different Module. But maybe then the Module references cannot be desynchronized?


---

**#8 — sa...@chromium.org — May 30, 2024 10:28PM**

Setting state to Assigned again for Jakob to take a look. Please mark as Fixed if this is indeed fixed by the identified change. Thanks!


---

**#9 — jk...@chromium.org — Jun 12, 2024 09:21PM**

It makes sense that the specific approach is fixed by that CL. However, I think `WasmTableObject` is still vulnerable in other ways; I'll take a closer look now.


---

**#10 — sp...@google.com — Jul 18, 2024 07:57AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $5000.00 for this report.  
  
Rationale for this decision:  
v8 heap sandbox bypass reward  
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#11 — am...@chromium.org — Jul 18, 2024 08:23AM**

Congratulations Edouard and Tao! Thank you for digging into the V8 heap sandbox and reporting this bypass to us -- nice work!


---

**#12 — pe...@google.com — Aug 10, 2024 12:43AM**

The NextAction date has arrived: 2024-08-09 To opt-out from this automation rule, please add Optout-Blintz-Nextaction-Alert to the "Chromium Labels" custom field.


---

**#13 — am...@chromium.org — Aug 13, 2024 03:01AM**

opening this up for public disclosure post Black Hat Thanks for presenting your research at Black Hat -- it was a very good presentation and I enjoyed meeting you both, albeit briefly before we were kicked out of South Seas :) !


---

**#14 — ed...@gmail.com — Aug 14, 2024 01:54AM**

Thank you Amy ! It was nice meeting in-person :)
