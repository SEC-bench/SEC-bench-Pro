const kNumRegs = 65534;
let body = [];
for (let i = 0; i < kNumRegs; ++i) {
    body.push(`  let r${i} = ${i};`);
}
let f = eval(`(function*() {\n${body.join('\n')}})`);

% PrepareFunctionForOptimization(f);
f();
% OptimizeMaglevOnNextCall(f);
f();
