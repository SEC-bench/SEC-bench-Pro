import * as m from 'module.txt'

m.foo;

function bar() {
  try {
    m.foo = 2;
  } catch (e) {}
}

for (let i = 0; i < 1000; i++) {
  bar();
}

Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 1000);
