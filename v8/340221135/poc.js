import * as m from 'module.txt'

m.foo;

function bar() {
  try {
    m.foo = 2;
  } catch (e) {}
}

while (true) {
  bar();
}
