# Crash [@ ??] on UD2 with WebAssembly

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1895123
Component: JavaScript: WebAssembly
Bounty: (unknown)
Date: 2024-05-05T09:27:04Z
Keywords: crash, csectype-uaf, pernosco, regression, sec-high, testcase

The attached testcase crashes on mozilla-central revision 20240430-b7a1a8a3af7f (build with opt, run with --fuzzing-safe --cpu-count=2 --ion-offthread-compile=off). 

Backtrace:

```
    received signal SIGILL, Illegal instruction.
    [Switching to Thread 0x7ffff47ff700 (LWP 2297)]
    0x00001f7ec1980032 in ?? ()
    #0  0x00001f7ec1980032 in ?? ()
    [...]
    #11 0x00001f7ec19b23ba in ?? ()
    #12 0x0000000000000000 in ?? ()
    rax	0x7ffff47fd998	140737295407512
    rbx	0x3fc9bc62d2e0	70135681569504
    rcx	0x7ff8000000000000	9221120237041090560
    rdx	0xfff9800000000000	-1829587348619264
    rsi	0x0	0
    rdi	0x2904ff000020	45101434798112
    rbp	0x7ffff47fd820	140737295407136
    rsp	0x7ffff47fd800	140737295407104
    r8	0x66333333	1714631475
    r9	0x0	0
    r10	0x7ffff3e24c00	140737285082112
    r11	0x0	0
    r12	0x7ffff3ea3800	140737285601280
    r13	0x0	0
    r14	0x7ffff367eda0	140737277062560
    r15	0x0	0
    rip	0x1f7ec1980032	34629274304562
    => 0x1f7ec1980032:	ud2    
       0x1f7ec1980034:	mov    %r14,0x18(%rsp)
```


Note that this test is quite sensitive to reduction, even to whitespace/name lengths in some places.

---

**Comment 1 — choller@mozilla.com — 2024-05-05T09:27:08Z**

Created attachment 9400159
Detailed Crash Information

---

**Comment 2 — choller@mozilla.com — 2024-05-05T09:27:10Z**

Created attachment 9400160
Testcase

---

**Comment 3 — jdemooij@mozilla.com — 2024-05-06T06:15:28Z**

Maybe the same issue as bug 1893915?

---

**Comment 4 — bvisness@mozilla.com — 2024-05-08T14:27:34Z**

I've been looking into this over the last couple days in this [pernosco session](https://pernos.co/debug/mx59HSFnETYw3zpD3a5_yg/index.html#f%7Bm%5Blvk,9w_,t%5BCA,AQWI_,f%7Be%5BDW0,G3w_,s%7BaYDEONEAA,bBQ,uBOkymQ,oBO1ifw___,v%5B%7BwbuA,v%5B%7Bf'container',q'stack',p%7B_,xAYag_,%7Bf'list',q'join',p%7B'subqueries'%5B%7B'query''alerts','request'%7B__,%7B'query''signals','request'%7B____,xk3w_,%7Bf'notebook',q'notebook',p.,xAnnD___,%7Bwq9w,v%5B%7Bf'source',q'source',p%7B_,xAYag_,%7Bf'list',q'instructions',p%7B_,xAYag___,%7Bwa+I,v%5B%7Bf'container',q'registers',p%7B_,xAYag_,%7Bf'list',q'watchpoint',p%7B'address''0x289d7633a79d','type''uint8_t'_,xAYag____/). It seems to be a GC barrier issue somewhere in the soup of wasm trap handling. I'm not 100% sure of a fix yet but will keep chipping away at it.

It is not related to bug 1893915.

---

**Comment 5 — dveditz@mozilla.com — 2024-05-08T21:50:02Z**

How is the crashing stack being generated? Frame #12 at address 0x0000000000 seems unlikely to be able to call anything -- and there are other frames that look like that. Is the program so corrupt the stack is trashed, or is the tool broken?

sec-high if this is real

---

**Comment 6 — bvisness@mozilla.com — 2024-05-10T21:06:52Z**

Still haven't really gotten to the bottom of this one, but at least we have a clearer picture of the critical events:

1. We attempt to nursery-allocate a WasmValueBox for an externref param or something
2. We run out of nursery space, so we trigger a minor GC
3. The minor GC succeeds but also schedules an interrupt for a major GC (this looks like a stack overflow but it is fake)
4. We retry and successfully nursery-allocate the WasmValueBox and initialize it, giving it a Shape pointer in the tenured heap
5. We go back into jit code somewhere and hit the interrupt, and run a major GC WITHOUT running another minor GC
6. The WasmValueBox's Shape gets collected from the tenured heap, filling the space with `0x4b` (this should not happen)
7. Later, in some jit exit, we try loading the class pointer from the WasmValueBox and blow up

([updated pernosco link](https://pernos.co/debug/mx59HSFnETYw3zpD3a5_yg/index.html#f{m[DWM,DATi_,t[CA,AQWI_,f{e[DWM,C/6s_,s{aYDEONEAA,bBQ,uBwHehw,oBwPAyw___,v[{wbuA,v[{f'container',q'stack',p{_,xgjU_,{f'list',q'join',p{'subqueries'[{'query''alerts','request'{__,{'query''signals','request'{____,xMSk_,{f'notebook',q'notebook',p.,xAUe7___,{wn3w,v[{f'source',q'source',p{_,xw1A_,{f'list',q'instructions',p{_,xw1A___,{weEI,v[{f'container',q'registers',p{_,xw1A_,{f'list',q'watchpoint',p{'address''0x286768734600','type''js:3A%3AShape*'_,xw1A_,{f'list',q'watchpoint',p{'address''0xa50ae00020','type''WasmValueBox*'_,xAYag____/))

I have no answer yet for the null frames above. But as in other issues, the SIGILL itself is a red herring. In this case, it's the mechanism by which we perform the interrupt for the major GC. The ensuing SIGSEGV after (successfully?) handling the SIGILL is the real problem.

Overall, it seems that the WasmValueBox's Shape is being collected from the tenured heap when it should not be. (`0x4b` is the swept tenured pattern.) However, it's not clear what would _ever_ trace the Shape, since it's held alive by a nursery->tenured edge, and we might not be tracing nursery items at all here.

Generally it seems odd that we perform a minor GC, write a bit into the nursery, and then perform a major GC without another minor GC (which would presumably move the newly-allocated WasmValueBox). But none of this really seems wasm-specific to me, so I don't understand why this wouldn't happen all the time on these retry-in-the-nursery allocations. This is all happening on a worker, and Iain tells me that we don't run incremental GC on workers, so maybe it's somehow related to that and therefore just a much more rare event?

---

**Comment 7 — iireland@mozilla.com — 2024-05-13T15:39:33Z**

Update: I kept looking at the pernosco recording after Ben posted the above comment. Step 5 is incorrect. We do trigger a minor GC before running the major GC; we just weren't looking for it in the right place.

To the best of my current understanding, the real problem is as follows:

1. From JS, we call an import stub with `undefined` as the value for an AnyRef parameter.
2. We call AnyRef::boxValue in the OOL path for WasmAnyRefFromJSValue. 
3. The nursery is full. We trigger a minor collection and request a major GC via interrupt.
4. We allocate a WasmValueBox at the very beginning of the now-empty nursery, and return it.
5. We pass the fresh WasmValueBox in a register to the import stub.
6. We enter the prologue generated [here](https://searchfox.org/mozilla-central/rev/ee2ad260c25310a9fbf96031de05bbc0e94394cc/js/src/wasm/WasmStubs.cpp#1881-1889). In `wasmReserveStackChecked`, we generate an interrupt check.
7. The interrupt fires and runs a major GC, which triggers a minor GC during the preparation phase.
8. During the minor GC, we don't trace the register holding the fresh WasmValueBox. We don't tenure it.
9. Because it's allocated at the very beginning of the nursery, we [also don't poison it](https://searchfox.org/mozilla-central/rev/ee2ad260c25310a9fbf96031de05bbc0e94394cc/js/src/gc/Nursery.cpp#1937-1944).
10. During the major GC, we collect and poison the Shape of the WasmValueBox.
11. We return and try to use the WasmValueBox. The shape pointer has not been overwritten, but the contents of the Shape are poisoned, so that's where we crash.

To fix this I think we either need to trace the import stub's arguments, or avoid triggering a GC at that point.

---

**Comment 8 — ydelendik@mozilla.com — 2024-05-13T17:30:37Z**

Created attachment 9401483
reduced test case

Smaller test case that exposes (?) the same issue

---

**Comment 9 — jcoppeard@mozilla.com — 2024-05-14T08:37:26Z**

(In reply to Iain Ireland [:iain] from comment #7)
> 8. During the minor GC, we don't trace the register holding the fresh WasmValueBox. We don't tenure it.

This sounds like the problem here.

> 9. Because it's allocated at the very beginning of the nursery, we also don't poison it.

That shouldn't be the case. I'll look into it.

---

**Comment 10 — jcoppeard@mozilla.com — 2024-05-14T09:14:12Z**

(In reply to Jon Coppeard (:jonco) from comment #9)
Poisoning is not happening because it's not a debug build:

https://searchfox.org/mozilla-central/source/js/src/util/Utility.cpp#96-102

The first chunk is (optionally) poisoned in Nursery::collect here:

https://searchfox.org/mozilla-central/rev/ee2ad260c25310a9fbf96031de05bbc0e94394cc/js/src/gc/Nursery.cpp#1292

---

**Comment 11 — ydelendik@mozilla.com — 2024-05-14T15:56:10Z**

Created attachment 9401692
wip1895123-1.diff

I think we can narrow everything to the following:

- GenerateImportFunction generates prologue with wasmReserveStackChecked, which calls GC
- GenerateImportFunction has stack arguments (see line 1911, after wasmReserveStackChecked) that are non-tracked by GC

Normal wasm function is using CreateStackMapForFunctionEntryTrap, which creates stack maps for wasm function's wasmReserveStackChecked, but imports are not doing it. WIP adds that to the import function -- I'm just not clear if trapexit == wasmReserveStackChecked here and if frame layout is the same.

---

**Comment 12 — ydelendik@mozilla.com — 2024-05-15T16:04:05Z**

Created attachment 9401970
Bug 1895123 - Create stack map in wasm import stub if needed. r?jandem

---

**Comment 13 — ydelendik@mozilla.com — 2024-05-15T16:04:17Z**

Created attachment 9401971
Bug 1895123 - Add wasm import stub tests. r?bvisness



Depends on D210515

---

**Comment 14 — ydelendik@mozilla.com — 2024-05-15T16:11:59Z**

The provided fix addresses the smaller test I created. I was not able to reproduce the issue using OP test, but based of pernosco analysis they expose the same problem. The object is collected or moved -- making it UAF in some sense.

---

**Comment 15 — bvisness@mozilla.com — 2024-05-20T15:56:42Z**

Handing this one off to Yury since he is the one who actually put the patches together.

---

**Comment 16 — ydelendik@mozilla.com — 2024-05-22T13:07:42Z**

Comment on attachment 9401970
Bug 1895123 - Create stack map in wasm import stub if needed. r?jandem

### Security Approval Request
* **How easily could an exploit be constructed based on the patch?**: UAF. GC timing is critical here, it is hard to coordinate the moment via code execution timeout to end up in the affected code.
* **Do comments in the patch, the check-in comment, or tests included in the patch paint a bulls-eye on the security problem?**: Unknown
* **Which branches (beta, release, and/or ESR) are affected by this flaw, and do the release status flags reflect this affected/unaffected state correctly?**: 
* **If not all supported branches, which bug introduced the flaw?**: None
* **Do you have backports for the affected branches?**: No
* **If not, how different, hard to create, and risky will they be?**: It can be possible to apply current patch without modifications.
* **How likely is this patch to cause regressions; how much testing does it need?**: 
* **Is the patch ready to land after security approval is given?**: Yes
* **Is Android affected?**: Yes

---

**Comment 17 — tom@mozilla.com — 2024-05-22T14:29:40Z**

Comment on attachment 9401970
Bug 1895123 - Create stack map in wasm import stub if needed. r?jandem

Approved to land and uplift

---

**Comment 18 — pulsebot@bmo.tld — 2024-05-22T15:20:35Z**

Pushed by ydelendik@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/e63c05c12274
Create stack map in wasm import stub if needed. r=jandem,rhunt

---

**Comment 19 — aryx.bugmail@gmx-topmail.de — 2024-05-22T22:00:26Z**

https://hg.mozilla.org/mozilla-central/rev/e63c05c12274

---

**Comment 20 — release-mgmt-account-bot@mozilla.tld — 2024-05-23T12:01:47Z**

The patch landed in nightly and beta is affected.
:yury, is this bug important enough to require an uplift?
- If yes, please nominate the patch for beta approval.
- If no, please set `status-firefox127` to `wontfix`.

For more information, please visit [BugBot documentation](https://wiki.mozilla.org/BugBot#uplift_beta.py).

---

**Comment 21 — ydelendik@mozilla.com — 2024-05-23T13:46:12Z**

Comment on attachment 9401970
Bug 1895123 - Create stack map in wasm import stub if needed. r?jandem

### Beta/Release Uplift Approval Request
* **User impact if declined**: Some wasm programs can crash intermittently
* **Is this code covered by automated tests?**: Yes
* **Has the fix been verified in Nightly?**: Yes
* **Needs manual test from QE?**: No
* **If yes, steps to reproduce**: 
* **List of other uplifts needed**: None
* **Risk to taking this patch**: Low
* **Why is the change risky/not risky? (and alternatives if risky)**: affects wasm programs with with GC references
* **String changes made/needed**: 
* **Is Android affected?**: Yes

---

**Comment 22 — pascalc@gmail.com — 2024-05-23T13:56:47Z**

Comment on attachment 9401970
Bug 1895123 - Create stack map in wasm import stub if needed. r?jandem

Approved for 127 beta 6, thanks.

---

**Comment 23 — pulsebot@bmo.tld — 2024-05-23T14:00:03Z**

https://hg.mozilla.org/releases/mozilla-beta/rev/2c178aabc503

---

**Comment 24 — ryanvm@gmail.com — 2024-05-23T18:31:34Z**

(In reply to Yury Delendik (:yury) from comment #16)
> * **Which branches (beta, release, and/or ESR) are affected by this flaw, and do the release status flags reflect this affected/unaffected state correctly?**: 

Not sure why this was left blank. Is ESR impacted also?

---

**Comment 25 — ydelendik@mozilla.com — 2024-05-23T18:45:07Z**

(In reply to Ryan VanderMeulen [:RyanVM] from comment #24)
> (In reply to Yury Delendik (:yury) from comment #16)
> > * **Which branches (beta, release, and/or ESR) are affected by this flaw, and do the release status flags reflect this affected/unaffected state correctly?**: 
> 
> Not sure why this was left blank. Is ESR impacted also?

 GenerateImportFunction is an old piece of code. Stack maps were added later. ESRs are impacted.

---

**Comment 26 — ryanvm@gmail.com — 2024-05-24T18:37:58Z**

Comment on attachment 9401970
Bug 1895123 - Create stack map in wasm import stub if needed. r?jandem

Approved for 115.12esr.

---

**Comment 27 — pulsebot@bmo.tld — 2024-05-24T18:39:37Z**

https://hg.mozilla.org/releases/mozilla-esr115/rev/953871d57b9c

---

**Comment 28 — release-mgmt-account-bot@mozilla.tld — 2024-07-23T12:00:35Z**

2 months ago, tjr placed a reminder on the bug using the whiteboard tag `[reminder-test 2024-07-23]` .

yury, please refer to the original comment to better understand the reason for the reminder.

---

**Comment 29 — pulsebot@bmo.tld — 2024-07-25T22:26:59Z**

Pushed by ydelendik@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/f80c5cfc1bb6
Add wasm import stub tests. r=bvisness

---

**Comment 30 — ryanvm@gmail.com — 2024-07-26T04:04:56Z**

https://hg.mozilla.org/mozilla-central/rev/f80c5cfc1bb6

---

**Comment 31 — bugmon@mozilla.com — 2025-03-06T08:31:21Z**

Verified bug as fixed on rev mozilla-central 20240726035627-69a2460cfcb3.
Removing bugmon keyword as no further action possible.  Please review the bug and re-add the keyword for further analysis.
