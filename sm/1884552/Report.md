# Assertion failure: ins->isGoto(), at jit/IonAnalysis.cpp:715

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1884552
CVE: CVE-2024-3854
Component: JavaScript Engine: JIT
Bounty: (unknown)
Date: 2024-03-10T06:29:19Z
Keywords: csectype-jit, reporter-external, sec-high

Steps to reproduce:

On git commit e23c37371147c5ff5ac7d825ccaa90e096cd036e the attached sample asserts in the js-shell when invoked as `obj-x86_64-pc-linux-gnu/dist/bin/js --fuzzing-safe crash.js`.

```
for (let i22 = 0, i23 = 10;
    (() => {
        for (let i26 = 0, i27 = 10;
            (() => {
                let v28 = i26 != i27;
                const v29 = v28 === i23;
                if (v29) {
                    v28 = v29;
                } else {
                    switch (this) {
                    }
                }
                return v28;
            })();
            ) {
        }
        return i22 < i23;
    })();
    ) {
}
```

```
#0  0x0000555558fd8d7b in UpdateTestSuccessors (alloc=..., block=0x7ffff569f3f8, value=0x7ffff569eb20, ifTrue=0x7ffff56a0130, 
    ifFalse=0x7ffff56a0b78, existingPred=0x7ffff569fc98) at js/src/jit/IonAnalysis.cpp:715
#1  0x0000555558fd7864 in MaybeFoldDiamondConditionBlock (graph=..., initialBlock=0x7ffff569e2e8)
    at js/src/jit/IonAnalysis.cpp:862
#2  0x0000555558fa8533 in MaybeFoldConditionBlock (graph=..., initialBlock=0x7ffff569e2e8)
    at js/src/jit/IonAnalysis.cpp:1095
#3  0x0000555558fa8475 in js::jit::FoldTests (graph=...) at js/src/jit/IonAnalysis.cpp:1294
#4  0x0000555558ee1af1 in js::jit::OptimizeMIR (mir=0x7ffff569b180) at js/src/jit/Ion.cpp:1037
#5  0x0000555558ee384a in js::jit::CompileBackEnd (mir=0x7ffff569b180, snapshot=0x7ffff569b6a0)
    at js/src/jit/Ion.cpp:1605
#6  0x0000555558fc9287 in js::jit::IonCompileTask::runTask (this=0x7ffff569b718)
    at js/src/jit/IonCompileTask.cpp:52
#7  0x0000555558fc91b6 in js::jit::IonCompileTask::runHelperThreadTask (this=0x7ffff569b718, locked=...)
    at js/src/jit/IonCompileTask.cpp:30
#8  0x0000555557d769d0 in js::GlobalHelperThreadState::runTaskLocked (this=0x7ffff7618400, task=0x7ffff569b718, locked=...)
    at js/src/vm/HelperThreads.cpp:1728
#9  0x0000555557d767ab in js::GlobalHelperThreadState::runOneTask (this=0x7ffff7618400, lock=...)
    at js/src/vm/HelperThreads.cpp:1697
#10 0x0000555557db61c8 in js::HelperThread::threadLoop (this=0x7ffff7627420, pool=0x7ffff7623100)
    at js/src/vm/InternalThreadPool.cpp:282
#11 0x0000555557db6022 in js::HelperThread::ThreadMain (pool=0x7ffff7623100, helper=0x7ffff7627420)
    at js/src/vm/InternalThreadPool.cpp:225
#12 0x0000555557dde732 in js::detail::ThreadTrampoline<void (&)(js::InternalThreadPool*, js::HelperThread*), js::InternalThreadPool*&, js::HelperThread*>::callMain<0ul, 1ul> (this=0x7ffff760f5f0) at js/src/threading/Thread.h:228
#13 0x0000555557dde57b in js::detail::ThreadTrampoline<void (&)(js::InternalThreadPool*, js::HelperThread*), js::InternalThreadPool*&, js::HelperThread*>::Start (aPack=0x7ffff760f5f0) at js/src/threading/Thread.h:217
#14 0x00007ffff7897b5a in start_thread (arg=<optimized out>) at ./nptl/pthread_create.c:444
#15 0x00007ffff79285fc in clone3 () at ../sysdeps/unix/sysv/linux/x86_64/clone3.S:78
```

---

**Comment 1 — lukas.bernhard@rub.de — 2024-03-10T08:17:33Z**

This seems to be a long-standing issue; commit c9b61e116965bcf35c96a56f36de1b487aba1699 from Feb 24 2022 is affected already.

---

**Comment 2 — nicolas.b.pierron@mozilla.com — 2024-03-12T16:29:27Z**

I am not able to find any non-OOM related crashes under `UpdateTestSuccessors`, which suggests that if we do not crash with the current assertion, then we might be generating some dangling pointers in our MIR graph.

Looking at the test case this might be related to the empty switch statement, generated from WarpBuilder.

---

**Comment 3 — iireland@mozilla.com — 2024-03-13T07:02:36Z**

This is an interesting one. Here's a simpler test case:
```
function inner(cond) {
  var x;
  if (cond) {
    x = 0;
  } else {
    x = 1;
    switch (this) {}
  }
  return x;
}

function outer(cond) {
  var x;
  if (inner(cond)) {
    return 1;
  } else {
    return 2;
  }
}

with ({}) {}
for (var i = 0; i < 1000; i++) {
  outer(true);
  outer(false);
}
```

The problem is in [MaybeFoldDiamondConditionBlock](https://searchfox.org/mozilla-central/rev/b189986e26a92f749462094e7869771c1a6607c0/js/src/jit/IonAnalysis.cpp#770-794). We're looking for this pattern:
```
        initialBlock
          /     \
  trueBranch  falseBranch
          \     /
          phiBlock
             |
         testBlock
          /     \
```
If testBlock will branch based on a phi in phiBlock, then we can remove phiBlock and testBlock, and instead jump straight from trueBranch and falseBranch to the correct location. Importantly, when matching trueBranch and falseBranch, we only verify that they have the right number of incoming and outgoing edges, and not the actual control instruction. If we stick an empty switch statement in falseBranch (or theoretically trueBranch, although I haven't gotten that version to fail yet), then everything will work right up until we hit [this code](https://searchfox.org/mozilla-central/rev/b189986e26a92f749462094e7869771c1a6607c0/js/src/jit/IonAnalysis.cpp#715-729) in UpdateTestSuccessors, which wants to rewrite the end of falseBranch. It assumes that any block that's reached this point with a single successor must end in a goto. However, in this case we actually have a degenerate switch. We assert.

In a non-debug build, we incorrectly cast the MTableSwitch into an MGoto and try to load the target out of it. If my quick comparison of offsets is correct, we end up treating the pointer to the backing buffer of the switch's successors vector as if it were the target itself, then pass it to removePredecessor, where we read a variety of fields from it. I'm going to conservatively assume that it's somehow exploitable. 

One easy fix might be to rewrite [these tests](https://searchfox.org/mozilla-central/rev/b189986e26a92f749462094e7869771c1a6607c0/js/src/jit/IonAnalysis.cpp#749-758) to check that the last instruction is a goto, instead of the number of successors. AFAICT, MGoto and MTableSwitch are the only control instructions that can have a single successor: MTest always has two, and the other control instructions (MReturn, MUnreachable, etc...) have zero.

Anba rewrote this code in bug 1767966, but as far as I can tell the necessary conditions for this bug were already present when this optimization was first added in bug 1028580. Maybe we would have generated slightly different MIR pre-Warp.

---

**Comment 4 — iireland@mozilla.com — 2024-03-13T20:01:04Z**

Created attachment 9391110
Bug 1884552: Refactor IsDiamondPattern r=jandem

---

**Comment 5 — iireland@mozilla.com — 2024-03-13T20:01:14Z**

Created attachment 9391111
Bug 1884552: Add testcase r=jandem

---

**Comment 6 — iireland@mozilla.com — 2024-03-14T16:29:31Z**

Comment on attachment 9391110
Bug 1884552: Refactor IsDiamondPattern r=jandem

### Security Approval Request
* **How easily could an exploit be constructed based on the patch?**: Medium difficulty. It isn't too hard to work out that the only thing this patch changes is how we handle TableSwitch nodes. After that it requires a bit of cleverness with inlining to trigger the bug, and then whatever work is necessary to turn some out-of-bounds reads into an exploit.
* **Do comments in the patch, the check-in comment, or tests included in the patch paint a bulls-eye on the security problem?**: No
* **Which branches (beta, release, and/or ESR) are affected by this flaw, and do the release status flags reflect this affected/unaffected state correctly?**: All, and yes
* **If not all supported branches, which bug introduced the flaw?**: None
* **Do you have backports for the affected branches?**: No
* **If not, how different, hard to create, and risky will they be?**: The patch should apply cleanly to all supported branches.
* **How likely is this patch to cause regressions; how much testing does it need?**: Unlikely. It should not have any effect outside of the buggy case.
* **Is the patch ready to land after security approval is given?**: Yes
* **Is Android affected?**: Yes

---

**Comment 7 — tom@mozilla.com — 2024-03-21T15:44:54Z**

Comment on attachment 9391110
Bug 1884552: Refactor IsDiamondPattern r=jandem

sec-approvals were paused for a few days after merge, thanks for the patience.  approved to land and uplift

---

**Comment 8 — pulsebot@bmo.tld — 2024-03-21T16:24:23Z**

Pushed by iireland@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/cf42085d7c1d
Refactor IsDiamondPattern r=jandem

---

**Comment 9 — aryx.bugmail@gmx-topmail.de — 2024-03-21T21:27:09Z**

https://hg.mozilla.org/mozilla-central/rev/cf42085d7c1d

---

**Comment 10 — iireland@mozilla.com — 2024-03-21T21:44:52Z**

Comment on attachment 9391110
Bug 1884552: Refactor IsDiamondPattern r=jandem

### ESR Uplift Approval Request
* **If this is not a sec:{high,crit} bug, please state case for ESR consideration**: Sec-high
* **User impact if declined**: Potentially exploitable type confusion during Ion compilation
* **Fix Landed on Version**: 126
* **Risk to taking this patch**: Low
* **Why is the change risky/not risky? (and alternatives if risky)**: This patch replaces one check with a different check that should be the same in every case except the buggy case.

### Beta/Release Uplift Approval Request
* **User impact if declined**: Potentially exploitable type confusion during Ion compilation
* **Is this code covered by automated tests?**: Yes
* **Has the fix been verified in Nightly?**: Yes
* **Needs manual test from QE?**: No
* **If yes, steps to reproduce**: None
* **List of other uplifts needed**: None
* **Risk to taking this patch**: Low
* **Why is the change risky/not risky? (and alternatives if risky)**: This patch replaces one check with a different check that should be the same in every case except the buggy case.
* **String changes made/needed**: None
* **Is Android affected?**: Yes

---

**Comment 11 — ryanvm@gmail.com — 2024-03-22T15:04:16Z**

Comment on attachment 9391110
Bug 1884552: Refactor IsDiamondPattern r=jandem

Approved for 125.0b4 and 115.10esr.

---

**Comment 12 — pulsebot@bmo.tld — 2024-03-22T15:05:40Z**

https://hg.mozilla.org/releases/mozilla-esr115/rev/928b0540e421

---

**Comment 13 — pulsebot@bmo.tld — 2024-03-22T15:44:21Z**

https://hg.mozilla.org/releases/mozilla-beta/rev/b5a9b2119a23

---

**Comment 14 — dveditz@mozilla.com — 2024-04-15T09:50:25Z**

Created attachment 9396625
advisory.txt

---

**Comment 15 — release-mgmt-account-bot@mozilla.tld — 2024-05-28T12:01:06Z**

2 months ago, tjr placed a reminder on the bug using the whiteboard tag `[reminder-test 2024-05-28]` .

iain, please refer to the original comment to better understand the reason for the reminder.

---

**Comment 16 — pulsebot@bmo.tld — 2024-05-28T21:46:31Z**

Pushed by sstanca@mozilla.com:
https://hg.mozilla.org/mozilla-central/rev/147fdd4c5ddb
Add testcase r=jandem

---

**Comment 17 — aryx.bugmail@gmx-topmail.de — 2024-05-28T22:01:35Z**

https://hg.mozilla.org/mozilla-central/rev/147fdd4c5ddb
