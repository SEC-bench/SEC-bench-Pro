# Assertion failure: u.func.beginToUncheckedCallEntry_ != 0, at js/src/wasm/WasmCodegenTypes.h:488

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1903219
Component: JavaScript: WebAssembly
Bounty: (unknown)
Date: 2024-06-18T08:49:11Z
Keywords: csectype-wildptr, regression, reporter-external, sec-high, testcase

Created attachment 9408108
poc.js

Steps to reproduce:

commit : ae0ed821959cc6b5b255b0774becd34c317e53f8
configure :
```
ac_add_options --enable-project=js
ac_add_options --enable-debug
ac_add_options --enable-optimize
mk_add_options MOZ_OBJDIR=@TOPSRCDIR@/obj-debug-orig-@CONFIG_GUESS@
```
build command :
```
./mach build
```


Actual results:

proof of concept:
/gecko-dev/obj-debug-orig-x86_64-pc-linux-gnu/dist/bin/js --setpref=wasm_js_string_builtins=true ./poc.js
```
[3868076] Assertion failure: u.func.beginToUncheckedCallEntry_ != 0, at /gecko-dev/js/src/wasm/WasmCodegenTypes.h:488
#01: ???[/gecko-dev/obj-debug-orig-x86_64-pc-linux-gnu/dist/bin/js +0x31e9236]
#02: ???[/gecko-dev/obj-debug-orig-x86_64-pc-linux-gnu/dist/bin/js +0x30edbaf]
#03: ???[/gecko-dev/obj-debug-orig-x86_64-pc-linux-gnu/dist/bin/js +0x3104e5c]
#04: ???[/gecko-dev/obj-debug-orig-x86_64-pc-linux-gnu/dist/bin/js +0x31a2d7d]
#05: ???[/gecko-dev/obj-debug-orig-x86_64-pc-linux-gnu/dist/bin/js +0x3105c2c]
#06: ???[/gecko-dev/obj-debug-orig-x86_64-pc-linux-gnu/dist/bin/js +0x1d048b5]
#07: ???[/gecko-dev/obj-debug-orig-x86_64-pc-linux-gnu/dist/bin/js +0x1d0ea5d]
#08: ???[/gecko-dev/obj-debug-orig-x86_64-pc-linux-gnu/dist/bin/js +0x1cddf52]
#09: ???[/gecko-dev/obj-debug-orig-x86_64-pc-linux-gnu/dist/bin/js +0x1cec470]
#10: ???[/gecko-dev/obj-debug-orig-x86_64-pc-linux-gnu/dist/bin/js +0x1cdbbef]
#11: ???[/gecko-dev/obj-debug-orig-x86_64-pc-linux-gnu/dist/bin/js +0x1cdf10c]
#12: ???[/gecko-dev/obj-debug-orig-x86_64-pc-linux-gnu/dist/bin/js +0x1cdf580]
#13: ???[/gecko-dev/obj-debug-orig-x86_64-pc-linux-gnu/dist/bin/js +0x1e96232]
#14: JS_ExecuteScript(JSContext*, JS::Handle<JSScript*>)[/gecko-dev/obj-debug-orig-x86_64-pc-linux-gnu/dist/bin/js +0x1e9643c]
#15: ???[/gecko-dev/obj-debug-orig-x86_64-pc-linux-gnu/dist/bin/js +0x1c26c8f]
#16: ???[/gecko-dev/obj-debug-orig-x86_64-pc-linux-gnu/dist/bin/js +0x1c25fa9]
#17: ???[/gecko-dev/obj-debug-orig-x86_64-pc-linux-gnu/dist/bin/js +0x1be187a]
#18: ???[/gecko-dev/obj-debug-orig-x86_64-pc-linux-gnu/dist/bin/js +0x1bd9c62]
#19: __libc_start_main[/lib/x86_64-linux-gnu/libc.so.6 +0x24083]
#20: ???[/gecko-dev/obj-debug-orig-x86_64-pc-linux-gnu/dist/bin/js +0x1bce309]
#21: ??? (???:???)
Segmentation fault
```

stack dump:
```
gdb-peda$ bt
#0  js::wasm::CodeRange::funcCheckedCallEntry() const (this=0x7ffff512bcc0) at /gecko-dev/js/src/wasm/WasmCodegenTypes.h:488
#1  js::wasm::Table::fillFuncRef(unsigned int, unsigned int, js::wasm::FuncRef, JSContext*)
    (this=0x7ffff62df120, index=0x0, fillCount=0x1, ref=..., cx=<optimized out>) at /gecko-dev/js/src/wasm/WasmTable.cpp:246
#2  0x0000555558641baf in js::wasm::Instance::init(JSContext*, JS::GCVector<JSObject*, 0ul, js::SystemAllocPolicy> const&, JS::GCVector<js::wasm::Val, 0ul, js::SystemAllocPolicy> const&, JS::Handle<JS::GCVector<js::WasmMemoryObject*, 0ul, js::SystemAllocPolicy> >, JS::GCVector<js::WasmGlobalObject*, 0ul, js::SystemAllocPolicy> const&, JS::GCVector<js::WasmTagObject*, 0ul, js::SystemAllocPolicy> const&, mozilla::Vector<RefPtr<js::wasm::DataSegment const>, 0ul, js::SystemAllocPolicy> const&, mozilla::Vector<js::wasm::ModuleElemSegment, 0ul, js::SystemAllocPolicy> const&)
    (this=this@entry=0x7ffff626e400, cx=cx@entry=0x7ffff6235100, funcImports=..., globalImportValues=..., memories=memories@entry={
  vector = {
    <js::SystemAllocPolicy> = {
      <js::AllocPolicyBase> = {<No data fields>}, <No data fields>},
    members of mozilla::Vector<js::WasmMemoryObject*, 0ul, js::SystemAllocPolicy>:
    static kElemIsPod = 0x1,
    static kMaxInlineBytes = <optimized out>,
    static kInlineCapacity = 0x0,
    mBegin = 0x7ffff62254e0,
    mLength = 0x4,
    mTail = {
      <mozilla::Vector<js::WasmMemoryObject*, 0ul, js::SystemAllocPolicy>::CapacityAndReserved> = {
        mCapacity = 0x4,
        mReserved = 0x4
      }, <No data fields>},
    mEntered = 0x0,
    static sMaxInlineStorage = 0x0
  },
  static InlineLength = <optimized out>
}, globalObjs=..., tagObjs=..., dataSegments=..., elemSegments=...) at /gecko-dev/js/src/wasm/WasmInstance.cpp:2549
#3  0x0000555558658e5c in js::WasmInstanceObject::create(JSContext*, RefPtr<js::wasm::Code const> const&, mozilla::Vector<RefPtr<js::wasm::DataSegment const>, 0ul, js::SystemAllocPolicy> const&, mozilla::Vector<js::wasm::ModuleElemSegment, 0ul, js::SystemAllocPolicy> const&, unsigned int, JS::Handle<JS::GCVector<js::WasmMemoryObject*, 0ul, js::SystemAllocPolicy> >, mozilla::Vector<RefPtr<js::wasm::Table>, 0ul, js::SystemAllocPolicy>&&, JS::GCVector<JSObject*, 0ul, js::SystemAllocPolicy> const&, mozilla::Vector<js::wasm::GlobalDesc, 0ul, js::SystemAllocPolicy> const&, JS::GCVector<js::wasm::Val, 0ul, js::SystemAllocPolicy> const&, JS::GCVector<js::WasmGlobalObject*, 0ul, js::SystemAllocPolicy> const&, JS::GCVector<js::WasmTagObject*, 0ul, js::SystemAllocPolicy> const&, JS::Handle<JSObject*>, mozilla::UniquePtr<js::wasm::DebugState, JS::DeletePolicy<js::wasm::DebugState> >)
     (cx=0x7ffff6235100, code=[(const js::wasm::Code *)] = {...}, dataSegments=..., elemSegments=..., instanceDataLength=0xa30, memories={
  vector = {
    <js::SystemAllocPolicy> = {
      <js::AllocPolicyBase> = {<No data fields>}, <No data fields>},
    members of mozilla::Vector<js::WasmMemoryObject*, 0ul, js::SystemAllocPolicy>:
    static kElemIsPod = 0x1,
    static kMaxInlineBytes = <optimized out>,
    static kInlineCapacity = 0x0,
    mBegin = 0x7ffff62254e0,
    mLength = 0x4,
    mTail = {
      <mozilla::Vector<js::WasmMemoryObject*, 0ul, js::SystemAllocPolicy>::CapacityAndReserved> = {
        mCapacity = 0x4,
        mReserved = 0x4
      }, <No data fields>},
    mEntered = 0x0,
    static sMaxInlineStorage = 0x0
  },
stemAllocPolicy> const&, JS::Handle<JS::GCVector<js::WasmMemoryObject*, 0ul, js::SystemAllocPolicy> >, JS::GCVector<js::WasmGlobalObject*, 0ul, js::Syste[47/1867$
icy> const&, JS::GCVector<js::WasmTagObject*, 0ul, js::SystemAllocPolicy> const&, mozilla::Vector<RefPtr<js::wasm::DataSegment const>, 0ul, js::SystemAllocPolicy>
 const&, mozilla::Vector<js::wasm::ModuleElemSegment, 0ul, js::SystemAllocPolicy> const&)
    (this=this@entry=0x7ffff626e400, cx=cx@entry=0x7ffff6235100, funcImports=..., globalImportValues=..., memories=memories@entry={
  vector = {
    <js::SystemAllocPolicy> = {
      <js::AllocPolicyBase> = {<No data fields>}, <No data fields>},
    members of mozilla::Vector<js::WasmMemoryObject*, 0ul, js::SystemAllocPolicy>:
    static kElemIsPod = 0x1,
    static kMaxInlineBytes = <optimized out>,
    static kInlineCapacity = 0x0,
    mBegin = 0x7ffff62254e0,
    mLength = 0x4,
    mTail = {
      <mozilla::Vector<js::WasmMemoryObject*, 0ul, js::SystemAllocPolicy>::CapacityAndReserved> = {
        mCapacity = 0x4,
        mReserved = 0x4
      }, <No data fields>},
    mEntered = 0x0,
    static sMaxInlineStorage = 0x0
  },
  static InlineLength = <optimized out>
}, globalObjs=..., tagObjs=..., dataSegments=..., elemSegments=...) at /gecko-dev/js/src/wasm/WasmInstance.cpp:2549
#3  0x0000555558658e5c in js::WasmInstanceObject::create(JSContext*, RefPtr<js::wasm::Code const> const&, mozilla::Vector<RefPtr<js::wasm::DataSegment const>, 0ul
, js::SystemAllocPolicy> const&, mozilla::Vector<js::wasm::ModuleElemSegment, 0ul, js::SystemAllocPolicy> const&, unsigned int, JS::Handle<JS::GCVector<js::WasmMe
moryObject*, 0ul, js::SystemAllocPolicy> >, mozilla::Vector<RefPtr<js::wasm::Table>, 0ul, js::SystemAllocPolicy>&&, JS::GCVector<JSObject*, 0ul, js::SystemAllocPo
licy> const&, mozilla::Vector<js::wasm::GlobalDesc, 0ul, js::SystemAllocPolicy> const&, JS::GCVector<js::wasm::Val, 0ul, js::SystemAllocPolicy> const&, JS::GCVect
or<js::WasmGlobalObject*, 0ul, js::SystemAllocPolicy> const&, JS::GCVector<js::WasmTagObject*, 0ul, js::SystemAllocPolicy> const&, JS::Handle<JSObject*>, mozilla:
:UniquePtr<js::wasm::DebugState, JS::DeletePolicy<js::wasm::DebugState> >)
     (cx=0x7ffff6235100, code=[(const js::wasm::Code *)] = {...}, dataSegments=..., elemSegments=..., instanceDataLength=0xa30, memories={
  vector = {
    <js::SystemAllocPolicy> = {
      <js::AllocPolicyBase> = {<No data fields>}, <No data fields>},
    members of mozilla::Vector<js::WasmMemoryObject*, 0ul, js::SystemAllocPolicy>:
    static kElemIsPod = 0x1,
    static kMaxInlineBytes = <optimized out>,
    static kInlineCapacity = 0x0,
    mBegin = 0x7ffff62254e0,
    mLength = 0x4,
    mTail = {
      <mozilla::Vector<js::WasmMemoryObject*, 0ul, js::SystemAllocPolicy>::CapacityAndReserved> = {
        mCapacity = 0x4,
        mReserved = 0x4
      }, <No data fields>},
    mEntered = 0x0,
    static sMaxInlineStorage = 0x0
  },
  static InlineLength = <optimized out>
}, tables=..., funcImports=..., globals=..., globalImportValues=..., globalObjs=..., tagObjs=..., proto=(JSObject * const) 0xeeade241208 [object Object] used_as_prototype, maybeDebug=[(js::wasm::DebugState *) 0x0]) at /gecko-dev/js/src/wasm/WasmJS.cpp:1761
#4  0x00005555586f6d7d in js::wasm::Module::instantiate(JSContext*, js::wasm::ImportValues&, JS::Handle<JSObject*>, JS::MutableHandle<js::WasmInstanceObject*>) const (this=0x7ffff62fc600, cx=0x7ffff6235100, imports=..., instanceProto=(JSObject * const) 0xeeade241208 [object Object] used_as_prototype, instance=0x0)
    at /gecko-dev/js/src/wasm/WasmModule.cpp:1016
#5  0x0000555558659c2c in js::WasmInstanceObject::construct(JSContext*, unsigned int, JS::Value*)
    (cx=cx@entry=0x7ffff6235100, argc=<optimized out>, vp=<optimized out>) at /gecko-dev/js/src/wasm/WasmJS.cpp:1824
#6  0x00005555572588b5 in CallJSNative(JSContext*, bool (*)(JSContext*, unsigned int, JS::Value*), js::CallReason, JS::CallArgs const&)
    (cx=cx@entry=0x7ffff6235100, native=native@entry=0x555558659890 <js::WasmInstanceObject::construct(JSContext*, unsigned int, JS::Value*)>, reason=reason@entry=js::CallReason::Call, args=...) at /gecko-dev/js/src/vm/Interpreter.cpp:481
#7  0x0000555557262a5d in CallJSNativeConstructor(JSContext*, bool (*)(JSContext*, unsigned int, JS::Value*), JS::CallArgs const&)
    (cx=cx@entry=0x7ffff6235100, native=0x555558659890 <js::WasmInstanceObject::construct(JSContext*, unsigned int, JS::Value*)>, args=...)
    at /gecko-dev/js/src/vm/Interpreter.cpp:497
#8  0x0000555557231f52 in InternalConstruct(JSContext*, js::AnyConstructArgs const&, js::CallReason)
    (cx=cx@entry=0x7ffff6235100, args=..., reason=reason@entry=js::CallReason::Call) at /gecko-dev/js/src/vm/Interpreter.cpp:703
#9  0x0000555557240470 in js::ConstructFromStack(JSContext*, JS::CallArgs const&, js::CallReason) (cx=0x7ffff6235100, args=..., reason=<optimized out>)
    at /gecko-dev/js/src/vm/Interpreter.cpp:750
#10 js::Interpret(JSContext*, js::RunState&) (cx=0x7ffff6235100, state=...) at /gecko-dev/js/src/vm/Interpreter.cpp:3161
#11 0x000055555722ff39 in MaybeEnterInterpreterTrampoline(JSContext*, js::RunState&) (cx=0x7ffff7c107d0, cx@entry=0x7ffff6235100, state=...)
    at /gecko-dev/js/src/vm/Interpreter.cpp:395
#12 0x000055555722fbef in js::RunScript(JSContext*, js::RunState&) (cx=cx@entry=0x7ffff6235100, state=...)
    at /gecko-dev/js/src/vm/Interpreter.cpp:453
#13 0x000055555723310c in js::ExecuteKernel(JSContext*, JS::Handle<JSScript*>, JS::Handle<JSObject*>, js::AbstractFramePtr, JS::MutableHandle<JS::Value>)
    (cx=cx@entry=0x7ffff6235100, script=script@entry=0xeeade268650, envChainArg=envChainArg@entry=(JSObject * const) 0xeeade23f038 [object LexicalEnvironment], evalInFrame=evalInFrame@entry=AbstractFramePtr ((js::InterpreterFrame *) 0x0) = {...}, result=result@entry=$JS::UndefinedValue())
    at /gecko-dev/js/src/vm/Interpreter.cpp:840
#14 0x0000555557233580 in js::Execute(JSContext*, JS::Handle<JSScript*>, JS::Handle<JSObject*>, JS::MutableHandle<JS::Value>)
    (cx=cx@entry=0x7ffff6235100, script=0xeeade268650, envChain=(JSObject * const) 0xeeade23f038 [object LexicalEnvironment], rval=rval@entry=$JS::UndefinedValue()) at /gecko-dev/js/src/vm/Interpreter.cpp:872
#15 0x00005555573ea232 in ExecuteScript(JSContext*, JS::Handle<JSObject*>, JS::Handle<JSScript*>, JS::MutableHandle<JS::Value>)
    (cx=cx@entry=0x7ffff6235100, envChain=(JSObject * const) 0xeeade23f038 [object LexicalEnvironment], script=0xeeade268650, rval=rval@entry=$JS::UndefinedValue()) at /gecko-dev/js/src/vm/CompilationAndEvaluation.cpp:494
#16 0x00005555573ea43c in JS_ExecuteScript(JSContext*, JS::Handle<JSScript*>) (cx=cx@entry=0x7ffff6235100, scriptArg=scriptArg@entry=0xeeade268650)
    at /gecko-dev/js/src/vm/CompilationAndEvaluation.cpp:518
#17 0x000055555717ac8f in RunFile(JSContext*, char const*, _IO_FILE*, CompileUtf8, bool, bool)
    (cx=0x7ffff6235100, filename=<optimized out>, file=<optimized out>, compileMethod=CompileUtf8::DontInflate, compileOnly=0x0, fullParse=<optimized out>)
    at /gecko-dev/js/src/shell/js.cpp:1194
#18 0x0000555557179fa9 in Process(JSContext*, char const*, bool, FileKind)
    (cx=cx@entry=0x7ffff6235100, filename=0x0, forceTTY=<optimized out>, kind=kind@entry=FileScript)
    at /gecko-dev/js/src/shell/js.cpp:1828
#19 0x000055555713587a in ProcessArgs(JSContext*, js::cli::OptionParser*) (cx=0x7ffff6235100, op=0x7fffffffde28)
    at /gecko-dev/js/src/shell/js.cpp:11255
#20 Shell(JSContext*, js::cli::OptionParser*) (cx=0x7ffff6235100, op=op@entry=0x7fffffffde28)
    at /gecko-dev/js/src/shell/js.cpp:11507
#21 0x000055555712dc62 in main(int, char**) (argc=<optimized out>, argv=0x7fffffffe098) at /gecko-dev/js/src/shell/js.cpp:12033
#22 0x00007ffff7a46083 in __libc_start_main () at /lib/x86_64-linux-gnu/libc.so.6
#23 0x0000555557122309 in _start ()
```

---

**Comment 1 — ydelendik@mozilla.com — 2024-06-20T21:18:19Z**

Minimal test case to reproduce the issue:

```
var wasm_code = wasmTextToBinary(`
(module
  (import "wasm:js-string" "charCodeAt"
    (func $charCodeAt (param externref i32) (result i32)))
  (table 1 1 funcref ref.func $charCodeAt)
)
`);
new WebAssembly.Instance(new WebAssembly.Module(wasm_code, { builtins: ["js-string"] }), {});
```

---

**Comment 2 — ydelendik@mozilla.com — 2024-06-21T18:54:17Z**

Created attachment 9409007
Bug 1903219 - Allow wasm builtin functions to be used in ref. r?rhunt

---

**Comment 3 — rhunt@eqrion.net — 2024-06-25T20:41:12Z**

This one requires the js-string-builtins feature to be enabled (which is not enabled by default anywhere yet).

When the feature is on, this could lead to an incorrect code pointer being stored in a wasm table, which could be called with `call_indirect`. The code pointer would be to the first thing in the wasm code segment, which can be a function with a different type than expected. This probably could be used to have type confusion.

---

**Comment 4 — ydelendik@mozilla.com — 2024-06-25T21:01:39Z**

Comment on attachment 9409007
Bug 1903219 - Allow wasm builtin functions to be used in ref. r?rhunt

### Security Approval Request
* **How easily could an exploit be constructed based on the patch?**: The patch is not directly exposing the issue, and exploit is possible only with builtin modules functionality explicitly enabled.
* **Do comments in the patch, the check-in comment, or tests included in the patch paint a bulls-eye on the security problem?**: No
* **Which branches (beta, release, and/or ESR) are affected by this flaw, and do the release status flags reflect this affected/unaffected state correctly?**: 
* **If not all supported branches, which bug introduced the flaw?**: None
* **Do you have backports for the affected branches?**: No
* **If not, how different, hard to create, and risky will they be?**: trivial
* **How likely is this patch to cause regressions; how much testing does it need?**: low: affects only disabled by default functionality, and firefox translation project
* **Is the patch ready to land after security approval is given?**: Yes
* **Is Android affected?**: Yes

---

**Comment 5 — dveditz@mozilla.com — 2024-06-25T22:47:20Z**

> * Which branches (beta, release, and/or ESR) are affected by this flaw, and do the release status flags reflect this affected/unaffected state correctly?:
> * If not all supported branches, which bug introduced the flaw?: None

There's no answer to the first question, and lacking an explicit answer, the second answer implies ESR _is_ affected. Yet I couldn't find any sign of JS string builtins on ESR. It looks like this feature was introduced in bug 1863794 (Firefox 122) so that's the earliest possible affected release.

---

**Comment 6 — dveditz@mozilla.com — 2024-06-25T23:37:37Z**

Comment on attachment 9409007
Bug 1903219 - Allow wasm builtin functions to be used in ref. r?rhunt

sec-approval+ = dveditz
Since this is disabled by default we don't need to request a beta uplift. It looks safe enough to take if you want to request it, but we're in the last week of betas so I don't know if the release managers will approve it.

---

**Comment 7 — pulsebot@bmo.tld — 2024-06-26T03:56:23Z**

Pushed by ydelendik@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/bbd9830539c6
Allow wasm builtin functions to be used in ref. r=rhunt

---

**Comment 8 — aryx.bugmail@gmx-topmail.de — 2024-06-26T12:24:01Z**

https://hg.mozilla.org/mozilla-central/rev/bbd9830539c6

---

**Comment 9 — dveditz@mozilla.com — 2024-07-02T18:48:28Z**

Thank you for your interest in the bug bounty program and for reporting this valid security bug. Unfortunately our bounty program does not include non-standard configurations, and in particular new features that are disabled even in "Nightly" because they are not ready to be exposed to public testing and the bounty program.
https://www.mozilla.org/en-US/security/bug-bounty/faq/#nondefault-pref

---

**Comment 10 — fufuyqqqqqq@gmail.com — 2024-07-03T20:31:25Z**

I believe that the vulnerability ultimately depends on the final rating according to the rules: the policy states that 'the reward is determinate on the sec rating assigned,' and whether it is a default configuration only affects the sec rating, which in turn impacts the bounty. Therefore, based on the policy description, I think this vulnerability complies with the rules.

---

**Comment 11 — dveditz@mozilla.com — 2024-07-11T00:32:28Z**

The decision by the bounty committee was not arbitrary, and is line with the FAQ answer I referenced in comment 9. The wasm_js_string_builtins feature is in development and not ready for testing; it is currently off-limits for the bug bounty.

> If the preference is exposed via our Preferences Page; we consider that to be a supported configuration for Firefox. If the preference is enabled by default in a current Firefox channel (e.g. Nightly or Beta) it is also considered supported. If the preference must be configured via about:config or requires other non-standard Operating System configuration, that is typically not considered a supported configuration

It's not fair to the developers or our internal testers and QA team to call "open season" on unfinished features when we know many of these bugs will eventually be found and fixed by our own internal processes. It's also not fair to bounty hunters to let them put in lots of work and then arbitrarily say "sorry, too early for feature X" without warning. So we've tried to draw clear lines with the guidelines above. Sometimes we might be open to bug bounty hunting on specific disabled features, but to avoid disappointment you should ask us first.
