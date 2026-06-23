# [WASM] JIT Optimization Triggered TRAP on unknown address 0x000000000000

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1946004
CVE: CVE-2025-1933
Component: JavaScript: WebAssembly
Bounty: (unknown)
Date: 2025-02-05T07:08:05Z
Keywords: csectype-jit, reporter-external, sec-high

Created attachment 9463966
poc.js

Steps to reproduce:

My env:
Ubuntu 22.04 TLS
gecko-dev e85232b4b28ecc970240d39203e417d1c320623c

Build args:
../configure --disable-jemalloc --enable-fuzzing --enable-gczeal --enable-debug --enable-optimize --disable-shared-js --enable-address-sanitizer

Execution:
./dist/bin/js poc.js


Actual results:

AddressSanitizer:DEADLYSIGNAL
=================================================================
==2407027==ERROR: AddressSanitizer: TRAP on unknown address 0x000000000000 (pc 0x10c1009be66a bp 0x7fffe45805a0 sp 0x7fffe4580580 T0)
    #0 0x10c1009be66a  (<unknown module>)
    #1 0x10c100971be7  (<unknown module>)
    #2 0x10c1009eace9  (<unknown module>)
    #3 0x10c1008ced80  (<unknown module>)
    #4 0x55b8d3651cf2 in EnterBaseline(JSContext*, EnterJitData&) /data/workspace/gecko-dev/js/src/jit/BaselineJIT.cpp:143:5
    #5 0x55b8d3651cf2 in js::jit::EnterBaselineInterpreterAtBranch(JSContext*, js::InterpreterFrame*, unsigned char*) /data/workspace/gecko-dev/js/src/jit/BaselineJIT.cpp:199:26
    #6 0x55b8d1002b9e in js::Interpret(JSContext*, js::RunState&) /data/workspace/gecko-dev/js/src/vm/Interpreter.cpp:2107:17
    #7 0x55b8d0fc8763 in MaybeEnterInterpreterTrampoline(JSContext*, js::RunState&) /data/workspace/gecko-dev/js/src/vm/Interpreter.cpp:433:10
    #8 0x55b8d0fc781c in js::RunScript(JSContext*, js::RunState&) /data/workspace/gecko-dev/js/src/vm/Interpreter.cpp:502:13
    #9 0x55b8d0fcf251 in js::ExecuteKernel(JSContext*, JS::Handle<JSScript*>, JS::Handle<JSObject*>, js::AbstractFramePtr, JS::MutableHandle<JS::Value>) /data/workspace/gecko-dev/js/src/vm/Interpreter.cpp:893:13
    #10 0x55b8d0fcfdba in js::Execute(JSContext*, JS::Handle<JSScript*>, JS::Handle<JSObject*>, JS::MutableHandle<JS::Value>) /data/workspace/gecko-dev/js/src/vm/Interpreter.cpp:926:10
    #11 0x55b8d13bf4d2 in ExecuteScript(JSContext*, JS::Handle<JSObject*>, JS::Handle<JSScript*>, JS::MutableHandle<JS::Value>) /data/workspace/gecko-dev/js/src/vm/CompilationAndEvaluation.cpp:601:10
    #12 0x55b8d13bfae8 in JS_ExecuteScript(JSContext*, JS::Handle<JSScript*>) /data/workspace/gecko-dev/js/src/vm/CompilationAndEvaluation.cpp:625:10
    #13 0x55b8d0e2677a in RunFile(JSContext*, char const*, _IO_FILE*, CompileUtf8, bool, bool) /data/workspace/gecko-dev/js/src/shell/js.cpp:1311:10
    #14 0x55b8d0e2523a in Process(JSContext*, char const*, bool, FileKind) /data/workspace/gecko-dev/js/src/shell/js.cpp
    #15 0x55b8d0d83a04 in ProcessArgs(JSContext*, js::cli::OptionParser*) /data/workspace/gecko-dev/js/src/shell/js.cpp:11752:10
    #16 0x55b8d0d83a04 in Shell(JSContext*, js::cli::OptionParser*) /data/workspace/gecko-dev/js/src/shell/js.cpp:12006:12
    #17 0x55b8d0d6f43d in main /data/workspace/gecko-dev/js/src/shell/js.cpp:12421:12
    #18 0x7f925de79d8f in __libc_start_call_main csu/../sysdeps/nptl/libc_start_call_main.h:58:16

AddressSanitizer can not provide additional info.
SUMMARY: AddressSanitizer: TRAP (<unknown module>) 
==2407027==ABORTING


Expected results:

exit normally.

---

**Comment 1 — jdemooij@mozilla.com — 2025-02-06T13:04:17Z**

I can reproduce this. It looks like we fail the check in [this code](https://searchfox.org/mozilla-central/rev/d1fbe983fb7720f0a4aca0e748817af11c1a374e/js/src/jit/x64/MacroAssembler-x64.cpp#497-500) in `boxValue` while boxing an int32 value.

This means we're creating an `Int32Value` but the payload doesn't fit in 32 bits. This is dangerous because it'd create an invalid `JS::Value` and if the payload is sufficiently large it could corrupt the tag bits.

---

**Comment 2 — jdemooij@mozilla.com — 2025-02-10T09:07:24Z**

Here's a reduced test case that fails intermittently with `rr record -h` about 1 in every 10-20 runs with a Linux x64 debug build:
```js
let buf = new Uint8Array([0, 97, 115, 109, 1, 0, 0, 0, 1, 18, 3, 94, 120, 0, 96, 3, 127, 127, 127, 1, 127, 96, 2, 127, 127, 2, 127, 127, 3, 3, 2, 1, 2, 4, 1, 0, 7, 8, 1, 4, 109, 97, 105, 110, 0, 0, 10, 77, 2, 10, 0, 65, 0, 65, 0, 16, 1, 33, 0, 11, 64, 1, 4, 127, 3, 127, 65, 3, 11, 3, 127, 3, 127, 65, 3, 33, 3, 3, 127, 3, 127, 65, 3, 33, 5, 3, 127, 32, 5, 65, 1, 107, 34, 5, 4, 64, 12, 1, 11, 65, 5, 11, 4, 64, 11, 65, 0, 11, 26, 32, 3, 4, 64, 11, 65, 34, 11, 4, 64, 11, 65, 2, 11, 11, 11]);
let module = new WebAssembly.Module(buf);
let instance = new WebAssembly.Instance(module);
for (var i = 0; i < 10000; i++) {
  instance.exports.main(0, 0, 0);
}
```

What happens is this:
1. A Wasm-Ion function stores a stack result value of 3 (`LInteger`, `LWasmStoreSlot`) and then returns.
```
   0x5574bbc1052:       mov    $0x3,%eax
   0x5574bbc1057:       mov    %eax,(%rdx)
   0x5574bbc1059:       mov    $0x2,%eax
   0x5574bbc105e:       pop    %rbp
   0x5574bbc105f:       ret
```
2. This returns to a Wasm-Baseline function where we `pop` this value into `rax` (IIRC this happens in `popBlockResults` under `doReturn`). The value that's popped is `0x7ffd00000003`: the low bits are what we expect (3) but the high bits are garbage because the callee stored an int32.
```
   0x5574bb9106a:       lea    -0x28(%rbp),%rsp
   0x5574bb9106e:       mov    %eax,%eax
   0x5574bb91070:       mov    %eax,0x24(%rsp)
   0x5574bb91074:       pop    %rax
   0x5574bb91075:       jmp    0x5574bb9107b
   0x5574bb9107a:       int3
   0x5574bb9107b:       add    $0x20,%rsp
   0x5574bb9107f:       pop    %rbp
   0x5574bb91080:       ret
```
3. We return to the JIT entry stub [and do this](https://searchfox.org/mozilla-central/source/js/src/wasm/WasmStubs.cpp#1244-1245):
```cpp
        // No widening is required, as the value is boxed.
        masm.boxNonDouble(JSVAL_TYPE_INT32, ReturnReg, JSReturnOperand);
```
This comment (added in bug 1736531) seems wrong because `boxNonDouble` *does* expect a widened (= upper bits zero) value; that's what's causing the assertion failure.

---

**Comment 3 — jdemooij@mozilla.com — 2025-02-10T09:19:04Z**

In `GenerateDirectCallFromJit` we [already widen](https://searchfox.org/mozilla-central/rev/206eaea9a2fd4307da16e1614cd934920368165a/js/src/wasm/WasmStubs.cpp#1544) i32 return values so I think we just need to follow that for the JitEntry stub.

---

**Comment 4 — jdemooij@mozilla.com — 2025-02-10T09:31:11Z**

Created attachment 9465096
Bug 1946004 - Widen i32 return values in GenerateJitEntry. r?rhunt!

---

**Comment 5 — jdemooij@mozilla.com — 2025-02-10T09:31:22Z**

Created attachment 9465097
Bug 1946004 - Add test and comment. r?rhunt!

---

**Comment 6 — jdemooij@mozilla.com — 2025-02-10T09:42:21Z**

I think sec-high is accurate: because the value in the register is OR-ed into the `Int32Value` bits, it's possible to construct an arbitrary `SymbolValue` or `BigIntValue` as these have similar type tags but with some additional bits set. Pulling this off also requires controlling the 'garbage' value that's stored in the stack slot, but that's likely not too difficult with stack spraying.

---

**Comment 7 — jdemooij@mozilla.com — 2025-02-11T08:44:57Z**

Comment on attachment 9465096
Bug 1946004 - Widen i32 return values in GenerateJitEntry. r?rhunt!

### Security Approval Request
* **How easily could an exploit be constructed based on the patch?**: Not very easy.
* **Do comments in the patch, the check-in comment, or tests included in the patch paint a bulls-eye on the security problem?**: No
* **Which branches (beta, release, and/or ESR) are affected by this flaw, and do the release status flags reflect this affected/unaffected state correctly?**: all
* **If not all supported branches, which bug introduced the flaw?**: None
* **Do you have backports for the affected branches?**: Yes
* **If not, how different, hard to create, and risky will they be?**: This patch should apply or it will be easy to backport.
* **How likely is this patch to cause regressions; how much testing does it need?**: It's a small and simple patch and very unlikely to cause regressions.
* **Is the patch ready to land after security approval is given?**: Yes
* **Is Android affected?**: Yes

---

**Comment 8 — tom@mozilla.com — 2025-02-12T16:44:35Z**

Comment on attachment 9465096
Bug 1946004 - Widen i32 return values in GenerateJitEntry. r?rhunt!

Approved to land and request uplift

---

**Comment 9 — pulsebot@bmo.tld — 2025-02-13T12:36:21Z**

Pushed by jdemooij@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/17a8382a336f
Widen i32 return values in GenerateJitEntry. r=rhunt

---

**Comment 10 — jdemooij@mozilla.com — 2025-02-13T15:14:47Z**

Comment on attachment 9465096
Bug 1946004 - Widen i32 return values in GenerateJitEntry. r?rhunt!

### Beta/Release Uplift Approval Request
* **User impact if declined/Reason for urgency**: Security bugs or crashes.
* **Is this code covered by automated tests?**: Yes
* **Has the fix been verified in Nightly?**: No
* **Needs manual test from QE?**: No
* **If yes, steps to reproduce**: 
* **List of other uplifts needed**: None
* **Risk to taking this patch**: Low
* **Why is the change risky/not risky? (and alternatives if risky)**: It's a small patch that matches code elsewhere (ensures the upper bits of an int32 register are zero).
* **String changes made/needed**: N/A
* **Is Android affected?**: Yes

---

**Comment 11 — aryx.bugmail@gmx-topmail.de — 2025-02-13T20:59:29Z**

https://hg.mozilla.org/mozilla-central/rev/17a8382a336f

---

**Comment 12 — dmeehan@mozilla.com — 2025-02-14T17:36:45Z**

Comment on attachment 9465096
Bug 1946004 - Widen i32 return values in GenerateJitEntry. r?rhunt!

Approved for 136.0b7

---

**Comment 13 — pulsebot@bmo.tld — 2025-02-14T17:37:27Z**

https://hg.mozilla.org/releases/mozilla-beta/rev/d3ab432a76b8

---

**Comment 14 — dmeehan@mozilla.com — 2025-02-18T13:10:54Z**

Comment on attachment 9465096
Bug 1946004 - Widen i32 return values in GenerateJitEntry. r?rhunt!

Approved for 128.8esr

---

**Comment 15 — pulsebot@bmo.tld — 2025-02-18T13:11:45Z**

https://hg.mozilla.org/releases/mozilla-esr128/rev/20634f349813

---

**Comment 16 — dmeehan@mozilla.com — 2025-02-18T14:04:51Z**

Comment on attachment 9465096
Bug 1946004 - Widen i32 return values in GenerateJitEntry. r?rhunt!

Approved for 115.21esr

---

**Comment 17 — pulsebot@bmo.tld — 2025-02-18T14:05:21Z**

https://hg.mozilla.org/releases/mozilla-esr115/rev/60f7dc179043

---

**Comment 18 — dveditz@mozilla.com — 2025-03-03T15:05:35Z**

Created attachment 9469436
advisory.txt

---

**Comment 19 — release-mgmt-account-bot@mozilla.tld — 2025-04-15T12:01:07Z**

2 months ago, tjr placed a reminder on the bug using the whiteboard tag `[reminder-test 2025-04-15]` .

jandem, please refer to the original comment to better understand the reason for the reminder.

---

**Comment 20 — pulsebot@bmo.tld — 2025-04-17T21:41:42Z**

Pushed by jdemooij@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/02887da73ad0
Add test and comment. r=rhunt

---

**Comment 21 — aryx.bugmail@gmx-topmail.de — 2025-04-18T08:42:26Z**

https://hg.mozilla.org/mozilla-central/rev/02887da73ad0
