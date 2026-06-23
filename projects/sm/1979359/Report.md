# Assertion failure: aIndex < mLength, at mozilla/Vector.h:591 with --enable-symbols-as-weakmap-keys

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1979359
Component: JavaScript Engine
Bounty: (unknown)
Date: 2025-07-25T15:14:07Z
Keywords: assertion, csectype-bounds, regression, sec-high, testcase
See Also:
- https://bugzilla.mozilla.org/show_bug.cgi?id=1445260

The following testcase crashes on mozilla-central revision 20250725-12bf685e7003 (debug build, run with --fuzzing-safe --cpu-count=2 --ion-offthread-compile=off --enable-upsert --enable-symbols-as-weakmap-keys):

    gcslice(0)
    g66 = newGlobal({newCompartment: true})
    var baz = Symbol('different description');
    var map = new WeakMap();
    map.getOrInsert(baz, 2)
    gcslice(0)
    var baz = Symbol('different description');
    map.getOrInsert(baz, 2)


Backtrace:

    received signal SIGSEGV, Segmentation fault.
    #0  0x00005555575d6349 in js::gc::GCRuntime::isSymbolReferencedByUncollectedZone(JS::Symbol*) ()
    #1  0x00005555575d582e in js::WeakMap<JS::Value, JS::Value>::markEntry(js::GCMarker*, js::gc::CellColor, js::HeapPtr<JS::Value>&, js::HeapPtr<JS::Value>&, bool) ()
    #2  0x00005555575d3c9e in js::WeakMap<JS::Value, JS::Value>::markEntries(js::GCMarker*) ()
    #3  0x00005555579d46ab in CallTraceHook(JSTracer*, JSObject*) ()
    #4  0x00005555579d2c33 in bool js::GCMarker::processMarkStackTop<0u>(JS::SliceBudget&) ()
    #5  0x00005555579d2322 in bool js::GCMarker::markOneColor<0u, (js::gc::MarkColor)2>(JS::SliceBudget&) ()
    #6  0x00005555579b5ed4 in bool js::GCMarker::doMarking<0u>(JS::SliceBudget&, js::gc::ShouldReportMarkTime) ()
    #7  0x000055555798dfa3 in js::GCMarker::markUntilBudgetExhausted(JS::SliceBudget&, js::gc::ShouldReportMarkTime) ()
    #8  0x000055555798d24b in js::gc::GCRuntime::markUntilBudgetExhausted(JS::SliceBudget&, js::gc::GCRuntime::ParallelMarking, js::gc::ShouldReportMarkTime) ()
    #9  0x0000555557992557 in js::gc::GCRuntime::incrementalSlice(JS::SliceBudget&, JS::GCReason, bool) ()
    #10 0x0000555557996083 in js::gc::GCRuntime::gcCycle(bool, JS::SliceBudget const&, JS::GCReason) ()
    #11 0x00005555579978dd in js::gc::GCRuntime::collect(bool, JS::SliceBudget const&, JS::GCReason) ()
    #12 0x00005555579732aa in js::gc::GCRuntime::finishGC(JS::GCReason) ()
    #13 0x00005555573a35b9 in JSRuntime::destroyRuntime() ()
    #14 0x0000555557238e90 in js::DestroyContext(JSContext*) ()
    #15 0x0000555556ebbc41 in main ()
    rax	0x0	0
    rbx	0x7ffff4232888	140737289332872
    rcx	0x24f	591
    rdx	0x7ffff7804563	140737345766755
    rsi	0x0	0
    rdi	0x7ffff7805700	140737345771264
    rbp	0x7fffffffcfd0	140737488342992
    rsp	0x7fffffffcfb0	140737488342960
    r8	0x0	0
    r9	0x3	3
    r10	0x0	0
    r11	0x293	659
    r12	0xfffba37b6ab94030	-1227624416722896
    r13	0xfffb800000000000	-1266637395197952
    r14	0x228	552
    r15	0xfffb800000000000	-1266637395197952
    rip	0x5555575d6349 <js::gc::GCRuntime::isSymbolReferencedByUncollectedZone(JS::Symbol*)+505>
    => 0x5555575d6349 <_ZN2js2gc9GCRuntime35isSymbolReferencedByUncollectedZoneEPN2JS6SymbolE+505>:	mov    %rcx,(%rax)
       0x5555575d634c <_ZN2js2gc9GCRuntime35isSymbolReferencedByUncollectedZoneEPN2JS6SymbolE+508>:	call   0x555556f58350 <abort>


I think `--enable-upsert` is not yet turned on in Nightly - if it is though, please adjust the status flag accordingly.

---

**Comment 1 — choller@mozilla.com — 2025-07-25T15:14:11Z**

Created attachment 9502964
Detailed Crash Information

---

**Comment 2 — choller@mozilla.com — 2025-07-25T15:14:12Z**

Created attachment 9502965
Testcase

---

**Comment 3 — bugmon@mozilla.com — 2025-07-25T17:00:17Z**

Verified bug as reproducible on mozilla-central 20250725093757-12bf685e7003.
The bug appears to have been introduced in the following build range:
> Start: 7a5a05919345c7a0cd52e7ec5cca6dd3d111af03 (20250616071415)
> End: 4130049d20533018516d5380e1e958a716e706a2 (20250616081649)
> Pushlog: https://hg.mozilla.org/integration/autoland/pushloghtml?fromchange=7a5a05919345c7a0cd52e7ec5cca6dd3d111af03&tochange=4130049d20533018516d5380e1e958a716e706a2

---

**Comment 4 — release-mgmt-account-bot@mozilla.tld — 2025-07-25T19:42:14Z**

Set release status flags based on info from the regressing bug 1967693

:jonco, since you are the author of the regressor, bug 1967693, could you take a look? Also, could you set the severity field?

For more information, please visit [BugBot documentation](https://wiki.mozilla.org/BugBot#needinfo_regression_author.py).

---

**Comment 5 — jcoppeard@mozilla.com — 2025-07-29T13:55:52Z**

This doesn't require upsert and can be reproduced with the `--enable-symbols-as-weakmap-keys` option only:

```
gcslice(0);
newGlobal({newCompartment: true});
var key = Symbol('foo');
var map = new WeakMap();
map.set(key, 2);
gcslice(0);
var key = Symbol('bar');
map.set(key, 2);
```

---

**Comment 6 — jcoppeard@mozilla.com — 2025-07-29T14:17:08Z**

Note that symbols as weakmap keys is not enabled by default and is only present on nightly.

---

**Comment 7 — jcoppeard@mozilla.com — 2025-07-29T15:47:36Z**

Created attachment 9503646
(secure)


Add a range check for atomsUsedByUncollectedZones since atoms allocated after
the start of the collection will not be present in this bitmap.

---

**Comment 8 — jcoppeard@mozilla.com — 2025-07-31T13:16:19Z**

Comment on attachment 9503646
(secure)

### Security Approval Request
* **How easily could an exploit be constructed based on the patch?**: The crash requires symbols as weakmap keys to be enabled, which is only available on nightly and is off by default.
* **Do comments in the patch, the check-in comment, or tests included in the patch paint a bulls-eye on the security problem?**: No
* **Which branches (beta, release, and/or ESR) are affected by this flaw, and do the release status flags reflect this affected/unaffected state correctly?**: The code present on beta and release, but only nightly is affected
* **If not all supported branches, which bug introduced the flaw?**: Bug 1967693
* **Do you have backports for the affected branches?**: No
* **If not, how different, hard to create, and risky will they be?**: Trivial, same patch should apply.
* **How likely is this patch to cause regressions; how much testing does it need?**: Very unlikely, it simply adds a bounds check.
* **Is the patch ready to land after security approval is given?**: Yes
* **Is Android affected?**: Yes

---

**Comment 9 — continuation@gmail.com — 2025-07-31T15:30:48Z**

Comment on attachment 9503646
(secure)

Nightly-only sec problems don't need sec approval to land.

---

**Comment 10 — pulsebot@bmo.tld — 2025-08-01T13:53:35Z**

Pushed by jcoppeard@mozilla.com:
https://github.com/mozilla-firefox/firefox/commit/56674d4f9366
https://hg.mozilla.org/integration/autoland/rev/b1e49d490fba
Add range check in GCRuntime::isSymbolReferencedByUncollectedZone r=jandem

---

**Comment 11 — bugmon@mozilla.com — 2025-08-02T11:05:26Z**

Testcase crashes using the initial build (mozilla-central 20250725093757-12bf685e7003) but not with tip (mozilla-central 20250802092837-66eb1bb3ac0a.)

The bug appears to have been fixed in the following build range:
> Start: 7b615774792e08b3b3bad5b42637da553e33862d (20250801134152)
> End: b1e49d490fbabcb922bad16ca2dd248283199f43 (20250801135321)
> Pushlog: https://hg.mozilla.org/integration/autoland/pushloghtml?fromchange=7b615774792e08b3b3bad5b42637da553e33862d&tochange=b1e49d490fbabcb922bad16ca2dd248283199f43


jonco, can you confirm that the above bisection range is responsible for fixing this issue?
Removing bugmon keyword as no further action possible.  Please review the bug and re-add the keyword for further analysis.

---

**Comment 12 — ryanvm@gmail.com — 2025-08-02T13:39:22Z**

https://hg-edge.mozilla.org/mozilla-central/rev/b1e49d490fba
