# Bugzilla 2012018 / CVE-2026-2763

**Title:** Use-after-free in the JavaScript Engine (`SuppressDeletedProperty` proxy re-entry)
**Severity:** sec-high (MFSA 2026-13)
**Component:** SpiderMonkey — JavaScript Engine — for-in iteration / `NativeIterator`
**File touched:** `js/src/vm/Iteration.cpp` (`SuppressDeletedProperty` / `SuppressDeletedPropertyHelper`)
**Fix commit:** `2292742e2bba10cc7f56ff2f0f89f29e6f949b04` ("Bug 2012018 - Simplify property lookup in SuppressDeletedProperty. r=iain", Jan de Mooij, 2026-01-29, Phabricator D280679)
**Vulnerable revision:** `2292742e2bba10cc7f56ff2f0f89f29e6f949b04~1`
**Credit:** Evyatar Ben Asher, Keane Lucas, Nicholas Carlini, Newton Cheng, Daniel Freeman, Alex Gaynor, and Joel Weinberger using Claude from Anthropic.

## Summary

`SuppressDeletedProperty` walks the per-compartment list of active
`NativeIterator`s after a property delete, hides the deleted key from any
in-progress `for..in` enumeration, and — in the vulnerable path — performs a
visibility check up the prototype chain to decide whether the key should
remain visible. The visibility check used `GetPrototype` +
`PrimitiveValueToId<CanGC>` + `GetPropertyDescriptor`, any of which can invoke
a `Proxy` trap and run arbitrary JS. The attacker's trap re-enters the VM,
scrambles iterator state, and causes the `NativeIterator` being walked to be
finalized — leaving the helper with a raw `IteratorProperty* cursor` into
freed co-allocated tail storage. When the helper returns from the trap, the
unconditional `cursor->markDeleted();` write (Iteration.cpp:1852) lands on
freed memory.

## Root cause (pre-fix)

```cpp
// js/src/vm/Iteration.cpp — SuppressDeletedProperty, vulnerable path
IteratorProperty* cursor = ni->nextProperty();           // raw, unrooted
for (; cursor < ni->propertiesEnd(); ++cursor) {
  ...
  // Re-entry sites:
  RootedObject proto(cx);
  if (!GetPrototype(cx, obj, &proto)) return false;          // getPrototypeOf trap
  if (proto) {
    ...
    if (!GetPropertyDescriptor(cx, proto, id, &desc, &holder)) return false;
                                                             // getOwnPropertyDescriptor trap
    if (desc.isSome() && desc->enumerable()) return true;
  }
  cursor->markDeleted();                                     // <-- UAF write
  ni->markHasUnvisitedPropertyDeletion();
  return true;
}
```

## Fix

The fix (`2292742e2bba`) replaces the re-entrant visibility check with a pure,
non-re-entrant path that bails out unless `obj` has a static prototype:

```cpp
if (obj->hasStaticPrototype()) {
  JSObject* proto = obj->staticPrototype();
  if (proto) {
    JSAtom* atom = AtomizeString(cx, str);
    if (!atom) return false;
    PropertyResult prop;
    NativeObject* holder = nullptr;
    if (LookupPropertyPure(cx, proto, AtomToId(atom), &holder, &prop) &&
        prop.isFound()) {
      if (GetPropertyAttributes(holder, prop).enumerable()) return true;
    }
  }
}
```

`LookupPropertyPure` and `GetPropertyAttributes` are guaranteed not to run JS
or GC, so proxy traps can no longer invalidate the iterator list while the
cursor is live.

## Trigger (synthesized from the fix diff)

Pure JS from `js --fuzzing-safe --ion-offthread-compile=off` reliably reaches
the UAF by combining:

1. A **suspended generator** whose `for..in` over the victim object is the
   matching `NativeIterator` the helper will walk (`ni->objectBeingIterated()
   == target`). The generator's `GeneratorObject` is the only strong root to
   this `PropertyIteratorObject`.
2. A **proxy on the victim's prototype chain** whose
   `getOwnPropertyDescriptor` trap fires from inside `SuppressDeletedProperty`'s
   `GetPropertyDescriptor(cx, proto, id, ...)` call — exactly the re-entry
   site the fix removes.
3. **Iterator-cache flooding** inside the trap — allocating many distinct-
   shape iterators chews through `ObjectRealm::iteratorCache`, evicting the
   generator's iterator from the cache. This drops the cache's strong hold
   so the generator + iterator become collectible.
4. `g = null; gc(); gc(); gc(); finishgc();` inside the trap — majors tear
   through the sweep phase, finalize the generator's
   `PropertyIteratorObject`, and free the `NativeIterator`'s malloc'd tail
   storage. When the trap returns, `cursor->markDeleted()` writes to the
   freed region.
5. Trap returns `undefined` so the `desc.isSome() && desc->enumerable()` fast
   return is skipped, forcing execution to the `cursor->markDeleted()` line.

The observed ASAN report (see `output.txt`) confirms the write-site exactly
as `js::IteratorProperty::markDeleted() Iteration.h:217:29`, called from
`SuppressDeletedProperty Iteration.cpp:1852:13`, called from
`SuppressDeletedPropertyHelper Iteration.cpp:1877:10`, on memory freed by
`JSObject` finalize during the mid-trap `gc()` call.

## Verification

```sh
docker build -t smlijun/spidermonkey.x86_64:2012018 spidermonkey/2012018
bash spidermonkey/crash_check.sh 2012018
```

Expected: `CONFIMRED: ASAN_CRASH`.
