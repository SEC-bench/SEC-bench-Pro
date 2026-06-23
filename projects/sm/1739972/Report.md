# Assertion failure: obj->maybeCCWRealm() == this, at js/src/vm/Realm.cpp:445

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1739972
Component: JavaScript Engine: JIT
Bounty: (unknown)
Date: 2021-11-08T10:15:10Z
Keywords: assertion, csectype-uaf, regression, sec-high, testcase

The following testcase crashes on mozilla-central revision 20211108-5823cb0f6998 (debug build, run with --fuzzing-safe --cpu-count=2 --ion-offthread-compile=off --baseline-eager --ion-warmup-threshold=1):

    enableShellAllocationMetadataBuilder();
    a = newGlobal();
    a.evaluate("function x() {}");
    for (i = 0; i < 20; ++i)
      new a.x;


Backtrace:

    received signal SIGSEGV, Segmentation fault.
    #0  0x0000555556fbc12d in JS::Realm::setNewObjectMetadata(JSContext*, JS::Handle<JSObject*>) ()
    #1  0x0000555556ba63f4 in js::NativeObject::create(JSContext*, js::gc::AllocKind, js::gc::InitialHeap, JS::Handle<js::Shape*>, js::gc::AllocSite*) ()
    #2  0x00000ed23a02ed4d in ?? ()
    #3  0x0000000000000000 in ?? ()
    rax	0x5555557c7612	93824994801170
    rbx	0x7fffffffc0c0	140737488339136
    rcx	0x555558151520	93825038357792
    rdx	0x0	0
    rsi	0x7ffff7105770	140737338431344
    rdi	0x7ffff7104540	140737338426688
    rbp	0x7fffffffc070	140737488339056
    rsp	0x7fffffffc020	140737488338976
    r8	0x7ffff7105770	140737338431344
    r9	0x7ffff7f99840	140737353717824
    r10	0x0	0
    r11	0x0	0
    r12	0x7ffff600dc00	140737320639488
    r13	0x4	4
    r14	0x7fffffffc0d0	140737488339152
    r15	0x22ac1b300cb8	38122585853112
    rip	0x555556fbc12d <JS::Realm::setNewObjectMetadata(JSContext*, JS::Handle<JSObject*>)+653>
    => 0x555556fbc12d <_ZN2JS5Realm20setNewObjectMetadataEP9JSContextNS_6HandleIP8JSObjectEE+653>:	movl   $0x1bd,0x0
       0x555556fbc138 <_ZN2JS5Realm20setNewObjectMetadataEP9JSContextNS_6HandleIP8JSObjectEE+664>:	callq  0x555556b09e8f <abort>


Marking s-s until investigated because this is related to JITs and CCW.

---

**Comment 1 — choller@mozilla.com — 2021-11-08T10:15:13Z**

Created attachment 9249732
Detailed Crash Information

---

**Comment 2 — choller@mozilla.com — 2021-11-08T10:15:15Z**

Created attachment 9249733
Testcase

---

**Comment 3 — jcoppeard@mozilla.com — 2021-11-08T16:13:02Z**

This was an oversight in bug 1738721 which removed CreateThisWithTemplate, which switched realm where necessary.

---

**Comment 4 — jcoppeard@mozilla.com — 2021-11-08T16:14:02Z**

Created attachment 9249783
Bug 1739972 - Switch realm if necessary when creathing |this| in the NewPlainObject fallback functions r?jandem


When creating the |this| object for a scripted constructor, the shape's realm
may not match that of the context. The patch swiches realms when necessary.

This is not a problem for the inline JIT code generated as that uses the
shape's realm and ignores the context.

---

**Comment 5 — bugmon@mozilla.com — 2021-11-08T16:20:10Z**

**Bugmon Analysis**
Verified bug as reproducible on mozilla-central 20211108095312-21719d674fc4.
The bug appears to have been introduced in the following build range:
> Start: de5c7a16378c51ce4e540dbe42f8c11fad87efd2 (20211105172534)
> End: b151318ead18b7c6f1ecc5051b8b8b3b250088cd (20211105181720)
> Pushlog: https://hg.mozilla.org/integration/autoland/pushloghtml?fromchange=de5c7a16378c51ce4e540dbe42f8c11fad87efd2&tochange=b151318ead18b7c6f1ecc5051b8b8b3b250088cd

---

**Comment 6 — release-mgmt-account-bot@mozilla.tld — 2021-11-09T12:16:23Z**

Set release status flags based on info from the regressing bug 1738721

---

**Comment 7 — nicolas.b.pierron@mozilla.com — 2021-11-09T17:10:32Z**

Setting S2, as there is no workaround possible from the user perspective. The fact that this is dealing with CCW and UAF suggests that there is potential for escalating level from isolated content to privileged content.

---

**Comment 8 — aryx.bugmail@gmx-topmail.de — 2021-11-10T09:37:15Z**

Switch realm if necessary when creathing |this| in the NewPlainObject fallback functions r=jandem
https://hg.mozilla.org/integration/autoland/rev/59dbf9d365e5e3fd78383630e897243bba14c6ba
https://hg.mozilla.org/mozilla-central/rev/59dbf9d365e5

---

**Comment 9 — bugmon@mozilla.com — 2021-11-10T16:14:57Z**

**Bugmon Analysis**
Verified bug as fixed on rev mozilla-central 20211110092453-333f08065c8c.
Removing bugmon keyword as no further action possible.  Please review the bug and re-add the keyword for further analysis.

---

**Comment 10 — release-mgmt-account-bot@mozilla.tld — 2021-11-10T17:00:15Z**

As part of a security bug pattern analysis, we are requesting your help with a high level analysis of this bug. It is our hope to develop static analysis (or potentially runtime/dynamic analysis) in the future to identify classes of bugs.

Please visit [this google form](https://docs.google.com/forms/d/e/1FAIpQLSe9uRXuoMK6tRglbNL5fpXbun_oEb6_xC2zpuE_CKA_GUjrvA/viewform?usp=pp_url&entry.2124261401=https%3A%2F%2Fbugzilla.mozilla.org%2Fshow_bug.cgi%3Fid%3D1739972) to reply.
