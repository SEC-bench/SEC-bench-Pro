# Crash [@ js::Nursery::forwardBufferPointer(unsigned long*)]

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1988967
Component: JavaScript Engine
Bounty: (unknown)
Date: 2025-09-17T09:12:16Z
Keywords: crash, csectype-uninitialized, regression, sec-high, testcase

The following testcase crashes on mozilla-central revision 20250916-ae167020f535 (debug build, run with --fuzzing-safe --ion-offthread-compile=off --ion-regalloc=simple):

    function a() {
        a.apply(import("") ^ 0, new Array)
    }
    a()


Backtrace:

    received signal SIGSEGV, Segmentation fault.
    #0  0x0000555557a00975 in js::Nursery::forwardBufferPointer(unsigned long*) ()
    #1  0x00005555580cb9e4 in js::jit::UpdateJitActivationsForMinorGC(JSRuntime*) ()
    #2  0x0000555557a03440 in js::Nursery::doCollection(js::gc::AutoGCSession&, JS::GCOptions, JS::GCReason) ()
    #3  0x0000555557a025e6 in js::Nursery::collect(JS::GCOptions, JS::GCReason) ()
    #4  0x00005555579ae43d in js::gc::GCRuntime::collectNursery(JS::GCOptions, JS::GCReason, js::gcstats::PhaseKind) ()
    #5  0x0000555557994d4e in js::gc::GCRuntime::minorGC(JS::GCReason, js::gcstats::PhaseKind) ()
    #6  0x0000555557951480 in void* js::gc::CellAllocator::RetryNurseryAlloc<(js::AllowGC)1>(JSContext*, JS::TraceKind, js::gc::AllocKind, unsigned long, js::gc::AllocSite*) ()
    #7  0x0000555556ffd2c7 in js::NativeObject* js::gc::CellAllocator::NewObject<js::NativeObject, (js::AllowGC)1>(JSContext*, js::gc::AllocKind, js::gc::Heap, JSClass const*, js::gc::AllocSite*) ()
    #8  0x0000555556ffc3dd in js::NativeObject::create(JSContext*, js::gc::AllocKind, js::gc::Heap, JS::Handle<js::SharedShape*>, js::gc::AllocSite*) ()
    #9  0x00005555572a02ca in NewObject(JSContext*, JSClass const*, JS::Handle<js::TaggedProto>, js::gc::AllocKind, js::NewObjectKind, js::EnumFlags<js::ObjectFlag>, js::gc::AllocSite*) ()
    #10 0x00005555572a05d0 in js::NewObjectWithClassProto(JSContext*, JSClass const*, JS::Handle<JSObject*>, js::gc::AllocKind, js::NewObjectKind, js::EnumFlags<js::ObjectFlag>) ()
    #11 0x00005555573359cd in js::PromiseObject* js::NewObjectWithClassProto<js::PromiseObject>(JSContext*, JS::Handle<JSObject*>) ()
    #12 0x00005555573137b6 in CreatePromiseObjectInternal(JSContext*, JS::Handle<JSObject*>, bool, bool) ()
    #13 0x0000555557313719 in js::CreatePromiseObjectWithoutResolutionFunctions(JSContext*) ()
    #14 0x00005555576684f9 in JS::NewPromiseObject(JSContext*, JS::Handle<JSObject*>) ()
    #15 0x000055555735d339 in js::StartDynamicModuleImport(JSContext*, JS::Handle<JSScript*>, JS::Handle<JS::Value>, JS::Handle<JS::Value>) ()
    #16 0x0000245855d7e9ce in ?? ()
    [...]
    #21 0x0000000000000000 in ?? ()
    rax	0xfffe2d2d2d2d2d2d	-513277898707667
    rbx	0x7ffff4234af0	140737289341680
    rcx	0x325a9cbbffb8	55364758011832
    rdx	0x7ffff4245078	140737289408632
    rsi	0x7ffffffa8728	140737487996712
    rdi	0x7ffff4234af0	140737289341680
    rbp	0x7ffffffa7ce0	140737487994080
    rsp	0x7ffffffa7cc0	140737487994048
    r8	0x0	0
    r9	0xbffb8	786360
    r10	0x0	0
    r11	0x0	0
    r12	0x7ffffffa7d70	140737487994224
    r13	0x7ffffffa7d08	140737487994120
    r14	0x7ffffffa8760	140737487996768
    r15	0x7ffffffa7d78	140737487994232
    rip	0x555557a00975 <js::Nursery::forwardBufferPointer(unsigned long*)+325>
    => 0x555557a00975 <_ZN2js7Nursery20forwardBufferPointerEPm+325>:	mov    (%rax),%rcx
       0x555557a00978 <_ZN2js7Nursery20forwardBufferPointerEPm+328>:	mov    %rcx,(%rax)


Crashes with a poison pattern, marking s-s. It would be good to know why this reproduces specifically with simple regalloc, esp. if it has something to do with recursion depth / frame size.

---

**Comment 1 — choller@mozilla.com — 2025-09-17T09:12:21Z**

Created attachment 9513703
Detailed Crash Information

---

**Comment 2 — choller@mozilla.com — 2025-09-17T09:12:22Z**

Created attachment 9513704
Testcase

---

**Comment 3 — iireland@mozilla.com — 2025-09-17T23:20:45Z**

I looked into this. I suspect that it's a bug in how the simple regalloc creates safepoints involving object elements, but I haven't pinned down the exact problem yet. Here's a snippet of the iongraph that shows what I believe to be the problem:

```
18 {v19<o>:rcx} ← newarray t=(v18<g>:rax)
19 osipoint
20 {v20<o>:rax} ← pointer
0 movegroup [stack:16(8) → rdx, o]
21 guardspecificfunction (rdx), (rax)
0 movegroup [rcx → rbx, o]
22 {v22<o>:rbx} ← guardshape (rbx) t=(v21<g>:rax)
23 guardarrayispacked (rbx) t=(v23<g>:rax, v24<g>:rcx)
24 {v25<s>:rax} ← elements (rbx)
25 {v28<o>:rcx} ← pointer
0 movegroup [rcx → stack:24(8), o], [rsi → stack:8(8), x], [rax → stack:32(8), s]
26 {v29<x>:rcx} ← applyarraygeneric (rcx), (rax), (rsi) t=(v26<g>:rdi, v27<g>:rbx)
27 osipoint
```
At instruction 18, we allocate a new empty nursery array. It has fixed elements, so its elements pointer points into its own storage.
At instruction 24, we load the elements of that array into `rax`. At this point, the array is in `rbx`.
At instruction 26, we use the array in an applyarraygeneric to recursively call this function. This is the final use of the array; it's now dead.
In the movegroup just before that, we spill `rax` (the elements pointer) but not `rbx` (the array itself).

In TraceIonJSFrame, we don't trace the array, because the snapshot thinks it's dead. Later, however, in UpdateJitActivationsForMinorGC, we *do* trace the elements pointer. We expect to find a forwarding address, but instead we read poison (because the elements of the array have never been initialized).

We should not mark the elements pointer live across this call if we don't also mark the array itself.

---

**Comment 4 — bugmon@mozilla.com — 2025-09-18T00:59:27Z**

Verified bug as reproducible on mozilla-central 20250917161633-eb4cc6a1344e.
The bug appears to have been introduced in the following build range:
> Start: deaaef568c3fff7241a6bfdce273d35566663f6c (20250806210618)
> End: 40ecb7a6970690f3c09922e7280771698e08499c (20250806154829)
> Pushlog: https://hg.mozilla.org/mozilla-central/pushloghtml?fromchange=deaaef568c3fff7241a6bfdce273d35566663f6c&tochange=40ecb7a6970690f3c09922e7280771698e08499c

---

**Comment 5 — jdemooij@mozilla.com — 2025-09-18T13:09:49Z**

(In reply to Iain Ireland [:iain] from comment #3)
> In TraceIonJSFrame, we don't trace the array, because the snapshot thinks it's dead. Later, however, in UpdateJitActivationsForMinorGC, we *do* trace the elements pointer. We expect to find a forwarding address, but instead we read poison (because the elements of the array have never been initialized).
> 
> We should not mark the elements pointer live across this call if we don't also mark the array itself.

I think this happens because `LApplyArrayGeneric` 'uses' the elements but not the object, so the simple allocator will mark the elements vreg dead *after* the `LApplyArrayGeneric` instruction but the object's vreg becomes dead *before* that instruction.

This is also related to `AddKeepAliveInstructions` but that pass doesn't insert a keep-alive instruction (for the object) in this case because nothing between the definition and last use can GC. The `LApplyArrayGeneric` itself can GC though so this is a bit questionable. In practice it probably all works out because the elements register is only used at the start of the instruction before we can GC, but I want to check how backtracking handles this.

---

**Comment 6 — jdemooij@mozilla.com — 2025-09-18T13:42:22Z**

I think we should fix this in `AddKeepAliveInstructions` => `NeedsKeepAlive`. Everything probably works fine today with the backtracking allocator because it has more precise live ranges and smarter spilling, but we can make this a bit more robust and that also fixes this for the simple allocator.

---

**Comment 7 — jdemooij@mozilla.com — 2025-09-18T15:28:24Z**

Created attachment 9514058
Bug 1988967 - Also check the use-instruction in NeedsKeepAlive. r?iain!


This patch changes the `AddKeepAliveInstructions` pass to also check the `use`
instruction can't GC instead of only checking the instructions before it.
The effect is that we now add a keep-alive instruction for the object after
`MApplyArray` and `MConstructArray` instructions.

This fixes an issue with the simple allocator for `LApplyArrayGeneric` (which uses
the elements register before making a call that can GC). The simple allocator was
spilling the elements register and then added that stack slot to the safepoint but
not its owner object.

Running jit-tests with extra assertions identified a number of instructions that
can't GC that should be added to the allow-list in `NeedsKeepAlive`, to not change
behavior for those instructions.

---

**Comment 8 — jdemooij@mozilla.com — 2025-09-18T16:23:11Z**

The simple allocator isn't enabled by default.

---

**Comment 9 — pulsebot@bmo.tld — 2025-09-18T23:04:24Z**

Pushed by jdemooij@mozilla.com:
https://github.com/mozilla-firefox/firefox/commit/5dcdd12edecd
https://hg.mozilla.org/integration/autoland/rev/ed701b1540eb
Also check the use-instruction in NeedsKeepAlive. r=iain

---

**Comment 10 — smolnar@mozilla.com — 2025-09-19T08:59:48Z**

https://hg.mozilla.org/mozilla-central/rev/ed701b1540eb

---

**Comment 11 — release-mgmt-account-bot@mozilla.tld — 2025-09-19T12:09:13Z**

Based on comment #4, this bug contains a bisection range found by bugmon. However, the `Regressed by` field is still not filled.

:jandem, if possible, could you fill the `Regressed by` field?

For more information, please visit [BugBot documentation](https://wiki.mozilla.org/BugBot#bisection_without_regressed_by.py).

---

**Comment 12 — bugmon@mozilla.com — 2025-09-20T09:18:42Z**

Verified bug as fixed on rev mozilla-central 20250919085530-7de5f1111de8.
Removing bugmon keyword as no further action possible.  Please review the bug and re-add the keyword for further analysis.

---

**Comment 13 — jdemooij@mozilla.com — 2025-09-22T11:08:27Z**

(In reply to BugBot [:suhaib / :marco/ :calixte] from comment #11)
> :jandem, if possible, could you fill the `Regressed by` field?

I can add bug 1958280, where the simple allocator was added, but I hope the bot isn't going to mark 140+ as affected now...

Note that the fix for this bug wasn't in the simple allocator, but having the SA forces us to have better invariants.
