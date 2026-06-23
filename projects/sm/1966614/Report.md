# pwn2own-2025-2: Second entry from May 17th (Incorrect bounds check elimination when using ExtractLinearSum)

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1966614
CVE: CVE-2025-4919
Component: JavaScript Engine: JIT
Bounty: (unknown)
Date: 2025-05-15T10:11:46Z
Keywords: csectype-jit, perf-alert, pernosco, sec-critical
See Also:
- https://www.zerodayinitiative.com/blog/2025/7/14/cve-2025-4919-corruption-via-math-space-in-mozilla-firefox

This is the placeholder bug for the first pwn2own entry that we are going to receive tomorrow (May 17th 2025). Creating it now such that access is going to be widely available and granted ahead of time.

This entry is credited to Manfred Paul (`@manf@infosec.exchange`).

---

**Comment 1 — fbraun@mozilla.com — 2025-05-17T10:23:59Z**

Created attachment 9488466
writeup.pdf

---

**Comment 2 — fbraun@mozilla.com — 2025-05-17T10:24:16Z**

Created attachment 9488467
expl.js (not defangled yet)

---

**Comment 3 — fbraun@mozilla.com — 2025-05-17T10:24:32Z**

Created attachment 9488468
index.html (not defangled yet)

---

**Comment 4 — fbraun@mozilla.com — 2025-05-17T10:27:45Z**

Created attachment 9488470
macos-lldb-backtrace.txt

---

**Comment 5 — choller@mozilla.com — 2025-05-17T10:35:37Z**

Created attachment 9488472
Javascript Shell Testcase

---

**Comment 6 — jdemooij@mozilla.com — 2025-05-17T11:23:00Z**

This is a problem with `ExtractLinearSum` in the JIT backend as explained in the excellent write-up.

This function supports 'modulo' and 'infinite' math spaces. The former doesn't work well for bounds check optimizations. In practice this was not an issue until we added support for large array buffers and typed arrays (enabled in bug 1703505).

It's possible this only affects processes with Spectre mitigations off (IIRC that's Fission content processes on desktop) but I'm not 100% sure about this and we shouldn't rely on it.

---

**Comment 7 — fbraun@mozilla.com — 2025-05-17T11:28:38Z**

Created attachment 9488477
advisory.txt

---

**Comment 8 — choller@mozilla.com — 2025-05-17T11:30:16Z**

(In reply to Jan de Mooij [:jandem] from comment #6)

> It's possible this only affects processes with Spectre mitigations off (IIRC that's Fission content processes on desktop) but I'm not 100% sure about this and we shouldn't rely on it.

Manfred also mentioned that Spectre mitigations break this reliably because the value is folded once more back into positive as far as I understood.

---

**Comment 9 — jdemooij@mozilla.com — 2025-05-17T11:57:26Z**

Created attachment 9488481
Bug 1966614 - Don't support modulo math space in ExtractLinearSum. r?iain!

---

**Comment 10 — jdemooij@mozilla.com — 2025-05-17T13:01:38Z**

Created attachment 9488486
Small standalone browser test

---

**Comment 11 — jdemooij@mozilla.com — 2025-05-17T13:05:47Z**

Created attachment 9488487
Small standalone browser test

---

**Comment 12 — continuation@gmail.com — 2025-05-17T13:25:02Z**

Per some discussion on Slack from jandem, it appears that Spectre mitigations prevent the crash in the test case. This means that the test case won't crash either on Android or when run via a `file://` URI.

---

**Comment 13 — pulsebot@bmo.tld — 2025-05-17T14:04:27Z**

Pushed by dsmith@mozilla.com:
https://hg.mozilla.org/mozilla-central/rev/3197c34f492e
Don't support modulo math space in ExtractLinearSum. r=iain, a=dsmith

---

**Comment 14 — dsmith@mozilla.com — 2025-05-17T14:18:51Z**

Comment on attachment 9488481
Bug 1966614 - Don't support modulo math space in ExtractLinearSum. r?iain!

Approved for 139.0b10
Approved for 138.0.4 dot release
Approved for 115.23.1esr
Approved for 128.10.1esr

---

**Comment 15 — pulsebot@bmo.tld — 2025-05-17T14:28:53Z**

https://hg.mozilla.org/releases/mozilla-beta/rev/5ff373e38736

---

**Comment 16 — pulsebot@bmo.tld — 2025-05-17T14:32:48Z**

https://hg.mozilla.org/releases/mozilla-release/rev/e97029d1cfe4

---

**Comment 17 — pulsebot@bmo.tld — 2025-05-17T14:35:04Z**

(115.24esr) https://hg.mozilla.org/releases/mozilla-esr115/rev/a595d9d9a723

---

**Comment 18 — pulsebot@bmo.tld — 2025-05-17T14:36:48Z**

(128.11esr) https://hg.mozilla.org/releases/mozilla-esr128/rev/b5906e8547be

---

**Comment 19 — pulsebot@bmo.tld — 2025-05-17T15:14:31Z**

(115.23.1esr) https://hg.mozilla.org/releases/mozilla-esr115/rev/977d574cef3e

---

**Comment 20 — pulsebot@bmo.tld — 2025-05-17T15:21:04Z**

(128.10.1esr) https://hg.mozilla.org/releases/mozilla-esr128/rev/cf43f46ebc3d

---

**Comment 21 — dpop@mozilla.com — 2025-05-18T07:32:18Z**

Verified as fixed for mobile, on the following builds:
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

**Comment 22 — bugmon@mozilla.com — 2025-05-19T02:46:35Z**

Verified bug as fixed on rev mozilla-central 20250518220019-8e9456975478.
Successfully recorded a pernosco session.  A link to the pernosco session will be added here shortly.
Removing bugmon keyword as no further action possible.  Please review the bug and re-add the keyword for further analysis.

---

**Comment 23 — bugmon@mozilla.com — 2025-05-19T03:35:17Z**

A pernosco session for this bug can be found [here](https://pernos.co/debug/Qk0tpZuCqCkulD7nlgHlxA/index.html).

---

**Comment 24 — mboldan@mozilla.com — 2025-05-20T06:52:41Z**

Managed to reproduce the issue on 140.0a1 (2025-05-16).
Confirming the fix also on Firefox 115.24 ESR, Firefox 128.11 ESR and on Firefox 140.0a1 (2025-05-19).

---

**Comment 25 — afinder@mozilla.com — 2025-05-27T11:30:57Z**

(In reply to Pulsebot from comment #13)
> Pushed by dsmith@mozilla.com:
> https://hg.mozilla.org/mozilla-central/rev/3197c34f492e
> Don't support modulo math space in ExtractLinearSum. r=iain, a=dsmith


Perfherder has detected a browsertime performance change from push [46e4a93846b20b6a408f4be3876276320f6695af](https://hg.mozilla.org/integration/autoland/pushloghtml?changeset=46e4a93846b20b6a408f4be3876276320f6695af).

If you have any questions, please reach out to a performance sheriff. Alternatively, you can find help on Slack by joining [#perf-help](https://mozilla.enterprise.slack.com/archives/C03U19JCSFQ), and on Matrix you can find help by joining [#perftest](https://matrix.to/#/#perftest:mozilla.org).

### Improvements:

| **Ratio** | **Test** | **Platform** | **Options** | **Absolute values (old vs new)** |  **Performance Profiles** | 
|--|--|--|--|--|--| 
| [4%](https://treeherder.mozilla.org/perfherder/graphs?timerange=1209600&series=autoland,3777175,1,13)  | [google-docs](https://firefox-source-docs.mozilla.org/testing/perfdocs/raptor.html#google-docs-d) PerceptualSpeedIndex | linux1804-64-shippable-qr | fission warm webrender | 2,394.15 -> 2,302.90 | [Before](https://profiler.firefox.com/from-url/https%3A%2F%2Ffirefox-ci-tc.services.mozilla.com%2Fapi%2Fqueue%2Fv1%2Ftask%2FBBHVCm86SUu6kmzz5xySAg%2Fruns%2F0%2Fartifacts%2Fpublic%2Ftest_info%2Fprofile_google-docs.zip)/[After](https://profiler.firefox.com/from-url/https%3A%2F%2Ffirefox-ci-tc.services.mozilla.com%2Fapi%2Fqueue%2Fv1%2Ftask%2FACGcQX0iTqGrdQzc52OhMQ%2Fruns%2F0%2Fartifacts%2Fpublic%2Ftest_info%2Fprofile_google-docs.zip) |
| [4%](https://treeherder.mozilla.org/perfherder/graphs?timerange=1209600&series=autoland,3777172,1,13)  | [google-docs](https://firefox-source-docs.mozilla.org/testing/perfdocs/raptor.html#google-docs-d) LastVisualChange | linux1804-64-shippable-qr | fission warm webrender | 5,221.32 -> 5,027.28 | [Before](https://profiler.firefox.com/from-url/https%3A%2F%2Ffirefox-ci-tc.services.mozilla.com%2Fapi%2Fqueue%2Fv1%2Ftask%2FBBHVCm86SUu6kmzz5xySAg%2Fruns%2F0%2Fartifacts%2Fpublic%2Ftest_info%2Fprofile_google-docs.zip)/[After](https://profiler.firefox.com/from-url/https%3A%2F%2Ffirefox-ci-tc.services.mozilla.com%2Fapi%2Fqueue%2Fv1%2Ftask%2FACGcQX0iTqGrdQzc52OhMQ%2Fruns%2F0%2Fartifacts%2Fpublic%2Ftest_info%2Fprofile_google-docs.zip) |
| [4%](https://treeherder.mozilla.org/perfherder/graphs?timerange=1209600&series=autoland,3777169,1,13)  | [google-docs](https://firefox-source-docs.mozilla.org/testing/perfdocs/raptor.html#google-docs-d) PerceptualSpeedIndex | linux1804-64-shippable-qr | cold fission webrender | 3,024.09 -> 2,913.38 | [Before](https://profiler.firefox.com/from-url/https%3A%2F%2Ffirefox-ci-tc.services.mozilla.com%2Fapi%2Fqueue%2Fv1%2Ftask%2FBBHVCm86SUu6kmzz5xySAg%2Fruns%2F0%2Fartifacts%2Fpublic%2Ftest_info%2Fprofile_google-docs.zip)/[After](https://profiler.firefox.com/from-url/https%3A%2F%2Ffirefox-ci-tc.services.mozilla.com%2Fapi%2Fqueue%2Fv1%2Ftask%2FACGcQX0iTqGrdQzc52OhMQ%2Fruns%2F0%2Fartifacts%2Fpublic%2Ftest_info%2Fprofile_google-docs.zip) |
| [4%](https://treeherder.mozilla.org/perfherder/graphs?timerange=1209600&series=autoland,3777166,1,13)  | [google-docs](https://firefox-source-docs.mozilla.org/testing/perfdocs/raptor.html#google-docs-d) LastVisualChange | linux1804-64-shippable-qr | cold fission webrender | 5,810.53 -> 5,607.35 | [Before](https://profiler.firefox.com/from-url/https%3A%2F%2Ffirefox-ci-tc.services.mozilla.com%2Fapi%2Fqueue%2Fv1%2Ftask%2FBBHVCm86SUu6kmzz5xySAg%2Fruns%2F0%2Fartifacts%2Fpublic%2Ftest_info%2Fprofile_google-docs.zip)/[After](https://profiler.firefox.com/from-url/https%3A%2F%2Ffirefox-ci-tc.services.mozilla.com%2Fapi%2Fqueue%2Fv1%2Ftask%2FACGcQX0iTqGrdQzc52OhMQ%2Fruns%2F0%2Fartifacts%2Fpublic%2Ftest_info%2Fprofile_google-docs.zip) |
| [3%](https://treeherder.mozilla.org/perfherder/graphs?timerange=1209600&series=autoland,3777173,1,13)  | [google-docs](https://firefox-source-docs.mozilla.org/testing/perfdocs/raptor.html#google-docs-d) ContentfulSpeedIndex | linux1804-64-shippable-qr | fission warm webrender | 1,608.32 -> 1,555.40 | [Before](https://profiler.firefox.com/from-url/https%3A%2F%2Ffirefox-ci-tc.services.mozilla.com%2Fapi%2Fqueue%2Fv1%2Ftask%2FBBHVCm86SUu6kmzz5xySAg%2Fruns%2F0%2Fartifacts%2Fpublic%2Ftest_info%2Fprofile_google-docs.zip)/[After](https://profiler.firefox.com/from-url/https%3A%2F%2Ffirefox-ci-tc.services.mozilla.com%2Fapi%2Fqueue%2Fv1%2Ftask%2FACGcQX0iTqGrdQzc52OhMQ%2Fruns%2F0%2Fartifacts%2Fpublic%2Ftest_info%2Fprofile_google-docs.zip) |
|...|...|...|...|...|...|
| [3%](https://treeherder.mozilla.org/perfherder/graphs?timerange=1209600&series=autoland,3777167,1,13)  | [google-docs](https://firefox-source-docs.mozilla.org/testing/perfdocs/raptor.html#google-docs-d) ContentfulSpeedIndex | linux1804-64-shippable-qr | cold fission webrender | 1,973.94 -> 1,917.77 | [Before](https://profiler.firefox.com/from-url/https%3A%2F%2Ffirefox-ci-tc.services.mozilla.com%2Fapi%2Fqueue%2Fv1%2Ftask%2FBBHVCm86SUu6kmzz5xySAg%2Fruns%2F0%2Fartifacts%2Fpublic%2Ftest_info%2Fprofile_google-docs.zip)/[After](https://profiler.firefox.com/from-url/https%3A%2F%2Ffirefox-ci-tc.services.mozilla.com%2Fapi%2Fqueue%2Fv1%2Ftask%2FACGcQX0iTqGrdQzc52OhMQ%2Fruns%2F0%2Fartifacts%2Fpublic%2Ftest_info%2Fprofile_google-docs.zip) |


Details of the alert can be found in the [alert summary](https://treeherder.mozilla.org/perfherder/alerts?id=45219), including links to graphs and comparisons for each of the affected tests.

If you need the profiling jobs [you can trigger them yourself from treeherder job view](https://firefox-source-docs.mozilla.org/testing/perfdocs/perftest-in-a-nutshell.html#using-the-firefox-profiler) or ask a performance sheriff to do that for you.

You can run all of these tests on try with `./mach try perf --alert 45219`

The following [documentation link](https://firefox-source-docs.mozilla.org/testing/perfdocs/mach-try-perf.html#running-alert-tests) provides more information about this command.

---

**Comment 26 — continuation@gmail.com — 2025-07-15T19:24:17Z**

There's a public writeup of this now.
