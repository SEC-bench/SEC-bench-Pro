function a() {}
function b(c) {
  c.d = 2;
}
function e() {
  f = new a;
  verifyprebarriers();
  b(f);
}
for (let i = 0; i < 50; i++)
  new e;
