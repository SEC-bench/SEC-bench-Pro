// CVE-2026-2802: GC gray bits invalid during concurrent sweeping
// Bug 2011069 - Official test from fix commit 4faa7e9916a8f
// Fix: 34384ff7e250e "Wait for sweeping before marking gray bits invalid"
function f() {}
[x] = (() => {
  y = (function () {})();
  z = class e {
    #m() {}
  };
  return [f];
})();
this.gczeal(10, 10);
for (let i = 0; i < 500000; i++) {
  (function () {
    this.setGrayBitsInvalid();
  })();
}
