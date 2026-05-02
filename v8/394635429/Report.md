# V8 Sandbox Bypass: AAW & Control flow hijack via RegExp pattern parse TOCTOU to RegExpCapture OOB

Issue URL: https://issues.chromium.org/issues/394635429
VRP-Reward: 20000
Date: Feb 6, 2025 07:18PM


### VULNERABILITY DETAILS

#### Summary

V8 sandbox bypass, arbitrary address write + control flow hijack (arbitrary call) by corrupting RegExp string pattern concurrently during compilation. This may lead to inconsistent parsing state, resulting in out-of-bounds access of `RegExpCapture*` from `RegExpParserImpl::capture_` with a controlled offset. By spraying the heap with target addresses, we can trigger arbitrary writes on controlled address as well as control flow hijack via arbitrary address call.

#### Details

When compiling regexes with backreferences or named captures [`RegExpParserImpl<CharT>::ScanForCaptures()`](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/regexp/regexp-parser.cc;drc=743e7262f9ccb00132b727bbf261395e80f7a387;l=1427>) is invoked to do an eager scan across the whole pattern to find the total number of capture counts, which is later used in [`RegExpParserImpl<CharT>::GetCapture()`](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/regexp/regexp-parser.cc;drc=743e7262f9ccb00132b727bbf261395e80f7a387;l=1739>) to determine the required number of `RegExpCapture` objects to lazily allocate:

```
// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/regexp/regexp-parser.cc;drc=743e7262f9ccb00132b727bbf261395e80f7a387;l=1739
template <class CharT>
RegExpCapture* RegExpParserImpl<CharT>::GetCapture(int index) {
  // The index for the capture groups are one-based. Its index in the list is
  // zero-based.
  const int known_captures =
      is_scanned_for_captures_ ? capture_count_ : captures_started_;         // [!] use eagerly scanned total number of captures
  DCHECK(index <= known_captures);
  if (captures_ == nullptr) {
    captures_ =
        zone()->template New<ZoneList<RegExpCapture*>>(known_captures, zone());
  }
  while (captures_->length() < known_captures) {
    captures_->Add(zone()->template New<RegExpCapture>(captures_->length() + 1),
                   zone());
  }
  return captures_->at(index - 1);                                           // [!] fetch capture struct
}
```

`GetCapture()` is called whenever a capture is closed, where we used the current capture count `capture_index`:

```
// https://source.chromium.org/chromium/chromium/src/+/main:v8/src/regexp/regexp-parser.cc;drc=743e7262f9ccb00132b727bbf261395e80f7a387;l=960
template <class CharT>
RegExpTree* RegExpParserImpl<CharT>::ParseDisjunction() {
  // Used to store current state while parsing subexpressions.
  RegExpParserState initial_state(nullptr, INITIAL, RegExpLookaround::LOOKAHEAD,
                                  0, nullptr, flags(), zone());
  RegExpParserState* state = &initial_state;
  // Cache the builder in a local variable for quick access.
  RegExpBuilder* builder = initial_state.builder();
  while (true) {
    switch (current()) {
      // ...
      case ')': {
        if (!state->IsSubexpression()) {
          return ReportError(RegExpError::kUnmatchedParen);
        }
        DCHECK_NE(INITIAL, state->group_type());

        Advance();
        // End disjunction parsing and convert builder content to new single
        // regexp atom.
        RegExpTree* body = builder->ToRegExp();

        int end_capture_index = captures_started();

        int capture_index = state->capture_index();
        SubexpressionType group_type = state->group_type();

        // Build result of subexpression.
        if (group_type == CAPTURE) {
          if (state->IsNamedCapture()) {
            CreateNamedCaptureAtIndex(state, capture_index CHECK_FAILED);
          }
          RegExpCapture* capture = GetCapture(capture_index);                // [!] get capture struct
          capture->set_body(body);                                           // [!] primitive: AAW
          body = capture;
        } // ...

        // Restore previous state.
        state = state->previous_state();
        builder = state->builder();

        builder->AddAtom(body);                                              // [!] primitive: control flow hijack
        // For compatibility with JSC and ES3, we allow quantifiers after
        // lookaheads, and break in all cases.
        break;
      }
      // ...
      case '(': {
        state = ParseOpenParenthesis(state CHECK_FAILED);                    // [!] new capture, capture_index++
        builder = state->builder();
        flags_ = builder->flags();
        continue;
      }
      // ...
    }  // end switch(current())
    // ...
  }
}
```

However, the underlying regex pattern is in-sandbox and subject to concurrent modification by a malicious worker thread. This may cause inconsistent parser states, where:

  * Eager scanning returns `N` captures
  * Subsequent parser logic finds `M` captures, where `M > N`

This results in accessing an out-of-bounds `RegExpCapture*` at `GetCapture()`. Following logic that use this provides rich exploit primitives - `capture->set_body(body)` results in arbitrary address write, and the following `builder->AddAtom(body)` results in a memory indirect call with attacker-controlled address:

```
   0x5555560b3226 <v8::internal::(anonymous namespace)::RegExpParserImpl<unsigned char>::ParseDisjunction()+11302>    mov    rdi, r12
   0x5555560b3229 <v8::internal::(anonymous namespace)::RegExpParserImpl<unsigned char>::ParseDisjunction()+11305>    mov    esi, r8d
   0x5555560b322c <v8::internal::(anonymous namespace)::RegExpParserImpl<unsigned char>::ParseDisjunction()+11308>    call   v8::internal::(anonymous namespace)::RegExpParserImpl<unsigned short>::GetCapture(int) <v8::internal::(anonymous namespace)::RegExpParserImpl<unsigned short>::GetCapture(int)>
 
   0x5555560b3231 <v8::internal::(anonymous namespace)::RegExpParserImpl<unsigned char>::ParseDisjunction()+11313>    mov    r15, rax                      // [!] attacker-controlled
   0x5555560b3234 <v8::internal::(anonymous namespace)::RegExpParserImpl<unsigned char>::ParseDisjunction()+11316>    mov    rbx, qword ptr [rbp - 0x1f8]
   0x5555560b323b <v8::internal::(anonymous namespace)::RegExpParserImpl<unsigned char>::ParseDisjunction()+11323>    mov    qword ptr [rax + 8], rbx      // [!] arbitrary address write
   0x5555560b323f <v8::internal::(anonymous namespace)::RegExpParserImpl<unsigned char>::ParseDisjunction()+11327>    mov    rax, qword ptr [rbx]
   0x5555560b3242 <v8::internal::(anonymous namespace)::RegExpParserImpl<unsigned char>::ParseDisjunction()+11330>    mov    rdi, rbx
   0x5555560b3245 <v8::internal::(anonymous namespace)::RegExpParserImpl<unsigned char>::ParseDisjunction()+11333>    call   qword ptr [rax + 0x38]
   0x5555560b3248 <v8::internal::(anonymous namespace)::RegExpParserImpl<unsigned char>::ParseDisjunction()+11336>    mov    dword ptr [r15 + 0x14], eax
   0x5555560b324c <v8::internal::(anonymous namespace)::RegExpParserImpl<unsigned char>::ParseDisjunction()+11340>    mov    rax, qword ptr [rbx]
   0x5555560b324f <v8::internal::(anonymous namespace)::RegExpParserImpl<unsigned char>::ParseDisjunction()+11343>    mov    rdi, rbx
   0x5555560b3252 <v8::internal::(anonymous namespace)::RegExpParserImpl<unsigned char>::ParseDisjunction()+11346>    call   qword ptr [rax + 0x40]
   0x5555560b3255 <v8::internal::(anonymous namespace)::RegExpParserImpl<unsigned char>::ParseDisjunction()+11349>    mov    dword ptr [r15 + 0x18], eax
   0x5555560b3259 <v8::internal::(anonymous namespace)::RegExpParserImpl<unsigned char>::ParseDisjunction()+11353>    mov    r14, qword ptr [rbp - 0x1b8]
   0x5555560b3260 <v8::internal::(anonymous namespace)::RegExpParserImpl<unsigned char>::ParseDisjunction()+11360>    mov    r14, qword ptr [r14]
   0x5555560b3263 <v8::internal::(anonymous namespace)::RegExpParserImpl<unsigned char>::ParseDisjunction()+11363>    lea    rbx, [r14 + 8]
   0x5555560b3267 <v8::internal::(anonymous namespace)::RegExpParserImpl<unsigned char>::ParseDisjunction()+11367>    mov    rax, qword ptr [r15]          // [!] deref from attacker-controlled pointer
   0x5555560b326a <v8::internal::(anonymous namespace)::RegExpParserImpl<unsigned char>::ParseDisjunction()+11370>    mov    rdi, r15
   0x5555560b326d <v8::internal::(anonymous namespace)::RegExpParserImpl<unsigned char>::ParseDisjunction()+11373>    call   qword ptr [rax + 0x120]       // [!] arbitrary call
```

The attached repro repeatedly requests a new regex compilation by calling `new RegExp(pattern)` where pattern is constantly flipped between the following two values:

  * `/\1()()...((((...))))[]/`, where with `SCAN_SIZE` repeats of `()` and `OOB_OFS` deep `((((...))))` a total of `SCAN_SIZE + OOB_OFS` captures will be parsed
  * `/\1()()...[(((...))))[]/`, where the change results in only `SCAN_SIZE` captures to be parsed

Once the pre-scan logic computes capture counts based on the second state and then parser continues with the first state, we access an out-of-bounds index of `SCAN_SIZE + OOB_OFS` on a ZoneList `RegExpParserImpl::capture_` of length `SCAN_SIZE`. This lands on the heap spray and crashes on the first arbitrary address write attempt.

### VERSION

V8: Tested on CF asan / no-asan sandbox-testing d8 @ revision 98499 (commit [4f7e475](<https://chromium-review.googlesource.com/c/v8/v8/+/6226583>))

### REPRODUCTION CASE

Attached as `regexp-capture-double-parse-oob-call.js`, run with `./d8 --sandbox-testing`.

The repro attempts an arbitrary write to address `0x42424242424a`. If this is instead set to an attacker-controlled address, we immediately reach the arbitrary call primitive too.

### FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION

Type of crash: Sandbox violation

### CREDIT INFORMATION

Reporter credit: Seunghyun Lee (@0x10n) of CMU CyLab

* * *

This was discovered with a v8 sandbox fuzzer.


---

**#2 — pt...@chromium.org — Feb 6, 2025 08:46PM**

Thanks for the detailed report! Going to work on a fix.


---

**#3 — ap...@google.com — Feb 6, 2025 10:14PM**

Project: v8/v8  
Branch: main  
Author: pthier <[pthier@chromium.org](<mailto:pthier@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6239220](<https://chromium-review.googlesource.com/6239220>)

[regexp] Harden access of captures during RegExp parsing

* * *

Expand for full commit details

```
[regexp] Harden access of captures during RegExp parsing 
 
Capture indices are calculated while parsing a RegExp pattern and 
used to retrieve capture objects from a ZoneList. Since the pattern 
is allocated inside the sandbox, we can't trust any calculated value 
based on it. 
 
Drive-by: Remove unused member variable. 
 
Fixed: 394635429 
Change-Id: If85dab92b59ce8af6dd742dc7721fb40828ee510 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6239220 
Auto-Submit: Patrick Thier <pthier@chromium.org> 
Reviewed-by: Camillo Bruni <cbruni@chromium.org> 
Commit-Queue: Camillo Bruni <cbruni@chromium.org> 
Cr-Commit-Position: refs/heads/main@{#98543}
```

* * *

Files:

  * M `src/regexp/regexp-parser.cc`

* * *

Hash: 6c5f6bdc3652c1bed3b5f3e4a42090cd684e4d75  
Date: Thu Feb 06 13:34:30 2025

* * *


---

**#4 — pe...@google.com — Feb 6, 2025 10:32PM**

Dear owner, thanks for fixing this bug. We've reopened it because:

  * Security bugs need the Severity (S0-S3) and the Found In set, which will enable the bots to request merges to the correct branches (as well as helping out our vulnerability reward and CVE processes). Please consult with any Chrome security contact ([security@chromium.org](<mailto:security@chromium.org>)) to arrange to set these labels. Severity guidelines: [https://chromium.googlesource.com/chromium/src/+/refs/heads/main/docs/security/severity-guidelines.md#severity-guidelines-for-security-issues](<https://chromium.googlesource.com/chromium/src/+/refs/heads/main/docs/security/severity-guidelines.md#severity-guidelines-for-security-issues>) FoundIn guidelines: [https://chromium.googlesource.com/chromium/src/+/main/docs/security/security-labels.md#labels-relevant-for-any-type_bug_security](<https://chromium.googlesource.com/chromium/src/+/main/docs/security/security-labels.md#labels-relevant-for-any-type_bug_security>) After resolving the above issue(s), this bug can be marked closed again. Thanks for your time!


---

**#5 — pe...@google.com — Feb 8, 2025 12:39AM**

Setting milestone because of s2 severity.


---

**#6 — pe...@google.com — Feb 8, 2025 12:40AM**

Setting Priority to P1 to match Severity s2. If this is incorrect, please reset the priority. The automation bot account won't make this change again.


---

**#7 — pe...@google.com — Feb 8, 2025 12:43AM**

Security Merge Request Consideration: This is sufficiently serious that it should be merged to beta. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M134. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately. **Merge approved:** your change passed merge requirements and is auto-approved for M134. Please go ahead and merge the CL to branch 6998 (refs/branch-heads/6998) manually. Please contact milestone owner if you have questions. Merge instructions: [https://chromium.googlesource.com/chromium/src.git/+/refs/heads/main/docs/process/merge_request.md](<https://chromium.googlesource.com/chromium/src.git/+/refs/heads/main/docs/process/merge_request.md>) Owners: lmenezes (ChromeOS), srinivassista (Desktop US), danielyip (Desktop EMEA), govind (Mobile US), eakpobaro (Mobile EMEA) Security Merge Request: Thank you for fixing this security bug! We aim to ship security fixes as quickly as possible, to limit their opportunity for exploitation as an "n-day" (that is, a bug where git fixes are developed into attacks before those fixes reach users).

We have determined this fix is necessary on milestone(s): [134].

Please answer the following questions so that we can safely process this merge request:

  1. Which CLs should be backmerged? (Please include Gerrit links.)
  2. Has this fix been verified on Canary to not pose any stability regressions?
  3. Does this fix pose any potential non-verifiable stability risks?
  4. Does this fix pose any known compatibility risks?
  5. Does it require manual verification by the test team? If so, please describe required testing.
  6. (no answer required) Please check the OS custom field to ensure all impacted OSes are checked!


---

**#8 — pe...@google.com — Feb 8, 2025 01:02AM**

The issue's primary component must be in the Component Tags, so re-adding it. To change the primary component, use the edit button at the top of the issue, just above the title.


---

**#9 — pt...@chromium.org — Feb 8, 2025 01:02AM**

I don't think we backmerge sandbox escapes yet? Assigning Sandbox as correct component.


---

**#10 — am...@chromium.org — Feb 11, 2025 07:04AM**

We don't. Someone set a found-in rather than setting this as SI-None, so the bots assumed a merge. I've removed the merge approval tag and set the SI-none hotlist.


---

**#11 — sp...@google.com — Feb 15, 2025 07:55AM**

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

**#12 — am...@chromium.org — Feb 15, 2025 08:04AM**

Congratulations on another one, Seunghyun! Thanks for another excellent report and your continued efforts researching the V8 sandbox!


---

**#13 — ch...@google.com — May 16, 2025 09:43PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
