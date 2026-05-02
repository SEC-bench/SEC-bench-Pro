# [WASM-GC] Incorrect cast optimization with i31ref

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1851569
Component: JavaScript: WebAssembly
Bounty: (unknown)
Date: 2023-09-05T09:36:51Z
Keywords: crash, regression, sec-high, testcase

The following testcase crashes on mozilla-central revision 20230903-39747a728e31 (debug build, run with --fuzzing-safe --ion-offthread-compile=off --wasm-gc):

    function a(b) {
      binary = wasmTextToBinary(b)
      c = new WebAssembly.Module(binary)
      return new WebAssembly.Instance(c)
    }
    d = `
      (module (type $e (struct i8 i8 i8 i8))
        (func (export "readU8hi1") (param $f eqref) (result i32) (struct.get_u $e 3 (ref.cast (ref $e) local.get $f)))
      )
    `;
    a(d).exports.readU8hi1(0);


Backtrace:

    received signal SIGSEGV, Segmentation fault.
    #0  0x000020471dc80044 in ?? ()
    #1  0x00007fffffffcac0 in ?? ()
    #2  0x000020471dc800c7 in ?? ()
    #3  0x00007ffff2d9a0e0 in ?? ()
    #4  0x00005555576995c1 in js::CheckContextLocal::check() const ()
    Backtrace stopped: previous frame inner to this frame (corrupt stack?)
    rax	0x7ffff3e06b00	140737284958976
    rbx	0x7fffffffcbd8	140737488341976
    rcx	0x7fffffffcf01	140737488342785
    rdx	0x1	1
    rsi	0x7ffff2d9a0e0	140737267736800
    rdi	0x1	1
    rbp	0x7fffffffca60	140737488341600
    rsp	0x7fffffffca60	140737488341600
    r8	0xffffd55555984a38	-46912491730376
    r9	0xffffd55555984a28	-46912491730392
    r10	0x7fffffffcf18	140737488342808
    r11	0x7c00f7f	130027391
    r12	0x7fffffffcad8	140737488341720
    r13	0x7ffff2d9a0e0	140737267736800
    r14	0x7ffff2d9a0e0	140737267736800
    r15	0x0	0
    rip	0x20471dc80044	35489814413380
    => 0x20471dc80044:	mov    0x8(%rdi),%rcx
       0x20471dc80048:	mov    0x10(%rcx),%rcx


I don't know if this one is on file already but it has been bothering me for a while with missing testcases and the stack has barely anything to match on so would be good to get this out of the way.

---

**Comment 1 — choller@mozilla.com — 2023-09-05T09:36:54Z**

Created attachment 9351543
Detailed Crash Information

---

**Comment 2 — choller@mozilla.com — 2023-09-05T09:36:56Z**

Created attachment 9351544
Testcase

---

**Comment 3 — bugmon@mozilla.com — 2023-09-05T16:23:10Z**

Unable to reproduce bug 1851569 using build mozilla-central 20230903210251-39747a728e31.  Without a baseline, bugmon is unable to analyze this bug.
Removing bugmon keyword as no further action possible.  Please review the bug and re-add the keyword for further analysis.

---

**Comment 4 — jseward@acm.org — 2023-09-06T13:20:03Z**

Using GDB, I followed compilation into MacroAssembler::branchWasmRefIsSubtypeAny
[1] but failed to make any progress due to insufficient understanding of how
subtype checking works.  I established only the following:

  sourceType.isAnyHierarchy() = true
  destType.isAnyHierarchy() = true

so they are at least in the same hierarchy, and

  sourceType.isEq = true
  sourceType.isI31/isStruct/isArray/isNone = false

  destType.isNullable/isEq/isArray/isStruct/isI31 = false

So it seems like `sourceType` is EqRef -- which makes sense given the test
case -- but `destType` isn't further identified.  I guess it is a concrete
struct type, and that doesn't show up as `true` for `isStruct()`.

I did wonder if the clause guarded by `if (destType.isI31()) {` should be moved
down the function.  It seems like we have a sequence of checks that work their
way down from the top of the hierarchy, beginning `if (destType.isNone()) {`,
but once it gets past the `isAny` check, it "jumps over" the Eq case and
directly does an I31 check.  The Eq check is further down.  Should the I31
check be pushed down to the same level as the array/struct handling, given that
I31, Array and Struct are siblings in the hierarchy, and all have Eq as a
parent?

[1] https://searchfox.org/mozilla-central/source/js/src/jit/MacroAssembler.cpp#5634

---

**Comment 5 — bvisness@mozilla.com — 2023-09-06T14:55:39Z**

This module contains a cast that should fail in this case. Reformatting for clarity:

```
(module
  (type $e (struct i8 i8 i8 i8))
  (func (export "readU8hi1") (param $f eqref) (result i32)
    local.get $f
    ref.cast (ref $e)
    struct.get_u $e 3
  )
)
```

We can see that this function simply gets a param of type `eqref` (i.e. `(ref null eq)`) casts it to `(ref $e)` (a struct with four `i8` fields) and gets a field from it.

`eq` and `$e` are both part of the `any` hierarchy, so the cast instruction itself should validate. Furthermore, `(ref $e)` is a subtype of `(ref null eq)`, so it's possible that this could succeed. (You could imagine passing in an instance of `$e` for the `eqref` param.) However in this case we're clearly not doing that, we're passing a JS number, which I believe is converted to an i31 value ([here](https://searchfox.org/mozilla-central/source/js/src/wasm/WasmAnyRef.cpp#79-82), [here](https://searchfox.org/mozilla-central/source/js/src/wasm/WasmAnyRef.h#129)).

The source and dest types seems like they are being tracked correctly. You are correct that `destType` is a concrete type and therefore `isTypeRef` instead of `isStruct`.

After looking at the code, I think the problem lies [here](https://searchfox.org/mozilla-central/source/js/src/jit/MacroAssembler.cpp#5684). This code attemps to suppress some checks based on assumptions that are no longer valid. Basically, the assumption is that any non-null value that is a subtype of `eq` _must_ be a GC object. This is no longer the case, because i31. It should be valid to remove that guard entirely, or perhaps to change it to the following, which is more explicit about the assumption being made:

```
  if (
    !wasm::RefType::isSubTypeOf(sourceType, wasm::RefType::struct_())
    && !wasm::RefType::isSubTypeOf(sourceType, wasm::RefType::array())
  )
```

To be extra clear - the `if (destType.isI31())` check is not relevant here because the dest type is not i31. However, i31 values should be caught by the "is it a GC object" path, but due to an outdated assumption, i31 values can slip through and be accessed as if they were a struct or array.

I've attached a patch that may fix the issue. It also includes updates to `cast-abstract.js` that might turn up other errors while you're in there. (Tests seem to be failing for validation reasons that seem incorrect to me.) Of course, there's no need to include these test changes in your patch, but it might be valuable for preemptively finding other casting bugs.

---

**Comment 6 — bvisness@mozilla.com — 2023-09-06T14:56:11Z**

Created attachment 9351806
bug1851569-bvisness.diff

---

**Comment 7 — bvisness@mozilla.com — 2023-09-06T15:00:38Z**

Tangentially related - I see the function has `(result i32)` but the struct field is of type `i8`. I'm not sure this should validate, although it's not related to this segfault.

---

**Comment 8 — jseward@acm.org — 2023-09-06T16:59:46Z**

@bvisness thanks for the comment 6 patch.  Applying just the C++ parts fixes
the test case here (so it fails with "RuntimeError: bad cast") and does not 
cause any other failures in jit_tests (wasm/).  Applying also the JS part causes
`cast-abstract.js` to fail, as you observe.

---

**Comment 9 — bvisness@mozilla.com — 2023-09-13T16:28:55Z**

Created attachment 9352946
Bug 1851569: Add i31 to ref.cast test suite. r=jseward


This thoroughly tests i31's interaction with other types, and fixes a couple subtle bugs. For example, casting an anyref to an eqref was incorrectly failing if the value was i31.

---

**Comment 10 — pulsebot@bmo.tld — 2023-09-13T21:08:48Z**

Pushed by bvisness@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/a654205d8470
Add i31 to ref.cast test suite. r=jseward

---

**Comment 11 — aryx.bugmail@gmx-topmail.de — 2023-09-14T08:05:34Z**

https://hg.mozilla.org/mozilla-central/rev/a654205d8470

---

**Comment 12 — bvisness@mozilla.com — 2023-09-14T13:10:53Z**

*** Bug 1852995 has been marked as a duplicate of this bug. ***

---

**Comment 13 — dveditz@mozilla.com — 2024-04-29T06:35:37Z**

Bulk-unhiding security bugs fixed in Firefox 119-121 (Fall 2023). Use "moo-doctrine-subsidy" to filter
