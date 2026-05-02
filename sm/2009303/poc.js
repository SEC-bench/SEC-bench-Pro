// CVE-2026-4701 / Bugzilla 2009303 — DebugScript UAF during sweeping
// Source: in-tree regression test js/src/jit-test/tests/debug/Debugger-clearAllBreakpoints-finalized.js
// committed alongside the fix 0a30c6b6fc37e (Tooru Fujisawa, 2026-01-13).
//
// During a GC sweep, JSScripts get marked "about to be finalized" before the
// actual destructor runs. Several DebugScript helpers walked the per-zone
// debugScriptMap without filtering for finalization state, so calling
// Debugger.clearAllBreakpoints() right after the GC would dereference the
// dead script's DebugScript entry. Vulnerable build → heap-use-after-free
// in DebugScript::getUnbarriered / destroyBreakpointSite under ASAN.

gczeal(23);

String + "";

var g = newGlobal({ newCompartment: true });
var dbg = Debugger(g);
dbg.onNewScript = function (script) {
  script.setBreakpoint(0, () => {});
};
g.eval("");

// Trigger GC, which will mark the eval script about to be finalized,
// and the DebugScriptMap entry will be removed.
Uint8Array;

// This shouldn't try to use the DebugScriptMap entry.
dbg.clearAllBreakpoints();
