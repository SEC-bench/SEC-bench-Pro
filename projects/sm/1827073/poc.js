function f1(a2, a3, a4, a5) {
    function f6(a7, a8) {
        a8(f1, a4);
        const o10 = {
        };
        o10[1] = f1;
        const v11 = o10[1];
        v11.arguments;
        return v11;
    }
    try {
        f6("undefined", f1);
    } catch(e14) {
    }
    return a2;
}
f1();
