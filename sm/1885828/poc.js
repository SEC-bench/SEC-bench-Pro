// CVE-2024-3855: JIT MSubstr Invalid Memory Read
// Bug 1885828 - Wild pointer deref from jitted code via MSubstr LICM
// Run with: --fast-warmup --fuzzing-safe
function f9(a10) {
    for (let i13 = 1000; i13-- > 0;) {
        (`(f32.neg`).slice(a10).search(undefined);
    }
}
f9(1);
f9(-1);
