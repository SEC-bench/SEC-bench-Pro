function init() {
    var target = {};
    for (var i = 0; i < 100; i++) {
        target["a" + i] = i;
    }
    var arr = [];
    for (var i = 0; i < 50 * 1000; i++) {
        var cons = function() {};
        cons.x1 = 1;
        cons.x2 = target;
        cons.x3 = 3;
        cons.x4 = 4;
        cons.x5 = 5;
        cons.x6 = 6;
        cons.x7 = 7;
        arr.push(cons);
    }
    return arr;   
}
function f() {
    var arr = init();
    var interesting = arr[arr.length - 10];
    for (var i = 0; i < arr.length; i++) {
        var cons = arr[i];
        interesting.x1 = 10;
        new cons();
        assertEq(interesting.x2.a10, 10);
    }
}
f();
