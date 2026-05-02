function a(b) {
  binary = wasmTextToBinary(b)
  c = new WebAssembly.Module(binary)
  return new WebAssembly.Instance(c)
}
d = `
  (module (type $e (struct i8 i8 i8 i8))
    (func (export "readU8hi1") (param $f eqref) (result i32) (struct.get_u $e 3 (ref.cast (ref $e) local.get $f)))
  )
`;
a(d).exports.readU8hi1(0);