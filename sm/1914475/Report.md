# Assertion failure: this->flags() == 0, at /Users/yury/Work/mozilla-unified/js/src/gc/Cell.h:777

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1914475
Component: JavaScript: WebAssembly
Bounty: (unknown)
Date: 2024-08-22T20:03:13Z
Keywords: csectype-uaf, pernosco, sec-high

Created attachment 9420423
test.js

The attached test case is crashing with stack:

```
[15954] Assertion failure: this->flags() == 0, at /Users/yury/Work/mozilla-unified/js/src/gc/Cell.h:777
#01: js::gc::CellWithTenuredGCPointer<js::gc::Cell, js::Shape>::headerPtr() const[/Users/yury/Work/mozilla-unified/obj-aarch64-apple-darwin23.5.0/dist/bin/js +0x1e1c4]
#02: JSObject::shape() const[/Users/yury/Work/mozilla-unified/obj-aarch64-apple-darwin23.5.0/dist/bin/js +0x1e140]
#03: JSObject::getClass() const[/Users/yury/Work/mozilla-unified/obj-aarch64-apple-darwin23.5.0/dist/bin/js +0x1ec90]
#04: bool JSObject::is<WasmValueBox>() const[/Users/yury/Work/mozilla-unified/obj-aarch64-apple-darwin23.5.0/dist/bin/js +0x196afb8]
#05: js::wasm::AnyRef::toJSValue() const[/Users/yury/Work/mozilla-unified/obj-aarch64-apple-darwin23.5.0/dist/bin/js +0x196b358]
#06: bool ToJSValue_externref<js::wasm::NoDebug>(JSContext*, void*, JS::MutableHandle<JS::Value>)[/Users/yury/Work/mozilla-unified/obj-aarch64-apple-darwin23.5.0/dist/bin/js +0x1c8dc84]
#07: bool js::wasm::ToJSValue<js::wasm::NoDebug>(JSContext*, void const*, js::wasm::PackedType<js::wasm::StorageTypeTraits>, JS::MutableHandle<JS::Value>, js::wasm::CoercionLevel)[/Users/yury/Work/mozilla-unified/obj-aarch64-apple-darwin23.5.0/dist/bin/js +0x1c8c10c]
#08: bool js::wasm::ToJSValue<js::wasm::DebugCodegenVal>(JSContext*, void const*, js::wasm::PackedType<js::wasm::ValTypeTraits>, JS::MutableHandle<JS::Value>, js::wasm::CoercionLevel)[/Users/yury/Work/mozilla-unified/obj-aarch64-apple-darwin23.5.0/dist/bin/js +0x1c8ffdc]
#09: js::wasm::ResultsToJSValue(JSContext*, js::wasm::ResultType, void*, mozilla::Maybe<char*>, JS::MutableHandle<JS::Value>, js::wasm::CoercionLevel)[/Users/yury/Work/mozilla-unified/obj-aarch64-apple-darwin23.5.0/dist/bin/js +0x1b3bca0]
#10: ReturnToJSResultCollector::collect(JSContext*, void*, JS::MutableHandle<JS::Value>, js::wasm::CoercionLevel)[/Users/yury/Work/mozilla-unified/obj-aarch64-apple-darwin23.5.0/dist/bin/js +0x1b3de04]
#11: js::wasm::Instance::callExport(JSContext*, unsigned int, JS::CallArgs const&, js::wasm::CoercionLevel)[/Users...
```

Most likely something is getting GC'ed and used later.

---

**Comment 1 — ydelendik@mozilla.com — 2024-08-23T15:22:03Z**

Pernosco debugging session: https://pernos.co/debug/bZ-skb73GZ989tl40nIanQ/index.html

---

**Comment 2 — ydelendik@mozilla.com — 2024-08-23T17:25:41Z**

Created attachment 9420602
smaller test case

---

**Comment 3 — ydelendik@mozilla.com — 2024-08-23T17:28:11Z**

It is related to Ion caching global's value: ext1 is getting tenured, but the function is still using old reference (see smaller test case)

---

**Comment 4 — jseward@acm.org — 2024-08-27T06:32:16Z**

Created attachment 9420940
testcase1914475.js

Here's an even smaller test case.  It doesn't require multivalue returns
and it doesn't need the MIR optimizer to do GVN on MWasmLoadInstanceDataField
nodes.  So it pretty much rules out any bugs at the MIR level; I guess the
problem is in the LIR or later levels.  We now have
```
===== BuildSSA (== input to OptimizeMIR) =====
  Block0:
    0 = Pointer.wasmparameter
    1 = WasmAnyRef.wasmnullconstant
    2 = WasmAnyRef.wasmloadinstancedatafield (offs=208, isConst=true) 0
    3 = Int32.constant 0x0
    4 = None.wasmcalluncatchable 3 0
    5 = WasmAnyRef.wasmregisterresult
    6 = None.wasmcalluncatchable 2 0 5
    7 = None.wasmreturn 2 0
===== end wasm MIR dump =====

===== BeforeLIR (== result of OptimizeMIR) =====
  Block0:
    0 = Pointer.wasmparameter
    1 = WasmAnyRef.wasmloadinstancedatafield (offs=208, isConst=true) 0
    2 = Int32.constant 0x0
    3 = None.wasmcalluncatchable 2 0
    4 = WasmAnyRef.wasmregisterresult
    5 = None.wasmcalluncatchable 1 0 4
    6 = None.wasmreturn 1 0
===== end wasm MIR dump =====
```
The only change made by OptimizeMIR is to remove `1 = WasmAnyRef.wasmnullconstant`
since it is unused, which seems to me pretty harmless.

---

**Comment 5 — jseward@acm.org — 2024-08-27T06:35:18Z**

Valgrind says this about it, just before the crash.  This makes it clear
that comment 3 is correct.
```
Conditional jump or move depends on uninitialised value(s)
   at 0x21661F5: js::gc::CellWithTenuredGCPointer<js::gc::Cell, js::Shape>::headerPtr() const (src/gc/Cell.h:777)
   by 0x2166184: JSObject::shape() const (src/vm/JSObject.h:93)
   by 0x2166C34: JSObject::getClass() const (src/vm/JSObject.h:114)
 ...
 Uninitialised value was created by a client request
   at 0x3137E53: SetMemCheckKind(void*, unsigned long, MemCheckKind) (src/util/Poison.h:114)
   by 0x3137B80: js::Poison(void*, unsigned char, unsigned long, MemCheckKind) (src/util/Poison.h:198)
   by 0x313F6DB: js::NurseryChunk::poisonRange(unsigned long, unsigned long, unsigned char, MemCheckKind) (src/gc/Nursery.cpp:142)
   by 0x311D001: js::Nursery::poisonAndInitCurrentChunk() (src/gc/Nursery.cpp:2058)
   by 0x3120F08: js::Nursery::collect(JS::GCOptions, JS::GCReason) (src/gc/Nursery.cpp:1320)
```

---

**Comment 6 — jseward@acm.org — 2024-08-27T12:27:58Z**

Created attachment 9420997
Bug 1914475.  r=yury.

---

**Comment 7 — jseward@acm.org — 2024-08-27T12:43:06Z**

What happened is: LWasmCall, to an indirect target, is split into a fast- and
slow-path at the masm level, depending on whether or not it is cross-instance.
That means that some LWasmCall nodes need two stackmaps (LSafepoints).  But a
LIR node can only have at most one LSafepoint.

So we have a kludge, in which the LWasmCall is followed immediately by a
LWasmCallIndirectAdjunctSafepoint, which generates no code and exists only to
carry the second LSafepoint for indirect calls -- for the cross-instance case.
That has been used for some time for calls of the kind
`wasm::CalleeDesc::WasmTable`; however it also needed to be extended to handle
`wasm::CalleeDesc::FuncRef`, but that unfortunately didn't happen until now.

It would be nice in future to remove LWasmCallIndirectAdjunctSafepoint, by
somehow or other making it possible for a LIR node to have more than one
LSafepoint.  That would also allow removing some nasty assumptions / kludgery
in the register allocator.

Triggering the failure required a call-ref to a function in a different
instance, that function to do GC, and to have a GC-object live across the call
site.  So, deep into fuzzer territory.

---

**Comment 8 — jseward@acm.org — 2024-08-30T06:29:07Z**

Comment on attachment 9420997
Bug 1914475.  r=yury.

### Security Approval Request
* **How easily could an exploit be constructed based on the patch?**: I think it would be difficult.  Given the patch, it would require quite some chasing round the source code to infer the circumstances needed to trigger the UAF.  Even if that was successful, it's unclear to me how one would use it to create an exploit.
* **Do comments in the patch, the check-in comment, or tests included in the patch paint a bulls-eye on the security problem?**: No
* **Which branches (beta, release, and/or ESR) are affected by this flaw, and do the release status flags reflect this affected/unaffected state correctly?**: All of beta, release, ESR are affected
* **If not all supported branches, which bug introduced the flaw?**: I don't know; but it has been in-tree at least since we shipped wasm-gc last year
* **Do you have backports for the affected branches?**: No
* **If not, how different, hard to create, and risky will they be?**: The patch is trivial and I expect it would apply directly on older trees; if not, backporting is trivial.
* **How likely is this patch to cause regressions; how much testing does it need?**: Unlikely to cause regression:
* wasm-gc is still relatively lightly used
* the patch gives the GC information about stack layout that was missing before, that it should have had all along

It passes local jit_tests on {x86,x64,arm32,arm64} plus I ran it on try when merged into to a much larger and unrelated patch
* **Is the patch ready to land after security approval is given?**: Yes
* **Is Android affected?**: Yes

---

**Comment 9 — tom@mozilla.com — 2024-09-03T17:25:17Z**

Comment on attachment 9420997
Bug 1914475.  r=yury.

Approved to land and request uplift

---

**Comment 10 — pulsebot@bmo.tld — 2024-09-04T06:30:00Z**

Pushed by jseward@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/548f81df1d27
r=yury.

---

**Comment 11 — ryanvm@gmail.com — 2024-09-05T04:23:58Z**

https://hg.mozilla.org/mozilla-central/rev/548f81df1d27

---

**Comment 12 — release-mgmt-account-bot@mozilla.tld — 2024-09-05T12:02:21Z**

The patch landed in nightly and beta is affected.
:jseward, is this bug important enough to require an uplift?
- If yes, please nominate the patch for beta approval.
- If no, please set `status-firefox131` to `wontfix`.

For more information, please visit [BugBot documentation](https://wiki.mozilla.org/BugBot#uplift_beta.py).

---

**Comment 13 — jseward@acm.org — 2024-09-09T17:08:52Z**

Comment on attachment 9420997
Bug 1914475.  r=yury.

### ESR Uplift Approval Request
* **If this is not a sec:{high,crit} bug, please state case for ESR consideration**: this bug is sec-high
* **User impact if declined**: Potential crashing / JS heap UAF for pages that make use of the Wasm "GC" feature-set.
* **Fix Landed on Version**: 132
* **Risk to taking this patch**: Low
* **Why is the change risky/not risky? (and alternatives if risky)**: * wasm-gc is still relatively lightly used
* the patch gives the GC information about stack layout that was missing before, that it should have had all along

### Beta/Release Uplift Approval Request
* **User impact if declined**: Potential crashing / JS heap UAF for pages that make use of the Wasm "GC" feature-set.  Note: requesting uplift for beta only, not for release.
* **Is this code covered by automated tests?**: No
* **Has the fix been verified in Nightly?**: Yes
* **Needs manual test from QE?**: No
* **If yes, steps to reproduce**: 
* **List of other uplifts needed**: none
* **Risk to taking this patch**: Low
* **Why is the change risky/not risky? (and alternatives if risky)**: * wasm-gc is still relatively lightly used
* the patch gives the GC information about stack layout that was missing before, that it should have had all along
* **String changes made/needed**: none
* **Is Android affected?**: Yes

---

**Comment 14 — ydelendik@mozilla.com — 2024-09-09T17:14:11Z**

Wasm GC feature is enabled/shipped in FF120

---

**Comment 15 — dsmith@mozilla.com — 2024-09-10T18:15:29Z**

Comment on attachment 9420997
Bug 1914475.  r=yury.

Approved for 131.0b5

---

**Comment 16 — pulsebot@bmo.tld — 2024-09-10T18:19:16Z**

https://hg.mozilla.org/releases/mozilla-beta/rev/f58ae106dbe9

---

**Comment 17 — ryanvm@gmail.com — 2024-09-10T19:47:22Z**

Comment on attachment 9420997
Bug 1914475.  r=yury.

Approved for 128.3esr.

---

**Comment 18 — pulsebot@bmo.tld — 2024-09-10T19:48:38Z**

https://hg.mozilla.org/releases/mozilla-esr128/rev/7132eb2b1a48
