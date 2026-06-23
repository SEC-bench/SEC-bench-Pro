# Bugzilla 2013165 / CVE-2026-2796

**Title:** Fix import optimization
**Severity:** **sec-critical** (MFSA 2026-13 — JavaScript: WebAssembly component)
**Component:** SpiderMonkey — WebAssembly — Instance import fast-path
**File touched:** `js/src/wasm/WasmInstance.cpp` (`MaybeOptimizeFunctionCallBind`)
**Fix commit:** `e2acef6711967949cd0825869034165383c482e1` (Ryan Hunt, 2026-02-05, r=yury)
**Vulnerable revision:** `e2acef6711967949cd0825869034165383c482e1~1`
**Phabricator:** D281104
**Bugzilla:** https://bugzilla.mozilla.org/show_bug.cgi?id=2013165 (sec-restricted)
**MFSA:** https://www.mozilla.org/en-US/security/advisories/mfsa2026-13/

## Background: the `Function.prototype.call.bind(fn)` fast-path

SpiderMonkey's wasm engine pattern-matches one common JS import shape at instantiation time: a `BoundFunctionObject` whose target is the built-in `Function.prototype.call` native and whose bound `this` is a callable object. That pattern is a "curried `this`" adapter — calling `bound(thisValue, ...args)` is semantically equivalent to `targetFn.call(thisValue, ...args)`. Detecting it once up-front lets `Instance::callImport` skip creating the BoundFunctionObject call frame on every invocation and instead route the wasm import's first argument directly into the callee's `thisv()` slot.

The matcher is `js::wasm::MaybeOptimizeFunctionCallBind` (`js/src/wasm/WasmInstance.cpp:2316`):

```cpp
JSObject* MaybeOptimizeFunctionCallBind(const wasm::FuncType& funcType,
                                        JSObject* f) {
  if (funcType.args().length() == 0) return nullptr;
  if (!f->is<BoundFunctionObject>()) return nullptr;

  BoundFunctionObject* boundFun = &f->as<BoundFunctionObject>();
  JSObject* boundTarget = boundFun->getTarget();
  Value       boundThis = boundFun->getBoundThis();

  if (boundFun->numBoundArgs() != 0) return nullptr;
  if (!IsNativeFunction(boundTarget, fun_call)) return nullptr;

  if (!boundThis.isObject() || !boundThis.toObject().isCallable() ||
      IsCrossCompartmentWrapper(boundThis.toObjectOrNull())) {
    return nullptr;
  }

  return boundThis.toObjectOrNull();   // <-- returns the unwrapped inner callable
}
```

When this returns non-null, `Instance::callImport` (same file, line 2580) sets the `isFunctionCallBind` flag on `FuncImportInstanceData` and subsequent wasm→import calls forward the *first* wasm argument into the inner callee's `thisv()` and the remaining wasm arguments into the natural JS argument positions.

## Root cause

`isCallable()` and the `CrossCompartmentWrapper` check are the only filters on `boundThis`. They are satisfied by **any** callable JSObject, including **wasm-exported JSFunctions** (each wasm function is wrapped in a JSFunction with `isWasm() == true`).

When the importer is itself a wasm module, the optimizer happily accepts the unwrapped wasm function as the target of the fast-path. At call time, `Instance::callImport` — confident that it is dispatching a normal JS callable — takes the wasm arguments it just unpacked from the caller's stack and forwards them through the JS marshalling path (writing them into `InvokeArgs`'s Value slots). The inner wasm function then receives those Values reinterpreted under **its own** declared wasm signature.

The caller's first wasm argument is routed into the callee's `thisv()`. On the way, no type conversion is performed — the raw i32/f64/externref/anyref Value is handed to the target wasm function expecting whatever type **its** signature declared for its first parameter.

A concrete exploit primitive:

- Caller (module A) declares the import as `(func (param i32) (result i32))` and calls it with a chosen i32 constant.
- Callee (module B) is a wasm function whose first parameter is `externref` and whose body does anything observable with that ref — `struct.get`, `call_ref`, or handing it to a JS import that reads `.x`.
- The fast-path routes the caller's i32 constant directly into the callee's `externref` slot. The i32 is now interpreted as a GC-object pointer. The callee's `struct.get` dereferences it at a controlled offset, or the JS import's `.x` read crashes/confuses objects.

On an ASAN+debug shell the confusion is caught as an `AddressSanitizer: SEGV` on the fabricated address, or as a `MOZ_CRASH` from a later shape/type assertion.

## Fix

Five lines added to `MaybeOptimizeFunctionCallBind`, right after the existing callable check:

```diff
   if (!boundThis.isObject() || !boundThis.toObject().isCallable() ||
       IsCrossCompartmentWrapper(boundThis.toObjectOrNull())) {
     return nullptr;
   }

+  if (boundThis.toObject().is<JSFunction>() &&
+      boundThis.toObject().as<JSFunction>().isWasm()) {
+    return nullptr;
+  }

   return boundThis.toObjectOrNull();
 }
```

Explicitly bails out whenever the unwrapped `boundThis` is a wasm JSFunction. `Instance::callImport` then takes the ordinary wasm-to-wasm (or wasm-to-BoundFunction) import path, which marshals the caller's arguments through the formal wasm signature of the callee — no reinterpretation.

## Trigger (`poc.js`)

The committed regression test ships the pattern used by `crash_check.sh`:

1. Build module B with an `externref` parameter that is immediately consumed (`(call $use (local.get 0))`, where `$use` is an `env.use` JS import reading `.x`).
2. `callBound = Function.prototype.call.bind(instB.exports.f)` — creates the BoundFunctionObject the optimizer pattern-matches.
3. Build module A importing the wrapped callable as `(func (param i32) (result i32))` and calling it via `call_ref` with a plain integer.
4. Invoke `instA.exports.go(4)`.

On the vulnerable revision the i32 `4` is routed into module B's externref parameter, the JS `use` import receives it as a Value, `.x` dereferences the confused pointer, and ASAN reports the crash.

## Verification

```sh
bash spidermonkey/crash_check.sh 2013165
```

Expected: `CONFIMRED: ASAN_CRASH` (SEGV on dereference of a confused externref, or MOZ_CRASH from an internal type/shape check).
