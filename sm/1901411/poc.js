async function* f0(a1) {
    return f0;
}
const v2 = f0();
const o3 = {
};
const v4 = [o3];
function F5(a7) {
    if (!new.target) { throw 'must be called with new'; }
    const v8 = o3.__proto__;
    function f9() {
        for (let i16 = 200; i16--;) {
            v2["return"]();
        }
        return a7;
    }
    function f22(a23) {
        return a23;
    }
    Object.defineProperty(v8, "then", { configurable: true, get: f9, set: f22 });
}
new F5(Promise);
Promise.any(v4);

