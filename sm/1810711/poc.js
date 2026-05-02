// CVE-2023-25735 / Bugzilla 1810711 — FindErrorInstanceOrPrototype
// cross-compartment stale pointer.
//
// In-tree regression test: js/src/jit-test/tests/errors/bug1810711.js
// (commit 5635e34af97fe, 2023-03-29). Shipped verbatim.
//
// Mechanism (fix 5461a647546a7, Iain Ireland, 2023-01-24):
//   js::FindErrorInstanceOrPrototype walked the prototype chain of `obj`
//   to find a prototype tagged as an Error. The original code did
//   CheckedUnwrapStatic(obj) once to get the starting target, then called
//   GetPrototype on `target` — but GetPrototype can invoke a Proxy's
//   getPrototypeOf trap, returning a handler-controlled object whose
//   provenance is not re-validated. The returned prototype could belong to
//   a different compartment from `target`, and the code stored it back into
//   `target` without re-running CheckedUnwrapStatic on the cross-compartment
//   result. The subsequent IsErrorProtoKey(StandardProtoKeyOrNull(target))
//   dereferenced a JSObject whose owning compartment had since been nuked
//   (or was otherwise stale), producing a use-after-free on Error.prototype
//   lookups when `err.stack` is requested.
//
// The fix refactors the loop to call CheckedUnwrapStatic *inside* the loop
// on every candidate and to advance via GetPrototype on the un-unwrapped
// `curr` reference, so the unwrap invariant is re-asserted each iteration.

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
