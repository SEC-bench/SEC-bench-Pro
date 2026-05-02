// CVE-2024-0744: Wild pointer dereference from JIT compiled code
// Bug 1871089 - ICStub spilled to stack becomes stale after GC clones it
// Run with: --fuzzing-safe --fast-warmup --gc-zeal=14
// Crash is flaky - may need multiple attempts
function F0() {
    if (!new.target) { throw 'must be called with new'; }
}
const v2 = new F0();
const v5 = [0, 0, 0, 0, 0, 0, 0];
class C6 {
    constructor(a8, a9) {
        a8[a9];
    }
    toString(a12, a13) {
        const t11 = this.constructor;
        new t11(v2);
        const t13 = this.constructor;
        new t13(3622, this);
    }
}
const v18 = new C6("aaaa");
const v19 = new C6(v5);
const t19 = v19.constructor;
new t19("aaaa", v18);
