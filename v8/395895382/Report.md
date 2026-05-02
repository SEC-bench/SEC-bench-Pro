# V8 Sandbox Bypass: AAW via array length corruption in Turbofan spread call inlining

Issue URL: https://issues.chromium.org/issues/395895382
VRP-Reward: 20000
Date: Feb 12, 2025 05:48PM


### VULNERABILITY DETAILS

#### Summary

V8 sandbox bypass, arbitrary address write by corrupting `AllocationSite` boilerplate array literal length to a negative value. When this array is used with spread syntax for a call/construct argument, tier-up compilation of this code results in `JSCallReducer::ReduceCallOrConstructWithArrayLikeOrSpread()` to operate on out-of-bounds `Node*` input nodes / `Use*` chain. By spraying the heap with target addresses, we can trigger arbitrary writes on controlled address.

#### Details

For functions containing array literals, feedback collection caches the literal as an `AllocationSite` boilerplate:

```
// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/runtime/runtime-literals.cc;drc=80d0291f109d2b8349b264b45920fbd0616ba2e7;l=520
MaybeDirectHandle<JSObject> CreateLiteral(Isolate* isolate,
                                          Handle<HeapObject> maybe_vector,
                                          int literals_index,
                                          Handle<HeapObject> description,
                                          int flags) {
  if (!IsFeedbackVector(*maybe_vector)) {
    DCHECK(IsUndefined(*maybe_vector));
    return CreateLiteralWithoutAllocationSite<LiteralHelper>(                 // [!] no FeedbackVector yet
        isolate, description, flags);
  }
  auto vector = Cast<FeedbackVector>(maybe_vector);
  FeedbackSlot literals_slot(FeedbackVector::ToSlot(literals_index));
  CHECK(literals_slot.ToInt() < vector->length());
  Handle<Object> literal_site(Cast<Object>(vector->Get(literals_slot)),       // [!] check corresponding spot
                              isolate);
  Handle<AllocationSite> site;
  Handle<JSObject> boilerplate;

  if (HasBoilerplate(literal_site)) {
    site = Cast<AllocationSite>(literal_site);
    boilerplate = Handle<JSObject>(site->boilerplate(), isolate);             // [!] fetch boilerplate to copy
  } else {
    // Eagerly create AllocationSites for literals that contain an Array.
    bool needs_initial_allocation_site =
        (flags & AggregateLiteral::kNeedsInitialAllocationSite) != 0;
    if (!needs_initial_allocation_site &&
        IsUninitializedLiteralSite(*literal_site)) {
      PreInitializeLiteralSite(vector, literals_slot);
      return CreateLiteralWithoutAllocationSite<LiteralHelper>(
          isolate, description, flags);
    } else {
      boilerplate = LiteralHelper::Create(isolate, description, flags,        // [!] create array literal boilerplate
                                          AllocationType::kOld);
    }
    // Install AllocationSite objects.
    AllocationSiteCreationContext creation_context(isolate);
    site = creation_context.EnterNewScope();                                  // [!] create AllocationSite to cache the boilerplate array literal
    RETURN_ON_EXCEPTION(isolate, DeepWalk(boilerplate, &creation_context));
    creation_context.ExitScope(site, boilerplate);

    vector->SynchronizedSet(literals_slot, *site);                            // [!] save it back to FeedbackVector slot
  }
  // ...
}
```

This `AllocationSite` boilerplate feedback is later used for Turbofan tier-up compilation, specifically at `JSCallReducer::ReduceCallOrConstructWithArrayLikeOrSpread()` which as part of `InliningPhase` to process call/construct nodes with spread syntax, e.g. `fn(...arr)`. Below is the relevant part of the code:

```
// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/compiler/js-call-reducer.cc;drc=80d0291f109d2b8349b264b45920fbd0616ba2e7;l=4417
Reduction JSCallReducer::ReduceCallOrConstructWithArrayLikeOrSpread(
    Node* node, int argument_count, int arraylike_or_spread_index,
    CallFrequency const& frequency, FeedbackSource const& feedback_source,
    SpeculationMode speculation_mode, CallFeedbackRelation feedback_relation,
    Node* target, Effect effect, Control control) {
  // ...
  int new_argument_count;                                                         // [!] signed integer
  // ...
  // Find array length and elements' kind from the feedback's allocation
  // site's boilerplate JSArray.
  JSCreateLiteralOpNode args_node(arguments_list);
  CreateLiteralParameters const& args_params = args_node.Parameters();
  const FeedbackSource& array_feedback = args_params.feedback();
  const ProcessedFeedback& feedback =
      broker()->GetFeedbackForArrayOrObjectLiteral(array_feedback);
  if (feedback.IsInsufficient()) return NoChange();

  AllocationSiteRef site = feedback.AsLiteral().value();                          // [!] fetching feedback slot for AllocationSite
  if (!site.boilerplate(broker()).has_value()) return NoChange();

  JSArrayRef boilerplate_array = site.boilerplate(broker())->AsJSArray();         // [!] fetching boilerplate array literal
  int const array_length =
      boilerplate_array.GetBoilerplateLength(broker()).AsSmi();

  // We'll replace the arguments_list input with {array_length} element loads.
  new_argument_count = argument_count - 1 + array_length;
  // ...
  Node* elements = effect = graph()->NewNode(
      simplified()->LoadField(AccessBuilder::ForJSObjectElements()),
      arguments_list, effect, control);
  for (int i = 0; i < array_length; i++) {                                        // [!] input insertion skipped if array_length < 0
    // ...
    node->InsertInput(graph()->zone(), arraylike_or_spread_index + i, load);
  }

  NodeProperties::ChangeOp(
      node,
      javascript()->Call(JSCallNode::ArityForArgc(new_argument_count),            // [!] update arity and nodes
                         frequency, feedback_source, ConvertReceiverMode::kAny,
                         speculation_mode, CallFeedbackRelation::kUnrelated));
  NodeProperties::ReplaceEffectInput(node, effect);                               // [!] replace effect input
  return Changed(node).FollowedBy(ReduceJSCall(node));
}
```

**We see that once the boilerplate array literal is corrupted,`new_argument_count` computation may go wrong.** Notably, if it becomes negative the whole for-loop calling `node->InsertInput()` to emit array element loads in place of arguments is completely skipped.

The code then executes `NodeProperties::ChangeOp()`, replacing the node operation with the new `javascript()->Call(...)` which uses the corrupted argument count. This interestingly stores the argument count in a 27 bit wide bitfield, resulting in truncation once fetched back:

```
// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/compiler/js-operator.h;drc=80d0291f109d2b8349b264b45920fbd0616ba2e7;l=235
class CallParameters final {
 public:
  // ...
  CallParameters(size_t arity, CallFrequency const& frequency,
                 FeedbackSource const& feedback,
                 ConvertReceiverMode convert_mode,
                 SpeculationMode speculation_mode,
                 CallFeedbackRelation feedback_relation)
      : bit_field_(ArityField::encode(arity) /* ... more bitfields */),   // [!] arity stored in ArityField
        frequency_(frequency),
        feedback_(feedback) {
    // ...
  }
  // ...
  size_t arity() const { return ArityField::decode(bit_field_); }
  // ...
 private:
  friend size_t hash_value(CallParameters const& p) {
    FeedbackSource::Hash feedback_hash;
    return base::hash_combine(p.bit_field_, p.frequency_,
                              feedback_hash(p.feedback_));
  }

  using ArityField = base::BitField<size_t, 0, 27>;                       // [!] 27 bit wide
};

// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/compiler/js-operator.cc;drc=80d0291f109d2b8349b264b45920fbd0616ba2e7;l=882
const Operator* JSOperatorBuilder::Call(
    size_t arity, CallFrequency const& frequency,
    FeedbackSource const& feedback, ConvertReceiverMode convert_mode,
    SpeculationMode speculation_mode, CallFeedbackRelation feedback_relation) {
  CallParameters parameters(arity, frequency, feedback, convert_mode,
                            speculation_mode, feedback_relation);
  return zone()->New<Operator1<CallParameters>>(   // --
      IrOpcode::kJSCall, Operator::kNoProperties,  // opcode
      "JSCall",                                    // name
      parameters.arity(), 1, 1, 1, 1, 2,           // inputs/outputs      // [!] truncated arity as value_in
      parameters);                                 // parameter
}
```

This conveniently allows us to truncate the corrupted negative arity back to a positive value. We now continue on to `NodeProperties::ReplaceEffectInput(node, effect)`:

```
// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/compiler/node-properties.cc;drc=810a03bbcbf8aa449a483ce84eb85552606a9a8f;l=125
void NodeProperties::ReplaceEffectInput(Node* node, Node* effect, int index) {
  CHECK_LE(0, index);
  CHECK_LT(index, node->op()->EffectInputCount());                           // [!] RHS returns attacker-controlled value
  return node->ReplaceInput(FirstEffectIndex(node) + index, effect);         // [!] attacker-controlled value as input node index to be replaced
}

// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/compiler/node-properties.h;drc=80d0291f109d2b8349b264b45920fbd0616ba2e7;l=24
class V8_EXPORT_PRIVATE NodeProperties {
 public:
  // ---------------------------------------------------------------------------
  // Input layout.
  // Inputs are always arranged in order as follows:
  //     0 [ values, context, frame state, effects, control ] node->InputCount()

  static int FirstValueIndex(const Node* node) { return 0; }
  static int FirstContextIndex(Node* node) { return PastValueIndex(node); }  // [!] arity
  static int FirstFrameStateIndex(Node* node) { return PastContextIndex(node); }
  static int FirstEffectIndex(Node* node) { return PastFrameStateIndex(node); }
  static int FirstControlIndex(Node* node) { return PastEffectIndex(node); }

  static int PastValueIndex(Node* node) {
    return FirstValueIndex(node) + node->op()->ValueInputCount();
  }

  static int PastContextIndex(Node* node) {
    return FirstContextIndex(node) +
           OperatorProperties::GetContextInputCount(node->op());
  }

  static int PastFrameStateIndex(Node* node) {
    return FirstFrameStateIndex(node) +
           OperatorProperties::GetFrameStateInputCount(node->op());
  }

  static int PastEffectIndex(Node* node) {
    return FirstEffectIndex(node) + node->op()->EffectInputCount();
  }
  // ...
};
```

`FirstEffectIndex(node)` picks up the corrupted arity `node->op()->ValueInputCount()` and adds it to compute the result. This allows us to call `node->ReplaceInput()` with an arbitrary attacker-controlled index without the corresponding number of input nodes allocated. This finally results in out-of-bounds pointer fetch:

```
// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/compiler/node.h;drc=80d0291f109d2b8349b264b45920fbd0616ba2e7;l=77
  void ReplaceInput(int index, Node* new_to) {
    DCHECK_LE(0, index);
    DCHECK_LT(index, InputCount());
    ZoneNodePtr* input_ptr = GetInputPtr(index);
    Node* old_to = *input_ptr;                      // [!] oob pointer read
    if (old_to != new_to) {
      Use* use = GetUsePtr(index);                  // [!] oob pointer read
      if (old_to) old_to->RemoveUse(use);           // [!] arb. address write (use, old_to)
      *input_ptr = new_to;                          // [!] oob write
      if (new_to) new_to->AppendUse(use);           // [!] arb. address write (use)
    }
  }

// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/compiler/node.cc;drc=80d0291f109d2b8349b264b45920fbd0616ba2e7;l=419
void Node::RemoveUse(Use* use) {
  DCHECK(first_use_ == nullptr || first_use_->prev == nullptr);
  if (use->prev) {
    DCHECK_NE(first_use_, use);
    use->prev->next = use->next;                    // [!] arb. write
  } else {
    DCHECK_EQ(first_use_, use);
    first_use_ = use->next;                         // [!] arb. write
  }
  if (use->next) {
    use->next->prev = use->prev;                    // [!] arb. write
  }
}
```

By spraying pointers nearby on the heap and triggering this bug, we can cause an arbitrary write on attacker-controlled pointer.

### VERSION

V8: Tested on CF asan / no-asan sandbox-testing d8 @ revision 98615 (commit [1d65fd3](<https://chromium-review.googlesource.com/c/v8/v8/+/6227080>))

### REPRODUCTION CASE

Attached as `array-spread-call-tierup-inline-oob.js`, run with `./d8 --sandbox-testing` for non-ASAN builds which will attempt an arbitrary write to address `0x424242424242` (or sometimes crash while OOB reading target pointer). A fair amount of heap spray is involved (~4GB) so YMMV.

On ASAN builds, the repro will crash with an invalid memory access if run with `./d8 --expose-memory-corruption-api`, or otherwise will simply exit with a "harmless" memory permission violation.

### FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION

Type of crash: Sandbox violation

Crash state:

```
$ ./d8-sandbox-testing-linux-release-v8-component-98615/d8 --sandbox-testing ./array-spread-call-tierup-inline-oob.js 
Sandbox testing mode is enabled. Only sandbox violations will be reported, all other crashes will be ignored.
[*] spraying...
[*] spray 0 / 260 (0.00%)
[*] spray 16 / 260 (6.15%)
[*] spray 32 / 260 (12.31%)
[*] spray 48 / 260 (18.46%)
[*] spray 64 / 260 (24.62%)
[*] spray 80 / 260 (30.77%)
[*] spray 96 / 260 (36.92%)
[*] spray 112 / 260 (43.08%)
[*] spray 128 / 260 (49.23%)
[*] spray 144 / 260 (55.38%)
[*] spray 160 / 260 (61.54%)
[*] spray 176 / 260 (67.69%)
[*] spray 192 / 260 (73.85%)
[*] spray 208 / 260 (80.00%)
[*] spray 224 / 260 (86.15%)
[*] spray 240 / 260 (92.31%)
[*] spray 256 / 260 (98.46%)

## V8 sandbox violation detected!

Received signal 11 SEGV_MAPERR 424242424242

==== C stack trace ===============================

./d8-sandbox-testing-linux-release-v8-component-98615/d8(_ZN2v84base5debug10StackTraceC1Ev+0x13)[0x5c894ecbfae3]
./d8-sandbox-testing-linux-release-v8-component-98615/d8(+0x68caa5f)[0x5c894ecbfa5f]
/lib/x86_64-linux-gnu/libc.so.6(+0x42520)[0x7fe7b7242520]
./d8-sandbox-testing-linux-release-v8-component-98615/d8(_ZN2v88internal8compiler4Node9RemoveUseEPNS2_3UseE+0x10)[0x5c894e2d5d60]
./d8-sandbox-testing-linux-release-v8-component-98615/d8(_ZN2v88internal8compiler4Node12ReplaceInputEiPS2_+0x45)[0x5c894e16c865]
./d8-sandbox-testing-linux-release-v8-component-98615/d8(_ZN2v88internal8compiler13JSCallReducer42ReduceCallOrConstructWithArrayLikeOrSpreadEPNS1_4NodeEiiRKNS1_13CallFrequencyERKNS1_14FeedbackSourceENS0_15SpeculationModeENS1_20CallFeedbackRelationES4_NS1_6EffectENS1_7ControlE+0x68b)[0x5c894e1ff85b]
./d8-sandbox-testing-linux-release-v8-component-98615/d8(_ZN2v88internal8compiler13JSCallReducer22ReduceJSCallWithSpreadEPNS1_4NodeE+0xf3)[0x5c894e1f7c33]
./d8-sandbox-testing-linux-release-v8-component-98615/d8(_ZN2v88internal8compiler7Reducer6ReduceEPNS1_4NodeEPNS1_18ObserveNodeManagerE+0x19)[0x5c894e1d4579]
./d8-sandbox-testing-linux-release-v8-component-98615/d8(_ZN2v88internal8compiler12GraphReducer6ReduceEPNS1_4NodeE+0xaa)[0x5c894e1d4bca]
./d8-sandbox-testing-linux-release-v8-component-98615/d8(_ZN2v88internal8compiler12GraphReducer9ReduceTopEv+0x135)[0x5c894e1d49a5]
./d8-sandbox-testing-linux-release-v8-component-98615/d8(_ZN2v88internal8compiler12GraphReducer10ReduceNodeEPNS1_4NodeE+0x38)[0x5c894e1d4768]
./d8-sandbox-testing-linux-release-v8-component-98615/d8(_ZN2v88internal8compiler13InliningPhase3RunEPNS1_14TFPipelineDataEPNS0_4ZoneE+0x3e9)[0x5c894e319b69]
./d8-sandbox-testing-linux-release-v8-component-98615/d8(_ZN2v88internal8compiler12PipelineImpl3RunITkNS1_10turboshaft13TurbofanPhaseENS1_13InliningPhaseEJEEEDaDpOT0_+0x4f)[0x5c894e2e068f]
./d8-sandbox-testing-linux-release-v8-component-98615/d8(_ZN2v88internal8compiler12PipelineImpl11CreateGraphEPNS1_7LinkageE+0x68)[0x5c894e2de4f8]
./d8-sandbox-testing-linux-release-v8-component-98615/d8(_ZN2v88internal8compiler22PipelineCompilationJob14ExecuteJobImplEPNS0_16RuntimeCallStatsEPNS0_12LocalIsolateE+0xc8)[0x5c894e2de218]
./d8-sandbox-testing-linux-release-v8-component-98615/d8(_ZN2v88internal23OptimizedCompilationJob10ExecuteJobEPNS0_16RuntimeCallStatsEPNS0_12LocalIsolateE+0x37)[0x5c894d3fb327]
./d8-sandbox-testing-linux-release-v8-component-98615/d8(_ZN2v88internal27OptimizingCompileDispatcher11CompileNextEPNS0_22TurbofanCompilationJobEPNS0_12LocalIsolateE+0x35)[0x5c894d459315]
./d8-sandbox-testing-linux-release-v8-component-98615/d8(_ZN2v88internal27OptimizingCompileDispatcher11CompileTask17RunCompilationJobEPNS0_7IsolateERNS0_12LocalIsolateEPNS0_22TurbofanCompilationJobE+0x1a0)[0x5c894d45c9c0]
./d8-sandbox-testing-linux-release-v8-component-98615/d8(_ZN2v88internal27OptimizingCompileDispatcher11CompileTask3RunEPNS_11JobDelegateE+0x1a1)[0x5c894d45c711]
./d8-sandbox-testing-linux-release-v8-component-98615/d8(_ZN2v88platform16DefaultJobWorker3RunEv+0x72)[0x5c894ecc0fb2]
./d8-sandbox-testing-linux-release-v8-component-98615/d8(_ZN2v88platform30DefaultWorkerThreadsTaskRunner12WorkerThread3RunEv+0xc0)[0x5c894ecc43b0]
./d8-sandbox-testing-linux-release-v8-component-98615/d8(+0x68c6f25)[0x5c894ecbbf25]
/lib/x86_64-linux-gnu/libc.so.6(+0x94ac3)[0x7fe7b7294ac3]
/lib/x86_64-linux-gnu/libc.so.6(+0x126850)[0x7fe7b7326850]
[end of stack trace]
```

### CREDIT INFORMATION

Reporter credit: Seunghyun Lee (@0x10n) of CMU CyLab

* * *

This was discovered with a v8 sandbox fuzzer.


---

**#2 — se...@gmail.com — Feb 12, 2025 05:53PM**

A small update: `Use* use = GetUsePtr(index);` is not an immediate OOB pointer read but is an OOB reference to an array of `Use`. Once this lands on the heap spray `use->prev` and `use->next` is both `0x424242424242` resulting in arbitrary address/value write within `Node::RemoveUse()`.

* * *

Relevant to this in the PoC is the comment `// new_to offset: -idx * 3 * 8`, which should instead be `// Use offset: ...`

* * *

Also marking any rewards for charity in advance.


---

**#3 — th...@chromium.org — Feb 12, 2025 11:44PM**

Since this is a V8 sandbox bypass, setting a provisional severity of Medium (S2) + provisional priority of P1, assigning to the current V8 Sheriff sroettger@. Adding the Security_Impact-None hotlist and the V8 Sandbox hotlist.


---

**#4 — dx...@google.com — Apr 25, 2025 08:22PM**

Project: v8/v8  
Branch: main  
Author: Nico Hartmann [nicohartmann@chromium.org](<mailto:nicohartmann@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6478570](<https://chromium-review.googlesource.com/6478570>)

[turbofan] Fix Call argument count mismatch for array literals

* * *

Expand for full commit details

```
     
    When the boilerplate array literal length is corrupted inside the 
    AllocationSite, TurboFan can be tricked into emitting a Call node 
    where the operator's arity is set to a large number, while the node 
    doesn't have any actual inputs. During lowering, this can be exploited 
    to force TF into reading and writing at attacker controlled locations 
    (outside SB) when replacing node's inputs based on this corrupted arity. 
     
    Bug: 395895382 
    Change-Id: Ic4770ab81c11d617ac4826a745eda647c7d72332 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6478570 
    Commit-Queue: Nico Hartmann <nicohartmann@chromium.org> 
    Reviewed-by: Samuel Groß <saelo@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#99913}
```

* * *

Files:

  * M `src/compiler/js-call-reducer.cc`

* * *

Hash: da14a949b0dc122c848f556b9e89ab1064a73306  
Date: Fri Apr 25 08:59:10 2025

* * *


---

**#5 — sp...@google.com — May 3, 2025 03:55AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $20000.00 for this report.  
  
Rationale for this decision:  
V8 sandbox bypass demonstrating arbitrary write outside of the heap sandbox  
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#6 — ch...@google.com — Aug 2, 2025 09:52PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
