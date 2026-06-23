# Assertion failure: pred->isLoopBackedge(), at jit/IonAnalysis.cpp:3503 or Crash [@ ??] or Crash [@ js::jit::BacktrackingAllocator::go]

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1919246
Component: JavaScript Engine: JIT
Bounty: (unknown)
Date: 2024-09-17T10:09:41Z
Keywords: assertion, crash, csectype-jit, regression, sec-high, testcase

The following testcase crashes on mozilla-central revision 20240917-f7ef18cdcabb (debug build, run with --fuzzing-safe --ion-offthread-compile=off):

    gczeal(9, 7)
    while(true)
      for (let a = 2; a;) {
          b = toString;
          Promise;
          for (c = 0; c < 10;);
      }


Backtrace:

    received signal SIGSEGV, Segmentation fault.
    #0  0x0000555557fd3ad3 in js::jit::AssertGraphCoherency(js::jit::MIRGraph&, bool) ()
    #1  0x0000555557fd4e80 in js::jit::AssertExtendedGraphCoherency(js::jit::MIRGraph&, bool, bool) ()
    #2  0x0000555557fcf32e in js::jit::OptimizeMIR(js::jit::MIRGenerator*) ()
    #3  0x0000555557fdb6f5 in js::jit::CompileBackEnd(js::jit::MIRGenerator*, js::jit::WarpSnapshot*) ()
    #4  0x0000555557fdcc56 in js::jit::Compile(JSContext*, JS::Handle<JSScript*>, js::jit::BaselineFrame*, unsigned char*) ()
    #5  0x0000555557fdd763 in IonCompileScriptForBaseline(JSContext*, js::jit::BaselineFrame*, unsigned char*) ()
    #6  0x0000555557fde0aa in js::jit::IonCompileScriptForBaselineOSR(JSContext*, js::jit::BaselineFrame*, unsigned int, unsigned char*, js::jit::IonOsrTempData**) ()
    #7  0x00003b1a51e3dcd6in ?? ()
    #8  0x0000000000000000 in ?? ()
    rax	0x5555558384b4	93824995263668
    rbx	0x7ffff3d82068	140737284415592
    rcx	0x5555588b7fd0	93825046118352
    rdx	0x0	0
    rsi	0x7ffff7105770	140737338431344
    rdi	0x7ffff7104540	140737338426688
    rbp	0x7fffffffc560	140737488340320
    rsp	0x7fffffffc530	140737488340272
    r8	0x7ffff7105770	140737338431344
    r9	0x7ffff7f92840	140737353689152
    r10	0x0	0
    r11	0x0	0
    r12	0xffffffff	4294967295
    r13	0x2	2
    r14	0x7ffff3d85570	140737284429168
    r15	0x7ffff3d86360	140737284432736
    rip	0x555557fd3ad3 <js::jit::AssertGraphCoherency(js::jit::MIRGraph&, bool)+771>
    => 0x555557fd3ad3 <_ZN2js3jit20AssertGraphCoherencyERNS0_8MIRGraphEb+771>:	movl   $0xdaf,0x0
       0x555557fd3ade <_ZN2js3jit20AssertGraphCoherencyERNS0_8MIRGraphEb+782>:	callq  0x555556f21380 <abort>

---

**Comment 1 — choller@mozilla.com — 2024-09-17T10:09:45Z**

Created attachment 9425242
Detailed Crash Information

---

**Comment 2 — choller@mozilla.com — 2024-09-17T10:09:47Z**

Created attachment 9425243
Testcase

---

**Comment 3 — choller@mozilla.com — 2024-09-17T10:46:24Z**

This is an automated crash issue comment:

Summary: Crash [@ ??]
Build version: mozilla-central revision 20240917-f7ef18cdcabb
Build type: opt
Runtime options: --fuzzing-safe --ion-offthread-compile=off --ion-warmup-threshold=10 --fast-warmup --blinterp-warmup-threshold=1

Testcase:

    a = ["", "", ""]
    function b() {
        return [{}, Date]
    }
    c = [[]]
    for (d in c) {
        e = b()
        for (f in e) {
            try {
                [] = g
            } catch {}
            for (h in a);
        }
    }

Backtrace:

    received signal SIGSEGV, Segmentation fault.
    0x00001405816daa0a in ?? ()
    #0  0x00001405816daa0a in ?? ()
    #1  0x0000000000000000 in ?? ()
    rax	0xfffe1c7372d3d100	-531667780120320
    rbx	0xfffe1c7372d3d0b0	-531667780120400
    rcx	0xfffa800000000001	-1548112371908607
    rdx	0x1c7372d3d038	31282173300792
    rsi	0xfffb1c7372d04660	-1376092710484384
    rdi	0x1c7372d3d100	31282173300992
    rbp	0x7fffffffbe90	140737488338576
    rsp	0x7fffffffbe50	140737488338512
    r8	0xfffb1c7372d04640	-1376092710484416
    r9	0xfffe1c7372d3d088	-531667780120440
    r10	0xfffb1c7372d04640	-1376092710484416
    r11	0x1fff5	131061
    r12	0xfffe1c7372d3d088	-531667780120440
    r13	0x0	0
    r14	0x0	0
    r15	0x0	0
    rip	0x1405816daa0a	22013878839818
    => 0x1405816daa0a:	mov    0x18(%rcx),%rax
       0x1405816daa0e:	testl  $0x8,0x3c(%rax)

---

**Comment 4 — jdemooij@mozilla.com — 2024-09-17T14:47:53Z**

Created attachment 9425332
Bug 1919246 - Back out D221953 and add tests. r?mgaudet!


For now back out D221953 because it was an optional change to improve codegen a bit
for loops that contain an OSR loop, but it's probably not worth the complexity to
try to handle this.

---

**Comment 5 — jdemooij@mozilla.com — 2024-09-17T14:49:08Z**

This is a regression from bug 1917817 part 1. OSR can result in weird graph structures apparently not covered by tests. Let's revert that change for now.

---

**Comment 6 — release-mgmt-account-bot@mozilla.tld — 2024-09-17T15:43:01Z**

Set release status flags based on info from the regressing bug 1917817

---

**Comment 7 — pulsebot@bmo.tld — 2024-09-17T16:32:07Z**

Pushed by jdemooij@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/e88a00447043
Back out D221953 and add tests. r=mgaudet

---

**Comment 8 — bugmon@mozilla.com — 2024-09-17T18:52:38Z**

Verified bug as reproducible on mozilla-central 20240917155236-48a19540af0f.
The bug appears to have been introduced in the following build range:
> Start: 6c6355062108adfdf3ab84be595c02462419b56b (20240916090815)
> End: b98486f0aad5d732a1733ceffad17b1dc5abc552 (20240916114729)
> Pushlog: https://hg.mozilla.org/integration/autoland/pushloghtml?fromchange=6c6355062108adfdf3ab84be595c02462419b56b&tochange=b98486f0aad5d732a1733ceffad17b1dc5abc552

---

**Comment 9 — aryx.bugmail@gmx-topmail.de — 2024-09-18T08:05:39Z**

https://hg.mozilla.org/mozilla-central/rev/e88a00447043

---

**Comment 10 — bugmon@mozilla.com — 2024-09-18T16:43:59Z**

Verified bug as fixed on rev mozilla-central 20240918041351-6f33b896b26b.
Removing bugmon keyword as no further action possible.  Please review the bug and re-add the keyword for further analysis.

---

**Comment 11 — twsmith@mozilla.com — 2024-09-19T19:38:27Z**

This was detected by live site testing.
