# V8 sandbox violation in icu_74::UnicodeString::doAppend

Issue URL: https://issues.chromium.org/issues/393989622
VRP-Reward: 5000
Date: Feb 3, 2025 08:28PM


#### VULNERABILITY DETAILS

Converting a long string to local encoding via `"<...>".localeCompare` causes an OOB write.

#### VERSION

V8 commit: 69b47d88cb8f3bff0966000cd039b50786bbd891

#### REPRODUCTION CASE

Build args:

```
is_debug=false
is_asan=true
v8_enable_sandbox=true
v8_enable_memory_corruption_api=true
dcheck_always_on=false
v8_static_library=true
v8_fuzzilli=false
target_cpu="x64"
```

Shell args: `d8 --single-threaded --sandbox-fuzzing --allow-natives-syntax --expose-gc bug.js`

##### ASAN Report:

```
==180411==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x7a72fffff7f0 at pc 0x5645f9e49ac6 bp 0x7fff70df8510 sp 0x7fff70df7cd0
WRITE of size 4294967286 at 0x7a72fffff7f0 thread T0
    #0 0x5645f9e49ac5 in __asan_memmove /b/s/w/ir/cache/builder/src/third_party/llvm/compiler-rt/lib/asan/asan_interceptors_memintrinsics.cpp:71:3
    #1 0x564600fdec1b in us_arrayCopy third_party/icu/source/common/unistr.cpp:87:5
    #2 0x564600fdec1b in icu_74::UnicodeString::doAppend(char16_t const*, int, int) third_party/icu/source/common/unistr.cpp:1641:7
    #3 0x5645fd89268d in v8::internal::Intl::ToICUUnicodeString(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::String>, int) src/objects/intl-objects.cc:240:10
    #4 0x5645fd8ad712 in v8::internal::Intl::CompareStrings(v8::internal::Isolate*, icu_74::Collator const&, v8::internal::DirectHandle<v8::internal::String>, v8::internal::DirectHandle<v8::internal::String>, v8::internal::Intl::CompareStringsOptions) src/objects/intl-objects.cc:1483:7
    #5 0x5645fd8aa9b1 in v8::internal::Intl::StringLocaleCompare(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::String>, v8::internal::DirectHandle<v8::internal::String>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>, char const*) src/objects/intl-objects.cc:1037:10
    #6 0x5645fb14f0ad in v8::internal::Builtin_Impl_StringPrototypeLocaleCompareIntl(v8::internal::BuiltinArguments, v8::internal::Isolate*) src/builtins/builtins-intl.cc:74:31
    #7 0x5645fb14ca6f in v8::internal::Builtin_StringPrototypeLocaleCompareIntl(int, unsigned long*, v8::internal::Isolate*) src/builtins/builtins-intl.cc:64:1
    #8 0x564604c878b5 in Builtins_CEntry_Return1_ArgvOnStack_BuiltinExit setup-isolate-deserialize.cc
    #9 0x564604be0c74 in Builtins_InterpreterEntryTrampoline setup-isolate-deserialize.cc
    #10 0x564604bde75b in Builtins_JSEntryTrampoline setup-isolate-deserialize.cc
    #11 0x564604bde4aa in Builtins_JSEntry setup-isolate-deserialize.cc
    #12 0x5645fb7af3e6 in v8::internal::GeneratedCode<unsigned long, unsigned long, unsigned long, unsigned long, unsigned long, long, unsigned long**>::Call(unsigned long, unsigned long, unsigned long, unsigned long, long, unsigned long**) src/execution/simulator.h:191:12
    #13 0x5645fb7a4b78 in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:437:22
    #14 0x5645fb7a6026 in v8::internal::Execution::CallScript(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>) src/execution/execution.cc:537:10
    #15 0x5645fa854468 in v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) src/api/api.cc:2147:7
    #16 0x5645fa8531b6 in v8::Script::Run(v8::Local<v8::Context>) src/api/api.cc:2110:10
    #17 0x5645f9f464dc in v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) src/d8/d8.cc:1017:44
    #18 0x5645f9fd4a72 in v8::SourceGroup::Execute(v8::Isolate*) src/d8/d8.cc:4959:10
    #19 0x5645f9fe9772 in v8::Shell::RunMainIsolate(v8::Isolate*, bool) src/d8/d8.cc:5904:37
    #20 0x5645f9fe8106 in v8::Shell::RunMain(v8::Isolate*, bool) src/d8/d8.cc:5812:18
    #21 0x5645f9fee603 in v8::Shell::Main(int, char**) src/d8/d8.cc:6680:18
    #22 0x5645f9fef8f1 in main src/d8/d8.cc:6772:43
    #23 0x7fbe476111c9 in __libc_start_call_main csu/../sysdeps/nptl/libc_start_call_main.h:58:16
    #24 0x7fbe4761128a in __libc_start_main csu/../csu/libc-start.c:360:3
    #25 0x5645f9dac029 in _start (/work/v8-build/v8/out/Reproduction/d8+0x24e6029) (BuildId: 9691a3447490edc9)

0x7a72fffff7f0 is located 0 bytes after 4294967280-byte region [0x7a71fffff800,0x7a72fffff7f0)
allocated by thread T0 here:
    #0 0x5645f9e4b714 in malloc /b/s/w/ir/cache/builder/src/third_party/llvm/compiler-rt/lib/asan/asan_malloc_linux.cpp:67:3
    #1 0x564600fdfe1d in allocate third_party/icu/source/common/unistr.cpp:382:34
    #2 0x564600fdfe1d in icu_74::UnicodeString::cloneArrayIfNeeded(int, int, signed char, int**, signed char) third_party/icu/source/common/unistr.cpp:1892:8
    #3 0x564600fdebb2 in icu_74::UnicodeString::doAppend(char16_t const*, int, int) third_party/icu/source/common/unistr.cpp:1631:7
    #4 0x5645fd89268d in v8::internal::Intl::ToICUUnicodeString(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::String>, int) src/objects/intl-objects.cc:240:10
    #5 0x5645fd8ad712 in v8::internal::Intl::CompareStrings(v8::internal::Isolate*, icu_74::Collator const&, v8::internal::DirectHandle<v8::internal::String>, v8::internal::DirectHandle<v8::internal::String>, v8::internal::Intl::CompareStringsOptions) src/objects/intl-objects.cc:1483:7
    #6 0x5645fd8aa9b1 in v8::internal::Intl::StringLocaleCompare(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::String>, v8::internal::DirectHandle<v8::internal::String>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>, char const*) src/objects/intl-objects.cc:1037:10
    #7 0x5645fb14f0ad in v8::internal::Builtin_Impl_StringPrototypeLocaleCompareIntl(v8::internal::BuiltinArguments, v8::internal::Isolate*) src/builtins/builtins-intl.cc:74:31
    #8 0x5645fb14ca6f in v8::internal::Builtin_StringPrototypeLocaleCompareIntl(int, unsigned long*, v8::internal::Isolate*) src/builtins/builtins-intl.cc:64:1
    #9 0x564604c878b5 in Builtins_CEntry_Return1_ArgvOnStack_BuiltinExit setup-isolate-deserialize.cc
    #10 0x564604be0c74 in Builtins_InterpreterEntryTrampoline setup-isolate-deserialize.cc
    #11 0x564604bde75b in Builtins_JSEntryTrampoline setup-isolate-deserialize.cc
    #12 0x564604bde4aa in Builtins_JSEntry setup-isolate-deserialize.cc
    #13 0x5645fb7af3e6 in v8::internal::GeneratedCode<unsigned long, unsigned long, unsigned long, unsigned long, unsigned long, long, unsigned long**>::Call(unsigned long, unsigned long, unsigned long, unsigned long, long, unsigned long**) src/execution/simulator.h:191:12
    #14 0x5645fb7a4b78 in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:437:22
    #15 0x5645fb7a6026 in v8::internal::Execution::CallScript(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>) src/execution/execution.cc:537:10
    #16 0x5645fa854468 in v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) src/api/api.cc:2147:7
    #17 0x5645fa8531b6 in v8::Script::Run(v8::Local<v8::Context>) src/api/api.cc:2110:10
    #18 0x5645f9f464dc in v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) src/d8/d8.cc:1017:44
    #19 0x5645f9fd4a72 in v8::SourceGroup::Execute(v8::Isolate*) src/d8/d8.cc:4959:10
    #20 0x5645f9fe9772 in v8::Shell::RunMainIsolate(v8::Isolate*, bool) src/d8/d8.cc:5904:37
    #21 0x5645f9fe8106 in v8::Shell::RunMain(v8::Isolate*, bool) src/d8/d8.cc:5812:18
    #22 0x5645f9fee603 in v8::Shell::Main(int, char**) src/d8/d8.cc:6680:18
    #23 0x5645f9fef8f1 in main src/d8/d8.cc:6772:43
    #24 0x7fbe476111c9 in __libc_start_call_main csu/../sysdeps/nptl/libc_start_call_main.h:58:16
    #25 0x7fbe4761128a in __libc_start_main csu/../csu/libc-start.c:360:3
    #26 0x5645f9dac029 in _start (/work/v8-build/v8/out/Reproduction/d8+0x24e6029) (BuildId: 9691a3447490edc9)

SUMMARY: AddressSanitizer: heap-buffer-overflow third_party/icu/source/common/unistr.cpp:87:5 in us_arrayCopy
Shadow bytes around the buggy address:
  0x7a72fffff500: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x7a72fffff580: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x7a72fffff600: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x7a72fffff680: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x7a72fffff700: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
=>0x7a72fffff780: 00 00 00 00 00 00 00 00 00 00 00 00 00 00[fa]fa
  0x7a72fffff800: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x7a72fffff880: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x7a72fffff900: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x7a72fffff980: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x7a72fffffa00: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
Shadow byte legend (one shadow byte represents 8 application bytes):
  Addressable:           00
  Partially addressable: 01 02 03 04 05 06 07 
  Heap left redzone:       fa
  Freed heap region:       fd
  Stack left redzone:      f1
  Stack mid redzone:       f2
  Stack right redzone:     f3
  Stack after return:      f5
  Stack use after scope:   f8
  Global redzone:          f9
  Global init order:       f6
  Poisoned by user:        f7
  Container overflow:      fc
  Array cookie:            ac
  Intra object redzone:    bb
  ASan internal:           fe
  Left alloca redzone:     ca
  Right alloca redzone:    cb
==180411==ABORTING

## V8 sandbox violation detected!
```

#### CREDIT INFORMATION

Reporter credit: v8sbxfuzz


---

**#2 — cl...@appspot.gserviceaccount.com — Feb 4, 2025 02:26AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5525256982691840](<https://clusterfuzz.com/testcase?key=5525256982691840>).


---

**#3 — bb...@google.com — Feb 4, 2025 03:36AM**

Provisional S2/P2/Foundin for V8 Sandbox bypass - Over to V8. sroettger You appear to be "next up" and clemensb is listed as OOO.


---

**#4 — cl...@appspot.gserviceaccount.com — Feb 4, 2025 11:13AM**

Detailed Report: [https://clusterfuzz.com/testcase?key=6058595317645312](<https://clusterfuzz.com/testcase?key=6058595317645312>)  
  
Fuzzer: None  
Job Type: linux_asan_d8_sandbox_testing  
Platform Id: linux  
  
Crash Type: V8 sandbox violation  
Crash Address: 0x79fefffff7f0  
Crash State:  
icu_74::UnicodeString::doAppend  
v8::internal::Intl::ToICUUnicodeString  
v8::internal::Intl::CompareStrings  
  
Sanitizer: address (ASAN)  
  
Crash Revision: [https://clusterfuzz.com/revisions?job=linux_asan_d8_sandbox_testing&revision=98480](<https://clusterfuzz.com/revisions?job=linux_asan_d8_sandbox_testing&revision=98480>)  
  
Reproducer Testcase: [https://clusterfuzz.com/download?testcase_id=6058595317645312](<https://clusterfuzz.com/download?testcase_id=6058595317645312>)  
  
To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.   
  
If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.  
  
If you have any feedback on reproducing test cases, let us know at [https://forms.gle/Yh3qCYFveHj6E5jz5](<https://forms.gle/Yh3qCYFveHj6E5jz5>) so we can improve.


---

**#5 — am...@chromium.org — Feb 4, 2025 11:24AM**

I'm pretty sure this is one is going to get assigned by clusterfuzz to saelo@ based on [https://crrev.com/c/5335156](<https://crrev.com/c/5335156>) or something close, so adding other sandbox owners to cc for visibility.


---

**#6 — 24...@project.gserviceaccount.com — Feb 4, 2025 11:48AM**

Automatically applying components based on crash stacktrace and information from OWNERS files.  
  
If this is incorrect, please apply the hotlistid:4801165.


---

**#7 — sr...@google.com — Feb 4, 2025 08:50PM**

This is what's happening:

  * Intl::ToICUUnicodeString calls the icu::UnicodeString constructor with an in-sandbox uint32 as length.
  * UnicodeString::UnicodeString (in third_party/icu) takes this length as an int32 and calls doAppend()
  * doAppend calls 
    * cloneArrayIfNeeded(newLength, getGrowCapacity(newLength)) to allocate a new buffer
    * and then memmoves into it

The problem is that it doesn't handle lengths close to intmax.

[getGrowCapacity](<https://source.chromium.org/chromium/chromium/src/+/main:third_party/icu/source/common/unistr.cpp;l=358;drc=3deaac799dc39f0ba14200463fd31bba49eb72a6>) caps the size at kMaxCapacity (0x7ffffff5), but the memmove can use a slightly larger value.

I.e. in the poc, the source length is 0x7ffffffb instead.

This sounds like a bug in third_party/icu to me, since it doesn't handle the large text length.


---

**#8 — ft...@google.com — Feb 25, 2025 05:36PM**

upstream bug filed in [https://unicode-org.atlassian.net/browse/ICU-23060](<https://unicode-org.atlassian.net/browse/ICU-23060>) Can be reproduce in by ICU 74 and 77


---

**#9 — ft...@google.com — Feb 25, 2025 06:16PM**

Fix in [https://github.com/unicode-org/icu/pull/3416](<https://github.com/unicode-org/icu/pull/3416>)


---

**#10 — ft...@google.com — Feb 26, 2025 09:45AM**

Fix landed to ICU 77 maintain branch. Cherrypick into chromium icu tree in [https://chromium-review.googlesource.com/c/chromium/deps/icu/+/6302545](<https://chromium-review.googlesource.com/c/chromium/deps/icu/+/6302545>)


---

**#11 — ap...@google.com — Feb 26, 2025 05:50PM**

Project: chromium/deps/icu  
Branch: main  
Author: Frank Tang <[ftang@chromium.org](<mailto:ftang@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6302545](<https://chromium-review.googlesource.com/6302545>)

Fix sandbox violation in icu::UnicodeString::doAppend

* * *

Expand for full commit details

```
Fix sandbox violation in icu::UnicodeString::doAppend 
 
Cherrypick https://github.com/unicode-org/icu/pull/3416 
upstream bug https://unicode-org.atlassian.net/browse/ICU-23060 
 
Bug: 393989622 
Change-Id: I700c331b79789d66c58f766f70776de2b25d5a5f 
Reviewed-on: https://chromium-review.googlesource.com/c/chromium/deps/icu/+/6302545 
Reviewed-by: David Yeung <dayeung@chromium.org> 
Reviewed-by: Hannes Payer <hpayer@chromium.org>
```

* * *

Files:

  * M `README.chromium`
  * A `patches/unicode_string.patch`
  * M `source/common/unistr.cpp`
  * M `source/test/intltest/ustrtest.cpp`
  * M `source/test/intltest/ustrtest.h`

* * *

Hash: 13d4881bc75ad15bce0e4923628d3532a73d2bd5  
Date: Tue Feb 25 16:41:04 2025

* * *


---

**#12 — el...@chromium.org — Feb 27, 2025 10:20AM**

Security shepherd: I see the fix commit there but it doesn't appear to be present in chromium yet - is there a roll that needs to happen as well?


---

**#13 — ft...@google.com — Feb 27, 2025 11:42AM**

We found the fix has another issue in ICU and I am still working on that . After I landed that to ICU and cherrypick that into chroumium ICU tree I will try to roll icu to the new commit.


---

**#14 — ft...@chromium.org — Feb 28, 2025 04:03AM**

we also need to cherrypick [https://patch-diff.githubusercontent.com/raw/unicode-org/icu/pull/3420.diff](<https://patch-diff.githubusercontent.com/raw/unicode-org/icu/pull/3420.diff>)


---

**#15 — ap...@google.com — Feb 28, 2025 05:49AM**

Project: chromium/deps/icu  
Branch: main  
Author: Frank Tang <[ftang@chromium.org](<mailto:ftang@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6310736](<https://chromium-review.googlesource.com/6310736>)

Cherrypick ICU PR3420 to fix error condition of heap buffer overflow

* * *

Expand for full commit details

```
Cherrypick ICU PR3420 to fix error condition of heap buffer overflow 
 
https://patch-diff.githubusercontent.com/raw/unicode-org/icu/pull/3420.diff 
 
We found some additional issues on the ICU and fixed that on 
https://github.com/unicode-org/icu/pull/3420 
 
Bug: 393989622 
Change-Id: I047c4a3e8c851281bf034cc79ea92ae6e897bb10 
Reviewed-on: https://chromium-review.googlesource.com/c/chromium/deps/icu/+/6310736 
Reviewed-by: Hannes Payer <hpayer@chromium.org> 
Reviewed-by: David Yeung <dayeung@chromium.org> 
Reviewed-by: Shu-yu Guo <syg@chromium.org>
```

* * *

Files:

  * M `README.chromium`
  * M `patches/unicode_string.patch`
  * M `source/common/unistr.cpp`
  * M `source/test/intltest/ustrtest.cpp`

* * *

Hash: d30b7b0bb3829f2e220df403ed461a1ede78b774  
Date: Thu Feb 27 11:14:27 2025

* * *


---

**#16 — ft...@google.com — Feb 28, 2025 05:56AM**

icu roll cl in [https://chromium-review.googlesource.com/c/chromium/src/+/6310356](<https://chromium-review.googlesource.com/c/chromium/src/+/6310356>)


---

**#17 — ft...@google.com — Feb 28, 2025 08:39AM**

the roll is complete. The bug should be fixed.


---

**#18 — ft...@google.com — Feb 28, 2025 08:40AM**

we need to make sure the icu roll into v8 too


---

**#19 — ft...@google.com — Feb 28, 2025 08:41AM**

icu on v8 v8/DEPS is auto roll from the DEPS of the chromium/src/DEPS right?


---

**#20 — ap...@google.com — Feb 28, 2025 08:43AM**

Project: chromium/src  
Branch: main  
Author: Frank Tang <[ftang@chromium.org](<mailto:ftang@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6310356](<https://chromium-review.googlesource.com/6310356>)

[intl] Roll ICU to cherrypick fix of heap buffer overflow

* * *

Expand for full commit details

```
[intl] Roll ICU to cherrypick fix of heap buffer overflow 
 
https://chromium.googlesource.com/chromium/deps/icu/+/bbccc2f..d30b7b0 
 
Patch UnicodeString to fix heap-buffer-overflow . 
    patches/unicode_string.patch 
  - https://unicode-org.atlassian.net/browse/ICU-23060 
  - https://g-issues.chromium.org/issues/393989622 
  - https://patch-diff.githubusercontent.com/raw/unicode-org/icu/pull/3416.diff 
  - https://patch-diff.githubusercontent.com/raw/unicode-org/icu/pull/3420.diff 
 
Bug: 393989622 
Change-Id: I131a13d8a08a119b59591f89013b30ef0c670ef9 
Reviewed-on: https://chromium-review.googlesource.com/c/chromium/src/+/6310356 
Reviewed-by: Shu-yu Guo <syg@chromium.org> 
Commit-Queue: Frank Tang <ftang@chromium.org> 
Reviewed-by: David Yeung <dayeung@chromium.org> 
Cr-Commit-Position: refs/heads/main@{#1426020}
```

* * *

Files:

  * M `DEPS`
  * M `third_party/icu`

* * *

Hash: 80a11a8d2bcde8846c2ee47cfa536e91553b07be  
Date: Thu Feb 27 15:39:29 2025

* * *


---

**#21 — sp...@google.com — Mar 6, 2025 09:55AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $5000.00 for this report.  
  
Rationale for this decision:  
V8 sandbox bypass demonstrating memory corruption outside the V8 heap sandbox  
  
  
Important: This payment will be issued by Bugcrowd. You will receive an email from Bugcrowd in the next 24 hours which contains a submission you must claim to be rewarded.  
  
If you do not receive an email from them, please check your spam folder and then reach out to us via a comment here. For issues related to Bugcrowd itself, please contact them via [https://bugcrowd.com/support](<https://bugcrowd.com/support>).  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#22 — am...@chromium.org — Mar 6, 2025 10:03AM**

Congratulations v8sbxfuzz! Thank you for your efforts fuzzing the V8 sandbox and reporting this issue to us!


---

**#23 — ch...@google.com — Jun 7, 2025 09:42PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
