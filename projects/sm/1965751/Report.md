# Assertion failure: (value & RESERVED_MASK) == 0, at gc/Cell.h:109

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1965751
Component: JavaScript Engine
Bounty: (unknown)
Date: 2025-05-12T09:00:48Z
Keywords: assertion, csectype-wildptr, regression, sec-high, testcase

The following testcase crashes on mozilla-central revision 20250502-5b5bd7e73009 (debug build, run with --fuzzing-safe --ion-offthread-compile=off test-indirect.js):

    function a(b, c) {
        d = "a".repeat(1000)
        e = ensureLinearString(newRope(d, "Unknown"))
        ensureLinearString(newRope(e, "abcdef", {
            nursery: c
        }))
        gc()
    }
    a(true, false)


Backtrace:

    received signal SIGSEGV, Segmentation fault.
    #0  0x00005a44b6ac2a9c in JSString::base() const ()
    #1  0x00005a44b7043827 in void js::GCMarker::eagerlyMarkChildren<4u>(JSLinearString*) ()
    #2  0x00005a44b70477c1 in bool js::GCMarker::processMarkStackTop<0u>(JS::SliceBudget&) ()
    #3  0x00005a44b7046b72 in bool js::GCMarker::markOneColor<0u, (js::gc::MarkColor)2>(JS::SliceBudget&) ()
    #4  0x00005a44b702a5a4 in bool js::GCMarker::doMarking<0u>(JS::SliceBudget&, js::gc::ShouldReportMarkTime) ()
    #5  0x00005a44b7001a63 in js::GCMarker::markUntilBudgetExhausted(JS::SliceBudget&, js::gc::ShouldReportMarkTime) ()
    #6  0x00005a44b7000d0b in js::gc::GCRuntime::markUntilBudgetExhausted(JS::SliceBudget&, js::gc::GCRuntime::ParallelMarking, js::gc::ShouldReportMarkTime) ()
    #7  0x00005a44b70060a7 in js::gc::GCRuntime::incrementalSlice(JS::SliceBudget&, JS::GCReason, bool) ()
    #8  0x00005a44b7009c13 in js::gc::GCRuntime::gcCycle(bool, JS::SliceBudget const&, JS::GCReason) ()
    #9  0x00005a44b700b484 in js::gc::GCRuntime::collect(bool, JS::SliceBudget const&, JS::GCReason) ()
    #10 0x00005a44b6ff181a in js::gc::GCRuntime::gc(JS::GCOptions, JS::GCReason) ()
    #11 0x00005a44b7012c80 in JS::NonIncrementalGC(JSContext*, JS::GCOptions, JS::GCReason) ()
    #12 0x00005a44b6c21608 in GC(JSContext*, unsigned int, JS::Value*) ()
    #13 0x00005a44b66ef845 in CallJSNative(JSContext*, bool (*)(JSContext*, unsigned int, JS::Value*), js::CallReason, JS::CallArgs const&) ()
    [...]
    #24 0x00005a44b655cede in main ()
    rax	0x0	0
    rbx	0x73a960442b60	127171301747552
    rcx	0x6d	109
    rdx	0x73a9637d3723	127171355817763
    rsi	0x0	0
    rdi	0x73a9637d4a60	127171355822688
    rbp	0x7fffaf5ac740	140736135350080
    rsp	0x7fffaf5ac740	140736135350080
    r8	0x71	113
    r9	0x0	0
    r10	0x0	0
    r11	0x18	24
    r12	0x158	344
    r13	0xab8	2744
    r14	0x1e3dbf777028	33250554114088
    r15	0x73a960442b60	127171301747552
    rip	0x5a44b6ac2a9c <JSString::base() const+380>
    => 0x5a44b6ac2a9c <_ZNK8JSString4baseEv+380>:	mov    %rcx,(%rax)
       0x5a44b6ac2a9f <_ZNK8JSString4baseEv+383>:	call   0x5a44b65f7780 <abort>


This kind of assert is usually bad news, marking s-s.

---

**Comment 1 — choller@mozilla.com — 2025-05-12T09:00:51Z**

Created attachment 9486867
Detailed Crash Information

---

**Comment 2 — choller@mozilla.com — 2025-05-12T09:00:53Z**

Created attachment 9486868
Testcase

---

**Comment 3 — jdemooij@mozilla.com — 2025-05-12T13:04:23Z**

This might be related to the dependent-string changes.

---

**Comment 4 — bugmon@mozilla.com — 2025-05-12T16:58:16Z**

Verified bug as reproducible on mozilla-central 20250511205430-e473aa82ffe1.
The bug appears to have been introduced in the following build range:
> Start: 97439c139468d52561dd0e1a31b15d0f732f042a (20250430002555)
> End: af5cca52d3c61a9a27a9aa36356209862c17ea3e (20250430010637)
> Pushlog: https://hg.mozilla.org/integration/autoland/pushloghtml?fromchange=97439c139468d52561dd0e1a31b15d0f732f042a&tochange=af5cca52d3c61a9a27a9aa36356209862c17ea3e

---

**Comment 5 — release-mgmt-account-bot@mozilla.tld — 2025-05-12T17:43:38Z**

Set release status flags based on info from the regressing bug 1959310

---

**Comment 6 — sphink@gmail.com — 2025-05-13T15:33:42Z**

This still reproduces after bug 1964192 and bug 1963648.

---

**Comment 7 — sphink@gmail.com — 2025-05-13T19:30:31Z**

Created attachment 9487386
Bug 1965751 - Always update to promoted root base string and post-barrier r=jonco

---

**Comment 8 — continuation@gmail.com — 2025-05-13T20:00:40Z**

This sounds like a kind of type confusion, so I'll mark it sec-high.

---

**Comment 9 — sphink@gmail.com — 2025-05-13T20:19:24Z**

UAF, but stemming from confusion over the status of a pointer, so "type confusion" is probably fair.

The main mitigating factor is that it's read-only.

---

**Comment 10 — sdetar@mozilla.com — 2025-05-13T20:32:56Z**

Changing severity to S2 since this is a sec-high

---

**Comment 11 — pulsebot@bmo.tld — 2025-05-17T13:49:29Z**

Pushed by sfink@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/8ecf0a6635cd
Always update to promoted root base string and post-barrier r=jonco

---

**Comment 12 — aryx.bugmail@gmx-topmail.de — 2025-05-17T21:34:50Z**

https://hg.mozilla.org/mozilla-central/rev/8ecf0a6635cd

---

**Comment 13 — bugmon@mozilla.com — 2025-05-19T00:54:57Z**

Verified bug as fixed on rev mozilla-central 20250517213057-99bb697dd65f.
Removing bugmon keyword as no further action possible.  Please review the bug and re-add the keyword for further analysis.
