# V8 Sandbox Bypass: Interger Overflow in TypedArraySet leading to out-of-sandbox write

Issue URL: https://issues.chromium.org/issues/386565139
VRP-Reward: 5000
Date: Dec 29, 2024 11:29PM


# VULNERABILITY DETAILS

Runtime function `Runtime_TypedArraySet` converts `HeapNumber` to `size_t` at [1] and [2]. When `offset + length` overflows, `CHECK` at [3] in function `CopyElementsHandleImpl` can be bypassed. So `destination->DataPtr() + offset * element_size` can be outside the address space of the sandbox.

`Runtime_TypedArraySet` can be called from `TypedArray.prototype.set`. But I use `%TypedArraySet` in JavaScript for simplicity.

**NOTE** that `%TypedArraySet` can only accept 2 arguments according to the definition in `src/runtime/runtime.h`, which does not match its implementation in the source code. Therefore, I changed the number of arguments from 2 to 4. Plese see the diff in REPRODUCTION CASE.

```
RUNTIME_FUNCTION(Runtime_TypedArraySet) {
  HandleScope scope(isolate);
  DCHECK_EQ(4, args.length());
  DirectHandle<JSTypedArray> target = args.at<JSTypedArray>(0);
  DirectHandle<JSAny> source = args.at<JSAny>(1);
  size_t length;
  CHECK(TryNumberToSize(args[2], &length));                          // [1]
  size_t offset;
  CHECK(TryNumberToSize(args[3], &offset));                          // [2]
  ElementsAccessor* accessor = target->GetElementsAccessor();
  return accessor->CopyElements(source, target, length, offset);
}
```

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
      CHECK_LE(offset + length,                                     // [3] integer overflow
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
        CopyElementsFromTypedArray(*source_ta, *destination_ta, length, offset);
        return *isolate->factory()->undefined_value();
      }
    } else if (IsJSArray(*source)) {
    // [...]
  }
```

# VERSION

V8 commit: c39d21639f3dbbdacf39e9fd0ffe5624c54a3f15

# REPRODUCTION CASE

To reproduce, please patch the number of arguments of TypedArraySet first.

```
diff --git a/src/runtime/runtime.h b/src/runtime/runtime.h
index 23b7aeabaf0..40438d1a0a9 100644
--- a/src/runtime/runtime.h
+++ b/src/runtime/runtime.h
@@ -662,7 +662,7 @@ namespace internal {
   F(GrowableSharedArrayBufferByteLength, 1, 1) \
   F(TypedArrayCopyElements, 3, 1)              \
   F(TypedArrayGetBuffer, 1, 1)                 \
-  F(TypedArraySet, 2, 1)                       \
+  F(TypedArraySet, 4, 1)                       \
   F(TypedArraySortFast, 1, 1)
 
 #if V8_ENABLE_DRUMBRAKE
```

then run

```
./d8 --sandbox-testing --allow-natives-syntax ./typedarray_set.js
```

# FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION

Type of crash: V8 sandbox violation

# CREDIT INFORMATION

Reporter credit: Anonymous


---

**#2 — cl...@appspot.gserviceaccount.com — Dec 31, 2024 01:47AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=6743741586931712](<https://clusterfuzz.com/testcase?key=6743741586931712>).


---

**#3 — cl...@appspot.gserviceaccount.com — Dec 31, 2024 01:59AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5027554528264192](<https://clusterfuzz.com/testcase?key=5027554528264192>).


---

**#4 — am...@chromium.org — Dec 31, 2024 02:33AM**

Thank you for the report. I wasn't able to get this to reproduce. This looks a bit similar to [issue 385775375](<https://issues.chromium.org/issues/385775375>), but without being able to repro it's difficult to confirm. Assigning to the same folks for visibility.


---

**#5 — iw...@gmail.com — Dec 31, 2024 09:59PM**

To reproduce, please first apply the patch from the REPRODUCTION CASE and then recompile d8. I think this patch is reasonable because `Runtime_TypedArraySet` requires 4 arguments instead of 2.


---

**#6 — sa...@google.com — Jan 3, 2025 07:28PM**

Thanks for the report! It would be important to get a reproducer that works without a patch, but more importantly that doesn't rely on calling a runtime function directly. In general, runtime functions are not robust against arbitrary inputs (because they are not normally exposed to such) and so it is expected that you can cause memory corruption by calling them directly. Would it be possible to provide a reproducer that works with just `TypedArray.prototype.set` (which is exposed to untrusted inputs) instead?


---

**#7 — sa...@google.com — Jan 3, 2025 07:28PM**

Cc Marja as an owner of ArrayBuffer-related code.


---

**#8 — iw...@gmail.com — Jan 4, 2025 01:13AM**

`typedarray_set_without_runtime.js` is a PoC which only requires `--sandbox-testing --expose-gc`. It's not 100% stable because a worker thread is used to modify the v8 heap concurrently.


---

**#9 — cl...@appspot.gserviceaccount.com — Jan 6, 2025 07:10PM**

Detailed Report: [https://clusterfuzz.com/testcase?key=5879502429159424](<https://clusterfuzz.com/testcase?key=5879502429159424>)  
  
Fuzzer: None  
Job Type: linux_d8_sandbox_testing  
Platform Id: linux  
  
Crash Type: V8 sandbox violation  
Crash Address:   
Crash State:  
NULL  
Sanitizer: address (ASAN)  
  
Crash Revision: [https://clusterfuzz.com/revisions?job=linux_d8_sandbox_testing&revision=97948](<https://clusterfuzz.com/revisions?job=linux_d8_sandbox_testing&revision=97948>)  
  
Reproducer Testcase: [https://clusterfuzz.com/download?testcase_id=5879502429159424](<https://clusterfuzz.com/download?testcase_id=5879502429159424>)  
  
To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.   
  
If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.  
  
If you have any feedback on reproducing test cases, let us know at [https://forms.gle/Yh3qCYFveHj6E5jz5](<https://forms.gle/Yh3qCYFveHj6E5jz5>) so we can improve.


---

**#10 — sa...@google.com — Jan 6, 2025 07:11PM**

Excellent, thank you! This makes it much easier. So I assume there's also some double-fetch style problem here, or why is concurrent heap corruption necessary? Marja, could you also take a look at this issue? Thanks!


---

**#11 — iw...@gmail.com — Jan 6, 2025 07:56PM**

> So I assume there's also some double-fetch style problem here, or why is concurrent heap corruption necessary?

Yes. `offset` and `length` are validated in builtin `TypedArrayPrototypeSet`. So `offset` and `length` need to be modified after these validations and before `CHECK(TryNumberToSize(args[2], &length));`.


---

**#12 — sa...@google.com — Jan 6, 2025 08:28PM**

Right ok, so maybe we also want to fix this double-fetch issue and treat the CHECK as a defense-in-depth measure (so we'd fix the integer overflow in the CHECK but also avoid reloading the offset and length from the heap).


---

**#13 — sr...@google.com — Mar 4, 2025 11:53PM**

@reporter, we now limit TryNumberToSize to return at most kMaxSafeBufferSizeForSandbox.

Can you confirm that this is fixed? Thanks!


---

**#14 — iw...@gmail.com — Mar 5, 2025 09:46AM**

This v8 sandbox bypass is fixed by [[sandbox] limit TryNumberToSize to kMaxSafeBufferSizeForSandbox](<https://chromium-review.googlesource.com/c/v8/v8/+/6285402>).


---

**#15 — sr...@google.com — Mar 5, 2025 05:06PM**

Thanks for confirming!


---

**#16 — sp...@google.com — Mar 14, 2025 07:55AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $5000.00 for this report.  
  
Rationale for this decision:  
report of V8 sandbox bypass demonstrating memory corruption outside the V8 sandbox  
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#17 — am...@chromium.org — Mar 14, 2025 08:04AM**

Congratulations! Thank you for your efforts hunting in the V8 sandbox and reporting this issue to us -- nice work!


---

**#18 — ch...@google.com — Jun 12, 2025 09:42PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
