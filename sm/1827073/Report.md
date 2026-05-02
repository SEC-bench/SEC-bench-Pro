# Assertion failure: mLength + 1 <= mTail.mReserved, at mozilla/Vector.h:1303

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1827073
Component: JavaScript Engine: JIT
Bounty: (unknown)
Date: 2023-04-08T11:21:09Z
Keywords: csectype-bounds, regression, reporter-external, sec-high
See Also:
- https://bugzilla.mozilla.org/show_bug.cgi?id=1445260

Created attachment 9327666
crash.js

Steps to reproduce:

On git commit 5b0c0c8f927a9b5e88adf6283380678ef2acd604 the attached sample asserts in the js-shell when invoked as `obj-x86_64-pc-linux-gnu/dist/bin/js --baseline-warmup-threshold=10 --fuzzing-safe crash.js`. Bisecting the issue points to commit e0aa2e4351ba3051b4e5001506c536ab0519ebc6 related to bug 1819722.
Setting s-s because it looks like an OOB but given the recency of the introducing commit neither beta nor release should be affected.

```
#0  0x0000555557a327ce in mozilla::Vector<JS::Value, 8ul, js::TempAllocPolicy>::internalAppend<JS::Value const&> (
    this=0x7fffffdfe7a8, aU=...)
    at obj-x86_64-pc-linux-gnu/dist/include/mozilla/Vector.h:1303
#1  0x0000555558033ff9 in mozilla::Vector<JS::Value, 8ul, js::TempAllocPolicy>::infallibleAppend<JS::Value const&> (
    this=0x7fffffdfe7a8, aU=...)
    at obj-x86_64-pc-linux-gnu/dist/include/mozilla/Vector.h:789
#2  0x0000555558033fb9 in JS::GCVector<JS::Value, 8ul, js::TempAllocPolicy>::infallibleAppend<JS::Value const&> (
    this=0x7fffffdfe7a8, aU=...)
    at obj-x86_64-pc-linux-gnu/dist/include/js/GCVector.h:117
#3  0x0000555558033f71 in js::MutableWrappedPtrOperations<JS::GCVector<JS::Value, 8ul, js::TempAllocPolicy>, JS::Rooted<JS::StackGCVector<JS::Value, js::TempAllocPolicy> > >::infallibleAppend<JS::Value
 const&> (this=0x7fffffdfe790, 
    aU=...) at obj-x86_64-pc-linux-gnu/dist/include/js/GCVector.h:299
#4  0x0000555558033f20 in CopyScriptFrameIterArgs::init(JSContext*)::{lambda(JS::Value const&)#1}::operator()(JS::Value const&) const (this=0x7fffffdfe5e0, v=...) at js/src/vm/ArgumentsObject.cpp:179
#5  0x0000555558034979 in js::jit::SnapshotIterator::readFunctionFrameArgs<CopyScriptFrameIterArgs::init(JSContext*)::{lambda(JS::Value const&)#1}>(CopyScriptFrameIterArgs::init(JSContext*)::{lambda(JS
::Value const&)#1}&, js::ArgumentsObject**, JS::Value*, unsigned int, unsigned int, JSScript*, js::jit::MaybeReadFallback&) (this=0x7fffffdfe4b8, op=..., 
    argsObj=0x0, thisv=0x0, start=0, end=4, script=0x3763db63060, fallback=...)
    at js/src/jit/JSJitFrameIter.h:569
#6  0x00005555580342f2 in js::jit::InlineFrameIterator::readFrameArgsAndLocals<CopyScriptFrameIterArgs::init(JSContext*)::{lambda(JS::Value const&)#1}, js::jit::InlineFrameIterator::Nop>(JSContext*, Co
pyScriptFrameIterArgs::init(JSContext*)::{lambda(JS::Value const&)#1}&, js::jit::InlineFrameIterator::Nop&, JSObject**, bool*, JS::Value*, js::ArgumentsObject**, JS::Value*, js::jit::ReadFrameArgsBehav
ior, js::jit::MaybeReadFallback&) const (this=0x7fffffdfe9c0, 
    cx=0x7ffff3a30100, argOp=..., localOp=..., envChain=0x0, hasInitialEnv=0x0, rval=0x0, argsObj=0x0, thisv=0x0,
    behavior=js::jit::ReadFrame_Actuals, fallback=...)
    at js/src/jit/JSJitFrameIter.h:689
#7  0x0000555558033be6 in js::jit::InlineFrameIterator::unaliasedForEachActual<CopyScriptFrameIterArgs::init(JSContext*)::{lambda(JS::Value const&)#1}>(JSContext*, CopyScriptFrameIterArgs::init(JSConte
xt*)::{lambda(JS::Value const&)#1}, js::jit::ReadFrameArgsBehavior, js::jit::MaybeReadFallback&) const (this=0x7fffffdfe9c0, cx=0x7ffff3a30100, op=..., 
    behavior=js::jit::ReadFrame_Actuals, fallback=...)
    at js/src/jit/JSJitFrameIter.h:748
#8  0x00005555580336d2 in js::FrameIter::unaliasedForEachActual<CopyScriptFrameIterArgs::init(JSContext*)::{lambda(JS::Value const&)#1}>(JSContext*, CopyScriptFrameIterArgs::init(JSContext*)::{lambda(J
S::Value const&)#1}) ( 
    this=0x7fffffdfe8f8, cx=0x7ffff3a30100, op=...) at js/src/vm/FrameIter-inl.h:33
#9  0x0000555558029d31 in CopyScriptFrameIterArgs::init (this=0x7fffffdfe788, cx=0x7ffff3a30100)
    at js/src/vm/ArgumentsObject.cpp:178
#10 0x0000555558029b3f in js::ArgumentsObject::createUnexpected (cx=0x7ffff3a30100, iter=...)
    at js/src/vm/ArgumentsObject.cpp:361
#11 0x0000555557929c03 in ArgumentsGetterImpl (cx=0x7ffff3a30100, args=...)
    at js/src/vm/JSFunction.cpp:201
#12 0x0000555557964a9c in JS::CallNonGenericMethod<&(IsFunction(JS::Handle<JS::Value>)), &(ArgumentsGetterImpl(JSContext*, JS::CallArgs const&))> (cx=0x7ffff3a30100, args=...)
    at obj-x86_64-pc-linux-gnu/dist/include/js/CallNonGenericMethod.h:103
#13 0x00005555579647fe in ArgumentsGetter (cx=0x7ffff3a30100, argc=0, vp=0x7fffffdfed08)
    at js/src/vm/JSFunction.cpp:220
#14 0x0000555558873f95 in js::jit::CallNativeGetter (cx=0x7ffff3a30100, callee=..., receiver=..., result=...)
    at js/src/jit/VMFunctions.cpp:1472
#15 0x00003d0054c1401f in ?? ()
#16 0x00005555599afdc0 in vtable for js::jit::MArrayState ()
#17 0x00007fffffdfed40 in ?? ()
#18 0xfff9800000000000 in ?? ()
#19 0x00005555599b0420 in js::jit::vmFunctions ()
```

---

**Comment 1 — lukas.bernhard@rub.de — 2023-04-08T13:37:24Z**

Actually, even on older commits fuzzers find similar crash signatures. Maybe bug 1819722 just made it easier to find.

---

**Comment 2 — continuation@gmail.com — 2023-04-10T17:50:48Z**

FWIW, it looks like bug 1825741 changed the code in ArgumentsObject.cpp.

---

**Comment 3 — jdemooij@mozilla.com — 2023-04-11T09:13:47Z**

Good find. I think bug 1825741 exposed this, but the underlying bug is that `InlineFrameIterator::unaliasedForEachActual` is buggy. If `nactuals < nformals` it calls the callback `nformals` times :/

---

**Comment 4 — jdemooij@mozilla.com — 2023-04-11T09:51:05Z**

Created attachment 9327900
Bug 1827073 part 1 - Remove unused ReadFrame_Formals. r?iain!

---

**Comment 5 — jdemooij@mozilla.com — 2023-04-11T09:51:18Z**

Created attachment 9327901
Bug 1827073 part 2 - Remove ReadFrame_Overflown and simplify unaliasedForEachActual. r?iain!


The only consumer of `ReadFrame_Overflown` is some debug dumping code where we
want to skip the formal arguments. It's simpler to skip the formals there so
that we can simplify the `unaliasedForEachActual` method.

Depends on D175112

---

**Comment 6 — jdemooij@mozilla.com — 2023-04-11T09:51:28Z**

Created attachment 9327902
Bug 1827073 part 3 - Fix reading of actual arguments. r?iain!



Depends on D175113

---

**Comment 7 — jdemooij@mozilla.com — 2023-04-11T09:51:34Z**

Created attachment 9327903
Bug 1827073 part 4 - Add test and release assertion. r?iain!



Depends on D175114

---

**Comment 8 — jdemooij@mozilla.com — 2023-04-11T10:23:05Z**

*** Bug 1827372 has been marked as a duplicate of this bug. ***

---

**Comment 9 — choller@mozilla.com — 2023-04-11T10:28:16Z**

Found by internal fuzzing at `Wed, 05 Apr 2023 09:29:41 +0000` (Crash ID 6621935).

---

**Comment 10 — jdemooij@mozilla.com — 2023-04-11T14:32:14Z**

Comment on attachment 9327900
Bug 1827073 part 1 - Remove unused ReadFrame_Formals. r?iain!

### Security Approval Request
* **How easily could an exploit be constructed based on the patch?**: Not very easy if we don't land the last part.
* **Do comments in the patch, the check-in comment, or tests included in the patch paint a bulls-eye on the security problem?**: No
* **Which older supported branches are affected by this flaw?**: 113
* **If not all supported branches, which bug introduced the flaw?**: Bug 1825741
* **Do you have backports for the affected branches?**: Yes
* **If not, how different, hard to create, and risky will they be?**: Recent merge/regression, so should be easy.
* **How likely is this patch to cause regressions; how much testing does it need?**: Unlikely to cause regressions.
* **Is Android affected?**: Yes

---

**Comment 11 — release-mgmt-account-bot@mozilla.tld — 2023-04-11T14:34:52Z**

Set release status flags based on info from the regressing bug 1825741

---

**Comment 12 — tom@mozilla.com — 2023-04-11T15:34:18Z**

Comment on attachment 9327900
Bug 1827073 part 1 - Remove unused ReadFrame_Formals. r?iain!

These aren't r+-ed yet, but everything seems fine to land and uplift when ready.  We'll land the test later of course.

---

**Comment 13 — jdemooij@mozilla.com — 2023-04-12T04:54:35Z**

Comment on attachment 9327900
Bug 1827073 part 1 - Remove unused ReadFrame_Formals. r?iain!

### Beta/Release Uplift Approval Request
* **User impact if declined**: Security issues or crashes.
* **Is this code covered by automated tests?**: Yes
* **Has the fix been verified in Nightly?**: No
* **Needs manual test from QE?**: No
* **If yes, steps to reproduce**: 
* **List of other uplifts needed**: None
* **Risk to taking this patch**: Low
* **Why is the change risky/not risky? (and alternatives if risky)**: Patches are pretty straight-forward.
* **String changes made/needed**: None
* **Is Android affected?**: Yes

---

**Comment 14 — aryx.bugmail@gmx-topmail.de — 2023-04-13T12:09:15Z**

part 1 - Remove unused ReadFrame_Formals. r=iain
https://hg.mozilla.org/integration/autoland/rev/82fddd67a4ae3e0dfc2e875ba6d18a6ac32e8b88
https://hg.mozilla.org/mozilla-central/rev/82fddd67a4ae

part 2 - Remove ReadFrame_Overflown and simplify unaliasedForEachActual. r=iain
https://hg.mozilla.org/integration/autoland/rev/ecbe2aa640a080431138383a5a75760dbdf904b3
https://hg.mozilla.org/mozilla-central/rev/ecbe2aa640a0

part 3 - Fix reading of actual arguments. r=iain
https://hg.mozilla.org/integration/autoland/rev/39eaca8bc0bffe78b8eee304f8b5506f86ba5067
https://hg.mozilla.org/mozilla-central/rev/39eaca8bc0bf

---

**Comment 15 — ryanvm@gmail.com — 2023-04-18T00:45:30Z**

Comment on attachment 9327900
Bug 1827073 part 1 - Remove unused ReadFrame_Formals. r?iain!

Approved for 113.0b5.

---

**Comment 16 — ryanvm@gmail.com — 2023-04-18T00:50:03Z**

https://hg.mozilla.org/releases/mozilla-beta/rev/958b8523d7e4
https://hg.mozilla.org/releases/mozilla-beta/rev/b781133b18e0
https://hg.mozilla.org/releases/mozilla-beta/rev/c2ea096e1e70

Given that this only affected 113+, can we land the testcase for this sooner, Tom?

---

**Comment 17 — tom@mozilla.com — 2023-04-19T18:03:45Z**

Yes, I am fine with landing the testcase now.

---

**Comment 18 — release-mgmt-account-bot@mozilla.tld — 2023-04-21T12:00:13Z**

a day ago, Tom Ritter [:tjr] placed a reminder on the bug using the whiteboard tag `[reminder-test 2023-04-20]` .

jandem, please refer to the original comment to better understand the reason for the reminder.

---

**Comment 19 — jdemooij@mozilla.com — 2023-04-24T12:20:42Z**

Landed the test:

https://hg.mozilla.org/integration/autoland/rev/1ca624984387c0812f23a0b26ce27a9504f4e25d

---

**Comment 20 — ryanvm@gmail.com — 2023-04-24T16:35:14Z**

https://hg.mozilla.org/mozilla-central/rev/1ca624984387

---

**Comment 21 — dveditz@mozilla.com — 2024-06-02T18:57:12Z**

Sorry for the burst of bugspam: filter on tinkling-glitter-filtrate
Adding `reporter-external` keyword to security bugs found by non-employees for accounting reasons
