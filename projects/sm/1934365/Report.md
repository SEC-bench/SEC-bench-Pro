# Crash [@ js::NativeDefineProperty] or Assertion failure: isObject(), at js/Value.h:972

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1934365
Component: JavaScript Engine
Bounty: (unknown)
Date: 2024-11-30T09:19:46Z
Keywords: assertion, crash, regression, sec-high, testcase

The following testcase crashes on mozilla-central revision 20241129-ed73389dc144 (opt build, run with --fuzzing-safe --ion-offthread-compile=off --enable-explicit-resource-management):

    evalInWorker(`
        function c() {
          d = new AsyncDisposableStack
          d.defer(() => e)
          d.defer(() => c())
          d.disposeAsync()
        } c();
    `)


Backtrace:

    received signal SIGSEGV, Segmentation fault.
    #0  0x0000555556c74ae3 in js::NativeDefineProperty(JSContext*, JS::Handle<js::NativeObject*>, JS::Handle<JS::PropertyKey>, JS::Handle<JS::PropertyDescriptor>, JS::ObjectOpResult&) ()
    #1  0x0000555556c76787 in js::NativeDefineDataProperty(JSContext*, JS::Handle<js::NativeObject*>, js::PropertyName*, JS::Handle<JS::Value>, unsigned int) ()
    #2  0x0000555556b2c165 in js::CreateSuppressedError(JSContext*, JS::Handle<JS::Value>, JS::Handle<JS::Value>) ()
    #3  0x00000b703bec032c in ?? ()
    [...]
    #24 0x0000000000000000 in ?? ()
    rax	0xfcc285f53d51bf00	-233476942327595264
    rbx	0x7ffff4f110b0	140737302827184
    rcx	0x513101df2bde0	1428334826405344
    rdx	0x7ffff4f110b0	140737302827184
    rsi	0x7ffff4f11150	140737302827344
    rdi	0x7ffff4737d00	140737294597376
    rbp	0x7ffff4f11090	140737302827152
    rsp	0x7ffff4f10fc0	140737302826944
    r8	0x7ffff4f110b8	140737302827192
    r9	0x7ffff4700c01	140737294371841
    r10	0x0	0
    r11	0x1	1
    r12	0x7ffff4f11150	140737302827344
    r13	0x7ffff4f110d8	140737302827224
    r14	0x7ffff4f110b8	140737302827192
    r15	0x7ffff4737d00	140737294597376
    rip	0x555556c74ae3 <js::NativeDefineProperty(JSContext*, JS::Handle<js::NativeObject*>, JS::Handle<JS::PropertyKey>, JS::Handle<JS::PropertyDescriptor>, JS::ObjectOpResult&)+51>
    => 0x555556c74ae3 <_ZN2js20NativeDefinePropertyEP9JSContextN2JS6HandleIPNS_12NativeObjectEEENS3_INS2_11PropertyKeyEEENS3_INS2_18PropertyDescriptorEEERNS2_14ObjectOpResultE+51>:	mov    (%rcx),%rax
       0x555556c74ae6 <_ZN2js20NativeDefinePropertyEP9JSContextN2JS6HandleIPNS_12NativeObjectEEENS3_INS2_11PropertyKeyEEENS3_INS2_18PropertyDescriptorEEERNS2_14ObjectOpResultE+54>:	mov    (%rax),%rax


Marking s-s due to crash address, likely a type confusion and sec-high.

---

**Comment 1 — choller@mozilla.com — 2024-11-30T09:19:50Z**

Created attachment 9440860
Detailed Crash Information

---

**Comment 2 — choller@mozilla.com — 2024-11-30T09:19:51Z**

Created attachment 9440861
Testcase

---

**Comment 3 — debadree333@gmail.com — 2024-12-01T12:28:08Z**

Created attachment 9440906
Bug 1934365 - Check for out of memory when creating SuppressedError. r?arai!

---

**Comment 4 — bugmon@mozilla.com — 2024-12-02T00:29:47Z**

Verified bug as reproducible on mozilla-central 20241201095257-4df19decbcec.
The bug appears to have been introduced in the following build range:
> Start: c1acf137ed794e8b553c1f40512d21090d1a9b7c (20241114072145)
> End: e299ddd844812c1cd97440fd74eb94e0736fbbe9 (20241114100954)
> Pushlog: https://hg.mozilla.org/integration/autoland/pushloghtml?fromchange=c1acf137ed794e8b553c1f40512d21090d1a9b7c&tochange=e299ddd844812c1cd97440fd74eb94e0736fbbe9

---

**Comment 5 — arai.unmht@gmail.com — 2024-12-02T08:30:29Z**

This is a regression from bug 1927195, which enabled the build flag for the explicit resource management feature only on nightly, while the feature itself is still disabled by default with a pref.

So, while bug 1927195 patch landed to 134, this is still nightly-only and only affects when users manually enabled the feature in about:config,
thus this should effectively match the (B) case in the security approval document.

https://firefox-source-docs.mozilla.org/bug-mgmt/processes/security-approval.html#on-requesting-sec-approval
> B) The bug is a recent regression on mozilla-central. This means
>   * A specific regressing check-in has been identified
>   * The developer can (and has) marked the status flags for ESR and Beta as “unaffected”
>   * We have not shipped this vulnerability in anything other than a nightly build

Also, while the type confusion can be sec-high as mentioned in the comment #0, the severity can be lowered given it's disabled by default and can be enabled only by about:config page,
thus this also matches the (A) case in the security approval document.

https://wiki.mozilla.org/Security_Severity_Ratings/Client
> Mitigating Circumstances
> If there are mitigating circumstances that severely constrain the vulnerability, then the issue could be reduced by one level of severity. Examples of mitigating circumstances include difficulty in reproducing due to very specific timing or load order requirements, a complex or unusual set of actions the user would have to take beyond normal browsing behaviors, or an unusual software configuration not provided by our Preferences page. 

https://firefox-source-docs.mozilla.org/bug-mgmt/processes/security-approval.html#on-requesting-sec-approval
> A) The bug has a sec-low, sec-moderate, sec-other, or sec-want rating.

I'm going to land the patch without the approval request.

---

**Comment 6 — pulsebot@bmo.tld — 2024-12-02T08:42:50Z**

Pushed by arai_a@mac.com:
https://hg.mozilla.org/integration/autoland/rev/c3ab38fe90bf
Check for out of memory when creating SuppressedError. r=arai

---

**Comment 7 — continuation@gmail.com — 2024-12-02T15:47:27Z**

As discussed, this is sec-high, but for a feature that is disabled in the browser.

---

**Comment 8 — aryx.bugmail@gmx-topmail.de — 2024-12-02T21:53:51Z**

https://hg.mozilla.org/mozilla-central/rev/c3ab38fe90bf

---

**Comment 9 — bugmon@mozilla.com — 2024-12-03T08:22:49Z**

Verified bug as fixed on rev mozilla-central 20241202214052-bde1ea11f25a.
Removing bugmon keyword as no further action possible.  Please review the bug and re-add the keyword for further analysis.
