# Type confusion due to improper WASM module size check in `AsyncStreamingDecoder`

Issue URL: https://issues.chromium.org/issues/368241697
VRP-Reward: 55000
Date: Sep 20, 2024 03:09PM


### VULNERABILITY DETAILS

#### Summary

Type confusion due to WASM streaming decoder size overflow with overly large modules. `AsyncStreamingDecoder` does not properly check maximum module size, resulting in offset truncation into 30 bits for `ConstantExpression::kWireBytesRef` constant expressions. This eventually results in a primitive to confuse `undefined` as any WASM (reference) type, resulting in type confusion (and an instant arbitrary caged RW).

#### Details

WASM modules must hold an invariant that its size is less than `kV8MaxWasmModuleSize = 1024 * 1024 * 1024 (1 GiB)`:

```
// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/wasm-limits.h;drc=f84fb630ee9aa58f7493db195d3ab6e0b254425e;l=49
constexpr size_t kV8MaxWasmModuleSize = 1024 * 1024 * 1024;  // = 1 GiB
```

However, `AsyncStreamingDecoder` only checks this limit on each section sizes and not the whole module:

```
// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/streaming-decoder.cc;l=465
class AsyncStreamingDecoder::DecodeSectionLength : public DecodeVarInt32 {
 public:
  explicit DecodeSectionLength(uint8_t id, uint32_t module_offset)
      : DecodeVarInt32(max_module_size(), "section length"),    // [!] checks each section size, not the whole module
        section_id_(id),
        module_offset_(module_offset) {}

  std::unique_ptr<DecodingState> NextWithValue(
      AsyncStreamingDecoder* streaming) override;

 private:
  const uint8_t section_id_;
  // The start offset of this section in the module.
  const uint32_t module_offset_;
};
```

This allows a module to grow over 1 GiB, which results in offset truncation in `ConstantExpression::kWireBytesRef` constant expressions:

```
// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/constant-expression.h;drc=247e36d85da39a66a1f68b46ef4aebf7dfdfdb03;l=31
// A representation of a constant expression. The most common expression types
// are hard-coded, while the rest are represented as a {WireBytesRef}.
class ConstantExpression {
 public:
  // ...
  static constexpr ConstantExpression WireBytes(uint32_t offset,
                                                uint32_t length) {
    return ConstantExpression(OffsetField::encode(offset) |
                              LengthField::encode(length) |
                              KindField::encode(kWireBytesRef));
  }
  // ...
  V8_EXPORT_PRIVATE WireBytesRef wire_bytes_ref() const;

 private:
  static constexpr int kValueBits = 32;
  static constexpr int kLengthBits = 30;   // [!] length limited to 30 bits (under 1 GiB)
  static constexpr int kOffsetBits = 30;
  static constexpr int kKindBits = 3;

  // There are two possible combinations of fields: offset + length + kind if
  // kind = kWireBytesRef, or value + kind for anything else.
  using ValueField = base::BitField<uint32_t, 0, kValueBits, uint64_t>;
  using OffsetField = base::BitField<uint32_t, 0, kOffsetBits, uint64_t>;
  using LengthField = OffsetField::Next<uint32_t, kLengthBits>;
  using KindField = LengthField::Next<Kind, kKindBits>;

  // ...
  uint64_t bit_field_ = 0;
};

// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/constant-expression.cc;drc=8cab41c0837d9b869abdb0e5ca6a929b302f0d6a;l=23
WireBytesRef ConstantExpression::wire_bytes_ref() const {
  DCHECK_EQ(kind(), kWireBytesRef);
  return WireBytesRef(OffsetField::decode(bit_field_),
                      LengthField::decode(bit_field_));
}
```

With a constant expression located in an offset over 1 GiB, `ConstantExpression::wire_bytes_ref()` uses a truncated offset to fetch the `WireBytesRef`. This function is notably used in `EvaluateConstantExpression()`:

```
// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/constant-expression.cc;drc=8cab41c0837d9b869abdb0e5ca6a929b302f0d6a;l=29
ValueOrError EvaluateConstantExpression(
    Zone* zone, ConstantExpression expr, ValueType expected, Isolate* isolate,
    Handle<WasmTrustedInstanceData> trusted_instance_data,
    Handle<WasmTrustedInstanceData> shared_trusted_instance_data) {
  switch (expr.kind()) {
    // ...
    case ConstantExpression::kWireBytesRef: {
      WireBytesRef ref = expr.wire_bytes_ref();

      base::Vector<const uint8_t> module_bytes =
          trusted_instance_data->native_module()->wire_bytes();

      const uint8_t* start = module_bytes.begin() + ref.offset();
      const uint8_t* end = module_bytes.begin() + ref.end_offset();

      auto sig = FixedSizeSignature<ValueType>::Returns(expected);
      // We have already validated the expression, so we might as well
      // revalidate it as non-shared, which is strictly more permissive.
      // TODO(14616): Rethink this.
      constexpr bool kIsShared = false;
      FunctionBody body(&sig, ref.offset(), start, end, kIsShared);
      WasmDetectedFeatures detected;
      const WasmModule* module = trusted_instance_data->module();
      ValueOrError result;
      {
        // We need a scope for the decoder because its destructor resets some
        // Zone elements, which has to be done before we reset the Zone
        // afterwards.
        // We use FullValidationTag so we do not have to create another template
        // instance of WasmFullDecoder, which would cost us >50Kb binary code
        // size.
        WasmFullDecoder<Decoder::FullValidationTag, ConstantExpressionInterface,
                        kConstantExpression>
            decoder(zone, module, WasmEnabledFeatures::All(), &detected, body,
                    module, isolate, trusted_instance_data,
                    shared_trusted_instance_data);

        decoder.DecodeFunctionBody();

        result = decoder.interface().has_error()
                     ? ValueOrError(decoder.interface().error())
                     : ValueOrError(decoder.interface().computed_value());
      }

      zone->Reset();

      return result;
    }
  }
}
```

This function is called on every cases that require constant expression evaluation (global init, data/table segment offset, element segment entry, etc). Unfortunately, `WasmFullDecoder<Decoder::FullValidationTag, ...>` is used which typechecks the expression result type with the expected type - only valid typechecked expression are allowed. (Note: failure cases still successfully result in a `kWasmVoid` typed `WasmValue`, but this is difficult to exploit.)

This can still be exploited by tricking `InstanceBuilder::InitGlobals()` into using a yet uninitialized reference typed global value, which initially has the placeholder value `undefined`.

`DecodeGlobalSection()` originally enforces initialization order of the globals by the decoding phase inside `consume_init_expr()`:

```
  void DecodeGlobalSection() {
    uint32_t globals_count = consume_count("globals count", kV8MaxWasmGlobals);
    uint32_t imported_globals = static_cast<uint32_t>(module_->globals.size());
    // It is important to not resize the globals vector from the beginning,      // [!] this enforces initialization order
    // because we use its current size when decoding the initializer.
    module_->globals.reserve(imported_globals + globals_count);
    for (uint32_t i = 0; ok() && i < globals_count; ++i) {
      // ...
      ConstantExpression init = consume_init_expr(module_.get(), type, shared);
      module_->globals.push_back(
          WasmGlobal{.type = type,
                     .mutability = mutability,
                     .init = init,
                     .index = 0,  // set later in CalculateGlobalOffsets
                     .shared = shared});
      if (shared) module_->has_shared_part = true;
    }
  }
```

At `InstanceBuilder::InitGlobals()`, we have all the `module_->globals` entries ready but are initializing them in order starting from index 0. This allows us to use a global value that is yet uninitialized, which returns `undefined` but is typed to be the global's type. In the attached PoC, we set up the module so that `global[0]` is initialized with `global.get 0`, which uses its own placeholder value of `undefined`.

This finally results in a type confusion, where using the global value results in `undefined` being confused as the global's type. This interestingly also immediately leads to arbitrary caged read/write primitive, as `undefined` has the following memory layout:

```
pwndbg> x/4wx 0x121300000068
0x121300000068: 0x000004f5      0x00000000      0x7ff80000      0x00005bb1
```

The entry at index 2, `0x7ff80000`, corresponds to the `length` field for `WasmArray` types. Thus we can confuse `undefined` to a `i32` array and obtain caged read/write primitive.

> Note: This bug also implies that `wasm_max_module_size` should never be allowed to be set higher than the current `kV8MaxWasmModuleSize` limit. However, there are no such invariants enforced.
> 
> Note 2: This bug may also be exploitable by overflowing the module size outside of `int`/`uint32_t` range, but this has not been investigated further as overflowing 1 GiB is already enough.

#### Bisect

  * Module size check bug introduced by commit [549692c](<https://chromiumdash.appspot.com/commit/549692cbc0ab4e9929e6e5f13db879072b119fb0>) in M63 that introduced WASM streaming compilation.
  * 30-bit offset optimization introduced by commit [e557383](<https://chromiumdash.appspot.com/commit/e557383c83d99a0b06168e87487018f94d29a467>) in M99 that optimizes constant expression decoding.

### VERSION

See bisect commit release info in Chromium Dash for more info: [549692c](<https://chromiumdash.appspot.com/commit/549692cbc0ab4e9929e6e5f13db879072b119fb0>), [e557383](<https://chromiumdash.appspot.com/commit/e557383c83d99a0b06168e87487018f94d29a467>)

Current exploit uses WasmGC, but this may also be exploitable even before the introduction of WasmGC as the underlying bug is technically irrelevant with WasmGC.

This (at least) affects all Chrome builds with WasmGC available by default, which is M112 up to latest (M112 ~ M118 behind Origin Trials, later shipped in M119~). The root cause exists from M99~, any may even affect M63~ if `int`/`uint32_t` overflow is feasible.

Chrome Version: M112 (?) ~ latest (tested on latest canary, 131.0.6727.0)  
Operating System: All

### REPRODUCTION CASE

Attached `poc.html` which exploits the vulnerability to obtain arbitrary caged read/write, then writes into cage offset `0x4242424` a value of `0x13333337` to demonstrate a crash.

In my local environment the repro required ~5GB of resident memory, so I recommend running this on an environment with 8GB or more memory. Also, ClusterFuzz may have a hard time reproing due to 1 GiB module creation - locally it repros in 3 seconds, but I recommend giving CF up to 60 seconds.

### FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION

Type of crash: Renderer  
Crash State: Crashes within JIT code, while trying to `array.set` which results in writing `0x13333337` into cage offset `0x4242424`.

### CREDIT INFORMATION

Reporter credit: Seunghyun Lee (@0x10n) of CMU CyLab

* * *

Full exploit coming soon... (again??)


---

**#2 — se...@gmail.com — Sep 20, 2024 04:19PM**

Attached full exploit `exp.html` that pops `calc` from a `--no-sandbox` renderer. Tested on Windows x86-64, Chrome build `131.0.6727.0 (Official Build)` (latest canary). The latter parts regarding v8sbx escape and RCE are copied without any modification from [b/360533914](<https://issues.chromium.org/issues/360533914>), [b/365802567](<https://issues.chromium.org/issues/365802567>).

Fix would be to verify total received buffer length and throw/abort if going over the limit on every buffer received (`OnBytesReceived()`), **likely for both`AsyncStreamingDecoder` and `SyncStreamingDecoder`**.


---

**#3 — se...@gmail.com — Sep 21, 2024 02:12AM**

A `d8`-compatible version of the initial PoC, just in case anyone wants to test this out without running a full-fledged Chrome runner.

Run the script in `d8` with the following flags: `--wasm-test-streaming --wasm_max_module_size=1500000000 --module`

  * `--wasm-test-streaming` to enable `WebAssembly.instantiateStreaming()`
  * `--wasm_max_module_size=1500000000` to manually lift the module size limitation of 1GiB, which is only present in `--wasm-test-streaming` mode and not in real Chrome builds 
    * Note [Blink's `WasmStreamingCallback`](<https://source.chromium.org/chromium/chromium/src/+/main:third_party/blink/renderer/bindings/core/v8/v8_wasm_response_extensions.cc;drc=f95a5679dc033cb7a1536416df1ba11b036a8401;l=637>) and the [testing mode `WasmStreamingCallback`](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/wasm-js.cc;drc=4e7ee87bb16e7d3b300ecf83c5b074f82874ff74;l=3394>). The former actually streaming decodes the body from a `Response`/`Promise<Response>`, while the latter simply receives an `ArrayBuffer` and then runs [`GetFirstArgumentAsBytes()`](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/wasm-js.cc;drc=4e7ee87bb16e7d3b300ecf83c5b074f82874ff74;l=680>) which triggers the check against `max_module_size()` which is absent in the former.
  * `--module` to enable top-level awaits


---

**#4 — se...@gmail.com — Sep 23, 2024 06:46AM**

Verified that the bug exists from at least M99.

Attached a PoC that crashes while attempting to `SetFunctionTableEntry()` on an `undefined` entry. This results in type confusion from `undefined` to `WasmInternalFunction`, ultimately resulting in a crash while deserializing fake `WasmCapiFunction`'s `serialized_signature` (based on types from M99). Tested on branch base position [961656](<https://commondatastorage.googleapis.com/chromium-browser-snapshots/index.html?prefix=Win_x64/961656/>), matching 99.0.4844.0. Note that even on that version the bug is still likely to be exploitable due to how `external` points to tagged address that may be fully controlled by the attacker (as shown by the `arrays` spray in the PoC).


---

**#5 — cl...@appspot.gserviceaccount.com — Sep 23, 2024 10:30PM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=6041534784798720](<https://clusterfuzz.com/testcase?key=6041534784798720>).


---

**#6 — se...@gmail.com — Sep 23, 2024 11:25PM**

Re #5: FYI, Chrome does not need the `--wasm-test-streaming --wasm_max_module_size=1500000000 --module` flags and the bug should trigger on default. Not that it's relevant to the repro task in CF being broken...


---

**#7 — se...@gmail.com — Sep 24, 2024 12:03AM**

ASAN log from a local run of the first PoC ([comment#1](<https://issues.chromium.org/issues/368241697#comment1>)) with the same build as that of [https://clusterfuzz.com/testcase?key=6041534784798720](<https://clusterfuzz.com/testcase?key=6041534784798720>).

```
=================================================================
==8504==ERROR: AddressSanitizer: access-violation on unknown address 0x005004242424 (pc 0x7e870c9c18c9 bp 0x003e7d7fd1b0 sp 0x003e7d7fd190 T0)
==8504==The signal is caused by a WRITE memory access.
SCARINESS: 30 (wild-addr-write)
    #0 0x7e870c9c18c8  (<unknown module>)
    #1 0x7e870c9c188a  (<unknown module>)
    #2 0x005000000774  (<unknown module>)
    #3 0x7e83000c06ec  (<unknown module>)
    #4 0x000000000007  (<unknown module>)
    #5 0x003e7d7fd1e7  (<unknown module>)
    #6 0x7ffcfc54c149 in Builtins_JSToWasmWrapperAsm (C:\Users\Xion\Desktop\win32-release_x64_asan-win32-release_x64-1358757\chrome.dll+0x1a742c149)
    #7 0x7ffcfc54c149 in Builtins_JSToWasmWrapperAsm (C:\Users\Xion\Desktop\win32-release_x64_asan-win32-release_x64-1358757\chrome.dll+0x1a742c149)
    #8 0x7ffcfc622305 in Builtins_JSToWasmWrapper (C:\Users\Xion\Desktop\win32-release_x64_asan-win32-release_x64-1358757\chrome.dll+0x1a7502305)
    #9 0x7ffcfc4b059d in Builtins_InterpreterEntryTrampoline (C:\Users\Xion\Desktop\win32-release_x64_asan-win32-release_x64-1358757\chrome.dll+0x1a739059d)
    #10 0x7ffcfc4f21ee in Builtins_AsyncFunctionAwaitResolveClosure (C:\Users\Xion\Desktop\win32-release_x64_asan-win32-release_x64-1358757\chrome.dll+0x1a73d21ee)
    #11 0x7ffcfc5d1da9 in Builtins_PromiseFulfillReactionJob (C:\Users\Xion\Desktop\win32-release_x64_asan-win32-release_x64-1358757\chrome.dll+0x1a74b1da9)
    #12 0x7ffcfc4e0eff in Builtins_RunMicrotasks (C:\Users\Xion\Desktop\win32-release_x64_asan-win32-release_x64-1358757\chrome.dll+0x1a73c0eff)
    #13 0x7ffcfc4ae032 in Builtins_JSRunMicrotasksEntry (C:\Users\Xion\Desktop\win32-release_x64_asan-win32-release_x64-1358757\chrome.dll+0x1a738e032)
    #14 0x7ffcda135e8e in v8::internal::`anonymous namespace'::Invoke C:\b\s\w\ir\cache\builder\src\v8\src\execution\execution.cc:435:41
    #15 0x7ffcda139ba8 in v8::internal::`anonymous namespace'::InvokeWithTryCatch C:\b\s\w\ir\cache\builder\src\v8\src\execution\execution.cc:477:18
    #16 0x7ffcda13a07a in v8::internal::Execution::TryRunMicrotasks(class v8::internal::Isolate *, class v8::internal::MicrotaskQueue *) C:\b\s\w\ir\cache\builder\src\v8\src\execution\execution.cc:578:10
    #17 0x7ffcda1d74de in v8::internal::MicrotaskQueue::RunMicrotasks(class v8::internal::Isolate *) C:\b\s\w\ir\cache\builder\src\v8\src\execution\microtask-queue.cc:185:22
    #18 0x7ffcda1d701e in v8::internal::MicrotaskQueue::PerformCheckpointInternal(class v8::Isolate *) C:\b\s\w\ir\cache\builder\src\v8\src\execution\microtask-queue.cc:129:3
    #19 0x7ffceced907e in blink::V8ScriptRunner::CallFunction(class v8::Local<class v8::Function>, class blink::ExecutionContext *, class v8::Local<class v8::Value>, int, class v8::Local<class v8::Value> *const, class v8::Isolate *) C:\b\s\w\ir\cache\builder\src\third_party\blink\renderer\bindings\core\v8\v8_script_runner.cc:888:1
    #20 0x7ffcf641dfa0 in blink::bindings::CallbackInvokeHelper<class blink::CallbackFunctionWithTaskAttributionBase, 0, 0>::Call(int, class v8::Local<class v8::Value> *) C:\b\s\w\ir\cache\builder\src\third_party\blink\renderer\bindings\core\v8\callback_invoke_helper.cc:162:10
    #21 0x7ffcf6a9dad7 in blink::V8EventHandlerNonNull::InvokeWithoutRunnabilityCheck(class blink::bindings::V8ValueOrScriptWrappableAdapter, class blink::HeapVector<class blink::ScriptValue, 0> const &) C:\b\s\w\ir\cache\builder\src\out\Release_x64\gen\third_party\blink\renderer\bindings\core\v8\v8_event_handler_non_null.cc:189:13
    #22 0x7ffcf26de1c6 in blink::JSEventHandler::InvokeInternal(class blink::EventTarget &, class blink::Event &, class v8::Local<class v8::Value>) C:\b\s\w\ir\cache\builder\src\third_party\blink\renderer\bindings\core\v8\js_event_handler.cc:134:14
    #23 0x7ffcf20b82da in blink::JSBasedEventListener::Invoke(class blink::ExecutionContext *, class blink::Event *) C:\b\s\w\ir\cache\builder\src\third_party\blink\renderer\bindings\core\v8\js_based_event_listener.cc:158:5
    #24 0x7ffced04d8f9 in blink::EventTarget::FireEventListeners(class blink::Event &, class blink::EventTargetData *, class blink::HeapVector<class cppgc::internal::BasicMember<class blink::RegisteredEventListener, class cppgc::internal::StrongMemberTag, struct cppgc::internal::DijkstraWriteBarrierPolicy, class cppgc::internal::DisabledCheckingPolicy, class cppgc::internal::CompressedPointer>, 1>) C:\b\s\w\ir\cache\builder\src\third_party\blink\renderer\core\dom\events\event_target.cc:1112:15
    #25 0x7ffced04b5ee in blink::EventTarget::FireEventListeners(class blink::Event &) C:\b\s\w\ir\cache\builder\src\third_party\blink\renderer\core\dom\events\event_target.cc:1031:29
    #26 0x7ffcece8a414 in blink::LocalDOMWindow::DispatchEvent(class blink::Event &, class blink::EventTarget *) C:\b\s\w\ir\cache\builder\src\third_party\blink\renderer\core\frame\local_dom_window.cc:2134:10
    #27 0x7ffcece89ce9 in blink::LocalDOMWindow::DispatchLoadEvent(void) C:\b\s\w\ir\cache\builder\src\third_party\blink\renderer\core\frame\local_dom_window.cc:2094:5
    #28 0x7ffcece895fa in blink::LocalDOMWindow::DispatchWindowLoadEvent(void) C:\b\s\w\ir\cache\builder\src\third_party\blink\renderer\core\frame\local_dom_window.cc:864:3
    #29 0x7ffcece89ed4 in blink::LocalDOMWindow::DocumentWasClosed(void) C:\b\s\w\ir\cache\builder\src\third_party\blink\renderer\core\frame\local_dom_window.cc:868:3
    #30 0x7ffcecc11a78 in blink::Document::ImplicitClose(void) C:\b\s\w\ir\cache\builder\src\third_party\blink\renderer\core\dom\document.cc:3900:18
    #31 0x7ffcecc12aa3 in blink::Document::CheckCompletedInternal(void) C:\b\s\w\ir\cache\builder\src\third_party\blink\renderer\core\dom\document.cc:4016:5
    #32 0x7ffcecc11636 in blink::Document::CheckCompleted(void) C:\b\s\w\ir\cache\builder\src\third_party\blink\renderer\core\dom\document.cc:3978:7
    #33 0x7ffceceeaffa in blink::FrameLoader::FinishedParsing(void) C:\b\s\w\ir\cache\builder\src\third_party\blink\renderer\core\loader\frame_loader.cc:453:26
    #34 0x7ffcecc4b9ad in blink::Document::FinishedParsing(void) C:\b\s\w\ir\cache\builder\src\third_party\blink\renderer\core\dom\document.cc:7409:21
    #35 0x7ffcf13cb434 in blink::HTMLDocumentParser::PrepareToStopParsing(void) C:\b\s\w\ir\cache\builder\src\third_party\blink\renderer\core\html\parser\html_document_parser.cc:568:3
    #36 0x7ffcf13d10e4 in blink::HTMLDocumentParser::AttemptToEnd(void) C:\b\s\w\ir\cache\builder\src\third_party\blink\renderer\core\html\parser\html_document_parser.cc:1115:3
    #37 0x7ffcf13cbd91 in blink::HTMLDocumentParser::PumpTokenizerIfPossible(void) C:\b\s\w\ir\cache\builder\src\third_party\blink\renderer\core\html\parser\html_document_parser.cc:653:5
    #38 0x7ffcf13cc632 in blink::HTMLDocumentParser::DeferredPumpTokenizerIfPossible(bool, class base::TimeTicks) C:\b\s\w\ir\cache\builder\src\third_party\blink\renderer\core\html\parser\html_document_parser.cc:625:7
    #39 0x7ffcf13eb6a5 in base::internal::Invoker<struct base::internal::FunctorTraits<void (__cdecl blink::HTMLDocumentParser::*&&)(bool, class base::TimeTicks), class cppgc::internal::BasicPersistent<class blink::HTMLDocumentParser, struct cppgc::internal::StrongPersistentPolicy, class cppgc::internal::IgnoreLocationPolicy, class cppgc::internal::DisabledCheckingPolicy> &&, bool &&, class base::TimeTicks &&>, struct base::internal::BindState<1, 1, 0, void (__cdecl blink::HTMLDocumentParser::*)(bool, class base::TimeTicks), class cppgc::internal::BasicPersistent<class blink::HTMLDocumentParser, struct cppgc::internal::StrongPersistentPolicy, class cppgc::internal::IgnoreLocationPolicy, class cppgc::internal::DisabledCheckingPolicy>, bool, class base::TimeTicks>, (void)>::RunOnce(class base::internal::BindStateBase *) C:\b\s\w\ir\cache\builder\src\base\functional\bind_internal.h:980:12
    #40 0x7ffce5750800 in base::TaskAnnotator::RunTaskImpl(struct base::PendingTask &) C:\b\s\w\ir\cache\builder\src\base\task\common\task_annotator.cc:202:34
    #41 0x7ffcea27a8fd in base::sequence_manager::internal::ThreadControllerWithMessagePumpImpl::DoWorkImpl(class base::LazyNow *) C:\b\s\w\ir\cache\builder\src\base\task\sequence_manager\thread_controller_with_message_pump_impl.cc:470:23
    #42 0x7ffcea2796a9 in base::sequence_manager::internal::ThreadControllerWithMessagePumpImpl::DoWork(void) C:\b\s\w\ir\cache\builder\src\base\task\sequence_manager\thread_controller_with_message_pump_impl.cc:332:40
    #43 0x7ffcea2bdf9e in base::MessagePumpDefault::Run(class base::MessagePump::Delegate *) C:\b\s\w\ir\cache\builder\src\base\message_loop\message_pump_default.cc:40:55
    #44 0x7ffcea27c5cf in base::sequence_manager::internal::ThreadControllerWithMessagePumpImpl::Run(bool, class base::TimeDelta) C:\b\s\w\ir\cache\builder\src\base\task\sequence_manager\thread_controller_with_message_pump_impl.cc:640:12
    #45 0x7ffce57aa46e in base::RunLoop::Run(class base::Location const &) C:\b\s\w\ir\cache\builder\src\base\run_loop.cc:133:14
    #46 0x7ffce94e3a2a in content::RendererMain(struct content::MainFunctionParams) C:\b\s\w\ir\cache\builder\src\content\renderer\renderer_main.cc:361:16
    #47 0x7ffce3970cd1 in content::RunOtherNamedProcessTypeMain(class std::__Cr::basic_string<char, struct std::__Cr::char_traits<char>, class std::__Cr::allocator<char>> const &, struct content::MainFunctionParams, class content::ContentMainDelegate *) C:\b\s\w\ir\cache\builder\src\content\app\content_main_runner_impl.cc:795:14
    #48 0x7ffce3972f2f in content::ContentMainRunnerImpl::Run(void) C:\b\s\w\ir\cache\builder\src\content\app\content_main_runner_impl.cc:1164:10
    #49 0x7ffce3967535 in content::RunContentProcess(struct content::ContentMainParams, class content::ContentMainRunner *) C:\b\s\w\ir\cache\builder\src\content\app\content_main.cc:356:36
    #50 0x7ffce39680dd in content::ContentMain(struct content::ContentMainParams) C:\b\s\w\ir\cache\builder\src\content\app\content_main.cc:369:10
    #51 0x7ffcd51216b0 in ChromeMain C:\b\s\w\ir\cache\builder\src\chrome\app\chrome_main.cc:231:12
    #52 0x7ff75329438d in MainDllLoader::Launch(struct HINSTANCE__*, class base::TimeTicks) C:\b\s\w\ir\cache\builder\src\chrome\app\main_dll_loader_win.cc:201:12
    #53 0x7ff75329200c in main C:\b\s\w\ir\cache\builder\src\chrome\app\chrome_exe_main_win.cc:351:20
    #54 0x7ff7536cc2bb in __scrt_common_main_seh D:\a\_work\1\s\src\vctools\crt\vcstartup\src\startup\exe_common.inl:288
    #55 0x7ffd6bb3257c  (C:\WINDOWS\System32\KERNEL32.DLL+0x18001257c)
    #56 0x7ffd6d6caa47  (C:\WINDOWS\SYSTEM32\ntdll.dll+0x18005aa47)

AddressSanitizer can not provide additional info.
SUMMARY: AddressSanitizer: access-violation (<unknown module>)

==8504==ADDITIONAL INFO

==8504==Note: Please include this section with the ASan report.
Task trace:
    #0 0x7ffcf13d093e in blink::HTMLDocumentParser::SchedulePumpTokenizer(bool) C:\b\s\w\ir\cache\builder\src\third_party\blink\renderer\core\html\parser\html_document_parser.cc:886:7
    #1 0x7ffce5e79d29 in IPC::ChannelAssociatedGroupController::Accept(class mojo::Message *) C:\b\s\w\ir\cache\builder\src\ipc\ipc_mojo_bootstrap.cc:1154:13

Command line: `"C:\Users\Xion\Desktop\win32-release_x64_asan-win32-release_x64-1358757\chrome.exe" --type=renderer --string-annotations=is-enterprise-managed=no --no-pre-read-main-dll --disable-in-process-stack-traces --no-sandbox --file-url-path-alias="/gen=C:\Users\Xion\Desktop\win32-release_x64_asan-win32-release_x64-1358757\gen" --video-capture-use-gpu-memory-buffer --lang=ko --device-scale-factor=1 --num-raster-threads=4 --enable-main-frame-before-activation --renderer-client-id=5 --time-ticks-at-unix-epoch=-1726990649352496 --launch-time-ticks=112962644138 --metrics-shmem-handle=3136,i,4853050985805574246,15652391961047868325,2097152 --field-trial-handle=3132,i,7804154520854205151,2716771143677104168,262144 --variations-seed-version --enable-logging=stderr --v=1 --mojo-platform-channel-handle=3128 /prefetch:1`

==8504==END OF ADDITIONAL INFO
==8504==ABORTING
```


---

**#8 — sk...@google.com — Sep 24, 2024 04:12AM**

Assigning to the latest code editor!


---

**#9 — cl...@chromium.org — Sep 24, 2024 06:26PM**

Jakob, can you take this one? Maybe all that's missing is a size check in the right place in the streaming decoder.


---

**#10 — jk...@chromium.org — Sep 24, 2024 10:00PM**

Thank you, Seunghyun, for another excellent report! I appreciate the d8-based test in particular :-)

Fix coming up.


---

**#11 — se...@gmail.com — Sep 24, 2024 11:51PM**

It seems that with [https://crrev.com/c/5886728](<https://crrev.com/c/5886728>) the PoC hits `CHECK_LE(total_length, max_module_size());` instead of gracefully failing, because we always call `AsyncStreamingDecoder::Finish()` regardless of the failure.

AFAICT `SyncStreamingDecoder` variant seems safe, as it always passes the buffer through `ModuleDecoderImpl::DecodeModule()` which does its own check against `max_module_size()`.


---

**#12 — jk...@chromium.org — Sep 25, 2024 12:36AM**

#11: Good point, thanks! That's what I get for addressing reviewer feedback without testing again :-)

Fixed in patch set 3.


---

**#13 — pe...@google.com — Sep 25, 2024 12:43AM**

Setting milestone because of s0/s1 severity.


---

**#14 — pe...@google.com — Sep 25, 2024 12:43AM**

This is a serious security regression. If you are not able to fix this quickly, please revert the change that introduced it.

If this doesn't affect a release branch, or has not been properly classified for severity, please update the Security Impact hotlist or the Severity field, and remove the ReleaseBlock hotlist.


---

**#15 — se...@gmail.com — Sep 25, 2024 12:45AM**

Re #12: Aside from the crashiness, according to [this comment](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/streaming-decoder.cc;drc=12bc2086862d5538c9303de194b3e0199cf35def;l=286>) it is illegal to call `Finish()` after `Fail()`, which is misleading considering how the whole function extensively uses `ok()` to check failure state?


---

**#16 — ap...@google.com — Sep 25, 2024 06:23PM**

Project: v8/v8  
Branch: main  
  
commit 9542895cdd3dbd97da3d9032ddb36fd4feb612e4  
Author: Jakob Kummerow <[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)>  
Date: Tue Sep 24 17:34:49 2024  
  
[wasm][streaming] Properly check max module size  
  
and allow d8-based tests for it.  
  
Fixed: 368241697  
Change-Id: Iddc9f7e669de7a1d79dccbc99bcc5fb43dad67a1  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5886728](<https://chromium-review.googlesource.com/c/v8/v8/+/5886728>)  
Reviewed-by: Clemens Backes <[clemensb@chromium.org](<mailto:clemensb@chromium.org>)>  
Reviewed-by: Matthias Liedtke <[mliedtke@chromium.org](<mailto:mliedtke@chromium.org>)>  
Auto-Submit: Jakob Kummerow <[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)>  
Commit-Queue: Jakob Kummerow <[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)>  
Cr-Commit-Position: refs/heads/main@{#96272}  
  
M src/wasm/streaming-decoder.cc  
M src/wasm/wasm-engine.cc  
M src/wasm/wasm-js.cc  
  
[https://chromium-review.googlesource.com/5886728](<https://chromium-review.googlesource.com/5886728>)


---

**#17 — jk...@chromium.org — Sep 25, 2024 06:44PM**

#15: That just seems to be an inaccurate comment. Fix: [https://chromium-review.googlesource.com/c/v8/v8/+/5890745](<https://chromium-review.googlesource.com/c/v8/v8/+/5890745>)


---

**#18 — am...@chromium.org — Oct 1, 2024 02:00AM**

The foundin on this issue was incorrect, so I'm updating it accordingly especially since the fix should likely require / be approved for backmerge


---

**#19 — am...@chromium.org — Oct 1, 2024 02:59AM**

In this case, I'm going to go ahead and add all the review labels; since RCs for this week's releases are already in the process of being cut, I'll revisit this for merge review / approval tomorrow after the releases have been shipped


---

**#20 — am...@chromium.org — Oct 2, 2024 07:18AM**

[https://crrev.com/c/5886728](<https://crrev.com/c/5886728>) and [https://crrev.com/c/5890745](<https://crrev.com/c/5890745>) approved for backmerges; please merge to 13.0, 12.9, and 12.8 at soonest (by EOD tomorrow, 2 October) since Thursday is a German public holiday


---

**#21 — ap...@google.com — Oct 2, 2024 10:43PM**

Project: v8/v8  
Branch: refs/branch-heads/12.8  
Author: Jakob Kummerow <[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/5904119](<https://chromium-review.googlesource.com/5904119>)

Merged: [wasm][streaming] Properly check max module size

* * *

Expand for full commit details

```
Merged: [wasm][streaming] Properly check max module size

and allow d8-based tests for it.

(cherry picked from commit 9542895cdd3dbd97da3d9032ddb36fd4feb612e4)

Fixed: 368241697
Change-Id: Ic1a39ee8c307df760cebbfd5854956edf846eb74
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/5904119
Auto-Submit: Jakob Kummerow <jkummerow@chromium.org>
Commit-Queue: Jakob Kummerow <jkummerow@chromium.org>
Reviewed-by: Clemens Backes <clemensb@chromium.org>
Commit-Queue: Clemens Backes <clemensb@chromium.org>
Cr-Commit-Position: refs/branch-heads/12.8@{#73}
Cr-Branched-From: 70cbb397b153166027e34c75adf8e7993858222e-refs/heads/12.8.374@{#1}
Cr-Branched-From: 451b63ed4251c2b21c56144d8428f8be3331539b-refs/heads/main@{#95151}
```

* * *

Files:

  * M `src/wasm/streaming-decoder.cc`
  * M `src/wasm/wasm-engine.cc`
  * M `src/wasm/wasm-js.cc`

* * *

Hash: 213d3905d02d6ee87bb519361b3fb6cdb181ccb7  
Date: Tue Sep 24 17:34:49 2024

* * *


---

**#22 — pe...@google.com — Oct 2, 2024 10:44PM**

LTS Milestone M126

This issue has been flagged as a merge candidate for Chrome OS' LTS channel. If selected, our merge team will handle any additional merges. To help us determine if this issue requires a merge to LTS, please answer this short questionnaire:

  1. Was this issue a regression for the milestone it was found in?
  2. Is this issue related to a change or feature merged after the latest LTS Milestone?


---

**#23 — ap...@google.com — Oct 2, 2024 10:45PM**

Project: v8/v8  
Branch: refs/branch-heads/12.9  
Author: Jakob Kummerow <[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/5904120](<https://chromium-review.googlesource.com/5904120>)

Merged: [wasm][streaming] Properly check max module size

* * *

Expand for full commit details

```
Merged: [wasm][streaming] Properly check max module size

and allow d8-based tests for it.

(cherry picked from commit 9542895cdd3dbd97da3d9032ddb36fd4feb612e4)

Fixed: 368241697
Change-Id: I55bfcb4e1760e1833f5fe0b2fec3b3bfc8bf7108
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/5904120
Commit-Queue: Clemens Backes <clemensb@chromium.org>
Commit-Queue: Jakob Kummerow <jkummerow@chromium.org>
Reviewed-by: Clemens Backes <clemensb@chromium.org>
Auto-Submit: Jakob Kummerow <jkummerow@chromium.org>
Cr-Commit-Position: refs/branch-heads/12.9@{#49}
Cr-Branched-From: 64a21d7ad7fca1ddc73a9264132f703f35000b69-refs/heads/12.9.202@{#1}
Cr-Branched-From: da4200b2cfe6eb1ad73c457ed27cf5b7ff32614f-refs/heads/main@{#95679}
```

* * *

Files:

  * M `src/wasm/streaming-decoder.cc`
  * M `src/wasm/wasm-engine.cc`
  * M `src/wasm/wasm-js.cc`

* * *

Hash: 94b35ad3dcb53090f89d36ca19ef07a55f5c3141  
Date: Tue Sep 24 17:34:49 2024

* * *


---

**#24 — ap...@google.com — Oct 2, 2024 10:47PM**

Project: v8/v8  
Branch: refs/branch-heads/13.0  
Author: Jakob Kummerow <[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/5904101](<https://chromium-review.googlesource.com/5904101>)

Merged: [wasm][streaming] Properly check max module size

* * *

Expand for full commit details

```
Merged: [wasm][streaming] Properly check max module size

and allow d8-based tests for it.

(cherry picked from commit 9542895cdd3dbd97da3d9032ddb36fd4feb612e4)

Fixed: 368241697
Change-Id: I3033c92392b188bc8093eb65523ec4420d87fbd7
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/5904101
Commit-Queue: Jakob Kummerow <jkummerow@chromium.org>
Reviewed-by: Clemens Backes <clemensb@chromium.org>
Auto-Submit: Jakob Kummerow <jkummerow@chromium.org>
Commit-Queue: Clemens Backes <clemensb@chromium.org>
Cr-Commit-Position: refs/branch-heads/13.0@{#25}
Cr-Branched-From: 4be854bd71ea878a25b236a27afcecffa2e29360-refs/heads/13.0.245@{#1}
Cr-Branched-From: 1f5183f7ad6cca21029fd60653d075730c644432-refs/heads/main@{#96103}
```

* * *

Files:

  * M `src/wasm/streaming-decoder.cc`
  * M `src/wasm/wasm-engine.cc`
  * M `src/wasm/wasm-js.cc`

* * *

Hash: c6839beb1b8bbb9156859ae68c0859fc026282b3  
Date: Tue Sep 24 17:34:49 2024

* * *


---

**#25 — sp...@google.com — Oct 3, 2024 09:56AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $55000.00 for this report.  
  
Rationale for this decision:  
high quality report demonstrating RCE in a sandboxed process / the renderer  
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#26 — am...@chromium.org — Oct 3, 2024 10:02AM**

Congratulations Seunghyun! Thank you for another excellent report with demonstration of RCE through a functional exploit -- very nice work!


---

**#27 — se...@gmail.com — Oct 3, 2024 10:34AM**

Thanks! I'd like to donate this bounty through Benevity too.

On another note, I'm planning to disclose details of many WASM-related vulnerabilities (including V8 Sandbox bypasses) that I've reported at POC2024 (Nov. 7-8) and CODE BLUE 2024 (Nov. 14-15), possibly including unfixed V8 Sandbox bypasses (but excluding [b/362780326](<https://issues.chromium.org/issues/362780326>)). Would this be OK?


---

**#28 — se...@gmail.com — Oct 3, 2024 10:39AM**

Oh and also, are there any Chrome VRP rules for old V8 security bugs? The VRP page mentions _"V8 security bugs older than M105 may be eligible for a reward higher than specified in the table, based on the age of the bug."_ but I don't know if this is still applicable.


---

**#29 — da...@google.com — Oct 3, 2024 07:13PM**

Your change has been approved. We will be taking M130 Beta RC cut tonight. Please land your changes before 5:30PM PST.


---

**#30 — am...@chromium.org — Oct 4, 2024 01:43AM**

> Thanks! I'd like to donate this bounty through Benevity too. Thanks for letting me know. I've put this down for donations processing via Benevity.

> On another note, I'm planning to disclose details of many WASM-related vulnerabilities (including V8 Sandbox bypasses) that I've reported at POC2024 (Nov. 7-8) and CODE BLUE 2024 (Nov. 14-15), possibly including unfixed V8 Sandbox bypasses (but excluding [b/362780326](<https://issues.chromium.org/issues/362780326>)). Would this be OK?

Thanks for checking, but both conferences are awfully close well before when we would publicly disclose. This is also to help ensure that users have an update and lessen the window of increased potential for n-day exploitation. We generally ask issues not be disclosed until 14 weeks after they are fixed to ensure all users have an opportunity to pick up the fix in a Stable channel update. Often we make exceptions for lower severity, less impactful issues when the disclosure is far off OR higher severity issues when the disclosure date if very near. This does NOT appear to be the case here.

Going through all of your WASM reports -- which there are five by my count (please correct me if I'm wrong) -- with only 1 being within what we would consider an acceptable disclosure period for severity high issues impacting Stable channel: [crbug.com/351327767](<https://crbug.com/351327767>) \-- resolved 11 July

The remaining four are not what we'd consider in an acceptable window for disclosure.

  1. This one, which was only just resolved 25 September
  2. [crbug.com/362780326](<https://crbug.com/362780326>) \-- still open / not yet resolved
  3. [crbug.com/365802567](<https://crbug.com/365802567>) \-- resolved 17 September
  4. [crbug.com/360533914](<https://crbug.com/360533914>) \-- resolved 20 August

In terms of the sandbox bypasses, we're okay with the disclosure of those -- that are resolved -- since we are planning to open all resolved sandbox bypasses early / soon, since we don't consider that full security boundary as of yet.

Your use of the words `I'm planning to disclose the details of many WASM-related vulnerabilities` is a bit concerning since it sounds that you have already submitted a talk which has been accepted. We're hopeful that this feedback will allow you to reconsider sharing any of the details of the four vulnerabilities above that we would not consider in an acceptable disclosure period at that time. If not, please let us know which ones you plan on disclosing the details so that we can prepare details and determine if there need to be communications to encourage folks to update in the light of forthcoming disclosures. Also, understandably we would need to withhold the bounties on these issues.


---

**#31 — se...@gmail.com — Oct 4, 2024 03:13AM**

Thanks for the prompt reply. A TL;DR would be that in the current version of the submitted talk, none of the described bugs are an issue as I have already verified that the talk is after the expected disclosure dates of all bugs intended to be disclosed (in fact, CFP deadline for both talks was much before the recent findings).

My talk intends to disclose details of the following vulnerabilities:

  * [b/344608204](<https://issues.chromium.org/issues/344608204>) \- TyphoonPWN 2024 submission, already public
  * [b/346197738](<https://issues.chromium.org/issues/346197738>) \- variant of the above, already public
  * [b/351327767](<https://issues.chromium.org/issues/351327767>) \- fixed Jul 11

I can be flexible with V8 Sandbox bypasses, especially those that are unresolved, as there are no concrete expectations to meet for the talk. But do note that **exploit for[b/351327767](<https://issues.chromium.org/issues/351327767>) involves the use of [b/350292240](<https://issues.chromium.org/issues/350292240>) which still isn't fixed, but which is soon reaching the 14 week deadline**.

I understand that the disclosure & fix dates of [b/360533914](<https://issues.chromium.org/issues/360533914>), [b/365802567](<https://issues.chromium.org/issues/365802567>), [b/368241697](<https://issues.chromium.org/issues/368241697>) (and [b/362780326](<https://issues.chromium.org/issues/362780326>), which is rather a non-issue really) are too recent and that these would preferrably be not included in the talk. The original comment may have been miscommunicated - it was not a unidirectional announcement but more of a question of whether the disclosure of these bugs could be coordinated so that these could be included in the talk, but agreeably this seems to be not the case.

One remaining question is whether any of the following would be acceptable:

  * Disclosing publicly available details of the bug (ex: release notes in chromereleases.googleblog.com, corresponding fix commit in crrev.com)
  * Disclosing that the bugs are exploitable (often immediately identifiable by reward amount or backmerge status, but is still technically a non-public detail)

Thanks again for the detailed response. Again, I want to clarify that I believe in coordinated disclosure and that I have no intentions to violate this trust - the talk is intended to help close the gap between offense and defense by facilitating more public researches, not to blast out some bugs.


---

**#32 — am...@chromium.org — Oct 4, 2024 05:25AM**

Thank you as well for the prompt, detailed, and considerate reply.

> I can be flexible with V8 Sandbox bypasses, especially those that are unresolved, as there are no concrete expectations to meet for the talk. But do note that exploit for [b/351327767](<https://issues.chromium.org/issues/351327767>) involves the use of [b/350292240](<https://issues.chromium.org/issues/350292240>) which still isn't fixed, but which is soon reaching the 14 week deadline.

I think we can also be pretty flexible with the sandbox bypasses. I think that even though there is a reliance here on an unresolved issue, you can be a little more forthcoming about the bypasses. In discussions between us on the security team, V8 Security, and V8 engineering we all agreed that we'll be opening all of the resolved bypasses early. I think we just all need to circle on our side exactly when we're doing this, but we did all agree to do it soon. Certainly by 7 November. So by opening the resolved one, we do know there may be some other not resolved issues that may be disclosed early and (as I recall) we are okay with that risk to share information with security researchers have about known bypass issues to further security research in this area.

> I understand that the disclosure & fix dates of [b/360533914](<https://issues.chromium.org/issues/360533914>), [b/365802567](<https://issues.chromium.org/issues/365802567>), [b/368241697](<https://issues.chromium.org/issues/368241697>) (and [b/362780326](<https://issues.chromium.org/issues/362780326>), which is rather a non-issue really) are too recent and that these would preferrably be not included in the talk. The original comment may have been miscommunicated - it was not a unidirectional announcement but more of a question of whether the disclosure of these bugs could be coordinated so that these could be included in the talk, but agreeably this seems to be not the case.

😅 okay great -- apologies for read there as being unidirectional and appreciate the clarification!

> One remaining question is whether any of the following would be acceptable:

> Disclosing publicly available details of the bug (ex: release notes in chromereleases.googleblog.com, corresponding fix commit in crrev.com)

> Disclosing that the bugs are exploitable (often immediately identifiable by reward amount or backmerge status, but is still technically a non-public detail)

I think discussions to this degree related to the non-disclosed bugs is just fine. We know there are plenty of eyes on vulnerabilities as soon as a draft CL makes it's way into Gerrit and more so once there's been release notes, CVE description, and a VRP reward. I know if I fire up twitter I'll see discourse related to the CL, so we're okay with pointing at these things in your talk as long as going into the granular details of how they are exploitable and the aspects of exploitability isn't part of the discussion.

> Thanks again for the detailed response. Again, I want to clarify that I believe in coordinated disclosure and that I have no intentions to violate this trust - the talk is intended to help close the gap between offense and defense by facilitating more public researches, not to blast out some bugs.

💜🙏 Amazing. This my presumption on a day to day basis and in general. We know at the end of the day, we can't guarantee non-disclosure, but I definitely want to make sure I dig into questions like this to ensure we're doing our part to protect users. We sincerely appreciate all your work here and all that it does towards that goal as well. Thanks again for the open dialogue!


---

**#33 — pe...@google.com — Oct 4, 2024 09:43PM**

This issue requires additional review before it can be merged to the LTS channel. Please answer the following questions to help us evaluate this merge:

  1. Number of CLs needed for this fix and links to them.
  2. Level of complexity (High, Medium, Low - Explain)
  3. Has this been merged to a stable release? beta release?
  4. Overall Recommendation (Yes, No)


---

**#34 — qk...@google.com — Oct 4, 2024 09:48PM**

1\. [https://chromium-review.googlesource.com/c/v8/v8/+/5905241](<https://chromium-review.googlesource.com/c/v8/v8/+/5905241>) and [https://chromium-review.googlesource.com/c/v8/v8/+/5906825](<https://chromium-review.googlesource.com/c/v8/v8/+/5906825>)  
2\. Low, no conflict  
3\. 128, 129, and 130  
4\. Yes, because the bug could affect M112 up to latest version according to the description.


---

**#35 — jk...@chromium.org — Oct 4, 2024 11:24PM**

#34: [https://chromium-review.googlesource.com/c/v8/v8/+/5906825](<https://chromium-review.googlesource.com/c/v8/v8/+/5906825>) is a comment-only patch and does not need to get backmerged. We haven't merged it to 128/129/130 either, and aren't planning to do so.

I do recommend backmerging [https://chromium-review.googlesource.com/c/v8/v8/+/5905241](<https://chromium-review.googlesource.com/c/v8/v8/+/5905241>) to any milestones you still care about.


---

**#36 — jk...@chromium.org — Oct 4, 2024 11:27PM**

#31/#32: Just a quick note regarding [issue 350292240](<https://issues.chromium.org/issues/350292240>): yes, that one's still on the to-do list. It's an example of the overall "we know the sandbox isn't complete yet" situation. We'll get to it as soon as time permits (currently working on _other_ cases where the sandbox is known not to be complete yet).


---

**#37 — qk...@google.com — Oct 7, 2024 02:18PM**

> I do recommend backmerging [https://chromium-review.googlesource.com/c/v8/v8/+/5905241](<https://chromium-review.googlesource.com/c/v8/v8/+/5905241>) to any milestones you still care about.  
  
Thank you for pointing it out. I abandon [https://crrev.com/c/5906825](<https://crrev.com/c/5906825>).


---

**#38 — gm...@google.com — Oct 8, 2024 11:49PM**

Merge approved for [https://chromium-review.googlesource.com/c/v8/v8/+/5905241](<https://chromium-review.googlesource.com/c/v8/v8/+/5905241>)


---

**#39 — ap...@google.com — Oct 10, 2024 04:09PM**

Project: v8/v8  
Branch: refs/branch-heads/12.6  
Author: Jakob Kummerow <[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/5905241](<https://chromium-review.googlesource.com/5905241>)

[M126-LTS][wasm][streaming] Properly check max module size

* * *

Expand for full commit details

```
[M126-LTS][wasm][streaming] Properly check max module size

and allow d8-based tests for it.

(cherry picked from commit 9542895cdd3dbd97da3d9032ddb36fd4feb612e4)

Fixed: 368241697
Change-Id: Iddc9f7e669de7a1d79dccbc99bcc5fb43dad67a1
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/5886728
Reviewed-by: Clemens Backes <clemensb@chromium.org>
Reviewed-by: Matthias Liedtke <mliedtke@chromium.org>
Auto-Submit: Jakob Kummerow <jkummerow@chromium.org>
Commit-Queue: Jakob Kummerow <jkummerow@chromium.org>
Cr-Original-Commit-Position: refs/heads/main@{#96272}
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/5905241
Commit-Queue: Gyuyoung Kim (xWF) <qkim@google.com>
Reviewed-by: Jakob Kummerow <jkummerow@chromium.org>
Cr-Commit-Position: refs/branch-heads/12.6@{#68}
Cr-Branched-From: 3c9fa12db3183a6f4ea53d2675adb66ea1194529-refs/heads/12.6.228@{#2}
Cr-Branched-From: 981bb15ba4dbf9e2381dfc94ec2c4af0b9c6a0b6-refs/heads/main@{#93835}
```

* * *

Files:

  * M `src/wasm/streaming-decoder.cc`
  * M `src/wasm/wasm-engine.cc`
  * M `src/wasm/wasm-js.cc`

* * *

Hash: 4f4cd3f00975cc6efa2600426f6c2a4c60ea54f1  
Date: Tue Sep 24 17:34:49 2024

* * *


---

**#40 — pe...@google.com — Jan 3, 2025 12:41AM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
