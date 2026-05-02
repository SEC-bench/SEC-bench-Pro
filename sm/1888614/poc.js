function a(b) {
    b.Array.prototype.toSorted.call([2, 3], () => c)
}
a(newGlobal())