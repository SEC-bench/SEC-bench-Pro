function a(b) {
    binary = wasmTextToBinary(b)
    c = new WebAssembly.Module(binary)
    return new WebAssembly.Instance(c)
}
gczeal(9,10)
t = a(`(module (type (struct ))
    (table (export "")  (ref null 0)
      (elem ( ref.null 0 ))
    )
  )
`).exports
f();