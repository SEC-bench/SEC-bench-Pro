# Compartment mismatch with a structured clone of a CCW to a WebAssembly.Memory

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=2023007
Component: JavaScript: WebAssembly
Bounty: (unknown)
Date: 2026-03-12T22:10:39Z
Keywords: ai-involved, assertion, csectype-uaf, sec-high, testcase

Created attachment 9552481
crash_stack.txt

### Summary

**Compartment-mismatch regression** in `JSStructuredCloneWriter::writeSharedWasmMemory` at `/firefox/js/src/vm/StructuredClone.cpp:1573-1600`. The function unwraps a cross-compartment `WasmMemoryObject` but fails to enter its realm before passing the unwrapped object's internal `SharedArrayBufferObject` to `startWrite()`. This violates SpiderMonkey's core compartment invariant and triggers `MOZ_CRASH` in Nightly/Debug builds. In Release builds the check is compiled out, allowing a raw cross-compartment pointer to silently flow into the backref `GCHashMap`.

### Affected Code

**File:** `/firefox/js/src/vm/StructuredClone.cpp`, lines 1573–1600

```cpp
bool JSStructuredCloneWriter::writeSharedWasmMemory(HandleObject obj) {
  MOZ_ASSERT(obj->canUnwrapAs<WasmMemoryObject>());
  ...
  Rooted<WasmMemoryObject*> memoryObj(context(),
                                      &obj->unwrapAs<WasmMemoryObject>());
  //                                   ^^^^^^^^^^^^^^ unwraps CCW → target compartment
  // <<< MISSING: JSAutoRealm ar(context(), memoryObj); >>>

  if (!out.writePair(SCTAG_SHARED_WASM_MEMORY_OBJECT, 0) ||
      !out.writePair(SCTAG_BOOLEAN, memoryObj->isHuge())) {
    return false;
  }

  // Use startWrite to register in memory map for back-reference support.
  MOZ_RELEASE_ASSERT(memoryObj->buffer().is<SharedArrayBufferObject>());
  RootedValue bufferVal(context(), ObjectValue(memoryObj->buffer()));
  //                                           ^^^^^^^^^^^^^^^^^^^ foreign compartment
  return startWrite(bufferVal);   // line 1599 — cross-compartment value passed
}
```

`obj->unwrapAs<WasmMemoryObject>()` strips the CCW, returning a raw pointer into the foreign compartment. `memoryObj->buffer()` returns the `SharedArrayBufferObject` that also lives in that foreign compartment. When passed to `startWrite()`, `context()->check(v)` at line 2133 detects `v.toObject().compartment() != cx->compartment()` and crashes.

The inline comment at line 1596 ("Use startWrite to register in memory map for back-reference support") indicates this was a refactor from a direct `writeSharedArrayBuffer()` call (which handles its own unwrapping) to a recursive `startWrite()` call. The refactor forgot the realm guard.

### Correct Pattern

All three sibling functions establish the precedent:

```cpp
// writeTypedArray (line 1410):
Rooted<TypedArrayObject*> tarr(context(), obj->maybeUnwrapAs<TypedArrayObject>());
JSAutoRealm ar(context(), tarr);    // ← realm entry immediately after unwrap

// writeDataView (line 1457):
Rooted<DataViewObject*> view(context(), obj->maybeUnwrapAs<DataViewObject>());
JSAutoRealm ar(context(), view);    // ← realm entry immediately after unwrap
...
RootedValue val(context(), view->bufferValue());
if (!startWrite(val)) { ... }       // ← safe: cx is now in view's compartment

// writeArrayBuffer (line 1490):
Rooted<ArrayBufferObject*> buffer(context(), obj->maybeUnwrapAs<ArrayBufferObject>());
JSAutoRealm ar(context(), buffer);  // ← realm entry immediately after unwrap
```

### Exploit Chain

1. Content creates `WebAssembly.Memory({shared: true})` in a separate compartment (in the browser: a cross-origin iframe; in shell: `newGlobal({newCompartment: true})`).
2. Content acquires a CCW to that `Memory` object via property access across the compartment boundary.
3. Content calls `structuredClone(ccw)` / `postMessage(ccw)` with SAB permitted (COOP/COEP).
4. `startWrite` → `wasm::IsSharedWasmMemoryObject(obj)` → `writeSharedWasmMemory(obj)` (line 2238).
5. Line 1589 unwraps the CCW → `memoryObj` points into the foreign compartment.
6. Line 1598 extracts `memoryObj->buffer()` — a foreign-compartment `SharedArrayBufferObject*`.
7. Line 1599 calls `startWrite(bufferVal)` without having entered the foreign realm.
8. **Nightly/Debug:** `cx->check(v)` at line 2133 → `ContextChecks::fail` → `MOZ_CRASH_UNSAFE_PRINTF("*** Compartment mismatch...")`.
9. **Release:** `JS_CRASH_DIAGNOSTICS` is undefined (see `/firefox/js/src/util/DiagnosticAssertions.h:16` — only `DEBUG || NIGHTLY_BUILD`), so `cx->check()` compiles to a no-op. Execution proceeds: `startObject(obj)` at line 2146 inserts the raw foreign-compartment `JSObject*` into `Rooted<GCHashMap<JSObject*, uint32_t>> memory` — a traced GC root now holds a cross-compartment edge bypassing the wrapper system.

### Security Impact

**Severity:** sec-moderate to sec-high. Compartment mismatches are treated as security bugs by Mozilla because compartments form the isolation boundary between origins.

**Nightly/Debug:** Content-triggerable safe `MOZ_CRASH` (DoS — the diagnostic caught the violation before harm).

**Release:** The diagnostic is compiled out. A naked cross-compartment pointer enters `Rooted<GCHashMap>`. SpiderMonkey's compartmental GC requires all cross-compartment edges to go through `CrossCompartmentWrapper`s tracked by `Compartment::traceOutgoingCrossCompartmentWrappers`. A raw edge in a rooted map violates this; during per-zone GC the source zone's roots can trace into an unscheduled target zone — a known UAF precondition. Backref-table key confusion (unwrapped vs. wrapped identity) may additionally produce malformed clone buffers.

**Preconditions:** `cross-origin-isolated` (COOP/COEP) for shared WASM memory serialization; target `Memory` object in a different compartment. Both achievable from web content.

### Suggested Fix

Add `JSAutoRealm` immediately after unwrapping, matching `writeTypedArray`/`writeDataView`/`writeArrayBuffer`:

```cpp
  Rooted<WasmMemoryObject*> memoryObj(context(),
                                      &obj->unwrapAs<WasmMemoryObject>());
  JSAutoRealm ar(context(), memoryObj);   // <<< FIX

  if (!out.writePair(SCTAG_SHARED_WASM_MEMORY_OBJECT, 0) ||
      !out.writePair(SCTAG_BOOLEAN, memoryObj->isHuge())) {
    return false;
  }

  MOZ_RELEASE_ASSERT(memoryObj->buffer().is<SharedArrayBufferObject>());
  RootedValue bufferVal(context(), ObjectValue(memoryObj->buffer()));
  return startWrite(bufferVal);
```

---

**Comment 1 — twsmith@mozilla.com — 2026-03-12T22:11:59Z**

Created attachment 9552483
testcase.js

---

**Comment 2 — continuation@gmail.com — 2026-03-12T23:13:59Z**

It looks like Yury worked on this bit of the structured cloning code recently in bug 1821582.

---

**Comment 3 — ydelendik@mozilla.com — 2026-03-13T18:33:56Z**

Agree is with security analysis in the bug description. Also, fix is good, I'll create patches

---

**Comment 4 — ydelendik@mozilla.com — 2026-03-13T20:05:06Z**

Created attachment 9552849
(secure)

---

**Comment 5 — ydelendik@mozilla.com — 2026-03-13T20:05:12Z**

Created attachment 9552850
(secure)



Depends on D287697

---

**Comment 6 — release-mgmt-account-bot@mozilla.tld — 2026-03-16T12:16:55Z**

The severity field for this bug is set to S3. However, the bug is flagged with the `sec-high` keyword.
:yury, could you consider increasing the severity of this security bug?

For more information, please visit [BugBot documentation](https://wiki.mozilla.org/BugBot#severity_high_security.py).

---

**Comment 7 — ydelendik@mozilla.com — 2026-03-16T20:27:16Z**

Comment on attachment 9552849
(secure)

### Security Approval Request
* **How easily could an exploit be constructed based on the patch?**: It is one line fix -- similar to all functions in the same file. IIRC similar bugs end up with UAF exploits.
* **Do comments in the patch, the check-in comment, or tests included in the patch paint a bulls-eye on the security problem?**: No
* **Which branches (beta, release, and/or ESR) are affected by this flaw, and do the release status flags reflect this affected/unaffected state correctly?**: all
* **If not all supported branches, which bug introduced the flaw?**: None
* **Do you have backports for the affected branches?**: No
* **If not, how different, hard to create, and risky will they be?**: It is an added single line patch (that follow `Rooted<WasmMemoryObject*> memoryObj`) -- it will be trivial to add it to e.g. ESR140
* **How likely is this patch to cause regressions; how much testing does it need?**: It needs the poc test (or following patch test) to verify the fix.
* **Is the patch ready to land after security approval is given?**: Yes
* **Is Android affected?**: Yes

---

**Comment 8 — dveditz@mozilla.com — 2026-03-24T01:13:11Z**

Comment on attachment 9552849
(secure)

sec-approval+ to land now without the test, and request uplifts. Please wait until 2026-05-20 or later to land tests (I'll set a reminder in the bug)

---

**Comment 9 — pulsebot@bmo.tld — 2026-03-25T16:50:54Z**

Pushed by ydelendik@mozilla.com:
https://github.com/mozilla-firefox/firefox/commit/a38514932bd9
https://hg.mozilla.org/integration/autoland/rev/5722a9eed71a
Enter the correct realm in writeSharedWasmMemory. r=sfink

---

**Comment 10 — aryx.bugmail@gmx-topmail.de — 2026-03-25T21:27:52Z**

https://hg.mozilla.org/mozilla-central/rev/5722a9eed71a

---

**Comment 11 — release-mgmt-account-bot@mozilla.tld — 2026-03-26T13:43:01Z**

The patch landed in nightly and beta is affected.
:yury, is this bug important enough to require an uplift?
- If yes, please nominate the patch for beta approval.
  - See https://wiki.mozilla.org/Release_Management/Requesting_an_Uplift for documentation on how to request an uplift.
- If no, please set `status-firefox150` to `wontfix`.

For more information, please visit [BugBot documentation](https://wiki.mozilla.org/BugBot#uplift_beta.py).

---

**Comment 12 — ydelendik@mozilla.com — 2026-03-26T15:55:27Z**

Comment on attachment 9552849
(secure)

### Beta/Release Uplift Approval Request
* **User impact if declined/Reason for urgency**: ability to produce exploit
* **Is this code covered by automated tests?**: No
* **Has the fix been verified in Nightly?**: Yes
* **Needs manual test from QE?**: No
* **If yes, steps to reproduce**: 
* **List of other uplifts needed**: None
* **Risk to taking this patch**: Low
* **Why is the change risky/not risky? (and alternatives if risky)**: One line, limited to structured cloning of wasm data
* **String changes made/needed**: 
* **Is Android affected?**: Yes

---

**Comment 13 — ydelendik@mozilla.com — 2026-03-26T18:19:58Z**

Created attachment 9558886
(secure)

---

**Comment 14 — dsmith@mozilla.com — 2026-03-28T12:59:46Z**

Comment on attachment 9552849
(secure)

Approved for 150.0b3

---

**Comment 15 — pulsebot@bmo.tld — 2026-03-28T13:00:10Z**

https://github.com/mozilla-firefox/firefox/commit/50f74442ab15
https://hg.mozilla.org/releases/mozilla-beta/rev/3c3a18b065c3

---

**Comment 16 — dmeehan@mozilla.com — 2026-03-29T08:13:31Z**

Please add a ESR115 uplift request

---

**Comment 17 — pulsebot@bmo.tld — 2026-03-29T08:21:29Z**

https://hg.mozilla.org/releases/mozilla-esr140/rev/ecfd7aabf4be

---

**Comment 18 — ydelendik@mozilla.com — 2026-03-30T14:36:11Z**

Created attachment 9560650
(secure)


Original Revision: https://phabricator.services.mozilla.com/D290230

---

**Comment 19 — phab-bot@bmo.tld — 2026-03-30T14:36:27Z**

### firefox-esr115 Uplift Approval Request
- **User impact if declined/Reason for urgency**: Possible UAF with Wasm memory structured clone
- **Code covered by automated testing?**: no
- **Fix verified in Nightly?**: yes
- **Needs manual QE testing?**: no
- **Steps to reproduce for manual QE testing**: 
- **Risk associated with taking this patch**: low
- **Explanation of risk level**: Landed on m-c, beta and esr140
- **String changes made/needed?**: no
- **Is Android affected?**: yes

---

**Comment 20 — pulsebot@bmo.tld — 2026-03-31T01:22:06Z**

https://hg.mozilla.org/releases/mozilla-esr115/rev/970b50a85b7a

---

**Comment 21 — pulsebot@bmo.tld — 2026-04-02T17:14:46Z**

https://github.com/mozilla-firefox/firefox/commit/240950fb18dd
https://hg.mozilla.org/releases/mozilla-release/rev/897a67f7d1bf

---

**Comment 22 — pulsebot@bmo.tld — 2026-04-02T17:37:55Z**

https://hg.mozilla.org/releases/mozilla-esr140/rev/2ecc01a5f3bd

---

**Comment 23 — pulsebot@bmo.tld — 2026-04-02T18:50:41Z**

https://hg.mozilla.org/releases/mozilla-esr115/rev/98873ea83521

---

**Comment 24 — release-mgmt-account-bot@mozilla.tld — 2026-05-20T12:00:59Z**

2 months ago, dveditz placed a reminder on the bug using the whiteboard tag `[reminder-test 2026-05-20]` .

yury, please refer to the original comment to better understand the reason for the reminder.

---

**Comment 25 — pulsebot@bmo.tld — 2026-05-22T23:23:45Z**

Pushed by ydelendik@mozilla.com:
https://github.com/mozilla-firefox/firefox/commit/f2466a4c119a
https://hg.mozilla.org/integration/autoland/rev/305c9e6ed963
Add regression test for cross-compartment WasmMemory serialization. r=sfink

---

**Comment 26 — ryanvm@gmail.com — 2026-05-23T14:21:36Z**

https://hg-edge.mozilla.org/mozilla-central/rev/305c9e6ed963
