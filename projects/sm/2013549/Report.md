# Bugzilla 2013549 / CVE-2026-2785

**Title:** Invalid pointer in JS Engine — synthetic module environments lack the `*namespace*` binding
**Severity:** sec-moderate (MFSA 2026-15)
**Component:** SpiderMonkey — Module loader — synthetic module environments
**Files touched:** `js/src/vm/Scope.cpp`, `js/src/builtin/ModuleObject.cpp`, `js/src/vm/EnvironmentObject.h`, `js/src/vm/Modules.cpp`
**Fix commit:** `c8104bed78889aaebf43316c1ba6acf61bb3a8ba` — "Bug 2013549 - Give synthetic module environments a *namespace* property the same as for cyclic modules r=spidermonkey-reviewers,dminor" (Jon Coppeard, 2026-02-05, Phabricator D281434)
**Vulnerable revision:** `c8104bed78889aaebf43316c1ba6acf61bb3a8ba~1`
**Credit:** Evyatar Ben Asher, Keane Lucas, Nicholas Carlini, Newton Cheng, Daniel Freeman, Alex Gaynor, and Joel Weinberger using Claude from Anthropic.

## Root cause

Cyclic (parsed) modules have a hidden `*namespace*` declaration injected into their module scope by `Parser::moduleBody`. It is used when a module does `import * as ns from 'mod'; export { ns };` — the re-export binding resolves to the `*namespace*` slot on the importing module's environment, which holds the imported module's namespace object.

Synthetic modules (JSON, CSS, bytes modules, …) share the same `ModuleEnvironmentObject` class but their shape is built by `js::CreateEnvironmentShapeForSyntheticModule` in `Scope.cpp`. Pre-fix:

```cpp
// pre-fix — only enumerates the synthetic export names
uint32_t slotIndex = numSlots;
for (JSAtom* exportName : module->syntheticExportNames()) {
  id = NameToId(exportName->asPropertyName());
  if (!SharedPropMap::addPropertyWithKnownSlot(cx, cls, &map, &mapLength, id,
                                               propFlags, slotIndex,
                                               &objectFlags)) {
    return nullptr;
  }
  slotIndex++;
}
```

No `*namespace*` property is added. `ModuleEnvironmentObject::firstSyntheticValueSlot()` returned `RESERVED_SLOTS` pre-fix, and `ModuleObject::createSyntheticEnvironment` asserted `propMapLength() == values.length()`.

When a re-exporter module resolves its exported namespace binding, the module linker walks the binding chain down to the synthetic module's environment and accesses its `*namespace*` slot — which does not exist on the vulnerable shape. The access reads/writes an out-of-bounds fixed slot on the `ModuleEnvironmentObject`.

## Fix

```cpp
// post-fix — prepends *namespace* before the synthetic exports
auto addProperty = [&](PropertyName* name) {
  id = NameToId(name);
  return SharedPropMap::addPropertyWithKnownSlot(
      cx, cls, &map, &mapLength, id, propFlags, slotIndex, &objectFlags);
};
if (!addProperty(cx->names().star_namespace_star_)) {   // <-- added
  return nullptr;
}
slotIndex++;
for (JSAtom* exportName : module->syntheticExportNames()) {
  if (!addProperty(exportName->asPropertyName())) {
    return nullptr;
  }
  slotIndex++;
}
```

`firstSyntheticValueSlot()` is shifted to `RESERVED_SLOTS + 1` so synthetic values still start after the new `*namespace*` slot. `createSyntheticEnvironment` now asserts `propMapLength() == values.length() + 1`. `hasCyclicModuleFields()` adds `MOZ_ASSERT_IF(result, !hasSyntheticModuleFields())` so synthetic modules cannot silently take the cyclic path.

## Trigger

1. Create a JSON synthetic module:
   ```js
   var jsonMod = parseModule('{"key": "value"}', 'jsonmod', 'json');
   registerModule('jsonmod', jsonMod);
   ```
2. Create a re-exporter that namespace-imports and re-exports:
   ```js
   var reexporter = parseModule(`
     import * as ns from 'jsonmod' with { type: 'json' };
     export { ns };
   `);
   registerModule('reexporter', reexporter);
   ```
3. Consumer reads the re-exported namespace, forcing resolution through the synthetic env's non-existent `*namespace*` slot:
   ```js
   var consumer = parseModule(`
     import { ns } from 'reexporter';
     assertEq(ns.default.key, "value");
   `);
   moduleLink(consumer);
   moduleEvaluate(consumer);
   ```

## Expected crash

ASAN **heap-buffer-overflow** / debug `MOZ_ASSERT` failure inside `ModuleEnvironmentObject` slot access during namespace re-export resolution. Label from MFSA 2026-15: "Invalid pointer in JS Engine".

## Verification

```sh
docker build -t smlijun/spidermonkey.x86_64:2013549 spidermonkey/2013549
bash spidermonkey/crash_check.sh 2013549
```

Expected: `CONFIMRED: ASAN_CRASH` or `CONFIMRED: MOZ_CRASH`.
