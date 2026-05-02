# V8 Sandbox Bypass: Uninitialized read to switch-case OOB jump in Maglev JSGeneratorObject allocation inlining

Issue URL: https://issues.chromium.org/issues/403600260
VRP-Reward: 25000
Date: Mar 15, 2025 05:41AM


### VULNERABILITY DETAILS

#### Summary

V8 sandbox bypass, uninitialized pointer read from Zone-allocated memory due to corrupted map information (instance size / inobject properties count). Due to this inconsistency Maglev might access uninitialized slots as `ValueNode` pointers. By spraying the heap with target addresses that point to precisely constructed fake `ValueNode` object, it is possible to trigger an out-of-bounds jump table access on an exhaustive switch-case over `Opcode` enum resulting in full PC control.

#### Details

On Maglev tier-up, it may try to inline JSGeneratorObject creation intrinsic. This operates with the generator `JSFunction`'s `initial_map` to read instance size and inobject properties count at `MaglevGraphBuilder::TryBuildAndAllocateJSGeneratorObject()`:

```
// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/maglev/maglev-graph-builder.cc;drc=dd4c05cef2261931f1ef71b49dba7378ae892b93;l=11414
MaybeReduceResult MaglevGraphBuilder::TryBuildAndAllocateJSGeneratorObject(
    ValueNode* closure, ValueNode* receiver) {
  // ...
  // Create the JS[Async]GeneratorObject instance.
  compiler::SlackTrackingPrediction slack_tracking_prediction =
      broker()->dependencies()->DependOnInitialMapInstanceSizePrediction(     // [!] size computation (based on initial_map)
          function);
  compiler::MapRef initial_map = function.initial_map(broker());
  VirtualObject* generator = CreateJSGeneratorObject(                         // [!] slot allocation based on computed instance size
      initial_map, slack_tracking_prediction.instance_size(), GetContext(),
      closure, receiver, register_file);

  // Handle in-object properties.
  for (int i = 0; i < slack_tracking_prediction.inobject_property_count();    // [!] slot initialization based on computed inobject property count
       i++) {
    generator->set(initial_map.GetInObjectPropertyOffset(i), undefined);
  }

  ValueNode* allocation =
      BuildInlinedAllocation(generator, AllocationType::kYoung);              // [!]
  return allocation;
}
```

There exists various `(SBX)CHECK`s inside the callees - however, these only check that we're not going out of bounds of the allocated slots array. With a corrupted initial map it is possible to forge instance size and inobject property counts such that some slots are left uninitialized.

These uninitialized `ValueNode*` slots are immediately accessed within `MaglevGraphBuilder::BuildInlinedAllocation()`:

```
// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/maglev/maglev-graph-builder.cc;drc=2f4e6fd051b670e0e032cc45c6492dd42d054a1c;l=13022
InlinedAllocation* MaglevGraphBuilder::BuildInlinedAllocation(
    VirtualObject* vobject, AllocationType allocation_type) {
  current_interpreter_frame_.add_object(vobject);
  InlinedAllocation* allocation;
  switch (vobject->type()) {
    // ...
    case VirtualObject::kDefault: {
      SmallZoneVector<ValueNode*, 8> values(zone());
      vobject->ForEachInput([&](ValueNode*& node) {            // [!] runs callback with all slots
        ValueNode* value_to_push;
        if (node->Is<VirtualObject>()) {
          // ...
        } else if (node->Is<Float64Constant>()) {
          // ...
        } else {
          value_to_push = GetTaggedValue(node);                // [!] uninit node
        }
        values.push_back(value_to_push);
      });
      // ...
    }
  }
  // ...
}
```

Each of the `ValueNode*` slots, including uninitialized ones, are passed through the callback. By spraying pointers nearby on the heap and triggering this bug, we can call subsequent code with attacker-controlled `node`.

Our target code to reach is `GetTaggedValue(node)`.

```
// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/maglev/maglev-graph-builder.cc;drc=2f4e6fd051b670e0e032cc45c6492dd42d054a1c;l=1479
ValueNode* MaglevGraphBuilder::GetTaggedValue(
    ValueNode* value, UseReprHintRecording record_use_repr_hint) {
  // ...
  ValueRepresentation representation =
      value->properties().value_representation();
  if (representation == ValueRepresentation::kTagged) return value;        // [!] avoid

  if (Int32Constant* as_int32_constant = value->TryCast<Int32Constant>();  // [!] avoid
      as_int32_constant && Smi::IsValid(as_int32_constant->value())) {
    return GetSmiConstant(as_int32_constant->value());
  }

  NodeInfo* node_info = GetOrCreateInfoFor(value);                         // [!] target
  // ...
}

// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/maglev/maglev-interpreter-frame-state.h;drc=2f4e6fd051b670e0e032cc45c6492dd42d054a1c;l=330
  NodeInfo* GetOrCreateInfoFor(ValueNode* node, compiler::JSHeapBroker* broker,
                               LocalIsolate* isolate) {
    auto info_it = FindInfo(node);
    if (IsValid(info_it)) return &info_it->second;                         // [!] avoid(ed automatically)
    auto res = &node_infos.emplace(node, NodeInfo()).first->second;
    res->CombineType(StaticTypeForNode(broker, isolate, node));            // [!] target
    return res;
  }

// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/maglev/maglev-graph-builder.cc;drc=2f4e6fd051b670e0e032cc45c6492dd42d054a1c;l=4400
NodeType StaticTypeForNode(compiler::JSHeapBroker* broker,
                           LocalIsolate* isolate, ValueNode* node) {
  switch (node->properties().value_representation()) {                     // [!] fallthrough this switch-case
    case ValueRepresentation::kInt32:
    case ValueRepresentation::kUint32:
    case ValueRepresentation::kFloat64:
    case ValueRepresentation::kIntPtr:
      return NodeType::kNumber;
    case ValueRepresentation::kHoleyFloat64:
      return NodeType::kNumberOrOddball;
    case ValueRepresentation::kTagged:
      break;
  }
  switch (node->opcode()) {                                                // [!] target switch-case, exhaustive over Opcode enum
    case Opcode::kPhi:
      return node->Cast<Phi>()->type();
    // ... all Opcode enum cases covered
  }
}
```

After a sequence of calls `node` finally reaches `StaticTypeForNode()`. We note the following:

  * The first switch-case is exhaustive over `ValueRepresentation`. However, the size is small so the compiler emits `ValueRepresentation::kTagged` (= 6) case with a `>= 6` comparison as if it's a `default` case. 
    * This allows us to conveniently set `node->properties().value_representation() = 7`, an invalid `ValueRepresentation`, which bypasses both the early return case at `MaglevGraphBuilder::GetTaggedValue()` and falls through the switch-case.
  * The second switch-case is exhaustive over `Opcode`. However, the size is large enough so the compiler emits a jump based on an unchecked access to the jump offset table. 
    * `node->opcode()` is a 16-bit attacker-controlled value - this allows using an OOB jump offset to jump to different code position. This has also been demonstrated in [b/390816209](<https://issues.chromium.org/issues/390816209>).

Using this OOB offset jump, we can easily call a suitable index that results in jumping to a vtable-call-like code to gain arbitrary PC control.

Note that the root cause is `ValueNode*` input slots being uninitialized - OOB offset jump is just one easy way immediately in the code path to exploit this. It is extremely likely that other inlining schemes are similarly vulnerable to the same code pattern.

### VERSION

V8: Tested on CF no-asan sandbox-testing d8 @ revision 99269 (commit [5734b2e](<https://chromium-review.googlesource.com/c/v8/v8/+/6349916>))

### REPRODUCTION CASE

Attached as `maglev-jsgenobj-inline-uninit-switch.js`, run with `./d8 --sandbox-testing --single-threaded` on ClusterFuzz `linux_d8_sandbox_testing` build, revision 99269. Running the PoC will result in PC control to `0x424242424242`.

### FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION

Type of crash: Sandbox violation

Crash state:

```
$ ./d8-sandbox-testing-linux-release-v8-component-99269/d8 --sandbox-testing --single-threaded ./maglev-jsgenobj-inline-uninit-switch.js 
Sandbox testing mode is enabled. Only sandbox violations will be reported, all other crashes will be ignored.

## V8 sandbox violation detected!

Received signal 11 SEGV_MAPERR 424242424242
Segmentation fault

=====================

pwndbg> bt
#0  0x0000424242424242 in ?? ()
#1  0x000055555b3df815 in v8::internal::Assembler::GrowBuffer() ()
#2  0x000055555b3ea071 in v8::internal::Assembler::vinstr(unsigned char, v8::internal::XMMRegister, v8::internal::XMMRegister, v8::internal::Operand, v8::internal::Assembler::SIMDPrefix, v8::internal::Assembler::LeadingOpcode, v8::internal::Assembler::VexW, v8::internal::CpuFeature) ()
#3  0x000055555af80841 in void v8::internal::Assembler::vsd<v8::internal::XMMRegister, v8::internal::Operand>(unsigned char, v8::internal::XMMRegister, v8::internal::XMMRegister, v8::internal::Operand) ()
#4  0x000055555af813e5 in void v8::internal::SharedMacroAssemblerBase::AvxHelper<v8::internal::XMMRegister, v8::internal::Operand>::emit<&v8::internal::Assembler::vmovsd, &v8::internal::Assembler::movsd>(v8::internal::XMMRegister, v8::internal::Operand) ()
#5  0x000055555af81385 in void v8::internal::SharedMacroAssemblerBase::Movsd<v8::internal::XMMRegister, v8::internal::Operand>(v8::internal::XMMRegister, v8::internal::Operand) ()
#6  0x000055555b1118b2 in v8::internal::maglev::ValueNode::DoLoadToRegister(v8::internal::maglev::MaglevAssembler*, v8::internal::XMMRegister) ()
#7  0x000055555c3c8da8 in ?? ()
#8  0x00007fffffffc290 in ?? ()
#9  0x000055555b09bee6 in v8::internal::maglev::KnownNodeAspects::GetOrCreateInfoFor(v8::internal::maglev::ValueNode*, v8::internal::compiler::JSHeapBroker*, v8::internal::LocalIsolate*) ()
Backtrace stopped: previous frame inner to this frame (corrupt stack?)

pwndbg> nearpc 0x000055555b3df811 1
   0x55555b3df80e <v8::internal::Assembler::GrowBuffer()+46>    mov    rdi, rax
 ► 0x55555b3df811 <v8::internal::Assembler::GrowBuffer()+49>    call   qword ptr [r11 + 0x18]
 
   0x55555b3df815 <v8::internal::Assembler::GrowBuffer()+53>    mov    r14d, eax

pwndbg> tele $r11
00:0000│ rax rdi r11 0x42b00000000 ◂— 0x42b00000000
01:0008│             0x42b00000008 ◂— 0
02:0010│             0x42b00000010 ◂— 0
03:0018│             0x42b00000018 ◂— 0x424242424242 /* 'BBBBBB' */
```

### CREDIT INFORMATION

Reporter credit: Seunghyun Lee (@0x10n) of CMU CyLab

* * *

This was discovered with a v8 sandbox fuzzer.  
Marking any rewards for charity in advance.


---

**#2 — ps...@google.com — Mar 17, 2025 11:11PM**

Setting provisional severity and priority and passing to V8 Shepard.


---

**#3 — cl...@appspot.gserviceaccount.com — Mar 17, 2025 11:33PM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=4572959016419328](<https://clusterfuzz.com/testcase?key=4572959016419328>).


---

**#4 — am...@chromium.org — Mar 17, 2025 11:58PM**

Clusterfuzz was not able to reproduce this, came back as `Caught harmless memory access violation (nullptr dereference). Exiting process...`

assigning to Maglev graph-builder folks who have done recent work in this area to see if some other recent change may have collided here


---

**#5 — se...@gmail.com — Mar 18, 2025 12:50AM**

Likely an issue with ASAN meddling with allocation behavior, repros on (non-asan) linux_d8_sandbox_testing latest revision 99291.

* * *

Repro may also be dependent on host libc allocator as PartitionAlloc support is not fully incorporated in d8, but I think the deviation is generally small enough to work on most glibc-based ones.


---

**#6 — ol...@chromium.org — Mar 18, 2025 01:31AM**

@victor, could you ptal. It seems we use `slack_tracking_prediction.instance_size` as the object size but only initialize `slack_tracking_prediction.inobject_property_count`. But I might miss some context as to why it was done this way.


---

**#7 — dm...@chromium.org — Mar 18, 2025 01:36AM**

@olivf: a hint at why it's done this way in Maglev: probably because it was done this way in Turbofan, cf js-create-lowering.cc. And given that this dates back to 7 years ago, there isn't a single compiler owner from back then who is still around, so I'm afraid that this piece of knowledge has been lost to the ages.


---

**#8 — vi...@chromium.org — Mar 19, 2025 08:31PM**

Sorry for the delay, I was OOO yesterday and only saw this issue today. I agree with Darius. I just copied the logic from `js-create-lowering.cc` [code](<https://crsrc.org/c/v8/src/compiler/js-create-lowering.cc;l=138;drc=1baf1050113a5418696839c273e05ea5ad1b5c4d>) in TF, which was added back in 2018. This makes me wonder if the same vulnerability exists there.

For Maglev, I suspect we could simply pass `(slack_tracking_prediction.inobject_property_count() + 1) * kTaggedSize`, as I don't believe the exact instance size is important in this context. We have other code patterns like that for Arrays as well in Maglev. So I guess all of them are potential sandbox escapes.


---

**#9 — vi...@chromium.org — Mar 24, 2025 07:32PM**

I guess we still need the correct instance size when materializing the object. The correct approach here should be to just initialize all the VirtualObject.


---

**#10 — dx...@google.com — Mar 24, 2025 08:04PM**

Project: v8/v8  
Branch: main  
Author: Victor Gomes [victorgomes@chromium.org](<mailto:victorgomes@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6386656](<https://chromium-review.googlesource.com/6386656>)

[maglev] Clear remaining slots for objects with slack

* * *

Expand for full commit details

```
     
    Fixed: 403600260 
    Change-Id: I3550af69e7f85bbef2ac0e33e94fdd7aae6130c0 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6386656 
    Reviewed-by: Olivier Flückiger <olivf@chromium.org> 
    Commit-Queue: Olivier Flückiger <olivf@chromium.org> 
    Auto-Submit: Victor Gomes <victorgomes@chromium.org> 
    Commit-Queue: Victor Gomes <victorgomes@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#99405}
```

* * *

Files:

  * M `src/maglev/maglev-graph-builder.cc`

* * *

Hash: 73f21fd09b6b2b9930dbed725bbbde78de4e1710  
Date: Mon Mar 24 10:33:22 2025

* * *


---

**#11 — se...@gmail.com — Mar 25, 2025 01:48AM**

Patch is insufficient, this is the bypass tested on `8b26aa3` (only the last line diff is important, others are for clarity):

```
@@ -60,7 +60,7 @@
 
 // spray data
 for (let i = 0; i < 3; i++) {
-  let spray = new BigUint64Array(Array(0x1000 * (1 << i)).fill(bs + 0x800n));
+  let spray = new BigUint64Array(Array(0x1000 * (1 << i)).fill(0x424242424242n));
   try {
     new WebAssembly.Module(spray.buffer);
   } catch {}
@@ -73,9 +73,9 @@
 // force !MapRef::IsInobjectSlackTrackingInProgress() for instance size simplification
 setField(pim, kMapBitField3Offset, getField(pim, kMapBitField3Offset) & ~(0x7 << 29));
 
-// overwrite instance_size_in_words = 0x0b, inobject_properties_start_or_constructor_function_index = 0x0b
+// overwrite instance_size_in_words = 0x0b, inobject_properties_start_or_constructor_function_index = 0x0c
 // last slot is uninit, fetched from spray data
-setField(pim, kMapInstanceSizeInWordsOffset, (getField(pim, kMapInstanceSizeInWordsOffset) & ~0xffff) | 0x0b0b);
+setField(pim, kMapInstanceSizeInWordsOffset, (getField(pim, kMapInstanceSizeInWordsOffset) & ~0xffff) | 0x0c0b);
 
 // trigger MaglevGraphBuilder::TryBuildAndAllocateJSGeneratorObject()
 for (let i = 0; i < 2000; i++) {
```

~~We can make`slack_tracking_prediction.inobject_property_count()` negative by providing more inobject properties than instance size, which will result in skipping the slot initialization at both the original for-loop and at the newly introduced `ClearSlots()` due to signedness issues.~~ See below for a better RCA.

* * *

#### Update:

If I'm not mistaken, it seems that the original PoC also still repros with the patch, just not with an obvious v8sbx violation due to offset differences? Applying only the first line diff of the above patch will repro as a v8sbx violation.

The check seems to trust `GetInObjectPropertyOffset()` which assumes that up to (but excluding) inobject property start is already all initialized, but this is a value loaded from `inobject_properties_start_or_constructor_function_index`. Thus any uninitialized values after the initial 10 slots (including map) will still be uninitialized. In the PoC we have 0xb slots so the last slot will still be left uninitialized.


---

**#12 — vi...@chromium.org — Mar 25, 2025 06:52PM**

Thanks for the heads up @seunghyun3288. I think negative `slack_tracking_prediction.inobject_property_count()` should be fine, right?

But we are relying on `GetInObjectPropertyOffset()`, which is based on `kInobjectPropertiesStartOrConstructorFunctionIndexOffset` from the map, which is _indeed_ unsafe.

Let me think about it...


---

**#13 — dx...@google.com — Mar 25, 2025 08:54PM**

Project: v8/v8  
Branch: main  
Author: Victor Gomes [victorgomes@chromium.org](<mailto:victorgomes@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6387758](<https://chromium-review.googlesource.com/6387758>)

[maglev] Always initialize all slots of a VirtualObject

* * *

Expand for full commit details

```
     
    Fixed: 403600260 
    Change-Id: I67fc56d50dbff40468435bcbc143fd715ab2bef9 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6387758 
    Reviewed-by: Olivier Flückiger <olivf@chromium.org> 
    Auto-Submit: Victor Gomes <victorgomes@chromium.org> 
    Commit-Queue: Olivier Flückiger <olivf@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#99441}
```

* * *

Files:

  * M `src/maglev/maglev-graph-builder.cc`

* * *

Hash: 3516747f87b9370e6865429707f50e5b3845ee68  
Date: Tue Mar 25 10:57:37 2025

* * *


---

**#14 — vi...@chromium.org — Mar 25, 2025 09:01PM**

@seunghyun3288, please do check if you can still break it. Thanks for the report!


---

**#15 — sp...@google.com — Apr 3, 2025 09:55AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $25000.00 for this report.  
  
Rationale for this decision:  
$20,000 for report of V8 sandbox bypass demonstrating the potential for code execution outside the V8 heap sandbox + $5,000 for identifying the insufficient initial patch to remediate   
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#16 — am...@chromium.org — Apr 3, 2025 10:11AM**

Congratulations Seunghyun! Thank you for your continued efforts against the V8 sandbox as well as catching another patch issue before it was closed out.


---

**#17 — ch...@google.com — Jul 2, 2025 09:42PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
