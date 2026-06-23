// Bug 1914009 — Wasm baseline emitReturnCallRef stack-result mismatch.
// Multi-value return_call_ref handed wrong stack slots, corrupting frame.
// Fix: d942bcd55a236074e4fd0601a103e8c252e56899.
//
// Reduced from official jit-test (commit 9ad11169dda1).
function wasmEvalText(str, imports) {
    const m = new WebAssembly.Module(wasmTextToBinary(str));
    return new WebAssembly.Instance(m, imports);
}

const ext1 = {};
function f1(p0,p1,p2,p3,p4,p5,p6) {
    return [
        1,
        1.125
    ];
}

const ins = wasmEvalText(`(module
(import "x" "ext1" (global $ext1 externref))

(type $t1 (func (param  externref i32 i32 f64 f64 f32 i64) (result i32 f32)))

(import "x" "f1" (func $f1 (param  externref i32 i32 f64 f64 f32 i64) (result i32 f32)))

(elem declare func $f1)

(func $f0 (export "f0") (result i32 f32)
    global.get $ext1
    i32.const 1
    i32.const 1
    f64.const 1.2
    f64.const 1.2
    f32.const 1.125
    i64.const 2

    ref.func $f1
    return_call_ref $t1
)
)`, {x: {
    ext1,
    f1,
}});

const res = ins.exports.f0();
