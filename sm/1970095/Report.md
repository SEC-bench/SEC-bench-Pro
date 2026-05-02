# SEGV WRITE in __memcpy_avx_unaligned_erms via OrderedHashTableImpl::rehash

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1970095
CVE: CVE-2025-49710
Component: JavaScript Engine
Bounty: (unknown)
Date: 2025-06-03T11:20:36Z
Keywords: csectype-intoverflow, regression, reporter-external, sec-high

Created attachment 9492361
poc.js

Run: ./objdir/dist/bin/js poc.js
```
AddressSanitizer:DEADLYSIGNAL
=================================================================
==5142==ERROR: AddressSanitizer: SEGV on unknown address 0x7b44f55c87f0 (pc 0x7b44b1588a6c bp 0x7fffed2fb090 sp 0x7fffed2fa848 T0)
==5142==The signal is caused by a WRITE memory access.
/home/user/Desktop/firefox/objdir/dist/bin/llvm-symbolizer: error: '[anon:js-executable-memory]': No such file or directory
    #0 0x7b44b1588a6c in __memcpy_avx_unaligned_erms string/../sysdeps/x86_64/multiarch/memmove-vec-unaligned-erms.S:344
    #1 0x55e9edcea82b in __asan_memcpy /builds/worker/fetches/llvm-project/compiler-rt/lib/asan/asan_interceptors_memintrinsics.cpp:63:3
    #2 0x55e9edf86a1b in js::detail::OrderedHashTableImpl<js::OrderedHashMapImpl<js::PreBarriered<js::HashableValue>, js::HeapPtr<JS::Value>, js::HashableValueHasher>::Entry, js::OrderedHashMapImpl<js::PreBarriered<js::HashableValue>, js::HeapPtr<JS::Value>, js::HashableValueHasher>::MapOps>::rehash(JSContext*, unsigned int) /home/user/Desktop/firefox/js/src/builtin/OrderedHashTableObject.h:1222:13
    #3 0x55e9edf85b64 in js::detail::OrderedHashTableImpl<js::OrderedHashMapImpl<js::PreBarriered<js::HashableValue>, js::HeapPtr<JS::Value>, js::HashableValueHasher>::Entry, js::OrderedHashMapImpl<js::PreBarriered<js::HashableValue>, js::HeapPtr<JS::Value>, js::HashableValueHasher>::MapOps>::rehashOnFull(JSContext*) /home/user/Desktop/firefox/js/src/builtin/OrderedHashTableObject.h:1181:12
    #4 0x55e9edf85b64 in bool js::detail::OrderedHashTableImpl<js::OrderedHashMapImpl<js::PreBarriered<js::HashableValue>, js::HeapPtr<JS::Value>, js::HashableValueHasher>::Entry, js::OrderedHashMapImpl<js::PreBarriered<js::HashableValue>, js::HeapPtr<JS::Value>, js::HashableValueHasher>::MapOps>::put<js::OrderedHashMapImpl<js::PreBarriered<js::HashableValue>, js::HeapPtr<JS::Value>, js::HashableValueHasher>::Entry>(JSContext*, js::OrderedHashMapImpl<js::PreBarriered<js::HashableValue>, js::HeapPtr<JS::Value>, js::HashableValueHasher>::Entry&&) /home/user/Desktop/firefox/js/src/builtin/OrderedHashTableObject.h:717:52
    #5 0x55e9edf70af9 in bool js::OrderedHashMapImpl<js::PreBarriered<js::HashableValue>, js::HeapPtr<JS::Value>, js::HashableValueHasher>::put<js::HashableValue const&, JS::Value const&>(JSContext*, js::HashableValue const&, JS::Value const&) /home/user/Desktop/firefox/js/src/builtin/OrderedHashTableObject.h:1357:17
    #6 0x55e9edf4ed8e in js::MapObject::setWithHashableKey(JSContext*, js::HashableValue const&, JS::Value const&) /home/user/Desktop/firefox/js/src/builtin/MapObject.cpp:564:22
    #7 0x55e9edf4ecdf in js::MapObject::set(JSContext*, JS::Value const&, JS::Value const&) /home/user/Desktop/firefox/js/src/builtin/MapObject.cpp:552:10
    #8 0x7b442de13992  ([anon:js-executable-memory]+0x4992)

==5142==Register values:
rax = 0x00007b44f55c87f0  rbx = 0x0000000000000000  rcx = 0x00000f691eab10ff  rdx = 0x0000000000000010  
rdi = 0x00007b44f55c87f0  rsi = 0x00007b43875c07f8  rbp = 0x00007fffed2fb090  rsp = 0x00007fffed2fa848  
 r8 = 0x00000f689eab90fe   r9 = 0x00007b44f55c87ff  r10 = 0x00000f689eab90ff  r11 = 0x00000f691eab10f8  
r12 = 0x00000f691eab10f8  r13 = 0xffffffffffffffcf  r14 = 0x00007fffed2fb268  r15 = 0x0000000020000000  
AddressSanitizer can not provide additional info.
SUMMARY: AddressSanitizer: SEGV string/../sysdeps/x86_64/multiarch/memmove-vec-unaligned-erms.S:344 in __memcpy_avx_unaligned_erms
==5142==ABORTING
========================================
```
mozconfig:
```
ac_add_options --enable-project=js
ac_add_options --enable-address-sanitizer
ac_add_options --disable-jemalloc
ac_add_options --disable-debug
ac_add_options --enable-optimize
mk_add_options MOZ_OBJDIR=@TOPSRCDIR@/objdir
```

---

**Comment 1 — jdemooij@mozilla.com — 2025-06-03T14:55:33Z**

I can reproduce this (takes about 1-3 minutes to crash depending on build flags).

It looks like the `OrderedHashTableObject` code uses `size_t` for the size of the buffer that we want to allocate, but [it calls](https://searchfox.org/mozilla-central/rev/8acb5f362849305467afc045e3c0f84625a03ebc/js/src/builtin/OrderedHashTableObject-inl.h#16) `AllocNurseryOrMallocBuffer` that has a `uint32_t` argument.

Jon, thoughts on changing these functions vs changing `OrderedHashTableObject`? It's a simple change to restrict the size to `uint32_t` in `calcAllocSize` but it is a bit of a footgun to require callers to check for this case.

---

**Comment 2 — jcoppeard@mozilla.com — 2025-06-03T16:23:29Z**

Yeah, these should all be size_t rather than uint32_t.

---

**Comment 3 — jdemooij@mozilla.com — 2025-06-04T12:11:04Z**

I think there are multiple issues. Our GC malloc-related functions don't expect arbitrary sizes because we normally restrict the size of allocations for slots, elements, string characters, etc. We should change from `uint32_t` to `size_t` but for now it might be safest to limit the number of `Map`/`Set` entries.

Testing this with JS shell builds of various engines with the script below, I get the following max number of entries:
```
Map:
v8:  16777216 (= 2^24)
jsc: 25165824 (= 1.5 * 2^24)
 
Set:
v8:  16777216 (= 2^24)
jsc: 50331648 (= 3 * 2^24)
```
We allow more entries than either v8 or JSC (we can go up to 170 million for a `Set` before we crash).
```js
function f() {
  var m = new Map();
  try {
    for (var i = 0; i < 1_000_000_000; i++) {
      m.set(i, 0);
    }
  } catch {}
  print(m.size);
}
f();
```

---

**Comment 4 — continuation@gmail.com — 2025-06-04T12:51:25Z**

This sounds like an integer overflow (from a conversion of a 64 bit int to a 32 bit int) involving memcopy, so I'm going to assume it is sec-high for now.

---

**Comment 5 — jdemooij@mozilla.com — 2025-06-04T19:55:35Z**

Created attachment 9492820
Bug 1970095 - Clean up some Map/Set code. r?iain!

---

**Comment 6 — jdemooij@mozilla.com — 2025-06-04T19:55:45Z**

Created attachment 9492821
(secure)

---

**Comment 7 — release-mgmt-account-bot@mozilla.tld — 2025-06-04T20:42:21Z**

Set release status flags based on info from the regressing bug 1928666

---

**Comment 8 — jdemooij@mozilla.com — 2025-06-05T12:31:50Z**

Created attachment 9492968
(secure)

---

**Comment 9 — jdemooij@mozilla.com — 2025-06-05T12:39:40Z**

Comment on attachment 9492820
Bug 1970095 - Clean up some Map/Set code. r?iain!

### Security Approval Request
* **How easily could an exploit be constructed based on the patch?**: Probably not super difficult because the patch is lowering the max number of entries we allow in Map/Set objects.
* **Do comments in the patch, the check-in comment, or tests included in the patch paint a bulls-eye on the security problem?**: No
* **Which branches (beta, release, and/or ESR) are affected by this flaw, and do the release status flags reflect this affected/unaffected state correctly?**: beta/release/ESR140
* **If not all supported branches, which bug introduced the flaw?**: Bug 1928666
* **Do you have backports for the affected branches?**: Yes
* **If not, how different, hard to create, and risky will they be?**: Patch should apply.
* **How likely is this patch to cause regressions; how much testing does it need?**: Not very likely. It limits the number of entries in Map/Set objects but this limit is quite high (and exceeds Chrome's).
* **Is the patch ready to land after security approval is given?**: Yes
* **Is Android affected?**: Yes

---

**Comment 10 — tom@mozilla.com — 2025-06-05T14:07:27Z**

Comment on attachment 9492820
Bug 1970095 - Clean up some Map/Set code. r?iain!

Approved to land and uplift

---

**Comment 11 — jdemooij@mozilla.com — 2025-06-05T17:59:16Z**

Created attachment 9493086
Bug 1970095 - Clean up some Map/Set code. r?iain!



Original Revision: https://phabricator.services.mozilla.com/D252581

---

**Comment 12 — jdemooij@mozilla.com — 2025-06-05T18:00:03Z**

Created attachment 9493087
Bug 1970095 - Clean up some Map/Set code. r?iain!



Original Revision: https://phabricator.services.mozilla.com/D252581

---

**Comment 13 — phab-bot@bmo.tld — 2025-06-05T18:04:03Z**

### firefox-beta Uplift Approval Request
- **User impact if declined**: security bugs
- **Code covered by automated testing**: yes
- **Fix verified in Nightly**: no
- **Needs manual QE test**: no
- **Steps to reproduce for manual QE testing**: -
- **Risk associated with taking this patch**: Low
- **Explanation of risk level**: Lowers the limit for number of Map/Set entries, unlikely to affect real code
- **String changes made/needed**: -
- **Is Android affected?**: yes

---

**Comment 14 — phab-bot@bmo.tld — 2025-06-05T18:04:10Z**

### firefox-release Uplift Approval Request
- **User impact if declined**: security bugs
- **Code covered by automated testing**: yes
- **Fix verified in Nightly**: no
- **Needs manual QE test**: no
- **Steps to reproduce for manual QE testing**: -
- **Risk associated with taking this patch**: Low
- **Explanation of risk level**: Lowers the limit for number of Map/Set entries, very unlikely to affect real-world code
- **String changes made/needed**: -
- **Is Android affected?**: yes

---

**Comment 15 — pulsebot@bmo.tld — 2025-06-05T19:27:14Z**

Pushed by jdemooij@mozilla.com:
https://github.com/mozilla-firefox/firefox/commit/d578778fe18e
https://hg.mozilla.org/integration/autoland/rev/013b8c0ac1aa
Clean up some Map/Set code. r=iain

---

**Comment 16 — aryx.bugmail@gmx-topmail.de — 2025-06-06T09:01:33Z**

https://hg.mozilla.org/mozilla-central/rev/013b8c0ac1aa

---

**Comment 17 — pulsebot@bmo.tld — 2025-06-06T18:53:49Z**

https://github.com/mozilla-firefox/firefox/commit/a145d25bb604
https://hg.mozilla.org/releases/mozilla-beta/rev/920c33eab35f

---

**Comment 18 — pulsebot@bmo.tld — 2025-06-06T22:10:54Z**

https://github.com/mozilla-firefox/firefox/commit/12cff9f1fac0
https://hg.mozilla.org/releases/mozilla-release/rev/b49341ffe49f

---

**Comment 19 — pulsebot@bmo.tld — 2025-09-17T16:27:06Z**

Pushed by jdemooij@mozilla.com:
https://github.com/mozilla-firefox/firefox/commit/0a95ec17b1a3
https://hg.mozilla.org/integration/autoland/rev/458f9ded3c84
Follow-up changes. r=iain
https://github.com/mozilla-firefox/firefox/commit/af26cdad06b8
https://hg.mozilla.org/integration/autoland/rev/7f7dcc4b99e9
Add a jit-test. r=mgaudet

---

**Comment 20 — dmeehan@mozilla.com — 2025-09-18T19:13:07Z**

https://hg-edge.mozilla.org/mozilla-central/rev/7f7dcc4b99e95e5a2047a86be1f4da53eeca6d0d
https://hg-edge.mozilla.org/mozilla-central/rev/458f9ded3c843fc4b301c29dc597aa6499b66ede
