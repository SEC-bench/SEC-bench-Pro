# V8 Sandbox Bypass: AAW (wildcopy) due to %TypedArray%.prototype.set bounds check integer overflow

Issue URL: https://issues.chromium.org/issues/391169061
VRP-Reward: 20000
Date: Jan 21, 2025 06:05AM


### VULNERABILITY DETAILS

#### Summary

V8 sandbox bypass, arbitrary address write (wildcopy) with controlled contents by bypassing bounds check with a double fetch + integer overflow in `%TypedArray%.prototype.set` -> `TypedElementsAccessor::CopyElementsHandleImpl()`.

This is an independent issue from both [b/40070746](<https://issues.chromium.org/issues/40070746>) and [b/390201806](<https://issues.chromium.org/issues/390201806>).

#### Details

Under corrupted in-sandbox memory many invariants can go wrong, e.g. `JSArray`s can hold a `HeapNumber` for its `length: Number` field that exceeds the "safe integer" bounds. Below is the internals for `%TypedArray%.prototype.set` with an array-like object:

```
// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/builtins/typed-array-set.tq;drc=8dcc3bf28a4c05a735c1963dd1dd0284ea7e2ec5;l=111
transitioning macro TypedArrayPrototypeSetArray(
    implicit context: Context, receiver: JSAny)(target: JSTypedArray,
    targetLength: uintptr, arrayArg: JSAny, targetOffset: uintptr,
    targetOffsetOverflowed: bool): void labels IfOffsetOutOfBounds {
  // 4. Let src be ? ToObject(source).
  const src: JSReceiver = ToObject_Inline(context, arrayArg);

  // 5. Let srcLength be ? LengthOfArrayLike(src).
  const srcLengthNum: Number = GetLengthProperty(src);                      // [!] this may not be a Number in safe integer range.

  // 6. If targetOffset is +∞, throw a RangeError exception.
  if (targetOffsetOverflowed) goto IfOffsetOutOfBounds;

  // 7. If srcLength + targetOffset > targetLength, throw a RangeError
  //   exception.
  const srcLength = ChangeSafeIntegerNumberToUintPtr(srcLengthNum)          // [!] broken invariant
      otherwise IfOffsetOutOfBounds;
  CheckIntegerIndexAdditionOverflow(srcLength, targetOffset, targetLength)  // [!] broken invariant
      otherwise IfOffsetOutOfBounds;

  // All the obvervable side effects are executed, so there's nothing else
  // to do with the empty source array.
  if (srcLength == 0) return;

  try {
    // ...
  } label IfSlow deferred {
    TypedArraySet(
        context, target, src, srcLengthNum, Convert<Number>(targetOffset));
  }
}

// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/builtins/base.tq;drc=c87310a1337d106d75500a8c9793a54ba4daa69a;l=1653
// Does "if (index1 + index2 > limit) goto IfOverflow" in an uintptr overflow
// friendly way where index1 and index2 are in [0, kMaxSafeInteger] range.
macro CheckIntegerIndexAdditionOverflow(
    index1: uintptr, index2: uintptr, limit: uintptr): void labels IfOverflow {
  if constexpr (Is64()) {
    dcheck(index1 <= kMaxSafeIntegerUint64);
    dcheck(index2 <= kMaxSafeIntegerUint64);
    // Given that both index1 and index2 are in a safe integer range the
    // addition can't overflow.
    if (index1 + index2 > limit) goto IfOverflow;                           // [!] addition overflows
  } else {
    // ...
  }
}
```

Thus, the bounds check overflow and we call into `Runtime_TypedArraySet()` which will convert the `Number`s back into `size_t` and call `TypedElementsAccessor::CopyElementsHandleImpl()` which looks like below:

```
  static Tagged<Object> CopyElementsHandleImpl(
      DirectHandle<JSAny> source, DirectHandle<JSObject> destination,
      size_t length, size_t offset) {
    Isolate* isolate = destination->GetIsolate();
    if (length == 0) return *isolate->factory()->undefined_value();

    DirectHandle<JSTypedArray> destination_ta = Cast<JSTypedArray>(destination);

    // All conversions from TypedArrays can be done without allocation.
    if (IsJSTypedArray(*source)) {
      CHECK(!destination_ta->WasDetached());
      bool out_of_bounds = false;
      CHECK_LE(offset + length,                                                   // [!] may overflow
               destination_ta->GetLengthOrOutOfBounds(out_of_bounds));
      CHECK(!out_of_bounds);
      auto source_ta = Cast<JSTypedArray>(source);
      ElementsKind source_kind = source_ta->GetElementsKind();
      bool source_is_bigint = IsBigIntTypedArrayElementsKind(source_kind);
      bool target_is_bigint = IsBigIntTypedArrayElementsKind(Kind);
      // If we have to copy more elements than we have in the source, we need to
      // do special handling and conversion; that happens in the slow case.
      if (source_is_bigint == target_is_bigint && !source_ta->WasDetached() &&
          length + offset <= source_ta->GetLength()) {
        CopyElementsFromTypedArray(*source_ta, *destination_ta, length, offset);  // [!] wildcopy w/ controlled address & content
        return *isolate->factory()->undefined_value();
      }
    } else if (IsJSArray(*source)) {
      // ...
    }
    // ...
    return CopyElementsHandleSlow(source, destination_ta, length, offset);
  }
```

Unfortunately, `JSArray` case is still guarded with a bounds check with `length` and the only exploitable case is when we take the `IsJSTypedArray()` path. With memory corruption primitive however we can corrupt the `map` of `JSArray` to change it into a `JSTypedArray` (and vice versa) and reach the wildcopy. `CHECK_LE(offset + length, destination_ta->GetLengthOrOutOfBounds(out_of_bounds))` may also be bypassed by overflowing `offset + length` irrespective of how `GetLengthOrOutOfBounds()` is implemented (e.g. [b/390201806](<https://issues.chromium.org/issues/390201806>)).

The attached repro creates a "polymorphic" object `u64s` which is initially created as a `BigUint64Array` but has `JSArray::length` overwritten to a large `HeapNumber`, which when added with `offset` overflows and results in a small in-bounds index. The main thread repeatedly triggers `TypedArrayPrototypeSet()` while a worker thread constantly flips back and forth the type of `u64s` between `BigUint64Array` and `JSArray` to trigger the vulnerable code path in the desired sequence with a fair amount of success rate.

Note that there is also an issue with `Number` being used to store sandbox-sensitive value after validating security properties (bound check, etc). This should never happen as `Number` can also be a `HeapNumber` allocated within the sandbox which a malicious thread can overwrite. This exact bug can also be triggered without the "polymorphic" object idea by overwriting `HeapNumber`s passed to `Runtime_TypedArraySet()` before it gets converted back through `TryNumberToSize()`.

### VERSION

V8: Tested on CF no-asan sandbox-testing d8 @ revision 98142 (commit [3ea3463](<https://chromium-review.googlesource.com/c/v8/v8/+/6175894>))

### REPRODUCTION CASE

Attached as `typedarray-set-wildcopy.js`, run with `./d8 --sandbox-testing`. This will likely not repro in ASAN builds.

The repro attempts a controlled write to address `0x424242424240` with the value `0x434343434343` as the first write attempt of the wildcopy.

### FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION

Type of crash: Sandbox violation

### CREDIT INFORMATION

Reporter credit: Seunghyun Lee (@0x10n) of CMU CyLab

* * *

This was discovered through variant analysis on a seemingly benign crash case from a WIP v8 sandbox fuzzer.  
Marking any potential VRP reward for this bug in advance to be processed for charity.


---

**#2 — ad...@google.com — Jan 21, 2025 06:23AM**

Adding standard labels for a V8 sandbox bypass and passing to V8 sheriff.


---

**#3 — ap...@google.com — Jan 31, 2025 01:22AM**

Project: v8/v8  
Branch: main  
Author: Marja Hölttä <[marja@chromium.org](<mailto:marja@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6216523](<https://chromium-review.googlesource.com/6216523>)

[sandbox] Convert dchecks so sbxchecks to avoid sandbox escapes

* * *

Expand for full commit details

```
[sandbox] Convert dchecks so sbxchecks to avoid sandbox escapes 
 
This fixes a sandbox escape related to array length processing. 
 
Bug: 391169061 
Change-Id: I01b989c326317b1ef65b61d4aae631b1bc349d61 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6216523 
Reviewed-by: Stephen Röttger <sroettger@google.com> 
Commit-Queue: Marja Hölttä <marja@chromium.org> 
Cr-Commit-Position: refs/heads/main@{#98418}
```

* * *

Files:

  * M `src/builtins/base.tq`

* * *

Hash: 5926c07a35614e391ecb6e63c4ee9f518eda3277  
Date: Thu Jan 30 15:19:11 2025

* * *


---

**#4 — se...@gmail.com — Feb 15, 2025 01:58AM**

Hi, is [https://crrev.com/c/6216523](<https://crrev.com/c/6216523>) the only fix for this issue? I see how the patch fixes my specific PoC implementation, but do not see how this would fix the broader `Number` issue mentioned in the report:

> Note that there is also an issue with `Number` being used to store sandbox-sensitive value after validating security properties (bound check, etc). This should never happen as `Number` can also be a `HeapNumber` allocated within the sandbox which a malicious thread can overwrite. This exact bug can also be triggered without the "polymorphic" object idea by overwriting `HeapNumber`s passed to `Runtime_TypedArraySet()` before it gets converted back through `TryNumberToSize()`.

The problem is that torque function `TypedArrayPrototypeSetArray()` is passing "sanitized" `Number` values `srcLengthNum` and `Convert<Number>(targetOffset)`, which could both be a `HeapNumber` allocated within the sandbox region, to `Runtime_TypedArraySet()` which assumes the values to be fully trusted and reads the numbers back from in-sandbox memory which would result in the same problem. More generally put, `Number` should be considered untrusted where in this case we're using it as a container to store trusted values.


---

**#5 — ma...@chromium.org — Feb 17, 2025 08:28PM**

Thanks for reminding us, it's possible that detail has escaped us. I'll have another look.


---

**#6 — ma...@chromium.org — Feb 17, 2025 11:17PM**

Created a spin-off for the general "passing HeapNumbers to runtime functions" problem: <https://issues.chromium.org/issues/397187119> ; closing this one again.


---

**#7 — sp...@google.com — Feb 20, 2025 09:55AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $20000.00 for this report.  
  
Rationale for this decision:  
V8 sandbox bypass demonstrating controlled write outside the V8 heap sandbox  
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#8 — am...@chromium.org — Feb 20, 2025 09:57AM**

Congratulations Seunghyun! Thank you for your efforts hunting in the V8 sandbox and reporting this issue to us-- nice work!


---

**#9 — ap...@google.com — Feb 20, 2025 09:37PM**

Project: v8/v8  
Branch: main  
Author: Marja Hölttä <[marja@chromium.org](<mailto:marja@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6269094](<https://chromium-review.googlesource.com/6269094>)

[sandbox] Add a regression test

* * *

Expand for full commit details

```
[sandbox] Add a regression test 
 
Bug: 391169061 
Change-Id: I2187388a3537d378ed44910ba4d1ff8ab1fc772c 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6269094 
Reviewed-by: Stephen Röttger <sroettger@google.com> 
Commit-Queue: Marja Hölttä <marja@chromium.org> 
Cr-Commit-Position: refs/heads/main@{#98829}
```

* * *

Files:

  * A `test/mjsunit/sandbox/regress-391169061.js`

* * *

Hash: e84df85a3808b1e3013687e956c7ed7a53bc469d  
Date: Fri Feb 14 13:43:51 2025

* * *


---

**#10 — ap...@google.com — Feb 25, 2025 10:41PM**

Project: v8/v8  
Branch: main  
Author: Stephen Roettger <[sroettger@google.com](<mailto:sroettger@google.com>)>  
Link: [https://chromium-review.googlesource.com/6285402](<https://chromium-review.googlesource.com/6285402>)

[sandbox] limit TryNumberToSize to kMaxSafeBufferSizeForSandbox

* * *

Expand for full commit details

```
[sandbox] limit TryNumberToSize to kMaxSafeBufferSizeForSandbox 
 
Bug: 391169061, 397187119 
Change-Id: I399e34589f726b7949045c3efba7695b8eae8e78 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6285402 
Reviewed-by: Leszek Swirski <leszeks@chromium.org> 
Commit-Queue: Leszek Swirski <leszeks@chromium.org> 
Cr-Commit-Position: refs/heads/main@{#98920}
```

* * *

Files:

  * M `src/numbers/conversions-inl.h`

* * *

Hash: ec48078aaeaef623314ed1dddc3a4b3967e8eb82  
Date: Fri Feb 21 12:04:58 2025

* * *


---

**#11 — ch...@google.com — May 27, 2025 09:47PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
