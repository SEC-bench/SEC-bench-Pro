# Crash [@ js::jit::CacheIRWriter::loadArgumentFixedSlot] or Assertion failure: slotIndex <= (255), at jit/CacheIRWriter.h:497

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1926235
Component: JavaScript Engine: JIT
Bounty: (unknown)
Date: 2024-10-22T09:14:34Z
Keywords: assertion, crash, csectype-bounds, regression, sec-high, testcase

The following testcase crashes on mozilla-central revision 20241022-c47ccf99a981 (opt build, run with --fuzzing-safe --ion-offthread-compile=off --blinterp-eager):

    x = [012345];
    for (let i = 6; i < 260; ++i) {
      x.push(i % 10);
    }
    eval(`
    (new Date().getTime(${x}))
    `);


Backtrace:

    received signal SIGSEGV, Segmentation fault.
    #0  0x0000555556eb72a7 in js::jit::CacheIRWriter::loadArgumentFixedSlot(js::jit::ArgumentKind, unsigned int, js::jit::CallFlags) ()
    #1  0x0000555556e6653f in js::jit::InlinableNativeIRGenerator::emitNativeCalleeGuard() ()
    #2  0x0000555556e9f87a in js::jit::InlinableNativeIRGenerator::tryAttachStub() ()
    #3  0x0000555556e83176 in js::jit::CallIRGenerator::tryAttachStub() ()
    #4  0x0000555556e80ca4 in js::jit::DoCallFallback(JSContext*, js::jit::BaselineFrame*, js::jit::ICFallbackStub*, unsigned int, JS::Value*, JS::MutableHandle<JS::Value>) ()
    #5  0x00000a84fbb1d8c4 in ?? ()
    [...]
    #127 0xfff8800000000005 in ?? ()
    rax	0x55555662290a	93825009854730
    rbx	0x7fffffff8c68	140737488325736
    rcx	0x100	256
    rdx	0xff	255
    rsi	0x0	0
    rdi	0x7fffffff8e18	140737488326168
    rbp	0x7fffffff89f0	140737488325104
    rsp	0x7fffffff89b0	140737488325040
    r8	0xff	255
    r9	0x7fffffff8c30	140737488325680
    r10	0xfffdffffffffffff	-562949953421313
    r11	0x7fffffff8e18	140737488326168
    r12	0x100	256
    r13	0x0	0
    r14	0x2b	43
    r15	0x7fffffff8c68	140737488325736
    rip	0x555556eb72a7 <js::jit::CacheIRWriter::loadArgumentFixedSlot(js::jit::ArgumentKind, unsigned int, js::jit::CallFlags)+775>
    => 0x555556eb72a7 <_ZN2js3jit13CacheIRWriter21loadArgumentFixedSlotENS0_12ArgumentKindEjNS0_9CallFlagsE+775>:	movl   $0x1f1,0x0
       0x555556eb72b2 <_ZN2js3jit13CacheIRWriter21loadArgumentFixedSlotENS0_12ArgumentKindEjNS0_9CallFlagsE+786>:	callq  0x555557156c80 <abort>


Marking s-s because this looks like a JIT related issue with potential oob slot. The original testcase had all the ~260 args specified manually, I wasn't able to use the spread operator to get it to reproduce so I resorted to use eval instead.

---

**Comment 1 — choller@mozilla.com — 2024-10-22T09:14:38Z**

Created attachment 9432465
Detailed Crash Information

---

**Comment 2 — choller@mozilla.com — 2024-10-22T09:14:40Z**

Created attachment 9432466
Testcase

---

**Comment 3 — jdemooij@mozilla.com — 2024-10-22T11:08:20Z**

anba, do you have time to look at this? If not I can write a patch.

---

**Comment 4 — dmeehan@mozilla.com — 2024-10-22T12:41:11Z**

(In reply to Jan de Mooij [:jandem] from comment #3)
> anba, do you have time to look at this? If not I can write a patch.

Is Bug 1925195 the bug that introduced this?

---

**Comment 5 — jdemooij@mozilla.com — 2024-10-22T12:43:14Z**

(In reply to Donal Meehan [:dmeehan] from comment #4)
> Is Bug 1925195 the bug that introduced this?

Correct.

---

**Comment 6 — andrebargull@googlemail.com — 2024-10-22T12:47:18Z**

Created attachment 9432524
Bug 1926235: Add missing argument length checks. r=jandem!

---

**Comment 7 — continuation@gmail.com — 2024-10-22T14:33:41Z**

It sounds like a missing bounds check, so I'm going to mark this sec-high.

---

**Comment 8 — pulsebot@bmo.tld — 2024-10-22T15:40:04Z**

Pushed by andre.bargull@gmail.com:
https://hg.mozilla.org/integration/autoland/rev/c64a2d656aae
Add missing argument length checks. r=jandem

---

**Comment 9 — bugmon@mozilla.com — 2024-10-22T16:27:45Z**

Verified bug as reproducible on mozilla-central 20241022095236-1fc2a51d27a0.
The bug appears to have been introduced in the following build range:
> Start: ba91ce2c95666a6ff904d181bac8c88595921025 (20241017120809)
> End: 900f5e31f7486084f273b91beb484bf7b67bc6f5 (20241017132946)
> Pushlog: https://hg.mozilla.org/integration/autoland/pushloghtml?fromchange=ba91ce2c95666a6ff904d181bac8c88595921025&tochange=900f5e31f7486084f273b91beb484bf7b67bc6f5

---

**Comment 10 — aryx.bugmail@gmx-topmail.de — 2024-10-22T21:38:45Z**

https://hg.mozilla.org/mozilla-central/rev/c64a2d656aae

---

**Comment 11 — bugmon@mozilla.com — 2024-10-23T08:21:05Z**

Verified bug as fixed on rev mozilla-central 20241022213158-c71b36339200.
Removing bugmon keyword as no further action possible.  Please review the bug and re-add the keyword for further analysis.
