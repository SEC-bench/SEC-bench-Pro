// CVE-2026-0884 / Bugzilla 2003588 — Debugger + CCW UAF after nukeAllCCWs.
//
// Pre-fix, Compartment::wrap paths did not allow (re)creation of CCWs to
// debugger instances after `nukeAllCCWs()`, leading to assertion / UAF
// inside the Debugger machinery when a debug event tried to wrap a
// debugger object whose CCW had been nuked.
//
// Fix: commit 0264cf850afd91cdd3956066e0b00b982566f684 (2025-12-08,
//      "Continue to allow creation of CCWs to debugger instances after
//      CCWs have been nuked r=jandem"). MFSA 2026-01.
//
// File: js/src/proxy/CrossCompartmentWrapper.cpp
// Public jit-test verbatim.

var x = newGlobal({ newCompartment: true });
var y = Debugger(x);
y.x = y;
y.onDebuggerStatement = function(w) {
  nukeAllCCWs();
  w.environment.getVariable("x");
}
x.eval('function f(z) { with(z) { debugger } }');
x.f(y);
