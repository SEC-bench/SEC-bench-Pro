# Wild pointer-deref from jitted code

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1871089
CVE: CVE-2024-0744
Component: JavaScript Engine
Bounty: (unknown)
Date: 2023-12-20T17:11:54Z
Keywords: csectype-wildptr, regression, reporter-external, sec-high

Steps to reproduce:

On git commit 3bd65516eb9b3a9568806d846ba8c81a9402a885 the attached sample crashes the js-shell when invoked as `obj-x86_64-pc-linux-gnu/dist/bin/js --fuzzing-safe --fast-warmup --gc-zeal=14 crash.js` The crash is flaky and might need a couple of attempts to manifest.
The crash occurs at the jitted instruction `mov DWORD PTR [rax+0xa0], ecx`, where rax points to unmapped memory.
Bisecting points to 71883785e1d2bed4392079a95e1caa45869cf0a1 related to bug 1868187. So this might be a debugger-related issue and not affecting users; still flagging as s-s just in case the bisect is a false positive.

```
function F0() {
    if (!new.target) { throw 'must be called with new'; }
}
const v2 = new F0();
const v5 = [0, 0, 0, 0, 0, 0, 0]; 
class C6 {
    constructor(a8, a9) {
        a8[a9];
    }   
    toString(a12, a13) {
        const t11 = this.constructor;
        new t11(v2);
        const t13 = this.constructor;
        new t13(3622, this);
    }   
}
const v18 = new C6("aaaa");
const v19 = new C6(v5);
const t19 = v19.constructor;
new t19("aaaa", v18);
```

---

**Comment 1 — dveditz@mozilla.com — 2023-12-20T22:14:33Z**

Calling this sec-high to start because the testcase itself doesn't seem to be using any debugging functions (unless gc-zeal=14 does something like that)

---

**Comment 2 — iireland@mozilla.com — 2023-12-22T01:09:20Z**

This is a very good find.  It is caused by an unfortunate collision between bug 1867193 and our implementation of inlined constructors in baseline ICs.

We inline a constructor call. Inside the baseline IC, we call CreateThis to create a `this` object. Before we do so, we [spill the ICStubReg to the stack](https://searchfox.org/mozilla-central/rev/b580e3f77470b2337bc8ae032b58a85c11e66aba/js/src/jit/BaselineCacheIRCompiler.cpp#3389), intending to [restore it later](https://searchfox.org/mozilla-central/rev/b580e3f77470b2337bc8ae032b58a85c11e66aba/js/src/jit/BaselineCacheIRCompiler.cpp#3424-3425).

Inside CreateThis, we trigger a GC and discard jitcode. While marking active ICScripts, we [see that our ICStub is active on the stack, so we clone it and update the stub frame](https://searchfox.org/mozilla-central/rev/b580e3f77470b2337bc8ae032b58a85c11e66aba/js/src/jit/JitScript.cpp#715-722). (This was added in bug 1867193; previously the stub would not have moved).

However, when we return, we reload the spilled version of the ICStubReg, instead of loading the updated ICStubReg from the frame. Later, when we [try to read the callee's ICScript out of the stub](https://searchfox.org/mozilla-central/rev/b580e3f77470b2337bc8ae032b58a85c11e66aba/js/src/jit/BaselineCacheIRCompiler.cpp#3597), we read a stale pointer. In a debug build, the LifoAlloc poisons the memory when we free it, but I don't think we poison in release.

There was no good reason for us to be spilling the ICStubReg instead of using the copy already stored in the frame. Making that change fixes the bug.

It's tricky to write a more reliable testcase. It looks like the LifoAlloc generally decommits this memory after we free the chunk, which seems to implicitly zero it, at least on my machine. If we read a null ICScript out of the stub, then the callee will just end up using the default ICScript, so we don't trigger a crash. In the original testcase, the GC that triggered the discarding of jitcode also reallocates the page and uses it to store other ICs (which seems like a pretty clear avenue for exploitable UAF if it can be done reliably). The original testcase has a pretty good crash rate for me.

---

**Comment 3 — iireland@mozilla.com — 2023-12-22T01:16:02Z**

Running the same testcase locally with different flags, I managed to trigger what looks at first glance like a related bug where the ICStub pointer is updated properly, but the inlined ICScript that it points to is freed because it isn't active on the stack yet, so we crash inside the callee.

But that seems like a Future Problem.

---

**Comment 4 — release-mgmt-account-bot@mozilla.tld — 2023-12-22T01:42:50Z**

Set release status flags based on info from the regressing bug 1867193

:jandem, since you are the author of the regressor, bug 1867193, could you take a look? Also, could you set the severity field?

For more information, please visit [BugBot documentation](https://wiki.mozilla.org/BugBot#needinfo_regression_author.py).

---

**Comment 5 — jdemooij@mozilla.com — 2024-01-03T16:00:19Z**

*** Bug 1871950 has been marked as a duplicate of this bug. ***

---

**Comment 6 — release-mgmt-account-bot@mozilla.tld — 2024-01-03T16:41:30Z**

Copying crash signatures from duplicate bugs.

---

**Comment 7 — jdemooij@mozilla.com — 2024-01-03T20:05:52Z**

Created attachment 9370927
Bug 1871089 - Load ICStub from the frame instead of storing it separately. r?iain!

---

**Comment 8 — jdemooij@mozilla.com — 2024-01-03T20:06:02Z**

Created attachment 9370928
Bug 1871089 - Add test and comments. r?iain!



Depends on D197608

---

**Comment 9 — jdemooij@mozilla.com — 2024-01-04T09:51:42Z**

Comment on attachment 9370927
Bug 1871089 - Load ICStub from the frame instead of storing it separately. r?iain!

### Security Approval Request
* **How easily could an exploit be constructed based on the patch?**: It's possible but not very easy.
* **Do comments in the patch, the check-in comment, or tests included in the patch paint a bulls-eye on the security problem?**: No
* **Which older supported branches are affected by this flaw?**: 121+
* **If not all supported branches, which bug introduced the flaw?**: Bug 1863939
* **Do you have backports for the affected branches?**: Yes
* **If not, how different, hard to create, and risky will they be?**: Patch should apply to older branches or is easy to backport.
* **How likely is this patch to cause regressions; how much testing does it need?**: Pretty unlikely to cause regressions. The usual Nightly testing/fuzzing should be sufficient.
* **Is Android affected?**: Yes

---

**Comment 10 — tom@mozilla.com — 2024-01-04T19:11:08Z**

Comment on attachment 9370927
Bug 1871089 - Load ICStub from the frame instead of storing it separately. r?iain!

Approved to land

---

**Comment 11 — pulsebot@bmo.tld — 2024-01-04T22:58:05Z**

Pushed by rvandermeulen@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/8cd6801e79fd
Load ICStub from the frame instead of storing it separately. r=iain

---

**Comment 12 — ryanvm@gmail.com — 2024-01-05T05:01:25Z**

https://hg.mozilla.org/mozilla-central/rev/8cd6801e79fd

---

**Comment 13 — release-mgmt-account-bot@mozilla.tld — 2024-01-05T12:05:18Z**

The patch landed in nightly and beta is affected.
:jandem, is this bug important enough to require an uplift?
- If yes, please nominate the patch for beta approval.
- If no, please set `status-firefox122` to `wontfix`.

For more information, please visit [BugBot documentation](https://wiki.mozilla.org/BugBot#uplift_beta.py).

---

**Comment 14 — jdemooij@mozilla.com — 2024-01-05T13:16:31Z**

Comment on attachment 9370927
Bug 1871089 - Load ICStub from the frame instead of storing it separately. r?iain!

### Beta/Release Uplift Approval Request
* **User impact if declined**: Security bug.
* **Is this code covered by automated tests?**: Yes
* **Has the fix been verified in Nightly?**: Yes
* **Needs manual test from QE?**: No
* **If yes, steps to reproduce**: 
* **List of other uplifts needed**: None
* **Risk to taking this patch**: Low
* **Why is the change risky/not risky? (and alternatives if risky)**: Patch is pretty small and code is covered by many tests.
* **String changes made/needed**: N/A
* **Is Android affected?**: Yes

---

**Comment 15 — dmeehan@mozilla.com — 2024-01-05T20:48:35Z**

Comment on attachment 9370927
Bug 1871089 - Load ICStub from the frame instead of storing it separately. r?iain!

Approved for 122.0b7

---

**Comment 16 — pulsebot@bmo.tld — 2024-01-05T20:49:42Z**

https://hg.mozilla.org/releases/mozilla-beta/rev/ecbd1a871311

---

**Comment 17 — jschwartzentruber@mozilla.com — 2024-01-18T20:14:59Z**

Created attachment 9373593
advisory.txt

---

**Comment 18 — release-mgmt-account-bot@mozilla.tld — 2024-03-05T12:01:02Z**

a month ago, tjr placed a reminder on the bug using the whiteboard tag `[reminder-test 2024-03-05]` .

jandem, please refer to the original comment to better understand the reason for the reminder.

---

**Comment 19 — pulsebot@bmo.tld — 2024-03-09T07:09:14Z**

Pushed by jdemooij@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/55305e127c70
Add test and comments. r=iain

---

**Comment 20 — ryanvm@gmail.com — 2024-03-09T21:10:57Z**

https://hg.mozilla.org/mozilla-central/rev/55305e127c70

---

**Comment 21 — dveditz@mozilla.com — 2024-05-15T04:13:47Z**

Making Firefox 122 security bugs public.  [bugspam filter string: Pilgarlic-Towers]
