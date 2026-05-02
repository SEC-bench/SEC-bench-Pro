# Assertion failure: iter->done(), at js/src/jit/JitFrames.cpp:695

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1904644
CVE: CVE-2024-7521
Component: JavaScript: WebAssembly
Bounty: (unknown)
Date: 2024-06-25T16:31:48Z
Keywords: csectype-uaf, reporter-external, sec-high, testcase

Created attachment 9409490
bug.js

Steps to reproduce:

Checkout commit 9fcc11127fbfbdc88cbf37489dac90542e141c77 and invoke the js shell as follows:
```
js --fuzzing-safe <test-case>
```


Actual results:

```
Assertion failure: iter->done(), at js/src/jit/JitFrames.cpp:695
```

---

**Comment 1 — jdemooij@mozilla.com — 2024-06-26T07:04:59Z**

We have a Wasm => JS JIT call and the JS code throws an exception. The Wasm code *catches* the exception but it looks like the exception handler code then doesn't expect that to happen (it's not just the assertion, the trampoline code calling the exception handler also seems incomplete). A bit surprising because I'd have expected tests, fuzzers, or websites to have hit this by now.

```js
var throwExc = false;
var e = {m: {foreign() {
    if (throwExc) {
        throw new TypeError("hi");
    }
}}};
var bin = wasmTextToBinary(`(module(import "m" "foreign" (func $foreign))(func (export "f") try(call $foreign)end))`);
var mod = new WebAssembly.Module(bin);
var inst = new WebAssembly.Instance(mod, e);
for (var i = 0; i < 20; i++) {
    inst.exports.f();
}
throwExc = true;
inst.exports.f();
```

---

**Comment 2 — jdemooij@mozilla.com — 2024-06-26T12:50:36Z**

Phabricator patches are not synced to bugzilla atm, so:

https://phabricator.services.mozilla.com/D214959
https://phabricator.services.mozilla.com/D214960

---

**Comment 3 — continuation@gmail.com — 2024-06-26T13:42:33Z**

I'm not able to view that Phabricator link, so maybe the permissions are off somehow.

How bad of a security issue is this? I can't tell from the comments in this bug so far. Thanks.

---

**Comment 4 — jdemooij@mozilla.com — 2024-06-26T14:13:00Z**

Created attachment 9409677
Bug 1904644 - Share more exception handling code. r?rhunt!

---

**Comment 5 — jdemooij@mozilla.com — 2024-06-26T14:13:09Z**

Created attachment 9409678
Bug 1904644 - Add tests. r?rhunt!

---

**Comment 6 — continuation@gmail.com — 2024-06-26T14:16:08Z**

I am able to view the Phabricator link now. It looks like phab-bot just updated it.

---

**Comment 7 — jdemooij@mozilla.com — 2024-06-26T14:39:14Z**

(In reply to Andrew McCreight [:mccr8] from comment #3)
> How bad of a security issue is this? I can't tell from the comments in this bug so far. Thanks.

I'll say sec-high because we jump to a Wasm catch handler with garbage in the instance register. A local non-debug build crashes like this:
```
   0x852ac69d101:       mov    0x48(%r14),%rcx
=> 0x852ac69d105:       testl  $0x1,(%rcx)

(rr) p/x $rcx
$1 = 0xe5e5e5e5e5e5e5e5
```

---

**Comment 8 — jdemooij@mozilla.com — 2024-06-28T11:50:16Z**

Comment on attachment 9409677
Bug 1904644 - Share more exception handling code. r?rhunt!

### Security Approval Request
* **How easily could an exploit be constructed based on the patch?**: It's not super easy but probably also not very difficult.
* **Do comments in the patch, the check-in comment, or tests included in the patch paint a bulls-eye on the security problem?**: No
* **Which branches (beta, release, and/or ESR) are affected by this flaw, and do the release status flags reflect this affected/unaffected state correctly?**: All
* **If not all supported branches, which bug introduced the flaw?**: None
* **Do you have backports for the affected branches?**: Yes
* **If not, how different, hard to create, and risky will they be?**: Should apply or be easy to backport.
* **How likely is this patch to cause regressions; how much testing does it need?**: Not very likely, but exception handling is complicated.
* **Is the patch ready to land after security approval is given?**: Yes
* **Is Android affected?**: Yes

---

**Comment 9 — dveditz@mozilla.com — 2024-07-03T09:24:58Z**

It's too late to get this into Fx128, and it's a bad candidate to be a "ride-along" in the mid-cycle point release because we don't schedule a mid-cycle release for the ESR branch(es). We should wait until after the release to land this.

---

**Comment 10 — dveditz@mozilla.com — 2024-07-15T15:15:47Z**

Comment on attachment 9409677
Bug 1904644 - Share more exception handling code. r?rhunt!

sec-approval+ = dveditz
please request beta uplift, and esr after we get some nightly/beta confidence

---

**Comment 11 — pulsebot@bmo.tld — 2024-07-18T10:54:44Z**

Pushed by jdemooij@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/821842bd3d34
Share more exception handling code. r=rhunt

---

**Comment 12 — aryx.bugmail@gmx-topmail.de — 2024-07-18T21:55:11Z**

https://hg.mozilla.org/mozilla-central/rev/821842bd3d34

---

**Comment 13 — dmeehan@mozilla.com — 2024-07-19T12:47:39Z**

:jandem could you add beta, ESR115, and ESR128 uplift requests on this when ready?

---

**Comment 14 — jdemooij@mozilla.com — 2024-07-19T13:28:36Z**

Comment on attachment 9409677
Bug 1904644 - Share more exception handling code. r?rhunt!

### Beta/Release Uplift Approval Request
* **User impact if declined**: Security bugs, crashes.
* **Is this code covered by automated tests?**: Yes
* **Has the fix been verified in Nightly?**: Yes
* **Needs manual test from QE?**: No
* **If yes, steps to reproduce**: 
* **List of other uplifts needed**: None
* **Risk to taking this patch**: Low
* **Why is the change risky/not risky? (and alternatives if risky)**: Complicated code but changes are fairly straight-forward. The problematic case that's being fixed isn't used much in the wild at this point.
* **String changes made/needed**: N/A
* **Is Android affected?**: Yes

---

**Comment 15 — jdemooij@mozilla.com — 2024-07-19T13:29:57Z**

I added the approval requests. This might not apply cleanly to the older branches - I can upload separate patches for these if it's an issue.

---

**Comment 16 — ryanvm@gmail.com — 2024-07-19T18:44:50Z**

It'll need a bit of rebasing for ESR115. The other branches graft cleanly.

---

**Comment 17 — dmeehan@mozilla.com — 2024-07-19T18:47:23Z**

Comment on attachment 9409677
Bug 1904644 - Share more exception handling code. r?rhunt!

Approved for 129.0b7

---

**Comment 18 — pulsebot@bmo.tld — 2024-07-19T18:48:23Z**

https://hg.mozilla.org/releases/mozilla-beta/rev/8df73ee5ebfc

---

**Comment 19 — jdemooij@mozilla.com — 2024-07-22T12:11:02Z**

Created attachment 9414107
Bug 1904644 - Share more exception handling code. r=rhunt!, a=dmeehan (ESR115)

---

**Comment 20 — jdemooij@mozilla.com — 2024-07-22T12:13:35Z**

(In reply to Ryan VanderMeulen [:RyanVM] from comment #16)
> It'll need a bit of rebasing for ESR115. The other branches graft cleanly.

I posted a patch for ESR115. Fortunately it was just a single minor conflict. I also verified the tests fail on ESR115 and are fixed by this patch.

---

**Comment 21 — dmeehan@mozilla.com — 2024-07-22T12:37:44Z**

Comment on attachment 9409677
Bug 1904644 - Share more exception handling code. r?rhunt!

Approved for 128.1esr.

---

**Comment 22 — pulsebot@bmo.tld — 2024-07-22T12:49:54Z**

https://hg.mozilla.org/releases/mozilla-esr128/rev/9d0bd5bd8933

---

**Comment 23 — dmeehan@mozilla.com — 2024-07-22T13:13:30Z**

Comment on attachment 9414107
Bug 1904644 - Share more exception handling code. r=rhunt!, a=dmeehan (ESR115)

Approved for 115.14esr

---

**Comment 24 — pulsebot@bmo.tld — 2024-07-22T13:14:08Z**

https://hg.mozilla.org/releases/mozilla-esr115/rev/723cc10c7059

---

**Comment 25 — twsmith@mozilla.com — 2024-08-01T20:07:17Z**

Created attachment 9417354
advisory.txt

---

**Comment 26 — release-mgmt-account-bot@mozilla.tld — 2024-09-09T12:05:21Z**

2 months ago, dveditz placed a reminder on the bug using the whiteboard tag `[reminder-test 2024-09-09]` .

jandem, please refer to the original comment to better understand the reason for the reminder.

---

**Comment 27 — pulsebot@bmo.tld — 2024-09-11T16:22:03Z**

Pushed by jdemooij@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/20af2f42d18f
Add tests. r=rhunt

---

**Comment 28 — aryx.bugmail@gmx-topmail.de — 2024-09-12T09:31:41Z**

https://hg.mozilla.org/mozilla-central/rev/20af2f42d18f
