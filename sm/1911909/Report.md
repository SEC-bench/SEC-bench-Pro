# [wasm-gc] WASM type confusion due to broken js::wasm::ArrayType::canBeSubtypeOf() check

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1911909
CVE: CVE-2024-8385
Component: JavaScript: WebAssembly
Bounty: (unknown)
Date: 2024-08-06T21:52:41Z
Keywords: regression, reporter-external, sec-high

Created attachment 9418025
poc.html

## Vulnerability Details

### Summary

WASM type confusion due to broken `js::wasm::ArrayType::canBeSubtypeOf()` check.

### Details

`js::wasm::ArrayType::canBeSubtypeOf()` always returns true if array mutability is different, resulting in arbitrary type confusion between array elements.

```h
// https://searchfox.org/mozilla-central/source/js/src/wasm/WasmTypeDef.h#457
  static bool canBeSubTypeOf(const ArrayType& subType,
                             const ArrayType& superType) {
    // Mutable fields are invariant w.r.t. field types
    if (subType.isMutable_ && superType.isMutable_) {
      return subType.elementType_ == superType.elementType_;
    }

    // Immutable fields are covariant w.r.t. field types
    if (!subType.isMutable_ && !superType.isMutable_) {
      return StorageType::isSubTypeOf(subType.elementType_,
                                      superType.elementType_);
    }

    return true;
  }
```

This allows an attacker to acquire traditional JS exploit primitives such as addrof/fakeobj, as well as arbitrary read/write primitives.

Bug discovered through code audit.


## Version / Bisect

Existed since the implementation of Bug 1774827 (108 Branch), up to latest.


## Repro

Attached `poc.html`, visit the html file in Firefox for an immediate renderer crash.

This PoC uses the bug to confuse:
- anyref -> I64 (addrof)
- I64 -> anyref (fakeobj)
- I64 -> struct ( I64 ) (arbitrary RW)

...and obtain corresponding memory corruption primitives. The PoC attempts to `console.log()` on a `fakeobj(0x424242424242n)`, resulting in a renderer crash.

Note that arbitrary read/write operations do work, but with invalid addresses it does not immediately crash the renderer. This is likely due to WASM trap handling incorrectly capturing the segfault as a null pointer dereference - the read/write attempt can easily be verified by a debugger.


-----


## Some info regarding submission

I've initially submitted this to security@mozilla.org over PGP-encrypted email, following this [Mozilla docs](https://www.mozilla.org/en-US/security/), but [another docs](https://www.mozilla.org/en-US/security/client-bug-bounty/) suggest that I shouldn't have...? Quite confusing (report via email? bug bounty form? or just new bug w/ security checked in Bugzilla?), but anyways note that the vulnerability details & PoC has already been sent over PGP-encrypted email (and delete them if necessary). Also, please tell me where & in what format I should submit my future bugs so that everything works out clean :)

---

**Comment 1 — seunghyun3288@gmail.com — 2024-08-07T05:32:40Z**

Created attachment 9418058
exp.html (for Windows x86-64)

Added `exp.html` that pops `calc` from an unsandboxed renderer. Run the following commands in cmd to disable content sandbox and test the exploit:
1. `set MOZ_DISABLE_CONTENT_SANDBOX=1`
2. `<path to firefox.exe> <path to exp.html>`

I thought Firefox has W^X, but somehow wasm code region is RWX? The exploit simply overwrites the JITed code of an exported wasm function to shellcode and runs it.

---

**Comment 2 — jdemooij@mozilla.com — 2024-08-07T08:52:02Z**

*** Bug 1911959 has been marked as a duplicate of this bug. ***

---

**Comment 3 — bvisness@mozilla.com — 2024-08-07T13:29:19Z**

Created attachment 9418135
reduced.js

Here is a reduced version of poc.html, suitable for use in the shell. It's a remarkably simple exploit.

---

**Comment 4 — dveditz@mozilla.com — 2024-08-07T15:22:27Z**

> Quite confusing (report via email? bug bounty form? or just new bug w/ security checked in Bugzilla?)  ... Also, please tell me where & in what format I should submit my future bugs so that everything works out clean :)

If you're specifically interested in the Bug Bounty you should definitely use the Bug Bounty form on bugzilla. The normal bugzilla bug entry form is great, too, but you have to remember to manually check the security issue box; if you don't the bug will be public, and the security team likely won't notice the report.  Either form directly creates an issue in bugzilla, which is our preference.

Encrypted mail is our least favorite way, but it's an option if necessary.

---

**Comment 5 — rhunt@eqrion.net — 2024-08-07T15:33:00Z**

Created attachment 9418159
Bug 1911909 - wasm: Refactor structs and arrays to more closely match the spec. r?bvisness


The spec has the notion of a 'FieldType' which both struct fields
and array types share. This commit refactors them to use the same
type.

---

**Comment 6 — jseward@acm.org — 2024-08-07T16:46:40Z**

Created attachment 9418183
make-D218753-apply-to-m_release

This makes D218753 (the patch in comment 5) apply to m-release.
First apply D218753, then apply this on top.

---

**Comment 7 — rhunt@eqrion.net — 2024-08-07T21:50:24Z**

Created attachment 9418238
Bug 1911909 - wasm: Add test. r?bvisness



Depends on D218753

---

**Comment 8 — rhunt@eqrion.net — 2024-08-07T21:53:36Z**

This has been an issue since we implemented declared subtyping in wasm-gc. Marking the regressed by bug for shipping wasm-gc, which happened in Fx120.

---

**Comment 9 — rhunt@eqrion.net — 2024-08-07T21:59:29Z**

Comment on attachment 9418159
Bug 1911909 - wasm: Refactor structs and arrays to more closely match the spec. r?bvisness

### Security Approval Request
* **How easily could an exploit be constructed based on the patch?**: Moderate difficulty. The real issue is that this line [1] should return false instead of true. This patch accomplishes this by doing a reasonable refactoring to change our ArrayType code to shared code with our StructField code (as the wasm spec does), which fixes the issue. But with a motivated enough attacker, they may be able to diff through the methods to figure out what really changed. And if they can isolate the real change an exploit is easy to construct.

[1] https://searchfox.org/mozilla-central/rev/891d104826fb0cfd5cbdd6128e2372ce62810028/js/src/wasm/WasmTypeDef.h#470
* **Do comments in the patch, the check-in comment, or tests included in the patch paint a bulls-eye on the security problem?**: No
* **Which branches (beta, release, and/or ESR) are affected by this flaw, and do the release status flags reflect this affected/unaffected state correctly?**: ESR, Beta, and Release. Release status flags are correct.
* **If not all supported branches, which bug introduced the flaw?**: None
* **Do you have backports for the affected branches?**: Yes
* **If not, how different, hard to create, and risky will they be?**: It was easy to create a patch for release, these changes are very mechanical.
* **How likely is this patch to cause regressions; how much testing does it need?**: Unlikely. It's a simple change, but just with a lot of lines to update. I've done a try run by melding it into some other unrelated work.
* **Is the patch ready to land after security approval is given?**: Yes
* **Is Android affected?**: Yes

---

**Comment 10 — dveditz@mozilla.com — 2024-08-08T18:25:59Z**

Comment on attachment 9418159
Bug 1911909 - wasm: Refactor structs and arrays to more closely match the spec. r?bvisness

sec-approval+ = dveditz. Also approving uplift to beta -- earlier is better: it will look like planned work that missed the deadline but was safe enough for promotion

---

**Comment 11 — dveditz@mozilla.com — 2024-08-08T18:52:24Z**

[Tracking Requested - why for this release]:
We should keep an eye on this one and consider taking it if there's a mid-cycle release of both 129.0.x and ESR-128.1.x. The patch does a great job of looking like a refactor and doesn't directly change the incorrect line of code (the entire method body it's in is removed in favor of calling a more generic version of the method), but once discovered the vulnerability can be triggered easily and reliably (see Ben's test in attachment 9418135).

I realize that may not be possible in an effectively short cycle with so many people out on vacations and conferences. Waiting until 130 should be safe enough.

---

**Comment 12 — pulsebot@bmo.tld — 2024-08-08T20:53:04Z**

Pushed by rhunt@eqrion.net:
https://hg.mozilla.org/integration/autoland/rev/34c774fe463c
wasm: Refactor structs and arrays to more closely match the spec. r=bvisness

---

**Comment 13 — aryx.bugmail@gmx-topmail.de — 2024-08-09T07:57:27Z**

https://hg.mozilla.org/mozilla-central/rev/34c774fe463c

---

**Comment 14 — rhunt@eqrion.net — 2024-08-09T14:42:18Z**

Created attachment 9418570
Bug 1911909 - wasm: Refactor structs and arrays to more closely match the spec. r?bvisness


The spec has the notion of a 'FieldType' which both struct fields
and array types share. This commit refactors them to use the same
type.

Original Revision: https://phabricator.services.mozilla.com/D218753

---

**Comment 15 — phab-bot@bmo.tld — 2024-08-09T14:43:47Z**

### beta Uplift Approval Request
- **User impact if declined**: Exploitable security issue, see sec-approval request for details.
- **Code covered by automated testing**: yes
- **Fix verified in Nightly**: no
- **Needs manual QE test**: no
- **Steps to reproduce for manual QE testing**: None
- **Risk associated with taking this patch**: Low
- **Explanation of risk level**: Mostly mechanical patch covered well by tests
- **String changes made/needed**: None
- **Is Android affected?**: yes

---

**Comment 16 — rhunt@eqrion.net — 2024-08-09T14:45:40Z**

Just created a formal beta uplift request and revision for this. Dan, do you need to transfer your beta approval over to that one?

---

**Comment 17 — dmeehan@mozilla.com — 2024-08-09T15:09:31Z**

(In reply to Ryan Hunt [:rhunt] from comment #16)
> Just created a formal beta uplift request and revision for this. Dan, do you need to transfer your beta approval over to that one?

It's ok, relman will take care of approving that request.
:rhunt could you add an esr128 request also?

---

**Comment 18 — rhunt@eqrion.net — 2024-08-09T19:18:59Z**

Created attachment 9418625
Bug 1911909 - wasm: Refactor structs and arrays to more closely match the spec. r?bvisness


The spec has the notion of a 'FieldType' which both struct fields
and array types share. This commit refactors them to use the same
type.

Original Revision: https://phabricator.services.mozilla.com/D218753

---

**Comment 19 — phab-bot@bmo.tld — 2024-08-09T19:20:35Z**

### esr128 Uplift Approval Request
- **User impact if declined**: Exploitable security issue, see sec-approval request for details
- **Code covered by automated testing**: yes
- **Fix verified in Nightly**: no
- **Needs manual QE test**: no
- **Steps to reproduce for manual QE testing**: None
- **Risk associated with taking this patch**: Low
- **Explanation of risk level**: Mostly mechanical patch covered well by tests
- **String changes made/needed**: None
- **Is Android affected?**: yes

---

**Comment 20 — dmeehan@mozilla.com — 2024-08-10T07:27:04Z**

Comment on attachment 9418570
Bug 1911909 - wasm: Refactor structs and arrays to more closely match the spec. r?bvisness

:rhunt this failed to land in beta due to conflicts.
Could you please take a look and rebase the patch?

---

**Comment 21 — rhunt@eqrion.net — 2024-08-11T15:27:34Z**

Just pushed a new version.

---

**Comment 22 — pulsebot@bmo.tld — 2024-08-12T08:43:32Z**

https://hg.mozilla.org/releases/mozilla-beta/rev/aea7011e4ff4

---

**Comment 23 — dmeehan@mozilla.com — 2024-08-12T15:29:12Z**

Comment on attachment 9418625
Bug 1911909 - wasm: Refactor structs and arrays to more closely match the spec. r?bvisness

:rhunt I added a comment on the esr128 patch, it needs to be rebased.

---

**Comment 24 — rhunt@eqrion.net — 2024-08-14T14:52:47Z**

I just rebased the patch.

---

**Comment 25 — pulsebot@bmo.tld — 2024-08-15T07:20:23Z**

https://hg.mozilla.org/releases/mozilla-esr128/rev/49deaa4855a5

---

**Comment 26 — seunghyun3288@gmail.com — 2024-08-21T14:53:18Z**

Please donate the bounty to a charity of your choice, thanks :)

---

**Comment 27 — dveditz@mozilla.com — 2024-09-02T18:55:07Z**

Created attachment 9422104
advisory.txt

---

**Comment 28 — release-mgmt-account-bot@mozilla.tld — 2024-10-15T12:01:00Z**

2 months ago, dveditz placed a reminder on the bug using the whiteboard tag `[reminder-test 2024-10-15]` .

rhunt, please refer to the original comment to better understand the reason for the reminder.

---

**Comment 29 — seunghyun3288@gmail.com — 2024-10-21T00:57:17Z**

Hi, I would like to disclose information about this bug on Nov. 7 at POC2024 conference, based on the standard 90-day disclosure deadline. Please let me know if you need more time, thanks.

---

**Comment 30 — fbraun@mozilla.com — 2024-10-29T09:33:14Z**

Thank you for reaching out to us Seunghyun Lee. I see no concerns with you talking about this bug in public given that we have addressed the bug 8 weeks ago in Firefox 130. Good luck with your presentation.

---

**Comment 31 — pulsebot@bmo.tld — 2025-09-10T21:21:59Z**

Pushed by rhunt@eqrion.net:
https://github.com/mozilla-firefox/firefox/commit/73f0f1026d13
https://hg.mozilla.org/integration/autoland/rev/6ee52d93eb5b
wasm: Add test. r=bvisness

---

**Comment 32 — nbeleuzu@mozilla.com — 2025-09-11T04:09:41Z**

https://hg.mozilla.org/mozilla-central/rev/6ee52d93eb5b
