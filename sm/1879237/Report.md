# [WASM] MOZ_ASSERT(v.isMem() == result.onStack());

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1879237
CVE: CVE-2024-2606
Component: JavaScript: WebAssembly
Bounty: (unknown)
Date: 2024-02-08T02:14:42Z
Keywords: csectype-jit, regression, reporter-external, sec-high

Created attachment 9378912
poc0208.js

User Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36

Steps to reproduce:

OS      : Linux ubuntu 5.11.10 #1 SMP Sat Oct 30 23:40:08 CST 2021 x86_64 x86_64 x86_64 GNU/Linux
Commit  : 719b4a8853b449674c018178f85b3667afe4f193
Build   : 
ac_add_options --enable-project=js
ac_add_options --disable-optimize
ac_add_options --disable-unified-build
ac_add_options --enable-debug
ac_add_options --disable-jemalloc

Running: 
./js --wasm-memory-control --wasm-compiler=baseline --wasm-exnref poc.js


Actual results:

```
Stopped reason: SIGSEGV
0x0000555559313036 in js::wasm::BaseCompiler::shuffleStackResultsBeforeBranch (this=0x7fffffff2be8, srcHeight=..., destHeight=..., type=...) at gecko-dev-latest/js/src/wasm/WasmBaselineCompile.cpp:1298
1298	      MOZ_ASSERT(v.isMem() == result.onStack());
gdb-peda$ bt
#0  0x0000555559313036 in js::wasm::BaseCompiler::shuffleStackResultsBeforeBranch(js::wasm::StackHeight, js::wasm::StackHeight, js::wasm::ResultType)
    (this=0x7fffffff2be8, srcHeight=..., destHeight=..., type=...) at gecko-dev-latest/js/src/wasm/WasmBaselineCompile.cpp:1298
#1  0x0000555559319a19 in js::wasm::BaseCompiler::jumpConditionalWithResults(js::wasm::BranchState*, js::wasm::RegRef, js::wasm::RefType, js::wasm::RefType, bool) (this=0x7fffffff2be8, b=0x7ffffffee658, object=..., sourceType=..., destType=..., onSuccess=0x0)
    at gecko-dev-latest/js/src/wasm/WasmBaselineCompile.cpp:3245
#2  0x000055555932e8a1 in js::wasm::BaseCompiler::emitBrOnCastCommon(bool, unsigned int, js::wasm::ResultType const&, js::wasm::RefType, js::wasm::RefType) (this=0x7fffffff2be8, onSuccess=0x0, labelRelativeDepth=0x0, labelType=..., sourceType=..., destType=...)
    at gecko-dev-latest/js/src/wasm/WasmBaselineCompile.cpp:8392
#3  0x000055555932ea8d in js::wasm::BaseCompiler::emitBrOnCast(bool) (this=0x7fffffff2be8, onSuccess=0x0)
    at gecko-dev-latest/js/src/wasm/WasmBaselineCompile.cpp:8418
#4  0x0000555559343057 in js::wasm::BaseCompiler::emitBody() (this=0x7fffffff2be8)
    at gecko-dev-latest/js/src/wasm/WasmBaselineCompile.cpp:10629
#5  0x000055555936831a in js::wasm::BaseCompiler::emitFunction() (this=0x7fffffff2be8)
    at gecko-dev-latest/js/src/wasm/WasmBaselineCompile.cpp:11740
#6  0x0000555559369669 in js::wasm::BaselineCompileFunctions(js::wasm::ModuleEnvironment const&, js::wasm::CompilerEnvironment const&, js::LifoAlloc&, mozilla::Vector<js::wasm::FuncCompileInput, 8ul, js::SystemAllocPolicy> const&, js::wasm::CompiledCode*, mozilla::UniquePtr<char [], JS::FreePolicy>*)
     (moduleEnv=..., compilerEnv=..., lifo=..., inputs=..., code=0x55555a0b1280, error=0x7fffffff5658)
    at gecko-dev-latest/js/src/wasm/WasmBaselineCompile.cpp:11917
#7  0x000055555943b9e4 in ExecuteCompileTask(js::wasm::CompileTask*, mozilla::UniquePtr<char [], JS::FreePolicy>*)
    (task=0x55555a0b0ed0, error=0x7fffffff5658) at gecko-dev-latest/js/src/wasm/WasmGenerator.cpp:735
#8  0x000055555943bbe4 in js::wasm::ModuleGenerator::locallyCompileCurrentTask() (this=0x7fffffff4560)
    at gecko-dev-latest/js/src/wasm/WasmGenerator.cpp:784
#9  0x000055555943c777 in js::wasm::ModuleGenerator::finishFuncDefs() (this=0x7fffffff4560)
    at gecko-dev-latest/js/src/wasm/WasmGenerator.cpp:915
#10 0x0000555559414106 in DecodeCodeSection<js::wasm::Decoder>(js::wasm::ModuleEnvironment const&, js::wasm::Decoder&, js::wasm::ModuleGenerator&)
    (env=..., d=..., mg=...) at gecko-dev-latest/js/src/wasm/WasmCompile.cpp:785
#11 0x0000555559413e32 in js::wasm::CompileBuffer(js::wasm::CompileArgs const&, js::wasm::ShareableBytes const&, mozilla::UniquePtr<char [], JS::FreePolicy>*, mozilla::Vector<mozilla::UniquePtr<char [], JS::FreePolicy>, 0ul, js::SystemAllocPolicy>*, JS::OptimizedEncodingListener*)
    (args=..., bytecode=..., error=0x7fffffff5658, warnings=0x7fffffff56a0, listener=0x0)
    at gecko-dev-latest/js/src/wasm/WasmCompile.cpp:807
#12 0x00005555594fe1ce in js::WasmModuleObject::construct(JSContext*, unsigned int, JS::Value*) (cx=0x555559f66060, argc=0x1, vp=0x55555a0731c8)
    at gecko-dev-latest/js/src/wasm/WasmJS.cpp:1494
#13 0x0000555557982f26 in CallJSNative(JSContext*, bool (*)(JSContext*, unsigned int, JS::Value*), js::CallReason, JS::CallArgs const&)
    (cx=0x555559f66060, native=0x5555594fddd0 <js::WasmModuleObject::construct(JSContext*, unsigned int, JS::Value*)>, reason=js::CallReason::Call, args=...) at gecko-dev-latest/js/src/vm/Interpreter.cpp:480
#14 0x00005555579940ea in CallJSNativeConstructor(JSContext*, bool (*)(JSContext*, unsigned int, JS::Value*), JS::CallArgs const&)
    (cx=0x555559f66060, native=0x5555594fddd0 <js::WasmModuleObject::construct(JSContext*, unsigned int, JS::Value*)>, args=...)
    at gecko-dev-latest/js/src/vm/Interpreter.cpp:496
#15 0x000055555794a3ae in InternalConstruct(JSContext*, js::AnyConstructArgs const&, js::CallReason)
    (cx=0x555559f66060, args=..., reason=js::CallReason::Call) at gecko-dev-latest/js/src/vm/Interpreter.cpp:702
#16 0x0000555557949dc1 in js::ConstructFromStack(JSContext*, JS::CallArgs const&, js::CallReason)
    (cx=0x555559f66060, args=..., reason=js::CallReason::Call) at gecko-dev-latest/js/src/vm/Interpreter.cpp:749
#17 0x000055555795f13e in js::Interpret(JSContext*, js::RunState&) (cx=0x555559f66060, state=...)
    at gecko-dev-latest/js/src/vm/Interpreter.cpp:3046
#18 0x00005555579488ac in MaybeEnterInterpreterTrampoline(JSContext*, js::RunState&) (cx=0x555559f66060, state=...)
    at gecko-dev-latest/js/src/vm/Interpreter.cpp:394
#19 0x0000555557948492 in js::RunScript(JSContext*, js::RunState&) (cx=0x555559f66060, state=...)
    at gecko-dev-latest/js/src/vm/Interpreter.cpp:452
#20 0x000055555794b257 in js::ExecuteKernel(JSContext*, JS::Handle<JSScript*>, JS::Handle<JSObject*>, js::AbstractFramePtr, JS::MutableHandle<JS::Value>)
    (cx=0x555559f66060, script=0xc92dfd66060, envChainArg=(JSObject * const) 0xc92dfd3f038 [object LexicalEnvironment], evalInFrame=AbstractFramePtr ((js::InterpreterFrame *) 0x0) = {...}, result=$JS::UndefinedValue()) at gecko-dev-latest/js/src/vm/Interpreter.cpp:839
#21 0x000055555794b65c in js::Execute(JSContext*, JS::Handle<JSScript*>, JS::Handle<JSObject*>, JS::MutableHandle<JS::Value>)
    (cx=0x555559f66060, script=0xc92dfd66060, envChain=(JSObject * const) 0xc92dfd3f038 [object LexicalEnvironment], rval=$JS::UndefinedValue())
    at gecko-dev-latest/js/src/vm/Interpreter.cpp:871
#22 0x0000555557dca0df in ExecuteScript(JSContext*, JS::Handle<JSObject*>, JS::Handle<JSScript*>, JS::MutableHandle<JS::Value>)
    (cx=0x555559f66060, envChain=(JSObject * const) 0xc92dfd3f038 [object LexicalEnvironment], script=0xc92dfd66060, rval=$JS::UndefinedValue())
    at gecko-dev-latest/js/src/vm/CompilationAndEvaluation.cpp:494
#23 0x0000555557dca206 in JS_ExecuteScript(JSContext*, JS::Handle<JSScript*>) (cx=0x555559f66060, scriptArg=0xc92dfd66060)
    at gecko-dev-latest/js/src/vm/CompilationAndEvaluation.cpp:518
#24 0x00005555577d0527 in RunFile(JSContext*, char const*, _IO_FILE*, CompileUtf8, bool, bool)
    (cx=0x555559f66060, filename=0x55555a07a5a0 "/tmp/crash3.js", file=0x555559ffe250, compileMethod=CompileUtf8::DontInflate, compileOnly=0x0, fullParse=0x0) at gecko-dev-latest/js/src/shell/js.cpp:1221
#25 0x00005555577cfba0 in Process(JSContext*, char const*, bool, FileKind)
    (cx=0x555559f66060, filename=0x55555a07a5a0 "/tmp/crash3.js", forceTTY=0x0, kind=FileScript)
    at gecko-dev-latest/js/src/shell/js.cpp:1801
#26 0x000055555779bb7b in ProcessArgs(JSContext*, js::cli::OptionParser*) (cx=0x555559f66060, op=0x7fffffffdec0)
    at gecko-dev-latest/js/src/shell/js.cpp:10905
#27 0x0000555557792c57 in Shell(JSContext*, js::cli::OptionParser*) (cx=0x555559f66060, op=0x7fffffffdec0)
    at gecko-dev-latest/js/src/shell/js.cpp:11167
#28 0x000055555778d969 in main(int, char**) (argc=0x5, argv=0x7fffffffe118) at gecko-dev-latest/js/src/shell/js.cpp:11571
#29 0x00007ffff7a48083 in __libc_start_main () at /lib/x86_64-linux-gnu/libc.so.6
#30 0x0000555557753b79 in _start ()
```

---

**Comment 1 — cz18811105578@gmail.com — 2024-02-08T02:25:47Z**

This is the GIT commit hash(719b4a8853b449674c018178f85b3667afe4f193).

---

**Comment 2 — rhunt@eqrion.net — 2024-02-08T16:44:11Z**

This seems like it's possibly the same root cause as bug 1879238.

---

**Comment 3 — bvisness@mozilla.com — 2024-02-13T17:01:33Z**

Created attachment 9379984
Bug 1879237: Consolidate wasm cast code. r=rhunt

---

**Comment 4 — dveditz@mozilla.com — 2024-02-14T23:57:59Z**

(In reply to Ryan Hunt [:rhunt] from comment #2)
> This seems like it's possibly the same root cause as bug 1879238.

That bug was deemed to be not a security bug, but largely because the MOZ_CRASH(). This one will keep executing after the assert. How bad is it?

---

**Comment 5 — rhunt@eqrion.net — 2024-02-20T23:21:29Z**

This one is different from bug 1879238. We're messing up our register allocation in wasm baseline during a cast+branch operation which has params. I'm not sure the full impact yet or if there is some mitigating factor. I'm reviewing the patch now. This is probably higher than an S3.

---

**Comment 6 — rhunt@eqrion.net — 2024-02-21T18:11:25Z**

This one is tricky, I'm not sure if it's exploitable or not.

The issue was that when doing a `br_on_cast $label` instruction to a `(block $label)` we can pass extra params in addition to the value we're casting. Our baseline compiler uses an ABI for passing block parameters, with the first value in a register and extra ones passed in the stack. Our code before this patch would first move all the params to the right regs/stack slots but then could accidentally call `needResultRegs` which would spill the reg params to the stack before performing the branch. The assert we ran into was checking that this doesn't happen.

The tricky part is that the old reg params will still be in registers, even if we spill them to the stack. So we won't be passing an invalid value. We also do a stack shuffle that looks like it could be messed up by the unexpected push, but it does all addressing relative to FP, so it should still be valid.

There could be something I'm missing though, so we should be conservative and assume there's a chance someone could figure a way to pass an invalid value to a block param.

---

**Comment 7 — rhunt@eqrion.net — 2024-02-21T18:14:14Z**

This was caused by bug 1817782 being an incomplete fix for the root problem.

---

**Comment 8 — dveditz@mozilla.com — 2024-02-22T00:08:32Z**

I'm a little confused about the security severity, but it sounds bad and Ryan rated it an "S2" worry.

---

**Comment 9 — rhunt@eqrion.net — 2024-02-22T15:38:03Z**

(In reply to Daniel Veditz [:dveditz] from comment #8)
> I'm a little confused about the security severity, but it sounds bad and Ryan rated it an "S2" worry.

Yeah, I'm just not sure. It seems like there are mitigating factors that could prevent this from going bad, but I'm not 100% sure so conservatively labeling sec-high seems safe to me.

---

**Comment 10 — rhunt@eqrion.net — 2024-02-26T18:09:11Z**

Comment on attachment 9379984
Bug 1879237: Consolidate wasm cast code. r=rhunt

### Security Approval Request
* **How easily could an exploit be constructed based on the patch?**: Not easily. The important change in the baseline compiler is masked by refactoring to centralize some of the register allocation logic. As noted above, it's not clear if this is exploitable either, but seems possible.
* **Do comments in the patch, the check-in comment, or tests included in the patch paint a bulls-eye on the security problem?**: No
* **Which branches (beta, release, and/or ESR) are affected by this flaw, and do the release status flags reflect this affected/unaffected state correctly?**: Beta and release
* **If not all supported branches, which bug introduced the flaw?**: 1817782, but not enabled until wasm-GC enabled in bug 1845373 (Fx120)
* **Do you have backports for the affected branches?**: Yes
* **If not, how different, hard to create, and risky will they be?**: 
* **How likely is this patch to cause regressions; how much testing does it need?**: This is tricky code, but we do have some good tests for it (with more added for this case). We've also done some manual testing on known Wasm-GC websites.
* **Is the patch ready to land after security approval is given?**: Yes
* **Is Android affected?**: Yes

---

**Comment 11 — tom@mozilla.com — 2024-02-27T15:26:18Z**

Comment on attachment 9379984
Bug 1879237: Consolidate wasm cast code. r=rhunt

approved to land anduplift

---

**Comment 12 — pulsebot@bmo.tld — 2024-02-27T16:12:27Z**

Pushed by bvisness@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/d20d0f5e7849
Consolidate wasm cast code. r=rhunt

---

**Comment 13 — bvisness@mozilla.com — 2024-02-27T19:07:39Z**

Created attachment 9387903
Bug 1879237: Consolidate wasm cast code. r=rhunt


The code for tracking register allocation in wasm casts was getting very
unwieldy. This patch replaces several switches with a single function
that checks which registers are necessary, and simplifies the allocation
logic in both baseline and ion to use this result.

Original Revision: https://phabricator.services.mozilla.com/D201734

---

**Comment 14 — phab-bot@bmo.tld — 2024-02-27T19:22:11Z**

# Uplift Approval Request
- **User impact if declined**: This issue may be discovered to be exploitable, resulting in invalid wasm values being created, such as arbitrary integers turning into pointer values.
- **Steps to reproduce for manual QE testing**: None
- **Code covered by automated testing**: yes
- **Is Android affected?**: yes
- **Fix verified in Nightly**: yes
- **Needs manual QE test**: no
- **Explanation of risk level**: This is difficult code that has already seen an incomplete fix before. We've improved our test coverage in response and done manual testing on real world sites with this patch to mitigate the risk.
- **Risk associated with taking this patch**: Medium
- **String changes made/needed**: None

---

**Comment 15 — ryanvm@gmail.com — 2024-02-28T04:36:05Z**

https://hg.mozilla.org/mozilla-central/rev/d20d0f5e7849

---

**Comment 16 — pulsebot@bmo.tld — 2024-03-02T16:15:13Z**

https://hg.mozilla.org/releases/mozilla-beta/rev/e28c70d1db21

---

**Comment 17 — fbraun@mozilla.com — 2024-03-05T20:01:41Z**

We're awarding a bounty on the lower end of the "sec-high" spectrum, because it's entirely unclear whether this can be exploited and how. We're happy to re-evaluate if you can find out more.

---

**Comment 18 — twsmith@mozilla.com — 2024-03-15T18:50:57Z**

Created attachment 9391525
advisory.txt
