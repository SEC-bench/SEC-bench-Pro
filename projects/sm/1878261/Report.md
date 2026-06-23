# Crash [@ JS::Compartment::wrap] with Debugger and interrupt callback

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1878261
Component: JavaScript Engine
Bounty: (unknown)
Date: 2024-02-02T09:21:33Z
Keywords: crash, csectype-uaf, regression, sec-high, testcase

The following testcase crashes on mozilla-central revision 20240202-854c462a083b (debug build, run with --fuzzing-safe --ion-offthread-compile=off --baseline-eager test.js):

    gczeal(7, 1)
    function a(b) {
        c = newGlobal({
            newCompartment: true
        })
        d = new Debugger
        setInterruptCallback(function() {
            d.addDebuggee(c)
            d.getNewestFrame().onStep = function() {
                return b
            }
            return true
        })
        try {
            c.eval("(" + function() {
                invokeInterruptCallback(function() {})
            } + ")()")
        } finally {}
    }
    a({
        throw: "thrown 42"
    })


Backtrace:

    received signal SIGSEGV, Segmentation fault.
    #0  0x0000555b7e2033db in JS::Compartment::wrap(JSContext*, JS::MutableHandle<JSString*>) ()
    #1  0x0000555b7deb61e4 in JS::Compartment::wrap(JSContext*, JS::MutableHandle<JS::Value>) ()
    #2  0x0000555b7e2c98ac in JSContext::getPendingException(JS::MutableHandle<JS::Value>) ()
    #3  0x0000555b7e2644ed in JS::GetPendingExceptionStack(JSContext*, JS::ExceptionStack*) ()
    #4  0x0000555b7e2643df in JS::StealPendingExceptionStack(JSContext*, JS::ExceptionStack*) ()
    #5  0x0000555b7de89cd1 in js::shell::AutoReportException::~AutoReportException() ()
    #6  0x0000555b7de92c01 in Shell(JSContext*, js::cli::OptionParser*) ()
    #7  0x0000555b7de8c459 in main ()
    rax	0x6c6a4000001	7450224754689
    rbx	0x7f5f9eb44000	140048661233664
    rcx	0xfffe2f2f2f2f2f2c	-511070251831508
    rdx	0x7fff0a6206e0	140733367584480
    rsi	0x7f5f9fd2e100	140048680018176
    rdi	0x7f5f9fd03240	140048679842368
    rbp	0x7fff0a6206b0	140733367584432
    rsp	0x7fff0a620670	140733367584368
    r8	0x0	0
    r9	0x7fff0a61e301	140733367575297
    r10	0x7fff0a7e5080	140733369438336
    r11	0x202	514
    r12	0x7f5f9fd03240	140048679842368
    r13	0x6c6a4000508	7450224755976
    r14	0x7fff0a6206e0	140733367584480
    r15	0x7f5f9fd2e100	140048680018176
    rip	0x555b7e2033db <JS::Compartment::wrap(JSContext*, JS::MutableHandle<JSString*>)+107>
    => 0x555b7e2033db <_ZN2JS11Compartment4wrapEP9JSContextNS_13MutableHandleIP8JSStringEE+107>:	cmp    %rbx,(%rcx)
       0x555b7e2033de <_ZN2JS11Compartment4wrapEP9JSContextNS_13MutableHandleIP8JSStringEE+110>:	jne    0x555b7e20340f <_ZN2JS11Compartment4wrapEP9JSContextNS_13MutableHandleIP8JSStringEE+159>



This involves the debugger so I assume it is sec-moderate at most, however with the poison pattern in the crash, we should confirm that first.

---

**Comment 1 — choller@mozilla.com — 2024-02-02T09:21:37Z**

Created attachment 9377891
Detailed Crash Information

---

**Comment 2 — choller@mozilla.com — 2024-02-02T09:21:39Z**

Created attachment 9377892
Testcase

---

**Comment 3 — bugmon@mozilla.com — 2024-02-02T16:26:28Z**

Verified bug as reproducible on mozilla-central 20240202094312-dd4c0135beb5.
The bug appears to have been introduced in the following build range:
> Start: 82dfbdd770bc54674f82bae256dae683772884af (20240122155520)
> End: 75c3c3ed6fe2c33aa435e3a099c5f18be4b4d8d2 (20240122183000)
> Pushlog: https://hg.mozilla.org/integration/autoland/pushloghtml?fromchange=82dfbdd770bc54674f82bae256dae683772884af&tochange=75c3c3ed6fe2c33aa435e3a099c5f18be4b4d8d2

---

**Comment 4 — iireland@mozilla.com — 2024-02-02T21:11:01Z**

I believe the problem is in [this code](https://searchfox.org/mozilla-central/rev/34ba7989ae53b9112d543ce39d350b79dc2a16b4/js/src/jit/JitFrames.cpp#501-504). We store the exception, which is a nursery string, in `rfe->exception`. Then we store the exception stack. It's from another compartment, so we have to wrap it. Allocating the wrapper triggers a minor GC, which promotes the exception string. However, despite our use of MutableHandleValue::fromMarkedLocation to make a handle out of it, `rfe` isn't actually traced. The exception value stored in `rfe` now points to freed nursery space.

I don't immediately see a reason that this couldn't be done without the debugger. It only requires a cross-compartment exception stack, and a very precisely timed GC. I'm going to conservatively bump this up to sec-high.

This is a regression from bug 1843499, although the first dubious use of fromMarkedLocation here [appears to date back](https://searchfox.org/mozilla-central/rev/d0117a6cb9364dfa8ec37020620eb62ba0a3e439/js/src/jit/IonFrames.cpp#544) all the way to bug 951282.

---

**Comment 5 — andrebargull@googlemail.com — 2024-02-05T14:41:51Z**

Created attachment 9378305
Bug 1878261: Prefer local variables over fromMarkedLocation. r=iain!

---

**Comment 6 — release-mgmt-account-bot@mozilla.tld — 2024-02-05T14:43:07Z**

Set release status flags based on info from the regressing bug 1843499

---

**Comment 7 — andrebargull@googlemail.com — 2024-02-05T14:43:56Z**

(In reply to Iain Ireland [:iain] from comment #4)
> I believe the problem is in [this code](https://searchfox.org/mozilla-central/rev/34ba7989ae53b9112d543ce39d350b79dc2a16b4/js/src/jit/JitFrames.cpp#501-504).

Yes, that sounds plausible. Explicitly rooting the variables fixes the crash.

---

**Comment 8 — iireland@mozilla.com — 2024-02-05T22:51:15Z**

Here's a testcase that triggers the bug without needing the debugger:
```
// |jit-test| --baseline-eager

var g = newGlobal({newCompartment: true});

function foo() {
  try {
    g.eval("gczeal(7,1); throw 'a thrown string'");
  } finally {
    gczeal(0);
  }
}

try {
  foo();
} catch (e) { assertEq(e, 'a thrown string')}
```

We can land it separately.

```

---

**Comment 9 — iireland@mozilla.com — 2024-02-05T23:08:27Z**

Created attachment 9378417
Bug 1878261: Add testcase r=anba

---

**Comment 10 — pulsebot@bmo.tld — 2024-02-06T07:31:37Z**

Pushed by andre.bargull@gmail.com:
https://hg.mozilla.org/integration/autoland/rev/df0b9539f560
Prefer local variables over fromMarkedLocation. r=iain

---

**Comment 11 — ryanvm@gmail.com — 2024-02-07T04:23:47Z**

https://hg.mozilla.org/mozilla-central/rev/df0b9539f560

---

**Comment 12 — bugmon@mozilla.com — 2024-02-07T08:24:48Z**

Verified bug as fixed on rev mozilla-central 20240207041740-79b383834481.
Removing bugmon keyword as no further action possible.  Please review the bug and re-add the keyword for further analysis.

---

**Comment 13 — pulsebot@bmo.tld — 2025-01-22T22:53:43Z**

Pushed by iireland@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/af3032626a68
Add testcase r=anba

---

**Comment 14 — abutkovits@mozilla.com — 2025-01-22T23:29:58Z**

Backed out for causing SM bustages.

Backout link: https://hg.mozilla.org/integration/autoland/rev/badfcbf084e2ec7ad9456346f23a4d6b36a7955e

Push with failures: https://treeherder.mozilla.org/jobs?repo=autoland&resultStatus=testfailed%2Cbusted%2Cexception%2Cretry%2Cusercancel&revision=af3032626a68b96b683ca4359802fc025da8e08c

Failure log: https://treeherder.mozilla.org/logviewer?job_id=491346147&repo=autoland&lineNumber=40413

---

**Comment 15 — iireland@mozilla.com — 2025-01-22T23:53:28Z**

Missing a check for gczeal.

---

**Comment 16 — pulsebot@bmo.tld — 2025-01-23T18:51:35Z**

Pushed by iireland@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/ccd5693bf1b0
Add testcase r=anba

---

**Comment 17 — sstanca@mozilla.com — 2025-01-23T21:52:35Z**

https://hg.mozilla.org/mozilla-central/rev/ccd5693bf1b0
