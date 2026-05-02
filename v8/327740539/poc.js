const v0 = -Infinity;
class C3 {
    static valueOf(a5, a6) {
        try {
            super.p(a6, this, a5, this, "T");
            const o8 = {
            };
            const o9 = {
            };
            Object.defineProperty(o9, "foo", a6);
        } catch(e13) {
        }
        return a5;
    }
    2 = v0;
    3 = "T";
    10;
    static #g = "source";
    static 7;
}
const v14 = new C3();
const v15 = new C3();
new C3();
function f18() {
    return v15;
}
class C19 extends C3 {
    #m(a21, a22) {
        Object.defineProperty("T", 1, { set: f18 });
        "T" <= a21;
        let {"f":v24,"h":v25,...v26} = a21;
        return a21;
    }
    static 9;
    [null] = "T";
    [C3] = v14;
}
const v30 = new C19();
v30[10] = v30;
const v31 = new C19();
v31[3];
const v33 = new C19();
v33[10];
function f35() {
    function f37() {
        return 0 / 0;
    }
    f37();
    const v41 = %OptimizeFunctionOnNextCall(f37);
    const o43 = {
    };
    return [,o43];
}
const v45 = %PrepareFunctionForOptimization(f35);
const o47 = {
};
o47.e = o47;
[,o47];
f35();
const o51 = {
};
o51.d = o51;
[,o51];
function f53(a54) {
    eval();
    return arguments[0];
}
function f59() {
    return f53(1);
}
f35();
const v63 = %OptimizeFunctionOnNextCall(f35);
const o65 = {
};
const v66 = [,o65];
try { v66.pop(); } catch (e) {}
f35();
