# Assertion failure: [barrier verifier] Unmarked edge: JS Object 247352a740b0 'shape' edge to JS Shape 247352a64160, at gc/Verifier.cpp:384

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1804626
Component: JavaScript Engine: JIT
Bounty: (unknown)
Date: 2022-12-08T08:53:12Z
Keywords: assertion, crash, csectype-uaf, regression, sec-high, testcase

The following testcase crashes on mozilla-central revision 20221208-58f36d1b73c5 (debug build, run with --fuzzing-safe --ion-offthread-compile=off --ion-warmup-threshold=0 --baseline-eager):

    function a() {}
    function b(c) {
      c.d = 2;
    }
    function e() {
      f = new a;
      verifyprebarriers();
      b(f);
    }
    for (;;)
      new e;


Backtrace:

    received signal SIGSEGV, Segmentation fault.
    #0  0x00005555576c6129 in js::gc::GCRuntime::endVerifyPreBarriers() ()
    #1  0x000055555723a5ea in VerifyPreBarriers(JSContext*, unsigned int, JS::Value*) ()
    #2  0x0000285a1fd9d862 in ?? ()
    #3  0x0000000000000000 in ?? ()
    rax	0x55555592788d	93824996243597
    rbx	0x5555558cc698	93824995870360
    rcx	0x555558368c98	93825040551064
    rdx	0x0	0
    rsi	0x7ffff7105770	140737338431344
    rdi	0x7ffff7104540	140737338426688
    rbp	0x7fffffffc0d0	140737488339152
    rsp	0x7fffffffbc20	140737488337952
    r8	0x7ffff7105770	140737338431344
    r9	0x7ffff7f99800	140737353717760
    r10	0x0	0
    r11	0x0	0
    r12	0x247352a740b0	40077726531760
    r13	0x555555880b15	93824995560213
    r14	0x7fffffffbca0	140737488338080
    r15	0x5555559134cc	93824996160716
    rip	0x5555576c6129 <js::gc::GCRuntime::endVerifyPreBarriers()+2105>
    => 0x5555576c6129 <_ZN2js2gc9GCRuntime20endVerifyPreBarriersEv+2105>:	movl   $0x181,0x0
       0x5555576c6134 <_ZN2js2gc9GCRuntime20endVerifyPreBarriersEv+2116>:	callq  0x555556c7948c <abort>

---

**Comment 1 — choller@mozilla.com — 2022-12-08T08:53:15Z**

Created attachment 9307258
Detailed Crash Information

---

**Comment 2 — choller@mozilla.com — 2022-12-08T08:53:16Z**

Created attachment 9307259
Testcase

---

**Comment 3 — bugmon@mozilla.com — 2022-12-08T18:07:29Z**

Verified bug as reproducible on mozilla-central 20221208153054-5b38548871de.
The bug appears to have been introduced in the following build range:
> Start: bd22ade4bc203f6f74578b64405d5ac1cb0df980 (20221204030525)
> End: 77591550134cad0a4943249c27acf6097a4b2871 (20221204033701)
> Pushlog: https://hg.mozilla.org/integration/autoland/pushloghtml?fromchange=bd22ade4bc203f6f74578b64405d5ac1cb0df980&tochange=77591550134cad0a4943249c27acf6097a4b2871

---

**Comment 4 — release-mgmt-account-bot@mozilla.tld — 2022-12-08T18:33:27Z**

Set release status flags based on info from the regressing bug 1800384

---

**Comment 5 — dothayer@mozilla.com — 2022-12-08T20:15:47Z**

Created attachment 9307411
Bug 1804626 - Backed out changeset 77591550134c r?iain


It looks like shapes are not being traced through MIR ops, instead relying on
the fact that shapes must always be tenured, and thus can only go away during
a compacting GC which will throw away Ion code anyway. Accordingly our
assumptions for why this optimization was okay were skewed.

---

**Comment 6 — jcoppeard@mozilla.com — 2022-12-09T10:52:31Z**

Created attachment 9307521
Bug 1804626 - Set GC use during background marking to satisfy assertions r?sfink


This assertion is going off because it thinks we souldn't be accessing a cell's
zone off-thread. In fact we are marking and the mutator is not running so this
is fine. The problem is we didn't set GC use to marking for the background mark
task (not parallel marking, this does single threaded marking off-thread during
sweeping).

---

**Comment 7 — aryx.bugmail@gmx-topmail.de — 2022-12-09T16:06:03Z**

Backed out changeset 77591550134c r=iain
https://hg.mozilla.org/integration/autoland/rev/deb7d446c1d59be174cb6c92b4afed603768f7c0
https://hg.mozilla.org/mozilla-central/rev/deb7d446c1d5

---

**Comment 8 — bugmon@mozilla.com — 2022-12-09T16:23:57Z**

Bug marked as FIXED but still reproduces on mozilla-central 20221209044848-408707dd85c5.  If you believe this to be incorrect, please remove the bugmon keyword to prevent further analysis.

---

**Comment 9 — jcoppeard@mozilla.com — 2022-12-09T17:42:00Z**

Sorry, posted patch to the wrong bug.

---

**Comment 10 — phab-bot@bmo.tld — 2022-12-09T17:44:13Z**

Comment on attachment 9307521
Bug 1804626 - Set GC use during background marking to satisfy assertions r?sfink

Revision D164320 was moved to bug 1804787. Setting attachment 9307521 to obsolete.

---

**Comment 11 — dothayer@mozilla.com — 2022-12-12T21:15:24Z**

Hey Jason - how precisely does Bugmon verify the reproducibility of the issue? I'm unable to reproduce this locally and it really doesn't seem like it should be happening anymore.

---

**Comment 12 — jkratzer@mozilla.com — 2022-12-13T16:30:03Z**

Doug, I verified this manually and can confirm that it is fixed.  Bugmon marked it as still active based on the patch revision in comment 7.

---

**Comment 13 — release-mgmt-account-bot@mozilla.tld — 2022-12-13T16:33:57Z**

Set release status flags based on info from the regressing bug 1800384

---

**Comment 14 — dothayer@mozilla.com — 2022-12-13T16:42:32Z**

Okay - given the manual confirmation in comment 12 and the fact that the fixing change landed before the freeze ended, I'm going to remove the bugmon keyword, mark this as fixed, and update the status flags.
