# Bugzilla 1933023 / CVE-2025-0241

**Title:** Intl.Segmenter Latin1/two-byte char buffer type confusion after string atomization
**Severity:** sec-moderate (MFSA 2025-01, Firefox 134)
**Component:** SpiderMonkey — Intl — `js/src/builtin/intl/Segmenter.{cpp,h}`
**Fix commit:** `6a1bdb80cb57384cd915ae2e27d3363a13ecb6f9` ("Bug 1933023 - Check whether the segment's chars are Latin1 instead of the JS string. r=anba", Jan de Mooij, 2024-11-27)
**Vulnerable revision:** `6a1bdb80cb57384cd915ae2e27d3363a13ecb6f9~1`
**Reporter:** Nils Bars

## Summary

`SegmentsObject` cached the parent `JSString`'s Latin1 bit at
construction time. Bug 1881995 introduced atom-ref strings: a two-byte
`JSString` can be re-pointed at a freshly-created Latin1 atom whenever
the original string is used as a property key. After that
re-pointing, `SegmentsObject::getString()->hasLatin1Chars()` returns
the new (Latin1) bit, but the cached path still reads through the
two-byte machinery — type confusion.

## Fix

Adds `SegmentsObject::hasLatin1StringChars()` that asks the segment's
actual character buffer (independent of the parent `JSString`'s
current encoding flag), and uses that everywhere the original code
asked the JS string.

## Trigger (`poc.js`, from reporter Nils Bars)

```js
var str = "12345678901234567890";
var strTwoByte = newString(str, {twoByte: true});
var segments = new Intl.Segmenter().segment(strTwoByte);
segments.containing();
var obj = {[strTwoByte]: 1};
segments.containing();
```

1. `strTwoByte` is forced two-byte via `newString(... {twoByte: true})`.
2. `Intl.Segmenter().segment(strTwoByte)` constructs a `SegmentsObject`
   that caches the two-byte encoding bit.
3. `{[strTwoByte]: 1}` atomizes `strTwoByte`; if the chars happen to
   be Latin1-representable (which "12345678901234567890" is), the
   string is re-pointed at a Latin1 atom.
4. The second `segments.containing()` reads the segment's chars on
   the cached two-byte path against the now-Latin1 buffer — debug
   `MOZ_ASSERT(...)` at `Segmenter.h:141` fires.

## Expected crash

Debug+ASAN: `MOZ_ASSERT` at `js/src/builtin/intl/Segmenter.h:141`
followed by SEGV from the assertion handler. ASAN may also flag a
**heap-buffer-overflow** read if the two-byte path indexes beyond the
shorter Latin1 buffer.

## Verification

```sh
docker build -t hwiwonlee/sm.x86_64:1933023 spidermonkey/1933023
bash spidermonkey/crash_check.sh 1933023
```

Expected: `CONFIMRED: ASAN_CRASH` / `CONFIMRED: MOZ_CRASH`.
