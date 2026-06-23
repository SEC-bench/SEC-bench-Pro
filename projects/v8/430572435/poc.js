function noop() {}
var trigger_obj = { initial_prop: 1 };

const NUM_UNROLLED_CALLS = 70000;

let func_body = '';
for (let i = 0; i < NUM_UNROLLED_CALLS; ++i) {
  func_body += 'noop();\n';
}
func_body += 'return trigger_obj.initial_prop;';

var largeFuncUnrolled;
try {
  largeFuncUnrolled = new Function('noop', 'trigger_obj', func_body);
} catch(e) {
  quit(0);
}

for (let i = 0; i < 2000; ++i) {
  largeFuncUnrolled(noop, trigger_obj);
}

try {
  largeFuncUnrolled(noop, trigger_obj);
  delete trigger_obj.initial_prop;
} catch (e) {}

Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 10000);
quit(0);
