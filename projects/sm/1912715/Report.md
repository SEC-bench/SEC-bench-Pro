# Assertion failure: this->is<T>(), at js/src/gc/Cell.h:193

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1912715
CVE: CVE-2024-8381
Component: JavaScript Engine
Bounty: (unknown)
Date: 2024-08-12T08:15:20Z
Keywords: csectype-wildptr, reporter-external, sec-high

Created attachment 9418784
bug.js

Steps to reproduce:

Steps to reproduce:

Checkout commit ef4ef8198add3192d1e49157fb3f377ea7e60009 and invoke the js shell as follows:
```
js --fuzzing-safe <test-case>
```




Actual results:

```
Assertion failure: this->is<T>(), at js/src/gc/Cell.h:193
```

---

**Comment 1 — continuation@gmail.com — 2024-08-12T13:44:34Z**

Please include a stack for the assertion to make it easier to triage, either as a comment or (if it is large) as an attachment.

---

**Comment 2 — sm-bugs@theinbox.de — 2024-08-12T14:49:08Z**

```
==2281576==ERROR: UndefinedBehaviorSanitizer: SEGV on unknown address 0x000000000000 (pc 0x55d46d4087f6 bp 0x7ffd6f59c290 sp 0x7ffd6f59c280 T2281576)
==2281576==The signal is caused by a WRITE memory access.
==2281576==Hint: address points to the zero page.
    #0 0x55d46d4087f6 in js::GetterSetter* js::gc::Cell::as<js::GetterSetter, void>() spidermonkey/src/js/src/gc/Cell.h:193:5
    #1 0x55d46d4087f6 in js::NativeObject::getGetterSetter(unsigned int) const spidermonkey/src/js/src/vm/NativeObject.h:1213:39
    #2 0x55d46d7ae260 in js::NativeObject::getGetter(js::PropertyInfoBase<unsigned int>) const spidermonkey/src/js/src/vm/NativeObject.h:1226:12
    #3 0x55d46d7ae260 in js::NativeObject::hasGetter(js::PropertyInfoBase<unsigned int>) const spidermonkey/src/js/src/vm/NativeObject.h:1235:41
    #4 0x55d46d7ae260 in bool GetExistingProperty<(js::AllowGC)1>(JSContext*, js::MaybeRooted<JS::Value, (js::AllowGC)1>::HandleType, js::MaybeRooted<js::NativeObject*, (js::AllowGC)1>::HandleType, js::MaybeRooted<JS::PropertyKey, (js::AllowGC)1>::HandleType, js::PropertyInfoBase<unsigned int>, js::MaybeRooted<JS::Value, (js::AllowGC)1>::MutableHandleType) spidermonkey/src/js/src/vm/NativeObject.cpp:2163:45
    #5 0x55d46d7adfd1 in js::NativeGetExistingProperty(JSContext*, JS::Handle<JSObject*>, JS::Handle<js::NativeObject*>, JS::Handle<JS::PropertyKey>, js::PropertyInfoBase<unsigned int>, JS::MutableHandle<JS::Value>) spidermonkey/src/js/src/vm/NativeObject.cpp:2178:10
    #6 0x55d46d34c78e in bool js::FetchName<(js::GetNameMode)0>(JSContext*, JS::Handle<JSObject*>, JS::Handle<JSObject*>, JS::Handle<js::PropertyName*>, js::PropertyResult const&, JS::MutableHandle<JS::Value>) spidermonkey/src/js/src/vm/Interpreter-inl.h:146:12
    #7 0x55d46d395df0 in bool js::GetEnvironmentName<(js::GetNameMode)0>(JSContext*, JS::Handle<JSObject*>, JS::Handle<js::PropertyName*>, JS::MutableHandle<JS::Value>) spidermonkey/src/js/src/vm/Interpreter-inl.h:198:10
    #8 0x55d46d366a5f in GetNameOperation(JSContext*, JS::Handle<JSObject*>, JS::Handle<js::PropertyName*>, JSOp, JS::MutableHandle<JS::Value>) spidermonkey/src/js/src/vm/Interpreter.cpp:265:10
    #9 0x55d46d366a5f in js::Interpret(JSContext*, js::RunState&) spidermonkey/src/js/src/vm/Interpreter.cpp:3500:12
    #10 0x55d46d34d8e1 in js::RunScript(JSContext*, js::RunState&) spidermonkey/src/js/src/vm/Interpreter.cpp:461:13
    #11 0x55d46d352ac1 in js::ExecuteKernel(JSContext*, JS::Handle<JSScript*>, JS::Handle<JSObject*>, js::AbstractFramePtr, JS::MutableHandle<JS::Value>) spidermonkey/src/js/src/vm/Interpreter.cpp:848:13
    #12 0x55d46d3532cc in js::Execute(JSContext*, JS::Handle<JSScript*>, JS::Handle<JSObject*>, JS::MutableHandle<JS::Value>) spidermonkey/src/js/src/vm/Interpreter.cpp:880:10
    #13 0x55d46d59f969 in ExecuteScript(JSContext*, JS::Handle<JSObject*>, JS::Handle<JSScript*>, JS::MutableHandle<JS::Value>) spidermonkey/src/js/src/vm/CompilationAndEvaluation.cpp:495:10
    #14 0x55d46d59fbe7 in JS_ExecuteScript(JSContext*, JS::Handle<JSScript*>) spidermonkey/src/js/src/vm/CompilationAndEvaluation.cpp:519:10
    #15 0x55d46d28974e in RunFile(JSContext*, char const*, _IO_FILE*, CompileUtf8, bool, bool) spidermonkey/src/js/src/shell/js.cpp:1205:10
    #16 0x55d46d288ab5 in Process(JSContext*, char const*, bool, FileKind) spidermonkey/src/js/src/shell/js.cpp
    #17 0x55d46d2437ae in ProcessArgs(JSContext*, js::cli::OptionParser*) spidermonkey/src/js/src/shell/js.cpp:11284:10
    #18 0x55d46d2437ae in Shell(JSContext*, js::cli::OptionParser*) spidermonkey/src/js/src/shell/js.cpp:11536:12
    #19 0x55d46d23b3c0 in main spidermonkey/src/js/src/shell/js.cpp:12068:12
    #20 0x7f0d4e631d8f in __libc_start_call_main csu/../sysdeps/nptl/libc_start_call_main.h:58:16
    #21 0x7f0d4e631e3f in __libc_start_main csu/../csu/libc-start.c:392:3
    #22 0x55d46d204d38 in _start (spidermonkey/src/reproducebuild/dist/bin/js+0x1c25d38) (BuildId: 35d8a8a3c389066dde8dc90be8c5997d)
```

---

**Comment 3 — iireland@mozilla.com — 2024-08-14T01:41:24Z**

Oh, this is a good find.

Very slightly cleaned up testcase:
```
const obj = {
  get prop() {
    Object.defineProperty(this, "prop", { enumerable: true, value: 0});
    return false;
  },
};
obj[Symbol.unscopables] = obj;
with (obj) {
  assertEq(prop, 0);
}
```
We create an object with a getter that will replace itself with a data property, and set it to be its own `Symbol.unscopables`. Then we look that property up inside a `with`. In [with_LookupProperty](https://searchfox.org/mozilla-central/rev/02a4a649ed75ebaf3fbdf301c3d3137baf6842a1/js/src/vm/EnvironmentObject.cpp#811-826), we:
1. Do a LookupProperty for obj.prop. This determines that it's an own-property getter, and populates the PropertyResult.
2. Call CheckUnscopables to determine whether we should ignore this property. In CheckUnscopables, we get`obj[Symbol.unscopables]` (which is just `obj`), and then get obj.prop. This triggers the getter, which replaces the property with a data property and returns `false` to indicate that this property is not unscopable.
3. We pass the PropertyResult into FetchName. It still thinks that the property is a getter, even though it's been replaced.
4. Explosions and sadness.

In a release build without this assertion, I believe we will load the new value of the slot as a pointer, load the first word of that value (which is where the getter would be stored if it were actually a getter), mask off any hypothetical tag bits, and then call it as a getter. This kind of type confusion is probably exploitable somehow.

Fixing this is kind of annoying. In general we don't want to call LookupName again, both because it's slow and because it can have observable side effects. A hacky patch to call LookupName again iff the shape of the object changed after calling CheckUnscopables fixes the bug, but it feels like we should be able to do something better.

---

**Comment 4 — iireland@mozilla.com — 2024-08-14T20:22:32Z**

Created attachment 9419176
Bug 1912715: Simplify with-env handling in FetchName r=jandem

---

**Comment 5 — iireland@mozilla.com — 2024-08-14T20:22:43Z**

Created attachment 9419177
Bug 1912715: Add tests r=jandem

---

**Comment 6 — iireland@mozilla.com — 2024-08-15T17:54:21Z**

Comment on attachment 9419176
Bug 1912715: Simplify with-env handling in FetchName r=jandem

### Security Approval Request
* **How easily could an exploit be constructed based on the patch?**: Non-trivial, but I think doable. After figuring out that Symbol.unscopables is the problem (which the patch doesn't point at directly), there are a variety of options for how to make things go wrong, and I assume that a sufficiently dedicated attacker could make at least one of them work.
* **Do comments in the patch, the check-in comment, or tests included in the patch paint a bulls-eye on the security problem?**: No
* **Which branches (beta, release, and/or ESR) are affected by this flaw, and do the release status flags reflect this affected/unaffected state correctly?**: All
* **If not all supported branches, which bug introduced the flaw?**: None
* **Do you have backports for the affected branches?**: No
* **If not, how different, hard to create, and risky will they be?**: The patch should apply cleanly.
* **How likely is this patch to cause regressions; how much testing does it need?**: This causes property lookups inside a `with` statement to take a slow path. It should not cause correctness regressions. It might cause performance regressions, but we don't care about `with` performance.
* **Is the patch ready to land after security approval is given?**: Yes
* **Is Android affected?**: Yes

---

**Comment 7 — pulsebot@bmo.tld — 2024-08-20T18:45:35Z**

Pushed by tritter@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/4f1411f1beb6
Simplify with-env handling in FetchName r=jandem

---

**Comment 8 — aryx.bugmail@gmx-topmail.de — 2024-08-21T09:34:21Z**

https://hg.mozilla.org/mozilla-central/rev/4f1411f1beb6

---

**Comment 9 — release-mgmt-account-bot@mozilla.tld — 2024-08-22T12:02:13Z**

The patch landed in nightly and beta is affected.
:iain, is this bug important enough to require an uplift?
- If yes, please nominate the patch for beta approval.
- If no, please set `status-firefox130` to `wontfix`.

For more information, please visit [BugBot documentation](https://wiki.mozilla.org/BugBot#uplift_beta.py).

---

**Comment 10 — iireland@mozilla.com — 2024-08-22T14:22:51Z**

Comment on attachment 9419176
Bug 1912715: Simplify with-env handling in FetchName r=jandem

### Beta/Release Uplift Approval Request
* **User impact if declined**: Potential sec bug
* **Is this code covered by automated tests?**: Yes
* **Has the fix been verified in Nightly?**: Yes
* **Needs manual test from QE?**: No
* **If yes, steps to reproduce**: 
* **List of other uplifts needed**: None
* **Risk to taking this patch**: Low
* **Why is the change risky/not risky? (and alternatives if risky)**: This pushes property lookup inside `with` environments to an already-existing slow path. It might regress performance slightly (on a feature that's been deprecated for decades) but there's very little risk of correctness/security issues.
* **String changes made/needed**: None
* **Is Android affected?**: Yes

### ESR Uplift Approval Request
* **If this is not a sec:{high,crit} bug, please state case for ESR consideration**: Sec-high
* **User impact if declined**: Sec-high
* **Fix Landed on Version**: 131
* **Risk to taking this patch**: Low
* **Why is the change risky/not risky? (and alternatives if risky)**: This pushes property lookup inside `with` environments to an already-existing slow path. It might regress performance slightly (on a feature that's been deprecated for decades) but there's very little risk of correctness/security issues.

---

**Comment 11 — ryanvm@gmail.com — 2024-08-22T22:55:48Z**

Comment on attachment 9419176
Bug 1912715: Simplify with-env handling in FetchName r=jandem

Approved for 130.0b9, 128.2esr, and 115.15esr.

---

**Comment 12 — pulsebot@bmo.tld — 2024-08-22T22:59:28Z**

https://hg.mozilla.org/releases/mozilla-beta/rev/ac10dac000c9

---

**Comment 13 — pulsebot@bmo.tld — 2024-08-22T23:17:19Z**

https://hg.mozilla.org/releases/mozilla-esr128/rev/4b1cec5599fc

---

**Comment 14 — pulsebot@bmo.tld — 2024-08-22T23:19:06Z**

https://hg.mozilla.org/releases/mozilla-esr115/rev/8bf27be9d572

---

**Comment 15 — dveditz@mozilla.com — 2024-09-02T21:45:51Z**

Created attachment 9422109
advisory.txt

---

**Comment 16 — release-mgmt-account-bot@mozilla.tld — 2024-10-15T12:01:02Z**

a month ago, tjr placed a reminder on the bug using the whiteboard tag `[reminder-test 2024-10-15]` .

iain, please refer to the original comment to better understand the reason for the reminder.

---

**Comment 17 — pulsebot@bmo.tld — 2024-10-29T18:49:32Z**

Pushed by iireland@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/5abb2828e234
Add tests r=jandem

---

**Comment 18 — aryx.bugmail@gmx-topmail.de — 2024-10-30T09:12:43Z**

https://hg.mozilla.org/mozilla-central/rev/5abb2828e234
