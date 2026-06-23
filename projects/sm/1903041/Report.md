# Assertion failure: superSTV, at /builds/worker/checkouts/gecko/js/src/wasm/WasmTypeDef.h:872

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1903041
CVE: CVE-2024-7520
Component: JavaScript: WebAssembly
Bounty: (unknown)
Date: 2024-06-17T13:26:09Z
Keywords: csectype-wildptr, reporter-external, sec-high

Created attachment 9407870
poc.js

## Reproduce
1. Clone the Firefox mirror from https://github.com/mozilla/gecko-dev
2. Run build command `mkdir fuzzbuild_OPT.OBJ && cd fuzzbuild_OPT.OBJ && ../configure --enable-address-sanitizer --disable-jemalloc --enable-debug --enable-optimize --disable-shared-js --enable-application=js --enable-gczeal && make -j64` in the js/src directory of the firefox checkout
3. Run poc: `js/src/fuzzbuild_OPT.OBJ/dist/bin/js  poc.js`

- my test spidermonkey commit hash
```
commit 30dfc0e2fcfec889f94fbd0ec5f20822c276c0fb (HEAD -> master, origin/master, origin/HEAD)
Author: Makoto Kato <m_kato@ga2.so-net.ne.jp>
Date:   Mon Jun 17 02:03:33 2024 +0000

    Bug 1899411 - Part 6. Adjust test results after upgrading ICU4X to 1.5. r=jfkthame,spidermonkey-reviewers,anba
    
    Differential Revision: https://phabricator.services.mozilla.com/D213011
```

## Bisect
Additionally, I ran autobisect, which bisected to the point where wasm-gc was enabled by default, so I believe this bug has existed since that code was introduced.

https://github.com/mozilla/gecko-dev/commit/827fdc584e706875a4293ab7e5700766fcc68602

## Debug Log
```
(autobisect-py3.10) ➜  autobisect git:(master) ✗ /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-12d5ea126a22/dist/bin/js poc.js
[1879183] Assertion failure: superSTV, at /builds/worker/checkouts/gecko/js/src/wasm/WasmTypeDef.h:872
#01: ???[/home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-12d5ea126a22/dist/bin/js +0x68088d4]
#02: ???[/home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-12d5ea126a22/dist/bin/js +0x6807313]
#03: ???[/home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-12d5ea126a22/dist/bin/js +0x6f69525]
#04: ???[/home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-12d5ea126a22/dist/bin/js +0x6fc3f41]
#05: ???[/home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-12d5ea126a22/dist/bin/js +0x6f75620]
#06: ???[/home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-12d5ea126a22/dist/bin/js +0x6bf3cd1]
#07: ???[/home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-12d5ea126a22/dist/bin/js +0x6cf9e2b]
#08: ???[/home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-12d5ea126a22/dist/bin/js +0x3c965cb]
#09: ???[/home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-12d5ea126a22/dist/bin/js +0x3cf5565]
#10: ???[/home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-12d5ea126a22/dist/bin/js +0x3c99718]
#11: ???[/home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-12d5ea126a22/dist/bin/js +0x3cb4d01]
#12: ???[/home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-12d5ea126a22/dist/bin/js +0x3c93767]
#13: ???[/home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-12d5ea126a22/dist/bin/js +0x3c9ba61]
#14: ???[/home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-12d5ea126a22/dist/bin/js +0x3c9c70a]
#15: ???[/home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-12d5ea126a22/dist/bin/js +0x407278a]
#16: ???[/home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-12d5ea126a22/dist/bin/js +0x4072c38]
#17: ???[/home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-12d5ea126a22/dist/bin/js +0x39a1007]
#18: ???[/home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-12d5ea126a22/dist/bin/js +0x399f900]
#19: ???[/home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-12d5ea126a22/dist/bin/js +0x38c088f]
#20: ???[/home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-12d5ea126a22/dist/bin/js +0x38b0dde]
#21: ???[/lib/x86_64-linux-gnu/libc.so.6 +0x29d90]
#22: __libc_start_main[/lib/x86_64-linux-gnu/libc.so.6 +0x29e40]
#23: ???[/home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-12d5ea126a22/dist/bin/js +0x37bd079]
#24: ??? (???:???)
AddressSanitizer:DEADLYSIGNAL
=================================================================
==1879183==ERROR: AddressSanitizer: SEGV on unknown address 0x000000000000 (pc 0x56402d3e1909 bp 0x7fff47706280 sp 0x7fff47706260 T0)
==1879183==The signal is caused by a WRITE memory access.
==1879183==Hint: address points to the zero page.
    #0 0x56402d3e1909 in js::wasm::TypeDef::isSubTypeOf(js::wasm::TypeDef const*, js::wasm::TypeDef const*) /builds/worker/checkouts/gecko/js/src/wasm/WasmTypeDef.h:872:5
    #1 0x56402d3e0312 in js::wasm::RefType::isSubTypeOf(js::wasm::RefType, js::wasm::RefType) /builds/worker/checkouts/gecko/js/src/wasm/WasmTypeDef.h:1461:12
    #2 0x56402db42524 in js::wasm::PackedType<js::wasm::StorageTypeTraits>::isSubTypeOf(js::wasm::PackedType<js::wasm::StorageTypeTraits>, js::wasm::PackedType<js::wasm::StorageTypeTraits>) /builds/worker/checkouts/gecko/js/src/wasm/WasmValType.h:889:14
    #3 0x56402db9cf40 in js::wasm::StructType::canBeSubTypeOf(js::wasm::StructType const&, js::wasm::StructType const&) /builds/worker/checkouts/gecko/js/src/wasm/WasmTypeDef.h:366:12
    #4 0x56402db4e61f in DecodeTypeSection(js::wasm::Decoder&, js::wasm::ModuleEnvironment*) /builds/worker/checkouts/gecko/js/src/wasm/WasmValidate.cpp:1885:14
    #5 0x56402db4e61f in js::wasm::DecodeModuleEnvironment(js::wasm::Decoder&, js::wasm::ModuleEnvironment*) /builds/worker/checkouts/gecko/js/src/wasm/WasmValidate.cpp:3023:8
    #6 0x56402d7cccd0 in js::wasm::CompileBuffer(js::wasm::CompileArgs const&, js::wasm::ShareableBytes const&, mozilla::UniquePtr<char [], JS::FreePolicy>*, mozilla::Vector<mozilla::UniquePtr<char [], JS::FreePolicy>, 0ul, js::SystemAllocPolicy>*, JS::OptimizedEncodingListener*) /builds/worker/checkouts/gecko/js/src/wasm/WasmCompile.cpp:806:29
    #7 0x56402d8d2e2a in js::WasmModuleObject::construct(JSContext*, unsigned int, JS::Value*) /builds/worker/checkouts/gecko/js/src/wasm/WasmJS.cpp:1514:7
    #8 0x56402a86f5ca in CallJSNative(JSContext*, bool (*)(JSContext*, unsigned int, JS::Value*), js::CallReason, JS::CallArgs const&) /builds/worker/checkouts/gecko/js/src/vm/Interpreter.cpp:487:13
    #9 0x56402a8ce564 in CallJSNativeConstructor(JSContext*, bool (*)(JSContext*, unsigned int, JS::Value*), JS::CallArgs const&) /builds/worker/checkouts/gecko/js/src/vm/Interpreter.cpp:503:8
    #10 0x56402a872717 in InternalConstruct(JSContext*, js::AnyConstructArgs const&, js::CallReason) /builds/worker/checkouts/gecko/js/src/vm/Interpreter.cpp:709:14
    #11 0x56402a88dd00 in js::ConstructFromStack(JSContext*, JS::CallArgs const&, js::CallReason) /builds/worker/checkouts/gecko/js/src/vm/Interpreter.cpp:756:10
    #12 0x56402a88dd00 in js::Interpret(JSContext*, js::RunState&) /builds/worker/checkouts/gecko/js/src/vm/Interpreter.cpp:3276:16
    #13 0x56402a86c766 in js::RunScript(JSContext*, js::RunState&) /builds/worker/checkouts/gecko/js/src/vm/Interpreter.cpp:459:13
    #14 0x56402a874a60 in js::ExecuteKernel(JSContext*, JS::Handle<JSScript*>, JS::Handle<JSObject*>, js::AbstractFramePtr, JS::MutableHandle<JS::Value>) /builds/worker/checkouts/gecko/js/src/vm/Interpreter.cpp:846:13
    #15 0x56402a875709 in js::Execute(JSContext*, JS::Handle<JSScript*>, JS::Handle<JSObject*>, JS::MutableHandle<JS::Value>) /builds/worker/checkouts/gecko/js/src/vm/Interpreter.cpp:878:10
    #16 0x56402ac4b789 in ExecuteScript(JSContext*, JS::Handle<JSObject*>, JS::Handle<JSScript*>, JS::MutableHandle<JS::Value>) /builds/worker/checkouts/gecko/js/src/vm/CompilationAndEvaluation.cpp:494:10
    #17 0x56402ac4bc37 in JS_ExecuteScript(JSContext*, JS::Handle<JSScript*>) /builds/worker/checkouts/gecko/js/src/vm/CompilationAndEvaluation.cpp:518:10
    #18 0x56402a57a006 in RunFile(JSContext*, char const*, _IO_FILE*, CompileUtf8, bool, bool) /builds/worker/checkouts/gecko/js/src/shell/js.cpp:1194:10
    #19 0x56402a5788ff in Process(JSContext*, char const*, bool, FileKind) /builds/worker/checkouts/gecko/js/src/shell/js.cpp
    #20 0x56402a49988e in ProcessArgs(JSContext*, js::cli::OptionParser*) /builds/worker/checkouts/gecko/js/src/shell/js.cpp:11255:10
    #21 0x56402a49988e in Shell(JSContext*, js::cli::OptionParser*) /builds/worker/checkouts/gecko/js/src/shell/js.cpp:11507:12
    #22 0x56402a489ddd in main /builds/worker/checkouts/gecko/js/src/shell/js.cpp:12033:12
    #23 0x7f83eac29d8f in __libc_start_call_main csu/../sysdeps/nptl/libc_start_call_main.h:58:16
    #24 0x7f83eac29e3f in __libc_start_main csu/../csu/libc-start.c:392:3
    #25 0x56402a396078 in _start (/home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-12d5ea126a22/dist/bin/js+0x37bd078) (BuildId: 562e16ed839a2453983df25de4080114854810c8)

AddressSanitizer can not provide additional info.
SUMMARY: AddressSanitizer: SEGV /builds/worker/checkouts/gecko/js/src/wasm/WasmTypeDef.h:872:5 in js::wasm::TypeDef::isSubTypeOf(js::wasm::TypeDef const*, js::wasm::TypeDef const*)
==1879183==ABORTING

```

---

**Comment 1 — bvisness@mozilla.com — 2024-06-25T15:50:08Z**

Created attachment 9409470
reduced.js

The following reproduces the crash more minimally. It seems the problem is that `$b` and `$c`'s supertype vectors are not yet initialized when we compare their struct fields for a subtype relationship - which requires the supertype vectors. Specifically, `$b`'s uninitialized supertype vector is tripping the assert.

---

**Comment 2 — bvisness@mozilla.com — 2024-06-26T15:55:52Z**

Created attachment 9409717
Bug 1903041: Use a linear search in more situations. r=rhunt

---

**Comment 3 — bvisness@mozilla.com — 2024-06-26T15:56:02Z**

Created attachment 9409718
Bug 1903041: Add test for STV type confusion. r=rhunt

---

**Comment 4 — dveditz@mozilla.com — 2024-06-26T22:24:02Z**

What is the consequence if we return an unexpected true/false here (before your patch)? Is it dangerously broken (wrt security) or is it merely wrong results?

---

**Comment 5 — bvisness@mozilla.com — 2024-06-27T12:50:34Z**

It seems to be a genuine type confusion issue - I have been able to cause it to recognize two incompatible types as subtypes, which means we could generate incorrect and possibly dangerous code. Definitely a security issue.

---

**Comment 6 — bvisness@mozilla.com — 2024-06-28T16:16:05Z**

Comment on attachment 9409717
Bug 1903041: Use a linear search in more situations. r=rhunt

### Security Approval Request
* **How easily could an exploit be constructed based on the patch?**: It is fairly easy to cause two struct fields to pass validation as subtypes when they should not, thanks to a `null == null` comparison. It seems quite easy to exploit.
* **Do comments in the patch, the check-in comment, or tests included in the patch paint a bulls-eye on the security problem?**: No
* **Which branches (beta, release, and/or ESR) are affected by this flaw, and do the release status flags reflect this affected/unaffected state correctly?**: beta and release
* **If not all supported branches, which bug introduced the flaw?**: None
* **Do you have backports for the affected branches?**: Yes
* **If not, how different, hard to create, and risky will they be?**: 
* **How likely is this patch to cause regressions; how much testing does it need?**: Unlikely to cause regressions. We are using an existing slow codepath in more situations.
* **Is the patch ready to land after security approval is given?**: Yes
* **Is Android affected?**: Yes

---

**Comment 7 — release-mgmt-account-bot@mozilla.tld — 2024-07-04T12:14:37Z**

The severity field for this bug is set to S3. However, the bug is flagged with the `sec-high` keyword.
:bvisness, could you consider increasing the severity of this security bug?

For more information, please visit [BugBot documentation](https://wiki.mozilla.org/BugBot#severity_high_security.py).

---

**Comment 8 — dveditz@mozilla.com — 2024-07-11T01:35:15Z**

Comment on attachment 9409717
Bug 1903041: Use a linear search in more situations. r=rhunt

sec-approval+ = dveditz approved to land, please request branch uplifts. We'll wait until after release to land the tests

---

**Comment 9 — pulsebot@bmo.tld — 2024-07-11T13:55:14Z**

Pushed by bvisness@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/e45730ae9793
Use a linear search in more situations. r=rhunt

---

**Comment 10 — aryx.bugmail@gmx-topmail.de — 2024-07-12T07:50:55Z**

https://hg.mozilla.org/mozilla-central/rev/e45730ae9793

---

**Comment 11 — release-mgmt-account-bot@mozilla.tld — 2024-07-12T12:08:01Z**

The patch landed in nightly and beta is affected.
:bvisness, is this bug important enough to require an uplift?
- If yes, please nominate the patch for beta approval.
- If no, please set `status-firefox129` to `wontfix`.

For more information, please visit [BugBot documentation](https://wiki.mozilla.org/BugBot#uplift_beta.py).

---

**Comment 12 — bvisness@mozilla.com — 2024-07-12T14:43:59Z**

Created attachment 9412494
Bug 1903041: Use a linear search in more situations. r=rhunt



Original Revision: https://phabricator.services.mozilla.com/D214989

---

**Comment 13 — phab-bot@bmo.tld — 2024-07-12T14:55:15Z**

### beta Uplift Approval Request
- **User impact if declined**: easily triggered type confusion security issue
- **Code covered by automated testing**: no
- **Fix verified in Nightly**: yes
- **Needs manual QE test**: no
- **Steps to reproduce for manual QE testing**: n/a
- **Risk associated with taking this patch**: minimal
- **Explanation of risk level**: a preexisting slow path is used in more situations
- **String changes made/needed**: none
- **Is Android affected?**: yes

---

**Comment 14 — dmeehan@mozilla.com — 2024-07-12T17:24:47Z**

:bvisness this will also need an uplift request for esr128

---

**Comment 15 — pulsebot@bmo.tld — 2024-07-12T17:51:51Z**

https://hg.mozilla.org/releases/mozilla-beta/rev/e809c01ab501

---

**Comment 16 — bvisness@mozilla.com — 2024-07-15T13:51:39Z**

When I do so, I get an error from Lando saying "Please select an uplift repository to create the uplift request." Am I doing something wrong?

---

**Comment 17 — dmeehan@mozilla.com — 2024-07-15T14:02:07Z**

(In reply to Ben Visness [:bvisness] from comment #16)
> When I do so, I get an error from Lando saying "Please select an uplift repository to create the uplift request." Am I doing something wrong?

:bvisness, Lando is currently missing support for esr128. That should be fixed later today. 
Link to internal Slack thread:
https://mozilla.slack.com/archives/C58QX7G3B/p1721051816793479?thread_ts=1721041430.000889&cid=C58QX7G3B

In the meantime, you could fill out the form on the attachment in the bug directly if you want? Otherwise, it will be available later today once the fix gets deployed.

---

**Comment 18 — dveditz@mozilla.com — 2024-07-15T15:22:32Z**

Comment on attachment 9409718
Bug 1903041: Add test for STV type confusion. r=rhunt

You don't need separate sec-approval for landing the tests, but please wait for the post-release landing date in the whiteboard reminder (2024-08-26). Bugbot should add a needinfo on that date.

---

**Comment 19 — bvisness@mozilla.com — 2024-07-15T19:40:05Z**

Created attachment 9412854
Bug 1903041: Use a linear search in more situations. r=rhunt



Original Revision: https://phabricator.services.mozilla.com/D214989

---

**Comment 20 — phab-bot@bmo.tld — 2024-07-15T21:01:25Z**

### esr128 Uplift Approval Request
- **User impact if declined**: easily triggered type confusion security issue
- **Code covered by automated testing**: no
- **Fix verified in Nightly**: yes
- **Needs manual QE test**: no
- **Steps to reproduce for manual QE testing**: n/a
- **Risk associated with taking this patch**: minimal
- **Explanation of risk level**: a preexisting slow path is used in more situations
- **String changes made/needed**: none
- **Is Android affected?**: yes

---

**Comment 21 — pulsebot@bmo.tld — 2024-07-16T14:31:50Z**

https://hg.mozilla.org/releases/mozilla-esr128/rev/42f57fc7e182

---

**Comment 22 — twsmith@mozilla.com — 2024-08-01T20:32:26Z**

Created attachment 9417363
advisory.txt

---

**Comment 23 — release-mgmt-account-bot@mozilla.tld — 2024-08-26T12:05:18Z**

a month ago, dveditz placed a reminder on the bug using the whiteboard tag `[reminder-test 2024-08-26]` .

bvisness, please refer to the original comment to better understand the reason for the reminder.

---

**Comment 24 — pulsebot@bmo.tld — 2024-08-26T14:45:17Z**

Pushed by bvisness@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/47b4c57ac649
Add test for STV type confusion. r=rhunt

---

**Comment 25 — aryx.bugmail@gmx-topmail.de — 2024-08-27T11:52:46Z**

https://hg.mozilla.org/mozilla-central/rev/47b4c57ac649
