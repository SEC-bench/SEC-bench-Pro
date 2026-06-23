function testMathyFunction(f, inputs) {
    for (var j = 0; j < inputs.length; ++j) {
        for (var k = 0; k < inputs.length; ++k) {
            f(inputs[j], inputs[k])
        }
    }
}
mathy0 = function(x, y) {
    Math.pow((Math.sign((+y)) >>> 0))
};
mathy2 = function(x, y) {
    mathy0(2 ** 53, (x | 0) ? (+x) : x) ? (y >>> 0) : (x >>> 0);
};
testMathyFunction(mathy2, [Math.PI, 0 / 0, 1.7976931348623157e308]);
mathy4 = function(x, y) {
    y | 0, (2 ** 53) ? Math.fround(mathy2(x, x)) : 1.7976931348623157e308 | 0;
};
testMathyFunction(mathy4, [, '', '0', /0/, '/0/', ({}), createIsHTMLDDA()]);