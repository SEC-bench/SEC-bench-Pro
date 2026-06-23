# Assertion failure: slotIndex <= (255), at jit/CacheIRWriter.h:469

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1838587
Component: JavaScript Engine: JIT
Bounty: (unknown)
Date: 2023-06-15T08:12:50Z
Keywords: assertion, regression, sec-high, testcase

The following testcase crashes on mozilla-central revision 20230613-e974af195c98 (debug build, run with --fuzzing-safe --cpu-count=2 --ion-offthread-compile=off --baseline-eager):

See attachment.


Backtrace:

    received signal SIGSEGV, Segmentation fault.
    #0  0x0000555557b56617 in js::jit::CacheIRWriter::loadArgumentFixedSlot(js::jit::ArgumentKind, unsigned int, js::jit::CallFlags) ()
    #1  0x0000555557b83bb2 in js::jit::CallIRGenerator::tryAttachBoundFunction(JS::Handle<js::BoundFunctionObject*>) ()
    #2  0x0000555557b84849 in js::jit::CallIRGenerator::tryAttachStub() ()
    #3  0x000055555791a12c in js::jit::DoCallFallback(JSContext*, js::jit::BaselineFrame*, js::jit::ICFallbackStub*, unsigned int, JS::Value*, JS::MutableHandle<JS::Value>) ()
    #4  0x0000292b5070f487 in ?? ()
    #5  0x0000000000000000 in ?? ()
    rax	0x5555557f4ed2	93824994987730
    rbx	0x7fffffffb558	140737488336216
    rcx	0x5555585a1cf8	93825042881784
    rdx	0x0	0
    rsi	0x7ffff6abd770	140737331844976
    rdi	0x7ffff6abc540	140737331840320
    rbp	0x7fffffffb340	140737488335680
    rsp	0x7fffffffb320	140737488335648
    r8	0x7ffff6abd770	140737331844976
    r9	0x7ffff7fe3840	140737354020928
    r10	0x2	2
    r11	0x0	0
    r12	0x0	0
    r13	0x7fffffffb3f8	140737488335864
    r14	0x100	256
    r15	0x1	1
    rip	0x555557b56617 <js::jit::CacheIRWriter::loadArgumentFixedSlot(js::jit::ArgumentKind, unsigned int, js::jit::CallFlags)+199>
    => 0x555557b56617 <_ZN2js3jit13CacheIRWriter21loadArgumentFixedSlotENS0_12ArgumentKindEjNS0_9CallFlagsE+199>:	movl   $0x1d5,0x0
       0x555557b56622 <_ZN2js3jit13CacheIRWriter21loadArgumentFixedSlotENS0_12ArgumentKindEjNS0_9CallFlagsE+210>:	callq  0x555556ca5adf <abort>


Marking s-s because this is a range-like assert in JIT code.

---

**Comment 1 — choller@mozilla.com — 2023-06-15T08:12:54Z**

Created attachment 9339234
Detailed Crash Information

---

**Comment 2 — choller@mozilla.com — 2023-06-15T08:12:56Z**

Created attachment 9339235
Testcase

---

**Comment 3 — jdemooij@mozilla.com — 2023-06-15T13:42:27Z**

That's a pretty impressive test case based on bug1383972.js. Below is a simplified test.

In `tryAttachBoundFunction` we use `loadArgumentFixedSlot` and the resulting index doesn't fit in a byte. This probably isn't security-sensitive because I think we'll end up loading a different `Value` from the stack instead of the callee, but we'd still emit the is-bound-function guards for that and then call *its* target. So it could be a correctness bug but probably not a security bug. I'll take a closer look though.

```js
function f() {
    var bound = (function () {}).bind(null);
    for (var i = 0; i < 20; i++) {
        bound(1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
            1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
            1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
            1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
            1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
            1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
            1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
            1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
            1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
            1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
            1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
            1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
            1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
            1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
            1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
            1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1);
    }
}
f();
```

---

**Comment 4 — bugmon@mozilla.com — 2023-06-15T16:22:46Z**

Verified bug as reproducible on mozilla-central 20230615144901-e8bfcd70e6ba.
Unable to bisect testcase (Unable to launch the start build!):
> Start: 1c45ab9d8ec1596f931df2a1a91795c2dca22b5b (20220616093051)
> End: e974af195c9886356987dd99ba40ab25692c134c (20230613034225)
> BuildFlags: BuildFlags(asan=False, tsan=False, debug=True, fuzzing=False, coverage=False, valgrind=False, no_opt=False, fuzzilli=False, nyx=False)

---

**Comment 5 — jdemooij@mozilla.com — 2023-06-19T13:56:38Z**

Created attachment 9339848
Bug 1838587 - Use loadArgumentDynamicSlot in tryAttachBoundFunction. r?iain!

---

**Comment 6 — jdemooij@mozilla.com — 2023-06-19T13:56:42Z**

Created attachment 9339849
Bug 1838587 - Add test and release assertion. r?iain!



Depends on D181389

---

**Comment 7 — jdemooij@mozilla.com — 2023-06-19T14:02:42Z**

(In reply to Jan de Mooij [:jandem] from comment #3)
> This probably isn't security-sensitive because I think we'll end up loading a different `Value` from the stack instead of the callee, but we'd still emit the is-bound-function guards for that and then call *its* target. So it could be a correctness bug but probably not a security bug. I'll take a closer look though.

I took a closer look and it's more complicated due to [this code](https://searchfox.org/mozilla-central/rev/c936f47f3a629ae49a4d528d3366bf29f2d4e4a7/js/src/jit/BaselineCacheIRCompiler.cpp#3322-3325) where we reload the *actual* callee from the stack if we're a constructing call. Considering that we should probably treat this as sec-high.

---

**Comment 8 — release-mgmt-account-bot@mozilla.tld — 2023-06-19T15:41:57Z**

Set release status flags based on info from the regressing bug 1483869

---

**Comment 9 — jdemooij@mozilla.com — 2023-06-19T16:43:16Z**

Comment on attachment 9339848
Bug 1838587 - Use loadArgumentDynamicSlot in tryAttachBoundFunction. r?iain!

### Security Approval Request
* **How easily could an exploit be constructed based on the patch?**: Not very easy but maybe with some work.
* **Do comments in the patch, the check-in comment, or tests included in the patch paint a bulls-eye on the security problem?**: No
* **Which older supported branches are affected by this flaw?**: 112+
* **If not all supported branches, which bug introduced the flaw?**: Bug 1483869
* **Do you have backports for the affected branches?**: Yes
* **If not, how different, hard to create, and risky will they be?**: Patch should apply to beta.
* **How likely is this patch to cause regressions; how much testing does it need?**: Pretty unlikely because it's a simple and local fix.
* **Is Android affected?**: Yes

---

**Comment 10 — tom@mozilla.com — 2023-06-20T03:11:53Z**

Comment on attachment 9339848
Bug 1838587 - Use loadArgumentDynamicSlot in tryAttachBoundFunction. r?iain!

Approved to request uplift and land

---

**Comment 11 — jdemooij@mozilla.com — 2023-06-20T09:59:07Z**

Comment on attachment 9339848
Bug 1838587 - Use loadArgumentDynamicSlot in tryAttachBoundFunction. r?iain!

### Beta/Release Uplift Approval Request
* **User impact if declined**: Potential security bugs.
* **Is this code covered by automated tests?**: Yes
* **Has the fix been verified in Nightly?**: No
* **Needs manual test from QE?**: No
* **If yes, steps to reproduce**: 
* **List of other uplifts needed**: None
* **Risk to taking this patch**: Low
* **Why is the change risky/not risky? (and alternatives if risky)**: Very small and local fix.
* **String changes made/needed**: 
* **Is Android affected?**: Yes

---

**Comment 12 — aryx.bugmail@gmx-topmail.de — 2023-06-20T16:29:46Z**

Use loadArgumentDynamicSlot in tryAttachBoundFunction. r=iain
https://hg.mozilla.org/integration/autoland/rev/bfe3e51df397787d8c2edc825f65f7e8dc43b362
https://hg.mozilla.org/mozilla-central/rev/bfe3e51df397

---

**Comment 13 — bugmon@mozilla.com — 2023-06-21T00:21:56Z**

Verified bug as fixed on rev mozilla-central 20230620212415-809786b4d44c.

---

**Comment 14 — dmeehan@mozilla.com — 2023-06-21T13:26:12Z**

Comment on attachment 9339848
Bug 1838587 - Use loadArgumentDynamicSlot in tryAttachBoundFunction. r?iain!

Approved for 115.0b9.

---

**Comment 15 — dmeehan@mozilla.com — 2023-06-21T13:30:19Z**

https://hg.mozilla.org/releases/mozilla-beta/rev/48cf25e5a1eb

---

**Comment 16 — release-mgmt-account-bot@mozilla.tld — 2023-08-15T12:00:47Z**

a month ago, tjr placed a reminder on the bug using the whiteboard tag `[reminder-test 2023-08-15]` .

jandem, please refer to the original comment to better understand the reason for the reminder.

---

**Comment 17 — pulsebot@bmo.tld — 2023-08-17T15:24:41Z**

Pushed by jdemooij@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/d00165395367
Add test and release assertion. r=iain

---

**Comment 18 — ryanvm@gmail.com — 2023-08-18T03:56:41Z**

https://hg.mozilla.org/mozilla-central/rev/d00165395367
