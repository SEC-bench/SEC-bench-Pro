# Crash [@ ??] with WebAssembly and gczeal

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1854068
Component: JavaScript: WebAssembly
Bounty: (unknown)
Date: 2023-09-20T08:01:38Z
Keywords: crash, regression, sec-high, testcase

The following testcase crashes on mozilla-central revision 20230920-f90822eea608 (debug build, run with --fuzzing-safe --cpu-count=2 --ion-offthread-compile=off --ion-warmup-threshold=10 --baseline-eager):

    gczeal(19, 1);
    function wasmEvalText(str, imports) {
      let binary = wasmTextToBinary(str);
      try {
        m = new WebAssembly.Module(binary);
      } catch(e) {}
      return new WebAssembly.Instance(m, imports);
    }
    let WasmNonAnyrefValues = [];
    let {ifNull} = wasmEvalText(`(module
      (func (export "ifNull") (param externref externref) (result externref)
        local.get 0
      )
    )`).exports;
    evaluate(`
      for (let i = 0; i < 10; ++i)
        ifNull(()=>{}) 
    `);


Backtrace:

    received signal SIGSEGV, Segmentation fault.
    #0  0x000012e4e25dc5ba in ?? ()
    #1  0x00007ffff3898180 in ?? ()
    #2  0xfff9800000000000 in ?? ()
    #3  0x0000000000000008 in ?? ()
    #4  0x00007fffffffc010 in ?? ()
    #5  0x000012e4e25dc4e9 in ?? ()
    #6  0x0000000000000000 in ?? ()
    rax	0x3aa13de00048	64464202235976
    rbx	0xfffe2f2f2f2f2f2f	-511070251831505
    rcx	0xfffe3aa13de00048	-498485751185336
    rdx	0x2622dccea040	41931175272512
    rsi	0x3aa13de00018	64464202235928
    rdi	0x3aa13de00048	64464202235976
    rbp	0x7fffffffbfd8	140737488338904
    rsp	0x7fffffffbfc0	140737488338880
    r8	0x7fffffffbfc0	140737488338880
    r9	0x0	0
    r10	0x0	0
    r11	0x7ffff3e0dfb8	140737284988856
    r12	0x0	0
    r13	0x0	0
    r14	0x7ffff3898180	140737279263104
    r15	0x0	0
    rip	0x12e4e25dc5ba	20774259639738
    => 0x12e4e25dc5ba:	mov    (%rbx),%rbx
       0x12e4e25dc5bd:	mov    (%rbx),%rbx


Marking s-s due to poison values involved.

---

**Comment 1 — choller@mozilla.com — 2023-09-20T08:01:41Z**

Created attachment 9354057
Detailed Crash Information

---

**Comment 2 — choller@mozilla.com — 2023-09-20T08:01:43Z**

Created attachment 9354058
Testcase

---

**Comment 3 — bugmon@mozilla.com — 2023-09-20T08:24:05Z**

Verified bug as reproducible on mozilla-central 20230920005018-f90822eea608.
Unable to bisect testcase (Unable to launch the start build!):
> Start: fb7ca98a68818c53c8eb69a3a8c8936fcb07ba01 (20220921035608)
> End: f90822eea608a6899fe80b6037d6954f3f936a3c (20230920005018)
> BuildFlags: BuildFlags(asan=None, tsan=None, debug=True, fuzzing=None, coverage=None, valgrind=None, no_opt=None, fuzzilli=None, nyx=None)

---

**Comment 4 — dveditz@mozilla.com — 2023-09-20T21:22:33Z**

Whatever happened, that stack is completely trashed (frame #3 is at address 0x08 ?)

---

**Comment 5 — rhunt@eqrion.net — 2023-09-21T15:51:50Z**

This is a regression caused by bug 1692065.

---

**Comment 6 — rhunt@eqrion.net — 2023-09-21T16:02:49Z**

Created attachment 9354377
Bug 1854068 - wasm: Trace AnyRef spill slots in Ion frames. r?jandem


Bug 1692065 changed JS safepoints to seperate out wasm::AnyRef from
JSObject* as wasm references could start to be tagged pointers. The
bug missed updating the code for handling registers spills for OOL
calls to trace wasm references.

---

**Comment 7 — rhunt@eqrion.net — 2023-09-21T16:04:16Z**

Created attachment 9354380
Bug 1854068 - Add test. r?jandem



Depends on D188845

---

**Comment 8 — release-mgmt-account-bot@mozilla.tld — 2023-09-21T16:42:37Z**

Set release status flags based on info from the regressing bug 1692065

---

**Comment 9 — rhunt@eqrion.net — 2023-09-25T21:44:11Z**

Comment on attachment 9354377
Bug 1854068 - wasm: Trace AnyRef spill slots in Ion frames. r?jandem

### Security Approval Request
* **How easily could an exploit be constructed based on the patch?**: Not trivially. It's clear that we're not tracing some kinds of values (wasm anyref's), but it's not clear how to force this to happen.

A successful repro also needs to have:
  1. JS calling into wasm enough times to tier up into Ion with a fast wasm call
  2. Multiple wasm anyref parameters to the call
  3. At least one parameter needs to not be an object or small integer, to force the other to be spilled across an allocation that could GC
  4. A reliable way to trigger GC's

Definitely possible to figure it out, but it would take me a while to figure out the other parts from just the patch.
* **Do comments in the patch, the check-in comment, or tests included in the patch paint a bulls-eye on the security problem?**: No
* **Which older supported branches are affected by this flaw?**: 118, 199
* **If not all supported branches, which bug introduced the flaw?**: Bug 1692065
* **Do you have backports for the affected branches?**: Yes
* **If not, how different, hard to create, and risky will they be?**: 
* **How likely is this patch to cause regressions; how much testing does it need?**: Unlikely, we're just tracing values that we shouldn't have ignored.
* **Is Android affected?**: Yes

---

**Comment 10 — rhunt@eqrion.net — 2023-09-25T21:45:14Z**

I will remove the commit message as it is a little incriminating, posting here for posterity:
```
Bug 1692065 changed JS safepoints to seperate out wasm::AnyRef from
JSObject* as wasm references could start to be tagged pointers. The
bug missed updating the code for handling registers spills for OOL
calls to trace wasm references.
```

---

**Comment 11 — tom@mozilla.com — 2023-09-26T13:36:10Z**

Comment on attachment 9354377
Bug 1854068 - wasm: Trace AnyRef spill slots in Ion frames. r?jandem

Approved to land.  Seems like we should uplift?

---

**Comment 12 — tom@mozilla.com — 2023-09-26T13:37:31Z**

[Tracking Requested - why for this release]:

---

**Comment 13 — release-mgmt-account-bot@mozilla.tld — 2023-09-26T13:44:37Z**

Set release status flags based on info from the regressing bug 1692065

---

**Comment 14 — rhunt@eqrion.net — 2023-09-26T14:41:03Z**

Yes, agreed that we should uplift. I still need to remove the commit message, then will land it and request uplift.

---

**Comment 15 — pulsebot@bmo.tld — 2023-09-26T16:27:47Z**

Pushed by rhunt@eqrion.net:
https://hg.mozilla.org/integration/autoland/rev/c022ceee1d34
wasm: Trace AnyRef spill slots in Ion frames. r=jandem

---

**Comment 16 — ryanvm@gmail.com — 2023-09-27T04:02:59Z**

https://hg.mozilla.org/mozilla-central/rev/c022ceee1d34

---

**Comment 17 — bugmon@mozilla.com — 2023-09-27T08:21:54Z**

Verified bug as fixed on rev mozilla-central 20230927034915-987e4e1b8f8e.
Removing bugmon keyword as no further action possible.  Please review the bug and re-add the keyword for further analysis.

---

**Comment 18 — release-mgmt-account-bot@mozilla.tld — 2023-09-27T12:05:34Z**

The patch landed in nightly and beta is affected.
:rhunt, is this bug important enough to require an uplift?
- If yes, please nominate the patch for beta approval.
- If no, please set `status-firefox119` to `wontfix`.

For more information, please visit [BugBot documentation](https://wiki.mozilla.org/BugBot#uplift_beta.py).

---

**Comment 19 — rhunt@eqrion.net — 2023-09-27T20:22:35Z**

Comment on attachment 9354377
Bug 1854068 - wasm: Trace AnyRef spill slots in Ion frames. r?jandem

### Beta/Release Uplift Approval Request
* **User impact if declined**: Potential UAF that could be exploited by a clever attacker.
* **Is this code covered by automated tests?**: No
* **Has the fix been verified in Nightly?**: Yes
* **Needs manual test from QE?**: No
* **If yes, steps to reproduce**: 
* **List of other uplifts needed**: None
* **Risk to taking this patch**: Low
* **Why is the change risky/not risky? (and alternatives if risky)**: Traces a missing part of JS call frames, adding back some code that was removed in a refactor.
* **String changes made/needed**: 
* **Is Android affected?**: Yes

---

**Comment 20 — pulsebot@bmo.tld — 2023-09-28T16:34:34Z**

https://hg.mozilla.org/releases/mozilla-beta/rev/b724edee3fc6

---

**Comment 21 — dsmith@mozilla.com — 2023-09-28T16:41:58Z**

Comment on attachment 9354377
Bug 1854068 - wasm: Trace AnyRef spill slots in Ion frames. r?jandem

Approved for 119.0b3

---

**Comment 22 — pascalc@gmail.com — 2023-09-29T14:37:46Z**

Comment on attachment 9354377
Bug 1854068 - wasm: Trace AnyRef spill slots in Ion frames. r?jandem

We don't include sec patches in planned dot releases, unless we are in a 0-day situation and 118 was already set as wontfix.

---

**Comment 23 — release-mgmt-account-bot@mozilla.tld — 2023-12-05T12:00:46Z**

2 months ago, tjr placed a reminder on the bug using the whiteboard tag `[reminder-test 2023-12-05]` .

rhunt, please refer to the original comment to better understand the reason for the reminder.

---

**Comment 24 — dveditz@mozilla.com — 2024-04-29T06:36:00Z**

Bulk-unhiding security bugs fixed in Firefox 119-121 (Fall 2023). Use "moo-doctrine-subsidy" to filter

---

**Comment 25 — pulsebot@bmo.tld — 2025-09-10T21:19:01Z**

Pushed by rhunt@eqrion.net:
https://github.com/mozilla-firefox/firefox/commit/a2940e2347fb
https://hg.mozilla.org/integration/autoland/rev/78cf328058aa
Add test. r=jandem

---

**Comment 26 — nbeleuzu@mozilla.com — 2025-09-11T04:09:32Z**

https://hg.mozilla.org/mozilla-central/rev/78cf328058aa
