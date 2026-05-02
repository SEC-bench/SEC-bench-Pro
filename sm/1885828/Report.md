# Wild pointer-deref from jitted code

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1885828
CVE: CVE-2024-3855
Component: JavaScript Engine: JIT
Bounty: (unknown)
Date: 2024-03-18T06:45:46Z
Keywords: csectype-jit, regression, reporter-external, sec-high

Steps to reproduce:

On git commit 6d5114b3ba4e5c3414a19419ca1d0170ca149b13 the attached sample crashes the js-shell when invoked as `obj-x86_64-pc-linux-gnu/dist/bin/js --fast-warmup --fuzzing-safe crash.js`. The crash is caused by a wild pointer deref from jitted code; e.g. when attempting to access `0x9cc00d6602f`.
I'm running a bisect now and will provide an update regarding the regression range.

```
function f9(a10) {
    for (let i13 = 1000; i13-- > 0;) {
        (`(f32.neg`).slice(a10).search(undefined);
    }   
}
f9(1);
f9(-1);
```

```
(gdb) x/i $rip
=> 0x2e17391d924d:	movzx  r10d,WORD PTR [r12]
(gdb) i r r12
r12            0x9cc00d6602f       10771792027695
(gdb) x/x 0x9cc00d6602f
0x9cc00d6602f:	Cannot access memory at address 0x9cc00d6602f


#0  0x00002e17391d924d in ?? ()
#1  0x0000000000000001 in ?? ()
#2  0x000009cb00d63040 in ?? ()
#3  0x00007fffffffc630 in ?? ()
#4  0x00007ffff4f7d600 in ?? ()
#5  0x00007fff00000000 in ?? ()
#6  0x00005555590de150 in ?? ()
#7  0xfff8000100000072 in ?? ()
#8  0x00005555590de210 in JSFunctionClassSpec ()
#9  0x00000001ffffc170 in ?? ()
#10 0x000055555814ea13 in js::BaseScript::sourceStart (this=<optimized out>)
    at js/src/jit/JitHints-inl.h:21
#11 js::jit::JitHintsMap::getScriptKey (this=<optimized out>, script=0xffffffff)
    at js/src/jit/JitHints-inl.h:22
#12 0x00002e17391577a5 in ?? ()
#13 0x0000000000000025 in ?? ()
#14 0x00001048bc800650 in ?? ()
#15 0xfff9800000000000 in ?? ()
#16 0xfff88000ffffffff in ?? ()
#17 0xfff9800000000000 in ?? ()
#18 0xfff9800000000000 in ?? ()
#19 0x00007fffffffc220 in ?? ()
#20 0x00002e1739157d81 in ?? ()
#21 0x0000000000000023 in ?? ()
#22 0x00001048bc800650 in ?? ()
#23 0xfff9800000000000 in ?? ()
#24 0xfff88000ffffffff in ?? ()
#25 0x00007fffffffc290 in ?? ()
#26 0x00002e1739157720 in ?? ()
#27 0x00007ffff6039100 in ?? ()
#28 0x00002e1739157c10 in ?? ()
#29 0x0000000000000002 in ?? ()
#30 0x00007fffffffc630 in ?? ()
#31 0x00007fffffffc580 in ?? ()
#32 0x0000555558803ae6 in EnterJit (cx=0x7fffffffc190, state=..., 
    code=0xfff9800000000000 <error: Cannot access memory at address 0xfff9800000000000>)
    at js/src/jit/Jit.cpp:115
#33 js::jit::MaybeEnterJit (cx=0x7fffffffc190, state=...) at js/src/jit/Jit.cpp:261
```

---

**Comment 1 — lukas.bernhard@rub.de — 2024-03-18T09:02:48Z**

Bisecting points to commit 426f62bd4988594fb63e655baee99f237887804e related to bug 1861983

---

**Comment 2 — andrebargull@googlemail.com — 2024-03-18T09:49:35Z**

This is the old issue that we allow to hoist instructions before guard-like instructions. In this case we hoist the `std_Math_max`, `std_Math_min`, and `SubstringKernel` calls from `String_slice` outside the loop, but keep the never executed `a10 < 0` inside the loop. In the JS code, `a10 < 0` acts like a guard-like instruction, but when compiling we ignore this and happily reorder all following instructions before `a10 < 0`. That means we execute something like:
```js
var str = `(f32.neg`;
var from = std_Math_min(a10, str.length);
var span = std_Math_max(str.length - from, 0);
var sliced = SubstringKernel(str, from, span);
for (let i13 = 1000; i13-- > 0;) {
  if (a10 < 0) bail; // Bailout for never executed case.
  sliced.search(undefined);
}
```
When later calling `f9(-1)`, `a10` is negative, so we execute:
```js
var from = std_Math_min(a10, str.length) = min(-1, str.length) = -1
var span = std_Math_max(str.length - from, 0) = max(str.length - -1, 0) = str.length + 1
var sliced = SubstringKernel(str, from, span) = SubstringKernel(str, -1, str.length + 1); // <- OOB access
```

We'll have to back-out <https://phabricator.services.mozilla.com/D192220> to fix this issue.

---

**Comment 3 — andrebargull@googlemail.com — 2024-03-18T10:15:33Z**

Created attachment 9391709
Bug 1885828: Make MSubstr non-movable. r=jandem!

---

**Comment 4 — andrebargull@googlemail.com — 2024-03-18T10:15:42Z**

Created attachment 9391710
Bug 1885828: Add test case. r=jandem!



Depends on D204882

---

**Comment 5 — andrebargull@googlemail.com — 2024-03-18T13:15:53Z**

Created attachment 9391744
Bug 1885828: Make MSubstr non-movable. r=jandem!



Original Revision: https://phabricator.services.mozilla.com/D204882

---

**Comment 6 — phab-bot@bmo.tld — 2024-03-18T13:18:25Z**

# Uplift Approval Request
- **Risk associated with taking this patch**: Low
- **User impact if declined**: Possible to read out-of-bounds values through JIT code.
- **Steps to reproduce for manual QE testing**: None
- **Fix verified in Nightly**: no
- **Needs manual QE test**: no
- **Is Android affected?**: yes
- **String changes made/needed**: None
- **Code covered by automated testing**: yes
- **Explanation of risk level**: Low risk because it just reverts D192220.

---

**Comment 7 — andrebargull@googlemail.com — 2024-03-18T13:34:50Z**

Comment on attachment 9391744
Bug 1885828: Make MSubstr non-movable. r=jandem!

### Security Approval Request
* **How easily could an exploit be constructed based on the patch?**: The patch will give a hint which instruction is affected (`MSubstr`) and because there are only a limited number of uses (these [SubstringKernel](https://searchfox.org/mozilla-central/search?q=SubstringKernel&path=js%2Fsrc%2Fbuiltin&case=false&regexp=false) calls), an attacker can likely infer which functions have to be called. The `MSubstr` is reverted to be again non-movable, so an attacker can also infer that this is related to LICM (loop invariant code motion), so an exploit will have to contain some looping code. 

The test case to trigger this bug is relatively small, which can help an attacker to write an exploit. It's not trivial to piece these hints together to write an exploit, but it's also not too hard, because neither complicated interactions between multiple components nor things like exact GC timings are required.
* **Do comments in the patch, the check-in comment, or tests included in the patch paint a bulls-eye on the security problem?**: No
* **Which branches (beta, release, and/or ESR) are affected by this flaw, and do the release status flags reflect this affected/unaffected state correctly?**: Firefox 121
* **If not all supported branches, which bug introduced the flaw?**: Bug 1861983
* **Do you have backports for the affected branches?**: Yes
* **If not, how different, hard to create, and risky will they be?**: 
* **How likely is this patch to cause regressions; how much testing does it need?**: Unlikely to cause regressions, because it just reverts <https://phabricator.services.mozilla.com/D192220>.
* **Is the patch ready to land after security approval is given?**: Yes
* **Is Android affected?**: Yes

---

**Comment 8 — dveditz@mozilla.com — 2024-03-20T22:15:13Z**

*** Bug 1885781 has been marked as a duplicate of this bug. ***

---

**Comment 9 — tom@mozilla.com — 2024-03-21T15:52:33Z**

Comment on attachment 9391709
Bug 1885828: Make MSubstr non-movable. r=jandem!

sec-approvals were paused for a few days after merge, thanks for the patience.  approved to land and uplift

---

**Comment 10 — pulsebot@bmo.tld — 2024-03-21T17:36:22Z**

Pushed by rvandermeulen@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/1267c0f83a66
Make MSubstr non-movable. r=jandem

---

**Comment 11 — aryx.bugmail@gmx-topmail.de — 2024-03-21T21:27:59Z**

https://hg.mozilla.org/mozilla-central/rev/1267c0f83a66

---

**Comment 12 — pulsebot@bmo.tld — 2024-03-22T17:03:25Z**

https://hg.mozilla.org/releases/mozilla-beta/rev/dc49e19e3ef3

---

**Comment 13 — dveditz@mozilla.com — 2024-04-15T10:08:11Z**

Created attachment 9396626
advisory.txt

---

**Comment 14 — release-mgmt-account-bot@mozilla.tld — 2024-05-28T12:01:10Z**

2 months ago, tjr placed a reminder on the bug using the whiteboard tag `[reminder-test 2024-05-28]` .

anba, please refer to the original comment to better understand the reason for the reminder.

---

**Comment 15 — pulsebot@bmo.tld — 2024-06-20T17:44:05Z**

Pushed by iireland@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/7b91af00b66e
Add test case. r=jandem

---

**Comment 16 — aryx.bugmail@gmx-topmail.de — 2024-06-20T23:16:07Z**

https://hg.mozilla.org/mozilla-central/rev/7b91af00b66e
