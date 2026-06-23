# Crash [@ js::wasm::DecodeModuleEnvironment]

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1987624
Component: JavaScript: WebAssembly
Bounty: (unknown)
Date: 2025-09-09T10:31:22Z
Keywords: crash, csectype-uaf, regression, sec-high, testcase

The following testcase crashes on mozilla-central revision 20250908-3927f21c92c9 (opt build, run with --fuzzing-safe --ion-offthread-compile=off):

    a = new ArrayBuffer(1 << 20)
    b = new Proxy({}, {
        get(c, d) {
            if (d == 'builtins')
    	  a.transfer(unescape)
        }
    })
    WebAssembly.validate(a, b)


Backtrace:

    received signal SIGSEGV, Segmentation fault.
    #0  0x00005555573e4b89 in js::wasm::DecodeModuleEnvironment(js::wasm::Decoder&, js::wasm::CodeMetadata*, js::wasm::ModuleMetadata*) ()
    #1  0x00005555573daad9 in js::wasm::Validate(JSContext*, js::wasm::BytecodeSource const&, js::wasm::FeatureOptions const&, std::unique_ptr<char [], JS::FreePolicy>*) ()
    #2  0x00005555573da888 in WebAssembly_validate(JSContext*, unsigned int, JS::Value*) ()
    #3  0x0000555556fbb3b4 in js::Interpret(JSContext*, js::RunState&) ()
    #4  0x0000555556e22088 in js::RunScript(JSContext*, js::RunState&) ()
    #5  0x0000555556e21cd5 in js::Execute(JSContext*, JS::Handle<JSScript*>, JS::Handle<JSObject*>, JS::MutableHandle<JS::Value>) ()
    #6  0x0000555556e219ae in JS_ExecuteScript(JSContext*, JS::Handle<JSScript*>) ()
    #7  0x000055555753087a in RunFile(JSContext*, char const*, _IO_FILE*, CompileUtf8, bool, bool) ()
    #8  0x000055555752f892 in Process(JSContext*, char const*, bool, FileKind) ()
    #9  0x000055555751d98b in main ()
    rax	0x100000	1048576
    rbx	0x7ffff30dad00	140737271147776
    rcx	0x7ffff2900000	140737262911488
    rdx	0x7ffff4222c90	140737289268368
    rsi	0x7ffff2800000	140737261862912
    rdi	0x7fffffffbb88	140737488337800
    rbp	0x7fffffffbb10	140737488337680
    rsp	0x7fffffffb6a0	140737488336544
    r8	0x38c10385	952173445
    r9	0xd10d970585523d08	-3382881695117984504
    r10	0x3e	62
    r11	0x60	96
    r12	0x7fffffffbb88	140737488337800
    r13	0x7fffffffbc38	140737488337976
    r14	0x7ffff30dad00	140737271147776
    r15	0x7fffffffbc20	140737488337952
    rip	0x5555573e4b89 <js::wasm::DecodeModuleEnvironment(js::wasm::Decoder&, js::wasm::CodeMetadata*, js::wasm::ModuleMetadata*)+89>
    => 0x5555573e4b89 <_ZN2js4wasm23DecodeModuleEnvironmentERNS0_7DecoderEPNS0_12CodeMetadataEPNS0_14ModuleMetadataE+89>:	mov    (%rsi),%edx
       0x5555573e4b8b <_ZN2js4wasm23DecodeModuleEnvironmentERNS0_7DecoderEPNS0_12CodeMetadataEPNS0_14ModuleMetadataE+91>:	lea    0x4(%rsi),%rax

---

**Comment 1 — choller@mozilla.com — 2025-09-09T10:31:24Z**

Created attachment 9512241
Detailed Crash Information

---

**Comment 2 — choller@mozilla.com — 2025-09-09T10:31:26Z**

Created attachment 9512242
Testcase

---

**Comment 3 — continuation@gmail.com — 2025-09-09T13:49:24Z**

This looks like a possible dupe of bug 1987611.

---

**Comment 4 — choller@mozilla.com — 2025-09-09T14:39:13Z**

Originally found `Thu, 04 Sep 2025 01:59:00 +0000` by internal fuzzing.

---

**Comment 5 — rhunt@eqrion.net — 2025-09-10T15:56:30Z**

When using the Module constructor or the validate API, we read the bytecode directly from the ArrayBuffer without making a copy. It looks like we are grabbing a pointer to the ArrayBuffer data, then calling FeatureOptions::init, which is proxied to detach the ArrayBuffer and invalidate the pointer we have.

The spec is slightly ambiguous about the order of 'copying the buffer' and 'parsing compile options', but I think a reasonable interpretation could have them reversed so that the detach happens first before we get the data pointer. This fixes the issue for me locally. To be even more robust here we should use the 'length pin' API of array buffers which will prevent unexpected detaches.

This can lead to reading free'ed memory while compiling/validating a wasm module. There will be no write's to the free'ed memory. It's highly likely this will just lead to crashes, but possibly could be used to exfiltrate data somehow if the attacker is able to get the data pointer to point at memory that validates yet somehow contains process-private data.

---

**Comment 6 — rhunt@eqrion.net — 2025-09-10T15:58:58Z**

This is a regression from bug 1931407.

---

**Comment 7 — rhunt@eqrion.net — 2025-09-10T16:11:38Z**

*** Bug 1987611 has been marked as a duplicate of this bug. ***

---

**Comment 8 — rhunt@eqrion.net — 2025-09-10T20:17:27Z**

Created attachment 9512693
(secure)

---

**Comment 9 — rhunt@eqrion.net — 2025-09-10T20:17:39Z**

Created attachment 9512694
(secure)

---

**Comment 10 — release-mgmt-account-bot@mozilla.tld — 2025-09-16T12:44:03Z**

Set release status flags based on info from the regressing bug 1931407

---

**Comment 11 — rhunt@eqrion.net — 2025-09-16T19:24:57Z**

Comment on attachment 9512693
(secure)

### Security Approval Request
* **How easily could an exploit be constructed based on the patch?**: Unclear. This bug would allow an attacker to free the wasm bytecode that we're currently compiling. This will only result in reads, not writes of freed memory. If the attacker could somehow concurrently mutate the free'ed bytecode memory while we are compiling they possibly could break our validation algorithm and get us to compile invalid wasm code. This would be tricky and novel, I'm unsure if it'd be possible.
* **Do comments in the patch, the check-in comment, or tests included in the patch paint a bulls-eye on the security problem?**: No
* **Which branches (beta, release, and/or ESR) are affected by this flaw, and do the release status flags reflect this affected/unaffected state correctly?**: Beta, Release, and ESR 140. Status flags are correct.
* **If not all supported branches, which bug introduced the flaw?**: Bug 1931407
* **Do you have backports for the affected branches?**: Yes
* **If not, how different, hard to create, and risky will they be?**: 
* **How likely is this patch to cause regressions; how much testing does it need?**: Unlikely, this code is pretty well tested.
* **Is the patch ready to land after security approval is given?**: Yes
* **Is Android affected?**: Yes

---

**Comment 12 — tom@mozilla.com — 2025-09-17T18:14:58Z**

Comment on attachment 9512693
(secure)

Approved to land and uplift

---

**Comment 13 — pulsebot@bmo.tld — 2025-09-17T20:32:02Z**

Pushed by rhunt@eqrion.net:
https://github.com/mozilla-firefox/firefox/commit/c89c1e356e68
https://hg.mozilla.org/integration/autoland/rev/ae88c4398cae
wasm: Refactor GetBufferSource. r=yury

---

**Comment 14 — dmeehan@mozilla.com — 2025-09-18T19:12:20Z**

https://hg-edge.mozilla.org/mozilla-central/rev/ae88c4398cae0b3d582245e8bcc4631e2b2804ec

---

**Comment 15 — dmeehan@mozilla.com — 2025-09-18T19:27:03Z**

:rhunt, could you please add beta and esr140 uplift requests when you have a moment?

---

**Comment 16 — phab-bot@bmo.tld — 2025-09-19T19:13:16Z**

### firefox-beta Uplift Approval Request
- **User impact if declined**: Potentially exploitable UaF.
- **Code covered by automated testing**: yes
- **Fix verified in Nightly**: yes
- **Needs manual QE test**: no
- **Steps to reproduce for manual QE testing**: 
- **Risk associated with taking this patch**: low
- **Explanation of risk level**: This is a well tested code path.
- **String changes made/needed**: N/A
- **Is Android affected?**: yes

---

**Comment 17 — rhunt@eqrion.net — 2025-09-19T19:13:16Z**

Created attachment 9514402
(secure)



Original Revision: https://phabricator.services.mozilla.com/D264478

---

**Comment 18 — phab-bot@bmo.tld — 2025-09-19T19:13:50Z**

### firefox-esr140 Uplift Approval Request
- **User impact if declined**: Potentially exploitable UaF.
- **Code covered by automated testing**: yes
- **Fix verified in Nightly**: yes
- **Needs manual QE test**: no
- **Steps to reproduce for manual QE testing**: 
- **Risk associated with taking this patch**: low
- **Explanation of risk level**: Well tested code.
- **String changes made/needed**: None
- **Is Android affected?**: yes

---

**Comment 19 — rhunt@eqrion.net — 2025-09-19T19:13:50Z**

Created attachment 9514403
(secure)



Original Revision: https://phabricator.services.mozilla.com/D264478

---

**Comment 20 — pulsebot@bmo.tld — 2025-09-20T14:17:33Z**

https://github.com/mozilla-firefox/firefox/commit/93765e4f87ac
https://hg.mozilla.org/releases/mozilla-beta/rev/83a487c959de

---

**Comment 21 — pulsebot@bmo.tld — 2025-09-22T14:05:42Z**

https://hg.mozilla.org/releases/mozilla-esr140/rev/18b9a7189cc9

---

**Comment 22 — bugmon@mozilla.com — 2026-04-18T11:14:16Z**

Verified bug as fixed on rev mozilla-central 20260418081104-4c39f991a01a.
Removing bugmon keyword as no further action possible.  Please review the bug and re-add the keyword for further analysis.
