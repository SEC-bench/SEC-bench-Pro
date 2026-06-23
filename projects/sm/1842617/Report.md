# Crash [@ js::NativeObject::allocDictionarySlot(JSContext*, JS::Handle<js::NativeObject*>, unsigned int*)] or Assertion failure: isInt32(), at js/Value.h:914

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1842617
Component: JavaScript Engine: JIT
Bounty: (unknown)
Date: 2023-07-10T15:02:01Z
Keywords: assertion, crash, csectype-jit, regression, sec-high, testcase

The following testcase crashes on mozilla-central revision 20230710-aaa3698312c5 (opt build, run with --fuzzing-safe --cpu-count=2 --ion-offthread-compile=off --baseline-eager):

    loadFile(``);
    loadFile(``);
    loadFile(`
      var lfClass = new LFC1695437225();
    `);
    loadFile(`
      (function(global) {
        global.assertDeepEq = (function(){})();
      })(this);
    `);
    loadFile(`
      log = "";
    `);
    loadFile(`
      for (let invalid of (log("lhs before name a"), "a")) {}
    `);
    loadFile(`}`);
    loadFile(`
      (function(global) {
        global.completesNormally = function completesNormally(code) {}
      })(this);
    `);
    loadFile(`
      for (let order = 0; order < 16; order++) {
        gc();
        setMark = undefined;
      }
    `);
    loadFile(`
      function f80() {}
      gc();
      delete Math
    `);
    loadFile(`
      for (const name of ["x", "y"]) {
        present = undefined;
        this[name] = function() {};
      }
    `);
    function loadFile(lfVarx) {
      try {
        evaluate(lfVarx);
      } catch (lfVare) {}
      Math = undefined;
    }


Backtrace:

    received signal SIGSEGV, Segmentation fault.
    #0  0x000055555620fc65 in js::NativeObject::allocDictionarySlot(JSContext*, JS::Handle<js::NativeObject*>, unsigned int*) ()
    #1  0x0000555555daf5c0 in js::NativeDefineProperty(JSContext*, JS::Handle<js::NativeObject*>, JS::Handle<JS::PropertyKey>, JS::Handle<JS::PropertyDescriptor>, JS::ObjectOpResult&) ()
    #2  0x00005555562108bd in js::SetPropertyByDefining(JSContext*, JS::Handle<JS::PropertyKey>, JS::Handle<JS::Value>, JS::Handle<JS::Value>, JS::ObjectOpResult&) ()
    #3  0x0000555556212e0b in bool SetNonexistentProperty<(js::QualifiedBool)0>(JSContext*, JS::Handle<js::NativeObject*>, JS::Handle<JS::PropertyKey>, JS::Handle<JS::Value>, JS::Handle<JS::Value>, JS::ObjectOpResult&) ()
    #4  0x0000555556212a50 in bool js::NativeSetProperty<(js::QualifiedBool)0>(JSContext*, JS::Handle<js::NativeObject*>, JS::Handle<JS::PropertyKey>, JS::Handle<JS::Value>, JS::Handle<JS::Value>, JS::ObjectOpResult&) ()
    #5  0x00005555561a3e00 in js::SetNameOperation(JSContext*, JSScript*, unsigned char*, JS::Handle<JSObject*>, JS::Handle<JS::Value>) ()
    #6  0x0000555555f2492c in js::jit::DoSetPropFallback(JSContext*, js::jit::BaselineFrame*, js::jit::ICFallbackStub*, JS::Value*, JS::Handle<JS::Value>, JS::Handle<JS::Value>) ()
    #7  0x00000c1818f3c8ce in ?? ()
    [...]
    #44 0x00007fffffffc120 in ?? ()
    #45 0x0000555556053c02 in js::jit::MaybeEnterJit(JSContext*, js::RunState&) ()
    Backtrace stopped: previous frame inner to this frame (corrupt stack?)
    rax	0x2e4000e8	775946472
    rbx	0x7fffffffb8f8	140737488337144
    rcx	0x3b649ee67080	65303348670592
    rdx	0x800165840710	140743486474000
    rsi	0x8	8
    rdi	0x800165840710	140743486474000
    rbp	0x7fffffffb710	140737488336656
    rsp	0x7fffffffb6e0	140737488336608
    r8	0x7fffffffb8f8	140737488337144
    r9	0x7fffffffb8f8	140737488337144
    r10	0x3b649ee2cd60	65303348432224
    r11	0x3b649ee3c3e0	65303348495328
    r12	0x7fffffffb7a4	140737488336804
    r13	0x3b649ee3c400	65303348495360
    r14	0x132	306
    r15	0x7ffff3e20100	140737285062912
    rip	0x55555620fc65 <js::NativeObject::allocDictionarySlot(JSContext*, JS::Handle<js::NativeObject*>, unsigned int*)+229>
    => 0x55555620fc65 <_ZN2js12NativeObject19allocDictionarySlotEP9JSContextN2JS6HandleIPS0_EEPj+229>:	mov    (%rdx),%edx
       0x55555620fc67 <_ZN2js12NativeObject19allocDictionarySlotEP9JSContextN2JS6HandleIPS0_EEPj+231>:	mov    %edx,0x78(%rcx)


Likely a JIT bug but GC seems also involved - the test started to reduce much better with --baseline-eager but I couldn't find any other options that would make it reduce further. S-s since this is a non-zero JIT crash.

---

**Comment 1 — choller@mozilla.com — 2023-07-10T15:02:05Z**

Created attachment 9343092
Detailed Crash Information

---

**Comment 2 — choller@mozilla.com — 2023-07-10T15:02:07Z**

Created attachment 9343093
Testcase

---

**Comment 3 — continuation@gmail.com — 2023-07-10T15:05:54Z**

I'll assume the worst and mark this sec-high.

---

**Comment 4 — bugmon@mozilla.com — 2023-07-10T16:23:44Z**

Verified bug as reproducible on mozilla-central 20230710155516-ce73b773910f.
Unable to bisect testcase (Unable to launch the start build!):
> Start: f4a77bb114fa619442cf5d7448204e4ae0b4e62d (20220711065843)
> End: aaa3698312c56a08a7b405178ee462fe3c2a30e7 (20230710094014)
> BuildFlags: BuildFlags(asan=False, tsan=False, debug=True, fuzzing=False, coverage=False, valgrind=False, no_opt=False, fuzzilli=False, nyx=False)

---

**Comment 5 — iireland@mozilla.com — 2023-07-10T18:38:58Z**

Good find. This is a regression from bug 1837620.

Here's a more reduced version that fails with `--baseline-eager`:

```
function foo(src) {
  try {
    evaluate(src);
  } catch {}
  Math = undefined;
}

foo(``);
foo(``);
foo(`var a = 0;`);
foo(`var b = 0;`);
foo(`var c = 0;`);
foo(`var d = 0;`);
foo(`undef();`);
foo(`{`);
foo(`
     gc();
     e = 0;
     gc();
`);
foo(`
     var f = 0;
     gc();
     delete Math;
`);
foo(`
     g = undefined;
`);
```
 A lot of this testcase is just mystical incantations to get the GC behaviour to line up right. The important lines are `Math = undefined` and `delete Math`. We start by calling `foo` and defining a bunch of new global variables. This means we reach `Math = undefined` with a variety of global shapes. We try attaching at least seven stubs of the form `GuardToObject/GuardShape/SetDynamicSlot/ReturnFromIC`, with seven different global shapes. On the seventh, we do stub folding, replacing it with a single `GuardToObject/GuardMultipleShapes/SetDynamicSlot/ReturnFromIC` stub with a list of shape pointers.

We trigger GC a few times, each time collecting most/all of the shape list. Eventually we reach a point where the shape list is empty following a GC, at which point we delete `Math` and turn the global into a dictionary shape. Critically: the dictionary shape that we allocate here is allocated at the same address as the shape that *was* at the beginning of the shape list before the most recent GC. We add the slot that was previously storing `Math` to the dictionary shape's free list, and store a private uint32 in that slot..

We return to the body of `foo` and call into the folded `Math = undefined` IC. The shape list is empty. However, this was not possible in the original implementation of stub folding. We were previously guaranteed that there would be at least one element in the list, so in the [masm implementation of branchTestShapeList](https://searchfox.org/mozilla-central/rev/6220909421e5cdb2e706a87f77ba7c6f4f21e4d0/js/src/jit/MacroAssembler.cpp#4458-4482), we generate the equivalent of a do-while loop, which will only check the condition at the end. We compare the first element of the shape list (an old dead shape) with the current shape of the global. Because of the collision between the addresses of the old shape and the new dictionary shape, this check passes. We go ahead and clobber the free list value that was being stored in that slot.

When we try to allocate a new slot in the object, we explode.

The best fix is probably to rewrite branchTestShapeList to check for an empty list. We could also consider zeroing out deleted shapes in [ShapeListObject::traceWeak](https://searchfox.org/mozilla-central/source/js/src/jit/BaselineCacheIRCompiler.cpp#2139), but I think that's too fancy to avoid generating one branch.

Sec-high seems reasonable to me.

---

**Comment 6 — release-mgmt-account-bot@mozilla.tld — 2023-07-10T18:42:12Z**

:jonco, since you are the author of the regressor, bug 1837620, could you take a look? Also, could you set the severity field?

For more information, please visit [BugBot documentation](https://wiki.mozilla.org/BugBot#needinfo_regression_author.py).

---

**Comment 7 — sdetar@mozilla.com — 2023-07-10T18:57:56Z**

Setting severity to S2 for now since Iain suggests Sec-High is reasonable in comment 5.

---

**Comment 8 — iireland@mozilla.com — 2023-07-10T19:08:19Z**

Created attachment 9343129
Bug 1842617: Check for empty shape list in branchTestObjShapeList r=jonco

---

**Comment 9 — iireland@mozilla.com — 2023-07-11T16:59:09Z**

*** Bug 1842847 has been marked as a duplicate of this bug. ***

---

**Comment 10 — release-mgmt-account-bot@mozilla.tld — 2023-07-11T17:40:58Z**

Copying crash signatures from duplicate bugs.

---

**Comment 11 — pulsebot@bmo.tld — 2023-07-12T19:45:00Z**

Pushed by iireland@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/5af60a416884
Check for empty shape list in branchTestObjShapeList r=jonco

---

**Comment 12 — aryx.bugmail@gmx-topmail.de — 2023-07-13T12:50:35Z**

https://hg.mozilla.org/mozilla-central/rev/5af60a416884

---

**Comment 13 — iireland@mozilla.com — 2023-07-13T16:02:19Z**

*** Bug 1843280 has been marked as a duplicate of this bug. ***

---

**Comment 14 — bugmon@mozilla.com — 2023-07-13T16:20:55Z**

Verified bug as fixed on rev mozilla-central 20230713091748-211b29e869ca.
Removing bugmon keyword as no further action possible.  Please review the bug and re-add the keyword for further analysis.
