gczeal(7, 1)

function a(b) {
    c = newGlobal({
        newCompartment: true
    })
    d = new Debugger
    setInterruptCallback(function() {
        d.addDebuggee(c)
        d.getNewestFrame().onStep = function() {
            return b
        }
        return true
    })
    try {
        c.eval("(" + function() {
            invokeInterruptCallback(function() {})
        } + ")()")
    } finally {}
}
a({
    throw: "thrown 42"
})