// CVE-2026-2785 / Bugzilla 2013549
// Invalid pointer / memory-safety issue in JS Engine module linking:
// Synthetic module environments (JSON/CSS/bytes modules) were created without
// the internal `*namespace*` property that cyclic-module environments have.
// Re-exporting a namespace binding out of a synthetic module
// (`import * as ns from 'jsonmod' with { type: 'json' }; export { ns };`)
// resolves to a slot that does not exist in the synthetic env's shape.
//
// Fix: commit 3b5800515463f1a9c676a744f8bd4e1256247020 — prepends a
// `*namespace*` property in CreateEnvironmentShapeForSyntheticModule and
// shifts firstSyntheticValueSlot() from RESERVED_SLOTS to RESERVED_SLOTS+1.

// Create a JSON synthetic module.
var jsonMod = parseModule('{"key": "value"}', 'jsonmod', 'json');
registerModule('jsonmod', jsonMod);

// Re-export the JSON module's namespace. This requires the synthetic module
// env to hold a namespace binding in its *namespace* slot — which doesn't
// exist on vulnerable builds.
var reexporter = parseModule(`
  import * as ns from 'jsonmod' with { type: 'json' };
  export { ns };
`);
registerModule('reexporter', reexporter);

// Consumer that reads the re-exported namespace binding, forcing resolution
// through the synthetic module env's *namespace* slot.
var consumer = parseModule(`
  import { ns } from 'reexporter';
  assertEq(ns.default.key, "value");
`);

moduleLink(consumer);
moduleEvaluate(consumer);
