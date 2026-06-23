# WasmGCTypeAnalyzer improperly revisits single-block loops, leading to type confusion

Issue URL: https://issues.chromium.org/issues/383356864
VRP-Reward: 55000
Date: Dec 11, 2024 10:28PM


`WasmGCTypeAnalyzer` is a Turboshaft analyzer responsible for inferring known type information for various operations, which can then be used by `WasmGCTypedOptimizationReducer` to potentially remove some type checks at compile time. To do this, it traverses the Turboshaft graph while keeping track of which types might be encountered at any particular point in the code. When encountering a loop, the analyzer keeps revisiting the loop body indefinitely until the type feedback stabilizes - this is intended to ensure that the loop backedge's type feedback is properly accounted for. The analyzer revisits the loop's body by calling `iterator.MarkLoopForRevisitSkipHeader()` \- the loop header has already been revisited while trying to determine whether the type feedback stabilized, so it is skipped here, presumably as an optimization.

However, this assumption / optimization doesn't account for single-block loops, which can occur in the Turboshaft graph when compiling infinite loops without any branches. For these loops, the loop header contains the entire loop body, effectively turning `iterator.MarkLoopForRevisitSkipHeader()` into a No-Op, and preventing the loop from being revisited any additional times. This cuts the fixed-point analysis short after two iterations: one initial visit, and one additional visit as part of the check to determine whether the type feedback stabilized. As such, `WasmGCTypeAnalyzer` might report incorrect type feedback to `WasmGCTypedOptimizationReducer` when the loop's type information does not stabilize after two iterations (which can be the case because of, for example, a chain of Phis), which can lead to type checks being incorrectly removed, resulting in type confusion.

See attached two files:

  * `poc.js`: this contains a minimal POC which utilizes this bug to create and dereference a fake object, resulting in a crash. This POC has been reproduced with an D8 optdebug build (commit `86ffa19a533bdec3b9ce4a56106a2d9e8015e108`) on an x86-64 Linux machine.
  * `exploit.js`: this contains a full Chromium exploit chain, utilizing this bug + unprotected PartitionAlloc metadata to demonstrate an attacker controlled write outside of the sandbox. This exploit has been tested and confirmed to work on Chromium 131.0.6778.108 on an x86-64 Linux machine, using `--js-flags="--turboshaft-wasm"` to enable Turboshaft for Wasm. Note that this class of sandbox escape (namely manipulating exposed `SlotSpanMetadata` objects) has been used in other exploit chains to achieve full RCE; this exploit stops short of achieving RCE, only demonstrating attacker controlled writes, since further exploitation requires hardcoding offsets for specific Chromium builds, which reduces the general reproducibility and reliability of the exploit.

A potential fix for this bug would be to not use `MarkLoopForRevisitSkipHeader` for revisiting single block loops, and instead use `MarkLoopForRevisit` for this particular edge case. A sample patch of such a fix could look as follows:

```
@@ -61,8 +61,14 @@ void WasmGCTypeAnalyzer::Run() {
         if (needs_revisit) {
           block_to_snapshot_[loop_header.index()] = MaybeSnapshot(snapshot);
           // This will push the successors of the loop header to the iterator
-          // stack, so the loop body will be visited in the next iteration.
-          iterator.MarkLoopForRevisitSkipHeader();
+          // stack, so the loop body will be visited in the next iteration. If
+          // this is a single-block loop, then there are no successors - as such
+          // revisit the entire loop (consisting of just the header) in this
+          // case.
+          if (block.index() != header.index()) {
+            iterator.MarkLoopForRevisitSkipHeader();
+          } else {
+            iterator.MarkLoopForRevisit();
+          }
         }
       }
     }
```

Reporter Credit: if applicable, please credit my pseudonym Popax21 in regards to this report.


---

**#2 — ma...@gmail.com — Dec 12, 2024 05:29AM**

A quick sidenote regarding impact (since I accidentally forgot said information while composing my original report; sorry for the hassle): In V8, the `--turboshaft-wasm` flag has been enabled by default since Oct. 13 (commit `b34e0aa98b28bfbf07b1f8a2a1ec89f8ac89e21c`), and the ability to turn it off has been removed last week when the flag was made readonly in commit `14c7a5614d6cd8ccc4b55360ae590e76714b5597`.

The bug's impact in the context of Chromium is more complicated: [issue 382509286](<https://issues.chromium.org/issues/382509286>), which made the feature flag readonly, mentions the following:

> The flag is enabled by default in M-133 (and shipped via finch in M-130).

However, the associated Finch trial, `V8WasmTurboshaft`, currently assigns a 100% probability of enabling this feature to all Chrome releases since M-128. This means all Chromium builds from embedders which utilize Finch since M-128 (branch cut on Jul. 22, Chrome stable release on Aug. 20 [^1]), as well as all builds which are based of the soon-to-be-released M-133 (expected branch cut on Jan. 6 2025, expected Chrome stable release on Feb. 4 2025 [^1]), regardless of if they use Finch or not, are affected and exploitable using this bug. Note that all current canary builds should be affected as well, since they are also based of M-133.

I've since then also tested my exploit against a stable release of Google Chrome inside of this range (namely 131.0.6778.108). As expected, the exploit works just fine, without the need to enable any additional feature flags.

[^1]: version branch cut / release dates are taken from [https://chromiumdash.appspot.com/schedule](<https://chromiumdash.appspot.com/schedule>)


---

**#3 — cl...@appspot.gserviceaccount.com — Dec 12, 2024 10:46AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5622350724661248](<https://clusterfuzz.com/testcase?key=5622350724661248>).


---

**#4 — 24...@project.gserviceaccount.com — Dec 12, 2024 11:59AM**

Detailed Report: [https://clusterfuzz.com/testcase?key=5622350724661248](<https://clusterfuzz.com/testcase?key=5622350724661248>)  
  
Fuzzer: None  
Job Type: linux_asan_d8_dbg  
Platform Id: linux  
  
Crash Type: UNKNOWN READ  
Crash Address: 0x77cb00012340  
Crash State:  
Builtins_JSToWasmHandleReturns  
Builtins_JSToWasmWrapperAsm  
Builtins_JSToWasmWrapper  
  
Sanitizer: address (ASAN)  
  
Recommended Security Severity: Medium  
  
Regressed: [https://clusterfuzz.com/revisions?job=linux_asan_d8_dbg&range=96789:96790](<https://clusterfuzz.com/revisions?job=linux_asan_d8_dbg&range=96789:96790>)  
  
Reproducer Testcase: [https://clusterfuzz.com/download?testcase_id=5622350724661248](<https://clusterfuzz.com/download?testcase_id=5622350724661248>)  
  
To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.   
  
If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.  
  
If you have any feedback on reproducing test cases, let us know at [https://forms.gle/Yh3qCYFveHj6E5jz5](<https://forms.gle/Yh3qCYFveHj6E5jz5>) so we can improve.  
  
  
A recommended severity was added to this bug. Please change the severity if it is inaccurate.


---

**#5 — 24...@project.gserviceaccount.com — Dec 12, 2024 12:14PM**

Automatically applying components based on crash stacktrace and information from OWNERS files.  
  
If this is incorrect, please apply the hotlistid:4801165.


---

**#6 — ml...@chromium.org — Dec 12, 2024 08:21PM**

Wow, this is a great finding, thanks a lot for the report!

> This cuts the fixed-point analysis short after two iterations: one initial visit, and one additional visit as part of the check to determine whether the type feedback stabilized.

This is done by design. When having a single loop, the analysis is designed to not need more than two iterations. With nested loops, this gets slightly more complicated but mainly because of the option of nested loops it is very relevant for compile time to not perform a slowly progressing fixed-point iteration here.

I have slightly simplified the reproducer (by using an explicit flag to disable loop unrolling) and I can see the following tracing with `--wasm-trace-typer`:

```
[b9] Reprocessing loop header b9 at backedge #76
[b9] Predecessors reachability: b9, b8
[b9] #61(Phi): Refine type for object #61(Phi) -> anyref
- phi input 0: #3(Parameter) -> anyref
- phi input 1: #3(Parameter) -> anyref
[b9] #62(Phi): Refine type for object #62(Phi) -> anyref
- phi input 0: #33(WasmAllocateStruct) -> (ref 0)
- phi input 1: #61(Phi) -> anyref
[b9] #63(Phi): Refine type for object #63(Phi) -> (ref 0)
- phi input 0: #33(WasmAllocateStruct) -> (ref 0)
- phi input 1: #62(Phi) -> (ref 0)
```

We can clearly see the nested phis being analyized here and it infers correctly that `#62` is `anyref` and then we get to the next phi, it looks up the known type and says "`#62` is a `(ref 0)`!"

[Here](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/compiler/turboshaft/wasm-gc-typed-optimization-reducer.cc;l=328;drc=9b4a12838ad376d3f06a6f102b448e7e49555d05>) is the code where the bug seems to be:

```
  for (int i = 1; i < phi.input_count; ++i) {
    wasm::ValueType input_type =
        types_table_.GetPredecessorValue(ResolveAliases(phi.input(i)), i);
```

For precisely refining phi types, we need to check their type based on the input edge that phi input belongs to. This works correctly as long as that input has the correct type at the predecessor. In this case, the input to that phi doesn't come from that predecessor, it is located in the same block before the phi we are looking at.

The refined values are only "snapshotted" at the end of the block, so when we do the `GetPredecessorValue`, we don't see the updated value yet.

I think we need to special-case this situation for phi inputs whose definition is located in the same block and located prior to the phi (which should also mean that the input has to be a phi itself as no other instruction may appear in front of a phi in a block afaik).

I'll take a look into how to fix this properly.


---

**#7 — ml...@chromium.org — Dec 12, 2024 10:15PM**

I also talked with Nico who confirmed that this special case of having a phi as input into another phi in the same block where the input is defined before the phi can only happen in single-block-loops (and only as an input for the back-edge).

Fix: [https://crrev.com/c/6087921](<https://crrev.com/c/6087921>)

Unfortunately I'm not quite sure how to build a nice test case for something that requires testing that running an endless loop doesn't cause a crash.


---

**#8 — ml...@chromium.org — Dec 12, 2024 10:22PM**

I don't know if we could also have an issue in the [maglev-graph-building-phase](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/compiler/turboshaft/maglev-graph-building-phase.cc;l=5532;drc=3f054e77a5dd5ce209cb4b449ddbad15ddb71db2>):

```
      if (__ current_block()->Contains(generator_context)) {
        DCHECK(!__ current_block()->IsLoop());
        DCHECK(__ output_graph().Get(generator_context).Is<PhiOp>());
        // If {generator_context} is a Phi defined in the current block and it's
        // used as input for another Phi, then we need to use it's value from
        // the correct predecessor, since a Phi can't be an input to another Phi
        // in the same block.
        return __ GetPredecessorValue(generator_context_, input_index);
      }
```

(Or at least the comment is slightly inaccurate.)

That is however experimental code and it could be that such a pattern is impossible when creating a Turboshaft graph from a Maglev graph.

Darius / Nico: Could you verify whether this is an issue?


---

**#9 — sa...@google.com — Dec 12, 2024 10:28PM**

Thanks for the great report! IIUC, the V8 Sandbox bypass should be fixed by [PartitionAlloc's Shadow Metadata feature](<https://crbug.com/40238514>) which is currently being rolled out, but isn't active on M131 yet.


---

**#10 — ap...@google.com — Dec 12, 2024 10:50PM**

Project: v8/v8  
Branch: main  
Author: Matthias Liedtke <[mliedtke@chromium.org](<mailto:mliedtke@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6087921](<https://chromium-review.googlesource.com/6087921>)

[turboshaft][wasm] WasmGCTypeAnalyzer: Fix phi input for single-block loops

* * *

Expand for full commit details

```
[turboshaft][wasm] WasmGCTypeAnalyzer: Fix phi input for single-block loops 
 
Fixed: 383356864 
Change-Id: Idc644923c2e09e16b0c4c1cb1cda8f5c3d8189d9 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6087921 
Reviewed-by: Jakob Kummerow <jkummerow@chromium.org> 
Reviewed-by: Nico Hartmann <nicohartmann@chromium.org> 
Commit-Queue: Matthias Liedtke <mliedtke@chromium.org> 
Cr-Commit-Position: refs/heads/main@{#97723}
```

* * *

Files:

  * M `src/compiler/turboshaft/wasm-gc-typed-optimization-reducer.cc`
  * M `src/compiler/turboshaft/wasm-gc-typed-optimization-reducer.h`

* * *

Hash: f231d83cb3c08754413b3ee1aa249cebd4d5445f  
Date: Thu Dec 12 14:11:00 2024

* * *


---

**#11 — ml...@chromium.org — Dec 12, 2024 10:51PM**

Regarding the Maglev graph building phase: I have created [issue 383661629](<https://issues.chromium.org/issues/383661629>) to make sure that we don't lose track of this. (Access-restricted as it contains some information about this issue.)


---

**#12 — pe...@google.com — Dec 13, 2024 12:40AM**

Setting milestone because of s0/s1 severity.


---

**#13 — pe...@google.com — Dec 13, 2024 12:44AM**

Security Merge Request Consideration: This is sufficiently serious that it should be merged to extended stable. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M130. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately. Security Merge Request Consideration: This is sufficiently serious that it should be merged to stable. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M131. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately. Security Merge Request Consideration: This is sufficiently serious that it should be merged to beta. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M132. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately. Security Merge Request: Thank you for fixing this security bug! We aim to ship security fixes as quickly as possible, to limit their opportunity for exploitation as an "n-day" (that is, a bug where git fixes are developed into attacks before those fixes reach users).

We have determined this fix is necessary on milestone(s): [].

Please answer the following questions so that we can safely process this merge request:

  1. Which CLs should be backmerged? (Please include Gerrit links.)
  2. Has this fix been verified on Canary to not pose any stability regressions?
  3. Does this fix pose any potential non-verifiable stability risks?
  4. Does this fix pose any known compatibility risks?
  5. Does it require manual verification by the test team? If so, please describe required testing.
  6. (no answer required) Please check the OS custom field to ensure all impacted OSes are checked!


---

**#14 — ma...@gmail.com — Dec 13, 2024 03:40AM**

Thanks for the quick turnaround! I did some more testing, and it turns out the fix mentioned here is easily bypassable by just inverting the order the variables are declared in - this inverts the order of the phis as well, resulting in the conditions of the new edge case check not being true anymore (see the attached updated POC). In general, this fix breaks whenever the type information doesn't flow strictly downwards throughout the block, which is not guaranteed since the order of the phi instructions is attacker controlled; as such fully fixing this vulnerability requires that earlier phis can be revisited an arbitrary number of times, since type information might flow backwards to a phi earlier in the same block at any time. Given that I'm not sure that a fix consisting of just an edge case when handling Phi inputs can be sufficient, unless `ProcessOperations` gains the ability to "rewind" to an earlier instruction.


---

**#15 — 24...@project.gserviceaccount.com — Dec 13, 2024 04:28PM**

ClusterFuzz testcase 5622350724661248 is verified as fixed in [https://clusterfuzz.com/revisions?job=linux_asan_d8_dbg&range=97722:97723](<https://clusterfuzz.com/revisions?job=linux_asan_d8_dbg&range=97722:97723>)  
  
If this is incorrect, please add the hotlistid:5433040 and re-open the issue.


---

**#16 — cl...@appspot.gserviceaccount.com — Dec 13, 2024 06:09PM**

Detailed Report: [https://clusterfuzz.com/testcase?key=5105311287279616](<https://clusterfuzz.com/testcase?key=5105311287279616>)  
  
Fuzzer: None  
Job Type: linux_asan_d8_dbg  
Platform Id: linux  
  
Crash Type: UNKNOWN READ  
Crash Address: 0x7ea400012340  
Crash State:  
Builtins_JSToWasmHandleReturns  
Builtins_JSToWasmWrapperAsm  
Builtins_JSToWasmWrapper  
  
Sanitizer: address (ASAN)  
  
Recommended Security Severity: Medium  
  
Crash Revision: [https://clusterfuzz.com/revisions?job=linux_asan_d8_dbg&revision=97732](<https://clusterfuzz.com/revisions?job=linux_asan_d8_dbg&revision=97732>)  
  
Reproducer Testcase: [https://clusterfuzz.com/download?testcase_id=5105311287279616](<https://clusterfuzz.com/download?testcase_id=5105311287279616>)  
  
To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.   
  
If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.  
  
If you have any feedback on reproducing test cases, let us know at [https://forms.gle/Yh3qCYFveHj6E5jz5](<https://forms.gle/Yh3qCYFveHj6E5jz5>) so we can improve.


---

**#17 — ml...@chromium.org — Dec 13, 2024 10:47PM**

WIP fix: [https://chromium-review.googlesource.com/c/v8/v8/+/6092870](<https://chromium-review.googlesource.com/c/v8/v8/+/6092870>)

This now does exactly what was proposed in [comment #1](<https://issues.chromium.org/issues/383356864#comment1>).

I agree that we can't do anything else to prevent the fixed point iteration. We could make all loop phis pessimistic e.g. if one revisit isn't enough by marking the input types as "top" for any loop phi. Anything that isn't a loop phi can't generate the need to revisit the loop. This makes the generated code less optimal in certain conditions which however would probably be more than acceptable.

However, implementing this - while it sounds trivial - might have other side effects which I haven't considered yet, so it would be a much riskier change. This could be explored in the future and there is already a `TODO` in the code to anyways re-evaluate the fixed point iteration in the type analyzer.


---

**#18 — pe...@google.com — Dec 13, 2024 10:58PM**

Merge review required: M132 is already shipping to beta.

Please answer the following questions so that we can safely process your merge request:

  1. Why does your merge fit within the merge criteria for these milestones?

  * Chrome Browser: [https://chromiumdash.appspot.com/branches](<https://chromiumdash.appspot.com/branches>)
  * Chrome OS: [https://goto.google.com/cros-release-branch-merge-guidelines](<https://goto.google.com/cros-release-branch-merge-guidelines>)

  2. What changes specifically would you like to merge? Please link to Gerrit.
  3. Have the changes been released and tested on canary?
  4. Is this a new feature? If yes, is it behind a Finch flag and are experiments active in any release channels?
  5. [Chrome OS only]: Was the change reviewed and approved by the Eng Prod Representative? [https://goto.google.com/cros-engprodcomponents](<https://goto.google.com/cros-engprodcomponents>)
  6. If this merge addresses a major issue in the stable channel, does it require manual verification by the test team? If so, please describe required testing.

Please contact the milestone owner if you have questions. Owners: govind (Android), govind (iOS), alonbajayo (ChromeOS), srinivassista (Desktop)


---

**#19 — pe...@google.com — Dec 13, 2024 10:58PM**

Merge review required: M131 is already shipping to stable.

Please answer the following questions so that we can safely process your merge request:

  1. Why does your merge fit within the merge criteria for these milestones?

  * Chrome Browser: [https://chromiumdash.appspot.com/branches](<https://chromiumdash.appspot.com/branches>)
  * Chrome OS: [https://goto.google.com/cros-release-branch-merge-guidelines](<https://goto.google.com/cros-release-branch-merge-guidelines>)

  2. What changes specifically would you like to merge? Please link to Gerrit.
  3. Have the changes been released and tested on canary?
  4. Is this a new feature? If yes, is it behind a Finch flag and are experiments active in any release channels?
  5. [Chrome OS only]: Was the change reviewed and approved by the Eng Prod Representative? [https://goto.google.com/cros-engprodcomponents](<https://goto.google.com/cros-engprodcomponents>)
  6. If this merge addresses a major issue in the stable channel, does it require manual verification by the test team? If so, please describe required testing.

Please contact the milestone owner if you have questions. Owners: harrysouders (Android), harrysouders (iOS), obenedict (ChromeOS), pbommana (Desktop)


---

**#20 — pe...@google.com — Dec 13, 2024 10:58PM**

Merge review required: M130 is already shipping to stable.

Please answer the following questions so that we can safely process your merge request:

  1. Why does your merge fit within the merge criteria for these milestones?

  * Chrome Browser: [https://chromiumdash.appspot.com/branches](<https://chromiumdash.appspot.com/branches>)
  * Chrome OS: [https://goto.google.com/cros-release-branch-merge-guidelines](<https://goto.google.com/cros-release-branch-merge-guidelines>)

  2. What changes specifically would you like to merge? Please link to Gerrit.
  3. Have the changes been released and tested on canary?
  4. Is this a new feature? If yes, is it behind a Finch flag and are experiments active in any release channels?
  5. [Chrome OS only]: Was the change reviewed and approved by the Eng Prod Representative? [https://goto.google.com/cros-engprodcomponents](<https://goto.google.com/cros-engprodcomponents>)
  6. If this merge addresses a major issue in the stable channel, does it require manual verification by the test team? If so, please describe required testing.

Please contact the milestone owner if you have questions. Owners: eakpobaro (Android), eakpobaro (iOS), gmpritchard (ChromeOS), danielyip (Desktop)


---

**#21 — ml...@chromium.org — Dec 13, 2024 11:09PM**

Re-assigning to Jakob for performing the back-merges.

The CLs needed to back-merge are:

  1. [https://chromium-review.googlesource.com/c/v8/v8/+/6087921](<https://chromium-review.googlesource.com/c/v8/v8/+/6087921>)
  2. [https://chromium-review.googlesource.com/c/v8/v8/+/6092870](<https://chromium-review.googlesource.com/c/v8/v8/+/6092870>) (not landed yet)


---

**#22 — ma...@gmail.com — Dec 15, 2024 06:17AM**

I've performed some more testing, and can confirm that versions as far back as 128.0.6613.84 (released on Aug. 21) are affected, confirming my initial estimate based on the relevant Finch configuration data.


---

**#23 — am...@chromium.org — Dec 17, 2024 02:58AM**

[https://crrev.com/c/6087921](<https://crrev.com/c/6087921>) and [https://crrev.com/c/6092870](<https://crrev.com/c/6092870>) approved for merges; please merge asap to be included in next respective updates;   
given the timing of when these changes were landed, if merged to 13.1 and 13.0 immediately, these fixes will shipped in this week's update of Stable and Extended Stable before release freeze beginning this Friday (20 December), otherwise they will ship in the first updates following release freeze on the first Tuesday in January


---

**#24 — ap...@google.com — Dec 17, 2024 05:04AM**

Project: v8/v8  
Branch: refs/branch-heads/13.1  
Author: Matthias Liedtke <[mliedtke@chromium.org](<mailto:mliedtke@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6097631](<https://chromium-review.googlesource.com/6097631>)

Merged: [turboshaft][wasm] WasmGCTypeAnalyzer: Fix phi input for single-block loops

* * *

Expand for full commit details

```
Merged: [turboshaft][wasm] WasmGCTypeAnalyzer: Fix phi input for single-block loops 
 
Fixed: 383356864 
(cherry picked from commit f231d83cb3c08754413b3ee1aa249cebd4d5445f) 
 
Change-Id: Id9b88581b62c22fdeff2fbb69d9331e17d076244 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6097631 
Auto-Submit: Jakob Kummerow <jkummerow@chromium.org> 
Reviewed-by: Eva Herencsárová <evih@chromium.org> 
Commit-Queue: Eva Herencsárová <evih@chromium.org> 
Commit-Queue: Jakob Kummerow <jkummerow@chromium.org> 
Cr-Commit-Position: refs/branch-heads/13.1@{#38} 
Cr-Branched-From: 7998da66cb2883ef9734743857713b1194212d9a-refs/heads/13.1.201@{#1} 
Cr-Branched-From: 5e9af2a913539cf67091def99b62f49afece6f56-refs/heads/main@{#96554}
```

* * *

Files:

  * M `src/compiler/turboshaft/wasm-gc-typed-optimization-reducer.cc`
  * M `src/compiler/turboshaft/wasm-gc-typed-optimization-reducer.h`

* * *

Hash: 576543f81afd0d75fbd11d61b3b313e864d7ce48  
Date: Thu Dec 12 14:11:00 2024

* * *


---

**#25 — ap...@google.com — Dec 17, 2024 05:04AM**

Project: v8/v8  
Branch: refs/branch-heads/13.2  
Author: Matthias Liedtke <[mliedtke@chromium.org](<mailto:mliedtke@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6097630](<https://chromium-review.googlesource.com/6097630>)

Merged: [turboshaft][wasm] WasmGCTypeAnalyzer: Fix phi input for single-block loops

* * *

Expand for full commit details

```
Merged: [turboshaft][wasm] WasmGCTypeAnalyzer: Fix phi input for single-block loops 
 
Fixed: 383356864 
(cherry picked from commit f231d83cb3c08754413b3ee1aa249cebd4d5445f) 
 
Change-Id: I6a4a406d89d09b5ade3d5a5252a5b8921b8919a9 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6097630 
Auto-Submit: Jakob Kummerow <jkummerow@chromium.org> 
Commit-Queue: Jakob Kummerow <jkummerow@chromium.org> 
Reviewed-by: Eva Herencsárová <evih@chromium.org> 
Commit-Queue: Eva Herencsárová <evih@chromium.org> 
Cr-Commit-Position: refs/branch-heads/13.2@{#42} 
Cr-Branched-From: 24068c59cedad9ee976ddc05431f5f497b1ebd71-refs/heads/13.2.152@{#1} 
Cr-Branched-From: 6054ba94db0969220be4f94dc1677fc4696bdc4f-refs/heads/main@{#97085}
```

* * *

Files:

  * M `src/compiler/turboshaft/wasm-gc-typed-optimization-reducer.cc`
  * M `src/compiler/turboshaft/wasm-gc-typed-optimization-reducer.h`

* * *

Hash: 52f0e1b20997e35f04851bb09a688ecee4f21ddf  
Date: Thu Dec 12 14:11:00 2024

* * *


---

**#26 — ap...@google.com — Dec 17, 2024 05:12AM**

Project: v8/v8  
Branch: refs/branch-heads/13.0  
Author: Jakob Kummerow <[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6097632](<https://chromium-review.googlesource.com/6097632>)

Merged: [turboshaft][wasm] WasmGCTypeAnalyzer: Fix phi input for single-block loops

* * *

Expand for full commit details

```
Merged: [turboshaft][wasm] WasmGCTypeAnalyzer: Fix phi input for single-block loops 
 
Fixed: 383356864 
(cherry picked from commit f231d83cb3c08754413b3ee1aa249cebd4d5445f) 
 
Change-Id: I3247f6071a9a27eaef49ae8981b7eea93f83dc55 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6097632 
Reviewed-by: Eva Herencsárová <evih@chromium.org> 
Auto-Submit: Jakob Kummerow <jkummerow@chromium.org> 
Commit-Queue: Eva Herencsárová <evih@chromium.org> 
Commit-Queue: Jakob Kummerow <jkummerow@chromium.org> 
Cr-Commit-Position: refs/branch-heads/13.0@{#45} 
Cr-Branched-From: 4be854bd71ea878a25b236a27afcecffa2e29360-refs/heads/13.0.245@{#1} 
Cr-Branched-From: 1f5183f7ad6cca21029fd60653d075730c644432-refs/heads/main@{#96103}
```

* * *

Files:

  * M `src/compiler/turboshaft/wasm-gc-typed-optimization-reducer.cc`
  * M `src/compiler/turboshaft/wasm-gc-typed-optimization-reducer.h`

* * *

Hash: e1b6fb9242219edefc9d6efb093868b7897c9aec  
Date: Mon Dec 16 20:34:29 2024

* * *


---

**#27 — pe...@google.com — Dec 17, 2024 05:15AM**

LTS Milestone M126

This issue has been flagged as a merge candidate for Chrome OS' LTS channel. If selected, our merge team will handle any additional merges. To help us determine if this issue requires a merge to LTS, please answer this short questionnaire:

  1. Was this issue a regression for the milestone it was found in?
  2. Is this issue related to a change or feature merged after the latest LTS Milestone?


---

**#28 — ap...@google.com — Dec 17, 2024 05:20AM**

Project: v8/v8  
Branch: refs/branch-heads/13.0  
Author: Jakob Kummerow <[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6097772](<https://chromium-review.googlesource.com/6097772>)

Merged: [turboshaft][wasm] WasmGCTypeAnalyzer: Fix single-block loops properly

* * *

Expand for full commit details

```
Merged: [turboshaft][wasm] WasmGCTypeAnalyzer: Fix single-block loops properly 
 
While https://crrev.com/c/6087921 fixed a bug where the type in the 
loop header revisit was reflecting "older" knowledge, it didn't address 
the general issue of loop phis dependencies in single block loops where 
it might require many iterations until all type information has 
stabilized. 
 
The fix linked above also introduce too specific DCHECKs, as even 
outside of single-block loops we can end up with phis where a phi input 
appears in the same block before the phi itself. 
The binaryen fuzzer found the following pattern: 
  v113 = Phi(v26, v113) 
  v114 = Phi(v26, v113) 
 
In follow-up changes it should be ensured that the useless phi v113 
doesn't get emitted, then v114 wouldn't have that issue (and it could 
also be removed.) 
 
(cherry picked from commit c84e01e92bfd61d29541c59e378b9a15ba6fc891) 
 
Fixed: 383356864 
Bug: 383814042 
Change-Id: I222dc493bf0a2613d14ebb7df2bdeca931c8daa6 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6097772 
Auto-Submit: Jakob Kummerow <jkummerow@chromium.org> 
Commit-Queue: Eva Herencsárová <evih@chromium.org> 
Reviewed-by: Eva Herencsárová <evih@chromium.org> 
Commit-Queue: Jakob Kummerow <jkummerow@chromium.org> 
Cr-Commit-Position: refs/branch-heads/13.0@{#47} 
Cr-Branched-From: 4be854bd71ea878a25b236a27afcecffa2e29360-refs/heads/13.0.245@{#1} 
Cr-Branched-From: 1f5183f7ad6cca21029fd60653d075730c644432-refs/heads/main@{#96103}
```

* * *

Files:

  * M `src/compiler/turboshaft/wasm-gc-typed-optimization-reducer.cc`

* * *

Hash: 6661a068e593bd8b5a0b5bee7f9e80a2dc920292  
Date: Mon Dec 16 20:41:57 2024

* * *


---

**#29 — ap...@google.com — Dec 17, 2024 05:44AM**

Project: v8/v8  
Branch: refs/branch-heads/13.1  
Author: Matthias Liedtke <[mliedtke@chromium.org](<mailto:mliedtke@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6097633](<https://chromium-review.googlesource.com/6097633>)

Merged: [turboshaft][wasm] WasmGCTypeAnalyzer: Fix single-block loops properly

* * *

Expand for full commit details

```
Merged: [turboshaft][wasm] WasmGCTypeAnalyzer: Fix single-block loops properly 
 
While https://crrev.com/c/6087921 fixed a bug where the type in the 
loop header revisit was reflecting "older" knowledge, it didn't address 
the general issue of loop phis dependencies in single block loops where 
it might require many iterations until all type information has 
stabilized. 
 
The fix linked above also introduce too specific DCHECKs, as even 
outside of single-block loops we can end up with phis where a phi input 
appears in the same block before the phi itself. 
The binaryen fuzzer found the following pattern: 
  v113 = Phi(v26, v113) 
  v114 = Phi(v26, v113) 
 
In follow-up changes it should be ensured that the useless phi v113 
doesn't get emitted, then v114 wouldn't have that issue (and it could 
also be removed.) 
 
Fixed: 383356864 
Bug: 383814042 
(cherry picked from commit c84e01e92bfd61d29541c59e378b9a15ba6fc891) 
 
Change-Id: Ia6fbfcf89facdd273e3b9038bd710edd8ec0a39a 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6097633 
Commit-Queue: Jakob Kummerow <jkummerow@chromium.org> 
Auto-Submit: Jakob Kummerow <jkummerow@chromium.org> 
Commit-Queue: Eva Herencsárová <evih@chromium.org> 
Reviewed-by: Eva Herencsárová <evih@chromium.org> 
Cr-Commit-Position: refs/branch-heads/13.1@{#40} 
Cr-Branched-From: 7998da66cb2883ef9734743857713b1194212d9a-refs/heads/13.1.201@{#1} 
Cr-Branched-From: 5e9af2a913539cf67091def99b62f49afece6f56-refs/heads/main@{#96554}
```

* * *

Files:

  * M `src/compiler/turboshaft/wasm-gc-typed-optimization-reducer.cc`

* * *

Hash: e606275980b9b0192d26115a77bd5bf37e49a07f  
Date: Fri Dec 13 14:20:14 2024

* * *


---

**#30 — ap...@google.com — Dec 17, 2024 05:44AM**

Project: v8/v8  
Branch: refs/branch-heads/13.2  
Author: Matthias Liedtke <[mliedtke@chromium.org](<mailto:mliedtke@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6097336](<https://chromium-review.googlesource.com/6097336>)

Merged: [turboshaft][wasm] WasmGCTypeAnalyzer: Fix single-block loops properly

* * *

Expand for full commit details

```
Merged: [turboshaft][wasm] WasmGCTypeAnalyzer: Fix single-block loops properly 
 
While https://crrev.com/c/6087921 fixed a bug where the type in the 
loop header revisit was reflecting "older" knowledge, it didn't address 
the general issue of loop phis dependencies in single block loops where 
it might require many iterations until all type information has 
stabilized. 
 
The fix linked above also introduce too specific DCHECKs, as even 
outside of single-block loops we can end up with phis where a phi input 
appears in the same block before the phi itself. 
The binaryen fuzzer found the following pattern: 
  v113 = Phi(v26, v113) 
  v114 = Phi(v26, v113) 
 
In follow-up changes it should be ensured that the useless phi v113 
doesn't get emitted, then v114 wouldn't have that issue (and it could 
also be removed.) 
 
Fixed: 383356864 
Bug: 383814042 
(cherry picked from commit c84e01e92bfd61d29541c59e378b9a15ba6fc891) 
 
Change-Id: I909737ccd25e31a02a31498dd12567da9286de41 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6097336 
Auto-Submit: Jakob Kummerow <jkummerow@chromium.org> 
Reviewed-by: Eva Herencsárová <evih@chromium.org> 
Commit-Queue: Eva Herencsárová <evih@chromium.org> 
Commit-Queue: Jakob Kummerow <jkummerow@chromium.org> 
Cr-Commit-Position: refs/branch-heads/13.2@{#44} 
Cr-Branched-From: 24068c59cedad9ee976ddc05431f5f497b1ebd71-refs/heads/13.2.152@{#1} 
Cr-Branched-From: 6054ba94db0969220be4f94dc1677fc4696bdc4f-refs/heads/main@{#97085}
```

* * *

Files:

  * M `src/compiler/turboshaft/wasm-gc-typed-optimization-reducer.cc`

* * *

Hash: dca8e9de2eb6cc54a6262dd166adfa703d31a0ed  
Date: Fri Dec 13 14:20:14 2024

* * *


---

**#31 — qk...@google.com — Dec 17, 2024 05:01PM**

Labeling as LTS-NotApplicable-126 because the `V8WasmTurboshaft` was not enabled in M126 according to [comment #2](<https://issues.chromium.org/issues/383356864#comment2>). Besides we don't merge back a patch related to a new feature to LTS.  
  
[1] [https://chromium-review.googlesource.com/c/v8/v8/+/5476494](<https://chromium-review.googlesource.com/c/v8/v8/+/5476494>) (b8431f57e0fc19223e9371ccaf7e99a9b9a061f0)


---

**#32 — ma...@gmail.com — Dec 18, 2024 08:57AM**

A quick update regarding the POC regarding this issue: I've now developed an alternate proof-of-concept exploit for this bug which uses [issue 384186547](<https://issues.chromium.org/issues/384186547>) as the sandbox escape. This POC achieves RCE within the renderer process in around 9/10 runs. I've attached its source code below (please excuse its messiness; it's the raw output of my internal tooling, and not minified / prettified in any way); alternatively, a version with a WebSocket-based logging harness is also hosted at [https://cytc.popax21.dev/3e8cdb8d00743bce2c92e055b7516e44c66bea6d7317806143b27d93e2964153](<https://cytc.popax21.dev/3e8cdb8d00743bce2c92e055b7516e44c66bea6d7317806143b27d93e2964153>). Note that this exploit only works within the confines of Chromium; this is because of the nature of the bug used to escape the sandbox. I've however tested the exploit and confirmed that it works on both stable Google Chrome 131.0.6778.108, and Chromium 131.0.6778.139 with `--js-flags='--turboshaft-wasm'`.


---

**#33 — sp...@google.com — Dec 19, 2024 06:55AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $55000.00 for this report.  
  
Rationale for this decision:  
high-quality report demonstrating RCE in a sandboxed process / renderer   
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#34 — am...@chromium.org — Dec 19, 2024 09:15AM**

Congratulations Popax21! Thank you for your excellent and through efforts on this issue, complete with two exploits, once demonstrating a controlled write followed by one demonstrating RCE -- excellent work!


---

**#35 — pe...@google.com — Jan 2, 2025 09:43PM**

Dear owner, thanks for fixing this bug. We've reopened it because:

  * It is not clear which CLs have ‘fixed’ (=required to consider the bug resolved; e.g. not logging) this bug. Please fill in the “Fixed By Code Changes” field with the appropriate Gerrit url to disambiguate using the following guidelines: 
    * If there are multiple CLs required, please list all.
    * If the fix landed in a third party library (v8, Dawn, etc), please list the third party commits - not the rolls.
    * If there are cherrypicks or back merges, please list the original commits which landed on HEAD.
    * If there is no relevant Gerrit link (i.e. the fix does not live in or roll into Chromium), please use the value ‘NA’.
    * If this is a non-browser ChromeOS-specific bug, please move it to component 1335705 in the Google issue tracker.
    * If this field requires human intervention for some reason, please add this bug to the hotlist id 6265590. After resolving the above issue(s), this bug can be marked closed again. Thanks for your time!


---

**#36 — pe...@google.com — Jan 3, 2025 12:38AM**

jkummerow: Uh oh! This issue still open and hasn't been updated in the last 19 days. This is a serious vulnerability, and we want to ensure that there's progress. Could you please leave an update with the current status and any potential blockers?

If you're not the right owner for this issue, could you please remove yourself as soon as possible or help us find the right one?

If the issue is fixed or you can't reproduce it, please close the bug. If you've started working on a fix, please set the status to Started.

Thanks for your time! To disable nags, add Disable-Nags (case sensitive) to the Chromium Labels custom field.


---

**#37 — ap...@google.com — Jan 9, 2025 08:53PM**

Project: v8/v8  
Branch: main  
Author: Matthias Liedtke <[mliedtke@chromium.org](<mailto:mliedtke@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6162977](<https://chromium-review.googlesource.com/6162977>)

[test] Add regression test for [crbug.com/383356864](<https://crbug.com/383356864>)

* * *

Expand for full commit details

```
[test] Add regression test for crbug.com/383356864 
 
Bug: 383356864, 383740723 
Change-Id: I3f206c7896836388eff1a6a0d39d8ec5c6c732b0 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6162977 
Commit-Queue: Stephen Röttger <sroettger@google.com> 
Auto-Submit: Matthias Liedtke <mliedtke@chromium.org> 
Reviewed-by: Stephen Röttger <sroettger@google.com> 
Cr-Commit-Position: refs/heads/main@{#98020}
```

* * *

Files:

  * A `test/mjsunit/regress/wasm/regress-383356864.js`

* * *

Hash: 44ea78c7a36c0ddc3cac9f71234b8aaa6ce1a347  
Date: Thu Jan 09 11:59:38 2025

* * *


---

**#38 — ap...@google.com — Jan 11, 2025 01:22AM**

Project: v8/v8  
Branch: main  
Author: Matthias Liedtke <[mliedtke@chromium.org](<mailto:mliedtke@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6163632](<https://chromium-review.googlesource.com/6163632>)

[fuzzer][wasm] Generate shift of local values

* * *

Expand for full commit details

```
[fuzzer][wasm] Generate shift of local values 
 
Generates patterns like: 
  local.set 0 (local.get 1) 
  local.set 1 (local.get 2) 
  local.set 2 (local.get 3) 
  local.get 0 
 
When this is emitted in a loop, the value of local 3 slowly progresses 
towards local 0, needing multiple iterations to "reach" it. 
This is an interesting pattern for typed optimizations: 
If the first 3 locals contain a structref and the 4th an anyref, these 
are the refined types at the beginning of the loop on each iteration: 
0:  [structref, structref, structref, anyref] 
1:  [structref, structref, anyref,    anyref] 
2:  [structref, anyref,    anyref,    anyref] 
3+: [anyref,    anyref,    anyref,    anyref] 
 
This change also changes the implementation of get_local_ref() which 
previously only picked a random local and would just fail if the local 
wasn't of the requested type. 
Instead it now picks a random local and if it doesn't have a matching 
type, it iterates over the locals starting from the random local trying 
to find a local with a matching type. 
This increases the chance of being able to emit a local.get. 
 
Bug: 383356864, 383740723 
Change-Id: Ic98f69a2a4baa915b098394484588d2c730719cc 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6163632 
Auto-Submit: Matthias Liedtke <mliedtke@chromium.org> 
Reviewed-by: Jakob Kummerow <jkummerow@chromium.org> 
Commit-Queue: Jakob Kummerow <jkummerow@chromium.org> 
Cr-Commit-Position: refs/heads/main@{#98055}
```

* * *

Files:

  * M `src/wasm/fuzzing/random-module-generation.cc`

* * *

Hash: c36f622fe7964eab16446c18dd852ebc4ef60115  
Date: Fri Jan 10 14:42:50 2025

* * *


---

**#39 — ch...@google.com — Apr 11, 2025 09:51PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
