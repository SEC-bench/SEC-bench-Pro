# Escape analysis bypass via phi in [@ IsWasmStructEscaped] leaves uninitialized anyref in live Wasm GC struct

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=2024918
Component: JavaScript: WebAssembly
Bounty: (unknown)
Date: 2026-03-20T12:52:39Z
Keywords: ai-involved, crash, csectype-wildptr, regression, sec-high, testcase

### Summary

**Type:** Uninitialized heap memory → GC type confusion / wild pointer dereference  
**File:** [`js/src/jit/ScalarReplacement.cpp`](https://searchfox.org/firefox-main/source/js/src/jit/ScalarReplacement.cpp#3900), line 3900  
**Root cause:** `IsWasmStructEscaped` is called recursively when walking through phi nodes (`IsWasmStructEscaped(phi, newStruct)`), but the `WasmStoreFieldRef` case compares `value()` against the original `newStruct` parameter instead of the current iteration cursor `ins`. When the cursor is a phi and the phi is the `value()` operand of a store into an *escaping* struct, the comparison `phi == newStruct` is always false — the escape is missed. Scalar replacement then discards the struct's init store while the `MWasmNewStructObject(zeroFields=false)` allocation — which skips field zeroing at [`MacroAssembler.cpp:7645`](https://searchfox.org/firefox-main/source/js/src/jit/MacroAssembler.cpp#7645) — still reaches the heap with raw nursery garbage in a GC-traced `anyref` slot.

### Affected Code

**File:** [`js/src/jit/ScalarReplacement.cpp`](https://searchfox.org/firefox-main/source/js/src/jit/ScalarReplacement.cpp#3857-3937), line 3900

```cpp
static bool IsWasmStructEscaped(MDefinition* ins, MInstruction* newStruct) {
  ...
  for (MUseIterator i(ins->usesBegin()); i != ins->usesEnd(); i++) {
    ...
    MDefinition* def = consumer->toDefinition();
    switch (def->op()) {
      ...
      case MDefinition::Opcode::WasmStoreFieldRef: {
        // Escaped if it's stored into another struct.
        if (def->toWasmStoreFieldRef()->value() == newStruct) {  // <-- BUG: should compare to `ins`
          JitSpewDef(JitSpew_Escape, "is escaped by\n", def);
          return true;
        }
        break;
      }
      ...
      case MDefinition::Opcode::Phi: {
        auto* phi = def->toPhi();
        if (!WasmStructPhiOperandsEqualTo(phi, newStruct)) { ... return true; }
        if (IsWasmStructEscaped(phi, newStruct)) {           // <-- recursion: ins becomes `phi`
          ... return true;
        }
        break;
      }
```

**Why it's wrong:** At line 3883 the loop iterates `ins->usesBegin()`. Any consumer found there uses `ins`, not `newStruct`. In the top-level call `ins == newStruct` so the check happens to work. But after the recursion at line 3917, `ins` is the phi — so a `WasmStoreFieldRef` whose `value()` is the phi will satisfy `value() != newStruct`, and the function treats the store as using the phi as its **base** (safe) when it's actually the **value** (escaping).

### Connection to MIR-wasm.cpp

`MWasmStructState` at `MIR-wasm.cpp:1019-1045` is the state-tracking infrastructure that scalar replacement uses. `MWasmStructState::init()` sizes `fields_` based on `wasmStruct_->toWasmNewStructObject()->structType().fields_.length()`. The state machine assumes that after SR completes, `struct_->hasUses()` is false — enforced only by `MOZ_ASSERT` (debug-only) at `ScalarReplacement.cpp:3648`. When the escape bypass occurs, `MWasmStructState` correctly tracks the field values but the `MWasmNewStructObject` itself leaks into the graph with no init stores and `zeroFields=false`, violating the invariant that `MWasmStructState` relies on.

### Exploit Chain

1. **Wasm source defines three struct types:** `$Inner` (holds `anyref`), `$Outer` (holds `ref $Inner`), `$Container` (holds `ref $Inner`, escapes via global).
2. **Ion compiles `run` after warmup.** MIR contains:
   - `s1 = MWasmNewStructObject($Outer, zeroFields=false)`
   - `s2 = MWasmNewStructObject($Inner, zeroFields=false)`
   - `container = MWasmNewStructObject($Container, ...)` — escapes via global, **never SR-eligible**.
   - `StoreA = MWasmStoreFieldRef(base=s1, value=s2)` before the loop.
   - Inside the loop: `Load = MWasmLoadField(base=s1)` → `StoreB = MWasmStoreFieldRef(base=container, value=Load)` → `StoreC = MWasmStoreFieldRef(base=s1, value=s2)`.
3. **`ScalarReplacement` iterates RPO. `s1` is defined first, processed first.**
4. **Escape check for `s1` passes:** all its uses are as `base()` of loads/stores.
5. **SR on `s1` runs.** `mergeIntoSuccessorState` creates `Phi1` at the loop header for `s1`'s field (loop has 2 predecessors). `StoreA` sets state to `s2` pre-loop; `StoreC` sets state to `s2` at backedge → `Phi1 = phi(s2, s2)`. `visitWasmLoadField` replaces `Load` with `Phi1`, so `StoreB` becomes `MWasmStoreFieldRef(base=container, value=Phi1)`. `StoreA` and `StoreC` are **discarded**.
6. **Driver loop reaches `s2`. Escape check `IsWasmStructEscaped(s2, s2)`:**
   - `s2`'s init store: `value() = i31ref ≠ s2` → safe (s2 is base).
   - `s2` feeds `Phi1`: `WasmStructPhiOperandsEqualTo(Phi1, s2)` → true (both inputs are `s2`). Recurse: `IsWasmStructEscaped(Phi1, s2)`.
   - `Phi1` is used by `StoreB`. **Line 3900: `StoreB->value() == s2`? → `Phi1 == s2`? → FALSE.** Escape missed.
   - Returns **not escaped**. ← **Bug triggered.**
7. **SR on `s2` runs:** `visitWasmStoreFieldRef` discards `s2`'s init store. `visitPhi` replaces `Phi1` with `s2` → `StoreB` is now `MWasmStoreFieldRef(base=container, value=s2)`.
8. **`assertSuccess` is a no-op in release** — `MOZ_ASSERT(!struct_->hasUses())` would fire in debug since `StoreB` still uses `s2`.
9. **Codegen:** `wasmNewStructObject` with `zeroFields=false` does `wasmBumpPointerAllocate` + shape/supertype stores, **skips the zeroing loop at line 7645**. `s2`'s field 0 contains **raw prior nursery contents**.
10. **Runtime:** `s2` (uninitialized) is stored into `container`, `container` is in global `$g`. `read()` dereferences `s2->field[0]` as `anyref` → wild pointer. Or GC traces `container → s2 → garbage` in `WasmStructObject::obj_trace` → follows garbage as object edge → SEGV in `TenuringTracer::onObjectEdge`.

### Security Impact

**Severity:** sec-high / sec-critical

**Attacker capability:** A malicious webpage can deliver wasm with this struct-chaining pattern to the content-process Ion compiler (Wasm GC ships by default). The nursery is a bump-pointer allocator with no reuse poisoning in release; the attacker can spray it with arbitrary 64-bit values before triggering the bug, placing a **chosen 64-bit word** into the uninitialized `anyref` slot. Since the GC will subsequently `TraceEdge` this value as a `JSObject*`, this is a **fake-object primitive** — the attacker can point the GC at attacker-controlled memory, leading to arbitrary read/write and code execution in the content process.

**Preconditions:** None beyond default Ion/Wasm-GC — triggers under `--fuzzing-safe` with standard tiering (`--fast-warmup` only accelerates). No user interaction beyond visiting a page.

**Differential:** `--ion-scalar-replacement=off` → correct output `final: -1052688063`. Default → crash.

### Suggested Fix

Compare `value()` against the current iteration cursor `ins`:

```cpp
--- a/js/src/jit/ScalarReplacement.cpp
+++ b/js/src/jit/ScalarReplacement.cpp
@@ -3897,7 +3897,7 @@ static bool IsWasmStructEscaped(MDefinition* ins, MInstruction* newStruct) {
       }
       case MDefinition::Opcode::WasmStoreFieldRef: {
         // Escaped if it's stored into another struct.
-        if (def->toWasmStoreFieldRef()->value() == newStruct) {
+        if (def->toWasmStoreFieldRef()->value() == ins) {
           JitSpewDef(JitSpew_Escape, "is escaped by\n", def);
           return true;
         }
```

Additionally, upgrade `assertSuccess` at line 3648 from `MOZ_ASSERT` to `MOZ_RELEASE_ASSERT(!struct_->hasUses())` — an escaping non-zeroed struct is always a memory-safety hazard.

---

**Comment 1 — bugmon@mozilla.com — 2026-03-20T12:52:43Z**

Created attachment 9555539
Crash stack trace

---

**Comment 2 — bugmon@mozilla.com — 2026-03-20T12:52:44Z**

Created attachment 9555540
Testcase: testcase.js

---

**Comment 3 — jdemooij@mozilla.com — 2026-03-20T16:19:16Z**

Julien, needinfo'ing you since you did work on scalar replacement before.

---

**Comment 4 — rhunt@eqrion.net — 2026-03-20T20:56:17Z**

Sorry for the mid-air collision, but I wrote up a quick fix for this. The analysis and suggested fix are correct. The regressing bug is bug 1947614.

I "cleaned up" the hard coded '3' constant by changing:
```
       if (def->indexOf(*i) == 3) {
```
to:
```
        if (def->toWasmStoreFieldRef()->value() == newStruct) {
```

Which is the vulnerable form.

---

**Comment 5 — rhunt@eqrion.net — 2026-03-20T20:56:40Z**

Created attachment 9555747
(secure)

---

**Comment 6 — rhunt@eqrion.net — 2026-03-20T20:56:56Z**

Created attachment 9555748
(secure)

---

**Comment 7 — jpages@mozilla.com — 2026-03-20T22:47:29Z**

The analysis and the fix also look good to me.

---

**Comment 8 — release-mgmt-account-bot@mozilla.tld — 2026-03-23T12:16:22Z**

The bug has a release status flag that shows some version of Firefox is affected, thus it will be considered confirmed.

---

**Comment 9 — rhunt@eqrion.net — 2026-03-27T15:14:29Z**

Comment on attachment 9555747
(secure)

### Security Approval Request
* **How easily could an exploit be constructed based on the patch?**: Not easy for a human. Requires knowledge of Ion/scalar replacement algorithm. Maybe easier for Claude?
* **Do comments in the patch, the check-in comment, or tests included in the patch paint a bulls-eye on the security problem?**: No
* **Which branches (beta, release, and/or ESR) are affected by this flaw, and do the release status flags reflect this affected/unaffected state correctly?**: Beta, release, ESR. Flags are right.
* **If not all supported branches, which bug introduced the flaw?**: None
* **Do you have backports for the affected branches?**: Yes
* **If not, how different, hard to create, and risky will they be?**: One line change.
* **How likely is this patch to cause regressions; how much testing does it need?**: Unlikely, it passes all our tests, and just reverts a bad change to a known good previous.
* **Is the patch ready to land after security approval is given?**: Yes
* **Is Android affected?**: Yes

---

**Comment 10 — dveditz@mozilla.com — 2026-03-27T17:29:38Z**

Comment on attachment 9555747
(secure)

sec-approval+ to land now and request uplifts; please wait until May to land the tests

---

**Comment 11 — pulsebot@bmo.tld — 2026-03-28T02:03:32Z**

Pushed by rhunt@eqrion.net:
https://github.com/mozilla-firefox/firefox/commit/1c39b127b06b
https://hg.mozilla.org/integration/autoland/rev/5927bf0cbc3d
Fix scalar replacement. r=jseward,jpages

---

**Comment 12 — aryx.bugmail@gmx-topmail.de — 2026-03-28T20:11:45Z**

https://hg.mozilla.org/mozilla-central/rev/5927bf0cbc3d

---

**Comment 13 — release-mgmt-account-bot@mozilla.tld — 2026-03-30T12:03:41Z**

The patch landed in nightly and beta is affected.
:rhunt, is this bug important enough to require an uplift?
- If yes, please nominate the patch for beta approval.
  - See https://wiki.mozilla.org/Release_Management/Requesting_an_Uplift for documentation on how to request an uplift.
- If no, please set `status-firefox150` to `wontfix`.

For more information, please visit [BugBot documentation](https://wiki.mozilla.org/BugBot#uplift_beta.py).

---

**Comment 14 — choller@mozilla.com — 2026-03-31T13:06:26Z**

*** Bug 2027986 has been marked as a duplicate of this bug. ***

---

**Comment 15 — phab-bot@bmo.tld — 2026-03-31T15:52:44Z**

### firefox-beta Uplift Approval Request
- **User impact if declined/Reason for urgency**: fakeObj primitive that can lead to arbitrary read/write.
- **Code covered by automated testing?**: yes
- **Fix verified in Nightly?**: yes
- **Needs manual QE testing?**: no
- **Steps to reproduce for manual QE testing**: 
- **Risk associated with taking this patch**: low
- **Explanation of risk level**: Reverts an optimization back to a previous good state.
- **String changes made/needed?**: N/A
- **Is Android affected?**: yes

---

**Comment 16 — rhunt@eqrion.net — 2026-03-31T15:52:44Z**

Created attachment 9562243
(secure)


Original Revision: https://phabricator.services.mozilla.com/D288998

---

**Comment 17 — phab-bot@bmo.tld — 2026-03-31T15:53:03Z**

### firefox-esr140 Uplift Approval Request
- **User impact if declined/Reason for urgency**: fakeObj primitive that can lead to arbitrary read/write.
- **Code covered by automated testing?**: yes
- **Fix verified in Nightly?**: yes
- **Needs manual QE testing?**: no
- **Steps to reproduce for manual QE testing**: 
- **Risk associated with taking this patch**: low
- **Explanation of risk level**: Reverts an optimization back to a previous good state.
- **String changes made/needed?**: N/A
- **Is Android affected?**: yes

---

**Comment 18 — rhunt@eqrion.net — 2026-03-31T15:53:03Z**

Created attachment 9562244
(secure)


Original Revision: https://phabricator.services.mozilla.com/D288998

---

**Comment 19 — pulsebot@bmo.tld — 2026-03-31T19:32:06Z**

https://github.com/mozilla-firefox/firefox/commit/79331863ae46
https://hg.mozilla.org/releases/mozilla-beta/rev/1f77dfc560d1

---

**Comment 20 — release-mgmt-account-bot@mozilla.tld — 2026-05-05T12:01:10Z**

a month ago, dveditz placed a reminder on the bug using the whiteboard tag `[reminder-test 2026-05-05]` .

rhunt, please refer to the original comment to better understand the reason for the reminder.
