# Assertion failure: IsBackgroundFinalizedWhenTenured(a) == IsBackgroundFinalizedWhenTenured(b), at /builds/worker/checkouts/gecko/js/src/vm/JSObject.cpp:1226

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1834711
CVE: CVE-2023-37202
Component: JavaScript Engine
Bounty: (unknown)
Date: 2023-05-24T08:24:13Z
Keywords: regression, reporter-external, sec-high

Run following javascript code
```
const v3 = newGlobal();
v3.nukeAllCCWs();
const v13 = this.transplantableObject(v3);
const v27 = newGlobal({"newCompartment": true});

try {
    const t45 = v27.DataView;
    const v29 = new t45(v27);
} catch(e30) {
}

v27.firstGlobalInCompartment(v13.object);
v13.transplant(v3);
```
Stacktrace
```
#0  0x0000555556f4913d in JSObject::swap(JSContext*, JS::Handle<JSObject*>, JS::Handle<JSObject*>, js::AutoEnterOOMUnsafeRegion&) ()
#1  0x00005555572c903d in js::RemapDeadWrapper(JSContext*, JS::Handle<JSObject*>, JS::Handle<JSObject*>) ()
#2  0x00005555572c8ba4 in js::RemapWrapper(JSContext*, JSObject*, JSObject*) ()
#3  0x00005555572c9770 in js::RemapAllWrappersForObject(JSContext*, JS::Handle<JSObject*>, JS::Handle<JSObject*>) ()
#4  0x0000555557270f25 in JS_TransplantObject(JSContext*, JS::Handle<JSObject*>, JS::Handle<JSObject*>) ()
#5  0x0000555556bd9808 in TransplantObject(JSContext*, unsigned int, JS::Value*) ()
#6  0x0000555556d0dff6 in CallJSNative(JSContext*, bool (*)(JSContext*, unsigned int, JS::Value*), js::CallReason, JS::CallArgs const&) ()
#7  0x0000555556d0d786 in js::InternalCallOrConstruct(JSContext*, JS::CallArgs const&, js::MaybeConstruct, js::CallReason) ()
#8  0x0000555556d1bc1b in js::Interpret(JSContext*, js::RunState&) ()
#9  0x0000555556d0ccda in js::RunScript(JSContext*, js::RunState&) ()
#10 0x0000555556d1045b in js::ExecuteKernel(JSContext*, JS::Handle<JSScript*>, JS::Handle<JSObject*>, js::AbstractFramePtr, JS::MutableHandle<JS::Value>) ()
#11 0x0000555556d109a0 in js::Execute(JSContext*, JS::Handle<JSScript*>, JS::Handle<JSObject*>, JS::MutableHandle<JS::Value>) ()
#12 0x0000555556e55120 in ExecuteScript(JSContext*, JS::Handle<JSObject*>, JS::Handle<JSScript*>, JS::MutableHandle<JS::Value>) ()
#13 0x0000555556e5535c in JS_ExecuteScript(JSContext*, JS::Handle<JSScript*>) ()
#14 0x0000555556be2ae9 in RunFile(JSContext*, char const*, _IO_FILE*, CompileUtf8, bool, bool) ()
#15 0x0000555556be20b0 in Process(JSContext*, char const*, bool, FileKind) ()
#16 0x0000555556b7d20d in Shell(JSContext*, js::cli::OptionParser*) ()
#17 0x0000555556b76fb0 in main ()
```

---

**Comment 1 — dveditz@mozilla.com — 2023-05-24T21:11:38Z**

This doesn't seem like the kind of thing content could do. Some of the actions could be caused to happen by opening and closing windows, but probably not with the control needed in this testcase.

---

**Comment 2 — mgaudet@mozilla.com — 2023-05-30T16:06:51Z**

Hey Jon, 

This bug seems to be related to last year's work to transplant nursery objects (bug 1765338). It strikes me as potentially shell only, but may be worth a look.

---

**Comment 3 — release-mgmt-account-bot@mozilla.tld — 2023-05-31T12:42:08Z**

Set release status flags based on info from the regressing bug 1765338

---

**Comment 4 — jcoppeard@mozilla.com — 2023-05-31T16:19:35Z**

Created attachment 9336811
Bug 1834711 - Set background finalized flag for dead object proxes created after nuking all CCWs r?jandem


The background finalized flag wasn't getting set in the second overload of
NewDeadProxyObject. The patch makes the first overload of this function more
generic so it can accept non-proxy arguments and uses it in all cases.

The testcase also results in dead object proxies being returned from rewrap()
in RemapDeadWrapper which previously cased an assertion. I added an early
return for this case - do you think that's OK?

---

**Comment 5 — jcoppeard@mozilla.com — 2023-05-31T16:20:33Z**

Created attachment 9336812
Bug 1834711 - Add testcase r?jandem



Depends on D179576

---

**Comment 6 — dveditz@mozilla.com — 2023-05-31T21:57:28Z**

Jon: is this a security problem for Firefox? Or is Matthew right this is shell (and chrome?) only?

---

**Comment 7 — jcoppeard@mozilla.com — 2023-06-01T09:19:10Z**

(In reply to Daniel Veditz [:dveditz] from comment #6)
The testcase relies on shell test functionality to reproduce the problem.

I don't know whether this is possible in the browser.  It would require transplanting an object after we have nuked all CCWs for the current compartment.  I suspect that is not possible, but I don't know for sure.

---

**Comment 8 — continuation@gmail.com — 2023-06-01T13:40:35Z**

Peter, can we run JS code that could do a transplant after we nuke a window in WindowDestroyedEvent? My vague recollection is that we are still running JS at that point, and we're only killing chrome to content references when we do that, so you could still have a reference to another global to transplant into or something? Thanks.

---

**Comment 9 — jcoppeard@mozilla.com — 2023-06-05T13:54:07Z**

Comment on attachment 9336811
Bug 1834711 - Set background finalized flag for dead object proxes created after nuking all CCWs r?jandem

### Security Approval Request
* **How easily could an exploit be constructed based on the patch?**: Extremely difficult.
* **Do comments in the patch, the check-in comment, or tests included in the patch paint a bulls-eye on the security problem?**: No
* **Which older supported branches are affected by this flaw?**: Everything back to 101
* **If not all supported branches, which bug introduced the flaw?**: None
* **Do you have backports for the affected branches?**: No
* **If not, how different, hard to create, and risky will they be?**: This patch should apply but I haven't tested this.
* **How likely is this patch to cause regressions; how much testing does it need?**: Unlikley.  This cleans up setting flags for dead object proxy to make it more obviously correct.
* **Is Android affected?**: Yes

---

**Comment 10 — jcoppeard@mozilla.com — 2023-06-05T13:54:59Z**

I've requested approval to land the patch, but I don't know what sec rating this should be.  I'm not even sure this is something that could be triggered in the browser.

---

**Comment 11 — tom@mozilla.com — 2023-06-05T19:25:31Z**

Comment on attachment 9336811
Bug 1834711 - Set background finalized flag for dead object proxes created after nuking all CCWs r?jandem

Approved to land and request uplift

---

**Comment 12 — tom@mozilla.com — 2023-06-05T19:29:35Z**

If you do need to uplift it here's a reminder for landing tests.

---

**Comment 13 — release-mgmt-account-bot@mozilla.tld — 2023-06-06T16:44:04Z**

Set release status flags based on info from the regressing bug 1765338

---

**Comment 14 — ryanvm@gmail.com — 2023-06-07T03:42:08Z**

https://hg.mozilla.org/mozilla-central/rev/a4d881b1f4ed

---

**Comment 15 — continuation@gmail.com — 2023-06-07T14:05:44Z**

It would be good to get confirmation from Peter, but I think this is at least in the ballpark of something that could really happen on a web page if you worked at it hard enough, so I'm going to mark it sec-high.

---

**Comment 16 — ryanvm@gmail.com — 2023-06-08T02:36:51Z**

Please nominate this for Beta approval when you get a chance. It'll also need a rebased patch for ESR102.

---

**Comment 17 — jcoppeard@mozilla.com — 2023-06-14T14:44:35Z**

Comment on attachment 9336811
Bug 1834711 - Set background finalized flag for dead object proxes created after nuking all CCWs r?jandem

### Beta/Release Uplift Approval Request
* **User impact if declined**: Possible crash / security vulnerability.
* **Is this code covered by automated tests?**: Yes
* **Has the fix been verified in Nightly?**: Yes
* **Needs manual test from QE?**: No
* **If yes, steps to reproduce**: 
* **List of other uplifts needed**: None
* **Risk to taking this patch**: Low
* **Why is the change risky/not risky? (and alternatives if risky)**: This change fixes the logic around creating dead objects proxies and the result is simpler and more obviously correct than before.  This change has been on central for a week with no regressions found.
* **String changes made/needed**: 
* **Is Android affected?**: Yes

---

**Comment 18 — jcoppeard@mozilla.com — 2023-06-14T15:11:44Z**

Created attachment 9339088
Bug 1834711 - Set background finalized flag for dead object proxes created after nuking all CCWs r=jandem (ESR102)


The background finalized flag wasn't getting set in the second overload of
NewDeadProxyObject. The patch makes the first overload of this function more
generic so it can accept non-proxy arguments and uses it in all cases.

The testcase also results in dead object proxies being returned from rewrap()
in RemapDeadWrapper which previously cased an assertion. I added an early
return for this case - do you think that's OK?

---

**Comment 19 — jcoppeard@mozilla.com — 2023-06-14T15:13:55Z**

Comment on attachment 9339088
Bug 1834711 - Set background finalized flag for dead object proxes created after nuking all CCWs r=jandem (ESR102)

### ESR Uplift Approval Request
* **If this is not a sec:{high,crit} bug, please state case for ESR consideration**: This is a sec-high bug
* **User impact if declined**: Possible crash / security vulnerability.
* **Fix Landed on Version**: 116
* **Risk to taking this patch**: Low
* **Why is the change risky/not risky? (and alternatives if risky)**: This change fixes the logic around creating dead objects proxies and the result is simpler and more obviously correct than before. This change has been on central for a week with no regressions found.

---

**Comment 20 — dmeehan@mozilla.com — 2023-06-14T18:56:17Z**

Comment on attachment 9336811
Bug 1834711 - Set background finalized flag for dead object proxes created after nuking all CCWs r?jandem

Approved for 115.0b6.

---

**Comment 21 — dmeehan@mozilla.com — 2023-06-14T19:23:20Z**

https://hg.mozilla.org/releases/mozilla-beta/rev/c5d9308166ae

---

**Comment 22 — dmeehan@mozilla.com — 2023-06-15T14:25:40Z**

Comment on attachment 9339088
Bug 1834711 - Set background finalized flag for dead object proxes created after nuking all CCWs r=jandem (ESR102)

Approved for 102.13esr.

---

**Comment 23 — dmeehan@mozilla.com — 2023-06-15T14:29:40Z**

https://hg.mozilla.org/releases/mozilla-esr102/rev/145eb64b95c1

---

**Comment 24 — dveditz@mozilla.com — 2023-06-27T18:23:08Z**

We'll go ahead and assume this is really triggerable from content and therefore sec-high for bug bounty purposes, but if we get proof of that (a POC that runs in a web page) we can raise the bounty amount we are awarding.

---

**Comment 25 — jkratzer@mozilla.com — 2023-06-28T13:35:12Z**

Created attachment 9341517
advisory.txt

---

**Comment 26 — release-mgmt-account-bot@mozilla.tld — 2023-08-15T12:00:48Z**

2 months ago, tjr placed a reminder on the bug using the whiteboard tag `[reminder-test 2023-08-15]` .

jonco, please refer to the original comment to better understand the reason for the reminder.

---

**Comment 27 — pulsebot@bmo.tld — 2023-08-15T12:16:34Z**

Pushed by jcoppeard@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/34ea39f6bd8a
Add testcase r=jandem

---

**Comment 28 — ryanvm@gmail.com — 2023-08-16T03:49:47Z**

https://hg.mozilla.org/mozilla-central/rev/34ea39f6bd8a
