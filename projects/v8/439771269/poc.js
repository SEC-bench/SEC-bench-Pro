// Flags: --expose-gc
const buffer = new ArrayBuffer(100);
const options = new Proxy({}, {
    get(target, property, receiver) {
        if (property === 'builtins') {
            buffer.transfer();
            gc();
        }
    }
});
WebAssembly.validate(buffer, options);