# Assertion failure: aIndex < mLength, at mozilla/Vector.h:585 with OOM in [@ js::wasm::BaseCompiler::loadAllocSiteInstanceData]

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1954042
Component: JavaScript: WebAssembly
Bounty: (unknown)
Date: 2025-03-14T09:52:37Z
Keywords: assertion, csectype-bounds, regression, sec-high, testcase
See Also:
- https://bugzilla.mozilla.org/show_bug.cgi?id=1445260

The attached testcase crashes on mozilla-central revision 20250312-bec9c7796872 (build with debug, run with --fuzzing-safe --cpu-count=2 --ion-offthread-compile=off). 

Backtrace:

```
    received signal SIGSEGV, Segmentation fault.
    #0  0x0000555558186e1b in js::wasm::BaseCompiler::loadAllocSiteInstanceData(unsigned int) ()
    #1  0x0000555558188c4b in bool js::wasm::BaseCompiler::emitStructAlloc<false>(unsigned int, js::wasm::RegRef*, bool*, js::wasm::RegPtr*, unsigned int) ()
    #2  0x00005555581880f9 in js::wasm::BaseCompiler::emitStructNew() ()
    #3  0x000055555819e4d4 in js::wasm::BaseCompiler::emitBody() ()
    #4  0x00005555581c226d in js::wasm::BaselineCompileFunctions(js::wasm::CodeMetadata const&, js::wasm::CompilerEnvironment const&, js::LifoAlloc&, mozilla::Vector<js::wasm::FuncCompileInput, 8ul, js::SystemAllocPolicy> const&, js::wasm::CompiledCode*, mozilla::UniquePtr<char [], JS::FreePolicy>*) ()
    #5  0x000055555824a358 in ExecuteCompileTask(js::wasm::CompileTask*, mozilla::UniquePtr<char [], JS::FreePolicy>*) ()
    #6  0x000055555824bb27 in js::wasm::ModuleGenerator::finishFuncDefs() ()
    #7  0x00005555582210eb in bool DecodeCodeSection<js::wasm::Decoder, js::wasm::ModuleGenerator>(js::wasm::CodeMetadata const&, js::wasm::Decoder&, js::wasm::ModuleGenerator&) ()
    #8  0x0000555558220abd in js::wasm::CompileBuffer(js::wasm::CompileArgs const&, js::wasm::ShareableVector<unsigned char, 0ul, js::SystemAllocPolicy> const&, mozilla::UniquePtr<char [], JS::FreePolicy>*, mozilla::Vector<mozilla::UniquePtr<char [], JS::FreePolicy>, 0ul, js::SystemAllocPolicy>*, JS::OptimizedEncodingListener*) ()
    #9  0x0000555558281504 in js::WasmModuleObject::construct(JSContext*, unsigned int, JS::Value*) ()
    #10 0x00000cc49f416279 in ?? ()
    #11 0x0000000000000000 in ?? ()
    rax	0x0	0
    rbx	0x7fffffff8560	140737488323936
    rcx	0x249	585
    rdx	0x1	1
    rsi	0x0	0
    rdi	0x7ffff7bee7d0	140737349871568
    rbp	0x7fffffff8200	140737488323072
    rsp	0x7fffffff81c0	140737488323008
    r8	0x0	0
    r9	0x3	3
    r10	0x0	0
    r11	0x0	0
    r12	0x7fffffff82d0	140737488323280
    r13	0x7fffffff8560	140737488323936
    r14	0x1	1
    r15	0x0	0
    rip	0x555558186e1b <js::wasm::BaseCompiler::loadAllocSiteInstanceData(unsigned int)+571>
    => 0x555558186e1b <_ZN2js4wasm12BaseCompiler25loadAllocSiteInstanceDataEj+571>:	mov    %rcx,(%rax)
       0x555558186e1e <_ZN2js4wasm12BaseCompiler25loadAllocSiteInstanceDataEj+574>:	callq  0x555556f47b70 <abort>
```


Marking s-s due to potential out-of-bounds.

---

**Comment 1 — choller@mozilla.com — 2025-03-14T09:52:42Z**

Created attachment 9472013
Detailed Crash Information

---

**Comment 2 — choller@mozilla.com — 2025-03-14T09:52:43Z**

Created attachment 9472014
Testcase

---

**Comment 3 — continuation@gmail.com — 2025-03-14T13:32:54Z**

I'll mark this sec-moderate because of the OOM requirement, but maybe sec-high is better?

---

**Comment 4 — choller@mozilla.com — 2025-03-14T14:46:03Z**

sec bugs are usually not sec-moderate because of OOM, we know that these can be exploited somewhat reliably.

---

**Comment 5 — ydelendik@mozilla.com — 2025-03-14T16:52:30Z**

Created attachment 9472155
Bug 1954042 - Check OOM condition after readAllocSiteIndex(). r?rhunt

---

**Comment 6 — rhunt@eqrion.net — 2025-03-14T17:47:41Z**

This is a recent regression from bug 1940320 and is only in nightly. I'm not sure how exploitable it is. It relies on an OOM happening during a baseline function compilation, and in that condition we will generate an incorrect index into a vector and later use it here [1]. The value we write is a code offset that's maybe user controllable? We we only ever write it one past the end of the vector, because we use the vector length to get the index and once we OOM that won't grow anymore [2]. The entire function will be thrown away at the end when we observe that masm had an OOM, so none of the code we generate will be runnable.

With all of that, I think it's unlikely this could be easily exploited.

[1] https://searchfox.org/mozilla-central/rev/5c2888b35d56928d252acf84e8816fa89a8a6a61/js/src/wasm/WasmBaselineCompile.cpp#7372
[2] https://searchfox.org/mozilla-central/rev/5c2888b35d56928d252acf84e8816fa89a8a6a61/js/src/wasm/WasmBaselineCompile.cpp#7378

---

**Comment 7 — pulsebot@bmo.tld — 2025-03-14T20:44:46Z**

Pushed by ydelendik@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/35f957ec5175
Check OOM condition after readAllocSiteIndex(). r=rhunt

---

**Comment 8 — ryanvm@gmail.com — 2025-03-15T21:19:57Z**

https://hg.mozilla.org/mozilla-central/rev/35f957ec5175

---

**Comment 9 — bugmon@mozilla.com — 2025-09-05T08:16:55Z**

Verified bug as fixed on rev mozilla-central 20250315210952-163fa0640eef.
Removing bugmon keyword as no further action possible.  Please review the bug and re-add the keyword for further analysis.
