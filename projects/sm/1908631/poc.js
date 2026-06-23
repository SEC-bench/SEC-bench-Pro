// Bug 1908631 — Wasm baseline compiler missing dead-code check in table.fill.
// Pre-fix, BaseCompiler::emitTableFill consumed operands from the value
// stack even when deadCode_ was true — i.e., when table.fill appeared
// after an `unreachable`. With an empty stack this violates the
// numval <= stk_.length() invariant inside the baseline compiler and
// trips MOZ_CRASH. sec-high (csectype-bounds).
// Fix: 5a54e992206bf047493b1081886b364fe21837d7 (Ben Visness, 2024-07-22).
//
// Reduced from official jit-test (commit c3216db173b3,
// js/src/jit-test/tests/wasm/bug1908631.js).

const bytes = wasmTextToBinary(`(module
  (table 0 externref)
  (func
    block
      unreachable
      table.fill 0
  )
)`);

try {
    new WebAssembly.Module(bytes);
} catch (e) {}
