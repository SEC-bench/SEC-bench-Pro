# Write side effects in MCallGetProperty opcode not accounted for

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1675905
CVE: CVE-2020-26950
Component: JavaScript Engine: JIT
Bounty: (unknown)
Date: 2020-11-07T02:32:39Z
Keywords: csectype-jit, sec-critical

The root cause is in the |MIR.h| file and the opcode |MCallGetProperty|:

```
AliasSet getAliasSet() const override {
    if (!idempotent_) {
      return AliasSet::Store(AliasSet::Any);
    }
    return AliasSet::Load(AliasSet::ObjectFields | AliasSet::FixedSlot |
                          AliasSet::DynamicSlot);
  }
```

if |idempotent_| is true, compiler will think this opcode does NOT have write side effect. But this is wrong.

In the function |createThisScripted|, it will emit a |MCallGetProperty| which |idempotent_| is true:

```
 else {
    MCallGetProperty* callGetProp =
        MCallGetProperty::New(alloc(), newTarget, names().prototype);
    callGetProp->setIdempotent();
    getProto = callGetProp;
  }
```

It use this opcode to get callee.prototype, and this operatioin may call function |func_reslove| and write the |prototype| to slots, so it may be grow the slots buffer and update callee's slots buffer address. This will lead to UaF problem in JIT code as JIT code may be use the old buffer address after the grow.

https://twitter.com/TianfuCup/status/1324900642393976832

---

**Comment 1 — tom@mozilla.com — 2020-11-07T03:55:46Z**

Created attachment 9186442
exploit-details.zip

Got this zip from them; awaiting the password.

---

**Comment 2 — tom@mozilla.com — 2020-11-07T04:12:43Z**

Password is `tfc2020@cic@tfc2020`

---

**Comment 3 — fbraun@mozilla.com — 2020-11-07T05:03:58Z**

Created attachment 9186445
poc.html

The zip file doesn't work trivially with all typical unzippers. Attaching PoC directly.

---

**Comment 4 — tcampbell@mozilla.com — 2020-11-07T06:23:22Z**

Created attachment 9186450
Bug 1675905 - Simplify IonBuilder::createThisScripted. r?jandem!,iain!

---

**Comment 5 — jdemooij@mozilla.com — 2020-11-07T06:45:16Z**

Created attachment 9186451
JS shell testcase

I wrote a PoC based on theirs. Repros on m-c tip, debug build:
```
$ obj-shell-dbg/dist/bin/js --no-warp --no-threads poc.js
poc.js:23:17 Error: Assertion failed: got -437918235, expected 2
```
That's a poison value.

---

**Comment 6 — jdemooij@mozilla.com — 2020-11-07T08:01:12Z**

Created attachment 9186452
JS shell test v2

This one triggers a crash in debug and opt builds.

---

**Comment 7 — jdemooij@mozilla.com — 2020-11-07T08:04:22Z**

Created attachment 9186453
Browser test

Crashes content process in 82.0.2 on Mac.

---

**Comment 8 — ryanvm@gmail.com — 2020-11-07T13:26:36Z**

IIUC, this might not affect 83+ due to Warp being enabled, but I'll leave that for someone on the JS team to confirm and set.

---

**Comment 9 — tcampbell@mozilla.com — 2020-11-07T13:28:37Z**

We should fix 83, because a warp/ion experiment is supposed to happen when release 83 ships.

---

**Comment 10 — ryanvm@gmail.com — 2020-11-07T13:31:43Z**

(In reply to Ted Campbell [:tcampbell] from comment #10)
> We should fix 83, because a warp/ion experiment is supposed to happen when release 83 ships.

Thanks for confirming. Setting flags accordingly.

---

**Comment 11 — tcampbell@mozilla.com — 2020-11-07T23:32:19Z**

Comment on attachment 9186450
Bug 1675905 - Simplify IonBuilder::createThisScripted. r?jandem!,iain!

### Security Approval Request
* **How easily could an exploit be constructed based on the patch?**: The patch suggests that `MCallGetProperty` is bad in this context, but doesn't directly point out the `fun_resolve`  reallocation that is also needed to exploit. This aspect was novel to us and deriving from patch would require experience with jit exploitation.
* **Do comments in the patch, the check-in comment, or tests included in the patch paint a bulls-eye on the security problem?**: Unknown
* **Which older supported branches are affected by this flaw?**: ALL
* **If not all supported branches, which bug introduced the flaw?**: None
* **Do you have backports for the affected branches?**: Yes
* **If not, how different, hard to create, and risky will they be?**: Patch applies onto FF78 through 84
* **How likely is this patch to cause regressions; how much testing does it need?**: We are removing a very rare case that existed solely as a perf trick. Correctness risk of this patch is low, and primary risk is a performance cliff in rare cases. We've added a perf mitigation in this patch that avoids Ion in rare cases and sticks with the more predictable BaselineJIT.

---

**Comment 12 — tcampbell@mozilla.com — 2020-11-07T23:41:08Z**

Comment on attachment 9186450
Bug 1675905 - Simplify IonBuilder::createThisScripted. r?jandem!,iain!

### ESR Uplift Approval Request
* **If this is not a sec:{high,crit} bug, please state case for ESR consideration**: External report of sec-crit. TianFu Cup 2020.
* **User impact if declined**: Remote-code-execution in Content process.
* **Fix Landed on Version**: 
* **Risk to taking this patch**: Low
* **Why is the change risky/not risky? (and alternatives if risky)**: Correctness risk is low since we are removing a rare edge case added as a hypothetical performance fix.
Perfomance risk is mitigated by an addition in this patch to rely on BaselineJIT in the very rare case instead of IonMonkey doing unnecessary compiles. The only place I've run into this rare case is heavily obfuscated JavaScript that is not performance critical.
* **String or UUID changes made by this patch**: None

---

**Comment 13 — tcampbell@mozilla.com — 2020-11-07T23:43:53Z**

Comment on attachment 9186450
Bug 1675905 - Simplify IonBuilder::createThisScripted. r?jandem!,iain!

### Beta/Release Uplift Approval Request
* **User impact if declined**: External sec-crit. TianFu Cup 2020.
Remote-code-execution in Content process.
* **Is this code covered by automated tests?**: Yes
* **Has the fix been verified in Nightly?**: No
* **Needs manual test from QE?**: Yes
* **If yes, steps to reproduce**: See chemspill QA Plan.
A crash-test HTML file is on bug. It may require 1-line tweaks for different versions.
* **List of other uplifts needed**: None
* **Risk to taking this patch**: Low
* **Why is the change risky/not risky? (and alternatives if risky)**: Correctness risk is low since we are removing a rare edge case added as a hypothetical performance fix.
Perfomance risk is mitigated by an addition in this patch to rely on BaselineJIT in the very rare case instead of IonMonkey doing unnecessary compiles. The only place I've run into this rare case is heavily obfuscated JavaScript that is not performance critical.
Note: Affected code is off-by-default in 83+, so perf risk is very short lived.
* **String changes made/needed**: None

---

**Comment 14 — tcampbell@mozilla.com — 2020-11-07T23:49:32Z**

- ESR-78: Affected. Patch applies cleanly.
- GeckoView-81: Affected. This previous version is still required for some mobile builds.
- Release-82: Affected.
- Beta-83: Disabled by default. A experiment is planned when this hits release that will re-enable Ion for a small population for limited time.
- Nightly-84: Disabled by default.
- Impacted code will be permanently removed from tree in Nightly-85.

---

**Comment 15 — tcampbell@mozilla.com — 2020-11-08T03:08:42Z**

Created attachment 9186486
Crashtest for QA (FF78-84)

Updated version of browser test with support for pre-82 and 82+ versions. On affected builds, this will crash tab. On fixed builds, this will render "Passed".

---

**Comment 16 — tom@mozilla.com — 2020-11-08T17:11:26Z**

Comment on attachment 9186450
Bug 1675905 - Simplify IonBuilder::createThisScripted. r?jandem!,iain!

sec-approved

---

**Comment 17 — ryanvm@gmail.com — 2020-11-08T17:16:29Z**

https://hg.mozilla.org/mozilla-central/rev/8cdc2037b4b092157f1d04700bb09b00b19bbca6

---

**Comment 18 — ryanvm@gmail.com — 2020-11-08T17:40:13Z**

Comment on attachment 9186450
Bug 1675905 - Simplify IonBuilder::createThisScripted. r?jandem!,iain!

Approved for 83.0b10, 82.0.3, GV81, and 78.4.1esr.

---

**Comment 19 — ryanvm@gmail.com — 2020-11-08T17:50:15Z**

https://hg.mozilla.org/releases/mozilla-beta/rev/f1da4198e696bbeb7c96e22ce1427655a173b243

---

**Comment 20 — ryanvm@gmail.com — 2020-11-08T18:05:05Z**

https://hg.mozilla.org/releases/mozilla-release/rev/861857e7c10478e180cc39a394377a3b1304954b (default)
https://hg.mozilla.org/releases/mozilla-release/rev/6b20179fc7ae7932cd41cc522b01a9cdf5d6271a (GECKOVIEW_81_RELBRANCH)

---

**Comment 21 — ryanvm@gmail.com — 2020-11-08T18:26:55Z**

https://hg.mozilla.org/releases/mozilla-esr78/rev/f8c30263d78e8e81b20e5f59ef0cbfeabe17f6b6 (default)
https://hg.mozilla.org/releases/mozilla-esr78/rev/22b8bef3c436a4d36b586804f342928e1ab11e51 (FIREFOX_ESR_78_4_X_RELBRANCH)

---

**Comment 22 — tom@mozilla.com — 2020-11-09T05:37:19Z**

Created attachment 9186575
advisory.txt

Attached is an advisory; if it can be improved please leave suggestions.

---

**Comment 23 — tom@mozilla.com — 2020-11-09T05:44:23Z**

Created attachment 9186576
advisory.txt

---

**Comment 24 — dveditz@mozilla.com — 2020-11-09T07:53:34Z**

Some useful background from Ted in chat that I don't see here or in phabricator. Might be good history to preserve:
>This issue is exactly the sort of problem that motivated the design of Warp. In two weeks, Warp will be shipped to Release FF83 and we hopefully can put many of this family of security issues behind us. This issue has a lot in common with [the] 0-day at start of the Whistler 2019 and was the final straw that kicked off the Warp project. A huge congrats to @jandem and all the others for getting this designed, built, and shipped in less than a year. We've focused on the performance side mostly when discussing Warp, but improving security was one of the biggest motivations behind the scenes.

---

**Comment 25 — jdemooij@mozilla.com — 2020-11-09T08:13:02Z**

(In reply to Tom Ritter [:tjr] (ni? for response to sec-[advisories/bounties/ratings/cves]) from comment #23)
> Attached is an advisory; if it can be improved please leave suggestions.

Looks good to me, but the text is truncated at the end.

---

**Comment 26 — daniel.cicas@softvision.ro — 2020-11-09T09:39:20Z**

Hello everybody!

QA has managed to verify this issue on Win 10, Ubuntu 18 and mac OS (Cristi Fogel thank you!).  We managed to verify this bug on Fx 83.0b10, Nightly 84.0a1 (BuildID:20201108093650),   Fx 82.0.3,  Fx DevEd 83.0b10 and Firefox esr treeherder build (https://treeherder.mozilla.org/jobs?repo=mozilla-esr78&revision=f8c30263d78e8e81b20e5f59ef0cbfeabe17f6b6).

Once esr is officially built we can have a quick pass at it if you feel its necessary.

---

**Comment 27 — ohorvath@mozilla.com — 2020-11-09T14:45:33Z**

The bug fix was also verified on mobile on the following builds and devices:
- versions: Nightly 84, Beta 83.0.0-beta.4 & RC 82.1.3, Focus Beta 8.8.4
- devices:  Xiaomi Mi Pad 2 (Android 5.1, x86), OnePlus A3 (Android 6.0.1), Nexus 9 (Android 7.1.1), Motorola Moto G6 (Android 8), Google Pixel 3a (Android 11), Huawei Mate 20 Lite (Android 10).

---

**Comment 28 — daniel.cicas@softvision.ro — 2020-11-11T09:49:25Z**

Hello,

Verified the official esr 78.5.0 for good measure. No issues.

---

**Comment 29 — release-mgmt-account-bot@mozilla.tld — 2020-11-11T17:00:11Z**

As part of a security bug pattern analysis, we are requesting your help with a high level analysis of this bug. It is our hope to develop static analysis (or potentially runtime/dynamic analysis) in the future to identify classes of bugs.

Please visit [this google form](https://docs.google.com/forms/d/e/1FAIpQLSe9uRXuoMK6tRglbNL5fpXbun_oEb6_xC2zpuE_CKA_GUjrvA/viewform?usp=pp_url&entry.2124261401=https%3A%2F%2Fbugzilla.mozilla.org%2Fshow_bug.cgi%3Fid%3D1675905) to reply.
