# V8 Sandbox Bypass: Control flow hijack via Torque function type corruption

Issue URL: https://issues.chromium.org/issues/390639820
VRP-Reward: 20000
Date: Jan 18, 2025 01:17PM


### VULNERABILITY DETAILS

#### Summary

V8 sandbox bypass, control flow hijack (arbitrary call) by corrupting in-sandbox Torque function types. These are conceptually equivalent to `smi`s representing its index within the builtins table used in a completely unguarded manner, which results in arbitrary builtins call as well as fully arbitrary call when using an out-of-bounds index to dereference function pointers within a controlled heap spray region.

#### Details

`Array.prototype.sort()` uses `SortState` to represent the current sorting state. Interestingly, it includes several function types used for comparison, load, store, delete and accessor check:

```
// https://source.chromium.org/chromium/chromium/src/+/main:v8/third_party/v8/builtins/array-sort.tq;drc=c87310a1337d106d75500a8c9793a54ba4daa69a;l=17
class SortState extends HeapObject {
  // ...
  // Function pointer to the comparison function. This can either be a builtin
  // that calls the user-provided comparison function or "SortDefault", which
  // uses ToString and a lexicographical compare.
  sortComparePtr: CompareBuiltinFn;

  // The following four function pointer represent an Accessor/Path.
  // These are used to Load/Store/Delete elements and to check whether
  // to bail to the baseline GenericElementsAccessor.
  loadFn: LoadFn;
  storeFn: StoreFn;
  deleteFn: DeleteFn;
  canUseSameAccessorFn: CanUseSameAccessorFn;
  // ...
}

// https://source.chromium.org/chromium/chromium/src/+/main:v8/third_party/v8/builtins/array-sort.tq;drc=c87310a1337d106d75500a8c9793a54ba4daa69a;l=235
type LoadFn = builtin(Context, SortState, Smi) => (JSAny|TheHole);
type StoreFn = builtin(Context, SortState, Smi, JSAny) => Smi;
type DeleteFn = builtin(Context, SortState, Smi) => Smi;
type CanUseSameAccessorFn = builtin(Context, JSReceiver, Map, Number) =>
    Boolean;
type CompareBuiltinFn = builtin(Context, JSAny, JSAny, JSAny) => Number;
```

This is in fact represented as an `smi`:

```
// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/builtins/base.tq;drc=c87310a1337d106d75500a8c9793a54ba4daa69a;l=294
type BuiltinPtr extends Smi generates 'TNode<BuiltinPtr>';
```

Torque code that fetches and calls such function is transpiled into CSA code using `{Load,Store}Reference<BuiltinPtr>`, which will emit a memory indirect call dereferencing the target builtin function pointer using the given `smi` index. Below is an example of such call in `Builtins_ArrayTimSort()`:

```
0x55555ba77602 <Builtins_ArrayTimSort+1026>    mov    r8d, dword ptr [rdi + r8*4 + 7]
0x55555ba77607 <Builtins_ArrayTimSort+1031>    add    r8, r14
0x55555ba7760a <Builtins_ArrayTimSort+1034>    mov    r11d, dword ptr [rax + 0x13]      ; rax = SortArray object, r11 = sortComparePtr
0x55555ba7760e <Builtins_ArrayTimSort+1038>    mov    r12d, dword ptr [rax + 0xf]
0x55555ba77612 <Builtins_ArrayTimSort+1042>    add    r12, r14
0x55555ba77615 <Builtins_ArrayTimSort+1045>    mov    qword ptr [rbp - 0x10], rcx
0x55555ba77619 <Builtins_ArrayTimSort+1049>    mov    qword ptr [rbp - 0x30], rdi
0x55555ba7761d <Builtins_ArrayTimSort+1053>    mov    qword ptr [rbp - 0x48], r9
0x55555ba77621 <Builtins_ArrayTimSort+1057>    mov    rax, r12
0x55555ba77624 <Builtins_ArrayTimSort+1060>    mov    rbx, r9
0x55555ba77627 <Builtins_ArrayTimSort+1063>    mov    rcx, r8
0x55555ba7762a <Builtins_ArrayTimSort+1066>    call   qword ptr [r13 + r11*4 + 0x51e8]  ; r13+0x51e8 = builtins table
```

We see that there are no checks whatsoever on what the index can be. This results in arbitrary (incompatible) builtin function calls, and even a complete control flow hijack by calling out-of-bounds index pointing to attacker-controlled heap spray.

The attached exploit works as follows:

  1. Spray `TARGET` address to call on the native heap using Wasm
  2. Create an object with a getter defined on index 0 in which we: 
     1. Search the sandbox region for the constructed `SortState` object
     2. Corrupt `sortComparePtr` index to point to heap spray
  3. Call `Array.prototype.sort()` on the object 
     1. Index 0 getter called, `sortComparePtr` corrupted
     2. Comparator called to compare values at index 0 and 1, resulting in control flow hijack to `TARGET`

> The bypass does not fundamentally require Wasm. In the repro, Wasm is used simply as a means of heap spraying on the native heap - any other sprayable allocations on the native heap suffices.

### VERSION

V8: Tested on CF **no-asan** sandbox-testing d8 @ revision 98142 (commit [3ea3463](<https://chromium-review.googlesource.com/c/v8/v8/+/6175894>)) & custom **no-asan** Chrome build with sandbox testing enabled

### REPRODUCTION CASE

Attached as `array-sort-sortstate-corruption.js`, run with `./d8 --sandbox-testing` **on a no-asan build.**

The repro attempts a control flow hijack to address `0x42424242c0d3`.

> This bypass grants equivalent ~ stronger primitive than arbitrary writes, as this allows an attacker to immediately execute arbitrary code by e.g. running `Array.prototype.sort()` within a normal Wasm function as an imported function with stack sprayed with nop-sledded ropchain, triggered by calling into pivot gadget `add rsp, X; ...; ret`.

#### Triaging

For ClusterFuzz triage, I recommend the `linux_d8_sandbox_testing` job type.

### FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION

Type of crash: Sandbox violation

### CREDIT INFORMATION

Reporter credit: Seunghyun Lee (@0x10n) of CMU CyLab

* * *

This was discovered during a test run of a WIP v8 sandbox fuzzer.  
Marking any potential VRP reward for this bug in advance to be processed for charity.


---

**#2 — se...@gmail.com — Jan 18, 2025 01:24PM**

Also mentioned in [b/384549659#comment13](<https://issues.chromium.org/issues/384549659#comment13>), but repeating here for clarity:

As also demonstrated in [b/384549659](<https://issues.chromium.org/issues/384549659>) and [b/384553540](<https://issues.chromium.org/issues/384553540>), in this report I demonstrate again a fully controlled control flow hijack. I have not explicitly demonstrated a _Controlled write outside the V8 sandbox_ as per the v8 sandbox bypass VRP criteria since the demonstrated primitive is already stronger, but if this is a strict requirement please let me know :)

* * *

Also note that other Torque code that stores `smi` indexed function types within the sandbox may also be vulnerable to the same bypass.


---

**#3 — ad...@google.com — Jan 18, 2025 07:14PM**

Setting standard triage labels for a provisional V8 sandbox bypass - V8 sheriff please adjust.


---

**#4 — sr...@google.com — Jan 21, 2025 12:09AM**

syg@ could you take a look at this or do you know who is familiar with this code?

Also, is there a good search pattern to find all these function pointer assignments in torque? Maybe something like `f:tq$ type.*=.*=>`?


---

**#5 — sy...@google.com — Jan 22, 2025 03:26AM**

Nico's the owner of Torque, so reassigning. So what's a possible solution here? BuiltinPtrs need to be external pointer'd?


---

**#6 — sr...@google.com — Jan 22, 2025 06:27PM**

We could also move the objects that contain builtin ptrs into the TrustedSpace.


---

**#7 — ap...@google.com — Jan 27, 2025 11:38PM**

Project: v8/v8  
Branch: main  
Author: Nico Hartmann <[nicohartmann@chromium.org](<mailto:nicohartmann@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6189989](<https://chromium-review.googlesource.com/6189989>)

[torque] Remove indirect calls in array-sort.tq

* * *

Expand for full commit details

```
[torque] Remove indirect calls in array-sort.tq 
 
Bug: 390639820 
Change-Id: Id3cd199ea3af56912f1433696eb0e5147184f292 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6189989 
Commit-Queue: Nico Hartmann <nicohartmann@chromium.org> 
Reviewed-by: Stephen Röttger <sroettger@google.com> 
Reviewed-by: Leszek Swirski <leszeks@chromium.org> 
Cr-Commit-Position: refs/heads/main@{#98328}
```

* * *

Files:

  * M `src/torque/csa-generator.cc`
  * M `third_party/v8/builtins/array-sort.tq`

* * *

Hash: 02d0fc9fbda0c8a06f2e71ab2bacaa85560510a9  
Date: Thu Jan 23 12:33:31 2025

* * *


---

**#8 — sp...@google.com — Feb 6, 2025 10:56AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $20000.00 for this report.  
  
Rationale for this decision:  
V8 sandbox bypass report demonstrating attacker controlled control flow hijack   
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#9 — am...@chromium.org — Feb 6, 2025 11:18AM**

Congratulations on another one, Seunghyun! Thank you for your efforts researcher the V8 heap sandbox and reporting this issue to us -- great work!


---

**#10 — ch...@google.com — May 7, 2025 09:57PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
