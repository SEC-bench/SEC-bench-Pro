# AddressSanitizer: use-after-poison on js::wasm::AnyRef::isNull

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1885829
CVE: CVE-2024-3856
Component: JavaScript: WebAssembly
Bounty: (unknown)
Date: 2024-03-18T07:26:18Z
Keywords: csectype-uaf, regression, reporter-external, sec-high

Created attachment 9391684
poc.js

## Reproduce
1. Clone the Firefox mirror from https://github.com/mozilla/gecko-dev
2. Run build command `mkdir fuzzbuild_OPT.OBJ && cd fuzzbuild_OPT.OBJ && ../configure --enable-address-sanitizer --disable-jemalloc --enable-debug --enable-optimize --disable-shared-js --enable-application=js --enable-gczeal && make -j64` in the js/src directory of the firefox checkout
3. Run poc: `js/src/fuzzbuild_OPT.OBJ/dist/bin/js poc.js`

## ASAN LOG
```
==3045212==ERROR: AddressSanitizer: use-after-poison on address 0x24cc639fffa8 at pc 0x55c92c706f47 bp 0x7ffd627ccce0 sp 0x7ffd627cccd8
READ of size 8 at 0x24cc639fffa8 thread T0
/home/test/.mozbuild/clang/bin/llvm-symbolizer: error: '[anon:js-executable-memory]': No such file or directory
    #0 0x55c92c706f46 in js::wasm::AnyRef::isNull() const /home/test/gecko-dev/js/src/wasm/WasmAnyRef.h:290:32
    #1 0x55c92c706f46 in js::wasm::AnyRef::isGCThing() const /home/test/gecko-dev/js/src/wasm/WasmAnyRef.h:291:36
    #2 0x55c92c706f46 in js::gc::StoreBuffer::WasmAnyRefEdge::deref() const /home/test/gecko-dev/js/src/gc/StoreBuffer.h:453:20
    #3 0x55c92dfde4e1 in js::gc::StoreBuffer::WasmAnyRefEdge::maybeInRememberedSet(js::Nursery const&) const /home/test/gecko-dev/js/src/gc/StoreBuffer.h:459:7
    #4 0x55c92dfde35b in void js::gc::StoreBuffer::put<js::gc::StoreBuffer::MonoTypeBuffer<js::gc::StoreBuffer::WasmAnyRefEdge>, js::gc::StoreBuffer::WasmAnyRefEdge>(js::gc::StoreBuffer::MonoTypeBuffer<js::gc::StoreBuffer::WasmAnyRefEdge>&, js::gc::StoreBuffer::WasmAnyRefEdge const&, JS::GCReason) /home/test/gecko-dev/js/src/gc/StoreBuffer.h:497:15
    #5 0x55c92e0195bb in js::gc::StoreBuffer::putWasmAnyRef(js::wasm::AnyRef*) /home/test/gecko-dev/js/src/gc/StoreBuffer.h:595:5
    #6 0x55c92e0195bb in js::wasm::Instance::postBarrier(js::wasm::Instance*, void**) /home/test/gecko-dev/js/src/wasm/WasmInstance.cpp:1409:27
    #7 0x7f3e8aa70702  ([anon:js-executable-memory]+0x11702)

Address 0x24cc639fffa8 is a wild pointer inside of access range of size 0x000000000008.
SUMMARY: AddressSanitizer: use-after-poison /home/test/gecko-dev/js/src/wasm/WasmAnyRef.h:290:32 in js::wasm::AnyRef::isNull() const
Shadow bytes around the buggy address:
  0x24cc639ffd00: f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7
  0x24cc639ffd80: f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7
  0x24cc639ffe00: f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7
  0x24cc639ffe80: f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7
  0x24cc639fff00: f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7 f7
=>0x24cc639fff80: f7 f7 f7 f7 f7[f7]f7 f7 00 00 00 00 00 00 00 00
  0x24cc63a00000: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x24cc63a00080: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x24cc63a00100: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x24cc63a00180: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x24cc63a00200: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
Shadow byte legend (one shadow byte represents 8 application bytes):
  Addressable:           00
  Partially addressable: 01 02 03 04 05 06 07
  Heap left redzone:       fa
  Freed heap region:       fd
  Stack left redzone:      f1
  Stack mid redzone:       f2
  Stack right redzone:     f3
  Stack after return:      f5
  Stack use after scope:   f8
  Global redzone:          f9
  Global init order:       f6
  Poisoned by user:        f7
  Container overflow:      fc
  Array cookie:            ac
  Intra object redzone:    bb
  ASan internal:           fe
  Left alloca redzone:     ca
  Right alloca redzone:    cb
==3045212==ABORTING
```

## Env
1. Operating system
```
uname -a
Linux test-MZ72-2 5.19.0-32-generic #33~22.04.1-Ubuntu SMP PREEMPT_DYNAMIC Mon Jan 30 17:03:34 UTC 2 x86_64 x86_64 x86_64 GNU/Linux
```
2. commit
```
commit 529f04f4cd2ae68a0f729ba91cf8985edb23e9d3 (HEAD -> master, origin/master, origin/HEAD)
Author: Jamie Nicol <jnicol@mozilla.com>
Date:   Sun Mar 17 21:30:11 2024 +0000

    Bug 1884791 - Avoid shader miscompilation on some Adreno drivers. r=gw

    Webrender's glslopt-optimized shaders encounter a miscompilation on
    some Adreno driver versions regarding fetching empty clip tasks. This
    patch reshuffles the code in such a way as to avoid the
    bug. Unfortunately the specific cause of the miscompilation remains
    unknown, meaning we must take extra care not to regress it in the
    future.

    Differential Revision: https://phabricator.services.mozilla.com/D204864
```

---

**Comment 1 — rhunt@eqrion.net — 2024-03-19T17:39:26Z**

I can only reproduce this extremely intermittently. Are you running with additional flags to make this reproduce more reliably? Are you setting specific gc zeal values?

---

**Comment 2 — rhunt@eqrion.net — 2024-03-19T17:42:19Z**

Created attachment 9392083
poc-anyref.js

Here's a text format version of the bug. I can't minimize it yet until I can reproduce it consistently.

---

**Comment 3 — eternalsakuraalpha@gmail.com — 2024-03-20T02:38:42Z**

The stability of reproducing (the issue) on Linux using the compilation options and reproduction steps I provided seems to be 100 percent. Additionally, if you cannot reproduce it stably, could you let me know how to convert wasm bytecode into readable wasmText? I might be able to try and help you simplify it.

---

**Comment 4 — rhunt@eqrion.net — 2024-03-20T16:18:53Z**

(In reply to Nan Wang[:sakura] from comment #3)
> The stability of reproducing (the issue) on Linux using the compilation options and reproduction steps I provided seems to be 100 percent. Additionally, if you cannot reproduce it stably, could you let me know how to convert wasm bytecode into readable wasmText? I might be able to try and help you simplify it.

I probably need to run on Linux instead of my M1 MacBook then. I will be able to do that sometime today or early tomorrow.

One good way to get bytecode into the wasm text format is to install `wasm-tools` [1] and then do `wasm-tools print file.wasm`. If you need to get the bytes out of the JS shell into a file, you can use `os.file.writeTypedArrayToFile(filename, array)`.

We also have a bug on file to have a `wasmBinaryToText` builtin in the shell, but don't have that right now.

[1] https://github.com/bytecodealliance/wasm-tools

---

**Comment 5 — ydelendik@mozilla.com — 2024-03-25T18:35:54Z**

I can only reproduce with address sanitizer flags. Smaller test case:

```
  var wasm_code = wasmTextToBinary(`
  (module
    (type $t1 (array (mut i16)))
    (type $t3 (sub (array (mut (ref $t1)))))
    (func (export "main")
      i32.const 0
      i32.const 20
      array.new $t1
      i32.const 3
      array.new $t3
      i32.const 1
      i32.const 2
      i32.const 7
      array.new $t1
      array.set $t3

      call 0
    )
  )`);
  var wasm_module = new WebAssembly.Module(wasm_code);
  var wasm_instance = new WebAssembly.Instance(wasm_module);
  wasm_instance.exports.main();
```

It is just creation of arrays and stack overflow.

---

**Comment 6 — iireland@mozilla.com — 2024-03-25T23:14:46Z**

I got nerd-sniped here.

The sequence of events appears to be:
1. We have an MWasmLoadField that is generated via getWasmArrayObjectData.
2. It loads the address of the nursery-allocated backing storage of an array into a register (in my rr recording, rdx).
3. We create a new array by calling WasmArrayObject::createArrayIL.
4. Just before the call, we spill rdx to the stack.
5. Inside the call, we trigger a nursery collection and poison the existing chunk.
6. After the call, we reload the spilled value of rdx. It is now pointing to poisoned memory.
7. Shortly afterwards, an OOL post-barrier path (visitOutOfLineWasmCallPostWriterBarrierIndeX) uses rdx to construct an address to pass into the PostBarrier code.
8. That address is poisoned. ASAN complains.

The root of the problem is that we're holding a reference to the array elements alive across a call that can GC, without doing anything to preserve it.

---

**Comment 7 — ydelendik@mozilla.com — 2024-03-27T14:41:47Z**

Created attachment 9393518
Bug 1885829 - Track ArrayDataPointer at safepoints. r?bvisness

---

**Comment 8 — ydelendik@mozilla.com — 2024-03-27T14:41:52Z**

Created attachment 9393519
Bug 1885829 - Add test for safepoint live registers. r?bvisness



Depends on D205846

---

**Comment 9 — ydelendik@mozilla.com — 2024-03-27T15:30:52Z**

The related functionality was introduced by bug 1863435 (not sure if it is a regressor)

---

**Comment 10 — release-mgmt-account-bot@mozilla.tld — 2024-03-28T12:14:33Z**

The severity field for this bug is set to S3. However, the bug is flagged with the `sec-high` keyword.
:yury, could you consider increasing the severity of this security bug?

For more information, please visit [BugBot documentation](https://wiki.mozilla.org/BugBot#severity_high_security.py).

---

**Comment 11 — rhunt@eqrion.net — 2024-03-28T17:38:31Z**

Bug 1863435 is definitely the regressor.

---

**Comment 12 — rhunt@eqrion.net — 2024-03-28T17:39:45Z**

Setting status based on regressing bug.

---

**Comment 13 — release-mgmt-account-bot@mozilla.tld — 2024-03-28T17:46:04Z**

Set release status flags based on info from the regressing bug 1863435

---

**Comment 14 — ydelendik@mozilla.com — 2024-03-28T19:52:50Z**

Comment on attachment 9393518
Bug 1885829 - Track ArrayDataPointer at safepoints. r?bvisness

### Security Approval Request
* **How easily could an exploit be constructed based on the patch?**: Typical UAF that involves garbage collector -- not trivial to reproduce and construct exploit.
* **Do comments in the patch, the check-in comment, or tests included in the patch paint a bulls-eye on the security problem?**: No
* **Which branches (beta, release, and/or ESR) are affected by this flaw, and do the release status flags reflect this affected/unaffected state correctly?**: beta/release
* **If not all supported branches, which bug introduced the flaw?**: None
* **Do you have backports for the affected branches?**: No
* **If not, how different, hard to create, and risky will they be?**: The same may cleanly apply to beta/release.
* **How likely is this patch to cause regressions; how much testing does it need?**: Test is provided in next patch.
* **Is the patch ready to land after security approval is given?**: Yes
* **Is Android affected?**: Unknown

---

**Comment 15 — tom@mozilla.com — 2024-03-29T12:43:07Z**

Comment on attachment 9393518
Bug 1885829 - Track ArrayDataPointer at safepoints. r?bvisness

Approved to land and request uplift

---

**Comment 16 — pulsebot@bmo.tld — 2024-03-29T14:44:19Z**

Pushed by ydelendik@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/da8c3fe5c79f
Track ArrayDataPointer at safepoints. r=bvisness,rhunt

---

**Comment 17 — aryx.bugmail@gmx-topmail.de — 2024-03-29T21:56:40Z**

https://hg.mozilla.org/mozilla-central/rev/da8c3fe5c79f

---

**Comment 18 — ydelendik@mozilla.com — 2024-03-29T22:15:42Z**

Comment on attachment 9393518
Bug 1885829 - Track ArrayDataPointer at safepoints. r?bvisness

### Beta/Release Uplift Approval Request
* **User impact if declined**: Possible crashes when using wasm code with Wasm GC functionality.
* **Is this code covered by automated tests?**: Yes
* **Has the fix been verified in Nightly?**: Yes
* **Needs manual test from QE?**: No
* **If yes, steps to reproduce**: 
* **List of other uplifts needed**: None
* **Risk to taking this patch**: Medium
* **Why is the change risky/not risky? (and alternatives if risky)**: affects only wasm gc functionality
* **String changes made/needed**: 
* **Is Android affected?**: Unknown

---

**Comment 19 — ryanvm@gmail.com — 2024-03-30T18:42:40Z**

Comment on attachment 9393518
Bug 1885829 - Track ArrayDataPointer at safepoints. r?bvisness

Approved for 125.0b7.

---

**Comment 20 — pulsebot@bmo.tld — 2024-03-30T18:43:49Z**

https://hg.mozilla.org/releases/mozilla-beta/rev/f9a7338ba3ab

---

**Comment 21 — dveditz@mozilla.com — 2024-04-15T05:28:47Z**

Created attachment 9396589
advisory.txt

---

**Comment 22 — release-mgmt-account-bot@mozilla.tld — 2024-05-28T12:01:04Z**

a month ago, tjr placed a reminder on the bug using the whiteboard tag `[reminder-test 2024-05-28]` .

yury, please refer to the original comment to better understand the reason for the reminder.

---

**Comment 23 — pulsebot@bmo.tld — 2024-05-28T18:33:31Z**

Pushed by ydelendik@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/c7a6ad12193f
Add test for safepoint live registers. r=bvisness

---

**Comment 24 — aryx.bugmail@gmx-topmail.de — 2024-05-29T14:58:01Z**

https://hg.mozilla.org/mozilla-central/rev/c7a6ad12193f
