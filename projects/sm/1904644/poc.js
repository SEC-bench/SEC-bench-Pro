function a() {}
b = c =
    `(module(import "m" "foreign" (func $foreign))(func (export "f") try(call $foreign)end))`
d = {
  foreign()
    {
    a(...b )}}
e = {
  "m" : d}
k = wasmTextToBinary(c)
l = WebAssembly.Module
g = new l(k)
h = WebAssembly.Instance
i = new h(g, e)
j = i.exports
j.f()
b = e
j.f()

