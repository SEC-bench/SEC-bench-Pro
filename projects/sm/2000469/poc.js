var a = ["g"];
function f() {
  const x = {
    set g(z) {
      (function(v) {
        if (b !== undefined) v[a.shift()] = 0;
      })(this);
      this.m = 0;
      this.n = 0;
      for (var y in this);
    },
  };
  x.g = x;
}
new Int8Array(32).reduceRight(f);
var b = 1;
new Int8Array(32).reduceRight(f);