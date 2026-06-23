// CVE-2024-3852 / Bugzilla 1883542 — GetBoundName in the JIT returned
// the wrong object (bare global vs WindowProxy) when a getter on the
// global was warmed up. Regression from Bug 1805199.
//
// Fix: commit 86083f35c4dc832565464cca79f6224821a985e0
//      ("Bug 1883542: Simplify GetBoundName ICs r=jandem", Iain Ireland, 2024-03-21)
// Follow-up: 83c1f27889e88fb90d6eb60846f7c57820519529 (test + assertion)
// File: js/src/jit/CacheIR.cpp
// Reporter: Logan Stratton / Andrew Kramer. MFSA 2024-18 (Firefox 125).

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
