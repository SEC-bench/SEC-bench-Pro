# AddressSanitizer: heap-use-after-free involving js::jit::ICScript::active or Assertion failure: findInlinedChild(fallback->pcOffset())->active(), at jit/JitScript.cpp:521

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1871618
Component: JavaScript Engine: JIT
Bounty: (unknown)
Date: 2023-12-22T22:16:38Z
Keywords: csectype-uaf, regression, reporter-external, sec-high, testcase

Created attachment 9370083
stack

I have a hard-to-reproduce issue here, debug ASan build stack is attached.

Run with `--fast-warmup --ion-gvn=off --gc-zeal=10,233 --blinterp-warmup-threshold=1 --baseline-warmup-threshold=0 --ion-licm=off --ion-warmup-threshold=100 --fuzzing-safe --ion-optimize-shapeguards=off --no-incremental-gc --disable-parser-deferred-alloc --differential-testing --ion-edgecase-analysis=off`, compile with `AR=ar sh ../configure --enable-debug --enable-address-sanitizer --enable-fuzzing --disable-jemalloc --disable-stdcxx-compat --without-sysroot --with-ccache --enable-nspr-build --enable-ctypes --enable-debug-symbols --enable-gczeal --enable-rust-simd --disable-tests`, tested on m-c rev e22abf3976f2.

Setting s-s because it's an ASan UAF as a start, albeit with a debug build. I'll keep trying to reproduce with other flags and builds.

cc'ing :iain, :jandem, :jonco, :sfink, anybody who might be around prior to the holidays.

---

**Comment 1 — nth10sd@gmail.com — 2023-12-22T22:25:29Z**

Will, :sdetar mentioned get you in the loop for triage. I'm around for a couple of moments if anybody needs me to try any commands on the very-hard-to-reproduce issue.

---

**Comment 2 — nth10sd@gmail.com — 2023-12-22T22:29:50Z**

The testcase is quite large and unreduceable. If the debug ASan stack points to the problem, that will be great, but someone should take a look to confirm.

---

**Comment 3 — dveditz@mozilla.com — 2023-12-31T05:26:09Z**

The `testcase` keyword means there's a testcase attached to the bug, to signal it's 100% ready for analysis by anyone. Maybe you could capture a pernosco case if your unreduced testcase is unworkable?

---

**Comment 4 — nth10sd@gmail.com — 2023-12-31T06:55:55Z**

I have a coredump of a testcase I'm attaching. However, the dump needs the binary I have locally.

Either I could send the shell to someone, or I could try inputting commands for anybody.

I couldn't reproduce it in `rr`, at least not yet. Chaos mode in `rr` doesn't work either.

---

**Comment 5 — nth10sd@gmail.com — 2023-12-31T06:56:40Z**

Created attachment 9370606
etestcase.js

---

**Comment 6 — nth10sd@gmail.com — 2023-12-31T08:02:19Z**

Created attachment 9370608
debug stack

```
Assertion failure: findInlinedChild(fallback->pcOffset())->active(), at /home/yksnegowt/trees/mozilla-central/js/src/jit/JitScript.cpp:521
#01: ???[/home/yksnegowt/shell-cache/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422 +0x3a064f3]
#02: ???[/home/yksnegowt/shell-cache/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422 +0x3a231d7]
#03: ???[/home/yksnegowt/shell-cache/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422 +0x3a23281]
#04: ???[/home/yksnegowt/shell-cache/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422 +0x3a06360]
#05: ???[/home/yksnegowt/shell-cache/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422 +0x3a061f9]
#06: ???[/home/yksnegowt/shell-cache/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422 +0x335cfaa]
#07: ???[/home/yksnegowt/shell-cache/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422 +0x3358295]
#08: JS::Zone::forceDiscardJitCode(JS::GCContext*, JS::Zone::DiscardOptions const&)[/home/yksnegowt/shell-cache/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422 +0x3357efd]
#09: JS::Zone::discardJitCode(JS::GCContext*, JS::Zone::DiscardOptions const&)[/home/yksnegowt/shell-cache/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422 +0x3357dca]
#10: JS::Zone::prepareForCompacting()[/home/yksnegowt/shell-cache/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422 +0x31eb476]
#11: ???[/home/yksnegowt/shell-cache/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422 +0x31ead5e]
#12: ???[/home/yksnegowt/shell-cache/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422 +0x31e92bd]
#13: ???[/home/yksnegowt/shell-cache/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422 +0x31e8f52]
#14: ???[/home/yksnegowt/shell-cache/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422 +0x3202e57]
#15: ???[/home/yksnegowt/shell-cache/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422 +0x3204ee5]
#16: ???[/home/yksnegowt/shell-cache/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422 +0x3205e82]
#17: ???[/home/yksnegowt/shell-cache/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422 +0x31e45d2]
#18: ???[/home/yksnegowt/shell-cache/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422 +0x31e4af6]
#19: ???[/home/yksnegowt/shell-cache/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422 +0x3210051]
#20: ???[/home/yksnegowt/shell-cache/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422 +0x259e52f]
#21: ???[/home/yksnegowt/shell-cache/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422 +0x2a0062d]
#22: ???[/home/yksnegowt/shell-cache/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422 +0x2a005d2]
#23: ???[/home/yksnegowt/shell-cache/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422 +0x2a0054d]
#24: ???[/home/yksnegowt/shell-cache/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422 +0x2af1081]
#25: ???[/home/yksnegowt/shell-cache/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422/js-dbg-optDisabled-64-linux-x86_64-3e9c9290e422 +0x2b138d1]
#26: ??? (???:???)
Segmentation fault (core dumped)
```

---

**Comment 7 — nth10sd@gmail.com — 2023-12-31T08:40:15Z**

Created attachment 9370610
full backtrace debug stack

Configuration command is: `AR=ar sh ../configure --enable-debug --disable-optimize --with-ccache --enable-nspr-build --enable-ctypes --enable-debug-symbols --enable-gczeal --enable-rust-simd --disable-tests`

Run with: `--ion-warmup-threshold=0 --no-native-regexp --ion-offthread-compile=on --execute=\"setJitCompilerOption\(\\\"ion.forceinlineCaches\\\",1\)\" --baseline-warmup-threshold=0 --ion-extra-checks --gc-zeal=14,79 --ion-optimize-shapeguards=off --scalar-replace-arguments --fuzzing-safe --blinterp-warmup-threshold=0 --ion-gvn=off --differential-testing --fast-warmup --enable-shadow-realms`

On latest m-c rev 3e9c9290e422.

---

**Comment 8 — nth10sd@gmail.com — 2023-12-31T19:44:29Z**

Created attachment 9370631
coredump.tar.xz

---

**Comment 9 — nth10sd@gmail.com — 2024-01-03T21:54:37Z**

I've given Iain access to the shell binary off thread (and contacted Jan as well).

---

**Comment 10 — jdemooij@mozilla.com — 2024-01-04T10:37:42Z**

This is a duplicate of bug 1871947.

I can reproduce both of these bugs reliably with a non-ASan debug build if I add an assertion to `ICScript::purgeStubs` (to check the `ICScript`'s bytecode size field). This fails with jemalloc because we get the jemalloc poison value. I verified the patch for bug 1871947 fixes this test case too.

I'll add this debug assertion to the follow-up patch in that bug.

*** This bug has been marked as a duplicate of bug 1871947 ***

---

**Comment 11 — jdemooij@mozilla.com — 2024-01-04T11:45:49Z**

For bug bounty purposes: this bug was reported *before* bug 1871947. I just happened to fix the other one first.

---

**Comment 12 — dveditz@mozilla.com — 2024-05-15T04:14:01Z**

Making Firefox 122 security bugs public.  [bugspam filter string: Pilgarlic-Towers]
