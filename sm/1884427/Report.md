# Crash [@ js::CheckTracedThing]

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1884427
CVE: CVE-2024-3853
Component: JavaScript: GC
Bounty: (unknown)
Date: 2024-03-08T19:25:56Z
Keywords: csectype-uaf, regression, reporter-external, sec-high, testcase

Created attachment 9390239
debug stack

```
gczeal(10);
x = 1;
newGlobal();
oomAtAllocation(8);
try {
  newGlobal();
} catch (e) {}
oomAtAllocation(8);
try {
  newGlobal();
} catch (e) {}
oomAtAllocation(8);
try {
  newGlobal();
} catch (e) {}
newGlobal();
```

```
136	  if (IsForwarded(thing)) {
(gdb) bt
#0  js::CheckTracedThing<JSObject> (trc=trc@entry=0x7fffffffbb38, thing=0xe5e5e5e5e5e5e5e5) at /home/yksubu/trees/mozilla-central/js/src/gc/Marking.cpp:136
#1  0x0000555557c8c134 in js::gc::TraceEdgeInternal (trc=0x7fffffffbb38, thingp=0x7fffffffbb68, Object=<optimized out>) at /home/yksubu/trees/mozilla-central/js/src/gc/Tracer.h:109
#2  js::TraceManuallyBarrieredEdge<JSObject*> (trc=0x7fffffffbb38, thingp=0x7fffffffbb68, name=<optimized out>) at /home/yksubu/trees/mozilla-central/js/src/gc/Tracer.h:252
#3  js::BaseShape::traceChildren (this=0x1bfc73d6e2e0, trc=0x7fffffffbb38) at /home/yksubu/trees/mozilla-central/js/src/gc/TraceMethods-inl.h:305
#4  UpdateCellPointers<js::BaseShape> (trc=0x7fffffffbb38, cell=0x1bfc73d6e2e0) at /home/yksubu/trees/mozilla-central/js/src/gc/Compacting.cpp:497
#5  UpdateArenaPointersTyped<js::BaseShape> (trc=0x7fffffffbb38, arena=0x1bfc73d6e000) at /home/yksubu/trees/mozilla-central/js/src/gc/Compacting.cpp:503
#6  UpdateArenaPointers (trc=0x7fffffffbb38, arena=0x1bfc73d6e000) at /home/yksubu/trees/mozilla-central/js/src/gc/Compacting.cpp:533
#7  UpdateArenaListSegmentPointers (gc=gc@entry=0x7ffff662f798, arenas=...) at /home/yksubu/trees/mozilla-central/js/src/gc/Compacting.cpp:557
#8  0x0000555557c8bb9d in js::gc::GCRuntime::updateCellPointers (this=this@entry=0x7ffff662f798, zone=zone@entry=0x7ffff65b4000, kinds=...) at /home/yksubu/trees/mozilla-central/js/src/gc/Compacting.cpp:676
#9  0x0000555557c86633 in js::gc::GCRuntime::updateAllCellPointers (this=0x7ffff662f798, trc=0x7fffffffc300, zone=0x7ffff65b4000) at /home/yksubu/trees/mozilla-central/js/src/gc/Compacting.cpp:744
#10 js::gc::GCRuntime::updateZonePointersToRelocatedCells (this=this@entry=0x7ffff662f798, zone=zone@entry=0x7ffff65b4000) at /home/yksubu/trees/mozilla-central/js/src/gc/Compacting.cpp:781
/snip
```

Run with `--fuzzing-safe --no-threads --no-baseline --no-ion`, compile with `AR=ar sh ../configure --enable-debug --enable-debug-symbols --with-ccache --enable-nspr-build --enable-ctypes --enable-gczeal --enable-rust-simd --disable-tests`, tested on m-c rev fe38c21e5d5b.

Setting s-s to be safe.

---

**Comment 1 — nth10sd@gmail.com — 2024-03-08T20:24:24Z**

```
The first bad revision is:
changeset:   https://hg.mozilla.org/mozilla-central/rev/86209ac07283
user:        Jan de Mooij
date:        Tue Feb 06 12:51:28 2024 +0000
summary:     Bug 1877193 part 3 - Add testing functions to look up pref names and values. r=mgaudet
```

Jan, is bug 1877193 a likely (or unlikely) regressor?

---

**Comment 2 — release-mgmt-account-bot@mozilla.tld — 2024-03-08T20:42:41Z**

Set release status flags based on info from the regressing bug 1877193

---

**Comment 3 — jdemooij@mozilla.com — 2024-03-11T14:13:02Z**

(In reply to Gary Kwong [:gkw] [:nth10sd] (NOT official MoCo now) from comment #1)
> Jan, is bug 1877193 a likely (or unlikely) regressor?

It's most likely that the new testing functions affect the GC heap in some way. I'll take a closer look.

---

**Comment 4 — jdemooij@mozilla.com — 2024-03-11T17:15:37Z**

The test doesn't call the new testing functions. We destroy a realm but later trace a `BaseShape` pointing to that realm, so we crash when we try to trace its global.

---

**Comment 5 — jcoppeard@mozilla.com — 2024-03-13T11:47:42Z**

Created attachment 9391005
Bug 1884427 - Don't destroy realms that were being initialised at the start of GC r?jandem


The problem is that when global object creation fails it may leave a live base
shape with a pointer into a realm that has been destroyed. This happens when
the base shape is allocated during an incremental GC (and is therefore kept
alive), but the realm was allocated before the GC was started and can be freed.

If the realm was a GC thing it would have been placed in a Rooted and this
would work.

There is a flag to keep the realm alive if it was allocated during GC. The
patch also sets this flag if the realm is in the process of being initialized
at the start of GC.

---

**Comment 6 — jcoppeard@mozilla.com — 2024-03-13T11:48:35Z**

Created attachment 9391006
Bug 1884427 - Add testcode r?jandem

---

**Comment 7 — jcoppeard@mozilla.com — 2024-03-13T16:40:38Z**

Comment on attachment 9391005
Bug 1884427 - Don't destroy realms that were being initialised at the start of GC r?jandem

### Security Approval Request
* **How easily could an exploit be constructed based on the patch?**: Pretty hard, requiring triggering OOM at just the right time.
* **Do comments in the patch, the check-in comment, or tests included in the patch paint a bulls-eye on the security problem?**: No
* **Which branches (beta, release, and/or ESR) are affected by this flaw, and do the release status flags reflect this affected/unaffected state correctly?**: All
* **If not all supported branches, which bug introduced the flaw?**: None
* **Do you have backports for the affected branches?**: No
* **If not, how different, hard to create, and risky will they be?**: The same fix should apply, or would be trivial to backport.
* **How likely is this patch to cause regressions; how much testing does it need?**: Unlikely, as this is a simple change that keeps Realms alive longer in some cases.
* **Is the patch ready to land after security approval is given?**: Yes
* **Is Android affected?**: Yes

---

**Comment 8 — tom@mozilla.com — 2024-03-21T15:51:02Z**

Comment on attachment 9391005
Bug 1884427 - Don't destroy realms that were being initialised at the start of GC r?jandem

sec-approvals were paused for a few days after merge, thanks for the patience.  Normally I'd be circumspect about this level of detail in the commit message; but looking at the patch, I don't think it's really saying anything someone couldn't figure out _very_ quickly from the flag, so there isn't a lot of reason to censor it and then try to add the comment later, leave the description in the bug, etc.  So approved to land and uplift

---

**Comment 9 — tom@mozilla.com — 2024-03-21T15:51:06Z**

Comment on attachment 9391006
Bug 1884427 - Add testcode r?jandem

clearing sec-approval flag for the test, that can land when the reminder expires.

---

**Comment 10 — pulsebot@bmo.tld — 2024-03-21T17:34:53Z**

Pushed by jcoppeard@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/2b96ff9f9527
Don't destroy realms that were being initialised at the start of GC r=jandem

---

**Comment 11 — aryx.bugmail@gmx-topmail.de — 2024-03-21T21:27:36Z**

https://hg.mozilla.org/mozilla-central/rev/2b96ff9f9527

---

**Comment 12 — release-mgmt-account-bot@mozilla.tld — 2024-03-22T12:08:33Z**

The patch landed in nightly and beta is affected.
:jonco, is this bug important enough to require an uplift?
- If yes, please nominate the patch for beta approval.
- If no, please set `status-firefox125` to `wontfix`.

For more information, please visit [BugBot documentation](https://wiki.mozilla.org/BugBot#uplift_beta.py).

---

**Comment 13 — jcoppeard@mozilla.com — 2024-03-26T17:00:57Z**

Comment on attachment 9391005
Bug 1884427 - Don't destroy realms that were being initialised at the start of GC r?jandem

### Beta/Release Uplift Approval Request
* **User impact if declined**: Possible crash / security vulnerability
* **Is this code covered by automated tests?**: Yes
* **Has the fix been verified in Nightly?**: Yes
* **Needs manual test from QE?**: No
* **If yes, steps to reproduce**: 
* **List of other uplifts needed**: None
* **Risk to taking this patch**: Low
* **Why is the change risky/not risky? (and alternatives if risky)**: This is a simple change and has baked on central for a few days.
* **String changes made/needed**: None
* **Is Android affected?**: Yes

---

**Comment 14 — ryanvm@gmail.com — 2024-03-26T22:14:52Z**

Comment on attachment 9391005
Bug 1884427 - Don't destroy realms that were being initialised at the start of GC r?jandem

Approved for 125.0b5.

---

**Comment 15 — pulsebot@bmo.tld — 2024-03-26T22:20:58Z**

https://hg.mozilla.org/releases/mozilla-beta/rev/774e8478df2c

---

**Comment 16 — dveditz@mozilla.com — 2024-04-15T07:24:40Z**

Created attachment 9396603
advisory.txt

---

**Comment 17 — release-mgmt-account-bot@mozilla.tld — 2024-05-28T12:01:15Z**

2 months ago, tjr placed a reminder on the bug using the whiteboard tag `[reminder-test 2024-05-28]` .

jonco, please refer to the original comment to better understand the reason for the reminder.

---

**Comment 18 — pulsebot@bmo.tld — 2024-05-28T12:41:02Z**

Pushed by jcoppeard@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/b9d131b4a351
Add testcode r=jandem

---

**Comment 19 — aryx.bugmail@gmx-topmail.de — 2024-05-28T21:57:44Z**

https://hg.mozilla.org/mozilla-central/rev/b9d131b4a351
