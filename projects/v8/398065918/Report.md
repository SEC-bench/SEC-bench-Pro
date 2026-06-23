# V8 Maglev improper folded allocation handling (leading to memory safety issues)

Issue URL: https://issues.chromium.org/issues/398065918
VRP-Reward: 7000
Date: Feb 21, 2025 07:02PM


VULNERABILITY DETAILS

### Intro

The vulnerability uses two V8 concepts:

  * Folded allocation - is an optimization where multiple allocation operations are combined into a single allocation.
  * Memory is divided into two main regions Young Generation (Young Space) and Old Generation (Old Space). When an object in the Young Space survives multiple garbage collections, it is promoted or reallocated to the Old Space. One of the moment when GC is called is during `Builtins_AllocateInYoungGeneration`, which is called when need to allocate more memory.

The issue gets triggered when reallocation is performed in the middle of folded allocation.

### The bug

Let's consider a simplified code

```
function triggerFunction(...a) {
    ...
}
function __f_0() {
    ...
    triggerFunction(v, pi, r);
    ...
}
```

When Maglev creates folded allocation and GC/reallocation is performed in the middle of such allocation, the variable "V" will be overlapped by array "A".

The process looks as follow:

  1. Allocate memory for "V" and create "V"
  2. Allocate memory for both "PI" and "A" (folded allocation) and create "PI".
  3. Allocate memory for "R" and create "R". As not enough memory in current block - extend it. During extention the garbage collection and reallocation (from Young to Old space) is done.
  4. Reallocate "PI" from Young to Old space. Reallocate "V" from Young to Old space. "V" is put right after "PI".
  5. Create array "A". As space after "PI" is reserved for "A" (in step 2) it is put right after "PI". But variable "V" now uses this space (becuase of step 4). "V" is overwritten by "A".

So, the "PI" is reallocated to the new place. The "V" varialbe is also, and it got placed right after "PI". However, due to the folded allocation, the place after "PI" is reserved for "A".

Variable "V" before overwritten by array "A"

```
0x33920064002d: [HeapNumber]
 - map: 0x339200000515 <Map[12](HEAP_NUMBER_TYPE)>
 - value: 1073751774.0
```

Variable "V" after overwritten by array "A"

```
0x33920064002d: [FixedArray]
 - map: 0x339200000565 <Map(FIXED_ARRAY_TYPE)>
 - length: 10
           0: 0x33920064002d <FixedArray[10]>
           1: 0x339200640021 <HeapNumber 3.14159>
           2: 0x339200000011 <undefined>
           3: 0x3392006400ad <HeapNumber 107375179900.0>
           4: 0x339200000011 <undefined>
           5: 0x339200640011 <Number map = 0x339200509f0d value = 0>
         6-9: 0x339200000011 <undefined>
```

### Restrictions/requirements for triggering the bug

Small modification in script result in triggering GC/reallocation in other functions, breaking the process. To trigger the issue this is a must:

  * Folded allocation of "PI" and "A" (we always have it with our code)
  * The quota to reallocate from Young to Old space for both "V" and "PI" should be reached right before step 3 (sensitive to side-effects)
  * Should not be enough space to allocate new variable "R" at step 3, so `Builtins_AllocateInYoungGeneration` would be called and trigger reallocation (sensitive to side-effects)

To accommodate the different memory layouts (between various source commits, different run flags, build arguments), we had to introduce additional allocations by adding stub variable declarations. We've made a script `search_allocations.py` to do this automatically.

### How it probably should work

Non-vulnerable, intended behavior probably is one of the following:

  * Reallocator should be aware of folded allocation and keep track reserved memory
  * Reallocation shouldn't happen in the middle of folded allocation (between step 2 and 5). All objects from folded allocation should be created before reallocation. Currently, "A" is created after reallocation.

### Root cause

Rest arguments create such sequence "V", "PI", "R", "A", where "PI" and "A" are folded-allocated.

### Proof of concept

#### PoC 1

Branch: main, commit: `f30c2930794e1347a85909c0272964692e4311f6`

args.gn (release build)

```
is_component_build = false
is_debug = false
target_cpu = "x64"
v8_enable_sandbox = true
v8_enable_backtrace = true
v8_enable_disassembler = true
v8_enable_object_print = true
v8_enable_verify_heap = true
dcheck_always_on = false
```

Command: `d8 --allow-natives-syntax --no-js-atomics-pause --no-script-context-mutable-heap-number --predictable --wasm-staging --isolate poc1.js`

Error:

```
Stacktrace:
    ptr1=0x9b1001c002d
    ptr2=(nil)
    ptr3=(nil)
    ptr4=(nil)
    ptr5=(nil)
    ptr6=(nil)
    failure_message_object=0x75c7c3df7130

==== JS stack trace =========================================

    0: ExitFrame [pc: 0x5f92730281b6]
    1: StubFrame [pc: 0x5f927307ce95]
    2: StubFrame [pc: 0x5f9273070a45]
    3: toString [0x9b1003431d1](this=10000000,0x09b1001c002d <FixedArray[10]>,0x09b1001c0021 <HeapNumber 3.14159>,0x09b100000011 <undefined>,0x09b1001c00ad <HeapNumber 78383880524.0>,0x09b100000011 <undefined>,0x09b1001c0011 <Number map = 0x9b10034308d value = 0>,0x09b100000011 <undefined>,0x09b100000011 <undefined>,0x09b100000011 <undefined>,0x09b100000011 <undefined>)
    4: __f_0 [0x9b10035bc81] [poc1.js:~170] [pc=0x5f92d2f4a95e](this=0x09b100341a85 <JSGlobalProxy>)
    5: __f_1 [0x9b10035bcb5] [poc1.js:190] [bytecode=0x31a0018013d offset=40](this=0x09b100341a85 <JSGlobalProxy>)
    6: /* anonymous */ [0x9b10035b3a1] [poc1.js:193] [bytecode=0x31a001800d1 offset=43](this=0x09b100341a85 <JSGlobalProxy>)
    7: InternalFrame [pc: 0x5f9272f7e71c]
    8: EntryFrame [pc: 0x5f9272f7e46b]

==== Details ================================================

[0]: ExitFrame [pc: 0x5f92730281b6]
[1]: StubFrame [pc: 0x5f927307ce95]
[2]: StubFrame [pc: 0x5f9273070a45]
[3]: toString [0x9b1003431d1](this=10000000,0x09b1001c002d <FixedArray[10]>,0x09b1001c0021 <HeapNumber 3.14159>,0x09b100000011 <undefined>,0x09b1001c00ad <HeapNumber 78383880524.0>,0x09b100000011 <undefined>,0x09b1001c0011 <Number map = 0x9b10034308d value = 0>,0x09b100000011 <undefined>,0x09b100000011 <undefined>,0x09b100000011 <undefined>,0x09b100000011 <undefined>) {
// optimized frame
--------- s o u r c e   c o d e ---------
<No Source>
-----------------------------------------
}
[4]: __f_0 [0x9b10035bc81] [poc1.js:~170] [pc=0x5f92d2f4a95e](this=0x09b100341a85 <JSGlobalProxy>) {
// optimized frame
--------- s o u r c e   c o d e ---------
function __f_0() {\x0a  let __v_2 = __v_1;\x0a\x0a  for (var i = 0; i < 100; i++) { \x0a    --__v_1;\x0a    __v_2 += __v_1;\x0a    console.log(i);\x0a    console.log(__v_1);\x0a    triggerFunction(10000000, 456109613, __v_1,   Math.PI, __getRandomObject(5161),__v_2, __getRandomObject(639756),new Number(), undefined,undefined, undefined,...

-----------------------------------------
}
[5]: __f_1 [0x9b10035bcb5] [poc1.js:190] [bytecode=0x31a0018013d offset=40](this=0x09b100341a85 <JSGlobalProxy>) {
  // expression stack (top to bottom)
  [01] : 0x09b100341a85 <JSGlobalProxy>
  [00] : 0x09b10035bc81 <JSFunction __f_0 (sfi = 0x9b10035b259)>
--------- s o u r c e   c o d e ---------
function __f_1() {\x0a  %PrepareFunctionForOptimization(__f_0);  \x0a  __f_0();\x0a  %OptimizeMaglevOnNextCall(__f_0);\x0a  __v_1 = 1073751824;\x0a  __f_0();\x0a}
-----------------------------------------
}

[6]: /* anonymous */ [0x9b10035b3a1] [poc1.js:193] [bytecode=0x31a001800d1 offset=43](this=0x09b100341a85 <JSGlobalProxy>) {
  // heap-allocated locals
  var __v_1 = 0x09b10035eb35 <FixedArray[1]>
  // expression stack (top to bottom)
  [04] : 0x09b100341a85 <JSGlobalProxy>
  [03] : 0x09b10035d63d <Object map = 0x9b10034281d>
  [02] : 0x09b10035d659 <Object map = 0x9b10034281d>
  [01] : 0x09b10035bcb5 <JSFunction __f_1 (sfi = 0x9b10035b289)>
  [00] : 0x09b100000011 <undefined>
--------- s o u r c e   c o d e ---------
var my_simple_var_0;\x0avar my_simple_var_1;\x0avar my_simple_var_2;\x0avar my_simple_var_3;\x0avar my_simple_var_4;\x0avar my_simple_var_5;\x0avar my_simple_var_6;\x0avar my_simple_var_7;\x0avar my_simple_var_8;\x0avar my_simple_var_9;\x0avar my_simple_var_10;\x0avar my_simple_var_11;\x0avar my_simple_var_12;\x0avar my_simple_var_13;\x0ava...

-----------------------------------------
}

[7]: InternalFrame [pc: 0x5f9272f7e71c]
[8]: EntryFrame [pc: 0x5f9272f7e46b]
=====================

Trace/breakpoint trap (core dumped)
```

The crash itself happens in `toString` (`NumberPrototypeToString` in `number.tq`), where the first argument is considered as radix. But as number value is overlapped by array the crash will happen during the convertion.

#### PoC 2

Branch: main, commit: `f30c2930794e1347a85909c0272964692e4311f6`

args.gn (build with dchecks)

```
symbol_level = 2
is_debug = false
v8_optimized_debug = false
dcheck_always_on = true
v8_win64_unwinding_info = true
v8_enable_verify_csa = true
v8_enable_object_print = true
v8_enable_maglev_graph_printer = true
v8_enable_disassembler = true
v8_enable_slow_dchecks = true
v8_enable_verify_heap = true
v8_enable_sandbox = true

target_cpu = "x64"
v8_enable_backtrace = true
v8_enable_gdbjit = true
```

Command: `d8 --allow-natives-syntax --no-js-atomics-pause --no-script-context-mutable-heap-number --predictable --wasm-staging --isolate poc2.js`

Error:

```
#
# Fatal error in ../../src/objects/object-type.cc, line 82
# Type cast failed in CAST(LoadFromObject(machine_type, object, raw_offset)) at ../../src/codegen/code-stub-assembler.h:1166
  Expected Map but found Smi: 0x2a22168c (706877068)

#
#
#
#FailureMessage Object: 0x7ce5a47fee00Trace/breakpoint trap (core dumped)
```

Here we trigger a crash in different place, which may be more useful for the exploitation.

#### PoC 3

Issue is also present in older versions. This is the earliest commit for which we made a PoC, but the issue may have existed even earlier.

Branch: main, commit: `4bfcab00943b1e35f4fb2326aafea5a64752f75e`

args.gn (release)

```
is_component_build = false
is_debug = false
target_cpu = "x64"
v8_enable_sandbox = true

v8_enable_backtrace = true
v8_enable_disassembler = true
v8_enable_object_print = true
v8_enable_verify_heap = true
dcheck_always_on = false
```

Command: `d8 --allow-natives-syntax --predictable --isolate poc3.js`

Error:

```
Stacktrace:
    ptr1=0x9b0001c002d
    ptr2=(nil)
    ptr3=(nil)
    ptr4=(nil)
    ptr5=(nil)
    ptr6=(nil)
    failure_message_object=0x7d52007f7150

==== JS stack trace =========================================

    0: ExitFrame [pc: 0x6452ba4f81b6]
    1: StubFrame [pc: 0x6452ba54cf94]
    2: StubFrame [pc: 0x6452ba5410c5]
    3: toString [0x9b000349b09](this=10000000,0x09b0001c002d <FixedArray[10]>,0x09b0001c0021 <HeapNumber 3.14159>,0x09b000000069 <undefined>,0x09b0001c00ad <HeapNumber 13958773634.0>,0x09b000000069 <undefined>,0x09b0001c0011 <Number map = 0x9b0003499c5 value = 0>,0x09b000000069 <undefined>,0x09b000000069 <undefined>,0x09b000000069 <undefined>,0x09b000000069 <undefined>)
    4: __f_0 [0x9b00035c99d] [../../poc3_4bfcab00943b1e35f4fb2326aafea5a64752f75e.js:~360] [pc=0x6452e000a190](this=0x09b0003416c9 <JSGlobalProxy>)
    5: __f_1 [0x9b00035c9d1] [../../poc3_4bfcab00943b1e35f4fb2326aafea5a64752f75e.js:380] [bytecode=0x31a000800b5 offset=40](this=0x09b0003416c9 <JSGlobalProxy>)
    6: /* anonymous */ [0x9b00035b209] [../../poc3_4bfcab00943b1e35f4fb2326aafea5a64752f75e.js:383] [bytecode=0x31a00080035 offset=61](this=0x09b0003416c9 <JSGlobalProxy>)
    7: InternalFrame [pc: 0x6452ba45671c]
    8: EntryFrame [pc: 0x6452ba45645f]

==== Details ================================================

[0]: ExitFrame [pc: 0x6452ba4f81b6]
[1]: StubFrame [pc: 0x6452ba54cf94]
[2]: StubFrame [pc: 0x6452ba5410c5]
[3]: toString [0x9b000349b09](this=10000000,0x09b0001c002d <FixedArray[10]>,0x09b0001c0021 <HeapNumber 3.14159>,0x09b000000069 <undefined>,0x09b0001c00ad <HeapNumber 13958773634.0>,0x09b000000069 <undefined>,0x09b0001c0011 <Number map = 0x9b0003499c5 value = 0>,0x09b000000069 <undefined>,0x09b000000069 <undefined>,0x09b000000069 <undefined>,0x09b000000069 <undefined>) {
// optimized frame
--------- s o u r c e   c o d e ---------
<No Source>
-----------------------------------------
}
[4]: __f_0 [0x9b00035c99d] [../../poc3_4bfcab00943b1e35f4fb2326aafea5a64752f75e.js:~360] [pc=0x6452e000a190](this=0x09b0003416c9 <JSGlobalProxy>) {
// optimized frame
--------- s o u r c e   c o d e ---------
function __f_0() {\x0a  let __v_2 = __v_1;\x0a\x0a  for (var i = 0; i < 100; i++) { \x0a    --__v_1;\x0a    __v_2 += __v_1;\x0a    console.log(i);\x0a    console.log(__v_1);\x0a    triggerFunction(10000000, 456109613, __v_1,   Math.PI, __getRandomObject(5161),__v_2, __getRandomObject(639756),new Number(), undefined,undefined, undefined,...

-----------------------------------------
}
[5]: __f_1 [0x9b00035c9d1] [../../poc3_4bfcab00943b1e35f4fb2326aafea5a64752f75e.js:380] [bytecode=0x31a000800b5 offset=40](this=0x09b0003416c9 <JSGlobalProxy>) {
  // expression stack (top to bottom)
  [01] : 0x09b0003416c9 <JSGlobalProxy>
  [00] : 0x09b00035c99d <JSFunction __f_0 (sfi = 0x9b00035b0a9)>
--------- s o u r c e   c o d e ---------
function __f_1() {\x0a  %PrepareFunctionForOptimization(__f_0);  \x0a  __f_0();\x0a  %OptimizeMaglevOnNextCall(__f_0);\x0a  __v_1 = 1073751824;\x0a  __f_0();\x0a}
-----------------------------------------
}

[6]: /* anonymous */ [0x9b00035b209] [../../poc3_4bfcab00943b1e35f4fb2326aafea5a64752f75e.js:383] [bytecode=0x31a00080035 offset=61](this=0x09b0003416c9 <JSGlobalProxy>) {
  // heap-allocated locals
  var __v_1 = 0x09b000360995 <FixedArray[1]>
  // expression stack (top to bottom)
  [04] : 0x09b0003416c9 <JSGlobalProxy>
  [03] : 0x09b00035e391 <Object map = 0x9b000342445>
  [02] : 0x09b00035e3ad <Object map = 0x9b000342445>
  [01] : 0x09b00035c9d1 <JSFunction __f_1 (sfi = 0x9b00035b0e9)>
  [00] : 0x09b000000069 <undefined>
--------- s o u r c e   c o d e ---------
var my_simple_var_0;\x0avar my_simple_var_1;\x0avar my_simple_var_2;\x0avar my_simple_var_3;\x0avar my_simple_var_4;\x0avar my_simple_var_5;\x0avar my_simple_var_6;\x0avar my_simple_var_7;\x0avar my_simple_var_8;\x0avar my_simple_var_9;\x0avar my_simple_var_10;\x0avar my_simple_var_11;\x0avar my_simple_var_12;\x0avar my_simple_var_13;\x0ava...

-----------------------------------------
}

[7]: InternalFrame [pc: 0x6452ba45671c]
[8]: EntryFrame [pc: 0x6452ba45645f]
=====================

Trace/breakpoint trap (core dumped)
```

### Fix

The fix should reset/split folded allocation done in rest arguments.

```
diff --git a/src/maglev/maglev-graph-builder.cc b/src/maglev/maglev-graph-builder.cc
index 7c7c1c36c95..b36b64df4eb 100644
--- a/src/maglev/maglev-graph-builder.cc
+++ b/src/maglev/maglev-graph-builder.cc
@@ -12900,6 +12900,7 @@ ValueNode* MaglevGraphBuilder::BuildInlinedAllocation(
       SmallZoneVector<ValueNode*, 8> values(zone());
       vobject->ForEachDeoptInputLocation(
           [&](ValueNode* node, ValueNode*& input) {
+            ClearCurrentAllocationBlock();
             if (node->Is<VirtualObject>()) {
               VirtualObject* nested = node->Cast<VirtualObject>();
               node = BuildInlinedAllocation(nested, allocation_type);
```

### Reproduction

See the attached files and the "Restrictions/requirements for triggering the bug" section

### CREDIT INFORMATION

Externally reported security bugs may appear in Chrome release notes. If this bug is included, how would you like to be credited? Reporter credit: Excello s.r.o.


---

**#2 — cl...@appspot.gserviceaccount.com — Feb 22, 2025 04:59AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5810666199777280](<https://clusterfuzz.com/testcase?key=5810666199777280>).


---

**#3 — cl...@appspot.gserviceaccount.com — Feb 22, 2025 08:18AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=6374616427593728](<https://clusterfuzz.com/testcase?key=6374616427593728>).


---

**#4 — cl...@appspot.gserviceaccount.com — Feb 25, 2025 03:50AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5785815468670976](<https://clusterfuzz.com/testcase?key=5785815468670976>).


---

**#5 — ca...@chromium.org — Feb 25, 2025 06:40AM**

Looks like CF wasn't able to reproduce this. Tentatively triaging as a valid high severity bug found in the current extended stable and assigning to the V8 sheriff for further triage.


---

**#6 — is...@chromium.org — Feb 25, 2025 06:26PM**

Thank you for the report!


---

**#7 — ch...@google.com — Feb 25, 2025 09:38PM**

Setting milestone because of s0/s1 severity.


---

**#8 — ap...@google.com — Feb 25, 2025 10:39PM**

Project: v8/v8  
Branch: main  
Author: Olivier Flückiger <[olivf@chromium.org](<mailto:olivf@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6297972](<https://chromium-review.googlesource.com/6297972>)

[maglev] Add missing ClearAllocationBlock

* * *

Expand for full commit details

```
[maglev] Add missing ClearAllocationBlock 
 
Fixed: 398065918 
Change-Id: Ifc163b6633e55ca707815ef910a26dfb144a667b 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6297972 
Reviewed-by: Victor Gomes <victorgomes@chromium.org> 
Commit-Queue: Olivier Flückiger <olivf@chromium.org> 
Auto-Submit: Olivier Flückiger <olivf@chromium.org> 
Cr-Commit-Position: refs/heads/main@{#98917}
```

* * *

Files:

  * M `src/maglev/maglev-graph-builder.cc`

* * *

Hash: eb9b25970b0ad4a3f8ce23d8de3583c62e5d6b87  
Date: Tue Feb 25 13:14:53 2025

* * *


---

**#9 — ap...@google.com — Feb 25, 2025 10:41PM**

Project: v8/v8  
Branch: main  
Author: Olivier Flückiger <[olivf@chromium.org](<mailto:olivf@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6297973](<https://chromium-review.googlesource.com/6297973>)

[maglev] Clear the current allocation block only on effects

* * *

Expand for full commit details

```
[maglev] Clear the current allocation block only on effects 
 
Instead of clearing manually we clear the block after allocating 
instructions and on control flow. 
 
Bug: 398065918 
Change-Id: If3baa726d3f140df66aa08f1d1364dd2458096e6 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6297973 
Reviewed-by: Victor Gomes <victorgomes@chromium.org> 
Commit-Queue: Victor Gomes <victorgomes@chromium.org> 
Auto-Submit: Olivier Flückiger <olivf@chromium.org> 
Cr-Commit-Position: refs/heads/main@{#98921}
```

* * *

Files:

  * M `src/maglev/maglev-graph-builder.cc`
  * M `src/maglev/maglev-graph-builder.h`

* * *

Hash: 8dc89d8bc1020bd2a6d7677e0804fda30e786055  
Date: Tue Feb 25 13:30:17 2025

* * *


---

**#10 — ap...@google.com — Feb 26, 2025 12:06AM**

Project: v8/v8  
Branch: main  
Author: Leszek Swirski <[leszeks@chromium.org](<mailto:leszeks@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6299061](<https://chromium-review.googlesource.com/6299061>)

Revert "[maglev] Clear the current allocation block only on effects"

* * *

Expand for full commit details

```
Revert "[maglev] Clear the current allocation block only on effects" 
 
This reverts commit 8dc89d8bc1020bd2a6d7677e0804fda30e786055. 
 
Reason for revert: Suspecting as root cause of https://ci.chromium.org/ui/p/v8/builders/ci/V8%20Linux64%20css%20-%20debug/11739/overview 
 
Original change's description: 
> [maglev] Clear the current allocation block only on effects 
> 
> Instead of clearing manually we clear the block after allocating 
> instructions and on control flow. 
> 
> Bug: 398065918 
> Change-Id: If3baa726d3f140df66aa08f1d1364dd2458096e6 
> Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6297973 
> Reviewed-by: Victor Gomes <victorgomes@chromium.org> 
> Commit-Queue: Victor Gomes <victorgomes@chromium.org> 
> Auto-Submit: Olivier Flückiger <olivf@chromium.org> 
> Cr-Commit-Position: refs/heads/main@{#98921} 
 
Bug: 398065918 
Change-Id: I62bfead1d05276a2ad825d42ac07c637033aac07 
No-Presubmit: true 
No-Tree-Checks: true 
No-Try: true 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6299061 
Commit-Queue: Rubber Stamper <rubber-stamper@appspot.gserviceaccount.com> 
Auto-Submit: Leszek Swirski <leszeks@chromium.org> 
Bot-Commit: Rubber Stamper <rubber-stamper@appspot.gserviceaccount.com> 
Cr-Commit-Position: refs/heads/main@{#98923}
```

* * *

Files:

  * M `src/maglev/maglev-graph-builder.cc`
  * M `src/maglev/maglev-graph-builder.h`

* * *

Hash: 47b298b5083f0d7c67fdc5b21dc3c6ac026995e2  
Date: Tue Feb 25 07:00:02 2025

* * *


---

**#11 — ch...@google.com — Feb 26, 2025 09:41PM**

Security Merge Request Consideration: This is sufficiently serious that it should be merged to extended stable. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M132. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately. Security Merge Request Consideration: This is sufficiently serious that it should be merged to stable. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M133. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately. Security Merge Request Consideration: This is sufficiently serious that it should be merged to beta. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M134. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately. Security Merge Request - Manual Review: Merge review required: a reverted commit was detected after the merge request.

Security Merge Request - Manual Review: Merge review required: a reverted commit was detected after the merge request.

Security Merge Request - Manual Review: Merge review required: a reverted commit was detected after the merge request.

Security Merge Request: Thank you for fixing this security bug! We aim to ship security fixes as quickly as possible, to limit their opportunity for exploitation as an "n-day" (that is, a bug where git fixes are developed into attacks before those fixes reach users).

We have determined this fix is necessary on milestone(s): [132, 133, 134].

Please answer the following questions so that we can safely process this merge request:

  1. Which CLs should be backmerged? (Please include Gerrit links.)
  2. Has this fix been verified on Canary to not pose any stability regressions?
  3. Does this fix pose any potential non-verifiable stability risks?
  4. Does this fix pose any known compatibility risks?
  5. Does it require manual verification by the test team? If so, please describe required testing.
  6. (no answer required) Please check the OS custom field to ensure all impacted OSes are checked!


---

**#12 — ol...@chromium.org — Feb 26, 2025 11:25PM**

1\. [https://chromium-review.googlesource.com/6297972](<https://chromium-review.googlesource.com/6297972>)  
2\. y  
3-5. n


---

**#13 — am...@chromium.org — Feb 27, 2025 04:06AM**

[https://crrev.com/c/6297972](<https://crrev.com/c/6297972>) approved for merge to M134, please merge this fix to branch 13.4 at your convenience M134 Stable RC was already cut for release next week; unless it is recut before release this fix will ship in the first update.


---

**#14 — ap...@google.com — Feb 27, 2025 05:59PM**

Project: v8/v8  
Branch: refs/branch-heads/13.4  
Author: Olivier Flückiger <[olivf@chromium.org](<mailto:olivf@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6304712](<https://chromium-review.googlesource.com/6304712>)

merged: [maglev] Add missing ClearAllocationBlock

* * *

Expand for full commit details

```
merged: [maglev] Add missing ClearAllocationBlock 
 
Fixed: 398065918 
(cherry picked from commit eb9b25970b0ad4a3f8ce23d8de3583c62e5d6b87) 
 
Change-Id: I20f3979984c1df11509f1630cf4c4c4460d6a83a 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6304712 
Reviewed-by: Victor Gomes <victorgomes@chromium.org> 
Auto-Submit: Olivier Flückiger <olivf@chromium.org> 
Commit-Queue: Olivier Flückiger <olivf@chromium.org> 
Commit-Queue: Victor Gomes <victorgomes@chromium.org> 
Cr-Commit-Position: refs/branch-heads/13.4@{#29} 
Cr-Branched-From: 0f87a54dade4353b6ece1d7591ca8c66f90c1c93-refs/heads/13.4.114@{#1} 
Cr-Branched-From: 27af2e9363b2701abc5f3feb701b1dad7d1a9fe8-refs/heads/main@{#98459}
```

* * *

Files:

  * M `src/maglev/maglev-graph-builder.cc`

* * *

Hash: 2b4812d502b2bbd2eeace4d383dd1bb3252702ba  
Date: Thu Feb 27 09:19:22 2025

* * *


---

**#15 — ap...@google.com — Feb 27, 2025 05:59PM**

[Details redacted due to bug visibility]  
  
Change-Id: Id1c07bb654a191f36811de01d70f239aa2d2d98a  
[https://chrome-internal-review.googlesource.com/8061108](<https://chrome-internal-review.googlesource.com/8061108>)


---

**#16 — ap...@google.com — Feb 27, 2025 08:57PM**

Project: v8/v8  
Branch: main  
Author: Olivier Flückiger <[olivf@chromium.org](<mailto:olivf@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6305040](<https://chromium-review.googlesource.com/6305040>)

Reland "[maglev] Clear the current allocation block only on effects"

* * *

Expand for full commit details

```
Reland "[maglev] Clear the current allocation block only on effects" 
 
This is a reland of commit 8dc89d8bc1020bd2a6d7677e0804fda30e786055 
 
Fixed: adding some missing CanAllocate properties to instructions 
 
Original change's description: 
> [maglev] Clear the current allocation block only on effects 
> 
> Instead of clearing manually we clear the block after allocating 
> instructions and on control flow. 
> 
> Bug: 398065918 
> Change-Id: If3baa726d3f140df66aa08f1d1364dd2458096e6 
> Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6297973 
> Reviewed-by: Victor Gomes <victorgomes@chromium.org> 
> Commit-Queue: Victor Gomes <victorgomes@chromium.org> 
> Auto-Submit: Olivier Flückiger <olivf@chromium.org> 
> Cr-Commit-Position: refs/heads/main@{#98921} 
 
Bug: 398065918 
Change-Id: Ia0497301b728dd8891c1d90e2f6bca01f89ee8d4 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6305040 
Auto-Submit: Olivier Flückiger <olivf@chromium.org> 
Reviewed-by: Victor Gomes <victorgomes@chromium.org> 
Commit-Queue: Olivier Flückiger <olivf@chromium.org> 
Cr-Commit-Position: refs/heads/main@{#98962}
```

* * *

Files:

  * M `src/maglev/maglev-graph-builder.cc`
  * M `src/maglev/maglev-graph-builder.h`
  * M `src/maglev/maglev-ir.h`

* * *

Hash: 58ad206e922fbd7f6fad7b9e2e134f0191109307  
Date: Wed Feb 26 16:06:59 2025

* * *


---

**#17 — ap...@google.com — Feb 27, 2025 08:59PM**

Project: v8/v8  
Branch: main  
Author: Leszek Swirski <[leszeks@chromium.org](<mailto:leszeks@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6306968](<https://chromium-review.googlesource.com/6306968>)

Revert "Reland "[maglev] Clear the current allocation block only on effects""

* * *

Expand for full commit details

```
Revert "Reland "[maglev] Clear the current allocation block only on effects"" 
 
This reverts commit 58ad206e922fbd7f6fad7b9e2e134f0191109307. 
 
Reason for revert: Alas: https://ci.chromium.org/ui/p/v8/builders/ci/V8%20Linux64%20-%20debug/53294/overview 
 
Original change's description: 
> Reland "[maglev] Clear the current allocation block only on effects" 
> 
> This is a reland of commit 8dc89d8bc1020bd2a6d7677e0804fda30e786055 
> 
> Fixed: adding some missing CanAllocate properties to instructions 
> 
> Original change's description: 
> > [maglev] Clear the current allocation block only on effects 
> > 
> > Instead of clearing manually we clear the block after allocating 
> > instructions and on control flow. 
> > 
> > Bug: 398065918 
> > Change-Id: If3baa726d3f140df66aa08f1d1364dd2458096e6 
> > Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6297973 
> > Reviewed-by: Victor Gomes <victorgomes@chromium.org> 
> > Commit-Queue: Victor Gomes <victorgomes@chromium.org> 
> > Auto-Submit: Olivier Flückiger <olivf@chromium.org> 
> > Cr-Commit-Position: refs/heads/main@{#98921} 
> 
> Bug: 398065918 
> Change-Id: Ia0497301b728dd8891c1d90e2f6bca01f89ee8d4 
> Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6305040 
> Auto-Submit: Olivier Flückiger <olivf@chromium.org> 
> Reviewed-by: Victor Gomes <victorgomes@chromium.org> 
> Commit-Queue: Olivier Flückiger <olivf@chromium.org> 
> Cr-Commit-Position: refs/heads/main@{#98962} 
 
Bug: 398065918 
Change-Id: I900f90276981b74f00eeb49bbbebb8a46197dc69 
No-Presubmit: true 
No-Tree-Checks: true 
No-Try: true 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6306968 
Auto-Submit: Leszek Swirski <leszeks@chromium.org> 
Commit-Queue: Rubber Stamper <rubber-stamper@appspot.gserviceaccount.com> 
Bot-Commit: Rubber Stamper <rubber-stamper@appspot.gserviceaccount.com> 
Cr-Commit-Position: refs/heads/main@{#98966}
```

* * *

Files:

  * M `src/maglev/maglev-graph-builder.cc`
  * M `src/maglev/maglev-graph-builder.h`
  * M `src/maglev/maglev-ir.h`

* * *

Hash: eb87bb4a7be34be7f230b3d6ed6e492cb01dc505  
Date: Thu Feb 27 03:55:23 2025

* * *


---

**#18 — ap...@google.com — Feb 28, 2025 01:56AM**

Project: v8/v8  
Branch: main  
Author: Olivier Flückiger <[olivf@chromium.org](<mailto:olivf@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6309164](<https://chromium-review.googlesource.com/6309164>)

Reland^2 "[maglev] Clear the current allocation block only on effects"

* * *

Expand for full commit details

```
Reland^2 "[maglev] Clear the current allocation block only on effects" 
 
This is a reland of commit 58ad206e922fbd7f6fad7b9e2e134f0191109307 
 
Fixed: 
* Clear allocation block even if the inliner ends in an unconditional 
  deopt. 
 
Original change's description: 
> Reland "[maglev] Clear the current allocation block only on effects" 
> 
> This is a reland of commit 8dc89d8bc1020bd2a6d7677e0804fda30e786055 
> 
> Fixed: adding some missing CanAllocate properties to instructions 
> 
> Original change's description: 
> > [maglev] Clear the current allocation block only on effects 
> > 
> > Instead of clearing manually we clear the block after allocating 
> > instructions and on control flow. 
> > 
> > Bug: 398065918 
> > Change-Id: If3baa726d3f140df66aa08f1d1364dd2458096e6 
> > Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6297973 
> > Reviewed-by: Victor Gomes <victorgomes@chromium.org> 
> > Commit-Queue: Victor Gomes <victorgomes@chromium.org> 
> > Auto-Submit: Olivier Flückiger <olivf@chromium.org> 
> > Cr-Commit-Position: refs/heads/main@{#98921} 
> 
> Bug: 398065918 
> Change-Id: Ia0497301b728dd8891c1d90e2f6bca01f89ee8d4 
> Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6305040 
> Auto-Submit: Olivier Flückiger <olivf@chromium.org> 
> Reviewed-by: Victor Gomes <victorgomes@chromium.org> 
> Commit-Queue: Olivier Flückiger <olivf@chromium.org> 
> Cr-Commit-Position: refs/heads/main@{#98962} 
 
Bug: 398065918 
Change-Id: I7f5cc44ee8fb84ed954376172459dac220261a0f 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6309164 
Reviewed-by: Victor Gomes <victorgomes@chromium.org> 
Auto-Submit: Olivier Flückiger <olivf@chromium.org> 
Commit-Queue: Victor Gomes <victorgomes@chromium.org> 
Cr-Commit-Position: refs/heads/main@{#98977}
```

* * *

Files:

  * M `src/maglev/maglev-graph-builder.cc`
  * M `src/maglev/maglev-graph-builder.h`
  * M `src/maglev/maglev-ir.h`

* * *

Hash: 7c3ccfc4429cb9fefe586a5359a12ebcbb101dd7  
Date: Thu Feb 27 15:27:29 2025

* * *


---

**#19 — pe...@google.com — Mar 4, 2025 12:36AM**

This issue has been approved for a merge. Please merge the fix to any appropriate branches as soon as possible!

If all merges have been completed, please remove any remaining Merge-Approved labels from this issue.

Thanks for your time! To disable nags, add Disable-Nags (case sensitive) to the Chromium Labels custom field.


---

**#20 — am...@chromium.org — Mar 4, 2025 02:30AM**

Hi victorgomes@, it appears that olivf@ is OOO this week, would you mind taking care of these backmerges in their absence? TIA!


---

**#21 — vi...@chromium.org — Mar 4, 2025 05:28PM**

Hi Amy, my understanding is that the fix was already merged on M134: [https://chromium-review.googlesource.com/c/v8/v8/+/6304712](<https://chromium-review.googlesource.com/c/v8/v8/+/6304712>)

The other CL (reverted and relanded multiple times) is an improvement, but not a fix.


---

**#22 — am...@chromium.org — Mar 5, 2025 03:44AM**

Ah, you're correct, I missed the 13.4 merge in the relation change when reviewing [https://crrev.com/c/6297972](<https://crrev.com/c/6297972>) in c#13, there is indeed a merge there


---

**#23 — sp...@google.com — Mar 6, 2025 09:55AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $7000.00 for this report.  
  
Rationale for this decision:  
report of memory corruption in a sandboxed process / renderer   
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#24 — am...@chromium.org — Mar 6, 2025 09:59AM**

Congratulations Excello s.r.o.! Thank you for your efforts and reporting this issue to us -- nice work!


---

**#25 — pe...@google.com — Apr 22, 2025 04:44PM**

This issue requires additional review before it can be merged to the LTS channel. Please answer the following questions to help us evaluate this merge:

  1. Number of CLs needed for this fix and links to them.
  2. Level of complexity (High, Medium, Low - Explain)
  3. Has this been merged to a stable release? beta release?
  4. Overall Recommendation (Yes, No)


---

**#26 — qk...@google.com — Apr 22, 2025 04:51PM**

1\. [https://chromium-review.googlesource.com/c/v8/v8/+/6475764](<https://chromium-review.googlesource.com/c/v8/v8/+/6475764>)  
2\. Medium - There were some conflicts.  
3\. 134  
4\. Yes. According to the description `PoC 3`, M132 contains the suspected CL[1]. There are some conflicts when merging back the fix to M132 though, the code where the fix modifies looks the same. And also, the fix owner thinks the patch looks good to merge back to M132.  
  
[1] 4bfcab00943b1e35f4fb2326aafea5a64752f75e => [https://chromium-review.googlesource.com/c/v8/v8/+/5633348](<https://chromium-review.googlesource.com/c/v8/v8/+/5633348>)


---

**#27 — dx...@google.com — May 1, 2025 02:19PM**

Project: v8/v8  
Branch: refs/branch-heads/13.2  
Author: Olivier Flückiger [olivf@chromium.org](<mailto:olivf@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6475764](<https://chromium-review.googlesource.com/6475764>)

[M132-LTS][maglev] Add missing ClearAllocationBlock

* * *

Expand for full commit details

```
     
    (cherry picked from commit eb9b25970b0ad4a3f8ce23d8de3583c62e5d6b87) 
     
    Fixed: 398065918 
    Change-Id: Ifc163b6633e55ca707815ef910a26dfb144a667b 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6297972 
    Reviewed-by: Victor Gomes <victorgomes@chromium.org> 
    Commit-Queue: Olivier Flückiger <olivf@chromium.org> 
    Auto-Submit: Olivier Flückiger <olivf@chromium.org> 
    Cr-Original-Commit-Position: refs/heads/main@{#98917} 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6475764 
    Reviewed-by: Olivier Flückiger <olivf@chromium.org> 
    Commit-Queue: Gyuyoung Kim (xWF) <qkim@google.com> 
    Cr-Commit-Position: refs/branch-heads/13.2@{#84} 
    Cr-Branched-From: 24068c59cedad9ee976ddc05431f5f497b1ebd71-refs/heads/13.2.152@{#1} 
    Cr-Branched-From: 6054ba94db0969220be4f94dc1677fc4696bdc4f-refs/heads/main@{#97085}
```

* * *

Files:

  * M `src/maglev/maglev-graph-builder.cc`

* * *

Hash: 45d40ca20f298d8b8b91792ad97b6f127fd99a38  
Date: Tue Feb 25 12:14:53 2025

* * *


---

**#28 — ch...@google.com — Jun 4, 2025 09:42PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.


---

**#29 — am...@chromium.org — Jun 26, 2025 03:48AM**

this is already resolved, but realizing this was still assigned to me
