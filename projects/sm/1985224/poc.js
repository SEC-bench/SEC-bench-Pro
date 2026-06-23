Object.defineProperty(this, "x", {
  value: {
    c: function*() {}.constructor
  }
})
x.c()().next();
setJitCompilerOption("offthread-compilation.enable", 1);
while (true) {
  x.c()().next();
}
