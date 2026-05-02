# [WASM-GC] Tables must keep the type context of their element type alive

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1841119
Component: JavaScript: WebAssembly
Bounty: (unknown)
Date: 2023-06-29T16:17:40Z
Keywords: assertion, crash, csectype-uaf, regression, sec-high, testcase

The following testcase crashes on mozilla-central revision 20230629-c93a9e0ad90d (debug build, run with --fuzzing-safe --ion-offthread-compile=off --wasm-function-references --wasm-gc):

    function a(b) {
        binary = wasmTextToBinary(b)
        c = new WebAssembly.Module(binary)
        return new WebAssembly.Instance(c)
    }
    gczeal(9,10)
    t = a(`(module (type (struct ))
        (table (export "")  (ref null 0)
          (elem ( ref.null 0 ))
        )
      )
    `).exports
    f();


Backtrace:

    received signal SIGSEGV, Segmentation fault.
    #0  0x0000555557f06291 in js::wasm::RefType::hierarchy() const ()
    #1  0x000055555816a35d in js::wasm::Table::gcMallocBytes() const ()
    #2  0x00005555580c6fa2 in js::WasmTableObject::finalize(JS::GCContext*, JSObject*) ()
    #3  0x000055555782733b in JSObject::finalize(JS::GCContext*) ()
    #4  0x0000555557826a0f in unsigned long js::gc::Arena::finalize<JSObject>(JS::GCContext*, js::gc::AllocKind, unsigned long) ()
    #5  0x0000555557826458 in bool FinalizeTypedArenas<JSObject>(JS::GCContext*, js::gc::ArenaList&, js::gc::SortedArenaList&, js::gc::AllocKind, js::SliceBudget&) ()
    #6  0x00005555578107c9 in js::gc::GCRuntime::foregroundFinalize(JS::GCContext*, JS::Zone*, js::gc::AllocKind, js::SliceBudget&, js::gc::SortedArenaList&) ()
    #7  0x00005555578118b6 in js::gc::GCRuntime::finalizeAllocKind(JS::GCContext*, js::SliceBudget&) ()
    #8  0x0000555557836064 in sweepaction::SweepActionForEach<ContainerIter<mozilla::EnumSet<js::gc::AllocKind, unsigned long> >, mozilla::EnumSet<js::gc::AllocKind, unsigned long> >::run(js::gc::SweepAction::Args&) ()
    #9  0x000055555783ce31 in sweepaction::SweepActionSequence::run(js::gc::SweepAction::Args&) ()
    #10 0x0000555557835949 in sweepaction::SweepActionForEach<js::gc::SweepGroupZonesIter, JSRuntime*>::run(js::gc::SweepAction::Args&) ()
    #11 0x000055555783ce31 in sweepaction::SweepActionSequence::run(js::gc::SweepAction::Args&) ()
    #12 0x000055555783503f in sweepaction::SweepActionForEach<js::gc::SweepGroupsIter, JSRuntime*>::run(js::gc::SweepAction::Args&) ()
    #13 0x00005555578131c0 in js::gc::GCRuntime::performSweepActions(js::SliceBudget&) ()
    #14 0x000055555775c371 in js::gc::GCRuntime::incrementalSlice(js::SliceBudget&, JS::GCReason, bool) ()
    #15 0x000055555775faae in js::gc::GCRuntime::gcCycle(bool, js::SliceBudget const&, JS::GCReason) ()
    #16 0x0000555557761434 in js::gc::GCRuntime::collect(bool, js::SliceBudget const&, JS::GCReason) ()
    #17 0x0000555557729a0a in js::gc::GCRuntime::gc(JS::GCOptions, JS::GCReason) ()
    #18 0x000055555715f7b5 in JSRuntime::destroyRuntime() ()
    #19 0x0000555556fdd9e5 in js::DestroyContext(JSContext*) ()
    #20 0x0000555556c0d204 in main ()
    rax	0x5555558c1cb2	93824995826866
    rbx	0x7ffff2d07bb0	140737267137456
    rcx	0x5555585b1378	93825042944888
    rdx	0x0	0
    rsi	0x7ffff7105770	140737338431344
    rdi	0x7ffff7104540	140737338426688
    rbp	0x7fffffffd620	140737488344608
    rsp	0x7fffffffd620	140737488344608
    r8	0x7ffff7105770	140737338431344
    r9	0x7ffff7f9a840	140737353721920
    r10	0x2	2
    r11	0x0	0
    r12	0x2cd7dd500000	49305642598400
    r13	0xfffe4b4b4b4b4b4b	-480163195565237
    r14	0x7ffff3e23758	140737285076824
    r15	0x7ffff2d07bb0	140737267137456
    rip	0x555557f06291 <js::wasm::RefType::hierarchy() const+273>
    => 0x555557f06291 <_ZNK2js4wasm7RefType9hierarchyEv+273>:	movl   $0x510,0x0
       0x555557f0629c <_ZNK2js4wasm7RefType9hierarchyEv+284>:	callq  0x555556cac07f <abort>


Marking s-s until triaged. If it turns out to be a sec bug, this should still be disabled on Nightly (wasm-gc).

---

**Comment 1 — choller@mozilla.com — 2023-06-29T16:17:43Z**

Created attachment 9341758
Detailed Crash Information

---

**Comment 2 — choller@mozilla.com — 2023-06-29T16:17:45Z**

Created attachment 9341759
Testcase

---

**Comment 3 — bugmon@mozilla.com — 2023-06-30T00:24:07Z**

Unable to reproduce bug 1841119 using build mozilla-central 20230629085424-c93a9e0ad90d.  Without a baseline, bugmon is unable to analyze this bug.
Removing bugmon keyword as no further action possible.  Please review the bug and re-add the keyword for further analysis.

---

**Comment 4 — rhunt@eqrion.net — 2023-06-30T15:29:47Z**

Interesting, I wonder if this is a case of the instance being finalized before the table, causing the TypeDef the table references to be freed leading to this segfault. If this is the case, this is just an issue with GC types. I'll need to confirm.

---

**Comment 5 — dveditz@mozilla.com — 2023-07-12T22:21:32Z**

sounds like we're reading garbage somewhere, and if it happened to be the right sort of garbage we might get past this MOZ_CRASH

---

**Comment 6 — rhunt@eqrion.net — 2023-07-14T16:55:28Z**

Yeah, we're reading a freed value here that could avoid this MOZ_CRASH. I can confirm this is only and issue with the GC feature, which is disabled by default. I have a fix incoming.

---

**Comment 7 — release-mgmt-account-bot@mozilla.tld — 2023-07-17T12:19:19Z**

The severity field for this bug is set to S3. However, the bug is flagged with the `sec-high` keyword.
:rhunt, could you consider increasing the severity of this security bug?

For more information, please visit [BugBot documentation](https://wiki.mozilla.org/BugBot#severity_high_security.py).

---

**Comment 8 — rhunt@eqrion.net — 2023-09-06T16:26:25Z**

Created attachment 9351831
Bug 1841119 - wasm: Keep recursion group alive for globals, tables, and tags. r?yury


Globals, tables, and tags can refer to specific TypeDef objects stored in RecGroups with the GC extension. These are normally kept alive by their containing instance, but it's possible for exported version of these to outlive their containing instance. This commit adds a strong reference from the JS-API objects to the
RecGroup that a TypeDef is in.

---

**Comment 9 — pulsebot@bmo.tld — 2023-09-08T18:03:59Z**

Pushed by rhunt@eqrion.net:
https://hg.mozilla.org/integration/autoland/rev/e0c97d1317e4
wasm: Keep recursion group alive for globals, tables, and tags. r=yury

---

**Comment 10 — aryx.bugmail@gmx-topmail.de — 2023-09-08T21:20:43Z**

https://hg.mozilla.org/mozilla-central/rev/e0c97d1317e4

---

**Comment 11 — dveditz@mozilla.com — 2024-04-29T06:35:19Z**

Bulk-unhiding security bugs fixed in Firefox 119-121 (Fall 2023). Use "moo-doctrine-subsidy" to filter
