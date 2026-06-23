# Crash [@ js::SavedStacks::insertFrames] or Assertion failure: aIndex < mLength, at dist/include/mozilla/Vector.h:585

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1945318
Component: JavaScript Engine
Bounty: (unknown)
Date: 2025-02-01T14:27:26Z
Keywords: assertion, crash, csectype-bounds, regression, sec-high, testcase

The following testcase crashes on mozilla-central revision 20250131-935aaee05e86 (debug build, run with --fuzzing-safe --ion-offthread-compile=off --setpref=experimental.error_capture_stack_trace test.js):

    function* a() {
         yield b = {}
         Error.captureStackTrace(b, Error)
     }
     async function c() {
         d = a();
         (await d.next())(d.next())
     }
     c()


Backtrace:

    received signal SIGSEGV, Segmentation fault.
    #0  0x0000581d78429d26 in js::SavedStacks::insertFrames(JSContext*, JS::MutableHandle<js::SavedFrame*>, mozilla::Variant<JS::AllFrames, JS::MaxFrames, JS::FirstSubsumedFrame>&&, JS::Handle<JSObject*>) ()
    #1  0x0000581d78428246 in js::SavedStacks::saveCurrentStack(JSContext*, JS::MutableHandle<js::SavedFrame*>, mozilla::Variant<JS::AllFrames, JS::MaxFrames, JS::FirstSubsumedFrame>&&, JS::Handle<JSObject*>) ()
    #2  0x0000581d786c9b45 in JS::CaptureCurrentStack(JSContext*, JS::MutableHandle<JSObject*>, mozilla::Variant<JS::AllFrames, JS::MaxFrames, JS::FirstSubsumedFrame>&&, JS::Handle<JSObject*>) ()
    #3  0x0000581d78242be5 in exn_captureStackTrace(JSContext*, unsigned int, JS::Value*) ()
    #4  0x0000581d7808b30b in CallJSNative(JSContext*, bool (*)(JSContext*, unsigned int, JS::Value*), js::CallReason, JS::CallArgs const&) ()
    #5  0x0000581d7808a8f4 in js::InternalCallOrConstruct(JSContext*, JS::CallArgs const&, js::MaybeConstruct, js::CallReason) ()
    #6  0x0000581d780a1729 in js::Interpret(JSContext*, js::RunState&) ()
    #7  0x0000581d78089c9b in js::RunScript(JSContext*, js::RunState&) ()
    #8  0x0000581d7808a7de in js::InternalCallOrConstruct(JSContext*, JS::CallArgs const&, js::MaybeConstruct, js::CallReason) ()
    #9  0x0000581d7808c229 in js::Call(JSContext*, JS::Handle<JS::Value>, JS::Handle<JS::Value>, js::AnyInvokeArgs const&, JS::MutableHandle<JS::Value>, js::CallReason) ()
    #10 0x0000581d78447408 in js::CallSelfHostedFunction(JSContext*, JS::Handle<js::PropertyName*>, JS::Handle<JS::Value>, js::AnyInvokeArgs const&, JS::MutableHandle<JS::Value>) ()
    #11 0x0000581d78190e62 in AsyncFunctionResume(JSContext*, JS::Handle<js::AsyncFunctionGeneratorObject*>, ResumeKind, JS::Handle<JS::Value>) ()
    #12 0x0000581d783bf4e6 in PromiseReactionJob(JSContext*, unsigned int, JS::Value*) ()
    #13 0x0000581d7808b30b in CallJSNative(JSContext*, bool (*)(JSContext*, unsigned int, JS::Value*), js::CallReason, JS::CallArgs const&) ()
    [...]
    #19 0x0000581d77f18d18 in RunShellJobs(JSContext*) ()
    #20 0x0000581d77ef60b0 in Shell(JSContext*, js::cli::OptionParser*) ()
    #21 0x0000581d77eec84b in main ()
    rax	0x581d7686565f	96883565811295
    rbx	0x7ffdd16cb6a8	140728117016232
    rcx	0x581d79ad27d0	96883618686928
    rdx	0x7afe914b2723	135233777903395
    rsi	0x0	0
    rdi	0x7afe914b3a60	135233777908320
    rbp	0x7ffdd16cbea0	140728117018272
    rsp	0x7ffdd16cb4e0	140728117015776
    r8	0x76	118
    r9	0x0	0
    r10	0x0	0
    r11	0x18	24
    r12	0x7ffdd16cc2e0	140728117019360
    r13	0x7ffdd16cbfe0	140728117018592
    r14	0xaaaaaaaaaaaaaaaa	-6148914691236517206
    r15	0x7afe90f3e800	135233772185600
    rip	0x581d78429d26 <js::SavedStacks::insertFrames(JSContext*, JS::MutableHandle<js::SavedFrame*>, mozilla::Variant<JS::AllFrames, JS::MaxFrames, JS::FirstSubsumedFrame>&&, JS::Handle<JSObject*>)+6278>
    => 0x581d78429d26 <_ZN2js11SavedStacks12insertFramesEP9JSContextN2JS13MutableHandleIPNS_10SavedFrameEEEON7mozilla7VariantIJNS3_9AllFramesENS3_9MaxFramesENS3_18FirstSubsumedFrameEEEENS3_6HandleIP8JSObjectEE+6278>:	movl   $0x249,0x0
       0x581d78429d31 <_ZN2js11SavedStacks12insertFramesEP9JSContextN2JS13MutableHandleIPNS_10SavedFrameEEEON7mozilla7VariantIJNS3_9AllFramesENS3_9MaxFramesENS3_18FirstSubsumedFrameEEEENS3_6HandleIP8JSObjectEE+6289>:	call   0x581d77f8a140 <abort>

---

**Comment 1 — choller@mozilla.com — 2025-02-01T14:27:31Z**

Created attachment 9463314
Detailed Crash Information

---

**Comment 2 — choller@mozilla.com — 2025-02-01T14:27:33Z**

Created attachment 9463315
Testcase

---

**Comment 3 — bugmon@mozilla.com — 2025-02-03T00:23:12Z**

Unable to reproduce bug 1945318 using build mozilla-central 20250131212813-935aaee05e86.  Without a baseline, bugmon is unable to analyze this bug.
Removing bugmon keyword as no further action possible.  Please review the bug and re-add the keyword for further analysis.

---

**Comment 4 — mgaudet@mozilla.com — 2025-02-03T18:44:29Z**

Created attachment 9463559
Bug 1945318 - Don't try to reparent an empty stack r?jandem

---

**Comment 5 — mgaudet@mozilla.com — 2025-02-03T18:45:22Z**

Not sensitive as relies on the use of an experimental off by default API.

---

**Comment 6 — mgaudet@mozilla.com — 2025-02-03T21:01:50Z**

Because this is currently not shipping, this should be bumped down one level to sec-moderate right? 

(my reading of [Securiyt Severity Ratings/Client](https://wiki.mozilla.org/Security_Severity_Ratings/Client))

---

**Comment 7 — choller@mozilla.com — 2025-02-03T21:08:32Z**

(In reply to Matthew Gaudet (he/him) [:mgaudet] from comment #6)
> Because this is currently not shipping, this should be bumped down one level to sec-moderate right? 
> 

No, security rating is not dependent on the default in Nightly for things that we plan to ship. We want bugs to be rated the same as if we had found them after switching the feature to on by default, otherwise it is hard to assess how effective we are at eliminating security bugs *before* shipping them.

Also, bugs should remain hidden unless we are absolutely sure that the feature won't be turned on before the bug is fixed.

---

**Comment 8 — mgaudet@mozilla.com — 2025-02-03T22:18:04Z**

Ok. That's good to know. 

I'm definitely going to land this fix before shipping it :)

---

**Comment 9 — pulsebot@bmo.tld — 2025-02-04T18:54:02Z**

Pushed by mgaudet@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/ceea43c1678f
Don't try to reparent an empty stack r=jandem

---

**Comment 10 — sstanca@mozilla.com — 2025-02-05T10:00:11Z**

https://hg.mozilla.org/mozilla-central/rev/ceea43c1678f
