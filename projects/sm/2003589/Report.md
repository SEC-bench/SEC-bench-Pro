# Assertion failure: !cx->runtime()->jitRuntime()->disallowArbitraryCode(), at vm/Interpreter.cpp:407

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=2003589
Component: JavaScript Engine
Bounty: (unknown)
Date: 2025-12-02T18:33:39Z
Keywords: csectype-jit, regression, reporter-external, sec-high, testcase

Created attachment 9530415
debug stack

```js
for (var i = 0 ; i < 99 ; i++) {
  [].__proto__.__proto__ = new Proxy(Object, Object);
  Object.keys([]);
}
```

```
(gdb) bt
#0  0x0000555557370638 in MOZ_CrashSequence (aAddress=0x0, aLine=407)
    at /home/msf2/shell-cache/js-dbg-64-linux-x86_64-256e8bad1a52-598750/objdir-js/dist/include/mozilla/Assertions.h:237
#1  js::RunScript (cx=cx@entry=0x7ffff5e3c200, state=...) at /home/msf2/trees/firefox/js/src/vm/Interpreter.cpp:406
#2  0x00005555573710fc in js::InternalCallOrConstruct (cx=0x7ffff5e3c200, args=..., construct=construct@entry=js::NO_CONSTRUCT, reason=<optimized out>)
    at /home/msf2/trees/firefox/js/src/vm/Interpreter.cpp:618
#3  0x0000555557371da8 in InternalCall (cx=<optimized out>, args=..., reason=407, reason@entry=js::CallReason::Call)
    at /home/msf2/trees/firefox/js/src/vm/Interpreter.cpp:653
#4  0x0000555557371fbd in js::Call (cx=<optimized out>, fval=fval@entry=..., thisv=thisv@entry=..., args=..., rval=...,
    reason=reason@entry=js::CallReason::Call) at /home/msf2/trees/firefox/js/src/vm/Interpreter.cpp:685
#5  0x00005555574399a7 in js::Call (cx=0x7ffff5e3c200, fval=..., thisObj=<optimized out>, arg0=..., arg1=..., rval=...)
    at /home/msf2/trees/firefox/js/src/vm/Interpreter.h:145
/snip
```

```
7c0e78c0e457-597167
7c0e78c0e4575dda295abed143b32888ac5a8f5d is the first interesting commit
commit 7c0e78c0e4575dda295abed143b32888ac5a8f5d
Author: Alex Thayer
Date:   Wed Nov 19 21:05:46 2025 +0000

    Bug 1995077 - Integrate with existing iterator indices optimizations r=iain
```

Run with `--fuzzing-safe --no-threads --ion-eager`, compile with `AR=ar sh ~/trees/firefox/js/src/configure --enable-debug --enable-debug-symbols --with-ccache --enable-nspr-build --enable-ctypes --enable-gczeal --enable-rust-simd --disable-tests`, tested on gh rev 256e8bad1a52af07e29574baf4aaf02f05b39d93.

Note that a previous similar-looking bug 1853180 was marked sec-moderate.

Alex/Iain, is bug 1995077 a likely regressor?

---

**Comment 1 — release-mgmt-account-bot@mozilla.tld — 2025-12-02T18:42:30Z**

Set release status flags based on info from the regressing bug 1995077

---

**Comment 2 — dothayer@mozilla.com — 2025-12-03T19:04:31Z**

Created attachment 9530714
(secure)

---

**Comment 3 — dveditz@mozilla.com — 2025-12-03T22:18:54Z**

Our fuzzers are hitting this multiple times a day, also. See bug 1897240. Could be a different triggering issue, especially since yours was a more recent regression.

---

**Comment 4 — dveditz@mozilla.com — 2025-12-03T22:22:23Z**

10 bugs on this assertion, with at least 7 different fixes
https://bugzilla.mozilla.org/buglist.cgi?quicksearch=ALL%20sum%3A%22Assertion%20failure%3A%20!cx-%3Eruntime()-%3EjitRuntime()-%3EdisallowArbitraryCode()%22

---

**Comment 5 — iireland@mozilla.com — 2025-12-03T23:17:18Z**

This is a fairly general assertion that can catch a variety of problems. Bug 1897240 is a case where it is likely too picky, but it's hard to be completely sure. This is a real bug, though, and probably exploitable.

---

**Comment 6 — nth10sd@gmail.com — 2025-12-04T01:14:04Z**

(In reply to Iain Ireland [:iain] from comment #5)
> This is a real bug, though, and probably exploitable.

Just checking, sec-moderate is still the most appropriate here, in case it's a different problem?

---

**Comment 7 — pulsebot@bmo.tld — 2025-12-04T07:23:00Z**

Pushed by dothayer@mozilla.com:
https://github.com/mozilla-firefox/firefox/commit/1d09788fc823
https://hg.mozilla.org/integration/autoland/rev/c291f45cf566
Only enumerate own properties in Object.keys ObjToIterator r=iain

---

**Comment 8 — aryx.bugmail@gmx-topmail.de — 2025-12-04T09:48:07Z**

https://hg.mozilla.org/mozilla-central/rev/c291f45cf566

---

**Comment 9 — iireland@mozilla.com — 2025-12-04T17:01:43Z**

This is a more significant bug than bug 1897240. It's probably exploitable. Consider a case where we're indexing into an array twice at the same index with an Object.keys in between. We think that we can reuse the bounds check, but in fact the Object.keys triggers a proxy handler that shrinks the array. Suddenly we have an OOB access.

Sec-high seems reasonable to me.

---

**Comment 10 — nth10sd@gmail.com — 2025-12-04T17:05:34Z**

> Just checking, sec-moderate is still the most appropriate here, in case it's a different problem?

> Sec-high seems reasonable to me.

Forwarding to Dan.

---

**Comment 11 — iireland@mozilla.com — 2025-12-05T16:54:21Z**

Not sure how much it matters, but I think this is probably csectype-jit. (Although I don't know the exact definitions of the various categories. Are they written down anywhere?)
