// Bug 1987290 — FinalizationRegistryObject::unregister can read arguments
// out of bound when no arguments are supplied (sec-high, csectype-bounds).
//
// Root cause: js/src/builtin/FinalizationRegistryObject.cpp uses `args[0]`
// to read the first argument instead of the bounds-checking `args.get(0)`.
// When the JS caller passes no arguments, CallArgs::operator[] asserts
// `i < argc_` and reads past the call frame's outgoing argument area,
// producing an OOB stack-or-redzone read that ASAN flags.
//
// Regressed by Bug 1863140 Part 3 (D263113). Fix: 2b8155c2c4c2 — Use
// get() instead of operator[] (Tooru Fujisawa, 2025-09-08).
//
// Bugzilla testcase verbatim — 2 lines.
const v = new FinalizationRegistry(() => {});
v.unregister();
