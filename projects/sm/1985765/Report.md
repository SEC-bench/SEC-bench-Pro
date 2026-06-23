# Crash [@ js::WeakMap<JS::Value, JS::Value>::clearAndCompact()] or Assertion failure: !gc::IsAboutToBeFinalized(r.front().value()), at gc/WeakMap-inl.h:424 with use-after-free

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1985765
Component: JavaScript Engine
Bounty: (unknown)
Date: 2025-08-28T12:18:27Z
Keywords: assertion, crash, csectype-uaf, regression, sec-high, testcase

The following testcase crashes on mozilla-central revision 20250825-9426f4b06a46 (opt build, run with --fuzzing-safe --ion-offthread-compile=off --enable-symbols-as-weakmap-keys --more-compartments):

    class b {
      #c;
      #$; 
      #n; 
      #m; 
      #e; 
      #f; 
      #g;
    }
    class h {
      #$;
      #n;
      #m;
      #e;
      #f;
      #g;
    }
    keyZone = newGlobal()
    i = newGlobal()
    keyZone.eval('var key = Symbol()')
    i.eval('map = new WeakMap')
    i.keyZone = keyZone
    i.eval('map.set(keyZone.key, {})')
    schedulezone(i)
    schedulezone('atoms')
    gc('zone')


Backtrace:

    received signal SIGSEGV, Segmentation fault.
    #0  0x0000555556ece2e2 in js::WeakMap<JS::Value, JS::Value>::clearAndCompact() ()
    #1  0x0000555556b82ffd in js::gc::GCRuntime::sweepWeakMaps() ()
    #2  0x0000555556e18f1e in js::gc::AutoRunParallelTask::run(js::AutoLockHelperThreadState&) ()
    #3  0x0000555556e18cee in js::GCParallelTask::runTask(JS::GCContext*, js::AutoLockHelperThreadState&) ()
    #4  0x0000555556e18c3c in js::GCParallelTask::runHelperThreadTask(js::AutoLockHelperThreadState&) ()
    #5  0x000055555762cf4b in js::GlobalHelperThreadState::runTaskLocked(JS::HelperThreadTask*, js::AutoLockHelperThreadState&) ()
    #6  0x000055555762f2a9 in js::HelperThread::threadLoop(js::InternalThreadPool*) ()
    #7  0x000055555762f097 in js::HelperThread::ThreadMain(js::InternalThreadPool*, js::HelperThread*) ()
    #8  0x000055555762f1c8 in js::detail::ThreadTrampoline<void (&)(js::InternalThreadPool*, js::HelperThread*), js::InternalThreadPool*&, js::HelperThread*>::Start(void*) ()
    #9  0x00005555572cd63b in set_alt_signal_stack_and_start(PthreadCreateParams*) ()
    #10 0x00007ffff769caa4 in ?? () from /lib/x86_64-linux-gnu/libc.so.6
    #11 0x00007ffff7729c3c in ?? () from /lib/x86_64-linux-gnu/libc.so.6
    rax	0x555557d43c1b	93825034107931
    rbx	0x3e7ba4c00000	68700765945856
    rcx	0xe5	229
    rdx	0xfffaffffffffffff	-1407374883553281
    rsi	0x3e7ba4ca6000	68700766625792
    rdi	0x9b9b9b9b9b9b9b9b	-7234017283807667301
    rbp	0x7ffff3c01a40	140737282841152
    rsp	0x7ffff3c019e0	140737282841056
    r8	0x7ffffff00000	140737487306752
    r9	0x20	32
    r10	0x7fffffffffff	140737488355327
    r11	0x7ffffffff000	140737488351232
    r12	0x7ffff30db600	140737271150080
    r13	0x11	17
    r14	0x7ffff30db798	140737271150488
    r15	0xfffe3e7ba4ca6040	-494249186795456
    rip	0x555556ece2e2 <js::WeakMap<JS::Value, JS::Value>::clearAndCompact()+210>
    => 0x555556ece2e2 <_ZN2js7WeakMapIN2JS5ValueES2_E15clearAndCompactEv+210>:	mov    0x10(%rdi),%eax
       0x555556ece2e5 <_ZN2js7WeakMapIN2JS5ValueES2_E15clearAndCompactEv+213>:	test   %eax,%eax

---

**Comment 1 — choller@mozilla.com — 2025-08-28T12:18:30Z**

Created attachment 9510074
Detailed Crash Information

---

**Comment 2 — choller@mozilla.com — 2025-08-28T12:18:32Z**

Created attachment 9510075
Testcase

---

**Comment 3 — bugmon@mozilla.com — 2025-08-29T08:55:17Z**

Verified bug as reproducible on mozilla-central 20250829033106-b3f73f75087d.
Unable to bisect testcase (Testcase reproduces on start build!):
> Start: 155c26b1f6a5fffc39863dfc7fcca8a91147827a (20250601084141)
> End: 9426f4b06a46e835770956a127c1b8d30c5af7dd (20250825155516)
> BuildFlags: BuildFlags(asan=True, tsan=False, debug=False, fuzzing=True, coverage=False, valgrind=False, no_opt=False, fuzzilli=False, nyx=False, searchfox=False, afl=False)

---

**Comment 4 — jcoppeard@mozilla.com — 2025-09-01T09:23:02Z**

This is nightly-only code and requires setting a pref.

---

**Comment 5 — jcoppeard@mozilla.com — 2025-09-01T09:27:58Z**

Created attachment 9510612
(secure)

---

**Comment 6 — jcoppeard@mozilla.com — 2025-09-03T07:13:14Z**

Comment on attachment 9510612
(secure)

### Security Approval Request
* **How easily could an exploit be constructed based on the patch?**: Very difficult.
* **Do comments in the patch, the check-in comment, or tests included in the patch paint a bulls-eye on the security problem?**: No
* **Which branches (beta, release, and/or ESR) are affected by this flaw, and do the release status flags reflect this affected/unaffected state correctly?**: Nightly only affected
* **If not all supported branches, which bug introduced the flaw?**: Bug 1967693
* **Do you have backports for the affected branches?**: Yes
* **If not, how different, hard to create, and risky will they be?**: N/A
* **How likely is this patch to cause regressions; how much testing does it need?**: Very unlikely. This is a simple localised change.
* **Is the patch ready to land after security approval is given?**: Yes
* **Is Android affected?**: Yes

---

**Comment 7 — continuation@gmail.com — 2025-09-03T14:10:21Z**

Comment on attachment 9510612
(secure)

This doesn't need sec-approval as enable-symbols-as-weakmap-keys is not enabled by default on any branch. (It would also not need sec-approval if it was enabled by default on Nightly but not any other branch.)

---

**Comment 8 — pulsebot@bmo.tld — 2025-09-04T07:13:39Z**

Pushed by jcoppeard@mozilla.com:
https://github.com/mozilla-firefox/firefox/commit/3a8fb49d343b
https://hg.mozilla.org/integration/autoland/rev/3035855099fb
Fix bitmask calculation when checking dense bitmap bit r=sfink

---

**Comment 9 — ryanvm@gmail.com — 2025-09-05T04:15:30Z**

https://hg-edge.mozilla.org/mozilla-central/rev/3035855099fb

---

**Comment 10 — bugmon@mozilla.com — 2025-09-05T08:55:59Z**

Verified bug as fixed on rev mozilla-central 20250905040921-a7e2017228ab.
Removing bugmon keyword as no further action possible.  Please review the bug and re-add the keyword for further analysis.
