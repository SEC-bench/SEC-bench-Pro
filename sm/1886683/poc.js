const v2 = new Int32Array(255);
new Uint32Array(v2);
new Int8Array(2682);
function f8(a9) {
    enableShellAllocationMetadataBuilder(255);
    class C12 {
        m(a14, a15) {
            function f16(a17) {
                return 254;
            }
            function f19(a20) {
                return a15;
            }
            const v23 = wasmTextToBinary(`\n(module\n  (import "" "allocate" (func $allocate (param i32) (result externref)))\n  (import "" "visit" (func $visit (param externref) (result i32)))\n\n  ;; A function with many params and locals, most of which are ref-typed.\n  ;; The purpose of having so many is to defeat any reasonable attempt at\n  ;; allocating them all in registers.  The asymmetrically-placed i32s are\n  ;; an attempt to expose any misalignment or inversion of the stack layout\n  ;; vs what the stackmap claims the layout to be.\n\n  (func $manyParamsAndLocals (export "manyParamsAndLocals")\n    (param $p1 externref) (param $p2 i32)    (param $p3 externref)\n    (param $p4 externref) (param $p5 externref) (param $p6 externref)\n    (param $p7 externref) (param $p8 externref) (param $p9 i32)\n    (result i32)\n    (local $l1 externref) (local $l2 externref) (local $l3 externref)\n    (local $l4 i32)    (local $l5 externref) (local $l6 i32)\n    (local $l7 externref) (local $l8 externref) (local $l9 externref)\n\n    (local $i i32)\n    (local $runningTotal i32)\n\n    ;; Bind some objects to l1 .. l9.  The JS harness will already\n    ;; have done the same for p1 .. p9.\n    (local.set $l1 (call $allocate (i32.const 1)))\n    (local.set $l2 (call $allocate (i32.const 3)))\n    (local.set $l3 (call $allocate (i32.const 5)))\n    (local.set $l4 (i32.const 7))\n    (local.set $l5 (call $allocate (i32.const 9)))\n    (local.set $l6 (i32.const 11))\n    (local.set $l7 (call $allocate (i32.const 13)))\n    (local.set $l8 (call $allocate (i32.const 15)))\n    (local.set $l9 (call $allocate (i32.const 17)))\n\n    ;; Now loop, allocating as we go, and forcing GC every 256 iterations.\n    ;; Also in each iteration, visit all the locals and params, in the hope\n    ;; of exposing any cases where they are not held live across GC.\n    (loop $CONT\n      ;; Allocate, and hold on to the resulting value, so that Ion can't\n      ;; delete the allocation.\n      (local.set $l9 (call $allocate (i32.and (local.get $i) (i32.const 255))))\n\n      ;; Visit all params and locals\n\n      local.get $runningTotal\n\n      (call $visit (local.get $p1))\n      i32.add\n      local.get $p2\n      i32.add\n      (call $visit (local.get $p3))\n      i32.add\n      (call $visit (local.get $p4))\n      i32.add\n      (call $visit (local.get $p5))\n      i32.add\n      (call $visit (local.get $p6))\n      i32.add\n      (call $visit (local.get $p7))\n      i32.add\n      (call $visit (local.get $p8))\n      i32.add\n      local.get $p9\n      i32.add\n\n      (call $visit (local.get $l1))\n      i32.add\n      (call $visit (local.get $l2))\n      i32.add\n      (call $visit (local.get $l3))\n      i32.add\n      local.get $l4\n      i32.add\n      (call $visit (local.get $l5))\n      i32.add\n      local.get $l6\n      i32.add\n      (call $visit (local.get $l7))\n      i32.add\n      (call $visit (local.get $l8))\n      i32.add\n      (call $visit (local.get $l9))\n      i32.add\n\n      local.set $runningTotal\n\n      (local.set $i (i32.add (local.get $i) (i32.const 1)))\n      (br_if $CONT (i32.lt_s (local.get $i) (i32.const 10000)))\n    ) ;; loop\n\n    local.get $runningTotal\n  ) ;; func\n)\n`);
            const t15 = WebAssembly.Module;
            const v26 = new t15(v23);
            const v28 = WebAssembly.Instance;
            const o29 = {
                "allocate": f16,
                "visit": f19,
            };
            const o30 = {
                "": o29,
            };
            const v31 = new v28(v26, o30);
            v31.exports.manyParamsAndLocals();
        }
    }
    C12[Symbol.toPrimitive] = f8;
    const v36 = new C12();
    return v36.m(C12, C12);
}
f8(1);
