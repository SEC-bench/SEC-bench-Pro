# V8 Sandbox Bypass: AAR/W due to length-tracking TypedArray length double fetch

Issue URL: https://issues.chromium.org/issues/390201806
VRP-Reward: 20000
Date: Jan 16, 2025 02:36PM


### VULNERABILITY DETAILS

#### Summary

V8 sandbox bypass, arbitrary address read/write by exploiting in-sandbox double fetch race condition when calculating length-tracked TypedArray length. This results in integer overflow and a subsequent out-of-bounds memory read/write within the full 64bit address space.

#### Details

Many prior v8 sandbox bypass reports, notably [b/349529650](<https://issues.chromium.org/issues/349529650>) and [b/352446085](<https://issues.chromium.org/issues/352446085>) in Wasm, demonstrated the issue of TOCTOU race condition within the v8 sandbox region where double fetching from the v8 sandbox may result in critical invariants to be broken (umbrella bug @ [b/376071292](<https://issues.chromium.org/issues/376071292>)). Length-tracked `TypedArray`s are also subject to this issue when computing its total length:

```
// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/objects/js-array-buffer.cc;drc=1d7b6d2d2d1c3fb18739405b6fd58ce801844f57;l=451
size_t JSTypedArray::GetVariableLengthOrOutOfBounds(bool& out_of_bounds) const {
  DCHECK(!WasDetached());
  if (is_length_tracking()) {
    if (is_backed_by_rab()) {
      // [!] omitted, but also vulnerable
    }
    if (byte_offset() >                                                         // [!] fetch #1
        buffer()->GetBackingStore()->byte_length(std::memory_order_seq_cst)) {
      out_of_bounds = true;
      return 0;
    }
    return (buffer()->GetBackingStore()->byte_length(
                std::memory_order_seq_cst) -
            byte_offset()) /                                                    // [!] fetch #2
           element_size();
  }
  // ...
}
```

This results in subtraction to overflow and return a large value enough to index the whole 64bit address space. One example that uses this length for bounds check is `%TypedArray%.prototype.copyWithin()`:

```
// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/builtins/builtins-typed-array.cc;drc=ff2449f5f5baaf56a34babaec640e9519a530623;l=47
BUILTIN(TypedArrayPrototypeCopyWithin) {
  // ...
  int64_t len = array->GetLength();      // [!] uses GetVariableLengthOrOutOfBounds() 
  int64_t to = 0;
  int64_t from = 0;
  int64_t final = len;

  if (V8_LIKELY(args.length() > 1)) {
    DirectHandle<Object> num;
    ASSIGN_RETURN_FAILURE_ON_EXCEPTION(
        isolate, num, Object::ToInteger(isolate, args.at<Object>(1)));
    to = CapRelativeIndex(num, 0, len);

    if (args.length() > 2) {
      ASSIGN_RETURN_FAILURE_ON_EXCEPTION(
          isolate, num, Object::ToInteger(isolate, args.at<Object>(2)));
      from = CapRelativeIndex(num, 0, len);

      DirectHandle<Object> end = args.atOrUndefined(isolate, 3);
      if (!IsUndefined(*end, isolate)) {
        ASSIGN_RETURN_FAILURE_ON_EXCEPTION(isolate, num,
                                           Object::ToInteger(isolate, end));
        final = CapRelativeIndex(num, 0, len);
      }
    }
  }

  int64_t count = std::min<int64_t>(final - from, len - to);
  if (count <= 0) return *array;
  // ...
  size_t element_size = array->element_size();
  to = to * element_size;
  from = from * element_size;
  count = count * element_size;

  uint8_t* data = static_cast<uint8_t*>(array->DataPtr());
  if (array->buffer()->is_shared()) {
    base::Relaxed_Memmove(reinterpret_cast<base::Atomic8*>(data + to),
                          reinterpret_cast<base::Atomic8*>(data + from), count);
  } else {
    std::memmove(data + to, data + from, count);
  }

  return *array;
}
```

We easily see that this results in arbitrary read/write across the whole 64bit address space. Thus, an attacker can spawn a malicious worker thread that constantly flips the offset between a normal value and an overflowing value to trigger the bug and obtain AAR/W.

One small quirk is that the index clamped through `CapRelativeIndex()` is a `double`, meaning that some precision loss might occur when using large indices to write to a lower address than the backing store. This does not limit the attacker's ability to read and write from arbitrary addresses since the attacker can simply modify backing store address to compensate the precision loss (this is however not implemented in the PoC).

### VERSION

V8: Tested on CF asan/no-asan sandbox-testing d8 @ revision 98142 (commit [3ea3463](<https://chromium-review.googlesource.com/c/v8/v8/+/6175894>))

### REPRODUCTION CASE

Attached as `typedarray-length-double-fetch.js`, run with `./d8 --sandbox-testing`.

The repro attempts a controlled write to address `0x424242424240` with the value `0x434343434343`. On ASAN builds we observe the precision loss which will result in writing to `0x424242424000` instead, which can easily be detected and compensated if needed.

### FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION

Type of crash: Sandbox violation

### CREDIT INFORMATION

Reporter credit: Seunghyun Lee (@0x10n) of CMU CyLab

* * *

This was discovered during a test run of a WIP v8 sandbox fuzzer.


---

**#2 — se...@gmail.com — Jan 16, 2025 02:36PM**

@amyressler: Marking any potential VRP reward for this bug in advance to be processed for charity.


---

**#3 — cl...@appspot.gserviceaccount.com — Jan 16, 2025 03:15PM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=6523193070125056](<https://clusterfuzz.com/testcase?key=6523193070125056>).


---

**#4 — ti...@chromium.org — Jan 16, 2025 03:29PM**

(primary shepherd)

Thanks for the report! I was able to reproduce locally. Assigning to the current v8 security shepherd.


---

**#5 — sr...@google.com — Jan 16, 2025 07:25PM**

marja@ could you take a look at this?


---

**#6 — pe...@google.com — Jan 17, 2025 12:39AM**

Setting milestone because of s2 severity.


---

**#7 — pe...@google.com — Jan 17, 2025 12:40AM**

Setting Priority to P1 to match Severity s2. If this is incorrect, please reset the priority. The automation bot account won't make this change again.


---

**#8 — se...@gmail.com — Jan 17, 2025 03:16AM**

FYI this is an independent issue from `JSTypedArray` sandbox compatibility work in progress at [b/40070746](<https://issues.chromium.org/issues/40070746>). The bug still exists regardless of how the length is represented (byte length vs element count) as the overflowing computation with double fetched value is the problem demonstrated here. Recent commits attempting to fix [b/40070746](<https://issues.chromium.org/issues/40070746>) also show the same double fetch pattern.


---

**#9 — ma...@chromium.org — Jan 20, 2025 04:36PM**

I'll put this on my list.


---

**#10 — pe...@google.com — Feb 5, 2025 12:36AM**

marja: Uh oh! This issue still open and hasn't been updated in the last 14 days. This is a serious vulnerability, and we want to ensure that there's progress. Could you please leave an update with the current status and any potential blockers?

If you're not the right owner for this issue, could you please remove yourself as soon as possible or help us find the right one?

If the issue is fixed or you can't reproduce it, please close the bug. If you've started working on a fix, please set the status to Started.

Thanks for your time! To disable nags, add Disable-Nags (case sensitive) to the Chromium Labels custom field.


---

**#11 — ap...@google.com — Feb 21, 2025 07:15PM**

Project: v8/v8  
Branch: main  
Author: Marja Hölttä <[marja@chromium.org](<mailto:marja@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6289045](<https://chromium-review.googlesource.com/6289045>)

[typed arrays] Implement GetVariableLengthOrOutOfBounds in terms of GetVariableByteLengthOrOutOfBounds

* * *

Expand for full commit details

```
[typed arrays] Implement GetVariableLengthOrOutOfBounds in terms of GetVariableByteLengthOrOutOfBounds 
 
This gets rid of one usage of TypedArray length in code where 
performance won't be significantly affected by the extra division. 
 
Bug: 388844115, 390201806 
Fixed: 390201806 
Change-Id: I6829f3119cac1e91d69133af6f849599405d7803 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6289045 
Commit-Queue: Marja Hölttä <marja@chromium.org> 
Reviewed-by: Stephen Röttger <sroettger@google.com> 
Cr-Commit-Position: refs/heads/main@{#98854}
```

* * *

Files:

  * M `src/objects/js-array-buffer.cc`
  * M `src/objects/js-array-buffer.h`

* * *

Hash: de42e588f4f7bafc773e630f937407924528cb36  
Date: Fri Feb 21 10:33:22 2025

* * *


---

**#12 — sp...@google.com — Feb 27, 2025 09:55AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $20000.00 for this report.  
  
Rationale for this decision:  
V8 sandbox bypass report demonstrating controlled write outside the V8 sandbox  
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#13 — am...@chromium.org — Feb 27, 2025 10:11AM**

Congratulations on yet another one, Seunghyun! Thank you for your continued efforts hunting on the V8 sandbox -- nice work!


---

**#14 — ch...@google.com — May 31, 2025 09:38PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
