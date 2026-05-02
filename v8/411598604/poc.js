a = new DataView(new Sandbox.MemoryView(0, 967296))
function b() {
    c = {}.__proto__[Object] = d = []
    e = [Int16Array, d, Int16Array, "", 7, d]
    for (f in e) {
        function g() {
            for (h = 0;
                h < 100;
                h++)
                JSON.parse("4294967297")
        }
        for (i = 0;
            i < 100;
            i++)
            g()
    }
}
b()
a.setUint16(262144, 5141)

