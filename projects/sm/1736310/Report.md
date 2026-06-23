# Assertion failure: !obj->hasDetachedBuffer() (detaching an array buffer sets the length to zero), at js/src/vm/TypedArrayObject.cpp:1021 with GC

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1736310
Component: JavaScript Engine
Bounty: (unknown)
Date: 2021-10-18T08:32:19Z
Keywords: assertion, regression, sec-high, testcase

The following testcase crashes on mozilla-central revision 20211017-5e4047061e46 (debug build, run with --fuzzing-safe --ion-offthread-compile=off):

    gczeal(9, 10);
    function a() {
        var b = new Int32Array(buffer);
        function c(d) {
            b[5] = d;
        }
        return c;
    }
    b = new Int32Array(6);
    var buffer = b.buffer;
    a()({
        valueOf() {
            detachArrayBuffer(buffer);
        }
    })


Backtrace:

    received signal SIGSEGV, Segmentation fault.
    #0  0x00005555570a061d in (anonymous namespace)::TypedArrayObjectTemplate<int>::setElement(JSContext*, JS::Handle<js::TypedArrayObject*>, unsigned long, JS::Handle<JS::Value>, JS::ObjectOpResult&) ()
    #1  0x0000555556f94026 in SetExistingProperty(JSContext*, JS::Handle<JS::PropertyKey>, JS::Handle<JS::Value>, JS::Handle<JS::Value>, JS::Handle<js::NativeObject*>, js::PropertyResult const&, JS::ObjectOpResult&) ()
    #2  0x0000555556f930e6 in bool js::NativeSetProperty<(js::QualifiedBool)1>(JSContext*, JS::Handle<js::NativeObject*>, JS::Handle<JS::PropertyKey>, JS::Handle<JS::Value>, JS::Handle<JS::Value>, JS::ObjectOpResult&) ()
    #3  0x0000555556c1c0c9 in Interpret(JSContext*, js::RunState&) ()
    [...]



Could be related to bug 1736308 but doesn't involve serialization, filing to make sure we don't miss this. Also marking s-s because detached array buffers and GC involved make my spidey sense tingle.

---

**Comment 1 — choller@mozilla.com — 2021-10-18T08:32:22Z**

Created attachment 9246378
Detailed Crash Information

---

**Comment 2 — choller@mozilla.com — 2021-10-18T08:32:23Z**

Created attachment 9246379
Testcase

---

**Comment 3 — jcoppeard@mozilla.com — 2021-10-18T09:58:56Z**

Bisect blames:
```
changeset:   596023:032f4f99161c
user:        Jon Coppeard <jcoppeard@mozilla.com>
date:        Fri Oct 15 16:21:25 2021 +0000
summary:     Bug 1736021 - Replace InnerViewTable::sweepEntry with use of the standard sweep policy r=sfink
```

---

**Comment 4 — jcoppeard@mozilla.com — 2021-10-18T11:02:49Z**

*** Bug 1736308 has been marked as a duplicate of this bug. ***

---

**Comment 5 — release-mgmt-account-bot@mozilla.tld — 2021-10-18T12:17:23Z**

Set release status flags based on info from the regressing bug 1736021

---

**Comment 6 — jcoppeard@mozilla.com — 2021-10-18T13:25:37Z**

Created attachment 9246427
Bug 1736310 - Replace WeakCache::needsSweep method with empty() r?sfink


We use the 'needsSweep' method name for two separate things. We use it in
WeakCache to check whether a cache needs to be swept at all, i.e. whether it is
not empty. We also use it in the GCPolicy trait as a method to sweep something.
GCHashMap/Set/GCVector implement it for the former reason, and so if we attempt
to use one for something that will be swept with GCPolicy it won't work.

I was going to rename the WeakCache method later anyway (because it's clearer
just to provide an empty() method) but I hadn't realised this collision was
going to happen. The patch in bug 1736021 causes a GCVector to be swept via
GCPolicy which calls the existing needsSweep() method which doesn't sweep at
all. The fix is to provide a version that does.

This will itself go away soon and be replaced with traceWeak(), but we'll fix
this problem first.

---

**Comment 7 — bugmon@mozilla.com — 2021-10-18T16:18:56Z**

**Bugmon Analysis**
Verified bug as reproducible on mozilla-central 20211018095159-63d10a00d256.
The bug appears to have been introduced in the following build range:
> Start: a7de14d905e903c90d07f203b0bb1785363a4af3 (20211015161054)
> End: 032f4f99161cfd4b8d64d3af21c5744101711207 (20211015162411)
> Pushlog: https://hg.mozilla.org/integration/autoland/pushloghtml?fromchange=a7de14d905e903c90d07f203b0bb1785363a4af3&tochange=032f4f99161cfd4b8d64d3af21c5744101711207

---

**Comment 8 — continuation@gmail.com — 2021-10-18T17:21:55Z**

I'll assume this is sec-high, but feel free to adjust as needed.

---

**Comment 9 — aryx.bugmail@gmx-topmail.de — 2021-10-18T21:56:52Z**

Replace WeakCache::needsSweep method with empty() r=sfink
https://hg.mozilla.org/integration/autoland/rev/ea425d0080b39d59d1dff21ce52407911fd7ad1f
https://hg.mozilla.org/mozilla-central/rev/ea425d0080b3

---

**Comment 10 — bugmon@mozilla.com — 2021-10-19T00:14:22Z**

**Bugmon Analysis**
Verified bug as fixed on rev mozilla-central 20211018214442-3b1b07d0c956.
Removing bugmon keyword as no further action possible.  Please review the bug and re-add the keyword for further analysis.

---

**Comment 11 — release-mgmt-account-bot@mozilla.tld — 2021-10-20T17:00:09Z**

As part of a security bug pattern analysis, we are requesting your help with a high level analysis of this bug. It is our hope to develop static analysis (or potentially runtime/dynamic analysis) in the future to identify classes of bugs.

Please visit [this google form](https://docs.google.com/forms/d/e/1FAIpQLSe9uRXuoMK6tRglbNL5fpXbun_oEb6_xC2zpuE_CKA_GUjrvA/viewform?usp=pp_url&entry.2124261401=https%3A%2F%2Fbugzilla.mozilla.org%2Fshow_bug.cgi%3Fid%3D1736310) to reply.
