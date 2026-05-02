# [WASM-GC] Assertion failure: storageBytes.isValid() in calcStorageBytes

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1880719
Component: JavaScript: WebAssembly
Bounty: (unknown)
Date: 2024-02-17T14:06:23Z
Keywords: csectype-intoverflow, regression, reporter-external, sec-high
See Also:
- https://bugzilla.mozilla.org/show_bug.cgi?id=1882751

Created attachment 9380692
poc0217.js

Steps to reproduce:

Git Commit : 3da086bd7bce12353fc65968802445dca46f4537
Build :
ac_add_options --enable-project=js
ac_add_options --disable-optimize
ac_add_options --disable-unified-build
ac_add_options --enable-debug
ac_add_options --disable-jemalloc

Running:
./js --wasm-memory-control --wasm-compiler=optimizing --wasm-exnref poc.js


Actual results:

```
  * frame #0: 0x0000555558e0398f js`js::jit::CodeGenerator::visitWasmNewArrayObject(js::jit::LWasmNewArrayObject*) [inlined] js::WasmArrayObject::calcStorageBytes(numElements=4294967293) at WasmGcObject.h:223:5
    frame #1: 0x0000555558e03948 js`js::jit::CodeGenerator::visitWasmNewArrayObject(this=0x00007ffff66db1e0, lir=0x00007ffff006a2c0) at CodeGenerator.cpp:19094:9
    frame #2: 0x0000555558df4e75 js`js::jit::CodeGenerator::generateBody(this=0x00007ffff66db1e0) at CodeGenerator.cpp:7388:9
    frame #3: 0x0000555558ea4ef9 js`js::jit::CodeGenerator::generateWasm(this=0x00007ffff66db1e0, callIndirectId=CallIndirectId @ 0x00007ffff66daec0, trapOffset=(offset_ = 1194), argTypes=0x00007ffff66db1d0, trapExitLayout=0x00007ffff66dc0e0, trapExitLayoutNumWords=16, offsets=0x00007ffff66db1a0, stackMaps=0x000055555ab67958, decoder=0x00007ffff66db130) at CodeGenerator.cpp:15196:8
    frame #4: 0x000055555984421e js`js::wasm::IonCompileFunctions(moduleEnv=0x00007fffffffc770, compilerEnv=<unavailable>, lifo=0x000055555ab672d0, inputs=0x000055555ab67338, code=0x000055555ab67660, error=0x00007ffff66dcc20) at WasmIonCompile.cpp:9377:20
    frame #5: 0x00005555597db405 js`ExecuteCompileTask(task=0x000055555ab672b0, error=0x00007ffff66dcc20) at WasmGenerator.cpp:729:12
    frame #6: 0x00005555597dadad js`js::wasm::CompileTask::runHelperThreadTask(this=0x000055555ab672b0, lock=<unavailable>) at WasmGenerator.cpp:755:10
    frame #7: 0x0000555557c60c52 js`js::GlobalHelperThreadState::runTaskLocked(this=0x000055555aa1b940, task=0x000055555ab672b0, locked=0x00007ffff66dcd20) at HelperThreads.cpp:1726:9
    frame #8: 0x0000555557c60800 js`js::GlobalHelperThreadState::runOneTask(this=0x000055555aa1b940, lock=0x00007ffff66dcd20) at HelperThreads.cpp:1695:5
    frame #9: 0x0000555557c9ff7c js`js::HelperThread::threadLoop(this=0x000055555aa175d0, pool=0x000055555aa1cfb0) at InternalThreadPool.cpp:282:27
    frame #10: 0x0000555557c9fa7d js`js::HelperThread::ThreadMain(pool=0x000055555aa1cfb0, helper=0x000055555aa175d0) at InternalThreadPool.cpp:225:11
    frame #11: 0x0000555557ca1756 js`js::detail::ThreadTrampoline<void (&)(js::InternalThreadPool*, js::HelperThread*), js::InternalThreadPool*&, js::HelperThread*>::Start(void*) [inlined] void js::detail::ThreadTrampoline<void (&)(js::InternalThreadPool*, js::HelperThread*), js::InternalThreadPool*&, js::HelperThread*>::callMain<0ul, 1ul>(this=0x000055555aa1d080) at Thread.h:228:5
    frame #12: 0x0000555557ca1738 js`js::detail::ThreadTrampoline<void (&)(js::InternalThreadPool*, js::HelperThread*), js::InternalThreadPool*&, js::HelperThread*>::Start(aPack=0x000055555aa1d080) at Thread.h:217:11
    frame #13: 0x00007ffff7f8e609 libpthread.so.0`start_thread(arg=<unavailable>) at pthread_create.c:477:8
    frame #14: 0x00007ffff7b43353 libc.so.6`__clone + 67
```

---

**Comment 1 — dveditz@mozilla.com — 2024-02-21T23:25:25Z**

Looks like this landed in bug 1863435. This assertion means an integer overflow but in a non-debug build we use the value anyway. If storage allocation is involved that could lead to underallocation and bad stuff? But the code seems to deliberately opt-out of using the checked result so maybe there are mitigating factors that save the day?

---

**Comment 2 — rhunt@eqrion.net — 2024-02-21T23:32:18Z**

I believe we should be checking for overflow here, and I'm not seeing a mitigating factor (besides the patch having landed recently).

---

**Comment 3 — release-mgmt-account-bot@mozilla.tld — 2024-02-21T23:42:34Z**

Set release status flags based on info from the regressing bug 1863435

---

**Comment 4 — bvisness@mozilla.com — 2024-02-22T16:25:49Z**

Created attachment 9382078
Bug 1880719: Fix incorrect array size calculation. r=rhunt

---

**Comment 5 — rhunt@eqrion.net — 2024-02-22T18:18:25Z**

So it looks like we'll always run through this MOZ_DIAGNOSTIC_ASSERT in this case. This means we should always hit a safe crash in nightly and early beta.

After early beta, when this assert gets compiled out, it seems like this overflow could cause an array to get allocated with less space than the length would indicate, allowing accesses to pass bounds check and access other memory (because the actual memory we allocated overflowed). But I've not tested this out personally.

The patch that regressed this landed in 124, which looks like it's still just early beta. So this shouldn't be exploitable yet, but will change in late beta and release.

---

**Comment 6 — rhunt@eqrion.net — 2024-02-22T18:24:34Z**

Comment on attachment 9382078
Bug 1880719: Fix incorrect array size calculation. r=rhunt

### Security Approval Request
* **How easily could an exploit be constructed based on the patch?**: (I'm assuming for this approval that we drop the tests and comments from the patch, and asked Ben to do that)

Fairly easily, it looks like an overflow situation around arrays with constant lengths, I'd guess a skilled attacker could figure out how to create an array with underflowed allocation size, but long length easily.

As noted above though, we're currently saved by a diagnostic assert that fires in nightly/early beta that prevents this from being exploitable.
* **Do comments in the patch, the check-in comment, or tests included in the patch paint a bulls-eye on the security problem?**: No
* **Which branches (beta, release, and/or ESR) are affected by this flaw, and do the release status flags reflect this affected/unaffected state correctly?**: Beta
* **If not all supported branches, which bug introduced the flaw?**: Bug 1863435
* **Do you have backports for the affected branches?**: Yes
* **If not, how different, hard to create, and risky will they be?**: 
* **How likely is this patch to cause regressions; how much testing does it need?**: Unlikely, we're checking for overflow and falling back from an optimized path to the unoptimized catch-all that handles overflow already.
* **Is the patch ready to land after security approval is given?**: Yes
* **Is Android affected?**: Yes

---

**Comment 7 — bvisness@mozilla.com — 2024-02-22T21:04:10Z**

Created attachment 9382139
Bug 1880719: Add tests for overflow on array size calculations. r=rhunt



Depends on D202466

---

**Comment 8 — bvisness@mozilla.com — 2024-02-22T21:07:38Z**

Tests and comments have been moved to the second patch.

---

**Comment 9 — dveditz@mozilla.com — 2024-02-27T00:39:05Z**

Comment on attachment 9382078
Bug 1880719: Fix incorrect array size calculation. r=rhunt

sec-approval+ = dveditz

Thanks for splitting the tests into a separate patch. The patch by itself announces what kind of problem it is pretty clearly unfortunately (it's such a small patch we can't obfuscate the checked-int in a sea of changes), but we hopefully buy a little time not putting it on a silver platter. I'll be fine to land the tests shortly after we ship (a week?). You can file a separate "land tests for bug 1880719" bug if you want, but I'll set the `in-testsuite?` flag in this bug and if you track that you can set it to `in-testsuite+` when you land the tests without needing a separate bug.

As we discussed in side-chat Ryan has filed bug 1882201 to swap the function names (or use "unsafe") so future Mozillians are less likely to make this mistake during future code changes.

---

**Comment 10 — dveditz@mozilla.com — 2024-02-27T01:31:56Z**

Because it's a new regression in 124 we want to also land this on Beta. Please add a beta differential and request uplift on it.

---

**Comment 11 — rhunt@eqrion.net — 2024-02-27T15:18:36Z**

Created attachment 9387850
Bug 1880719: Fix incorrect array size calculation. r=bvisness

---

**Comment 12 — rhunt@eqrion.net — 2024-02-27T15:20:57Z**

I just added the D202833 revision which is based on FIREFOX_BETA_124_BASE. Had to change the reviewer as I submitted it for Ben.

---

**Comment 13 — rhunt@eqrion.net — 2024-02-27T15:28:40Z**

Created attachment 9387853
Bug 1880719: Fix incorrect array size calculation. r=rhunt



Original Revision: https://phabricator.services.mozilla.com/D202466

---

**Comment 14 — pulsebot@bmo.tld — 2024-02-27T15:29:20Z**

Pushed by rhunt@eqrion.net:
https://hg.mozilla.org/integration/autoland/rev/c9539953d2b0
Fix incorrect array size calculation. r=rhunt

---

**Comment 15 — phab-bot@bmo.tld — 2024-02-27T15:32:35Z**

# Uplift Approval Request
- **String changes made/needed**: N/A
- **Explanation of risk level**: disables an optimization when overflow happens and falls back to general case that can handle overflow.
- **Risk associated with taking this patch**: Low
- **Needs manual QE test**: no
- **Fix verified in Nightly**: yes
- **Code covered by automated testing**: yes
- **Is Android affected?**: yes
- **Steps to reproduce for manual QE testing**: N/A
- **User impact if declined**: Overflow in array size computation could result in OOB memory access.

---

**Comment 16 — rhunt@eqrion.net — 2024-02-27T15:34:11Z**

(In reply to Ryan Hunt [:rhunt] from comment #12)
> I just added the D202833 revision which is based on FIREFOX_BETA_124_BASE. Had to change the reviewer as I submitted it for Ben.

I was not aware that Lando had the ability to do this for me, so I just redid it the (hopefully) correct way and got D202835.

---

**Comment 17 — ryanvm@gmail.com — 2024-02-28T04:35:30Z**

https://hg.mozilla.org/mozilla-central/rev/c9539953d2b0

---

**Comment 18 — dsmith@mozilla.com — 2024-03-02T14:33:38Z**

Comment on attachment 9387853
Bug 1880719: Fix incorrect array size calculation. r=rhunt

Approved for 124.0b7

---

**Comment 19 — pulsebot@bmo.tld — 2024-03-02T14:40:34Z**

https://hg.mozilla.org/releases/mozilla-beta/rev/8a7004b5a774

---

**Comment 20 — cz18811105578@gmail.com — 2024-03-18T23:09:47Z**

Hello, could this bug be eligible for a CVE number?

---

**Comment 21 — rhunt@eqrion.net — 2024-03-19T13:57:47Z**

Forwarding the question. I think you can also reach out to security@mozilla.com for questions like this too.

---

**Comment 22 — bvisness@mozilla.com — 2024-03-19T16:59:44Z**

The new tests from this bug have been folded into the patches for bug 1882201, and can land with them later.

---

**Comment 23 — dveditz@mozilla.com — 2024-03-21T06:11:14Z**

> Hello, could this bug be eligible for a CVE number?

See bug 1862473 comment 13
