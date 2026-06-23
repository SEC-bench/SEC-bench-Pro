# Assertion failure: (kMinCPOffset) <= (cp_offset), at irregexp/imported/regexp-bytecode-generator.cc:194

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1994994
Component: JavaScript Engine
Bounty: (unknown)
Date: 2025-10-17T13:46:59Z
Keywords: assertion, csectype-bounds, regression, sec-high, testcase
See Also:
- https://issues.chromium.org/issues/451663011

The following testcase crashes on mozilla-central revision 20251015-e60dda01349d (debug build, run with --fuzzing-safe --ion-offthread-compile=off):

    const length = 32767;
    const pattern_body = "^" + "a".repeat(length);
    const pattern = new RegExp("(?<=" + pattern_body + ")", "m");
    pattern.exec("");


Backtrace:

    received signal SIGSEGV, Segmentation fault.
    #0  0x0000555557a8fc3b in v8::internal::RegExpBytecodeGenerator::LoadCurrentCharacterImpl(int, v8::internal::Label*, bool, int, int) ()
    #1  0x0000555557aa4c18 in v8::internal::AssertionNode::Emit(v8::internal::RegExpCompiler*, v8::internal::Trace*) ()
    #2  0x0000555557aa6aa0 in v8::internal::TextNode::Emit(v8::internal::RegExpCompiler*, v8::internal::Trace*) ()
    #3  0x0000555557aaa647 in v8::internal::ActionNode::Emit(v8::internal::RegExpCompiler*, v8::internal::Trace*) ()
    #4  0x0000555557a9e49a in v8::internal::RegExpCompiler::Assemble(v8::internal::Isolate*, v8::internal::RegExpMacroAssembler*, v8::internal::RegExpNode*, int, v8::internal::Handle<v8::internal::String>) ()
    #5  0x0000555557a8ace5 in js::irregexp::CompilePattern(JSContext*, JS::MutableHandle<js::RegExpShared*>, JS::Handle<JSLinearString*>, js::RegExpShared::CodeKind) ()
    #6  0x00005555573b1d04 in js::RegExpShared::execute(JSContext*, JS::MutableHandle<js::RegExpShared*>, JS::Handle<JSLinearString*>, unsigned long, js::VectorMatchPairs*) ()
    #7  0x0000555557002f89 in ExecuteRegExp(JSContext*, JS::Handle<JSObject*>, JS::Handle<JSString*>, int, js::VectorMatchPairs*) ()
    #8  0x0000555556ff75da in js::RegExpBuiltinExec(JSContext*, JS::Handle<js::RegExpObject*>, JS::Handle<JSString*>, bool, JS::MutableHandle<JS::Value>) ()
    #9  0x00005555573fdb9f in bool intrinsic_RegExpBuiltinExec<false>(JSContext*, unsigned int, JS::Value*) ()
    #10 0x000055555704fcf5 in CallJSNative(JSContext*, bool (*)(JSContext*, unsigned int, JS::Value*), js::CallReason, JS::CallArgs const&) ()
    [...]
    #21 0x0000555556ecc3e6 in main ()
    rax	0x0	0
    rbx	0x7fffb6203700	140736248952576
    rcx	0xc2	194
    rdx	0x7ffff7804563	140737345766755
    rsi	0x0	0
    rdi	0x7ffff7805700	140737345771264
    rbp	0x7fffffffad90	140737488334224
    rsp	0x7fffffffad60	140737488334176
    r8	0x0	0
    r9	0x3	3
    r10	0x0	0
    r11	0x293	659
    r12	0x1	1
    r13	0x0	0
    r14	0xffff8000	4294934528
    r15	0x7fffb4a01840	140736223778880
    rip	0x555557a8fc3b <v8::internal::RegExpBytecodeGenerator::LoadCurrentCharacterImpl(int, v8::internal::Label*, bool, int, int)+923>
    => 0x555557a8fc3b <_ZN2v88internal23RegExpBytecodeGenerator24LoadCurrentCharacterImplEiPNS0_5LabelEbii+923>:	mov    %rcx,(%rax)
       0x555557a8fc3e <_ZN2v88internal23RegExpBytecodeGenerator24LoadCurrentCharacterImplEiPNS0_5LabelEbii+926>:	call   0x555556f69b70 <abort>


This seems to be a debug check, but it does not crash in an opt build. We should check carefully if it has any potential security impact, as v8 might also be affected then.

---

**Comment 1 — choller@mozilla.com — 2025-10-17T13:47:02Z**

Created attachment 9520747
Detailed Crash Information

---

**Comment 2 — choller@mozilla.com — 2025-10-17T13:47:04Z**

Created attachment 9520748
Testcase

---

**Comment 3 — continuation@gmail.com — 2025-10-17T16:38:05Z**

The test case and assertion looks the same as this thread that I found with a bit of Googling: https://groups.google.com/g/v8-reviews/c/2xtbmX7_s8E

---

**Comment 4 — bugmon@mozilla.com — 2025-10-17T16:47:47Z**

Verified bug as reproducible on mozilla-central 20251017091423-0591e6ac073c.
The bug appears to have been introduced in the following build range:
> Start: 69b4a882f3d0a4361b042ba007ffde86284db859 (20250916192439)
> End: 59e9a2833440108d1769e12399656ab40c4f7c3d (20250916193410)
> Pushlog: https://hg.mozilla.org/integration/autoland/pushloghtml?fromchange=69b4a882f3d0a4361b042ba007ffde86284db859&tochange=59e9a2833440108d1769e12399656ab40c4f7c3d

---

**Comment 5 — release-mgmt-account-bot@mozilla.tld — 2025-10-17T17:42:55Z**

Set release status flags based on info from the regressing bug 1987312

---

**Comment 6 — iireland@mozilla.com — 2025-10-17T21:02:55Z**

There is currently a lot of work going on in upstream irregexp rewriting the compiler pipeline. I was intending to let that bake upstream for a while before pulling it in. I think the cleanest answer is to just manually cherry-pick the patch in comment 3.

---

**Comment 7 — iireland@mozilla.com — 2025-10-17T21:14:18Z**

Created attachment 9520859
(secure)

---

**Comment 8 — continuation@gmail.com — 2025-10-17T21:20:27Z**

Do you know what rating this should get? From reading that thread it sounds like at worst it could be a sec-high bounds problem, but maybe it isn't actually that bad?

---

**Comment 9 — iireland@mozilla.com — 2025-10-17T22:56:39Z**

It's a bit hard to say.

Roughly speaking, we're exceeding by 1 the limit on how far back/forward we're willing to look from the current character pointer. I think we should be doing a bounds check anyway, so naively it doesn't seem like this should be too bad. The scariest case that I can think of is if we overflow / underflow: the limit is set at 1<<15, which is uncomfortably close to overflowing an int16_t. My quick scan didn't turn up anywhere that we're storing this value as an int16_t; in fact, it looks like the interpreter bytecode stores these as int24 (eg [here](https://searchfox.org/firefox-main/source/js/src/irregexp/imported/regexp-interpreter.cc#939)). 

That said, this is a big complicated ball of code that I don't understand very well, and it's easy to imagine missing something. One factor in our favour is that I'm pretty sure this is only used for reading characters out of the string. I don't feel entirely confident ruling out an OOB read, but I'm pretty confident there's no OOB write.

---

**Comment 10 — continuation@gmail.com — 2025-10-19T01:30:47Z**

*** Bug 1995160 has been marked as a duplicate of this bug. ***

---

**Comment 11 — continuation@gmail.com — 2025-10-20T14:13:07Z**

Thanks. I'll conservatively mark this sec-high then.

---

**Comment 12 — iireland@mozilla.com — 2025-10-20T17:07:27Z**

Comment on attachment 9520859
(secure)

### Security Approval Request
* **How easily could an exploit be constructed based on the patch?**: Difficult. It's not clear there's an exploitable problem here, but the code is complicated enough that we can't easily rule it out.

Note that I've examined the testcase and verified that there's nothing exploitable in this particular instance. We exceed a self-imposed limit on how far backwards we are willing to look in the string, but we're still doing the necessary bounds checks before reading, so there's no OOB access here.
* **Do comments in the patch, the check-in comment, or tests included in the patch paint a bulls-eye on the security problem?**: No
* **Which branches (beta, release, and/or ESR) are affected by this flaw, and do the release status flags reflect this affected/unaffected state correctly?**: Beta
* **If not all supported branches, which bug introduced the flaw?**: Bug 1987312
* **Do you have backports for the affected branches?**: Yes
* **If not, how different, hard to create, and risky will they be?**: This patch should apply cleanly.
* **How likely is this patch to cause regressions; how much testing does it need?**: 
* **Is the patch ready to land after security approval is given?**: Yes
* **Is Android affected?**: Yes

---

**Comment 13 — continuation@gmail.com — 2025-10-20T17:13:41Z**

> Do comments in the patch, the check-in comment, or tests included in the patch paint a bulls-eye on the security problem?: No

It should be noted that this issue has been discussed (including with a test case) in a public thread (comment 3)

---

**Comment 14 — iireland@mozilla.com — 2025-10-20T17:33:56Z**

Oops, yeah, my thought when filling that out was "this patch does not make any information public that isn't already public", but I guess that's not the actual wording of the question.

---

**Comment 15 — dveditz@mozilla.com — 2025-10-21T00:17:54Z**

Comment on attachment 9520859
(secure)

sec-approval+ = dveditz

---

**Comment 16 — dveditz@mozilla.com — 2025-10-22T18:16:57Z**

Very curious that our code update was a month before this bug was filed, and presumably Chrome was using the code even earlier, but then we had two independent reports of this within a day, and folks fuzzing Chrome found it there just a couple days before that. Weird coincidence or did everyone improve their fuzzers at the same time (which would be an even weirder coincidence)?

---

**Comment 17 — dveditz@mozilla.com — 2025-10-22T18:27:08Z**

We will need an advisory for 145 for this bug because it was also reported by external reporter Nan Wang in bug 1995160. Looks like Chrome is going to consider their version of this bug as "internally found" and not assign a CVE, but I'm not 100% sure of that yet until they release. If they issue a CVE we should use the same one because we have taken the same patch.

---

**Comment 18 — choller@mozilla.com — 2025-10-22T20:03:09Z**

(In reply to Daniel Veditz [:dveditz] from comment #16)
> Very curious that our code update was a month before this bug was filed, and presumably Chrome was using the code even earlier, but then we had two independent reports of this within a day, and folks fuzzing Chrome found it there just a couple days before that. Weird coincidence or did everyone improve their fuzzers at the same time (which would be an even weirder coincidence)?

It's also possible that a test landed that made this easier to discover through mutation-based fuzzing.

---

**Comment 19 — continuation@gmail.com — 2025-10-22T21:56:11Z**

Ah, yeah that must be it. The patch [landed on October 14 with a test case](https://chromium.googlesource.com/v8/v8/+/ddf1b5dac063ad5d45313ba5b97f75dd96745dda%5E%21/#F4).

---

**Comment 20 — pulsebot@bmo.tld — 2025-10-23T17:47:54Z**

Pushed by iireland@mozilla.com:
https://github.com/mozilla-firefox/firefox/commit/866e7aa6a080
https://hg.mozilla.org/integration/autoland/rev/1ddb5389c708
Apply upstream irregexp patch r=dminor

---

**Comment 21 — aryx.bugmail@gmx-topmail.de — 2025-10-24T08:36:26Z**

https://hg.mozilla.org/mozilla-central/rev/1ddb5389c708

---

**Comment 22 — release-mgmt-account-bot@mozilla.tld — 2025-10-24T12:01:27Z**

The patch landed in nightly and beta is affected.
:iain, is this bug important enough to require an uplift?
- If yes, please nominate the patch for beta approval.
  - See https://wiki.mozilla.org/Release_Management/Requesting_an_Uplift for documentation on how to request an uplift.
- If no, please set `status-firefox145` to `wontfix`.

For more information, please visit [BugBot documentation](https://wiki.mozilla.org/BugBot#uplift_beta.py).

---

**Comment 23 — iireland@mozilla.com — 2025-10-24T16:29:40Z**

Comment on attachment 9520859
(secure)

### Beta/Release Uplift Approval Request
* **User impact if declined/Reason for urgency**: Fixes an assertion failure in bounds-check-adjacent code. It might not be exploitable, but the code involved is complicated enough that it's hard to be completely certain. If there is a way to exploit it, it would likely provide an OOB read.
* **Is this code covered by automated tests?**: Yes
* **Has the fix been verified in Nightly?**: Yes
* **Needs manual test from QE?**: No
* **If yes, steps to reproduce**: 
* **List of other uplifts needed**: None
* **Risk to taking this patch**: Low
* **Why is the change risky/not risky? (and alternatives if risky)**: Very slightly reduces the size of regexp we are willing to compile. The upstream patch landed a week ago.
* **String changes made/needed**: None
* **Is Android affected?**: Yes

---

**Comment 24 — bugmon@mozilla.com — 2025-10-24T19:17:01Z**

Verified bug as fixed on rev mozilla-central 20251024042341-54e9a1e89e6e.
Removing bugmon keyword as no further action possible.  Please review the bug and re-add the keyword for further analysis.

---

**Comment 25 — pulsebot@bmo.tld — 2025-10-27T10:30:49Z**

https://github.com/mozilla-firefox/firefox/commit/b3dcb06173e4
https://hg.mozilla.org/releases/mozilla-beta/rev/ce1975646577
