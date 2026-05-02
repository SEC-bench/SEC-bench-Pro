# Assertion failure: cx->realm() == oldRealm, at /js/src/vm/Realm.h:819

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1888614
Component: JavaScript Engine
Bounty: (unknown)
Date: 2024-03-29T08:15:20Z
Keywords: assertion, regression, sec-high, testcase
See Also:
- https://bugzilla.mozilla.org/show_bug.cgi?id=1888746

The following testcase crashes on mozilla-central revision 20240328-1bf9232e1e78 (debug build, run with --fuzzing-safe --ion-offthread-compile=off test.js):

    function a(b) {
        b.Array.prototype.toSorted.call([2, 3], () => c)
    }
    a(newGlobal())


Backtrace:

    received signal SIGSEGV, Segmentation fault.
    #0  0x000056108adc6b9d in js::jit::CallTrampolineNativeJitCode(JSContext*, js::jit::TrampolineNative, JS::CallArgs&) ()
    #1  0x000056108a170133 in js::array_sort(JSContext*, unsigned int, JS::Value*) ()
    #2  0x000056108a122565 in CallJSNative(JSContext*, bool (*)(JSContext*, unsigned int, JS::Value*), js::CallReason, JS::CallArgs const&) ()
    #3  0x000056108a121ad8 in js::InternalCallOrConstruct(JSContext*, JS::CallArgs const&, js::MaybeConstruct, js::CallReason) ()
    #4  0x000056108a1327bb in js::Interpret(JSContext*, js::RunState&) ()
    #5  0x000056108a12107f in js::RunScript(JSContext*, js::RunState&) ()
    #6  0x000056108a1219f8 in js::InternalCallOrConstruct(JSContext*, JS::CallArgs const&, js::MaybeConstruct, js::CallReason) ()
    #7  0x000056108a1233a3 in js::Call(JSContext*, JS::Handle<JS::Value>, JS::Handle<JS::Value>, js::AnyInvokeArgs const&, JS::MutableHandle<JS::Value>, js::CallReason) ()
    #8  0x000056108a39d82d in js::fun_call(JSContext*, unsigned int, JS::Value*) ()
    #9  0x000056108a122565 in CallJSNative(JSContext*, bool (*)(JSContext*, unsigned int, JS::Value*), js::CallReason, JS::CallArgs const&) ()
    #10 0x000056108a121ad8 in js::InternalCallOrConstruct(JSContext*, JS::CallArgs const&, js::MaybeConstruct, js::CallReason) ()
    [...]
    #20 0x0000561089f530a9 in main ()
    rax	0x561088906f23	94629010632483
    rbx	0x7fc4b1739100	140482767458560
    rcx	0x56108bb01a88	94629063039624
    rdx	0x1	1
    rsi	0x0	0
    rdi	0x7fc4b4aa97d0	140482821396432
    rbp	0x7ffd00b747f0	140724615464944
    rsp	0x7ffd00b744d0	140724615464144
    r8	0x0	0
    r9	0x6c	108
    r10	0x5610888013bb	94629009560507
    r11	0x18	24
    r12	0x7fc4b1739100	140482767458560
    r13	0x7fc4b05ba200	140482749112832
    r14	0x0	0
    r15	0xfffa800000000000	-1548112371908608
    rip	0x56108adc6b9d <js::jit::CallTrampolineNativeJitCode(JSContext*, js::jit::TrampolineNative, JS::CallArgs&)+1261>
    => 0x56108adc6b9d <_ZN2js3jit27CallTrampolineNativeJitCodeEP9JSContextNS0_16TrampolineNativeERN2JS8CallArgsE+1261>:	movl   $0x333,0x0
       0x56108adc6ba8 <_ZN2js3jit27CallTrampolineNativeJitCodeEP9JSContextNS0_16TrampolineNativeERN2JS8CallArgsE+1272>:	callq  0x561089ff6970 <abort>


S-s until investigated, but possibly a shell-only issue.

---

**Comment 1 — choller@mozilla.com — 2024-03-29T08:15:24Z**

Created attachment 9393934
Detailed Crash Information

---

**Comment 2 — choller@mozilla.com — 2024-03-29T08:15:26Z**

Created attachment 9393935
Testcase

---

**Comment 3 — bugmon@mozilla.com — 2024-03-29T16:22:57Z**

Verified bug as reproducible on mozilla-central 20240329091052-4120fb3d12f5.
The bug appears to have been introduced in the following build range:
> Start: 7f2993771f48536c575137e4b51984ab6d3de136 (20240327093111)
> End: 9c458764557de25f93134811a808f6c5b68b5683 (20240327123927)
> Pushlog: https://hg.mozilla.org/integration/autoland/pushloghtml?fromchange=7f2993771f48536c575137e4b51984ab6d3de136&tochange=9c458764557de25f93134811a808f6c5b68b5683

---

**Comment 4 — jdemooij@mozilla.com — 2024-04-02T07:27:29Z**

*** Bug 1888859 has been marked as a duplicate of this bug. ***

---

**Comment 5 — jdemooij@mozilla.com — 2024-04-02T07:42:35Z**

Created attachment 9394414
Bug 1888614 - Fix exception handler to restore realm for trampoline native frames too. r?iain!

---

**Comment 6 — release-mgmt-account-bot@mozilla.tld — 2024-04-02T12:10:54Z**

Based on comment #3, this bug contains a bisection range found by bugmon. However, the `Regressed by` field is still not filled.

:jandem, if possible, could you fill the `Regressed by` field and investigate this regression?

For more information, please visit [BugBot documentation](https://wiki.mozilla.org/BugBot#bisection_without_regressed_by.py).

---

**Comment 7 — release-mgmt-account-bot@mozilla.tld — 2024-04-03T09:42:51Z**

Set release status flags based on info from the regressing bug 1884360

---

**Comment 8 — pulsebot@bmo.tld — 2024-04-03T10:06:07Z**

Pushed by jdemooij@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/8ba15fb3353f
Fix exception handler to restore realm for trampoline native frames too. r=iain

---

**Comment 9 — ryanvm@gmail.com — 2024-04-04T03:51:20Z**

https://hg.mozilla.org/mozilla-central/rev/8ba15fb3353f

---

**Comment 10 — bugmon@mozilla.com — 2024-04-04T08:36:09Z**

Verified bug as fixed on rev mozilla-central 20240404034404-1d9c4672f9f5.
Removing bugmon keyword as no further action possible.  Please review the bug and re-add the keyword for further analysis.
