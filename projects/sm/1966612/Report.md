# pwn2own-2025-1: First entry from May 16th (out of bounds write in promiseAllSettled)

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1966612
CVE: CVE-2025-4918
Component: JavaScript Engine
Bounty: (unknown)
Date: 2025-05-15T10:10:26Z
Keywords: csectype-bounds, pernosco, regression, sec-critical

This is the placeholder bug for the first pwn2own entry that we are going to receive tomorrow (May 16th 2025). Creating it now such that access is going to be widely available and granted ahead of time.

This entry is credited to Edouard Bochin (@le_douds) and Tao Yan (@Ga1ois) from Palo Alto Networks.

---

**Comment 1 — fbraun@mozilla.com — 2025-05-16T10:01:40Z**

Created attachment 9488275
poc.js

---

**Comment 2 — fbraun@mozilla.com — 2025-05-16T10:01:52Z**

Created attachment 9488276
ff.html

---

**Comment 3 — fbraun@mozilla.com — 2025-05-16T10:02:03Z**

Created attachment 9488277
Spdy .pdf

---

**Comment 4 — choller@mozilla.com — 2025-05-16T11:17:32Z**

I was able to build the JS shell on the revision where we landed the initial API and was able to reproduce using the PoC.

---

**Comment 5 — fbraun@mozilla.com — 2025-05-16T11:55:57Z**

Comment on attachment 9488275
poc.js

We just checked. The attachments are safe to read, use and debug on your own computer without doing any harm.

---

**Comment 6 — release-mgmt-account-bot@mozilla.tld — 2025-05-16T12:20:54Z**

The bug is marked as tracked for firefox138 (release), tracked for firefox139 (beta) and tracked for firefox140 (nightly). We have limited time to fix this, the soft freeze is in 6 days. However, the bug still isn't assigned.

:sdetar, could you please find an assignee for this tracked bug? Given that it is a regression and we know the cause, we could also simply backout the regressor. If you disagree with the tracking decision, please talk with the release managers.

For more information, please visit [BugBot documentation](https://wiki.mozilla.org/BugBot#tracked_attention.py).

---

**Comment 7 — bugmon@mozilla.com — 2025-05-16T13:51:08Z**

Successfully recorded a pernosco session.  A link to the pernosco session will be added here shortly.

---

**Comment 8 — jdemooij@mozilla.com — 2025-05-16T14:07:19Z**

Created attachment 9488325
Bug 1966612 - Fix promise combinator function state. r?arai!

---

**Comment 9 — jdemooij@mozilla.com — 2025-05-16T15:25:07Z**

This is a very subtle bug in our implementation of `Promise.allSettled`. It does not affect similar builtins such as `Promise.all`.

First things first: I couldn't have done the analysis to fix this bug without Arai's help :)

---

Simplified a lot: `Promise.allSettled` typically takes an array of promises and returns a promise that resolves to a new array of objects.

The JS spec has a function called `PerformPromiseAllSettled` [defined here](https://tc39.es/ecma262/#sec-performpromiseallsettled). For each element in the input array, it creates a pair of functions: `onFulfilled` and `onRejected`. We must invoke only one of these two functions (so one call per array element). The spec does this with a shared `alreadyCalled` `Record` that both functions point to in their `[[AlreadyCalled]]` slot.

In our implementation we stored this state for each function separately. This was *mostly* okay because [we did handle](https://searchfox.org/mozilla-central/rev/fccab99f5b400b33b9ad16e7f066a5020119fbdc/js/src/builtin/Promise.cpp#4426-4437) this in `PromiseAllSettledElementFunction` by checking if the result array we allocated for `allSettled` already had a non-`undefined` value for the specific array index. In that case we knew we already called the other function of the pair so we just returned immediately.

The bug here is that the result array we build up is passed directly to JS code once we've processed all elements (when the `remainingElementsCount` drops to 0). This means you could have the following situation:
1. Invoke one function of the pair for the last array element, say the `onFulfilled` function.
2. We notice we're now done with all promises so we pass the result array to JS.
3. Malicious JS code invokes the *other* function of the pair (`onRejected` in this case). This will access the result array again in `PromiseAllSettledElementFunction` to check 'did we already handle this array element'. However because we have already exposed this array to JS in (2), it's no longer safe to access the array and make assumptions about its length and values.
  
The simplest fix we could think of is to change the second function of the pair to point to the first one, and then always use the first function's state instead of storing it separately for the two functions. This avoids the need for the additional check in `PromiseAllSettledElementFunction`.

---

**Comment 10 — jdemooij@mozilla.com — 2025-05-16T15:58:10Z**

Comment on attachment 9488325
Bug 1966612 - Fix promise combinator function state. r?arai!

### Security Approval Request
* **How easily could an exploit be constructed based on the patch?**: It's possible but not very easy.
* **Do comments in the patch, the check-in comment, or tests included in the patch paint a bulls-eye on the security problem?**: No
* **Which branches (beta, release, and/or ESR) are affected by this flaw, and do the release status flags reflect this affected/unaffected state correctly?**: All
* **If not all supported branches, which bug introduced the flaw?**: None
* **Do you have backports for the affected branches?**: Yes
* **If not, how different, hard to create, and risky will they be?**: According to ryanvm the patch applies to 115+, so hopefully we can just uplift it without any problems.
* **How likely is this patch to cause regressions; how much testing does it need?**: We went with the simplest fix we could think of so fairly low risk but it is complicated code. decoder is fuzzing the patch already.
* **Is the patch ready to land after security approval is given?**: Yes
* **Is Android affected?**: Yes

---

**Comment 11 — tom@mozilla.com — 2025-05-16T16:26:54Z**

Comment on attachment 9488325
Bug 1966612 - Fix promise combinator function state. r?arai!

approved to land.  This will sit on -release in public for a day before we spin releases, but the benefits of doing so outweigh the risks.  This is a content-process only bug, so you'd need a sandbox escape - the rarer of the beasts - to get much use out of it.  And because it is an older bug the risk of introducing a problem on a release branch (esr155, esr128, -release) is elevated and we would like to know ASAP if this does cause a test failure or other issue.

---

**Comment 12 — pulsebot@bmo.tld — 2025-05-16T16:54:16Z**

Pushed by dsmith@mozilla.com:
https://hg.mozilla.org/mozilla-central/rev/61e8f954db8a
Fix promise combinator function state. r=arai,a=dsmith

---

**Comment 13 — dsmith@mozilla.com — 2025-05-16T17:13:19Z**

Created attachment 9488387
Bug 1966612 - Fix promise combinator function state. r?arai!



Original Revision: https://phabricator.services.mozilla.com/D249782

---

**Comment 14 — phab-bot@bmo.tld — 2025-05-16T17:16:15Z**

### firefox-beta Uplift Approval Request
- **User impact if declined**: pwn2own
- **Code covered by automated testing**: no
- **Fix verified in Nightly**: yes
- **Needs manual QE test**: yes
- **Steps to reproduce for manual QE testing**: N/A
- **Risk associated with taking this patch**: N/A
- **Explanation of risk level**: pwn2own
- **String changes made/needed**: none
- **Is Android affected?**: yes

---

**Comment 15 — dsmith@mozilla.com — 2025-05-16T17:17:00Z**

Created attachment 9488388
Bug 1966612 - Fix promise combinator function state. r?arai!



Original Revision: https://phabricator.services.mozilla.com/D249782

---

**Comment 16 — phab-bot@bmo.tld — 2025-05-16T17:17:45Z**

### firefox-esr115 Uplift Approval Request
- **User impact if declined**: pwn2own
- **Code covered by automated testing**: no
- **Fix verified in Nightly**: yes
- **Needs manual QE test**: yes
- **Steps to reproduce for manual QE testing**: N/A
- **Risk associated with taking this patch**: N/A
- **Explanation of risk level**: pwn2own
- **String changes made/needed**: none
- **Is Android affected?**: yes

---

**Comment 17 — pulsebot@bmo.tld — 2025-05-16T17:23:45Z**

https://hg.mozilla.org/releases/mozilla-beta/rev/6293cfe0ed6f

---

**Comment 18 — dsmith@mozilla.com — 2025-05-16T17:25:58Z**

Created attachment 9488390
Bug 1966612 - Fix promise combinator function state. r?arai!



Original Revision: https://phabricator.services.mozilla.com/D249782

---

**Comment 19 — phab-bot@bmo.tld — 2025-05-16T17:26:38Z**

### firefox-release Uplift Approval Request
- **User impact if declined**: pwn2own
- **Code covered by automated testing**: no
- **Fix verified in Nightly**: yes
- **Needs manual QE test**: yes
- **Steps to reproduce for manual QE testing**: N/A
- **Risk associated with taking this patch**: N/A
- **Explanation of risk level**: pwn2own
- **String changes made/needed**: none
- **Is Android affected?**: yes

---

**Comment 20 — dsmith@mozilla.com — 2025-05-16T17:27:12Z**

Created attachment 9488392
Bug 1966612 - Fix promise combinator function state. r?arai!



Original Revision: https://phabricator.services.mozilla.com/D249782

---

**Comment 21 — phab-bot@bmo.tld — 2025-05-16T17:27:35Z**

### firefox-esr128 Uplift Approval Request
- **User impact if declined**: pwn2own
- **Code covered by automated testing**: no
- **Fix verified in Nightly**: no
- **Needs manual QE test**: yes
- **Steps to reproduce for manual QE testing**: N/A
- **Risk associated with taking this patch**: N/A
- **Explanation of risk level**: pwn2own
- **String changes made/needed**: None
- **Is Android affected?**: yes

---

**Comment 22 — pulsebot@bmo.tld — 2025-05-16T17:39:28Z**

https://hg.mozilla.org/releases/mozilla-release/rev/0ba4fa9d5eaf

---

**Comment 23 — pulsebot@bmo.tld — 2025-05-16T17:40:28Z**

(128.11esr) https://hg.mozilla.org/releases/mozilla-esr128/rev/b5a272e9b063

---

**Comment 24 — pulsebot@bmo.tld — 2025-05-16T17:40:54Z**

(115.24esr) https://hg.mozilla.org/releases/mozilla-esr115/rev/bad446550e1a

---

**Comment 25 — pulsebot@bmo.tld — 2025-05-16T20:42:21Z**

(128.10.1esr) https://hg.mozilla.org/releases/mozilla-esr128/rev/776b70c0793c

---

**Comment 26 — pulsebot@bmo.tld — 2025-05-16T21:02:59Z**

(115.23.1esr) https://hg.mozilla.org/releases/mozilla-esr115/rev/b8343b8f2730

---

**Comment 27 — mboldan@mozilla.com — 2025-05-17T07:27:23Z**

I managed to reproduce the issue on Firefox 139.0b9, under macOS 10.15.
Verified the issue with the treeherder builds and no crash occurred. The issue was verified on Firefox 115.23.1ESR, Firefox 128.11.0ESR, Firefox 138.0.4 and on Firefox 139.0b10.
Tests were covered under Windows 11, Ubuntu 22.04 and under macOS 10.15.

---

**Comment 28 — dpop@mozilla.com — 2025-05-17T09:56:57Z**

The patch is verified as fixed on Fenix and Focus:
Nightly build: 
- latest build from FTP - confirming the fix is in place for both Fenix and Focus using these builds
- from Treeherder - we were able to install only the debug version - confirming the fix is in place for both Fenix and Focus using these builds

Beta build:
- from Treeherder - we were able to install only the debug version - confirming the fix is in place for both Fenix and Focus using these builds

Release build
 - from Treeherder - we were able to install only the debug version - confirming the fix is in place for both Fenix and Focus using these builds

Tested with Nothing Phone (2a) 5G (Android 14), Google Pixel 9 (Android 15) and LG G7 fit (Android 9).

---

**Comment 29 — bugmon@mozilla.com — 2025-05-17T11:14:29Z**

Verified bug as fixed on rev mozilla-central 20250516214029-11cba058a68e.
Removing bugmon keyword as no further action possible.  Please review the bug and re-add the keyword for further analysis.

---

**Comment 30 — fbraun@mozilla.com — 2025-05-17T11:30:21Z**

Created attachment 9488479
advisory.txt

---

**Comment 31 — bugmon@mozilla.com — 2025-05-17T12:33:10Z**

Verified bug as fixed on rev mozilla-central 20250516214029-11cba058a68e.
Removing bugmon keyword as no further action possible.  Please review the bug and re-add the keyword for further analysis.

---

**Comment 32 — dpop@mozilla.com — 2025-05-18T07:30:53Z**

Verified as fixed for mobile as well, on the following builds:
Firefox for Android:
- Nightly 140.0a1 from 05/17
- Beta 139.0b10
- 138.0.4

Focus for Android:
- Nightly 140.0a1 from 05/17
- Beta 139.0b10
- 138.0.4

Tested with Nothing Phone (2a) 5G (Android 14), Lenovo Yoga Tab 11 (Android 12) and Motorola Nexus 6 (Android 8).

---

**Comment 33 — pulsebot@bmo.tld — 2025-07-08T16:11:02Z**

Pushed by jdemooij@mozilla.com:
https://github.com/mozilla-firefox/firefox/commit/7f47d311b5b5
https://hg.mozilla.org/integration/autoland/rev/98641a09b270
1966964: apply code formatting via Lando

---

**Comment 34 — aryx.bugmail@gmx-topmail.de — 2025-07-08T21:10:30Z**

https://hg.mozilla.org/mozilla-central/rev/98641a09b270
