# Wild deref in js::Shape::getObjectClass (this=0x37bb7837f080) at vm/Shape.h:391

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1895086
CVE: CVE-2024-5688
Component: JavaScript: GC
Bounty: (unknown)
Date: 2024-05-04T18:06:52Z
Keywords: csectype-uaf, reporter-external, sec-high
See Also:
- https://bugzilla.mozilla.org/show_bug.cgi?id=1894916

Steps to reproduce:

On git commit 38377227b8f96fda8f418db614e6a8aa67d01c31 the attached sample crashes in the js-shell when invoked as `obj-x86_64-pc-linux-gnu/dist/bin/js --fuzzing-safe crash.js`.
The reproducer looks similar to bug 1894916, maybe the root cause is related. Attempting to bisect failed but commits from 2022 are affected already (need to fiddle a bit with the second parameter to gczeal).
The older commits, e.g., d48cc4ab1193ac2a8f4aa78743a69fb24a3595e6 assert with `Assertion failure: IsBackgroundFinalizedWhenTenured(a) == IsBackgroundFinalizedWhenTenured(b), at vm/JSObject.cpp:1218`

```
gczeal(8, 37);
function f67() {
    for (let i71 = 0; i71 < 50; i71++) {
        const v82 = this.transplantableObject();
        const v83 = v82.object;
        class C84 {
        }
        const o86 = {
            "sameZoneAs": C84,
            "immutablePrototype": false,
        };
        const t60 = newGlobal(o86);
        t60.__proto__ = v83;
        const v90 = newGlobal();
        v90.nukeAllCCWs();
        v82.transplant(v90);
    }
}
f67();
```

```
#0  js::Shape::getObjectClass (this=0x37bb7837f080) at js/src/vm/Shape.h:391
#1  JSObject::finalize (this=0x37bb783ac040, gcx=0x7ffff6700c20) at js/src/vm/JSObject-inl.h:97
#2  0x0000555557ffda3f in js::gc::Arena::finalize<JSObject> (this=this@entry=0x37bb783ac000, gcx=gcx@entry=0x7ffff6700c20, thingKind=<optimized out>, thingSize=thingSize@entry=56)
    at js/src/gc/Sweeping.cpp:133
#3  0x0000555557ff2648 in FinalizeTypedArenas<JSObject> (gcx=0x7ffff6700c20, src=..., dest=..., thingKind=<optimized out>, budget=...) at js/src/gc/Sweeping.cpp:200
#4  0x0000555557fcf6e3 in FinalizeArenas (gcx=0xaaaaaaaaaaaa0008, gcx@entry=0x7ffff6700c20, src=..., dest=..., thingKind=thingKind@entry=js::gc::AllocKind::OBJECT4_BACKGROUND, budget=...)
    at js/src/gc/Sweeping.cpp:231
#5  0x0000555557fcf137 in js::gc::GCRuntime::backgroundFinalize (this=this@entry=0x7ffff6b2f798, gcx=gcx@entry=0x7ffff6700c20, zone=zone@entry=0x7ffff631d000, kind=<optimized out>, 
    empty=empty@entry=0x7ffff6700b10) at js/src/gc/Sweeping.cpp:270
#6  0x0000555557fd2662 in js::gc::GCRuntime::sweepBackgroundThings (this=this@entry=0x7ffff6b2f798, zones=...) at js/src/gc/Sweeping.cpp:348
#7  0x0000555557fd3025 in js::gc::GCRuntime::sweepFromBackgroundThread (this=0x7ffff6b2f798, lock=...) at js/src/gc/Sweeping.cpp:425
#8  0x0000555557f47050 in js::GCParallelTask::runTask (this=this@entry=0x7ffff6b31768, gcx=gcx@entry=0x7ffff6700c20, lock=...) at js/src/gc/GCParallelTask.cpp:201
#9  0x0000555557f47429 in js::GCParallelTask::runHelperThreadTask (this=0x7ffff6b31768, lock=...) at js/src/gc/GCParallelTask.cpp:183
#10 0x0000555557569fb7 in js::GlobalHelperThreadState::runTaskLocked (this=this@entry=0x7ffff6b19400, task=0x7ffff6b31768, locked=...) at js/src/vm/HelperThreads.cpp:1728
#11 0x0000555557569c12 in js::GlobalHelperThreadState::runOneTask (this=0x7ffff6b19400, lock=...) at js/src/vm/HelperThreads.cpp:1697
#12 0x00005555575a0e4b in js::HelperThread::threadLoop (this=this@entry=0x7ffff6b27260, pool=pool@entry=0x7ffff6b23380) at js/src/vm/InternalThreadPool.cpp:282
#13 0x00005555575a0a18 in js::HelperThread::ThreadMain (pool=0x7ffff6b23380, helper=0x7ffff6b27260) at js/src/vm/InternalThreadPool.cpp:225
#14 0x00005555575bda74 in js::detail::ThreadTrampoline<void (&)(js::InternalThreadPool*, js::HelperThread*), js::InternalThreadPool*&, js::HelperThread*>::callMain<0ul, 1ul> (this=0x7ffff6b0f2e0)
    at js/src/threading/Thread.h:228
#15 js::detail::ThreadTrampoline<void (&)(js::InternalThreadPool*, js::HelperThread*), js::InternalThreadPool*&, js::HelperThread*>::Start (aPack=0x7ffff6b0f2e0)
    at js/src/threading/Thread.h:217
#16 0x00007ffff7897b5a in start_thread (arg=<optimized out>) at ./nptl/pthread_create.c:444
#17 0x00007ffff79285fc in clone3 () at ../sysdeps/unix/sysv/linux/x86_64/clone3.S:78

(gdb) x/i $rip
=> 0x555557ffe2f4 <_ZN8JSObject8finalizeEPN2JS9GCContextE+148>: mov    (%rax),%rax
(gdb) i r rax 
rax            0xfffe4b4b00c000c0  -480164446207808
```

---

**Comment 1 — nicolas.b.pierron@mozilla.com — 2024-05-07T16:48:26Z**

Jon, any insight?
Sounds like a corner case of object transplant. Not sure this can be achieved in the browser but I'll let you judge that.

---

**Comment 2 — jcoppeard@mozilla.com — 2024-05-08T14:39:04Z**

*** Bug 1894916 has been marked as a duplicate of this bug. ***

---

**Comment 3 — jcoppeard@mozilla.com — 2024-05-08T14:40:42Z**

During swap JSObject::setIsUsedAsPrototype is triggering a GC before we do the write barrier.

---

**Comment 4 — jcoppeard@mozilla.com — 2024-05-08T15:34:27Z**

Created attachment 9400712
Bug 1895086 - Suppress GC during JSObject::swap r?jandem


We already suppress GC for part of this, but not for the part where we call
JSObject::setIsUsedAsPrototype. This can GC (which was surprising to me) and so
we can sweep before the pre-write barrier which comes after this.

The simplest and safest thing is to suppress GC for the whole method.

---

**Comment 5 — jcoppeard@mozilla.com — 2024-05-09T09:13:43Z**

Created attachment 9400885
Bug 1895086 - Add testcase r?jandem

---

**Comment 6 — jcoppeard@mozilla.com — 2024-05-09T09:21:30Z**

Comment on attachment 9400712
Bug 1895086 - Suppress GC during JSObject::swap r?jandem

### Security Approval Request
* **How easily could an exploit be constructed based on the patch?**: Very difficult as it relies on shell-only test functions.
* **Do comments in the patch, the check-in comment, or tests included in the patch paint a bulls-eye on the security problem?**: No
* **Which branches (beta, release, and/or ESR) are affected by this flaw, and do the release status flags reflect this affected/unaffected state correctly?**: All
* **If not all supported branches, which bug introduced the flaw?**: None
* **Do you have backports for the affected branches?**: Yes
* **If not, how different, hard to create, and risky will they be?**: Trivial
* **How likely is this patch to cause regressions; how much testing does it need?**: Very unlikely, this just extends the scope of GC suppression that's already active in this method.
* **Is the patch ready to land after security approval is given?**: Yes
* **Is Android affected?**: Yes

---

**Comment 7 — release-mgmt-account-bot@mozilla.tld — 2024-05-09T12:13:03Z**

The severity field for this bug is set to S4. However, the bug is flagged with the `sec-high` keyword.
:jonco, could you consider increasing the severity of this security bug?

For more information, please visit [BugBot documentation](https://wiki.mozilla.org/BugBot#severity_high_security.py).

---

**Comment 8 — tom@mozilla.com — 2024-05-14T18:16:34Z**

Comment on attachment 9400712
Bug 1895086 - Suppress GC during JSObject::swap r?jandem

Approved to land and uplift if needed - confused by the comment " relies on shell-only test functions." - if this relies on test functions, it wouldn't affect Firefox, right?  In which case it should not be a security bug.

The test can land immediatlely if it's not a sec bug; or in July if it is.

---

**Comment 9 — continuation@gmail.com — 2024-05-14T18:29:16Z**

(In reply to Tom Ritter [:tjr] from comment #8)
> Comment on attachment 9400712
> Bug 1895086 - Suppress GC during JSObject::swap r?jandem
> 
> Approved to land and uplift if needed - confused by the comment " relies on shell-only test functions." - if this relies on test functions, it wouldn't affect Firefox, right?  In which case it should not be a security bug.
> 
> The test can land immediatlely if it's not a sec bug; or in July if it is.

The shell-only test functions simulate actual operations we do in the browser.

---

**Comment 10 — jcoppeard@mozilla.com — 2024-05-15T08:15:46Z**

I should have said that the test in the patch relies on shell only functions. The issue is present in code used by the browser. The test has been moved to a separate patch now though.

A better answer to that question would be: Very difficult as it relies on triggering GC at a precise point and then exploiting the crash.

---

**Comment 11 — pulsebot@bmo.tld — 2024-05-15T08:49:54Z**

Pushed by jcoppeard@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/09652347e814
Suppress GC during JSObject::swap r=jandem

---

**Comment 12 — ryanvm@gmail.com — 2024-05-15T21:18:58Z**

https://hg.mozilla.org/mozilla-central/rev/09652347e814

---

**Comment 13 — release-mgmt-account-bot@mozilla.tld — 2024-05-16T12:02:13Z**

The patch landed in nightly and beta is affected.
:jonco, is this bug important enough to require an uplift?
- If yes, please nominate the patch for beta approval.
- If no, please set `status-firefox127` to `wontfix`.

For more information, please visit [BugBot documentation](https://wiki.mozilla.org/BugBot#uplift_beta.py).

---

**Comment 14 — jcoppeard@mozilla.com — 2024-05-16T13:36:45Z**

Comment on attachment 9400712
Bug 1895086 - Suppress GC during JSObject::swap r?jandem

### Beta/Release Uplift Approval Request
* **User impact if declined**: Possible crash / security vulnerability.
* **Is this code covered by automated tests?**: Yes
* **Has the fix been verified in Nightly?**: Yes
* **Needs manual test from QE?**: No
* **If yes, steps to reproduce**: 
* **List of other uplifts needed**: None
* **Risk to taking this patch**: Low
* **Why is the change risky/not risky? (and alternatives if risky)**: This is a very simple change to extend an existing GC suppression region already present in this code.
* **String changes made/needed**: None
* **Is Android affected?**: Yes

---

**Comment 15 — pascalc@gmail.com — 2024-05-16T18:52:41Z**

Can we get an uplift request for esr as well?

---

**Comment 16 — jcoppeard@mozilla.com — 2024-05-17T17:01:01Z**

Comment on attachment 9400712
Bug 1895086 - Suppress GC during JSObject::swap r?jandem

### ESR Uplift Approval Request
* **If this is not a sec:{high,crit} bug, please state case for ESR consideration**: This is a sec-high bug.
* **User impact if declined**: Possible crash / security vulnerability.
* **Fix Landed on Version**: 128
* **Risk to taking this patch**: Low
* **Why is the change risky/not risky? (and alternatives if risky)**: This is a very simple change to extend an existing GC suppression region already present in this code.

---

**Comment 17 — pascalc@gmail.com — 2024-05-20T06:53:19Z**

Comment on attachment 9400712
Bug 1895086 - Suppress GC during JSObject::swap r?jandem

Approved for 127 beta 4, thanks.

---

**Comment 18 — pulsebot@bmo.tld — 2024-05-20T06:56:35Z**

https://hg.mozilla.org/releases/mozilla-beta/rev/e3c74007c73f

---

**Comment 19 — ryanvm@gmail.com — 2024-05-24T18:37:17Z**

Comment on attachment 9400712
Bug 1895086 - Suppress GC during JSObject::swap r?jandem

Approved for 115.12esr.

---

**Comment 20 — pulsebot@bmo.tld — 2024-05-24T18:39:35Z**

https://hg.mozilla.org/releases/mozilla-esr115/rev/25c5e091b01e

---

**Comment 21 — tom@mozilla.com — 2024-06-03T18:19:43Z**

Created attachment 9405349
advisory.txt

---

**Comment 22 — release-mgmt-account-bot@mozilla.tld — 2024-07-23T12:00:39Z**

2 months ago, tjr placed a reminder on the bug using the whiteboard tag `[reminder-test 2024-07-23]` .

jonco, please refer to the original comment to better understand the reason for the reminder.

---

**Comment 23 — pulsebot@bmo.tld — 2024-07-23T12:38:10Z**

Pushed by jcoppeard@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/1f39276b16fb
Add testcase r=jandem

---

**Comment 24 — aryx.bugmail@gmx-topmail.de — 2024-07-23T21:20:25Z**

https://hg.mozilla.org/mozilla-central/rev/1f39276b16fb
