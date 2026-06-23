# V8 Sandbox Bypass: OOB write in FastJsonStringifier

Issue URL: https://issues.chromium.org/issues/442412895
VRP-Reward: DUP
Date: Sep 2, 2025 03:16AM


* * *

### Report description

V8 Sandbox Bypass: OOB write in FastJsonStringifier

* * *

### Bug location

#### Where do you want to report your vulnerability?

Chrome VRP – Report security issues affecting the Chrome browser. [See program rules](<https://bughunters.google.com/about/rules/5745167867576320/chrome-vulnerability-reward-program-rules>)

* * *

### The problem

#### Please describe the technical details of the vulnerability

The string's length can be corrupted, leading to the OOB write access in [1].

[1] [https://source.chromium.org/chromium/chromium/src/+/main:v8/src/json/json-stringifier.cc;l=3422-3429;drc=24ab048e0cdc0ce94ae004408ff5b838298cd3de](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/json/json-stringifier.cc;l=3422-3429;drc=24ab048e0cdc0ce94ae004408ff5b838298cd3de>)

#### Impact analysis – Please briefly explain who can exploit the vulnerability, and what they gain when doing so

V8 Sandbox Bypass

* * *

### The cause

#### What version of Chrome have you found the security issue in?

v8 14.1.136

#### Is the security issue related to a crash?

Yes, it is related to a crash.

#### Choose the type of vulnerability

Sandbox Escape


---

**#2 — he...@gmail.com — Sep 2, 2025 03:18AM**

This is a re-submit of my original report 442068023, since I'm not sure submitting in the stale security template is still works/visible. (I didn't get reply more than 2 weeks for the last two report). Feel free to let me know whether the original security template (i.e., [https://issuetracker.google.com/issues/new?component=1363614&template=1922342](<https://issuetracker.google.com/issues/new?component=1363614&template=1922342>)) still works. Thank you.


---

**#3 — el...@chromium.org — Sep 3, 2025 02:42AM**

Thanks for the report - the old issue should be just fine, but I'll mark it as a duplicate of this one.  
  
However, this doesn't repro for me. I built d8 with these args:  
  
```  
is_debug=false  
is_asan=true  
v8_enable_sandbox=true  
v8_enable_memory_corruption_api=true  
dcheck_always_on=false  
target_cpu="x64"  
```  
  
then ran it:  
```  
out/rel/d8 --omit-quit --fuzzing --jit-fuzzing --sandbox-fuzzing --js-staging /tmp/442068023.js  
```  
  
and I did not get an asan failure at all; instead I got this:  
```  
Sandbox testing mode is enabled. Only sandbox violations will be reported, all other crashes will be ignored.  
Sandbox bounds: [0x7a5d00000000,0x7b5d00000000)  
  
  
#  
# Safely terminating process due to error in , line 0  
# The following harmless error was encountered: Check failed: CheckTag(content, tag_range).  
#  
#  
#  
#FailureMessage Object: 0x7b9e3ad08860  
==== C stack trace ===============================  
  
out/rel/d8(__interceptor_backtrace+0x46) [0x5587a2f3b8a6]  
out/rel/d8(+0x5e41e43) [0x5587a7a7be43]  
out/rel/d8(+0x5e3ffba) [0x5587a7a79fba]  
out/rel/d8(+0x5e2145e) [0x5587a7a5b45e]  
out/rel/d8(+0x2179f8f) [0x5587a3db3f8f]  
out/rel/d8(+0x214981c) [0x5587a3d8381c]  
out/rel/d8(+0x2129a64) [0x5587a3d63a64]  
out/rel/d8(+0x1852399) [0x5587a348c399]  
out/rel/d8(+0x5c70d36) [0x5587a78aad36]  
```  
  
Have I missed something here?  
  
+cc pthier@ as well.


---

**#4 — th...@chromium.org — Sep 6, 2025 01:35AM**

[security shepherd]  
Triaging this as a V8 sandbox bypass:  
\- Set a provisional severity of Medium (S2).  
\- Set a provisional priority of P1.  
\- Assign to the current V8 Shepherd.  
\- Apply the Security_Impact-None hotlist (hotlistID:5433277).  
\- If possible, please also apply the V8 Sandbox hotlist (hotlistID:4802478).


---

**#5 — he...@gmail.com — Sep 6, 2025 04:35PM**

I'm not sure why you just get the CheckTag failure. I use the d8 on the commit d2f6aa053ff5e5f722acca9244adefabd055d430 and can stably reproduce the ASAN stack. Perhaps it might be the offset needed to be adjusted on your version.


---

**#6 — pe...@google.com — Sep 6, 2025 04:41PM**

Thank you for providing more feedback. Adding the requester to the CC list.


---

**#7 — pa...@google.com — Sep 8, 2025 09:26PM**

I was not able to reproduce the bug. Just like ellyjones@ I got the `Check failed: CheckTag(content, tag_range)` error instead.

I built d8 on commit `d2f6aa053ff5e5f722acca9244adefabd055d430` with args

```
is_debug=false
is_asan=true
v8_enable_sandbox=true
v8_enable_memory_corruption_api=true
dcheck_always_on=false
target_cpu="x64"
```

```
# d8 --omit-quit --fuzzing --jit-fuzzing --sandbox-fuzzing --js-staging poc.js

Sandbox testing mode is enabled. Only sandbox violations will be reported, all other crashes will be ignored.
Sandbox bounds: [0x7a7300000000,0x7b7300000000)

#
# Safely terminating process due to error in , line 0
# The following harmless error was encountered: Check failed: CheckTag(content, tag_range).
#
#
#
#FailureMessage Object: 0x7bb4b6508860
==== C stack trace ===============================

    ./out/sb_oob_442412895/d8(__interceptor_backtrace+0x46) [0x55de0787f8a6]
    ./out/sb_oob_442412895/d8(+0x5e1ee43) [0x55de0c36ae43]
    ./out/sb_oob_442412895/d8(+0x5e1cfba) [0x55de0c368fba]
    ./out/sb_oob_442412895/d8(+0x5dfe45e) [0x55de0c34a45e]
    ./out/sb_oob_442412895/d8(+0x21a3f0f) [0x55de086eff0f]
    ./out/sb_oob_442412895/d8(+0x217379c) [0x55de086bf79c]
    ./out/sb_oob_442412895/d8(+0x21539e4) [0x55de0869f9e4]
    ./out/sb_oob_442412895/d8(+0x1881949) [0x55de07dcd949]
    ./out/sb_oob_442412895/d8(+0x5c4d7f6) [0x55de0c1997f6]
```

I tried changing the offset (`+16 & +1` and other combinations instead of `+16 & +0`), I managed to get `Caught harmless memory access violation (inside sandbox address space). Exiting process...`.

Could you help me with that? Any suggestions I could try?

How did you build and run d8 to produce the error?


---

**#8 — he...@gmail.com — Sep 10, 2025 12:17AM**

Hi, I found that we need to add `v8_fuzzilli=true` in the [args.gn](<http://args.gn>) to better reproduce it. Hence the `[args.gn](<http://args.gn>)` against the commit d2f6aa053ff5e5f722acca9244adefabd055d430 is as follows:  
  
```  
is_debug=false  
is_asan=true  
v8_enable_sandbox=true  
v8_enable_memory_corruption_api=true  
dcheck_always_on=false  
v8_fuzzilli=true  
```  
  
You could try it to see whether it works.


---

**#9 — pt...@chromium.org — Sep 10, 2025 06:13PM**

I was able to repro with the provided build arguments. The reason this was not reproducible without `v8_fuzzili=true`: The repro overwrites 2 bytes of the map with an "arbitrary" constant. Only in this very specific build configuration the map word then points to some "valid" memory inside the sandbox (not a valid map).

The data at that memory location in this particular build makes as interpret the object as `EXTERNAL_INTERNALIZED_TWO_BYTE_STRING`, as this is the value at the location we load the `instance_type` from. In addition the `ExternalPointer` to the external string resource is manipulated to be a valid field in the EPT (External Pointer Table) containing an external string resource.

This then leads to an OOB **read** , which is a known (low priority) issue for external strings.


---

**#10 — ch...@google.com — Jan 8, 2026 09:41PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.


---

**#11 — ch...@google.com — Jan 8, 2026 09:42PM**

This V8 bug has been marked as either a release blocker or a vulnerability bug. V8 bugs affect all OSs supported by Chrome, so the OS field has been updated to reflect this. Please update the bug with the correct OS field if it only affects a subset of OSes.
