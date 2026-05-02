// CVE-2025-0241 / Bugzilla 1933023 — Intl.Segmenter Latin1/two-byte
// type mismatch after string atomization. SegmentsObject cached the
// parent JS string's encoding (Latin1 bit) at construction. When the
// underlying two-byte string was later atomized to a Latin1 atom-ref
// (Bug 1881995 mechanism), reading the segment's chars used the cached
// two-byte path against an actual Latin1 buffer — type confusion.
//
// Fix: commit 6a1bdb80cb57384cd915ae2e27d3363a13ecb6f9 (Jan de Mooij,
//      2024-11-27, r=anba). Adds hasLatin1StringChars() that checks
//      the segment's actual char buffer rather than the parent JSString.
// Files: js/src/builtin/intl/Segmenter.{cpp,h}
// Reporter: Nils Bars. MFSA 2025-01 (Firefox 134).

var str = "12345678901234567890";
var strTwoByte = newString(str, {twoByte: true});
var segments = new Intl.Segmenter().segment(strTwoByte);
segments.containing();
var obj = {[strTwoByte]: 1};
segments.containing();
