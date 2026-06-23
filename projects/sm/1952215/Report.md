# Crash [@ ??] through [@ js::wasm::Instance::callExport] with tiering

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1952215
Component: JavaScript: WebAssembly
Bounty: (unknown)
Date: 2025-03-06T13:12:56Z
Keywords: crash, csectype-wildptr, regression, sec-high, testcase
See Also:
- https://bugzilla.mozilla.org/show_bug.cgi?id=1952393

The attached testcase crashes on mozilla-central revision 20250305-e3f4fc6b9502 (build with fuzzing-debug, run with --no-threads --differential-testing --setpref=wasm_memory_control=true --setpref=wasm_js_string_builtins=true). 

Backtrace:

```
    ==3118880==ERROR: UndefinedBehaviorSanitizer: SEGV on unknown address 0x000000000170 (pc 0x10e9ec658010 bp 0x7ffe9f378340 sp 0x7ffe9f3782e8 T3118880)
    ==3118880==The signal is caused by a WRITE memory access.
    ==3118880==Hint: address points to the zero page.
        #0 0x10e9ec658010  (<unknown module>)
        #1 0x55a0d0c6d5be in js::wasm::Instance::callExport(JSContext*, unsigned int, JS::CallArgs const&, js::wasm::CoercionLevel) /js/src/wasm/WasmInstance.cpp:3790:10
        #2 0x55a0d0c6c6e3 in WasmCall(JSContext*, unsigned int, JS::Value*) /js/src/wasm/WasmInstance.cpp:3576:19
        #3 0x55a0cf4c6cd4 in CallJSNative(JSContext*, bool (*)(JSContext*, unsigned int, JS::Value*), js::CallReason, JS::CallArgs const&) /js/src/vm/Interpreter.cpp:493:13
        #4 0x55a0cf4c63df in js::InternalCallOrConstruct(JSContext*, JS::CallArgs const&, js::MaybeConstruct, js::CallReason) /js/src/vm/Interpreter.cpp:589:12
        #5 0x55a0cf4c797b in js::Call(JSContext*, JS::Handle<JS::Value>, JS::Handle<JS::Value>, js::AnyInvokeArgs const&, JS::MutableHandle<JS::Value>, js::CallReason) /js/src/vm/Interpreter.cpp:688:8
        #6 0x55a0cf4e5f41 in js::SpreadCallOperation(JSContext*, JS::Handle<JSScript*>, unsigned char*, JS::Handle<JS::Value>, JS::Handle<JS::Value>, JS::Handle<JS::Value>, JS::Handle<JS::Value>, JS::MutableHandle<JS::Value>) /js/src/vm/Interpreter.cpp:5006:12
        #7 0x55a0cf4d92a6 in js::Interpret(JSContext*, js::RunState&) /js/src/vm/Interpreter.cpp:3193:12
        #8 0x55a0cf4c5931 in js::RunScript(JSContext*, js::RunState&) /js/src/vm/Interpreter.cpp:463:13
        #9 0x55a0cf4c8f30 in js::ExecuteKernel(JSContext*, JS::Handle<JSScript*>, JS::Handle<JSObject*>, js::AbstractFramePtr, JS::MutableHandle<JS::Value>) /js/src/vm/Interpreter.cpp:854:13
        #10 0x55a0cf4c951e in js::Execute(JSContext*, JS::Handle<JSScript*>, JS::Handle<JSObject*>, JS::MutableHandle<JS::Value>) /js/src/vm/Interpreter.cpp:887:10
        #11 0x55a0cf63bdf1 in ExecuteScript(JSContext*, JS::Handle<JSObject*>, JS::Handle<JSScript*>, JS::MutableHandle<JS::Value>) /js/src/vm/CompilationAndEvaluation.cpp:601:10
        #12 0x55a0cf63bbff in JS_ExecuteScript(JSContext*, JS::Handle<JSScript*>, JS::MutableHandle<JS::Value>) /js/src/vm/CompilationAndEvaluation.cpp:618:10
        #13 0x55a0cf352647 in Evaluate(JSContext*, unsigned int, JS::Value*) /js/src/shell/js.cpp:3003:19
        #14 0x55a0cf4c6cd4 in CallJSNative(JSContext*, bool (*)(JSContext*, unsigned int, JS::Value*), js::CallReason, JS::CallArgs const&) /js/src/vm/Interpreter.cpp:493:13
        [...]
        #27 0x55a0cf324c9d in main /js/src/shell/js.cpp:12413:12
    
    ==3118880==Register values:
    rax = 0x0000000000000170  rbx = 0x000010e9ec639090  rcx = 0x000055a0d26e0a00  rdx = 0x0000000000000010  
    rdi = 0x00007ffe9f3787a8  rsi = 0x000055a0d3d59b50  rbp = 0x00007ffe9f378340  rsp = 0x00007ffe9f3782e8  
     r8 = 0x0000000000000000   r9 = 0x00007ffe9f378470  r10 = 0x00007ffe9f3787a8  r11 = 0x00007ffe9f3786f0  
    r12 = 0x00007ffe9f378358  r13 = 0x000055a0d3d59b50  r14 = 0x000055a0d3d59b50  r15 = 0x0000000000000000  
    UndefinedBehaviorSanitizer can not provide additional info.
    SUMMARY: UndefinedBehaviorSanitizer: SEGV (<unknown module>) 
    ==3118880==ABORTING
```


Marking s-s until investigated because this looks potentially dangerous.

---

**Comment 1 — choller@mozilla.com — 2025-03-06T13:13:01Z**

Created attachment 9470249
Detailed Crash Information

---

**Comment 2 — choller@mozilla.com — 2025-03-06T13:13:03Z**

Created attachment 9470250
Testcase

---

**Comment 3 — jpages@mozilla.com — 2025-03-07T00:19:36Z**

After a git bisect session, it looks like this is a regression caused by my stackmaps patch: bugzilla.mozilla.org/show_bug.cgi?id=1861078

I'll look into it

---

**Comment 4 — jpages@mozilla.com — 2025-03-10T21:16:40Z**

Created attachment 9470928
Bug 1952215 - wasm: Fix calleePtr for lazy stubs.

---

**Comment 5 — jpages@mozilla.com — 2025-03-10T21:24:29Z**

The attached patch fixes the issue, it also fixes this related bug submitted by an external contributor: https://bugzilla.mozilla.org/show_bug.cgi?id=1952393

---

**Comment 6 — jpages@mozilla.com — 2025-03-10T21:28:20Z**

The regression is recent and was only present in nightly, it requires to flip a flag to enable javascript.options.wasm_lazy_tiering

---

**Comment 7 — release-mgmt-account-bot@mozilla.tld — 2025-03-10T21:42:31Z**

Set release status flags based on info from the regressing bug 1861078

---

**Comment 8 — rhunt@eqrion.net — 2025-03-12T12:26:26Z**

Bug 1861078 is definitely the regressor here. However I think this doesn't require a pref flip because lazy tiering is enabled for wasm-gc content (javascript.options.wasm_lazy_tiering_for_gc=true).

This bug is pretty severe because we will generate a wasm entry stub that calls the wrong code pointer. The code pointer we use will always be in the range of code we generated for the module, but not necessarily the right function or prologue. I don't know if there are any other mitigating factors here, so we should try to land this fix quickly while it's just in nightly.

---

**Comment 9 — jpages@mozilla.com — 2025-03-12T15:19:15Z**

For the associated bug https://bugzilla.mozilla.org/show_bug.cgi?id=1952393, it required the flag javascript.options.wasm_lazy_tiering to trigger the bug (it works by default on nightly). This may be because the bug is in `createManyLazyEntryStubs`.

I agree that this bug is pretty bad though, I'll land the fix soon.

---

**Comment 10 — pulsebot@bmo.tld — 2025-03-12T18:08:31Z**

Pushed by jpages@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/b37cddf0a3b3
wasm: Fix calleePtr for lazy stubs. r=rhunt

---

**Comment 11 — aryx.bugmail@gmx-topmail.de — 2025-03-13T10:44:05Z**

https://hg.mozilla.org/mozilla-central/rev/b37cddf0a3b3

---

**Comment 12 — bugmon@mozilla.com — 2025-09-05T08:15:44Z**

Bugmon was unable reproduce this issue.
Removing bugmon keyword as no further action possible.  Please review the bug and re-add the keyword for further analysis.
