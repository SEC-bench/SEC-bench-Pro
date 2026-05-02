function main() {
    function func() {
      return '' + '<div><div><di';
    }
    %PrepareFunctionForOptimization(func);
    try {
      func();
    } catch (e) {}
    /./.test(func());
}
%PrepareFunctionForOptimization(main);
main();
%OptimizeFunctionOnNextCall(main);
main();
//flags: --allow-natives-syntax --optimize-on-next-call-optimizes-to-maglev --maglev-cse