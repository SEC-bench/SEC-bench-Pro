# V8 sandbox violation in v8

Issue URL: https://issues.chromium.org/issues/401732698
VRP-Reward: 5000
Date: Mar 9, 2025 08:11PM


## VULNERABILITY DETAILS

### CRASH LOG

```
$ /path/to/v8/v8/out/fuzzbuild-sandbox/d8  --sandbox-fuzzing ./poc.js 
Sandbox testing mode is enabled. Only sandbox violations will be reported, all other crashes will be ignored.
# Ignoring debug check failure in .....
# Ignoring debug check failure in .....
# Ignoring debug check failure in .....

## V8 sandbox violation detected!

Received signal 11 SEGV_MAPERR 08464d000848

==== C stack trace ===============================

/path/to/v8/v8/out/fuzzbuild-sandbox/d8(+0xaabe66)[0x55b346715e66]
/lib/x86_64-linux-gnu/libc.so.6(+0x42520)[0x7f8bbee42520]
/path/to/v8/v8/out/fuzzbuild-sandbox/d8(+0x2157e9b)[0x55b347dc1e9b]
/path/to/v8/v8/out/fuzzbuild-sandbox/d8(+0x21523d7)[0x55b347dbc3d7]
/path/to/v8/v8/out/fuzzbuild-sandbox/d8(+0x2146b1a)[0x55b347db0b1a]
/path/to/v8/v8/out/fuzzbuild-sandbox/d8(+0x21444ed)[0x55b347dae4ed]
/path/to/v8/v8/out/fuzzbuild-sandbox/d8(+0x2140ed0)[0x55b347daaed0]
/path/to/v8/v8/out/fuzzbuild-sandbox/d8(+0x2140dae)[0x55b347daadae]
/path/to/v8/v8/out/fuzzbuild-sandbox/d8(+0x260dfe9)[0x55b348277fe9]
/path/to/v8/v8/out/fuzzbuild-sandbox/d8(+0x260d742)[0x55b348277742]
/path/to/v8/v8/out/fuzzbuild-sandbox/d8(+0x55b84bd)[0x55b34b2224bd]
[end of stack trace]
[1]    3821081 segmentation fault  /path/to/v8/v8/out/fuzzbuild-sandbox/d8 --sandbox-fuzzing ./poc.js
```

### REPRODUCTION CASE

  * build

```
# Mar 8 2025 
git checkout fec6c4c97ac26259c4633142dd6423de1592fbf0
gn gen ./out/sbx --args='v8_enable_partition_alloc=false treat_warnings_as_errors=false is_debug=false dcheck_always_on=true v8_static_library=true v8_enable_slow_dchecks=true v8_enable_v8_checks=true v8_enable_verify_heap=true v8_enable_verify_csa=true v8_enable_verify_predictable=true target_cpu="x64" v8_enable_sandbox=true v8_enable_memory_corruption_api=true'
ninja -C ./out/sbx d8
```

  * trigger

```
./out/sbx/d8  --sandbox-fuzzing ./poc.js 
```

## FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION

Type of crash: tab

## CREDIT INFORMATION

Reporter credit: Zhenghang Xiao (@Kipreyyy) and Nan Wang (@eternalsakura13)


---

**#2 — cl...@appspot.gserviceaccount.com — Mar 10, 2025 02:21AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5460286844633088](<https://clusterfuzz.com/testcase?key=5460286844633088>).


---

**#3 — ph...@chromium.org — Mar 10, 2025 02:24AM**

Setting provisional found-in and severity for V8 bugs. Assigning to V8 sheriff.


---

**#4 — ki...@gmail.com — Mar 10, 2025 02:33AM**

## RCA

Crash Backtrace

```
#0  0x000056531d4afc2d in v8::internal::TaggedMember<v8::internal::Smi, v8::internal::V8HeapCompressionSchemeImpl<v8::internal::MainCage> >::tagged_to_full (tagged_value=<optimized out>) at ../../src/objects/tagged-field-inl.h:22
#1  v8::internal::TaggedMember<v8::internal::Smi, v8::internal::V8HeapCompressionSchemeImpl<v8::internal::MainCage> >::load (this=<optimized out>) at ../../src/objects/tagged-field-inl.h:45
#2  v8::internal::detail::ArrayHeaderBase<v8::internal::HeapObjectLayout, true>::length (this=<optimized out>) at ../../src/objects/fixed-array-inl.h:62
#3  v8::internal::detail::ArrayHeaderBase<v8::internal::HeapObjectLayout, true>::capacity (this=<optimized out>) at ../../src/objects/fixed-array-inl.h:83
#4  v8::internal::TaggedArrayBase<v8::internal::FixedArray, v8::internal::TaggedArrayShape, v8::internal::HeapObjectLayout>::IsInBounds (index=0, this=<optimized out>) at ../../src/objects/fixed-array-inl.h:104
#5  v8::internal::TaggedArrayBase<v8::internal::FixedArray, v8::internal::TaggedArrayShape, v8::internal::HeapObjectLayout>::get (index=0, this=<optimized out>) at ../../src/objects/fixed-array-inl.h:116
#6  v8::internal::HashTableBase::NumberOfElements (this=<optimized out>) at ../../src/objects/hash-table-inl.h:53
#7  v8::internal::(anonymous namespace)::CollectKeysFromDictionary<v8::internal::NameDictionary> (dictionary=..., keys=keys@entry=0x7ffc10d14f98) at ./../../src/objects/keys.cc:947
#8  0x000056531d4aa3d7 in v8::internal::KeyAccumulator::CollectOwnPropertyNames (this=this@entry=0x7ffc10d14f98, receiver=receiver@entry=..., object=...) at ./../../src/objects/keys.cc:1077
#9  0x000056531d49eb1a in v8::internal::KeyAccumulator::CollectOwnKeys (this=this@entry=0x7ffc10d14f98, receiver=receiver@entry=..., object=...) at ./../../src/objects/keys.cc:1172
#10 0x000056531d49c4ed in v8::internal::KeyAccumulator::CollectKeys (this=this@entry=0x7ffc10d14f98, receiver=..., object=...) at ./../../src/objects/keys.cc:280
#11 0x000056531d498ed0 in v8::internal::FastKeyAccumulator::GetKeysSlow (this=0x7ffc10d15008, keys_conversion=v8::internal::GetKeysConversion::kConvertToString) at ./../../src/objects/keys.cc:605
#12 v8::internal::FastKeyAccumulator::GetKeys (this=this@entry=0x7ffc10d15008, keys_conversion=keys_conversion@entry=v8::internal::GetKeysConversion::kConvertToString) at ./../../src/objects/keys.cc:468
#13 0x000056531d498dae in v8::internal::KeyAccumulator::GetKeys (isolate=<optimized out>, object=..., mode=v8::internal::KeyCollectionMode::kOwnOnly, filter=v8::internal::SKIP_SYMBOLS, keys_conversion=v8::internal::GetKeysConversion::kConvertToString, is_for_in=false, skip_indices=<optimized out>) at ./../../src/objects/keys.cc:103
#14 0x000056531d965fe9 in v8::internal::__RT_impl_Runtime_ObjectGetOwnPropertyNamesTryFast (args=..., isolate=isolate@entry=0x565323f81000) at ./../../src/runtime/runtime-object.cc:149
#15 0x000056531d965742 in v8::internal::Runtime_ObjectGetOwnPropertyNamesTryFast (args_length=<optimized out>, args_object=0x7ffc10d15158, isolate=0x565323f81000) at ./../../src/runtime/runtime-object.cc:129
#16 0x00005653209104bd in Builtins_CEntry_Return1_ArgvOnStack_NoBuiltinExit ()
#17 0x000056532083f6d8 in Builtins_ObjectGetOwnPropertyNames ()
#18 0x00005653204d6d72 in Builtins_InterpreterEntryTrampoline ()
```

In stack backtracking #2, v8 attempts to read length_[1] of type SMI on the v8 heap, however, if the field is corrupted to a non-SMI object, the aggressive compilation optimizations in the downward call to the tagged_to_full function [2] cause the compiler to produce undefined behavior to the point of jumping to an incorrect branch when that condition is not met.

```
template <class S>
int detail::ArrayHeaderBase<S, true>::length() const {
  return length_.load().value(); // <--- [1]
}

// static
template <typename T, typename CompressionScheme>
Address TaggedMember<T, CompressionScheme>::tagged_to_full(
    Tagged_t tagged_value) {
#ifdef V8_COMPRESS_POINTERS
  if constexpr (std::is_same_v<Smi, T>) {
    V8_ASSUME(HAS_SMI_TAG(tagged_value));  // <------------- [2]
    return CompressionScheme::DecompressTaggedSigned(tagged_value);
  } else {
    return CompressionScheme::DecompressTagged(CompressionScheme::base(),
                                               tagged_value);
  }
#else
  return tagged_value;
#endif
}
```

Below is an example of decompiling the CollectKeysFromDictionary function using IDA pro. You can see that the compiled result tries to dereference the `DirectHandle<Dictionary>` structure three times in a row, to the point of directly dereferencing 8 bytes of data located on the v8 heap.

```
char __fastcall v8::internal::`anonymous namespace'::CollectKeysFromDictionary<v8::internal::NameDictionary>(
        v8::internal::DirectHandle_27 dictionary,
        v8::internal::KeyAccumulator *keys)
{
  ...

  v77 = keys;
  _sanitizer_cov_trace_pc_guard(&guard);
  v81.location_ = dictionary.handle_.location_;
  isolate = keys->isolate_;
  ...
  if ( !v82.location_ )
  {
    _sanitizer_cov_trace_pc_guard(&dword_6166178);
    v6 = *(_QWORD *)&_done; <--- [a]
    v7 = *(_DWORD *)(*(_QWORD *)&_done + 3LL);
    if ( (v7 & 1) == 0 )
      goto LABEL_9;
LABEL_35:
    _sanitizer_cov_trace_pc_guard(&dword_6166184);
    V8_Dcheck(
      "../../src/objects/tagged-field-inl.h",
      0x16u,
      "((static_cast<i::Tagged_t>(tagged_value) & ::i::kSmiTagMask) == ::i::kSmiTag)");
    goto LABEL_36; 
  }
  ...
  v6 = (v8::internal::Address)v82.location_;
  if ( (*((_BYTE *)&v8::internal::v8_flags + 1752) & 1) == 0 )
  {
LABEL_36:
    _sanitizer_cov_trace_pc_guard(&dword_61661BC);
    v10 = *(_QWORD *)v6;  <---- [b]
    v11 = *(_DWORD *)(v10 + 3); <--- [c]
    if ( (v11 & 1) != 0 )
      goto LABEL_37;
LABEL_23:
    _sanitizer_cov_trace_pc_guard(&dword_61661CC);
    if ( v11 < 5 )
      goto LABEL_38;
LABEL_24:
    _sanitizer_cov_trace_pc_guard(&dword_61661D4);
    v12 = (v8::internal::Address **)*(unsigned int *)(v10 + 15);
    if ( v8::internal::MainCage::base_ )
    {
LABEL_39:
      _sanitizer_cov_trace_pc_guard(&dword_61661DC);
      V8_Dcheck("../../src/common/ptr-compr-inl.h", 0x4Du, "(base & kPtrComprCageBaseMask) == base");
      goto LABEL_40;
    }
    goto LABEL_25;
  }
  ...
  _sanitizer_cov_trace_pc_guard(&dword_6166370);
  if ( v8::internal::IsSymbol((v8::internal::Tagged)v69) )
    goto LABEL_194;
LABEL_199:
  _sanitizer_cov_trace_pc_guard(&dword_6166378);
  v49 = v79;
  if ( v47 != v62 )
    goto LABEL_200;
LABEL_214:
  _sanitizer_cov_trace_pc_guard(&dword_6166388);
  return 1;
}
```


---

**#5 — ki...@gmail.com — Mar 10, 2025 02:43AM**

Uploaded the disassembly and decompilation results of the CollectKeysFromDictionary function for reference if needed.


---

**#6 — ch...@google.com — Mar 10, 2025 09:34PM**

Setting milestone because of s0/s1 severity.


---

**#7 — ch...@google.com — Mar 10, 2025 09:34PM**

Setting Priority to P1 to match Severity s1. If this is incorrect, please reset the priority. The automation bot account won't make this change again.


---

**#8 — is...@chromium.org — Mar 11, 2025 02:11AM**

Thank you for the report! Very nice catch!


---

**#9 — ki...@gmail.com — Mar 17, 2025 01:42PM**

hello，any update？


---

**#10 — ch...@google.com — Mar 25, 2025 09:33PM**

ishell: Uh oh! This issue still open and hasn't been updated in the last 14 days. This is a serious vulnerability, and we want to ensure that there's progress. Could you please leave an update with the current status and any potential blockers?

If you're not the right owner for this issue, could you please remove yourself as soon as possible or help us find the right one?

If the issue is fixed or you can't reproduce it, please close the bug. If you've started working on a fix, please set the status to Started.

Thanks for your time! To disable nags, add Disable-Nags (case sensitive) to the Chromium Labels custom field.


---

**#11 — ch...@google.com — Mar 26, 2025 09:36PM**

ishell: Uh oh! This issue still open and hasn't been updated in the last 15 days. This is a serious vulnerability, and we want to ensure that there's progress. Could you please leave an update with the current status and any potential blockers?

If you're not the right owner for this issue, could you please remove yourself as soon as possible or help us find the right one?

If the issue is fixed or you can't reproduce it, please close the bug. If you've started working on a fix, please set the status to Started.

Thanks for your time! To disable nags, add Disable-Nags (case sensitive) to the Chromium Labels custom field.


---

**#12 — ch...@google.com — Mar 27, 2025 09:37PM**

ishell: Uh oh! This issue still open and hasn't been updated in the last 16 days. This is a serious vulnerability, and we want to ensure that there's progress. Could you please leave an update with the current status and any potential blockers?

If you're not the right owner for this issue, could you please remove yourself as soon as possible or help us find the right one?

If the issue is fixed or you can't reproduce it, please close the bug. If you've started working on a fix, please set the status to Started.

Thanks for your time! To disable nags, add Disable-Nags (case sensitive) to the Chromium Labels custom field.


---

**#13 — is...@chromium.org — Mar 27, 2025 11:33PM**

We don't think this is exploitable in practice, but in order to play safe we'll change relevant `V8_ASSUME`s to `DCHECK`s ([https://crrev.com/c/6402513](<https://crrev.com/c/6402513>)).


---

**#14 — dx...@google.com — Mar 28, 2025 12:50AM**

Project: v8/v8  
Branch: main  
Author: Igor Sheludko [ishell@chromium.org](<mailto:ishell@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6402513](<https://chromium-review.googlesource.com/6402513>)

[ptr-compr] Replace V8_ASSUME with DCHECK

* * *

Expand for full commit details

```
     
    Conditions for these V8_ASSUME depend on the values read from the 
    sandbox. Play safe and don't let them turn into undefined behaviour. 
     
    Fixed: 401732698 
    Change-Id: Iacf3662f6ee911504c32c78267c2b945194abc3f 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6402513 
    Commit-Queue: Stephen Röttger <sroettger@google.com> 
    Auto-Submit: Igor Sheludko <ishell@chromium.org> 
    Commit-Queue: Igor Sheludko <ishell@chromium.org> 
    Reviewed-by: Stephen Röttger <sroettger@google.com> 
    Cr-Commit-Position: refs/heads/main@{#99521}
```

* * *

Files:

  * M `src/common/ptr-compr-inl.h`
  * M `src/common/ptr-compr.h`
  * M `src/objects/tagged-field-inl.h`

* * *

Hash: b887b9161acac9d1b13dee460d045e8a55d93b27  
Date: Thu Mar 27 14:30:32 2025

* * *


---

**#15 — sp...@google.com — Apr 3, 2025 09:55AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $5000.00 for this report.  
  
Rationale for this decision:  
report of V8 sandbox bypass demonstrating memory corruption outside the V8 heap sandbox  
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#16 — am...@chromium.org — Apr 3, 2025 10:12AM**

Congratulations Kiprey and Sakura! Thank you for your efforts in reporting this V8 sandbox bypass to us -- nice work!


---

**#17 — ch...@google.com — Jul 4, 2025 09:38PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
