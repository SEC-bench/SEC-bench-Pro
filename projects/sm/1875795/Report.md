# Assertion failure: slots == calculateDynamicSlots(), at js/src/vm/JSObject-inl.h:45 with OOM

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1875795
Component: JavaScript Engine: JIT
Bounty: (unknown)
Date: 2024-01-22T12:32:39Z
Keywords: assertion, csectype-jit, regression, sec-high, testcase

The following testcase crashes on mozilla-central revision 20240122-6b4a069fe37d (debug build, run with --fuzzing-safe --ion-offthread-compile=off --ion-warmup-threshold=10):

    b = function() {}
    evaluate(`   
      oomTest(function() {
        var c = new b
        for (d in this) 
          c[d] = []
      });
    `);


Backtrace:

    received signal SIGSEGV, Segmentation fault.
    0x00005555570f351b in js::NativeObject::numDynamicSlots() const ()
    #0  0x00005555570f351b in js::NativeObject::numDynamicSlots() const ()
    #1  0x0000555557c987b6 in bool js::jit::TryAddOrSetPlainObjectProperty<true>(JSContext*, JS::Handle<js::PlainObject*>, JS::PropertyKey, JS::Handle<JS::Value>, bool*) ()
    #2  0x0000555557c98199 in bool js::jit::SetElementMegamorphic<true>(JSContext*, JS::Handle<JSObject*>, JS::Handle<JS::Value>, JS::Handle<JS::Value>, bool) ()
    [...]
    #7  0x0000000000000000 in ?? ()
    rax	0x5555558a27d0	93824995698640
    rbx	0x7e	126
    rcx	0x555558966e28	93825046834728
    rdx	0x0	0
    rsi	0x7ffff7105770	140737338431344
    rdi	0x7ffff7104540	140737338426688
    rbp	0x7fffffffba60	140737488337504
    rsp	0x7fffffffba40	140737488337472
    r8	0x7ffff7105770	140737338431344
    r9	0x7ffff7f92840	140737353689152
    r10	0x2	2
    r11	0x0	0
    r12	0x4	4
    r13	0x7fffffffba98	140737488337560
    r14	0x3a12ac000798	63851869505432
    r15	0x80	128
    rip	0x5555570f351b <js::NativeObject::numDynamicSlots() const+267>
    => 0x5555570f351b <_ZNK2js12NativeObject15numDynamicSlotsEv+267>:	movl   $0x2d,0x0
       0x5555570f3526 <_ZNK2js12NativeObject15numDynamicSlotsEv+278>:	callq  0x555556ebef00 <abort>


S-s due to JIT assertion.

---

**Comment 1 — choller@mozilla.com — 2024-01-22T12:32:43Z**

Created attachment 9375768
Detailed Crash Information

---

**Comment 2 — choller@mozilla.com — 2024-01-22T12:32:45Z**

Created attachment 9375769
Testcase

---

**Comment 3 — jdemooij@mozilla.com — 2024-01-22T13:45:57Z**

Looks like an OOM issue with the megamorphic add-slot code.

---

**Comment 4 — jdemooij@mozilla.com — 2024-01-22T14:35:14Z**

The bug is in `MacroAssembler::emitMegamorphicCachedSetSlot`. We call `NativeObject::growSlotsPure` but don't check the return value correctly. We put the return value in  `scratch2` but then clobber `scratch2` with the saved value before we check if it's `false`. The value in `scratch2` will be non-zero because we skip the call if it's zero (although we only check the low byte for `branchIfFalseBool`).

---

**Comment 5 — jdemooij@mozilla.com — 2024-01-22T14:37:50Z**

I think this is bad because we give the object a shape that includes the new property, but the object doesn't have a slot for it because we failed to allocate it. (This is also what triggers the assertion failure.)

---

**Comment 6 — jdemooij@mozilla.com — 2024-01-22T14:43:08Z**

Created attachment 9375790
Bug 1875795 - Take scratch2 from register set before creating LiveRegisterSet. r?iain!

---

**Comment 7 — jdemooij@mozilla.com — 2024-01-22T14:43:19Z**

Created attachment 9375791
Bug 1875795 - Add test and assertion. r?iain!



Depends on D199233

---

**Comment 8 — bugmon@mozilla.com — 2024-01-22T16:21:58Z**

Verified bug as reproducible on mozilla-central 20240122123104-f7134e498cbd.
Unable to bisect testcase (Testcase reproduces on start build!):
> Start: c00936a538d944ced81780de7e2670806145f0ec (20231025092112)
> End: 6b4a069fe37d2413229dda3b61ccaf7b8f3a5f5d (20240122101417)
> BuildFlags: BuildFlags(asan=False, tsan=False, debug=True, fuzzing=True, coverage=False, valgrind=False, no_opt=False, fuzzilli=False, nyx=False)

---

**Comment 9 — jdemooij@mozilla.com — 2024-01-23T10:28:09Z**

Comment on attachment 9375790
Bug 1875795 - Take scratch2 from register set before creating LiveRegisterSet. r?iain!

### Security Approval Request
* **How easily could an exploit be constructed based on the patch?**: Not very easy. Requires triggering an OOM error in just the right place.
* **Do comments in the patch, the check-in comment, or tests included in the patch paint a bulls-eye on the security problem?**: No
* **Which older supported branches are affected by this flaw?**: All
* **If not all supported branches, which bug introduced the flaw?**: None
* **Do you have backports for the affected branches?**: Yes
* **If not, how different, hard to create, and risky will they be?**: Patch should apply or will be easy to backport.
* **How likely is this patch to cause regressions; how much testing does it need?**: Small patch that's unlikely to cause regressions.
* **Is Android affected?**: Yes

---

**Comment 10 — tom@mozilla.com — 2024-01-23T20:38:50Z**

Comment on attachment 9375790
Bug 1875795 - Take scratch2 from register set before creating LiveRegisterSet. r?iain!

Approved to land and uplift

---

**Comment 11 — pulsebot@bmo.tld — 2024-01-24T13:40:03Z**

Pushed by jdemooij@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/2adc22e92698
Take scratch2 from register set before creating LiveRegisterSet. r=iain

---

**Comment 12 — aryx.bugmail@gmx-topmail.de — 2024-01-24T21:39:36Z**

https://hg.mozilla.org/mozilla-central/rev/2adc22e92698

---

**Comment 13 — jdemooij@mozilla.com — 2024-01-25T08:00:00Z**

Comment on attachment 9375790
Bug 1875795 - Take scratch2 from register set before creating LiveRegisterSet. r?iain!

### Beta/Release Uplift Approval Request
* **User impact if declined**: Security issues, crashes.
* **Is this code covered by automated tests?**: Yes
* **Has the fix been verified in Nightly?**: Yes
* **Needs manual test from QE?**: No
* **If yes, steps to reproduce**: 
* **List of other uplifts needed**: None
* **Risk to taking this patch**: Low
* **Why is the change risky/not risky? (and alternatives if risky)**: Very small and local change.
* **String changes made/needed**: N/A
* **Is Android affected?**: Yes

---

**Comment 14 — bugmon@mozilla.com — 2024-01-25T08:22:49Z**

Verified bug as fixed on rev mozilla-central 20240124211633-150dd33322ea.
Removing bugmon keyword as no further action possible.  Please review the bug and re-add the keyword for further analysis.

---

**Comment 15 — pascalc@gmail.com — 2024-01-25T19:55:17Z**

Comment on attachment 9375790
Bug 1875795 - Take scratch2 from register set before creating LiveRegisterSet. r?iain!

Approved for 123 beta 3, thanks.

---

**Comment 16 — pascalc@gmail.com — 2024-01-25T20:00:17Z**

https://hg.mozilla.org/releases/mozilla-beta/rev/390710073437

---

**Comment 17 — ryanvm@gmail.com — 2024-02-09T02:16:14Z**

Comment on attachment 9375790
Bug 1875795 - Take scratch2 from register set before creating LiveRegisterSet. r?iain!

Approved for 115.8esr.

---

**Comment 18 — pulsebot@bmo.tld — 2024-02-09T02:23:08Z**

https://hg.mozilla.org/releases/mozilla-esr115/rev/1ac9eb59196a

---

**Comment 19 — release-mgmt-account-bot@mozilla.tld — 2024-04-02T12:01:01Z**

2 months ago, tjr placed a reminder on the bug using the whiteboard tag `[reminder-test 2024-04-02]` .

jandem, please refer to the original comment to better understand the reason for the reminder.

---

**Comment 20 — pulsebot@bmo.tld — 2024-04-03T10:07:23Z**

Pushed by jdemooij@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/8d5656c605fc
Add test and assertion. r=iain

---

**Comment 21 — ryanvm@gmail.com — 2024-04-04T03:51:34Z**

https://hg.mozilla.org/mozilla-central/rev/8d5656c605fc
