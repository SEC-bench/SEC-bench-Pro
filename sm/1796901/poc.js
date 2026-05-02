// CVE-2022-45409 / Bugzilla 1796901 — Realm incremental-marking state
// cleared at end-of-GC instead of start-of-GC, leaving a poisoned realm
// reachable into the next GC cycle. Triggers MOZ_CRASH zoneIsDead.
// Fix: 041774db08880cca1ab10e807d0d71718964dffe (Jon Coppeard).
gcslice(0);
evalcx("lazy");
abortgc();
