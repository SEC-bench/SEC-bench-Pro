// CVE-2026-2783: JIT int64/int32 stack slot type confusion
// Bug 2010943 - Official test from fix commit e00390fd4e3b0
// Fix: 0ba3af42be7fc "Support reading int64 from int32 stack slot"
for (var i = 0; i < 1000; i++) {
  function a() { a; }
  for (let b = 0; b < 5; b++) {
    new SharedArrayBuffer();
    a(BigInt.asUintN(64, BigInt(b)));
  }
}
