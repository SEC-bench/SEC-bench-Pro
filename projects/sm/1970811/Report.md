# Crash [@ bool JSScript::containsPC<4ul>(unsigned char const*) const] with self-hosted cache

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1970811
Component: JavaScript Engine
Bounty: (unknown)
Date: 2025-06-06T08:52:23Z
Keywords: assertion, crash, csectype-uaf, regression, sec-high, testcase

The following testcase crashes on mozilla-central revision 20250606-782839debd77 (debug build, run with --fuzzing-safe --ion-offthread-compile=off --setpref=experimental.self_hosted_cache=true --blinterp-eager --baseline-warmup-threshold=1):

    gczeal(14);
    a = new Set();
    for (b of a) 30;


Backtrace:

    received signal SIGSEGV, Segmentation fault.
    0x000055555706f87f in bool JSScript::containsPC<4ul>(unsigned char const*) const ()
    #0  0x000055555706f87f in bool JSScript::containsPC<4ul>(unsigned char const*) const ()
    #1  0x000055555705f033 in JSScript::getAtom(unsigned char*) const ()
    #2  0x0000555557062c5b in js::SetIntrinsicOperation(JSContext*, JSScript*, unsigned char*, JS::Handle<JS::Value>) ()
    #3  0x000004bfc526995e in ?? ()
    [...]
    #14 0x0000000000000000 in ?? ()
    rax	0x5	5
    rbx	0x11ccddc62100	19571591749888
    rcx	0x555555972a50	93824996551248
    rdx	0x7ffff46f279b	140737294313371
    rsi	0x7ffff46f279b	140737294313371
    rdi	0x11ccddc62100	19571591749888
    rbp	0x7fffffffbb60	140737488337760
    rsp	0x7fffffffbb60	140737488337760
    r8	0x2	2
    r9	0x7fffffffb858	140737488336984
    r10	0x0	0
    r11	0x7ffff46f279b	140737294313371
    r12	0x0	0
    r13	0x0	0
    r14	0x7ffff46f279b	140737294313371
    r15	0x7ffff463a200	140737293558272
    rip	0x55555706f87f <bool JSScript::containsPC<4ul>(unsigned char const*) const+31>
    => 0x55555706f87f <_ZNK8JSScript10containsPCILm4EEEbPKh+31>:	mov    0x48(%rdi),%rax
       0x55555706f883 <_ZNK8JSScript10containsPCILm4EEEbPKh+35>:	test   %rax,%rax

---

**Comment 1 — choller@mozilla.com — 2025-06-06T08:52:26Z**

Created attachment 9493244
Detailed Crash Information

---

**Comment 2 — choller@mozilla.com — 2025-06-06T08:52:26Z**

Created attachment 9493245
Testcase

---

**Comment 3 — bugmon@mozilla.com — 2025-06-06T18:04:27Z**

Unable to reproduce bug 1970811 using build mozilla-central 20250606014355-782839debd77.  Without a baseline, bugmon is unable to analyze this bug.
Removing bugmon keyword as no further action possible.  Please review the bug and re-add the keyword for further analysis.

---

**Comment 4 — bthrall@mozilla.com — 2025-06-06T19:19:57Z**

I was able to reproduce this and am investigating.

---

**Comment 5 — release-mgmt-account-bot@mozilla.tld — 2025-06-06T19:42:25Z**

Set release status flags based on info from the regressing bug 1827914

---

**Comment 6 — choller@mozilla.com — 2025-06-10T11:22:56Z**

Marking as fuzzblocker as this is very frequent. We will remove the flag from fuzzing for now. Please needinfo me when the bug is fixed so we can re-add the flag. Thanks!

---

**Comment 7 — dmeehan@mozilla.com — 2025-06-11T13:16:46Z**

:bthrall, the final Fx140 beta builds on Friday. There is little time to fix this if it's needed in Fx140?

---

**Comment 8 — bthrall@mozilla.com — 2025-06-11T15:35:13Z**

:dmeehan, thanks for the heads-up!

This bug definitely depends on having the javascript.experimental.self_hosted_cache pref enabled (it is disabled by default), so I don't think there is any harm to our users if Fx140 does not contain a fix.

---

**Comment 9 — dmeehan@mozilla.com — 2025-06-11T15:38:00Z**

Thanks for the detail, I hadn't noticed that.

---

**Comment 10 — bthrall@mozilla.com — 2025-06-11T15:48:14Z**

The problem here appears when a self-hosted script is OSR'd from the Interpreter into Baseline-compiled. In this case, the Interpreter stack frame is reinterpreted as a Baseline frame.

When the self_hosted_cache pref is enabled, a Baseline frame for self-hosted code should have the `BaselineFrame::REALM_INDEPENDENT` flag set, but the OSR'd frame does not. Therefore, [the frame's interpreterScript_ field is not traced](https://searchfox.org/mozilla-central/rev/240ca3fb4457621e155d039c7ea7055c0e22b374/js/src/jit/BaselineFrame.cpp#55).

In the case of this bug, a compacting GC is tenuring the top-level self-hosted script; the untraced `interpreterScript_` frame field is not updated and ends up pointing to poisoned memory. When the code tries to use the script, it segfaults.

This is not a problem when the self_hosted_cache pref is disabled because the Baseline-compiled code in that case has the script pointer baked into the code and doesn't use the frame to get it; the script pointer in this case is updated during GC via a data relocation trace.

---

**Comment 11 — bthrall@mozilla.com — 2025-06-11T19:27:09Z**

Created attachment 9494167
Bug 1970811 - Set REALM_INDEPENDENT flag on OSR'd frames when self_hosted_cache is enabled r=iain!

---

**Comment 12 — release-mgmt-account-bot@mozilla.tld — 2025-06-12T12:14:21Z**

The severity field for this bug is set to S3. However, the bug is flagged with the `sec-high` keyword.
:bthrall, could you consider increasing the severity of this security bug?

For more information, please visit [BugBot documentation](https://wiki.mozilla.org/BugBot#severity_high_security.py).

---

**Comment 13 — bthrall@mozilla.com — 2025-06-13T14:51:01Z**

I think S3 is appropriate, given that this bug depends on enabling an experimental preference; it does not affect behavior in the typical user case.

---

**Comment 14 — release-mgmt-account-bot@mozilla.tld — 2025-06-16T12:23:13Z**

This bug prevents fuzzing from making progress; however, it has low severity. It is important for fuzz blocker bugs to be addressed in a timely manner (see [here](https://firefox-source-docs.mozilla.org/tools/fuzzing/index.html#fuzz-blockers) why?).
:bthrall, could you consider increasing the severity?

For more information, please visit [BugBot documentation](https://wiki.mozilla.org/BugBot#fuzz_blockers.py).

---

**Comment 15 — bthrall@mozilla.com — 2025-06-16T15:40:07Z**

Comment on attachment 9494167
Bug 1970811 - Set REALM_INDEPENDENT flag on OSR'd frames when self_hosted_cache is enabled r=iain!

### Security Approval Request
* **How easily could an exploit be constructed based on the patch?**: It would be challenging: the attacker would have to know where to allocate memory to overwrite the poisoned JSScript and hope that the OSR'd frame that references that script will call a function on the script that allows them to execute code (such as jitCodeRaw()). It is not obvious that such a function will be called at all.
The scope of the exploit, however, will be small since it requires the javascript.options.experimental.self_hosted_cache pref be enabled (it is disabled by default).
* **Do comments in the patch, the check-in comment, or tests included in the patch paint a bulls-eye on the security problem?**: Yes
* **Which branches (beta, release, and/or ESR) are affected by this flaw, and do the release status flags reflect this affected/unaffected state correctly?**: beta
* **If not all supported branches, which bug introduced the flaw?**: Bug 1827914
* **Do you have backports for the affected branches?**: No
* **If not, how different, hard to create, and risky will they be?**: They should be trivial to create, since this bug applies to recent changes.
* **How likely is this patch to cause regressions; how much testing does it need?**: It is unlikely to cause regressions since it will only effect systems that have the javascript.options.experimental.self_hosted_cache pref enabled.
* **Is the patch ready to land after security approval is given?**: Yes
* **Is Android affected?**: Yes

---

**Comment 16 — fbraun@mozilla.com — 2025-06-17T12:50:36Z**

[sec-approval is only required for bugs that affect release](https://firefox-source-docs.mozilla.org/bug-mgmt/processes/security-approval.html). My understanding is that this is still disabled by default. Feel free to land right away.

---

**Comment 17 — pulsebot@bmo.tld — 2025-06-17T18:27:32Z**

Pushed by bthrall@mozilla.com:
https://github.com/mozilla-firefox/firefox/commit/4b63805dcd90
https://hg.mozilla.org/integration/autoland/rev/578eac49443f
Set REALM_INDEPENDENT flag on OSR'd frames when self_hosted_cache is enabled r=iain

---

**Comment 18 — aryx.bugmail@gmx-topmail.de — 2025-06-17T21:41:57Z**

https://hg.mozilla.org/mozilla-central/rev/578eac49443f

---

**Comment 19 — release-mgmt-account-bot@mozilla.tld — 2025-06-24T12:43:08Z**

Set release status flags based on info from the regressing bug 1827914

---

**Comment 20 — bthrall@mozilla.com — 2025-08-19T19:16:45Z**

Created attachment 9507953
(secure)

---

**Comment 21 — pulsebot@bmo.tld — 2025-08-19T21:39:30Z**

Pushed by bthrall@mozilla.com:
https://github.com/mozilla-firefox/firefox/commit/a682ef7a9240
https://hg.mozilla.org/integration/autoland/rev/7886da1a5c03
Add testcase r=iain

---

**Comment 22 — release-mgmt-account-bot@mozilla.tld — 2025-08-20T12:15:50Z**

A patch has been attached on this bug, which was already closed. Filing a separate bug will ensure better tracking. If this was not by mistake and further action is needed, please alert the appropriate party. (Or: if the patch doesn't change behavior -- e.g. landing a test case, or fixing a typo -- then feel free to disregard this message)

---

**Comment 23 — dmeehan@mozilla.com — 2025-08-20T12:17:56Z**

https://hg.mozilla.org/mozilla-central/rev/7886da1a5c03
