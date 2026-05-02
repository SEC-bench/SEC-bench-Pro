# Bugzilla 2023024 — Embargoed (likely sec-high) CacheIR reserved-slot fuse bug

**Title:** Don't use fuses for reserved slots
**Severity:** embargoed, signals point to **sec-high** (access-restricted Bugzilla entry, ships with a regression test)
**Component:** SpiderMonkey — JIT — CacheIR fuse infrastructure
**File touched:** `js/src/jit/CacheIR.cpp` (`IRGenerator::canOptimizeConstantDataProperty`)
**Fix commit:** `0d8fa127358980af62ad70abdcba632f0c683a91` (Iain Ireland, 2026-03-16, r=jandem)
**Test commit:** `6e91b751bf989146a76a2369da6d090109309fba` (Iain Ireland, 2026-03-16, r=jandem)
**Vulnerable revision:** `0d8fa127358980af62ad70abdcba632f0c683a91~1`
**Phabricator:** D287740 (code) + D287741 (test)
**Bugzilla:** https://bugzilla.mozilla.org/show_bug.cgi?id=2023024 (sec-restricted)
**MFSA:** CVE pending; expected in an upcoming Firefox 149.x / 150 rollup

## Root cause

Ion's CacheIR optimizer can attach a `ConstantDataProperty` stub that reads a property's current value once, caches it as a constant, and relies on an `ObjectFuse` (tripped by Watchtower) to invalidate the stub whenever the property is subsequently written. The decision to attach the stub is made in `IRGenerator::canOptimizeConstantDataProperty` (js/src/jit/CacheIR.cpp:2248).

Watchtower hooks into the `NativeObject` property-write machinery (`setSlot`, `addProperty`, `defineProperty`, etc.). It does **not** observe writes to the object's JSClass-reserved slots, which are mutated directly by engine-internal paths (e.g. `RegExpObject::setLastIndex` called from `RegExp.prototype.exec`). If `canOptimizeConstantDataProperty` attaches a fuse to a property that resolves to a reserved slot, subsequent engine-internal writes to that slot never trip the fuse, and the stub returns the stale cached value forever.

The stale value and the fresh value can have different SpiderMonkey value types. The committed regression test seeds `re.lastIndex = {}` (an ObjectValue), warms up a reader so Ion attaches the ConstantDataProperty stub with the object cached as constant, then calls `re.exec("foofoofoo")` which writes the Int32 match-end index into the reserved slot — bypassing Watchtower. The next read returns an ObjectValue-typed cached value while the actual slot holds an Int32, producing a type-confused Value reaching downstream stubs. In ASAN+debug builds this trips an assertion; in release builds it is a ready-made primitive for a broader exploit chain.

## Fix

```diff
 bool IRGenerator::canOptimizeConstantDataProperty(NativeObject* holder,
                                                   ...) {
   if (!prop.isDataProperty()) {
     return false;
   }
+
+  // Watchtower doesn't watch changes to reserved slots.
+  if (MOZ_UNLIKELY(prop.slot() < JSCLASS_RESERVED_SLOTS(holder->getClass()))) {
+    return false;
+  }

   *objFuse = cx_->zone()->objectFuses.getOrCreate(cx_, holder);
```

A five-line bail-out comparing the resolved slot number against the JSClass's reserved-slot count. If the property is in a reserved slot, the optimizer declines to attach the stub and Ion falls back to an ordinary shape-guarded load.

## Trigger

The committed regression test (`js/src/jit-test/tests/fuses/bug2023024.js`) ships as `poc.js` verbatim:

```js
var re = /foo/g;
re.lastIndex = {};                 // seed RegExp reserved slot with an Object
var obj = Object.create(re);       // inherit re so `obj.lastIndex` resolves up the chain
function read() { return obj.lastIndex; }
for (var i = 0; i < 50; i++) read();   // warm up → Ion attaches ConstantDataProperty
re.exec("foofoofoo");              // engine internals write Int32 into reserved slot
read();                            // vulnerable build returns stale Object; crashes
```

## Verification

```sh
bash spidermonkey/crash_check.sh 2023024
```

Expected: `CONFIMRED: ASSERTION_FAILURE` (type-check inside CacheIR stub execution) or `CONFIMRED: ASAN_CRASH`.
