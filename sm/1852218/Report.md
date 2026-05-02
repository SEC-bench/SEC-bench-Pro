# Assertion failure: aPtr.mMutationCount == mMutationCount, at dist/include/mozilla/HashTable.h:2137

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1852218
CVE: CVE-2023-5172
Component: JavaScript Engine: JIT
Bounty: (unknown)
Date: 2023-09-08T07:52:30Z
Keywords: assertion, csectype-uaf, regression, sec-high, testcase

The following testcase crashes on mozilla-central revision 20230907-f829a45e2207 (debug build, run with --fuzzing-safe --no-threads --disable-oom-functions --baseline-eager --ion-warmup-threshold=0):

    function patchSrc(src, exc) {
      try {
        let srcParts = src.split("\n");
        let srcLine = "d262 = undefined;"
        srcParts.splice(exc.lineNumber - 1, 0, srcLine);
        return srcParts.join("\n");
      } catch(exc) {}
    }
    initGlobals = new Set(Object.keys(this));
    loadFile(`
    //xorefuzz-dcd-selectmode
    /*---
    description: SingleNameBinding does assign name
    defines: [DETACHBUFFER]
    ---*/
    function DETACHBUFFER(buffer) {
      d262.detachArrayBuffer(buffer);
    }
    assert = initGlobals;
    assert.sameValue = DETACHBUFFER;
    `);
    loadFile(`
    //xorefuzz-dcd-evaluate
    // GENERATED, DO NOT EDIT
    // file: temporalHelpers.js
    // Copyright (C) 2021 Igalia, S.L. All rights reserved.
    // This code is governed by the BSD license found in the LICENSE file.
    /*---
    ---*/
    C55 = class {
      [1 * 1] = () => {};
    };
    c29 = new C55();
    assert.sameValue();
    `);
    function loadFile(lfVarx) {
        try {
          evaluate(lfVarx);
        } catch (lfVare) {
          if (lfVare.toString().indexOf("is not defined") >= 0 || lfVare.toString().indexOf("is undefined") >= 0) {
            newSrc = patchSrc(lfVarx, lfVare);
            loadFile(newSrc);
          }
        }
    }


Backtrace:

    received signal SIGSEGV, Segmentation fault.
    #0  0x00005555580a0d59 in bool mozilla::detail::HashTable<mozilla::HashMapEntry<unsigned int, js::jit::JitHintsMap::IonHint*>, mozilla::HashMap<unsigned int, js::jit::JitHintsMap::IonHint*, mozilla::DefaultHasher<unsigned int, void>, js::SystemAllocPolicy>::MapHashPolicy, js::SystemAllocPolicy>::add<unsigned int&, js::jit::JitHintsMap::IonHint*&>(mozilla::detail::HashTable<mozilla::HashMapEntry<unsigned int, js::jit::JitHintsMap::IonHint*>, mozilla::HashMap<unsigned int, js::jit::JitHintsMap::IonHint*, mozilla::DefaultHasher<unsigned int, void>, js::SystemAllocPolicy>::MapHashPolicy, js::SystemAllocPolicy>::AddPtr&, unsigned int&, js::jit::JitHintsMap::IonHint*&) ()
    #1  0x000055555809b6a4 in js::jit::JitHintsMap::addIonHint(unsigned int, mozilla::detail::HashTable<mozilla::HashMapEntry<unsigned int, js::jit::JitHintsMap::IonHint*>, mozilla::HashMap<unsigned int, js::jit::JitHintsMap::IonHint*, mozilla::DefaultHasher<unsigned int, void>, js::SystemAllocPolicy>::MapHashPolicy, js::SystemAllocPolicy>::AddPtr&) ()
    #2  0x000055555809bc11 in js::jit::JitHintsMap::recordIonCompilation(JSScript*) ()
    #3  0x0000555557f6536d in js::jit::CodeGenerator::link(JSContext*, js::jit::WarpSnapshot const*) ()
    #4  0x0000555557f9d522 in js::jit::Compile(JSContext*, JS::Handle<JSScript*>, js::jit::BaselineFrame*, unsigned char*) ()
    #5  0x0000555557f9c7c8 in js::jit::CanEnterIon(JSContext*, js::RunState&) ()
    #6  0x000055555808bc3c in js::jit::MaybeEnterJit(JSContext*, js::RunState&) ()
    #7  0x0000555557040e2f in js::RunScript(JSContext*, js::RunState&) ()
    #8  0x0000555557041811 in js::InternalCallOrConstruct(JSContext*, JS::CallArgs const&, js::MaybeConstruct, js::CallReason) ()
    #9  0x0000555557043a27 in InternalConstruct(JSContext*, js::AnyConstructArgs const&, js::CallReason) ()
    #10 0x0000555557b95bd5 in js::jit::DoCallFallback(JSContext*, js::jit::BaselineFrame*, js::jit::ICFallbackStub*, unsigned int, JS::Value*, JS::MutableHandle<JS::Value>) ()
    #11 0x0000003afc1c0f07 in ?? ()
    [...]
    #22 0x0000000000000000 in ?? ()
    rax	0x55555583caad	93824995281581
    rbx	0x7ffff33fc000	140737274429440
    rcx	0x5555588e7888	93825046313096
    rdx	0x0	0
    rsi	0x7ffff6abd770	140737331844976
    rdi	0x7ffff6abc540	140737331840320
    rbp	0x7ffffff85850	140737487853648
    rsp	0x7ffffff85820	140737487853600
    r8	0x7ffff6abd770	140737331844976
    r9	0x7ffff7fe3840	140737354020928
    r10	0x2	2
    r11	0x0	0
    r12	0x7ffffff85874	140737487853684
    r13	0xffffffffffffff	72057594037927935
    r14	0x7ffffff858b0	140737487853744
    r15	0xeb674046c8035882	-1484146879447738238
    rip	0x5555580a0d59 <bool mozilla::detail::HashTable<mozilla::HashMapEntry<unsigned int, js::jit::JitHintsMap::IonHint*>, mozilla::HashMap<unsigned int, js::jit::JitHintsMap::IonHint*, mozilla::DefaultHasher<unsigned int, void>, js::SystemAllocPolicy>::MapHashPolicy, js::SystemAllocPolicy>::add<unsigned int&, js::jit::JitHintsMap::IonHint*&>(mozilla::detail::HashTable<mozilla::HashMapEntry<unsigned int, js::jit::JitHintsMap::IonHint*>, mozilla::HashMap<unsigned int, js::jit::JitHintsMap::IonHint*, mozilla::DefaultHasher<unsigned int, void>, js::SystemAllocPolicy>::MapHashPolicy, js::SystemAllocPolicy>::AddPtr&, unsigned int&, js::jit::JitHintsMap::IonHint*&)+1177>
    => 0x5555580a0d59 <_ZN7mozilla6detail9HashTableINS_12HashMapEntryIjPN2js3jit11JitHintsMap7IonHintEEENS_7HashMapIjS7_NS_13DefaultHasherIjvEENS3_17SystemAllocPolicyEE13MapHashPolicyESC_E3addIJRjRS7_EEEbRNSF_6AddPtrEDpOT_+1177>:	movl   $0x859,0x0
       0x5555580a0d64 <_ZN7mozilla6detail9HashTableINS_12HashMapEntryIjPN2js3jit11JitHintsMap7IonHintEEENS_7HashMapIjS7_NS_13DefaultHasherIjvEENS3_17SystemAllocPolicyEE13MapHashPolicyESC_E3addIJRjRS7_EEEbRNSF_6AddPtrEDpOT_+1188>:	callq  0x555556f36513 <abort>



The testcase here reproduces reliably for me after 6-10 seconds but it does not reduce further and is comment-sensitive (so don't be rude around it ;)).

To me, this looks like a subtle form of memory corruption going on in JITs, marking s-s.

---

**Comment 1 — choller@mozilla.com — 2023-09-08T07:52:33Z**

Created attachment 9352172
Detailed Crash Information

---

**Comment 2 — choller@mozilla.com — 2023-09-08T07:52:34Z**

Created attachment 9352173
Testcase

---

**Comment 3 — bugmon@mozilla.com — 2023-09-08T08:39:15Z**

Verified bug as reproducible on mozilla-central 20230908034814-3096b15a785a.
Unable to bisect testcase (Unable to launch the start build!):
> Start: c3cd822e69a160e5358aa061d34f990b40ab100e (20220909043058)
> End: f829a45e22076f02abeee8ca0f757a842da4f4de (20230907040951)
> BuildFlags: BuildFlags(asan=None, tsan=None, debug=True, fuzzing=None, coverage=None, valgrind=None, no_opt=None, fuzzilli=None, nyx=None)

---

**Comment 4 — iireland@mozilla.com — 2023-09-08T19:17:40Z**

This is a bug in Denis's jit-hints work. I don't think it's security sensitive.

To avoid having to do multiple lookups, after checking to see if we have an existing hint, we pass the lookup result into [addIonHint](https://searchfox.org/mozilla-central/rev/7fe1954b761abeff36122b4a6ac74619704ee787/js/src/jit/JitHints.cpp#21-27). Before we add the hint, we check to see if we have exceeded IonHintMaxEntries, in which case we remove the oldest hint first.

In debug builds, hash tables store the number of mutations that have taken place and cache that number in each lookup result to make sure we don't mutate the hashtable between the lookup and the eventual insertion. Removing an existing hint violates this rule.

I think we can fix the bug by simply delaying the hint removal until after we've added the new hint.

Here's a reduced testcase:
```
// |jit-test| --fast-warmup; --no-threads

function makeIonCompiledScript(n) {
  let src = "";
  for (var i = 0; i < n; i++) {
    src += "\n";
  }
  src += "function f() {}";
  eval(src);
  for (var i = 0; i < 50; i++) {
    f();
  }
  return f;
}

for (var i = 0; i < 5010; i++) {
  makeIonCompiledScript(i);
}
```

---

**Comment 5 — iireland@mozilla.com — 2023-09-08T19:35:35Z**

Created attachment 9352291
Bug 1852218: Remove old hints after adding new hints r=dpalmeiro!

---

**Comment 6 — continuation@gmail.com — 2023-09-08T20:19:52Z**

(In reply to Iain Ireland [:iain] from comment #4)
> This is a bug in Denis's jit-hints work. I don't think it's security sensitive.

I think this is a security issue. remove() can call shrinkIfUnderloaded(), which can call changeTableSize() which will reallocate the hashtable's storage, thereby invalidating internal pointers into the hash table like `p`.

---

**Comment 7 — continuation@gmail.com — 2023-09-08T20:28:47Z**

(Unless I'm misunderstanding how add ptr works for HashTable...)

---

**Comment 8 — release-mgmt-account-bot@mozilla.tld — 2023-09-08T20:42:23Z**

Set release status flags based on info from the regressing bug 1837192

---

**Comment 9 — iireland@mozilla.com — 2023-09-08T21:38:26Z**

In this particular case I think we will avoid shrinkIfUnderloaded because we never actually decrease the overall number of entries in the hash table. We keep adding entries until we hit 5000, and then each time we add an entry after that we remove the oldest.

If there's something that can go badly wrong here, I think it would have to be something like:
1. Fill up the hint map.
2. Add a new hint which hashes to the same bucket as the oldest hint. Get back a slot based on that collision.
3. Remove the old hint. It looks like we take a [slightly different path](https://searchfox.org/mozilla-central/rev/c1fb133ca4901985070e519c92322b432fa254c5/mfbt/HashTable.h#1157) depending on whether there's been a collision for that slot, marking it as Free rather than Removed.
4. Add the new hint. The hash table is now in a slightly inconsistent state.
5. ???
6. Profit!

More broadly, though, you're right that we should probably treat this as s-s.

---

**Comment 10 — iireland@mozilla.com — 2023-09-11T16:00:06Z**

Comment on attachment 9352291
Bug 1852218: Remove old hints after adding new hints r=dpalmeiro!

### Security Approval Request
* **How easily could an exploit be constructed based on the patch?**: Fairly difficult. If you can control hash collisions then you can get the hash table into an inconsistent state, but I don't think you can reallocate the backing storage.
* **Do comments in the patch, the check-in comment, or tests included in the patch paint a bulls-eye on the security problem?**: No
* **Which older supported branches are affected by this flaw?**: 117, 118, 119
* **If not all supported branches, which bug introduced the flaw?**: Bug 1837192
* **Do you have backports for the affected branches?**: No
* **If not, how different, hard to create, and risky will they be?**: The patch should apply cleanly.
* **How likely is this patch to cause regressions; how much testing does it need?**: Unlikely. It reorders a small amount of code.
* **Is Android affected?**: Yes

---

**Comment 11 — tom@mozilla.com — 2023-09-11T16:14:34Z**

Comment on attachment 9352291
Bug 1852218: Remove old hints after adding new hints r=dpalmeiro!

Approved to land and uplift

---

**Comment 12 — iireland@mozilla.com — 2023-09-11T16:59:42Z**

Comment on attachment 9352291
Bug 1852218: Remove old hints after adding new hints r=dpalmeiro!

### Beta/Release Uplift Approval Request
* **User impact if declined**: Hashtable invariants are violated. I can't rule out the possibility that it's exploitable.
* **Is this code covered by automated tests?**: Yes
* **Has the fix been verified in Nightly?**: Yes
* **Needs manual test from QE?**: No
* **If yes, steps to reproduce**: 
* **List of other uplifts needed**: None
* **Risk to taking this patch**: Low
* **Why is the change risky/not risky? (and alternatives if risky)**: It reorders a small section of code to avoid mutating a hashtable with a live AddPtr.
* **String changes made/needed**: 
* **Is Android affected?**: Yes

---

**Comment 13 — pulsebot@bmo.tld — 2023-09-11T17:04:54Z**

Pushed by iireland@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/754947adaad8
Remove old hints after adding new hints r=dpalmeiro

---

**Comment 14 — ryanvm@gmail.com — 2023-09-11T17:26:26Z**

Comment on attachment 9352291
Bug 1852218: Remove old hints after adding new hints r=dpalmeiro!

This can ride 118 to release.

---

**Comment 15 — aryx.bugmail@gmx-topmail.de — 2023-09-11T18:27:46Z**

Backed out for failing its own test on Spidermonkey ARM64.

https://hg.mozilla.org/integration/autoland/rev/754947adaad8ea8d87b61fb678ae58db5edb1ea6

[Push with failures](https://treeherder.mozilla.org/jobs?repo=autoland&group_state=expanded&resultStatus=pending%2Crunning%2Ctestfailed%2Cbusted%2Cexception&revision=754947adaad8ea8d87b61fb678ae58db5edb1ea6&selectedTaskRun=ZimAs-9hT7CzUd9p6lvjqQ.0)
[Failure log](https://treeherder.mozilla.org/logviewer?job_id=428710442&repo=autoland)
> TEST-UNEXPECTED-FAIL | js/src/jit-test/tests/bug1852218.js | Timeout (code -6, args "--fast-warmup --no-threads") [150.3 s]

---

**Comment 16 — pulsebot@bmo.tld — 2023-09-11T18:32:14Z**

Backout by sstanca@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/8cc42aa6860e
Backed out changeset 754947adaad8 for causing SM bustages in bug1852218.js. CLOSED TREE

---

**Comment 17 — iireland@mozilla.com — 2023-09-11T20:39:49Z**

Weird. I don't see why this test should be especially slow in the simulator.

It should be fine to disable this in the arm64 simulator, anyway.

---

**Comment 18 — pulsebot@bmo.tld — 2023-09-11T22:31:30Z**

Pushed by iireland@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/78b325d096c9
Remove old hints after adding new hints r=dpalmeiro

---

**Comment 19 — aryx.bugmail@gmx-topmail.de — 2023-09-12T16:36:11Z**

https://hg.mozilla.org/mozilla-central/rev/78b325d096c9

---

**Comment 20 — bugmon@mozilla.com — 2023-09-13T00:47:29Z**

Verified bug as fixed on rev mozilla-central 20230912163015-fc9333c3b9f7.
Removing bugmon keyword as no further action possible.  Please review the bug and re-add the keyword for further analysis.

---

**Comment 21 — pascalc@gmail.com — 2023-09-13T16:00:07Z**

Comment on attachment 9352291
Bug 1852218: Remove old hints after adding new hints r=dpalmeiro!

Approved for 118.0b9 (last beta)  thanks.

---

**Comment 22 — pulsebot@bmo.tld — 2023-09-13T16:13:20Z**

https://hg.mozilla.org/releases/mozilla-beta/rev/3694c9cea635

---

**Comment 23 — tom@mozilla.com — 2023-09-21T16:03:51Z**

Created attachment 9354379
advisory.txt
