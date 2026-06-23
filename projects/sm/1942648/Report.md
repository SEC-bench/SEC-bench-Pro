# Assertion failure: ins->type() == MIRType::Int32, at js/src/jit/Lowering.cpp:2100

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1942648
Component: JavaScript Engine: JIT
Bounty: (unknown)
Date: 2025-01-20T15:23:32Z
Keywords: assertion, csectype-jit, regression, sec-high, testcase

The following testcase crashes on mozilla-central revision 20250120-7a6d654e992e (debug build, run with --fuzzing-safe --ion-offthread-compile=off --fast-warmup):

    function testMathyFunction(f, inputs) {
        for (var j = 0; j < inputs.length; ++j) {
            for (var k = 0; k < inputs.length; ++k) {
                f(inputs[j], inputs[k])
            }
        }
    }
    mathy0 = function(x, y) {
        Math.pow((Math.sign((+y)) >>> 0))
    };
    mathy2 = function(x, y) {
        mathy0(2 ** 53, (x | 0) ? (+x) : x) ? (y >>> 0) : (x >>> 0);
    };
    testMathyFunction(mathy2, [Math.PI, 0 / 0, 1.7976931348623157e308]);
    mathy4 = function(x, y) {
        y | 0, (2 ** 53) ? Math.fround(mathy2(x, x)) : 1.7976931348623157e308 | 0;
    };
    testMathyFunction(mathy4, [, '', '0', /0/, '/0/', ({}), createIsHTMLDDA()]);


Backtrace:

    received signal SIGSEGV, Segmentation fault.
    #0  0x000055555813da1d in js::jit::LIRGenerator::visitSign(js::jit::MSign*) ()
    #1  0x000055555818d270 in js::jit::LIRGenerator::visitInstruction(js::jit::MInstruction*) ()
    #2  0x000055555818da5f in js::jit::LIRGenerator::visitBlock(js::jit::MBasicBlock*) ()
    #3  0x000055555818de65 in js::jit::LIRGenerator::generate() ()
    #4  0x0000555557ffed69 in js::jit::GenerateLIR(js::jit::MIRGenerator*) ()
    #5  0x0000555557fff518 in js::jit::CompileBackEnd(js::jit::MIRGenerator*, js::jit::WarpSnapshot*) ()
    #6  0x000055555800105f in js::jit::Compile(JSContext*, JS::Handle<JSScript*>, js::jit::BaselineFrame*, unsigned char*) ()
    #7  0x0000555558001d59 in IonCompileScriptForBaseline(JSContext*, js::jit::BaselineFrame*, unsigned char*) ()
    #8  0x000029b70c094f16 in ?? ()
    [...]
    #13 0x00007fffffffcba8 in ?? ()
    #14 0x0000555557c7b007 in js::jit::AssertPropertyLookup(js::NativeObject*, JS::PropertyKey, unsigned int) ()
    Backtrace stopped: previous frame inner to this frame (corrupt stack?)
    rax	0x55555580c8cc	93824995084492
    rbx	0x7ffff4671af8	140737293785848
    rcx	0x555558a764d0	93825047946448
    rdx	0x1	1
    rsi	0x0	0
    rdi	0x7ffff7bee7d0	140737349871568
    rbp	0x7fffffffb420	140737488335904
    rsp	0x7fffffffb3e0	140737488335840
    r8	0x0	0
    r9	0x3	3
    r10	0x0	0
    r11	0x0	0
    r12	0x7ffff4672588	140737293788552
    r13	0x7ffff46709d0	140737293781456
    r14	0x7fffffffb4f0	140737488336112
    r15	0x7ffff4671af8	140737293785848
    rip	0x55555813da1d <js::jit::LIRGenerator::visitSign(js::jit::MSign*)+749>
    => 0x55555813da1d <_ZN2js3jit12LIRGenerator9visitSignEPNS0_5MSignE+749>:	movl   $0x834,0x0
       0x55555813da28 <_ZN2js3jit12LIRGenerator9visitSignEPNS0_5MSignE+760>:	callq  0x555556f345e0 <abort>


Marking s-s due to JIT assert that is known to indicate potential type confusion.

---

**Comment 1 — choller@mozilla.com — 2025-01-20T15:23:36Z**

Created attachment 9460547
Detailed Crash Information

---

**Comment 2 — choller@mozilla.com — 2025-01-20T15:23:38Z**

Created attachment 9460548
Testcase

---

**Comment 3 — bugmon@mozilla.com — 2025-01-20T16:46:10Z**

Verified bug as reproducible on mozilla-central 20250120104134-7a6d654e992e.
The bug appears to have been introduced in the following build range:
> Start: b32e47b8c156a7bb191fe4bab8aec833d670f8b5 (20250117120219)
> End: 3188e322f7981067e3e29c0acdf41023f3853193 (20250117132218)
> Pushlog: https://hg.mozilla.org/integration/autoland/pushloghtml?fromchange=b32e47b8c156a7bb191fe4bab8aec833d670f8b5&tochange=3188e322f7981067e3e29c0acdf41023f3853193

---

**Comment 4 — release-mgmt-account-bot@mozilla.tld — 2025-01-20T21:42:46Z**

:anba, since you are the author of the regressor, bug 1941826, could you take a look?

For more information, please visit [BugBot documentation](https://wiki.mozilla.org/BugBot#needinfo_regression_author.py).

---

**Comment 5 — andrebargull@googlemail.com — 2025-01-21T08:52:42Z**

Created attachment 9460650
Bug 1942648: Support MSign with Int32 input and Double output. r=jandem!

---

**Comment 6 — andrebargull@googlemail.com — 2025-01-21T11:20:51Z**

*** Bug 1942728 has been marked as a duplicate of this bug. ***

---

**Comment 7 — continuation@gmail.com — 2025-01-22T00:49:18Z**

What are the security implications of this issue? Could it cause type confusion as suggested in comment 0? Thanks.

---

**Comment 8 — andrebargull@googlemail.com — 2025-01-22T10:12:27Z**

There are two bad things happening here:
1. We allocate an float output register, but end up writing to an unrelated general purpose register. The written value is one of [-1, 0, 1].
2. Because we write to a GPR, the allocated output float register contains its previous value, which can later be read out by any following code.

---

**Comment 9 — pulsebot@bmo.tld — 2025-01-22T10:18:13Z**

Pushed by andre.bargull@gmail.com:
https://hg.mozilla.org/integration/autoland/rev/d72274278380
Support MSign with Int32 input and Double output. r=jandem

---

**Comment 10 — continuation@gmail.com — 2025-01-22T14:15:32Z**

Thanks. 1 doesn't sound easily exploitable (presumably once the register is allocated it won't be reused), but 2 does sound like a type confusion (consistent with the assertion) so I'll mark it sec-high.

---

**Comment 11 — aryx.bugmail@gmx-topmail.de — 2025-01-22T16:54:12Z**

https://hg.mozilla.org/mozilla-central/rev/d72274278380

---

**Comment 12 — bugmon@mozilla.com — 2025-01-23T00:35:11Z**

Verified bug as fixed on rev mozilla-central 20250122165122-d72274278380.
Removing bugmon keyword as no further action possible.  Please review the bug and re-add the keyword for further analysis.
