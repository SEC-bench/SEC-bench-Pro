# Wild deref in js::CheckTracedThing<js::Shape>

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1888892
CVE: CVE-2024-3858
Component: JavaScript Engine: JIT
Bounty: (unknown)
Date: 2024-04-01T08:43:49Z
Keywords: csectype-wildptr, regression, reporter-external, sec-high, testcase

Steps to reproduce:

On git commit 28cc363411d2029aed04c969c8f98785cae110db the attached sample crashes the js-shell when invoked as `obj-x86_64-pc-linux-gnu/dist/bin/js --fuzzing-safe --gc-zeal=10 crash.js`
Bisecting the issue points to commit 0f80a6542954802e72888f3a2e43136a9a56eb65 related to bug 1863939.

```
function probe(value) {
    let originalPrototype, newPrototype;
    let handler = {
        get(target, key, receiver) {
            return Reflect.get(target, key, receiver);
        },
    };

    try {
        originalPrototype = Object.getPrototypeOf(value);
        newPrototype = new Proxy(originalPrototype, handler);
        Object.setPrototypeOf(value, newPrototype);
    } catch (e) {}
}


const v0 = [];
function f1() {
    Object.defineProperty(v0, 5, { configurable: true, get: f1 });
    try { v0.toReversed(); } catch (e) {}
    probe([].__proto__);
}
f1();
```

```
#0  js::CheckTracedThing<js::Shape> (trc=trc@entry=0x7fffffe35a10, thing=0x2726717dab80) at js/src/gc/Marking.cpp:136
#1  0x0000555557f2621c in js::gc::TraceEdgeInternal (trc=0x7fffffe35a10, thingp=0x7ffff54f90e8, Shape=0x555555a43546 "cacheir-weak-shape")
    at js/src/gc/Tracer.h:109
#2  js::TraceSameZoneCrossCompartmentEdge<js::Shape*> (trc=trc@entry=0x7fffffe35a10, dst=dst@entry=0x7ffff54f90e8, name=0x555555a43546 "cacheir-weak-shape")
    at js/src/gc/Marking.cpp:529
#3  0x0000555558534288 in js::jit::TraceCacheIRStub<js::jit::ICCacheIRStub> (trc=trc@entry=0x7fffffe35a10, stub=stub@entry=0x7ffff54f90a8, 
    stubInfo=0x7ffff55c6c00) at js/src/jit/CacheIRCompiler.cpp:1289
#4  0x00005555580c26d4 in js::jit::ICCacheIRStub::trace (this=0x7ffff54f90a8, trc=0x7fffffe35a10) at js/src/jit/BaselineIC.cpp:458
#5  0x00005555587a4968 in js::jit::TraceBaselineStubFrame (trc=0x7fffffe35a10, frame=...) at js/src/jit/JitFrames.cpp:1172
#6  js::jit::TraceJitActivation (trc=0x7fffffe35a10, activation=<optimised out>) at js/src/jit/JitFrames.cpp:1472
#7  js::jit::TraceJitActivations (cx=cx@entry=0x7ffff743ec00, trc=trc@entry=0x7fffffe35a10) at js/src/jit/JitFrames.cpp:1517
#8  0x0000555557f6f092 in js::gc::GCRuntime::traceRuntimeCommon (this=this@entry=0x7ffff742f798, trc=trc@entry=0x7fffffe35a10, 
    traceOrMark=traceOrMark@entry=js::gc::GCRuntime::TraceRuntime) at js/src/gc/RootMarking.cpp:303
#9  0x0000555557f61c66 in js::gc::GCRuntime::traceRuntimeForMinorGC (this=0x7ffff742f798, trc=0x7fffffe35a10, session=...)
    at js/src/gc/RootMarking.cpp:258
#10 js::Nursery::traceRoots (this=this@entry=0x7ffff7431860, session=..., mover=...) at js/src/gc/Nursery.cpp:1634
#11 0x0000555557f5ee2f in js::Nursery::doCollection (this=this@entry=0x7ffff7431860, session=..., options=options@entry=JS::GCOptions::Shrink, 
    reason=reason@entry=JS::GCReason::EVICT_NURSERY) at js/src/gc/Nursery.cpp:1494
#12 0x0000555557f5e302 in js::Nursery::collect (this=0x7ffff7431860, options=JS::GCOptions::Shrink, reason=JS::GCReason::EVICT_NURSERY)
    at js/src/gc/Nursery.cpp:1264
#13 0x0000555557ed5b7d in js::gc::GCRuntime::collectNursery (this=this@entry=0x7ffff742f798, options=JS::GCOptions::Shrink, 
    reason=reason@entry=JS::GCReason::EVICT_NURSERY, phase=phase@entry=js::gcstats::PhaseKind::EVICT_NURSERY_FOR_MAJOR_GC)
    at js/src/gc/GC.cpp:4750
#14 0x0000555557eceac2 in js::gc::GCRuntime::collectNurseryFromMajorGC (this=this@entry=0x7ffff742f798, reason=<optimised out>)
    at js/src/gc/GC.cpp:3893
#15 0x0000555557ece17c in js::gc::GCRuntime::endPreparePhase (this=this@entry=0x7ffff742f798, reason=reason@entry=JS::GCReason::DEBUG_GC)
    at js/src/gc/GC.cpp:2830
#16 0x0000555557ed4c25 in js::gc::GCRuntime::incrementalSlice (this=this@entry=0x7ffff742f798, budget=..., reason=reason@entry=JS::GCReason::DEBUG_GC, 
    budgetWasIncreased=false) at js/src/gc/GC.cpp:3733
#17 0x0000555557ed81fe in js::gc::GCRuntime::gcCycle (this=this@entry=0x7ffff742f798, nonincrementalByAPI=false, budgetArg=..., 
    reason=reason@entry=JS::GCReason::DEBUG_GC) at js/src/gc/GC.cpp:4322
#18 0x0000555557ed9b44 in js::gc::GCRuntime::collect (this=this@entry=0x7ffff742f798, nonincrementalByAPI=false, budget=..., 
    reason=reason@entry=JS::GCReason::DEBUG_GC) at js/src/gc/GC.cpp:4513
#19 0x0000555557ea60d7 in js::gc::GCRuntime::runDebugGC (this=this@entry=0x7ffff742f798) at js/src/gc/GC.cpp:4976
#20 0x0000555557eddba0 in js::gc::CellAllocator::PreAllocChecks<(js::AllowGC)1> (cx=0x7ffff743ec00, kind=<optimised out>)
    at js/src/gc/Allocator.cpp:257
#21 0x00005555572513b4 in js::gc::CellAllocator::AllocNurseryOrTenuredCell<(JS::TraceKind)0, (js::AllowGC)1> (cx=cx@entry=0x7ffff743ec00, 
    allocKind=js::gc::AllocKind::OBJECT2_BACKGROUND, thingSize=40, heap=js::gc::Heap::Default, site=site@entry=0x7ffff559b978)
    at js/src/gc/Allocator-inl.h:114
#22 0x0000555557251238 in js::gc::CellAllocator::NewObject<js::NativeObject, (js::AllowGC)1> (cx=cx@entry=0x7ffff743ec00, 
    kind=kind@entry=js::gc::AllocKind::OBJECT2_BACKGROUND, heap=heap@entry=js::gc::Heap::Default, clasp=clasp@entry=0x55555905cca0 <js::PlainObject::class_>, 
    site=site@entry=0x7ffff559b978) at js/src/gc/Allocator-inl.h:94
#23 0x000055555724fee5 in js::gc::CellAllocator::NewCell<js::NativeObject, (js::AllowGC)1, js::gc::AllocKind&, js::gc::Heap&, JSClass const*&, js::gc::AllocSite*&> (cx=0x7ffff743ec00, args=<optimised out>, args=<optimised out>, args=<optimised out>, args=<optimised out>)
    at js/src/gc/Allocator-inl.h:35
#24 JSContext::newCell<js::NativeObject, (js::AllowGC)1, js::gc::AllocKind&, js::gc::Heap&, JSClass const*&, js::gc::AllocSite*&> (this=0x7ffff743ec00, 
    args=<optimised out>, args=<optimised out>, args=<optimised out>, args=<optimised out>) at js/src/vm/JSContext-inl.h:359
#25 js::NativeObject::create (cx=0x7ffff743ec00, kind=js::gc::AllocKind::OBJECT2_BACKGROUND, heap=js::gc::Heap::Default, shape=..., site=0x7ffff559b978)
    at js/src/vm/NativeObject-inl.h:495
#26 0x000055555729ef8c in js::NativeObject::create<js::PlainObject> (cx=0x7ffff743ec00, kind=js::gc::AllocKind::OBJECT2_BACKGROUND, shape=...,
    site=0x7ffff559b978, heap=<optimised out>) at js/src/vm/NativeObject.h:762
#27 js::NewPlainObjectBaselineFallback (cx=0x7ffff743ec00, shape=..., allocKind=js::gc::AllocKind::OBJECT2_BACKGROUND, site=0x7ffff559b978)
    at js/src/vm/Interpreter.cpp:5101
#28 0x00002af92f171aee in ?? ()
#29 0x00000000000000cf in ?? ()
#30 0x00007fffffe36200 in ?? ()
```

---

**Comment 1 — lukas.bernhard@rub.de — 2024-04-01T08:45:37Z**

```
js::CheckTracedThing<js::Shape> (trc=trc@entry=0x7fffffdfcf00, thing=0x1e8675ddab80)
    at js/src/gc/Marking.cpp:136
136	 if (IsForwarded(thing)) {
(gdb) x/i $rip
=> 0x555557f22ea6 <_ZN2js16CheckTracedThingINS_5ShapeEEEvP8JSTracerPT_+38>:	mov    (%rbx),%rax
(gdb) i r rbx
rbx            0x1e8675ddab80      33562851912576
```

---

**Comment 2 — release-mgmt-account-bot@mozilla.tld — 2024-04-01T13:42:48Z**

Set release status flags based on info from the regressing bug 1863939

:jandem, since you are the author of the regressor, bug 1863939, could you take a look? Also, could you set the severity field?

For more information, please visit [BugBot documentation](https://wiki.mozilla.org/BugBot#needinfo_regression_author.py).

---

**Comment 3 — dveditz@mozilla.com — 2024-04-01T22:56:22Z**

Haven't confirmed, but giving an initial sec-rating based on Lukas' description

---

**Comment 4 — jdemooij@mozilla.com — 2024-04-02T14:52:18Z**

I'm looking into this.

More reduced test:
```js
function f() {
    var v0 = [];
    Object.defineProperty(v0, 0, {get: f});
    try { v0.toReversed(); } catch {}
    var handler = {
        get(target, key, receiver) {
            return Reflect.get(target, key, receiver);
        }
    };
    var proxy = new Proxy(Object.prototype, handler);
    Object.setPrototypeOf(Array.prototype, proxy);
}
gczeal(10);
f();
```

---

**Comment 5 — jdemooij@mozilla.com — 2024-04-02T17:45:22Z**

What's happening is:
1. We have an active Baseline stub on the stack, a Sparse GetElement stub.
2. This stub ends up calling function `f` recursively due to the `0` element getter.
3. `f` also changes `Array.prototype`'s proto to a new (proxy) object, so the original `Array.prototype` shape is now dead.
4. The Baseline CacheIR stub from (1) is still active on the stack. We trace it in `TraceWeakBaselineStubFrame => TraceCacheIRStub` where `trc->traceWeakEdges()` is false, so we don't trace the now dead shape.
5. We later call `TraceWeakCacheIRStub` where we return `false` when we notice the dead shape, but `TraceWeakBaselineStubFrame` ignores this return value.
6. Next time we trace the BaselineStub frame, we find the same stub but a shape field is now garbage and we crash.

Potential fix is to always trace weak edges in `TraceCacheIRStub` when called for Baseline stub frames. That fixes the test locally.

Bug 1863939 may have exposed this, but I think this goes back to bug 1837620.

More reduced test:
```js
function f() {
    try { arr.toReversed(); } catch {}
    var handler = {get() { return arr[0]; }};
    var proxy = new Proxy(Object.prototype, handler);
    Object.setPrototypeOf(Array.prototype, proxy);
}
var arr = [];
Object.defineProperty(arr, 0, {get: f});
gczeal(10);
f();
```

---

**Comment 6 — jdemooij@mozilla.com — 2024-04-03T10:20:58Z**

Created attachment 9394738
Bug 1888892 - Trace all fields in TraceWeakCacheIRStub. r?jonco!

---

**Comment 7 — jdemooij@mozilla.com — 2024-04-03T10:21:09Z**

Created attachment 9394739
Bug 1888892 - Add test and comment. r?jonco!

---

**Comment 8 — jdemooij@mozilla.com — 2024-04-03T12:52:53Z**

Comment on attachment 9394738
Bug 1888892 - Trace all fields in TraceWeakCacheIRStub. r?jonco!

### Security Approval Request
* **How easily could an exploit be constructed based on the patch?**: Not easily. It's hard to trigger this.
* **Do comments in the patch, the check-in comment, or tests included in the patch paint a bulls-eye on the security problem?**: No
* **Which branches (beta, release, and/or ESR) are affected by this flaw, and do the release status flags reflect this affected/unaffected state correctly?**: Release and beta
* **If not all supported branches, which bug introduced the flaw?**: Bug 1837620
* **Do you have backports for the affected branches?**: Yes
* **If not, how different, hard to create, and risky will they be?**: Should apply or be easy to backport.
* **How likely is this patch to cause regressions; how much testing does it need?**: Unlikely to cause regressions.
* **Is the patch ready to land after security approval is given?**: Yes
* **Is Android affected?**: Yes

---

**Comment 9 — tom@mozilla.com — 2024-04-04T12:29:24Z**

Comment on attachment 9394738
Bug 1888892 - Trace all fields in TraceWeakCacheIRStub. r?jonco!

If you can get this uplifted before the deadline (tomorrow) then approved, otherwise let's hold it until next release

---

**Comment 10 — tom@mozilla.com — 2024-04-04T12:30:08Z**

Comment on attachment 9394739
Bug 1888892 - Add test and comment. r?jonco!

I'm going to flag the test so i remember to come back here and add a reminder flag for when the test should land.

---

**Comment 11 — jdemooij@mozilla.com — 2024-04-04T13:33:54Z**

Comment on attachment 9394738
Bug 1888892 - Trace all fields in TraceWeakCacheIRStub. r?jonco!

### Beta/Release Uplift Approval Request
* **User impact if declined**: Security bug, crashes.
* **Is this code covered by automated tests?**: Yes
* **Has the fix been verified in Nightly?**: No
* **Needs manual test from QE?**: No
* **If yes, steps to reproduce**: 
* **List of other uplifts needed**: None
* **Risk to taking this patch**: Low
* **Why is the change risky/not risky? (and alternatives if risky)**: The patch is pretty simple. Instead of returning immediately after seeing a dead field it returns after processing all fields.
* **String changes made/needed**: 
* **Is Android affected?**: Yes

---

**Comment 12 — pulsebot@bmo.tld — 2024-04-04T14:14:51Z**

Pushed by jdemooij@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/a8ef03c9c00a
Trace all fields in TraceWeakCacheIRStub. r=jonco

---

**Comment 13 — aryx.bugmail@gmx-topmail.de — 2024-04-04T21:38:44Z**

https://hg.mozilla.org/mozilla-central/rev/a8ef03c9c00a

---

**Comment 14 — ryanvm@gmail.com — 2024-04-05T13:01:20Z**

Comment on attachment 9394738
Bug 1888892 - Trace all fields in TraceWeakCacheIRStub. r?jonco!

Approved for 125.0b9.

---

**Comment 15 — pulsebot@bmo.tld — 2024-04-05T13:01:34Z**

https://hg.mozilla.org/releases/mozilla-beta/rev/df2d043410cb

---

**Comment 16 — dveditz@mozilla.com — 2024-04-15T09:29:22Z**

Created attachment 9396624
advisory.txt

---

**Comment 17 — release-mgmt-account-bot@mozilla.tld — 2024-05-28T12:01:08Z**

a month ago, dveditz placed a reminder on the bug using the whiteboard tag `[reminder-test 2024-05-28]` .

jandem, please refer to the original comment to better understand the reason for the reminder.

---

**Comment 18 — pulsebot@bmo.tld — 2024-05-28T21:46:25Z**

Pushed by sstanca@mozilla.com:
https://hg.mozilla.org/mozilla-central/rev/c885fbcf42fd
Add test and comment. r=jonco
