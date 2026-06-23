// CVE-2022-42928 / Bugzilla 1791520 — Missing GC keep-alive on TypedArray
// across BigInt allocation in JIT'd BigInt64Array element ops.
// MLoadUnboxedScalar / MAtomicTypedArrayElementBinop for Scalar::BigInt64
// returned via CreateBigIntFromInt64 which can nursery-allocate.
// The TypedArrayObject reference held in a register was not rooted, so a
// minor GC during the BigInt allocation moved/freed the backing array.
//
// Fix: commit d9db6d6fe7d255661578fc862408e4f452a65533 ("Add some keep
//      alive annotations. r=jandem", 2022-10-06). Adds MKeepAliveObject.
// Tests + GC-unsafe instrumentation: caa6ecc16202f59699f8f7244ecbdc3e2b226113
//                                  + b7c6834859a43d6a0be04677082d63ff6c855ef0
// File: js/src/jit/IonAnalysis.cpp
// MFSA 2022-46 (Firefox 107). Reporters: Samuel Groß, Carl Smith.

function testAtomicsAdd() {
  var x;
  for (var i = 0; i < 100; ++i) {
    var a = new BigInt64Array(2);
    x = Atomics.add(a, i & 1, 1n);
  }
  return x;
}
function testAtomicsSub()             { var x; for (var i=0;i<100;++i){var a=new BigInt64Array(2); x=Atomics.sub(a,i&1,1n);} return x; }
function testAtomicsAnd()             { var x; for (var i=0;i<100;++i){var a=new BigInt64Array(2); x=Atomics.and(a,i&1,1n);} return x; }
function testAtomicsOr()              { var x; for (var i=0;i<100;++i){var a=new BigInt64Array(2); x=Atomics.or (a,i&1,1n);} return x; }
function testAtomicsXor()             { var x; for (var i=0;i<100;++i){var a=new BigInt64Array(2); x=Atomics.xor(a,i&1,1n);} return x; }
function testAtomicsExchange()        { var x; for (var i=0;i<100;++i){var a=new BigInt64Array(2); x=Atomics.exchange(a,i&1,0n);} return x; }
function testAtomicsCompareExchange() { var x; for (var i=0;i<100;++i){var a=new BigInt64Array(2); x=Atomics.compareExchange(a,i&1,0n,0n);} return x; }
function testAtomicsLoad()            { var x; for (var i=0;i<100;++i){var a=new BigInt64Array(2); x=Atomics.load(a,i&1);} return x; }
function testLoadElement()            { var x; for (var i=0;i<100;++i){var a=new BigInt64Array(2); x=a[i&1];} return x; }

gczeal(14);
testAtomicsAdd(); testAtomicsSub(); testAtomicsAnd(); testAtomicsOr();
testAtomicsXor(); testAtomicsExchange(); testAtomicsCompareExchange();
testAtomicsLoad(); testLoadElement();
