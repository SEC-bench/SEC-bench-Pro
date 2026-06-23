# Assertion failure: CurrentThreadCanAccessRuntime(cell->runtimeFromAnyThread()) || CurrentThreadIsPerformingGC(), at gc/StableCellHasher-inl.h:29

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1863391
Component: JavaScript Engine
Bounty: (unknown)
Date: 2023-11-06T19:06:05Z
Keywords: assertion, regression, sec-high, testcase

The following testcase crashes on mozilla-central revision 20231106-925231a8fb5e (debug build, run with --fuzzing-safe --ion-offthread-compile=off):

    evalInWorker(`
      a = new WeakMap
      b = Symbol
      a.set(b )
      c = b.hasInstance;
      a.get(c)
    `)


Backtrace:

    received signal SIGSEGV, Segmentation fault.
    #0  0x0000555557225428 in js::gc::MaybeGetUniqueId(js::gc::Cell*, unsigned long*) ()
    #1  0x00005555575ee6ae in mozilla::detail::HashTable<mozilla::HashMapEntry<js::HeapPtr<JS::Value>, js::HeapPtr<JS::Value> >, mozilla::HashMap<js::HeapPtr<JS::Value>, js::HeapPtr<JS::Value>, js::StableCellHasher<js::HeapPtr<JS::Value> >, js::TrackedAllocPolicy<(js::TrackingKind)1> >::MapHashPolicy, js::TrackedAllocPolicy<(js::TrackingKind)1> >::readonlyThreadsafeLookup(JS::Value const&) const ()
    #2  0x00005555575947ef in js::WeakMap<js::HeapPtr<JS::Value>, js::HeapPtr<JS::Value> >::lookup(JS::Value const&) const ()
    #3  0x00005555575eeb19 in js::WeakMapObject::get_impl(JSContext*, JS::CallArgs const&) ()
    #4  0x0000555557593068 in js::WeakMapObject::get(JSContext*, unsigned int, JS::Value*) ()
    #5  0x000055555706b245 in CallJSNative(JSContext*, bool (*)(JSContext*, unsigned int, JS::Value*), js::CallReason, JS::CallArgs const&) ()
    #6  0x000055555706a81e in js::InternalCallOrConstruct(JSContext*, JS::CallArgs const&, js::MaybeConstruct, js::CallReason) ()
    #7  0x000055555707bc0b in js::Interpret(JSContext*, js::RunState&) ()
    #8  0x0000555557069d8f in js::RunScript(JSContext*, js::RunState&) ()
    #9  0x000055555706d94b in js::ExecuteKernel(JSContext*, JS::Handle<JSScript*>, JS::Handle<JSObject*>, js::AbstractFramePtr, JS::MutableHandle<JS::Value>) ()
    #10 0x000055555706df50 in js::Execute(JSContext*, JS::Handle<JSScript*>, JS::Handle<JSObject*>, JS::MutableHandle<JS::Value>) ()
    #11 0x00005555571d2b22 in ExecuteScript(JSContext*, JS::Handle<JSObject*>, JS::Handle<JSScript*>, JS::MutableHandle<JS::Value>) ()
    #12 0x00005555571d28c8 in JS_ExecuteScript(JSContext*, JS::Handle<JSScript*>, JS::MutableHandle<JS::Value>) ()
    #13 0x0000555556ee8588 in WorkerMain(mozilla::UniquePtr<WorkerInput, JS::DeletePolicy<WorkerInput> >) ()
    #14 0x0000555556ee8bda in js::detail::ThreadTrampoline<void (&)(mozilla::UniquePtr<WorkerInput, JS::DeletePolicy<WorkerInput> >), mozilla::UniquePtr<WorkerInput, JS::DeletePolicy<WorkerInput> > >::Start(void*) ()
    #15 0x0000555556f350bd in set_alt_signal_stack_and_start(PthreadCreateParams*) ()
    #16 0x00007ffff7bc16ba in start_thread (arg=0x7ffff4667700) at pthread_create.c:333
    #17 0x00007ffff6e4641d in clone () at ../sysdeps/unix/sysv/linux/x86_64/clone.S:109
    rax	0x555555839ac0	93824995269312
    rbx	0x7ffff4666328	140737293738792
    rcx	0x55555898edc8	93825046998472
    rdx	0x0	0
    rsi	0x7ffff7105770	140737338431344
    rdi	0x7ffff7104540	140737338426688
    rbp	0x7ffff4666310	140737293738768
    rsp	0x7ffff46662e0	140737293738720
    r8	0x7ffff7105770	140737338431344
    r9	0x7ffff4667700	140737293743872
    r10	0x2	2
    r11	0x0	0
    r12	0x555557592f80	93825026043776
    r13	0x1fcaaeb29858	34955374794840
    r14	0x9e18c03b090	10864321343632
    r15	0x9e18c000000	10864321101824
    rip	0x555557225428 <js::gc::MaybeGetUniqueId(js::gc::Cell*, unsigned long*)+504>
    => 0x555557225428 <_ZN2js2gc16MaybeGetUniqueIdEPNS0_4CellEPm+504>:	movl   $0x1d,0x0
       0x555557225433 <_ZN2js2gc16MaybeGetUniqueIdEPNS0_4CellEPm+515>:	callq  0x555556f349c0 <abort>


This is a fuzzblocker, happening with high frequency. Also marking s-s because I don't know the impact of this GC assert.

---

**Comment 1 — choller@mozilla.com — 2023-11-06T19:06:08Z**

Created attachment 9362196
Detailed Crash Information

---

**Comment 2 — choller@mozilla.com — 2023-11-06T19:06:09Z**

Created attachment 9362197
Testcase

---

**Comment 3 — continuation@gmail.com — 2023-11-06T22:10:50Z**

Possible regression from bug 1828144.

---

**Comment 4 — bugmon@mozilla.com — 2023-11-07T00:20:56Z**

Unable to reproduce bug 1863391 using build mozilla-central 20231106094018-925231a8fb5e.  Without a baseline, bugmon is unable to analyze this bug.
Removing bugmon keyword as no further action possible.  Please review the bug and re-add the keyword for further analysis.

---

**Comment 5 — choller@mozilla.com — 2023-11-07T08:56:55Z**

*** Bug 1863447 has been marked as a duplicate of this bug. ***

---

**Comment 6 — release-mgmt-account-bot@mozilla.tld — 2023-11-07T16:42:36Z**

Set release status flags based on info from the regressing bug 1828144

---

**Comment 7 — allstars.chh@gmail.com — 2023-11-07T17:51:49Z**

Created attachment 9362392
Bug 1863391 - Use Symbol::hash to get hashes.

---

**Comment 8 — dveditz@mozilla.com — 2023-11-08T22:42:39Z**

An actual collision looks racy, but maybe this could be sec-high? As a fuzzblocker clearly it will be easy for other people to find if it does turn out to be exploitable.

---

**Comment 9 — allstars.chh@gmail.com — 2023-11-09T09:43:15Z**

Created attachment 9362782
Bug 1863391 - tests.

---

**Comment 10 — allstars.chh@gmail.com — 2023-11-09T10:53:39Z**

Comment on attachment 9362392
Bug 1863391 - Use Symbol::hash to get hashes.

### Security Approval Request
* **How easily could an exploit be constructed based on the patch?**: Difficult. This patch is trying to get the hash number from the Symbol directly to get the entry in HashMap.
* **Do comments in the patch, the check-in comment, or tests included in the patch paint a bulls-eye on the security problem?**: No
* **Which older supported branches are affected by this flaw?**: No
* **If not all supported branches, which bug introduced the flaw?**: Bug 1828144
* **Do you have backports for the affected branches?**: No
* **If not, how different, hard to create, and risky will they be?**: Other branches won't have any risk as this bug is introduced in Bug 1828144.
* **How likely is this patch to cause regressions; how much testing does it need?**: Unlikely, this patch only gets the hash number from the Symbols.
The test is provided in a separate commit.
* **Is Android affected?**: Yes

---

**Comment 11 — release-mgmt-account-bot@mozilla.tld — 2023-11-09T12:17:41Z**

The severity field for this bug is set to S3. However, the bug is flagged with the `sec-high` keyword.
:allstars.chh, could you consider increasing the severity of this security bug?

For more information, please visit [BugBot documentation](https://wiki.mozilla.org/BugBot#severity_high_security.py).

---

**Comment 12 — ryanvm@gmail.com — 2023-11-13T18:40:25Z**

Comment on attachment 9362392
Bug 1863391 - Use Symbol::hash to get hashes.

Nightly-only bugs don't need sec-approval.

---

**Comment 13 — pulsebot@bmo.tld — 2023-11-13T18:47:49Z**

Pushed by rvandermeulen@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/4c400fa02bee
Use Symbol::hash to get hashes. r=jonco
https://hg.mozilla.org/integration/autoland/rev/0c78e4ad3659
tests. r=jonco

---

**Comment 14 — allstars.chh@gmail.com — 2023-11-14T07:15:58Z**

(In reply to Ryan VanderMeulen [:RyanVM] from comment #12)
> Comment on attachment 9362392
> Bug 1863391 - Use Symbol::hash to get hashes.
> 
> Nightly-only bugs don't need sec-approval.

oh, that's right, thanks for the reminding, I forgot that.

---

**Comment 15 — aryx.bugmail@gmx-topmail.de — 2023-11-14T09:34:08Z**

https://hg.mozilla.org/mozilla-central/rev/4c400fa02bee
https://hg.mozilla.org/mozilla-central/rev/0c78e4ad3659

---

**Comment 16 — jcoppeard@mozilla.com — 2025-09-01T07:06:55Z**

*** Bug 1862459 has been marked as a duplicate of this bug. ***
