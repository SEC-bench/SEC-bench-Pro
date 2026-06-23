# Check for unsigned overflow in inline array allocation

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1882751
Component: JavaScript: WebAssembly
Bounty: (unknown)
Date: 2024-02-29T12:09:50Z
Keywords: csectype-intoverflow, regression, reporter-external, sec-high
See Also:
- https://bugzilla.mozilla.org/show_bug.cgi?id=1880719

Created attachment 9388363
poc.js

## Reproduce
1. Clone the Firefox mirror from https://github.com/mozilla/gecko-dev
2. Run build command ` mkdir fuzzbuild_OPT.OBJ && cd fuzzbuild_OPT.OBJ && ../configure --enable-address-sanitizer --disable-jemalloc --enable-debug --enable-optimize --disable-shared-js --enable-application=js --enable-gczeal && make -j64 ` in the js/src directory of the firefox checkout
3. Run poc: `js/src/fuzzbuild_OPT.OBJ/dist/bin/js --wasm-compiler=baseline poc.js`

- my test spidermonkey commit hash
```
commit da2c1e64cc7aa8718fb92eb602136da5d505d664 (HEAD -> master, origin/master, origin/HEAD)
Author: Robin Steuber <bytesized@mozilla.com>
Date:   Thu Feb 29 08:23:07 2024 +0000

    Bug 1882322 - Prevent macOS channel frameworks from being in precomplete file r=jcristau

    Differential Revision: https://phabricator.services.mozilla.com/D203054
```

## Asan log
```
/home/test/gecko-dev/js/src/fuzzbuild_OPT.OBJ/dist/bin/js --wasm-compiler=baseline poc.js
AddressSanitizer:DEADLYSIGNAL
=================================================================
==2692978==ERROR: AddressSanitizer: SEGV on unknown address 0x7f101e600954 (pc 0x2b2979b666b9 bp 0x7ffd0dc9d730 sp 0x7ffd0dc9d6c0 T0)
==2692978==The signal is caused by a WRITE memory access.
    #0 0x2b2979b666b9  ([anon:js-executable-memory]+0x6b9)
    #1 0x2b2979b67cbe  ([anon:js-executable-memory]+0x1cbe)
    #2 0x558186a8444d  (/home/test/gecko-dev/js/src/fuzzbuild_OPT.OBJ/dist/bin/js+0x65c144d) (BuildId: d1d71326c86c49f03a89ce7878424135)
    #3 0x558186abb230  (/home/test/gecko-dev/js/src/fuzzbuild_OPT.OBJ/dist/bin/js+0x65f8230) (BuildId: d1d71326c86c49f03a89ce7878424135)
    #4 0x5581833bc01e  (/home/test/gecko-dev/js/src/fuzzbuild_OPT.OBJ/dist/bin/js+0x2ef901e) (BuildId: d1d71326c86c49f03a89ce7878424135)
    #5 0x55818334c8b8  (/home/test/gecko-dev/js/src/fuzzbuild_OPT.OBJ/dist/bin/js+0x2e898b8) (BuildId: d1d71326c86c49f03a89ce7878424135)
    #6 0x55818337970a  (/home/test/gecko-dev/js/src/fuzzbuild_OPT.OBJ/dist/bin/js+0x2eb670a) (BuildId: d1d71326c86c49f03a89ce7878424135)
    #7 0x55818334b6bc  (/home/test/gecko-dev/js/src/fuzzbuild_OPT.OBJ/dist/bin/js+0x2e886bc) (BuildId: d1d71326c86c49f03a89ce7878424135)
    #8 0x55818334a7d6  (/home/test/gecko-dev/js/src/fuzzbuild_OPT.OBJ/dist/bin/js+0x2e877d6) (BuildId: d1d71326c86c49f03a89ce7878424135)
    #9 0x558183353584  (/home/test/gecko-dev/js/src/fuzzbuild_OPT.OBJ/dist/bin/js+0x2e90584) (BuildId: d1d71326c86c49f03a89ce7878424135)
    #10 0x55818335429e  (/home/test/gecko-dev/js/src/fuzzbuild_OPT.OBJ/dist/bin/js+0x2e9129e) (BuildId: d1d71326c86c49f03a89ce7878424135)
    #11 0x5581837b2f9b  (/home/test/gecko-dev/js/src/fuzzbuild_OPT.OBJ/dist/bin/js+0x32eff9b) (BuildId: d1d71326c86c49f03a89ce7878424135)
    #12 0x5581837b359d  (/home/test/gecko-dev/js/src/fuzzbuild_OPT.OBJ/dist/bin/js+0x32f059d) (BuildId: d1d71326c86c49f03a89ce7878424135)
    #13 0x55818316c6a3  (/home/test/gecko-dev/js/src/fuzzbuild_OPT.OBJ/dist/bin/js+0x2ca96a3) (BuildId: d1d71326c86c49f03a89ce7878424135)
    #14 0x55818316a3d0  (/home/test/gecko-dev/js/src/fuzzbuild_OPT.OBJ/dist/bin/js+0x2ca73d0) (BuildId: d1d71326c86c49f03a89ce7878424135)
    #15 0x5581830b61af  (/home/test/gecko-dev/js/src/fuzzbuild_OPT.OBJ/dist/bin/js+0x2bf31af) (BuildId: d1d71326c86c49f03a89ce7878424135)
    #16 0x5581830a61f8  (/home/test/gecko-dev/js/src/fuzzbuild_OPT.OBJ/dist/bin/js+0x2be31f8) (BuildId: d1d71326c86c49f03a89ce7878424135)
    #17 0x7f0e1ee29d8f  (/lib/x86_64-linux-gnu/libc.so.6+0x29d8f) (BuildId: c289da5071a3399de893d2af81d6a30c62646e1e)

AddressSanitizer can not provide additional info.
SUMMARY: AddressSanitizer: SEGV ([anon:js-executable-memory]+0x6b9)
==2692978==ABORTING
```

---

**Comment 1 — eternalsakuraalpha@gmail.com — 2024-02-29T12:24:08Z**

Created attachment 9388366
poc1.js

---

**Comment 2 — eternalsakuraalpha@gmail.com — 2024-02-29T12:25:02Z**

I can get another poc. (see poc1.js)

run cmd: `/home/test/gecko-dev/js/src/fuzzbuild_OPT.OBJ/dist/bin/js poc.js`

```
/home/test/gecko-dev/js/src/fuzzbuild_OPT.OBJ/dist/bin/js poc1.js    
AddressSanitizer:DEADLYSIGNAL
=================================================================
==2899598==ERROR: AddressSanitizer: SEGV on unknown address 0x7f8a8ba00000 (pc 0x7f8a0924f463 bp 0x7ffd361fdb70 sp 0x7ffd361fdb40 T0)
==2899598==The signal is caused by a WRITE memory access.
    #0 0x7f8a0924f463  ([anon:js-executable-memory]+0x463)
    #1 0x7f8a0924f8de  ([anon:js-executable-memory]+0x8de)
    #2 0x560d68321a51  (/home/test/gecko-dev/js/src/fuzzbuild_OPT.OBJ/dist/bin/js+0x6e2ca51) (BuildId: d2fe0694d1d383bef13b7ae9e8fd74c9)
    #3 0x560d683690f9  (/home/test/gecko-dev/js/src/fuzzbuild_OPT.OBJ/dist/bin/js+0x6e740f9) (BuildId: d2fe0694d1d383bef13b7ae9e8fd74c9)
    #4 0x560d6442a79a  (/home/test/gecko-dev/js/src/fuzzbuild_OPT.OBJ/dist/bin/js+0x2f3579a) (BuildId: d2fe0694d1d383bef13b7ae9e8fd74c9)
    #5 0x560d64428bc2  (/home/test/gecko-dev/js/src/fuzzbuild_OPT.OBJ/dist/bin/js+0x2f33bc2) (BuildId: d2fe0694d1d383bef13b7ae9e8fd74c9)
    #6 0x560d64460ebb  (/home/test/gecko-dev/js/src/fuzzbuild_OPT.OBJ/dist/bin/js+0x2f6bebb) (BuildId: d2fe0694d1d383bef13b7ae9e8fd74c9)
    #7 0x560d64427291  (/home/test/gecko-dev/js/src/fuzzbuild_OPT.OBJ/dist/bin/js+0x2f32291) (BuildId: d2fe0694d1d383bef13b7ae9e8fd74c9)
    #8 0x560d64426667  (/home/test/gecko-dev/js/src/fuzzbuild_OPT.OBJ/dist/bin/js+0x2f31667) (BuildId: d2fe0694d1d383bef13b7ae9e8fd74c9)
    #9 0x560d64431f5d  (/home/test/gecko-dev/js/src/fuzzbuild_OPT.OBJ/dist/bin/js+0x2f3cf5d) (BuildId: d2fe0694d1d383bef13b7ae9e8fd74c9)
    #10 0x560d644331dd  (/home/test/gecko-dev/js/src/fuzzbuild_OPT.OBJ/dist/bin/js+0x2f3e1dd) (BuildId: d2fe0694d1d383bef13b7ae9e8fd74c9)
    #11 0x560d6493cc27  (/home/test/gecko-dev/js/src/fuzzbuild_OPT.OBJ/dist/bin/js+0x3447c27) (BuildId: d2fe0694d1d383bef13b7ae9e8fd74c9)
    #12 0x560d6493d317  (/home/test/gecko-dev/js/src/fuzzbuild_OPT.OBJ/dist/bin/js+0x3448317) (BuildId: d2fe0694d1d383bef13b7ae9e8fd74c9)
    #13 0x560d64280f29  (/home/test/gecko-dev/js/src/fuzzbuild_OPT.OBJ/dist/bin/js+0x2d8bf29) (BuildId: d2fe0694d1d383bef13b7ae9e8fd74c9)
    #14 0x560d6427e076  (/home/test/gecko-dev/js/src/fuzzbuild_OPT.OBJ/dist/bin/js+0x2d89076) (BuildId: d2fe0694d1d383bef13b7ae9e8fd74c9)
    #15 0x560d6413032a  (/home/test/gecko-dev/js/src/fuzzbuild_OPT.OBJ/dist/bin/js+0x2c3b32a) (BuildId: d2fe0694d1d383bef13b7ae9e8fd74c9)
    #16 0x560d6411c7d8  (/home/test/gecko-dev/js/src/fuzzbuild_OPT.OBJ/dist/bin/js+0x2c277d8) (BuildId: d2fe0694d1d383bef13b7ae9e8fd74c9)
    #17 0x7f8a8be29d8f  (/lib/x86_64-linux-gnu/libc.so.6+0x29d8f) (BuildId: c289da5071a3399de893d2af81d6a30c62646e1e)

AddressSanitizer can not provide additional info.
SUMMARY: AddressSanitizer: SEGV ([anon:js-executable-memory]+0x463) 
==2899598==ABORTING
```

---

**Comment 3 — eternalsakuraalpha@gmail.com — 2024-02-29T13:36:06Z**

Please see poc1.js, which seems better.

---

**Comment 4 — continuation@gmail.com — 2024-02-29T18:33:45Z**

These stacks would be more helpful if you had the llvm-symbolizer enabled to get actual path information. I think you can do this by having the environment variable LLVM_SYMBOLIZER set to point to it, or manually run it on the result.

---

**Comment 5 — rhunt@eqrion.net — 2024-02-29T20:35:45Z**

I attempted to reproduce this on my Mac (ARM64) and was not able to for either of the POC. I will attempt on my x64 linux box after I get back from PTO on Monday.

---

**Comment 6 — eternalsakuraalpha@gmail.com — 2024-02-29T22:47:00Z**

- asan log with symbol
```
/home/test/gecko-dev/js/src/fuzzbuild_OPT.OBJ/dist/bin/js poc1.js
AddressSanitizer:DEADLYSIGNAL
=================================================================
==3596726==ERROR: AddressSanitizer: SEGV on unknown address 0x20a46fd00000 (pc 0x1778c35e1463 bp 0x7ffc7dd13c70 sp 0x7ffc7dd13c40 T0)
==3596726==The signal is caused by a WRITE memory access.
/home/test/.mozbuild/clang/bin/llvm-symbolizer: error: '[anon:js-executable-memory]': No such file or directory
    #0 0x1778c35e1463  ([anon:js-executable-memory]+0x463)
    #1 0x1778c35e18de  ([anon:js-executable-memory]+0x8de)
    #2 0x55fc56298a51 in js::wasm::Instance::callExport(JSContext*, unsigned int, JS::CallArgs, js::wasm::CoercionLevel) /home/test/gecko-dev/js/src/wasm/WasmInstance.cpp:3199:10
    #3 0x55fc562e00f9 in WasmCall(JSContext*, unsigned int, JS::Value*) /home/test/gecko-dev/js/src/wasm/WasmJS.cpp:1842:19
    #4 0x55fc523a179a in CallJSNative(JSContext*, bool (*)(JSContext*, unsigned int, JS::Value*), js::CallReason, JS::CallArgs const&) /home/test/gecko-dev/js/src/vm/Interpreter.cpp:480:13
    #5 0x55fc5239fbc2 in js::InternalCallOrConstruct(JSContext*, JS::CallArgs const&, js::MaybeConstruct, js::CallReason) /home/test/gecko-dev/js/src/vm/Interpreter.cpp:574:12
    #6 0x55fc523d7ebb in js::CallFromStack(JSContext*, JS::CallArgs const&, js::CallReason) /home/test/gecko-dev/js/src/vm/Interpreter.cpp:646:10
    #7 0x55fc523d7ebb in js::Interpret(JSContext*, js::RunState&) /home/test/gecko-dev/js/src/vm/Interpreter.cpp:3061:16
    #8 0x55fc5239e291 in MaybeEnterInterpreterTrampoline(JSContext*, js::RunState&) /home/test/gecko-dev/js/src/vm/Interpreter.cpp:394:10
    #9 0x55fc5239d667 in js::RunScript(JSContext*, js::RunState&) /home/test/gecko-dev/js/src/vm/Interpreter.cpp:452:13
    #10 0x55fc523a8f5d in js::ExecuteKernel(JSContext*, JS::Handle<JSScript*>, JS::Handle<JSObject*>, js::AbstractFramePtr, JS::MutableHandle<JS::Value>) /home/test/gecko-dev/js/src/vm/Interpreter.cpp:839:13
    #11 0x55fc523aa1dd in js::Execute(JSContext*, JS::Handle<JSScript*>, JS::Handle<JSObject*>, JS::MutableHandle<JS::Value>) /home/test/gecko-dev/js/src/vm/Interpreter.cpp:871:10
    #12 0x55fc528b3c27 in ExecuteScript(JSContext*, JS::Handle<JSObject*>, JS::Handle<JSScript*>, JS::MutableHandle<JS::Value>) /home/test/gecko-dev/js/src/vm/CompilationAndEvaluation.cpp:494:10
    #13 0x55fc528b4317 in JS_ExecuteScript(JSContext*, JS::Handle<JSScript*>) /home/test/gecko-dev/js/src/vm/CompilationAndEvaluation.cpp:518:10
    #14 0x55fc521f7f29 in RunFile(JSContext*, char const*, _IO_FILE*, CompileUtf8, bool, bool) /home/test/gecko-dev/js/src/shell/js.cpp:1200:10
    #15 0x55fc521f5076 in Process(JSContext*, char const*, bool, FileKind) /home/test/gecko-dev/js/src/shell/js.cpp:1780:14
    #16 0x55fc520a732a in ProcessArgs(JSContext*, js::cli::OptionParser*) /home/test/gecko-dev/js/src/shell/js.cpp:10991:10
    #17 0x55fc520a732a in Shell(JSContext*, js::cli::OptionParser*) /home/test/gecko-dev/js/src/shell/js.cpp:11251:12
    #18 0x55fc520937d8 in main /home/test/gecko-dev/js/src/shell/js.cpp:11759:12
    #19 0x7f44fb229d8f in __libc_start_call_main csu/../sysdeps/nptl/libc_start_call_main.h:58:16

AddressSanitizer can not provide additional info.
SUMMARY: AddressSanitizer: SEGV ([anon:js-executable-memory]+0x463) 
==3596726==ABORTING
```
- operation system
```
uname -a                                                                                             
Linux test 5.19.0-32-generic #33~22.04.1-Ubuntu SMP PREEMPT_DYNAMIC Mon Jan 30 17:03:34 UTC 2 x86_64 x86_64 x86_64 GNU/Linux
```

---

**Comment 7 — eternalsakuraalpha@gmail.com — 2024-03-01T01:03:51Z**

I can reproduce it by: https://github.com/MozillaSecurity/autobisect.

```
/home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-e094286867e7/dist/bin/js poc1.js
AddressSanitizer:DEADLYSIGNAL
=================================================================
==3686742==ERROR: AddressSanitizer: SEGV on unknown address 0x20c0e1900000 (pc 0x177ccde83463 bp 0x7ffe2c155ef0 sp 0x7ffe2c155ec0 T0)
==3686742==The signal is caused by a WRITE memory access.
/home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-e094286867e7/dist/bin/llvm-symbolizer: error: '[anon:js-executable-memory]': No such file or directory
    #0 0x177ccde83463  ([anon:js-executable-memory]+0x463)
    #1 0x177ccde838de  ([anon:js-executable-memory]+0x8de)
    #2 0x55f05f2eadf9 in js::wasm::Instance::callExport(JSContext*, unsigned int, JS::CallArgs, js::wasm::CoercionLevel) /builds/worker/checkouts/gecko/js/src/wasm/WasmInstance.cpp:3199:10
    #3 0x55f05f32a9ae in WasmCall(JSContext*, unsigned int, JS::Value*) /builds/worker/checkouts/gecko/js/src/wasm/WasmJS.cpp:1842:19
    #4 0x55f05bb8eb5a in CallJSNative(JSContext*, bool (*)(JSContext*, unsigned int, JS::Value*), js::CallReason, JS::CallArgs const&) /builds/worker/checkouts/gecko/js/src/vm/Interpreter.cpp:480:13
    #5 0x55f05bb8d39d in js::InternalCallOrConstruct(JSContext*, JS::CallArgs const&, js::MaybeConstruct, js::CallReason) /builds/worker/checkouts/gecko/js/src/vm/Interpreter.cpp:574:12
    #6 0x55f05bbbbbe5 in js::CallFromStack(JSContext*, JS::CallArgs const&, js::CallReason) /builds/worker/checkouts/gecko/js/src/vm/Interpreter.cpp:646:10
    #7 0x55f05bbbbbe5 in js::Interpret(JSContext*, js::RunState&) /builds/worker/checkouts/gecko/js/src/vm/Interpreter.cpp:3061:16
    #8 0x55f05bb8c530 in MaybeEnterInterpreterTrampoline(JSContext*, js::RunState&) /builds/worker/checkouts/gecko/js/src/vm/Interpreter.cpp:394:10
    #9 0x55f05bb8b77c in js::RunScript(JSContext*, js::RunState&) /builds/worker/checkouts/gecko/js/src/vm/Interpreter.cpp:452:13
    #10 0x55f05bb9472b in js::ExecuteKernel(JSContext*, JS::Handle<JSScript*>, JS::Handle<JSObject*>, js::AbstractFramePtr, JS::MutableHandle<JS::Value>) /builds/worker/checkouts/gecko/js/src/vm/Interpreter.cpp:839:13
    #11 0x55f05bb9549e in js::Execute(JSContext*, JS::Handle<JSScript*>, JS::Handle<JSObject*>, JS::MutableHandle<JS::Value>) /builds/worker/checkouts/gecko/js/src/vm/Interpreter.cpp:871:10
    #12 0x55f05bffd33b in ExecuteScript(JSContext*, JS::Handle<JSObject*>, JS::Handle<JSScript*>, JS::MutableHandle<JS::Value>) /builds/worker/checkouts/gecko/js/src/vm/CompilationAndEvaluation.cpp:494:10
    #13 0x55f05bffd8e5 in JS_ExecuteScript(JSContext*, JS::Handle<JSScript*>) /builds/worker/checkouts/gecko/js/src/vm/CompilationAndEvaluation.cpp:518:10
    #14 0x55f05b81fa8f in RunFile(JSContext*, char const*, _IO_FILE*, CompileUtf8, bool, bool) /builds/worker/checkouts/gecko/js/src/shell/js.cpp:1200:10
    #15 0x55f05b81dd76 in Process(JSContext*, char const*, bool, FileKind) /builds/worker/checkouts/gecko/js/src/shell/js.cpp
    #16 0x55f05b71306a in ProcessArgs(JSContext*, js::cli::OptionParser*) /builds/worker/checkouts/gecko/js/src/shell/js.cpp:10991:10
    #17 0x55f05b71306a in Shell(JSContext*, js::cli::OptionParser*) /builds/worker/checkouts/gecko/js/src/shell/js.cpp:11250:12
    #18 0x55f05b702aae in main /builds/worker/checkouts/gecko/js/src/shell/js.cpp:11758:12
    #19 0x7f1496429d8f in __libc_start_call_main csu/../sysdeps/nptl/libc_start_call_main.h:58:16

AddressSanitizer can not provide additional info.
SUMMARY: AddressSanitizer: SEGV ([anon:js-executable-memory]+0x463) 
==3686742==ABORTING
```

---

**Comment 8 — eternalsakuraalpha@gmail.com — 2024-03-04T02:30:53Z**

I ran bisect, hope this helps with your investigation. I'm not sure if it has an impact on bisect because of the wasm functionality and features turned on, but it looks like this at least introduces a month.
Please take a look.
```
python3 -m autobisect js poc1.js --asan --debug
[2024-03-04 10:08:41] Begin bisection...
[2024-03-04 10:08:41] > Start: 30004166d9f2cc3399da68e8762c35b1b886c0dc (20231206051837)
[2024-03-04 10:08:41] > End: 62056fe89aac9d2f369746854f0e3a55ad7153d0 (20240303213416)
[2024-03-04 10:08:41] Attempting to verify boundaries...
[2024-03-04 10:08:41] Testing build 30004166d9f2cc3399da68e8762c35b1b886c0dc (20231206051837)
[2024-03-04 10:08:42] > Downloading: https://firefox-ci-tc.services.mozilla.com/api/queue/v1/task/DxDXLRQiRW6IG3FxB5QkfQ/artifacts/public/build/target.jsshell.zip (313.42MiB total)
[2024-03-04 10:09:12] .. still downloading (43.2%, 4.73MB/s)
[2024-03-04 10:09:42] .. still downloading (87.2%, 4.77MB/s)
[2024-03-04 10:09:51] .. downloaded (4.77MB/s)
[2024-03-04 10:09:51] .. extracting
[2024-03-04 10:09:57] Extracted into /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-30004166d9f2
[2024-03-04 10:09:59] > Verifying build...
[2024-03-04 10:09:59] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-30004166d9f2/dist/bin/js -e "quit()"
[2024-03-04 10:09:59] > Launching build with testcase...
[2024-03-04 10:09:59] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-30004166d9f2/dist/bin/js poc1.js
[2024-03-04 10:09:59] > Failed to reproduce issue!
[2024-03-04 10:10:00] Testing build 62056fe89aac9d2f369746854f0e3a55ad7153d0 (20240303213416)
[2024-03-04 10:10:00] > Downloading: https://firefox-ci-tc.services.mozilla.com/api/queue/v1/task/GVd462QVRs-mQBvkU-IP0A/artifacts/public/build/target.jsshell.zip (319.66MiB total)
[2024-03-04 10:10:30] .. still downloading (42.9%, 4.79MB/s)
[2024-03-04 10:11:00] .. still downloading (86.0%, 4.80MB/s)
[2024-03-04 10:11:10] .. downloaded (4.80MB/s)
[2024-03-04 10:11:10] .. extracting
[2024-03-04 10:11:16] Extracted into /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-62056fe89aac
[2024-03-04 10:11:19] > Verifying build...
[2024-03-04 10:11:19] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-62056fe89aac/dist/bin/js -e "quit()"
[2024-03-04 10:11:19] > Launching build with testcase...
[2024-03-04 10:11:19] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-62056fe89aac/dist/bin/js poc1.js
[2024-03-04 10:11:20] Verified supplied boundaries!
[2024-03-04 10:11:20] Attempting to reduce bisection range using taskcluster binaries
[2024-03-04 10:11:20] Enumerating daily builds: 2023-12-07 05:18:37+00:00 - 2024-03-02 21:34:16+00:00
[2024-03-04 10:11:22] Testing build b6393478fdf670fcce10fd4334c2601561eaea5d (20240119093321)
[2024-03-04 10:11:23] > Downloading: https://firefox-ci-tc.services.mozilla.com/api/queue/v1/task/PqZLh-aSTs6GI6__8qylGw/artifacts/public/build/target.jsshell.zip (311.37MiB total)
[2024-03-04 10:11:52] .. still downloading (43.6%, 4.74MB/s)
[2024-03-04 10:12:22] .. still downloading (87.8%, 4.77MB/s)
[2024-03-04 10:12:30] .. downloaded (4.77MB/s)
[2024-03-04 10:12:30] .. extracting
[2024-03-04 10:12:37] Extracted into /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-b6393478fdf6
[2024-03-04 10:12:39] > Verifying build...
[2024-03-04 10:12:39] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-b6393478fdf6/dist/bin/js -e "quit()"
[2024-03-04 10:12:39] > Launching build with testcase...
[2024-03-04 10:12:39] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-b6393478fdf6/dist/bin/js poc1.js
[2024-03-04 10:12:39] > Failed to reproduce issue!
[2024-03-04 10:12:42] Testing build a4ac5f36f609ad4a87fb047393aab7e4445270b4 (20240210094249)
[2024-03-04 10:12:43] > Downloading: https://firefox-ci-tc.services.mozilla.com/api/queue/v1/task/P52_IbQGRdOxqEiITy0YuA/artifacts/public/build/target.jsshell.zip (318.75MiB total)
[2024-03-04 10:13:12] .. still downloading (42.4%, 4.73MB/s)
[2024-03-04 10:13:42] .. still downloading (85.6%, 4.77MB/s)
[2024-03-04 10:13:53] .. downloaded (4.76MB/s)
[2024-03-04 10:13:53] .. extracting
[2024-03-04 10:13:59] Extracted into /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-a4ac5f36f609
[2024-03-04 10:14:01] > Verifying build...
[2024-03-04 10:14:01] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-a4ac5f36f609/dist/bin/js -e "quit()"
[2024-03-04 10:14:01] > Launching build with testcase...
[2024-03-04 10:14:01] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-a4ac5f36f609/dist/bin/js poc1.js
[2024-03-04 10:14:04] Testing build 49f49182fc503c7ebfff0af484b8f21c9a6ac29f (20240130045011)
[2024-03-04 10:14:05] > Downloading: https://firefox-ci-tc.services.mozilla.com/api/queue/v1/task/Jyarx8kLS5W2Ght2cOX0qg/artifacts/public/build/target.jsshell.zip (315.98MiB total)
[2024-03-04 10:15:14] .. downloaded (4.78MB/s)
[2024-03-04 10:15:14] .. extracting
[2024-03-04 10:15:20] Extracted into /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-49f49182fc50
[2024-03-04 10:15:23] > Verifying build...
[2024-03-04 10:15:23] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-49f49182fc50/dist/bin/js -e "quit()"
[2024-03-04 10:15:23] > Launching build with testcase...
[2024-03-04 10:15:23] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-49f49182fc50/dist/bin/js poc1.js
[2024-03-04 10:15:23] > Failed to reproduce issue!
[2024-03-04 10:15:25] Testing build 9ca12d444230411e2168420a584a7f95e90c1f97 (20240205094658)
[2024-03-04 10:15:26] > Downloading: https://firefox-ci-tc.services.mozilla.com/api/queue/v1/task/TLUmmhlASF6tQpsTJfZcmg/artifacts/public/build/target.jsshell.zip (316.28MiB total)
[2024-03-04 10:15:56] .. still downloading (43.1%, 4.75MB/s)
[2024-03-04 10:16:26] .. still downloading (86.6%, 4.78MB/s)
[2024-03-04 10:16:35] .. downloaded (4.78MB/s)
[2024-03-04 10:16:35] .. extracting
[2024-03-04 10:16:41] Extracted into /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-9ca12d444230
[2024-03-04 10:16:44] > Verifying build...
[2024-03-04 10:16:44] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-9ca12d444230/dist/bin/js -e "quit()"
[2024-03-04 10:16:44] > Launching build with testcase...
[2024-03-04 10:16:44] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-9ca12d444230/dist/bin/js poc1.js
[2024-03-04 10:16:45] > Failed to reproduce issue!
[2024-03-04 10:16:47] Testing build a18d76b700d3e57d1a0ad5ab37fa7d3fd5d3a79f (20240208045950)
[2024-03-04 10:16:48] > Downloading: https://firefox-ci-tc.services.mozilla.com/api/queue/v1/task/Ql33kO6nSkiXto9WlDME6A/artifacts/public/build/target.jsshell.zip (319.67MiB total)
[2024-03-04 10:17:17] .. still downloading (42.5%, 4.74MB/s)
[2024-03-04 10:17:47] .. still downloading (85.8%, 4.79MB/s)
[2024-03-04 10:17:57] .. downloaded (4.79MB/s)
[2024-03-04 10:17:57] .. extracting
[2024-03-04 10:18:04] Extracted into /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-a18d76b700d3
[2024-03-04 10:18:06] > Verifying build...
[2024-03-04 10:18:06] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-a18d76b700d3/dist/bin/js -e "quit()"
[2024-03-04 10:18:06] > Launching build with testcase...
[2024-03-04 10:18:06] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-a18d76b700d3/dist/bin/js poc1.js
[2024-03-04 10:18:09] Testing build 79b38383448166074627506218757a9881ca5679 (20240207041740)
[2024-03-04 10:18:10] > Downloading: https://firefox-ci-tc.services.mozilla.com/api/queue/v1/task/MtLwS_IuSIC4eCaZ_GBPpQ/artifacts/public/build/target.jsshell.zip (319.02MiB total)
[2024-03-04 10:18:40] .. still downloading (42.9%, 4.79MB/s)
[2024-03-04 10:19:10] .. still downloading (86.1%, 4.80MB/s)
[2024-03-04 10:19:19] .. downloaded (4.80MB/s)
[2024-03-04 10:19:19] .. extracting
[2024-03-04 10:19:26] Extracted into /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-79b383834481
[2024-03-04 10:19:28] > Verifying build...
[2024-03-04 10:19:28] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-79b383834481/dist/bin/js -e "quit()"
[2024-03-04 10:19:28] > Launching build with testcase...
[2024-03-04 10:19:28] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-79b383834481/dist/bin/js poc1.js
[2024-03-04 10:19:28] > Failed to reproduce issue!
[2024-03-04 10:19:28] Enumerating pushdate builds: 2024-02-07 04:17:40+00:00 - 2024-02-08 04:59:50+00:00
[2024-03-04 10:19:42] Testing build 612d82d4c66a380984d9f6d008a86c332edb11bc (20240207161531)
[2024-03-04 10:19:43] > Downloading: https://firefox-ci-tc.services.mozilla.com/api/queue/v1/task/YQPiTBDfSvieLC_pef4bsg/artifacts/public/build/target.jsshell.zip (319.02MiB total)
[2024-03-04 10:20:13] .. still downloading (42.6%, 4.75MB/s)
[2024-03-04 10:20:43] .. still downloading (85.8%, 4.78MB/s)
[2024-03-04 10:20:52] .. downloaded (4.79MB/s)
[2024-03-04 10:20:52] .. extracting
[2024-03-04 10:20:59] Extracted into /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-612d82d4c66a
[2024-03-04 10:21:01] > Verifying build...
[2024-03-04 10:21:01] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-612d82d4c66a/dist/bin/js -e "quit()"
[2024-03-04 10:21:02] > Launching build with testcase...
[2024-03-04 10:21:02] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-612d82d4c66a/dist/bin/js poc1.js
[2024-03-04 10:21:02] > Failed to reproduce issue!
[2024-03-04 10:21:02] Testing build 1b492cccd574e45d5f16e2681b0286fd97236cdf (20240207214625)
[2024-03-04 10:21:03] > Downloading: https://firefox-ci-tc.services.mozilla.com/api/queue/v1/task/Sc9kZNkcSNqWFAxenIS2OA/artifacts/public/build/target.jsshell.zip (319.68MiB total)
[2024-03-04 10:21:32] .. still downloading (42.4%, 4.73MB/s)
[2024-03-04 10:22:02] .. still downloading (85.5%, 4.77MB/s)
[2024-03-04 10:22:12] .. downloaded (4.78MB/s)
[2024-03-04 10:22:12] .. extracting
[2024-03-04 10:22:19] Extracted into /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-1b492cccd574
[2024-03-04 10:22:21] > Verifying build...
[2024-03-04 10:22:21] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-1b492cccd574/dist/bin/js -e "quit()"
[2024-03-04 10:22:21] > Launching build with testcase...
[2024-03-04 10:22:21] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-1b492cccd574/dist/bin/js poc1.js
[2024-03-04 10:22:22] Testing build dedf6c75f1b3cdf7694bf1247373de19347ec9bd (20240207192507)
[2024-03-04 10:22:23] > Downloading: https://firefox-ci-tc.services.mozilla.com/api/queue/v1/task/L1vfEoNuRBCdI-GUp2oR3Q/artifacts/public/build/target.jsshell.zip (319.02MiB total)
[2024-03-04 10:22:52] .. still downloading (42.4%, 4.72MB/s)
[2024-03-04 10:23:22] .. still downloading (85.6%, 4.77MB/s)
[2024-03-04 10:23:32] .. downloaded (4.77MB/s)
[2024-03-04 10:23:32] .. extracting
[2024-03-04 10:23:39] Extracted into /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-dedf6c75f1b3
[2024-03-04 10:23:41] > Verifying build...
[2024-03-04 10:23:41] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-dedf6c75f1b3/dist/bin/js -e "quit()"
[2024-03-04 10:23:41] > Launching build with testcase...
[2024-03-04 10:23:41] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-dedf6c75f1b3/dist/bin/js poc1.js
[2024-03-04 10:23:42] > Failed to reproduce issue!
[2024-03-04 10:23:42] Enumerating autoland builds: 2024-02-07 19:25:07+00:00 - 2024-02-07 21:46:25+00:00
[2024-03-04 10:23:45] Unable to find build for b93dc1e74e430c10d4921f543b6f72c7ec1b8556
[2024-03-04 10:23:46] Unable to find build for 9a3212e6834b651665697e4814a642085e31f22d
[2024-03-04 10:23:46] Unable to find build for f2851598d2162c14ad3bed5d338d922047219809
[2024-03-04 10:23:47] Unable to find build for a7519f7b264ccb39d5a6f9ff1f9371f3febedebf
[2024-03-04 10:23:48] Unable to find build for c03c917c8c39b35fcdf58ba90526b82abd0ed6c8
[2024-03-04 10:23:49] Unable to find build for 22c6ddd752f44bf22d4f711491b6582587e1e594
[2024-03-04 10:23:50] Unable to find build for c6bf976590c21378d558ab73996501cfc74fead2
[2024-03-04 10:23:51] Unable to find build for 0397429549019798d9be618d00ba58c6a71fa017
[2024-03-04 10:23:51] Unable to find build for f3d1619b2e3381aaa18be6edebc7c2e839bb5196
[2024-03-04 10:23:52] Unable to find build for d6573cb6851401856295230ff6e31cac305cb90d
[2024-03-04 10:23:54] Unable to find build for e792abe83b594eb023baf5ca26052655df717a91
[2024-03-04 10:23:55] Unable to find build for f5380dcdf65522420f9c5096f70c7dc111a4d268
[2024-03-04 10:23:56] Unable to find build for b7c00efa044487561eb4d7f6834ceaaacbff9e14
[2024-03-04 10:23:57] Unable to find build for 5fd4633cdd0b855d00c682ab049ddb0ea44c2f9e
[2024-03-04 10:23:59] Unable to find build for b665f717fa147812d202a5705bd4c6d0e1ed2284
[2024-03-04 10:24:00] Unable to find build for bbb41ba529482d0152a7d07ce342f4f7d694d389
[2024-03-04 10:24:00] Unable to find build for e2597e0646c5d46a80cd1b96cfde06bc7c7dc73d
[2024-03-04 10:24:01] Unable to find build for 7f404be38e35e6f8c11d8f52a7e45d091a4eae2d
[2024-03-04 10:24:02] Unable to find build for 8261e82577cfc7769a13ffca25ce3be316e207fc
[2024-03-04 10:24:03] Unable to find build for 97a25fa6638e30a7305563b20e2bf1fa68735f77
[2024-03-04 10:24:04] Unable to find build for 4468a6dab74e768f91a83853ae09f8d8214cd33b
[2024-03-04 10:24:05] Unable to find build for 721a670e780747f2a87499b1d3b45f6b72407000
[2024-03-04 10:24:06] Unable to find build for 920ea287d7ad0fca0fe6bad4c7ffff4d22209bf3
[2024-03-04 10:24:07] Unable to find build for 2c96ad2803366505f65dc66c1ffc3eb96009476c
[2024-03-04 10:24:08] Unable to find build for 3983fe0bd56fd0f499271d6b422128f70669b7d5
[2024-03-04 10:24:09] Unable to find build for 1118131d963c7a00bb60693f1c4c15b3b4b40d17
[2024-03-04 10:24:10] Unable to find build for 7b42bd13f188ac498e6aea2d228e920478153b89
[2024-03-04 10:24:10] Unable to find build for 54623e43b90d81d31c40d60a3c2c6f64099477ac
[2024-03-04 10:24:11] Unable to find build for 87220c621617a8afd5855ac77411db1439ae3c29
[2024-03-04 10:24:12] Unable to find build for 687b59c68abe8b74cfc471d4bb5d98a41b9576a2
[2024-03-04 10:24:13] Unable to find build for 5608a954442b4aabf36915b32bf88f9771b6e7fb
[2024-03-04 10:24:14] Unable to find build for 546580b659fbbbea276f9f129d1d9e461cbf8641
[2024-03-04 10:24:15] Unable to find build for 60c24f7a22942acec6c422d134e8548e9226870c
[2024-03-04 10:24:16] Unable to find build for cd358cbc7365674424118afe260caca572a773d6
[2024-03-04 10:24:16] Unable to find build for 2d60a4692649fd0392b2f9177c282265fd0fcc6d
[2024-03-04 10:24:17] Unable to find build for cc84740decf0030c6e452269d1d38939db88382e
[2024-03-04 10:24:18] Unable to find build for 36b086dfbd13b334c132b5d8cd9e9182783606db
[2024-03-04 10:24:19] Unable to find build for c4a9d375161900b09f757525edeb568164c5e325
[2024-03-04 10:24:20] Unable to find build for 330e9b1f94c24abf456f47dc3a3e4fcd1e7dad6c
[2024-03-04 10:24:20] Unable to find build for eb4e8c43f195d68dd0f5aac89f198d3e4d0fd3fd
[2024-03-04 10:24:21] Unable to find build for 84881cb47fa46377fd54fcfb36d395a61a4a70f6
[2024-03-04 10:24:22] Unable to find build for b921c505276985dc715895413ee299c96d755c00
[2024-03-04 10:24:23] Unable to find build for 1e73637ac83a296d733bc304b12c2e2f1ba09fe1
[2024-03-04 10:24:24] Unable to find build for b2e92a2d742f43ad92c80b206b3db15a6256fdd8
[2024-03-04 10:24:25] Unable to find build for 577ff71206991ac2e5533280b1bda0ecb275f9e4
[2024-03-04 10:24:25] Unable to find build for bb7ec83aef1c1264c029956e8c11bf87c9df3c87
[2024-03-04 10:24:26] Unable to find build for 578dc04cbc0cd6bb4b7742dd273e406e19fbe1f0
[2024-03-04 10:24:27] Unable to find build for 4190a8a3805bb29b7694a7b2e6994a0c19ff39c5
[2024-03-04 10:24:28] Unable to find build for 733356cf131d2cc0b61907f46dd48a75787d4a7c
[2024-03-04 10:24:29] Unable to find build for a06e0e423e3d76a05b255a5c7ea77b325bb9deca
[2024-03-04 10:24:29] Unable to find build for e11d865508b49d371a7f846c69be74995e370546
[2024-03-04 10:24:30] Unable to find build for 536bba21f1869a4888ad77c361d23f3e3ea88d7d
[2024-03-04 10:24:31] Unable to find build for 0ed7433a0a3b7947c0bf2328822c03bb3f733392
[2024-03-04 10:24:32] Unable to find build for 57c4fd85b6862a2f59f8c09368d77eba1f1edef1
[2024-03-04 10:24:33] Unable to find build for 63ad7de808caf7f2265374c13f9d42bc659ce0df
[2024-03-04 10:24:35] Unable to find build for 5acd1145137a07b861a918ef55923217ae4a0955
[2024-03-04 10:24:36] Unable to find build for d5e66d2f63ce649cdb2530c6ffd851648c2475b2
[2024-03-04 10:24:36] Unable to find build for 1b492cccd574e45d5f16e2681b0286fd97236cdf
[2024-03-04 10:24:36] Testing build fdda8b6b095615f06fbef5c21ff9ad0a90927c83 (20240207140510)
[2024-03-04 10:24:37] > Downloading: https://firefox-ci-tc.services.mozilla.com/api/queue/v1/task/DyNi5o7vS_-WHKOAxBTm-Q/artifacts/public/build/target.jsshell.zip (319.04MiB total)
[2024-03-04 10:25:07] .. still downloading (42.7%, 4.75MB/s)
[2024-03-04 10:25:37] .. still downloading (85.9%, 4.78MB/s)
[2024-03-04 10:25:47] .. downloaded (4.78MB/s)
[2024-03-04 10:25:47] .. extracting
[2024-03-04 10:25:53] Extracted into /home/test/.cache/autobisect/builds/js-m-a-linux-asan-debug-fdda8b6b0956
[2024-03-04 10:25:55] > Verifying build...
[2024-03-04 10:25:55] Running: /home/test/.cache/autobisect/builds/js-m-a-linux-asan-debug-fdda8b6b0956/dist/bin/js -e "quit()"
[2024-03-04 10:25:56] > Launching build with testcase...
[2024-03-04 10:25:56] Running: /home/test/.cache/autobisect/builds/js-m-a-linux-asan-debug-fdda8b6b0956/dist/bin/js poc1.js
[2024-03-04 10:25:56] > Failed to reproduce issue!
[2024-03-04 10:25:56] Testing build fcafc196f2cef3d5c607edaa0f66c96cdf1708d6 (20240207172501)
[2024-03-04 10:25:57] > Downloading: https://firefox-ci-tc.services.mozilla.com/api/queue/v1/task/Mriix49XQJGTQ5RUNJwz6g/artifacts/public/build/target.jsshell.zip (319.68MiB total)
[2024-03-04 10:26:26] .. still downloading (42.6%, 4.76MB/s)
[2024-03-04 10:26:56] .. still downloading (85.7%, 4.79MB/s)
[2024-03-04 10:27:06] .. downloaded (4.79MB/s)
[2024-03-04 10:27:06] .. extracting
[2024-03-04 10:27:12] Extracted into /home/test/.cache/autobisect/builds/js-m-a-linux-asan-debug-fcafc196f2ce
[2024-03-04 10:27:15] > Verifying build...
[2024-03-04 10:27:15] Running: /home/test/.cache/autobisect/builds/js-m-a-linux-asan-debug-fcafc196f2ce/dist/bin/js -e "quit()"
[2024-03-04 10:27:15] > Launching build with testcase...
[2024-03-04 10:27:15] Running: /home/test/.cache/autobisect/builds/js-m-a-linux-asan-debug-fcafc196f2ce/dist/bin/js poc1.js
[2024-03-04 10:27:15] Reduced build range to:
[2024-03-04 10:27:15] > Start: fdda8b6b095615f06fbef5c21ff9ad0a90927c83 (20240207140510)
[2024-03-04 10:27:15] > End: fcafc196f2cef3d5c607edaa0f66c96cdf1708d6 (20240207172501)
[2024-03-04 10:27:15] > https://hg.mozilla.org/integration/autoland/pushloghtml?fromchange=fdda8b6b095615f06fbef5c21ff9ad0a90927c83&tochange=fcafc196f2cef3d5c607edaa0f66c96cdf1708d6
[2024-03-04 10:27:15] Bisection completed in: 0:18:33
```

---

**Comment 9 — continuation@gmail.com — 2024-03-04T14:55:49Z**

Thank you for running a bisection. [Here](https://hg.mozilla.org/integration/autoland/pushloghtml?fromchange=fdda8b6b095615f06fbef5c21ff9ad0a90927c83&tochange=fcafc196f2cef3d5c607edaa0f66c96cdf1708d6) is the regression range reported by at the end. Bug 1863435 looks like the only WebAssembly thing in there, so I'll mark it as a regression for now.

---

**Comment 10 — release-mgmt-account-bot@mozilla.tld — 2024-03-04T15:42:59Z**

:bvisness, since you are the author of the regressor, bug 1863435, could you take a look? Also, could you set the severity field?

For more information, please visit [BugBot documentation](https://wiki.mozilla.org/BugBot#needinfo_regression_author.py).

---

**Comment 11 — jdemooij@mozilla.com — 2024-03-04T15:58:18Z**

[Tracking Requested - why for this release]:

---

**Comment 12 — release-mgmt-account-bot@mozilla.tld — 2024-03-04T16:42:36Z**

Set release status flags based on info from the regressing bug 1863435

---

**Comment 13 — rhunt@eqrion.net — 2024-03-04T21:23:19Z**

From talking with Ben, the root cause appears to be from some JIT array allocation code checking for signed overflow instead of unsigned overflow. The regressing commit is correct.

The net result here is that you can construct a wasm array with a length that overflowed to be very large, but yet has a small allocation, leading to OOB read/write.

---

**Comment 14 — bvisness@mozilla.com — 2024-03-04T21:23:25Z**

Created attachment 9389222
Bug 1882751: Replace runtime array length checks with a lookup. r=rhunt

---

**Comment 15 — bvisness@mozilla.com — 2024-03-04T21:23:36Z**

Created attachment 9389223
Bug 1882751: Document signed vs. unsigned assembler operations. r=rhunt



Depends on D203511

---

**Comment 16 — bvisness@mozilla.com — 2024-03-04T21:23:41Z**

Created attachment 9389224
Bug 1882751: Add more robust wasm array overflow tests. r=rhunt



Depends on D203512

---

**Comment 17 — eternalsakuraalpha@gmail.com — 2024-03-04T22:34:28Z**

Regarding comment#13: Thank you for your analysis. It sounds like this could lead to a potentially exploitable vulnerability involving a controllable and significant length of out-of-bounds read/write. 

I will attempt to write an exploit for it. Could you please provide a simplified, readable proof-of-concept (PoC) attachment here? This would save me a lot of time. Thank you.

---

**Comment 18 — bvisness@mozilla.com — 2024-03-05T15:26:59Z**

Created attachment 9389413
Bug 1882751: Rename calcStorageBytes to calcStorageBytesUnchecked. r=rhunt



Depends on D203513

---

**Comment 19 — rhunt@eqrion.net — 2024-03-05T22:12:50Z**

Comment on attachment 9389222
Bug 1882751: Replace runtime array length checks with a lookup. r=rhunt

### Security Approval Request
* **How easily could an exploit be constructed based on the patch?**: Medium to easy difficulty. The issue is that we're using signed overflow checking when we should be using unsigned overflow checking. However, our JIT arch support for unsigned overflow checking is spotty, so we instead refactored the routine to not use the asm overflow bit but to instead check the array length against our implementation limit directly. If the attacker figures out that the root issue was signed/unsigned overflow, then the next step is discovering that you need to do at least one array allocation with valid length before doing one with an overflow length. After that, the issue can be reliably triggered and seems easily exploitable.
* **Do comments in the patch, the check-in comment, or tests included in the patch paint a bulls-eye on the security problem?**: No
* **Which branches (beta, release, and/or ESR) are affected by this flaw, and do the release status flags reflect this affected/unaffected state correctly?**: Beta
* **If not all supported branches, which bug introduced the flaw?**: Bug 1863435
* **Do you have backports for the affected branches?**: Yes
* **If not, how different, hard to create, and risky will they be?**: 
* **How likely is this patch to cause regressions; how much testing does it need?**: Unlikely, we've added more robust tests here (in a separate patch), which we've been running.
* **Is the patch ready to land after security approval is given?**: Yes
* **Is Android affected?**: Yes

---

**Comment 20 — bvisness@mozilla.com — 2024-03-06T19:20:26Z**

*** Bug 1882481 has been marked as a duplicate of this bug. ***

---

**Comment 21 — bvisness@mozilla.com — 2024-03-06T19:22:04Z**

We received another independent report of this issue in bug 1882481. The reporter has not yet been added to the cc list on this bug - I can add them unless there is some reason I shouldn't.

---

**Comment 22 — continuation@gmail.com — 2024-03-06T19:26:29Z**

I went ahead and CC'ed them. There's generally no reason not to add the original reporter to a duplicate, unless somehow the bug you are duplicating to is some kind of massively larger and difficult to fix, but I think that is very rare.

---

**Comment 23 — dveditz@mozilla.com — 2024-03-06T20:31:16Z**

The regressing bug landed ~3 weeks before this bug was filed, and then two people found the same bug a day apart. But the fix for bug 1880719—another regression from bug 1863435—landed a day before this bug was found. Could be coincidence, or maybe this bug was unreachable until that one was out of the way.

---

**Comment 24 — bvisness@mozilla.com — 2024-03-06T20:43:40Z**

Created attachment 9389780
Bug 1882751: Replace runtime array length checks with a lookup. r=rhunt


We can reduce branching in our array allocation code by doing a single
comparison against a statically-known maximum numElements for each array
elemSize.

Original Revision: https://phabricator.services.mozilla.com/D203511

---

**Comment 25 — phab-bot@bmo.tld — 2024-03-06T20:51:37Z**

Comment on attachment 9389224
Bug 1882751: Add more robust wasm array overflow tests. r=rhunt

Revision D203513 was moved to bug 1882201. Setting attachment 9389224 to obsolete.

---

**Comment 26 — phab-bot@bmo.tld — 2024-03-06T20:51:48Z**

Comment on attachment 9389413
Bug 1882751: Rename calcStorageBytes to calcStorageBytesUnchecked. r=rhunt

Revision D203618 was moved to bug 1882201. Setting attachment 9389413 to obsolete.

---

**Comment 27 — dveditz@mozilla.com — 2024-03-06T21:07:44Z**

Comment on attachment 9389222
Bug 1882751: Replace runtime array length checks with a lookup. r=rhunt

sec-approval+ = dveditz

Please create a beta-branch version of this patch and request beta uplift ASAP
Please don't land on -central before you get beta uplift approval from release managers
Both branches need to land by tomorrow afternoon so it makes 124 beta-9 (last beta!)
Please move the test and function name-change patches to bug 1882201 to land after we release these fixes

Thanks!

---

**Comment 28 — phab-bot@bmo.tld — 2024-03-06T21:16:10Z**

# Uplift Approval Request
- **Risk associated with taking this patch**: Low
- **Code covered by automated testing**: yes
- **Explanation of risk level**: This is well-tested code, it is passing a battery of new tests for this issue, and we have tested it on real websites using WebAssembly GC.
- **Needs manual QE test**: no
- **Is Android affected?**: yes
- **Fix verified in Nightly**: yes
- **String changes made/needed**: None
- **User impact if declined**: Exploitable OOB reads and writes of large ranges of memory.
- **Steps to reproduce for manual QE testing**: None

---

**Comment 29 — pulsebot@bmo.tld — 2024-03-06T22:45:54Z**

Pushed by bvisness@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/e04e6de57633
Replace runtime array length checks with a lookup. r=rhunt

---

**Comment 30 — aryx.bugmail@gmx-topmail.de — 2024-03-07T09:58:55Z**

https://hg.mozilla.org/mozilla-central/rev/e04e6de57633

---

**Comment 31 — eternalsakuraalpha@gmail.com — 2024-03-07T12:48:29Z**

Can I get a CVE for this vulnerability? If so, please credit "Nan Wang(@eternalsakura13)" .

---

**Comment 32 — pulsebot@bmo.tld — 2024-03-07T15:31:24Z**

https://hg.mozilla.org/releases/mozilla-beta/rev/cafdca10a3ff

---

**Comment 33 — fbraun@mozilla.com — 2024-03-07T15:55:51Z**

(In reply to Nan Wang[:sakura] from comment #31)
> Can I get a CVE for this vulnerability? If so, please credit "Nan Wang(@eternalsakura13)" .

We'll do that. But we usually assign CVEs when we know which release this is going to be in, so this might take a bit.

---

**Comment 34 — eternalsakuraalpha@gmail.com — 2024-03-08T12:44:31Z**

As this is my first time submitting a vulnerability to Firefox, I would like to kindly bring this to the attention of the reward team. Thanks

Based on #c23, it appears that someone else and I have discovered the same issue within a 72-hour timeframe.
According to the following terms, the bounty will be equally divided among us:
https://www.mozilla.org/en-US/security/bug-bounty/
```
The security bug must be original and previously unreported. Duplicate submissions within 72 hours will split the bounty between reporters.
```

---

**Comment 35 — dveditz@mozilla.com — 2024-03-12T19:21:11Z**

We are awarding a bounty for this bug, split with the reporter who found the duplicate slightly earlier

---

**Comment 36 — continuation@gmail.com — 2024-04-15T13:31:20Z**

*** Bug 1882476 has been marked as a duplicate of this bug. ***
