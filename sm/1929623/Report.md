# JSON Module Cross-Compartment UAF

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1929623
CVE: CVE-2025-0240
Component: JavaScript Engine
Bounty: (sec-bounty+)
Keywords: sec-high

## Summary

A use-after-free vulnerability exists in SpiderMonkey's synthetic (JSON) module evaluation. In `SyntheticModuleEvaluate` (js/src/vm/Modules.cpp), the `result` MutableHandle<Value> was passed to `AsyncFunctionReturned` which could contain a cross-compartment object reference. When the result value from a different compartment is used after the compartment is destroyed, a UAF occurs.

## Steps to Reproduce

On the vulnerable revision, run with `--fuzzing-safe`:

```javascript
const a = "".startsWith("");
function b() { return newGlobal(b); }
b.newCompartment = a;
with (b()) this.moduleEvaluate(parseModule("45172", "", "json"));
```

Simplified reproduction:
```javascript
var m = parseModule("{}", "", "json");
newGlobal({newCompartment: true}).moduleEvaluate(m);
```

## Crash Type

MOZ_CRASH with compartment mismatch:
`MOZ_CRASH(*** Compartment mismatch ... at argument 1) at js/src/vm/JSContext-inl.h:56`

## Fix

Fix commit: `62ea7950e926` (git: `62ea7950e9268e5b58d1dc6e4de6016ab719e11f`)

The fix passes `UndefinedHandleValue` instead of the `result` value to `AsyncFunctionReturned`, since the only synthetic modules supported are JSON modules and the result should always be `undefined`.

## Affected Versions

Firefox 132-135, ESR 128.
