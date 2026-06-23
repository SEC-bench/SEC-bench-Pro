# Assertion failure: this->flags() == 0, at gc/Cell.h:797

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1886683
CVE: CVE-2024-3857
Component: JavaScript: WebAssembly
Bounty: (unknown)
Date: 2024-03-21T08:22:30Z
Keywords: csectype-uaf, reporter-external, sec-high

Created attachment 9392448
crash.js

Steps to reproduce:

This issue is about a flakey crash in the js-shell invoked as `obj-x86_64-pc-linux-gnu/dist/bin/js --fast-warmup --ion-check-range-analysis --
ion-extra-checks --fuzzing-safe --disable-oom-functions --enable-new-set-methods crash.js`.
I captured a pernos.co trace on my laptop on git commit 6a2a2a52d7e544a2fd5678d04991a7e78b694f22 (which is a couple of days old). On the server, the issue reproduces reliably even on the latest git commit f63ca2952da98e0817bdae0ddf1314281a497106.
Depending on your machine should be able to reproduce locally.

https://pernos.co/debug/Nmk1pGH10Siby2PktNMINw/index.html

```
#0  js::gc::CellWithTenuredGCPointer<js::gc::Cell, js::Shape>::headerPtr (this=<optimized out>)
    at js/src/gc/Cell.h:797
#1  JSObject::shape (this=<optimized out>) at js/src/vm/JSObject.h:93
#2  JSObject::getClass (this=<optimized out>) at js/src/vm/JSObject.h:114
#3  JSObject::is<WasmValueBox> (this=<optimized out>) at js/src/vm/JSObject.h:492
#4  js::wasm::AnyRef::toJSValue (this=<optimized out>) at js/src/wasm/WasmAnyRef.cpp:119
#5  0x00005722f405482f in ToJSValue_externref<js::wasm::NoDebug> (src=0x5722f0c6e5de, dst=..., cx=<optimized out>)
    at js/src/wasm/WasmValue.cpp:757
#6  js::wasm::ToJSValue<js::wasm::NoDebug> (cx=cx@entry=0x7ded5833d200, src=src@entry=0x7ffeab2c6be0, type=..., dst=..., 
    level=level@entry=js::wasm::CoercionLevel::Spec) at js/src/wasm/WasmValue.cpp:820
#7  0x00005722f4053526 in js::wasm::ToJSValue<js::wasm::NoDebug> (cx=0x7ded5833d200, src=src@entry=0x7ffeab2c6be0, type=..., 
    dst=..., level=level@entry=js::wasm::CoercionLevel::Spec) at js/src/wasm/WasmValue.cpp:842
#8  0x00005722f2508fd1 in js::wasm::Instance::callImport (this=0x7ded5397c300, cx=0x7ded5833d200, 
    funcImportIndex=<optimized out>, argc=<optimized out>, argv=0x7ffeab2c6be0)
    at js/src/wasm/WasmInstance.cpp:264
#9  0x00005722f250a424 in js::wasm::Instance::callImport_general (instance=0x7ded586008e0 <_IO_stdfile_2_lock>, 
    funcImportIndex=1482684227, argc=-184039728, argv=0x0) at js/src/wasm/WasmInstance.cpp:349
#10 0x00001e165f9e3ee3 in ?? ()
#11 0x00000f1bebdfff60 in ?? ()
#12 0x3e09a6bdc70b2d00 in ?? ()
#13 0x00007ffeab2c6c80 in ?? ()
```

---

**Comment 1 — lukas.bernhard@rub.de — 2024-03-21T08:28:36Z**

Created attachment 9392449
reliable_crash.js

---

**Comment 2 — lukas.bernhard@rub.de — 2024-03-21T08:29:13Z**

Turns out the fuzzer just found a crasher that works reliably, this should make things easier.

---

**Comment 3 — jdemooij@mozilla.com — 2024-03-21T16:01:24Z**

Slightly reduced test, fails on mozilla-central tip on linux x64 debug. Seems to be an `externref` GC issue?
```js
function f() {
    class C12 {
        m() {
            function f16() {
                return 254;
            }
            function f19() {
                return C12;
            }
            const binary = wasmTextToBinary(`
            (module
                (import "" "allocate" (func $allocate (param i32) (result externref)))
                (import "" "visit" (func $visit (param externref) (result i32)))
                (func $manyParamsAndLocals
                    (export "manyParamsAndLocals")
                    (param $p1 externref)
                    (param $p2 i32)
                    (param $p3 externref)
                    (param $p4 externref)
                    (param $p5 externref)
                    (param $p6 externref)
                    (param $p7 externref)
                    (param $p8 externref)
                    (result i32)
                    (local $l9 externref)
                    (local $i i32)
                    (local $runningTotal i32)
                    (loop $CONT
                        (local.set $l9
                            (call $allocate (i32.and (local.get $i) (i32.const 255))))
                        local.get $runningTotal
                        (call $visit (local.get $p1))
                        i32.add
                        local.set $runningTotal
                        (local.set $i (i32.add (local.get $i) (i32.const 1)))
                        (br_if $CONT (i32.lt_s (local.get $i) (i32.const 10000)))
                    )
                    local.get $runningTotal
                )
            )`);
            const mod = new WebAssembly.Module(binary);
            const imports = {
                "allocate": f16,
                "visit": f19,
            };
            const o30 = {"": imports};
            const instance = new WebAssembly.Instance(mod, o30);
            instance.exports.manyParamsAndLocals();
        }
    }
    C12[Symbol.toPrimitive] = f;
    const v36 = new C12();
    return v36.m();
}
f();
```

---

**Comment 4 — rhunt@eqrion.net — 2024-03-22T19:08:13Z**

Here's a further reduced test-case:
```
function f() {
    class C12 {
        m() {
            function f16() {
                return 0;
            }
            function f19() {
                return C12;
            }
            const binary = wasmTextToBinary(`
            (module
                (import "" "visit" (func $visit (param externref) (result i32)))
                (func $manyParamsAndLocals
                    (export "manyParamsAndLocals")
                    (param $p1 externref)
                    (param $p2 i32)
                    (param $p3 externref)
                    (param $p4 externref)
                    (param $p5 externref)
                    (param $p6 externref)
                    (param $p7 externref)
                    (param $p8 externref)
                    (call $visit (local.get $p1))
                    unreachable
                )
            )`);
            const mod = new WebAssembly.Module(binary);
            const imports = {
                "allocate": f16,
                "visit": f19,
            };
            const instance = new WebAssembly.Instance(mod, {"": imports});
            instance.exports.manyParamsAndLocals();
        }
    }
    C12[Symbol.toPrimitive] = f;
    const v36 = new C12();
    return v36.m();
}
f();
```

The following things seem to make this issue go away:
  1. Removing any more params from the wasm function.
  2. Changing the i32 param to be an externref
  3. Disabling JIT entry stubs into wasm (disabling JIT exit stubs from wasm is fine)
  4. Specifying the `undefined` params that are implicitly passed to manyParamsAndLocals

So my best guess is that something is going wrong in the JIT entry stub when we call the arguments rectifier to handle the mismatch in function parameters. The net results seems to be that we get an invalid pointer that gets dereferenced when we pass it out to JS on the import call side.

---

**Comment 5 — lukas.bernhard@rub.de — 2024-03-22T20:08:06Z**

A similar sample asserts produces a different backtrace, maybe it is helpful. If you think this is a separate issue, let me know and I'll open another ticket.

```
#0  js::gc::detail::GetCellChunkBase (cell=0xfffe2f2f2f2f2f28) at obj-lto/dist/include/js/HeapAPI.h:525
#1  js::gc::detail::CellHasStoreBuffer (cell=0xfffe2f2f2f2f2f28) at obj-lto/dist/include/js/HeapAPI.h:600
#2  js::gc::IsInsideNursery (cell=<optimized out>) at obj-lto/dist/include/js/HeapAPI.h:607
#3  js::gc::IsInsideNursery (obj=<optimized out>) at obj-lto/dist/include/js/HeapAPI.h:619
#4  js::CheckTracedThing<JSObject> (trc=trc@entry=0x7ffffffe6b10, thing=0xfffe2f2f2f2f2f28) at js/src/gc/Marking.cpp:145
#5  0x000055555869d7a0 in js::gc::TraceEdgeInternal (trc=0x7ffffffe6b10, thingp=0x7ffffffe64c0, Object=0x555555af79dd "Instance::traceWasmFrame: normal word")
    at js/src/gc/Tracer.h:109
#6  TraceTaggedPtrEdge<js::wasm::AnyRef>(JSTracer*, js::wasm::AnyRef*, char const*)::{lambda(auto:1)#1}::operator()<JSObject*>(JSObject*) const (this=0x7ffffffe6500, thing=0x2f2a10e461e0)
    at js/src/gc/Marking.cpp:672
#7  js::MapGCThingTyped<TraceTaggedPtrEdge<js::wasm::AnyRef>(JSTracer*, js::wasm::AnyRef*, char const*)::{lambda(auto:1)#1}>(js::wasm::AnyRef const&, TraceTaggedPtrEdge<js::wasm::AnyRef>(JSTracer*, js:
:wasm::AnyRef*, char const*)::{lambda(auto:1)#1}&&) (val=..., f=...) at js/src/wasm/WasmAnyRef.h:371
#8  0x0000555557435575 in TraceTaggedPtrEdge<js::wasm::AnyRef> (trc=0x7ffffffe6b10, thingp=0x7ffffffe7790, name=0x555555af79dd "Instance::traceWasmFrame: normal word")
    at js/src/gc/Marking.cpp:671
#9  js::gc::TraceEdgeInternal (trc=trc@entry=0x7ffffffe6b10, thingp=0x2f2a10e461e0, thingp@entry=0x7ffffffe7790, name=<optimized out>) at js/src/gc/Marking.cpp:702
#10 0x000055555737dd02 in js::TraceNullableRoot<js::wasm::AnyRef> (trc=0x7ffffffe6b10, thingp=<optimized out>, name=<optimized out>) at js/src/gc/Tracer.h:235
#11 js::wasm::Instance::traceFrame (this=<optimized out>, trc=0x7ffffffe6b10, wfi=..., nextPC=<optimized out>, highestByteVisitedInPrevFrame=140737488254975)
    at js/src/wasm/WasmInstance.cpp:2787
#12 0x0000555557a306f6 in js::jit::TraceJitActivation (trc=0x7ffffffe6b10, activation=<optimized out>) at js/src/jit/JitFrames.cpp:1464
#13 js::jit::TraceJitActivations (cx=cx@entry=0x7ffff6b39100, trc=trc@entry=0x7ffffffe6b10) at js/src/jit/JitFrames.cpp:1473
#14 0x00005555571d11c6 in js::gc::GCRuntime::traceRuntimeCommon (this=this@entry=0x7ffff6b2f798, trc=trc@entry=0x7ffffffe6b10, traceOrMark=traceOrMark@entry=js::gc::GCRuntime::TraceRuntime)
    at js/src/gc/RootMarking.cpp:303
#15 0x00005555571c5e4c in js::gc::GCRuntime::traceRuntimeForMinorGC (this=0x7ffff6b2f798, trc=0x7ffffffe6b10, session=...) at js/src/gc/RootMarking.cpp:258
#16 js::Nursery::traceRoots (this=this@entry=0x7ffff6b317f0, session=..., mover=...) at js/src/gc/Nursery.cpp:1522
#17 0x00005555571c3b4c in js::Nursery::doCollection (this=this@entry=0x7ffff6b317f0, session=..., options=options@entry=JS::GCOptions::Normal, reason=reason@entry=JS::GCReason::DEBUG_GC)
    at js/src/gc/Nursery.cpp:1400
#18 0x00005555571c3014 in js::Nursery::collect (this=0x7ffff6b317f0, options=JS::GCOptions::Normal, reason=JS::GCReason::DEBUG_GC) at js/src/gc/Nursery.cpp:1175
#19 0x00005555574bfbd2 in js::gc::GCRuntime::collectNursery (this=this@entry=0x7ffff6b2f798, options=options@entry=JS::GCOptions::Normal, reason=reason@entry=JS::GCReason::DEBUG_GC,
    phase=phase@entry=js::gcstats::PhaseKind::MINOR_GC) at js/src/gc/GC.cpp:4735
#20 0x000055555749d07f in js::gc::GCRuntime::minorGC (this=0x7ffff6b2f798, reason=reason@entry=JS::GCReason::DEBUG_GC, phase=phase@entry=js::gcstats::PhaseKind::MINOR_GC)
    at js/src/gc/GC.cpp:4708
#21 0x000055555749db00 in js::gc::GCRuntime::runDebugGC (this=0x7ffffffe6b10, this@entry=0x7ffff6b2f798) at js/src/gc/GC.cpp:4921
#22 0x00005555577b6df7 in js::gc::CellAllocator::PreAllocChecks<(js::AllowGC)1> (cx=0x7ffff6b39100, kind=<optimized out>) at js/src/gc/Allocator.cpp:256
#23 0x000055555777b5f8 in js::gc::CellAllocator::AllocNurseryOrTenuredCell<(JS::TraceKind)0, (js::AllowGC)1> (cx=0x7ffff6b39100, allocKind=js::gc::AllocKind::OBJECT0_BACKGROUND, thingSize=24,
    heap=js::gc::Heap::Default, site=0x7ffff5a49b20) at js/src/gc/Allocator-inl.h:114
#24 js::gc::CellAllocator::NewObject<js::NativeObject, (js::AllowGC)1> (cx=0x7ffff6b39100, kind=js::gc::AllocKind::OBJECT0_BACKGROUND, heap=js::gc::Heap::Default,
    clasp=0x5555593319b0 <js::PlainObject::class_>, site=0x7ffff5a49b20) at js/src/gc/Allocator-inl.h:94
#25 js::gc::CellAllocator::NewCell<js::NativeObject, (js::AllowGC)1, js::gc::AllocKind&, js::gc::Heap&, JSClass const*&, js::gc::AllocSite*&> (cx=0x7ffff6b39100, args=<optimized out>,
    args=<optimized out>, args=<optimized out>, args=<optimized out>) at js/src/gc/Allocator-inl.h:35
#26 JSContext::newCell<js::NativeObject, (js::AllowGC)1, js::gc::AllocKind&, js::gc::Heap&, JSClass const*&, js::gc::AllocSite*&> (this=0x7ffff6b39100, args=<optimized out>, args=<optimized out>,
    args=<optimized out>, args=<optimized out>) at js/src/vm/JSContext-inl.h:359 
#27 js::NativeObject::create (cx=0x7ffff6b39100, kind=js::gc::AllocKind::OBJECT0_BACKGROUND, heap=js::gc::Heap::Default, shape=..., site=0x7ffff5a49b20)
    at js/src/vm/NativeObject-inl.h:495
#28 0x0000555557d14f43 in js::NativeObject::create<js::PlainObject> (cx=0x7ffff6b39100, kind=js::gc::AllocKind::OBJECT0_BACKGROUND, shape=..., site=0x7ffff5a49b20, heap=<optimized out>)
    at js/src/vm/NativeObject.h:762
#29 js::NewPlainObjectBaselineFallback (cx=0x7ffff6b39100, shape=..., allocKind=js::gc::AllocKind::OBJECT0_BACKGROUND, site=0x7ffff5a49b20)
    at js/src/vm/Interpreter.cpp:5101
#30 0x00003590df7c8aee in ?? ()
#31 0xfc83ede08fa32d00 in ?? ()  
```

---

**Comment 6 — jdemooij@mozilla.com — 2024-03-25T14:58:54Z**

Arguments rectifier + JIT entry stub + externref made me wonder about this: when tracing the JSJitToWasm frame, we only [trace](https://searchfox.org/mozilla-central/rev/0e9ea50a999420d93df0e4e27094952af48dd3b8/js/src/jit/JitFrames.cpp#1397) the actual arguments. The rectifier can push `undefined` for other formal arguments, but these won't be traced, so if the stub uses the fomal argument slots for Wasm boxed `undefined` values, we have a GC hazard.

---

**Comment 7 — jdemooij@mozilla.com — 2024-03-25T16:10:07Z**

Created attachment 9393082
Bug 1886683 - Simplify tracing of arguments in TraceThisAndArguments. r?iain!

---

**Comment 8 — jdemooij@mozilla.com — 2024-03-25T16:10:12Z**

Created attachment 9393083
Bug 1886683 - Add test. r?iain!

---

**Comment 9 — jdemooij@mozilla.com — 2024-03-25T17:27:24Z**

Comment on attachment 9393082
Bug 1886683 - Simplify tracing of arguments in TraceThisAndArguments. r?iain!

### Security Approval Request
* **How easily could an exploit be constructed based on the patch?**: It's possible but not super easy. This code is used for multiple frame types so you'd have to figure out what the bug is and which frame type is affected.
* **Do comments in the patch, the check-in comment, or tests included in the patch paint a bulls-eye on the security problem?**: No
* **Which branches (beta, release, and/or ESR) are affected by this flaw, and do the release status flags reflect this affected/unaffected state correctly?**: All
* **If not all supported branches, which bug introduced the flaw?**: None
* **Do you have backports for the affected branches?**: Yes
* **If not, how different, hard to create, and risky will they be?**: The patch should apply or will be easy to backport.
* **How likely is this patch to cause regressions; how much testing does it need?**: Unlikely. The patch is pretty small and the code is covered by many tests.
* **Is the patch ready to land after security approval is given?**: Yes
* **Is Android affected?**: Yes

---

**Comment 10 — tom@mozilla.com — 2024-03-26T13:36:35Z**

Comment on attachment 9393082
Bug 1886683 - Simplify tracing of arguments in TraceThisAndArguments. r?iain!

Approved to land and uplift

---

**Comment 11 — pulsebot@bmo.tld — 2024-03-26T17:45:42Z**

Pushed by jdemooij@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/e56735907b9c
Simplify tracing of arguments in TraceThisAndArguments. r=iain

---

**Comment 12 — jdemooij@mozilla.com — 2024-03-27T08:50:04Z**

Comment on attachment 9393082
Bug 1886683 - Simplify tracing of arguments in TraceThisAndArguments. r?iain!

### Beta/Release Uplift Approval Request
* **User impact if declined**: Security bugs or crashes.
* **Is this code covered by automated tests?**: Yes
* **Has the fix been verified in Nightly?**: Yes
* **Needs manual test from QE?**: No
* **If yes, steps to reproduce**: 
* **List of other uplifts needed**: None
* **Risk to taking this patch**: Low
* **Why is the change risky/not risky? (and alternatives if risky)**: The fix is pretty small and local.
* **String changes made/needed**: 
* **Is Android affected?**: Yes

---

**Comment 13 — aryx.bugmail@gmx-topmail.de — 2024-03-27T09:16:28Z**

https://hg.mozilla.org/mozilla-central/rev/e56735907b9c

---

**Comment 14 — ryanvm@gmail.com — 2024-03-27T23:21:53Z**

Comment on attachment 9393082
Bug 1886683 - Simplify tracing of arguments in TraceThisAndArguments. r?iain!

Approved for 125.0b6.

---

**Comment 15 — pulsebot@bmo.tld — 2024-03-27T23:25:04Z**

https://hg.mozilla.org/releases/mozilla-beta/rev/f28b61aaa5f9

---

**Comment 16 — ryanvm@gmail.com — 2024-03-30T20:01:29Z**

Comment on attachment 9393082
Bug 1886683 - Simplify tracing of arguments in TraceThisAndArguments. r?iain!

Approved for 115.10esr.

---

**Comment 17 — pulsebot@bmo.tld — 2024-03-30T20:03:04Z**

https://hg.mozilla.org/releases/mozilla-esr115/rev/9f5ce0bf14f3

---

**Comment 18 — dveditz@mozilla.com — 2024-04-15T11:00:26Z**

Created attachment 9396630
advisory.txt

---

**Comment 19 — release-mgmt-account-bot@mozilla.tld — 2024-05-28T12:01:12Z**

2 months ago, tjr placed a reminder on the bug using the whiteboard tag `[reminder-test 2024-05-28]` .

jandem, please refer to the original comment to better understand the reason for the reminder.

---

**Comment 20 — pulsebot@bmo.tld — 2024-05-28T15:59:25Z**

Pushed by jdemooij@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/7c1b22e9a47b
Add test. r=iain

---

**Comment 21 — aryx.bugmail@gmx-topmail.de — 2024-05-28T21:59:47Z**

https://hg.mozilla.org/mozilla-central/rev/7c1b22e9a47b
