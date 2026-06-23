const v1 = new Int8Array();
const o4 = {
    get a() {
        Object.defineProperty(this, "a", { enumerable: true, value: v1 });
    },
};
o4[Symbol.unscopables] = o4;
with (o4) {
    let v6 = undefined;
    v6 = a;
}
