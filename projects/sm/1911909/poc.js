const m = new WebAssembly.Module(wasmTextToBinary(`(module
  (type $a1 (sub (array anyref)))
  (type $a2 (sub $a1 (array (mut i64))))
  (func $fakeobj (export "fakeobj") (param $v i64) (result anyref)
    (array.new $a2 (local.get $v) (i32.const 1))
    (array.get $a1 (i32.const 0))
  )
)`));
const { fakeobj } = new WebAssembly.Instance(m).exports;

print(fakeobj(0n)); // oh dear.
print(fakeobj(0x424242424242n)); // ...oh dear.
