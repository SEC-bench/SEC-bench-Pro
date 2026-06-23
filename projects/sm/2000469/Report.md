# Assertion failure: slots == calculateDynamicSlots(), at vm/JSObject-inl.h:36

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=2000469
Component: JavaScript Engine: JIT
Bounty: (unknown)
Date: 2025-11-16T19:35:16Z
Keywords: csectype-jit, regression, reporter-external, sec-high, testcase

Created attachment 9527056
debug stack

```js
var a = ["g"];
function f() {
  const x = {
    set g(z) {
      (function(v) {
        if (b !== undefined) v[a.shift()] = 0;
      })(this);
      this.m = 0;
      this.n = 0;
      for (var y in this);
    },
  };
  x.g = x;
}
new Int8Array(32).reduceRight(f);
var b = 1;
new Int8Array(32).reduceRight(f);
```

```
(gdb) bt
#0  0x00005555575aed72 in MOZ_CrashSequence (aAddress=0x0, aLine=36)
    at /home/msf2/shell-cache/js-dbg-64-linux-x86_64-1c2b83c1fdb8-596556/objdir-js/dist/include/mozilla/Assertions.h:237
#1  js::NativeObject::numDynamicSlots (this=0x13a944e029f0) at /home/msf2/trees/firefox/js/src/vm/JSObject-inl.h:36
#2  0x0000555557649ebf in js::NativeObject::growSlotsPure (cx=0x7ffff5e3c200, obj=0x13a944e029f0, newCapacity=6)
    at /home/msf2/trees/firefox/js/src/vm/NativeObject.cpp:435
#3  0x000033a09a50e607 in ?? ()
#4  0xfff8800000000000 in ?? ()
#5  0x000013a944e029f0 in ?? ()
/snip
```

```
90711c04449c-592521
90711c04449c324bb18eb22522010fe85a051143 is the first interesting commit
commit 90711c04449c324bb18eb22522010fe85a051143
Author: André Bargull
Date:   Tue Oct 21 07:05:41 2025 +0000

    Bug 1991402 - Part 7: Avoid duplicate shape guards for SetSize. r=jandem

    Switch `InlinableNativeIRGenerator::tryAttachSetSize()` to use
    `emitOptimisticClassGuard` in order to emit a shape guard instead of a class
    guard.

    MIR instructions after this change:
    ```
    6 GuardShape <object>
    7 GuardShape GuardShape6
    8 SetObjectSize GuardShape7
    ```

    Then add `MGuardShape::foldsTo` to optimise away the duplicate shape guards.

    Drive-by change:
    - Simplify `M{GuardShape,CallBindVar}::congruentTo` implementations.

    Differential Revision: https://phabricator.services.mozilla.com/D266599
```

Run with `--fuzzing-safe --no-threads --fast-warmup`, compile with `AR=ar sh ~/trees/firefox/js/src/configure --enable-debug --enable-debug-symbols --with-ccache --enable-nspr-build --enable-ctypes --enable-gczeal --enable-rust-simd --disable-tests`, tested on gh rev 1c2b83c1fdb8ba523831bcdb63947f5f7a4cfa5e.

Andre, is bug 1991402 a likely regressor? (Note that a previous similar JIT assert bug 1875795 was marked sec-high)

---

**Comment 1 — release-mgmt-account-bot@mozilla.tld — 2025-11-16T19:43:22Z**

Set release status flags based on info from the regressing bug 1991402

---

**Comment 2 — jdemooij@mozilla.com — 2025-11-21T09:09:04Z**

That's a good find. In `MGuardShape::foldsTo` we check if the object operand is another `MGuardShape` for the same shape, but that isn't valid because between these two instructions the object's shape could be mutated.

---

**Comment 3 — jdemooij@mozilla.com — 2025-11-21T09:10:01Z**

Created attachment 9528277
(secure)

---

**Comment 4 — jdemooij@mozilla.com — 2025-11-21T09:10:08Z**

Created attachment 9528278
(secure)

---

**Comment 5 — andrebargull@googlemail.com — 2025-11-24T10:05:14Z**

Thanks for fixing this bug! I didn't have time last week to look at this issue.

---

**Comment 6 — jdemooij@mozilla.com — 2025-11-24T15:13:20Z**

Comment on attachment 9528277
(secure)

### Security Approval Request
* **How easily could an exploit be constructed based on the patch?**: Not very easily but possible with some effort.
* **Do comments in the patch, the check-in comment, or tests included in the patch paint a bulls-eye on the security problem?**: No
* **Which branches (beta, release, and/or ESR) are affected by this flaw, and do the release status flags reflect this affected/unaffected state correctly?**: 146+
* **If not all supported branches, which bug introduced the flaw?**: Bug 1991402
* **Do you have backports for the affected branches?**: Yes
* **If not, how different, hard to create, and risky will they be?**: Patch should apply.
* **How likely is this patch to cause regressions; how much testing does it need?**: Unlikely, it's just adding an extra check.
* **Is the patch ready to land after security approval is given?**: Yes
* **Is Android affected?**: Yes

---

**Comment 7 — tom@mozilla.com — 2025-11-24T15:37:35Z**

Comment on attachment 9528277
(secure)

Approved to land and request uplift

---

**Comment 8 — jdemooij@mozilla.com — 2025-11-25T07:57:45Z**

Created attachment 9528927
(secure)


Original Revision: https://phabricator.services.mozilla.com/D273543

---

**Comment 9 — phab-bot@bmo.tld — 2025-11-25T07:57:57Z**

### firefox-beta Uplift Approval Request
- **User impact if declined**: Crashes or security issues.
- **Code covered by automated testing**: yes
- **Fix verified in Nightly**: yes
- **Needs manual QE test**: no
- **Steps to reproduce for manual QE testing**: 
- **Risk associated with taking this patch**: low
- **Explanation of risk level**: Very low risk. The patch just adds an extra check to an if-condition.
- **String changes made/needed**: None
- **Is Android affected?**: yes

---

**Comment 10 — pulsebot@bmo.tld — 2025-11-25T07:58:18Z**

Pushed by jdemooij@mozilla.com:
https://github.com/mozilla-firefox/firefox/commit/2fa42593dec7
https://hg.mozilla.org/integration/autoland/rev/7740770d1e8d
Check dependency in MGuardShape::foldsTo. r=iain

---

**Comment 11 — dmeehan@mozilla.com — 2025-11-25T21:04:22Z**

https://hg.mozilla.org/mozilla-central/rev/7740770d1e8d

---

**Comment 12 — pulsebot@bmo.tld — 2025-11-25T23:52:25Z**

https://github.com/mozilla-firefox/firefox/commit/7dae8da5bdd6
https://hg.mozilla.org/releases/mozilla-beta/rev/049b3c4a01de

---

**Comment 13 — pulsebot@bmo.tld — 2026-04-20T10:59:48Z**

Pushed by jdemooij@mozilla.com:
https://github.com/mozilla-firefox/firefox/commit/4f6895e96cb3
https://hg.mozilla.org/integration/autoland/rev/8dbd2bdd3f9f
Add test. r=iain

---

**Comment 14 — ryanvm@gmail.com — 2026-04-20T22:07:22Z**

https://hg-edge.mozilla.org/mozilla-central/rev/8dbd2bdd3f9f
