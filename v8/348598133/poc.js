d8.test.enableJSPI();
d8.test.installConditionalFeatures();
function main() {
  (function f8() {
    let v38 = new WebAssembly.Function({
      parameters: [],
      results: ['i32']
    }, () => Promise.resolve(42), {
      suspending: 'first'
    });
  })();
}
main();
