# Assertion failure: ins->compareType() == MCompare::Compare_String, at js/src/jit/MIR.cpp:3847

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1736307
Component: JavaScript Engine: JIT
Bounty: (unknown)
Date: 2021-10-18T08:23:17Z
Keywords: assertion, csectype-jit, regression, sec-high, testcase

The following testcase crashes on mozilla-central revision 20211017-5e4047061e46 (debug build, run with --fuzzing-safe --ion-offthread-compile=off):

    b = undefined;
    function c() {
        c(typeof Uint16Array == b);
    }
    c();


Backtrace:

    received signal SIGSEGV, Segmentation fault.
    #0  0x0000555557b0d9d9 in IsTypeOfCompare(js::jit::MCompare*) ()
    #1  0x0000555557b0d605 in js::jit::MCompare::tryFoldTypeOf(bool*) ()
    #2  0x0000555557b0db03 in js::jit::MCompare::tryFold(bool*) ()
    #3  0x0000555557b0f1ad in js::jit::MCompare::foldsTo(js::jit::TempAllocator&) ()
    #4  0x0000555557735f45 in js::jit::ValueNumberer::visitDefinition(js::jit::MDefinition*) ()
    #5  0x0000555557737465 in js::jit::ValueNumberer::visitBlock(js::jit::MBasicBlock*) ()
    #6  0x000055555773782d in js::jit::ValueNumberer::visitDominatorTree(js::jit::MBasicBlock*) ()
    #7  0x0000555557737bd3 in js::jit::ValueNumberer::visitGraph() ()
    #8  0x0000555557738aac in js::jit::ValueNumberer::run(js::jit::ValueNumberer::UpdateAliasAnalysisFlag) ()
    #9  0x0000555557a24969 in js::jit::OptimizeMIR(js::jit::MIRGenerator*) ()
    #10 0x0000555557a2dc4c in js::jit::CompileBackEnd(js::jit::MIRGenerator*, js::jit::WarpSnapshot*) ()
    #11 0x0000555557a2f4e2 in js::jit::Compile(JSContext*, JS::Handle<JSScript*>, js::jit::BaselineFrame*, unsigned char*) ()
    #12 0x0000555557a2ff2a in IonCompileScriptForBaseline(JSContext*, js::jit::BaselineFrame*, unsigned char*) ()
    #13 0x000002c4d31f8575 in ?? ()
    #14 0x0000000000000000 in ?? ()
    rax	0x55555577db4f	93824994499407
    rbx	0x7ffffffb4d40	140737488047424
    rcx	0x555558163d90	93825038433680
    rdx	0x0	0
    rsi	0x7ffff7105770	140737338431344
    rdi	0x7ffff7104540	140737338426688
    rbp	0x7ffffffb4d30	140737488047408
    rsp	0x7ffffffb4d10	140737488047376
    r8	0x7ffff7105770	140737338431344
    r9	0x7ffff7f99840	140737353717824
    r10	0x0	0
    r11	0x0	0
    r12	0x7ffffffb5018	140737488048152
    r13	0x7ffff60cd701	140737321424641
    r14	0x7ffffffb4dcf	140737488047567
    r15	0x7ffff60cd780	140737321424768
    rip	0x555557b0d9d9 <IsTypeOfCompare(js::jit::MCompare*)+473>
    => 0x555557b0d9d9 <_ZL15IsTypeOfComparePN2js3jit8MCompareE+473>:	movl   $0xf07,0x0
       0x555557b0d9e4 <_ZL15IsTypeOfComparePN2js3jit8MCompareE+484>:	callq  0x555556b163ee <abort>


Marking s-s because this is a JIT/MIR assertion. This is also a fuzzblocker as it seems to trigger really easy with infinite loops or over-recursion.

---

**Comment 1 — choller@mozilla.com — 2021-10-18T08:23:19Z**

Created attachment 9246372
Detailed Crash Information

---

**Comment 2 — choller@mozilla.com — 2021-10-18T08:23:20Z**

Created attachment 9246373
Testcase

---

**Comment 3 — jdemooij@mozilla.com — 2021-10-18T08:31:46Z**

Probably related to bug 725966.

---

**Comment 4 — andrebargull@googlemail.com — 2021-10-18T09:18:42Z**

Yes, that was dumb braino. That assertion should have been an `if`-statement. Interesting that now existing tests cover that case..

---

**Comment 5 — andrebargull@googlemail.com — 2021-10-18T11:36:12Z**

Created attachment 9246402
Bug 1736307: Properly test for string comparisons. r=jandem!

---

**Comment 6 — bugmon@mozilla.com — 2021-10-18T16:19:08Z**

**Bugmon Analysis**
Verified bug as reproducible on mozilla-central 20211018095159-63d10a00d256.
The bug appears to have been introduced in the following build range:
> Start: 7f19b67559304c4e222bd419804cdb1c32f57c61 (20211014175039)
> End: 4cc431f61ab073a2558da9ebb4a79579a217889a (20211014180318)
> Pushlog: https://hg.mozilla.org/integration/autoland/pushloghtml?fromchange=7f19b67559304c4e222bd419804cdb1c32f57c61&tochange=4cc431f61ab073a2558da9ebb4a79579a217889a

---

**Comment 7 — continuation@gmail.com — 2021-10-18T17:27:49Z**

I'll assume this is sec-high because it is some kind of type confusion, but feel free to adjust as necessary.

---

**Comment 8 — andrebargull@googlemail.com — 2021-10-18T20:06:44Z**

Combined with bug 1736043, this shouldn't actually be too bad:

This specific case can only be triggered when one operand is either `null`, `undefined`, or a BigInt value and the other operand is a `typeof` expression. Any other combination won't be able to trigger this bug. Because of bug 1736043, we're only interpreting a null/undefined/BigInt value as a `JSString*` and are then comparing that `JSString*` pointer with another `JSAtom*` pointer. That shouldn't actually be exploitable in any way, correct?

---

**Comment 9 — release-mgmt-account-bot@mozilla.tld — 2021-10-19T12:14:51Z**

Set release status flags based on info from the regressing bug 725966

---

**Comment 10 — andrebargull@googlemail.com — 2021-10-22T08:04:03Z**

I think because of the reasons outlined in comment #8, it should be okay to simply land the patch. Anyone disagreeing?

---

**Comment 11 — jdemooij@mozilla.com — 2021-10-22T08:20:38Z**

(In reply to André Bargull [:anba] from comment #10)
> I think because of the reasons outlined in comment #8, it should be okay to simply land the patch. Anyone disagreeing?

It should be fine to land without sec-approval also because it's a recent Nightly-only regression. See [here](https://firefox-source-docs.mozilla.org/bug-mgmt/processes/security-approval.html#on-requesting-sec-approval).

---

**Comment 12 — andrebargull@googlemail.com — 2021-10-22T08:31:24Z**

Thanks for the info!

---

**Comment 13 — aryx.bugmail@gmx-topmail.de — 2021-10-22T15:50:45Z**

Properly test for string comparisons. r=jandem
https://hg.mozilla.org/integration/autoland/rev/d8f24053c3412fb900c927f3da44f659e4a063d1
https://hg.mozilla.org/mozilla-central/rev/d8f24053c341

---

**Comment 14 — bugmon@mozilla.com — 2021-10-22T16:14:23Z**

**Bugmon Analysis**
Verified bug as fixed on rev mozilla-central 20211022154501-91860dc63199.
Removing bugmon keyword as no further action possible.  Please review the bug and re-add the keyword for further analysis.

---

**Comment 15 — release-mgmt-account-bot@mozilla.tld — 2021-10-27T17:00:09Z**

As part of a security bug pattern analysis, we are requesting your help with a high level analysis of this bug. It is our hope to develop static analysis (or potentially runtime/dynamic analysis) in the future to identify classes of bugs.

Please visit [this google form](https://docs.google.com/forms/d/e/1FAIpQLSe9uRXuoMK6tRglbNL5fpXbun_oEb6_xC2zpuE_CKA_GUjrvA/viewform?usp=pp_url&entry.2124261401=https%3A%2F%2Fbugzilla.mozilla.org%2Fshow_bug.cgi%3Fid%3D1736307) to reply.
