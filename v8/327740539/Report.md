# Check failed: !v8::internal::v8_flags.enable_slow_asserts.value() || (IsDereferenceAllowed()).

Issue URL: https://issues.chromium.org/issues/327740539
VRP-Reward: 15000
Date: Mar 2, 2024 03:43AM


#### Description

wh...@gmail.com created issue [ #1](</issues/327740539#comment1>)

Mar 2, 2024 03:43AM

Security Bug  
  
Please READ THIS FAQ before filing a bug: [https://chromium.googlesource.com/chromium/src/+/HEAD/docs/security/faq.md](<https://chromium.googlesource.com/chromium/src/+/HEAD/docs/security/faq.md>)  
  
Please see the following link for instructions on filing security bugs: [https://www.chromium.org/Home/chromium-security/reporting-security-bugs](<https://www.chromium.org/Home/chromium-security/reporting-security-bugs>)  
  
Reports may be eligible for reward payments under the Chrome VRP: [https://g.co/chrome/vrp](<https://g.co/chrome/vrp>)  
  
NOTE: Security bugs are normally made public once a fix has been widely deployed.  
  
\-------------------------  
  
VULNERABILITY DETAILS  
#  
# Fatal error in ../../src/handles/handles.h, line 162  
# Check failed: !v8::internal::v8_flags.enable_slow_asserts.value() || (IsDereferenceAllowed()).  
#  
#  
#  
#FailureMessage Object: 0x7f56e17f7ec0  
==== C stack trace ===============================  
  
/home/uuu/asan/d8_debug_zip/d8-linux-debug-v8-component-92624/libv8_libbase.so(v8::base::debug::StackTrace::StackTrace()+0x13) [0x7f571caa4963]  
/home/uuu/asan/d8_debug_zip/d8-linux-debug-v8-component-92624/libv8_libplatform.so(+0x1931d) [0x7f571ca4d31d]  
/home/uuu/asan/d8_debug_zip/d8-linux-debug-v8-component-92624/libv8_libbase.so(V8_Fatal(char const*, int, char const*, ...)+0x17e) [0x7f571ca85c0e]  
/home/uuu/asan/d8_debug_zip/d8-linux-debug-v8-component-92624/libv8.so(v8::internal::Scope::NewHomeObjectVariableProxy(v8::internal::AstNodeFactory*, v8::internal::AstRawString const*, int)+0x34b) [0x7f5719dd7d8b]  
/home/uuu/asan/d8_debug_zip/d8-linux-debug-v8-component-92624/libv8.so(v8::internal::ParserBase<v8::internal::Parser>::ParseSuperExpression()+0x24a) [0x7f571abcca4a]  
/home/uuu/asan/d8_debug_zip/d8-linux-debug-v8-component-92624/libv8.so(v8::internal::ParserBase<v8::internal::Parser>::ParseBinaryExpression(int)+0x112) [0x7f571abc8812]  
/home/uuu/asan/d8_debug_zip/d8-linux-debug-v8-component-92624/libv8.so(v8::internal::ParserBase<v8::internal::Parser>::ParseAssignmentExpressionCoverGrammar()+0x94) [0x7f571abc69a4]  
/home/uuu/asan/d8_debug_zip/d8-linux-debug-v8-component-92624/libv8.so(v8::internal::ParserBase<v8::internal::Parser>::ParseExpressionCoverGrammar()+0x116) [0x7f571abcd156]  
/home/uuu/asan/d8_debug_zip/d8-linux-debug-v8-component-92624/libv8.so(v8::internal::ParserBase<v8::internal::Parser>::ParseExpressionOrLabelledStatement(v8::internal::ZoneList<v8::internal::AstRawString const*>*, v8::internal::ZoneList<v8::internal::AstRawString const*>*, v8::internal::AllowLabelledFunctionStatement)+0x1a6) [0x7f571abdb6f6]  
/home/uuu/asan/d8_debug_zip/d8-linux-debug-v8-component-92624/libv8.so(v8::internal::ParserBase<v8::internal::Parser>::ParseBlock(v8::internal::ZoneList<v8::internal::AstRawString const*>*, v8::internal::Scope*)+0x2d1) [0x7f571abd5db1]  
/home/uuu/asan/d8_debug_zip/d8-linux-debug-v8-component-92624/libv8.so(v8::internal::ParserBase<v8::internal::Parser>::ParseTryStatement()+0x86) [0x7f571abd9ff6]  
/home/uuu/asan/d8_debug_zip/d8-linux-debug-v8-component-92624/libv8.so(v8::internal::ParserBase<v8::internal::Parser>::ParseStatementList(v8::internal::ScopedList<v8::internal::Statement*, void*>*, v8::internal::Token::Value)+0x23d) [0x7f571aba84cd]  
/home/uuu/asan/d8_debug_zip/d8-linux-debug-v8-component-92624/libv8.so(v8::internal::ParserBase<v8::internal::Parser>::ParseFunctionBody(v8::internal::ScopedList<v8::internal::Statement*, void*>*, v8::internal::AstRawString const*, int, v8::internal::ParserFormalParameters const&, v8::internal::FunctionKind, v8::internal::FunctionSyntaxKind, v8::internal::ParserBase<v8::internal::Parser>::FunctionBodyType)+0x47a) [0x7f571abb774a]  
/home/uuu/asan/d8_debug_zip/d8-linux-debug-v8-component-92624/libv8.so(v8::internal::Parser::ParseFunction(v8::internal::ScopedList<v8::internal::Statement*, void*>*, v8::internal::AstRawString const*, int, v8::internal::FunctionKind, v8::internal::FunctionSyntaxKind, v8::internal::DeclarationScope*, int*, int*, bool*, int*, int*, v8::internal::ZoneList<v8::internal::AstRawString const*>*)+0x52d) [0x7f571abb641d]  
/home/uuu/asan/d8_debug_zip/d8-linux-debug-v8-component-92624/libv8.so(v8::internal::Parser::ParseFunctionLiteral(v8::internal::AstRawString const*, v8::internal::Scanner::Location, v8::internal::FunctionNameValidity, v8::internal::FunctionKind, int, v8::internal::FunctionSyntaxKind, v8::internal::LanguageMode, v8::internal::ZoneList<v8::internal::AstRawString const*>*)+0x737) [0x7f571aba92d7]  
/home/uuu/asan/d8_debug_zip/d8-linux-debug-v8-component-92624/libv8.so(v8::internal::Parser::DoParseFunction(v8::internal::Isolate*, v8::internal::ParseInfo*, int, int, int, v8::internal::AstRawString const*)+0x2e7) [0x7f571abab407]  
/home/uuu/asan/d8_debug_zip/d8-linux-debug-v8-component-92624/libv8.so(v8::internal::Parser::ParseOnBackground(v8::internal::LocalIsolate*, v8::internal::ParseInfo*, int, int, int)+0xf7) [0x7f571abb9a67]  
/home/uuu/asan/d8_debug_zip/d8-linux-debug-v8-component-92624/libv8.so(v8::internal::BackgroundCompileTask::Run(v8::internal::LocalIsolate*, v8::internal::ReusableUnoptimizedCompileState*)+0xa18) [0x7f5719f916e8]  
/home/uuu/asan/d8_debug_zip/d8-linux-debug-v8-component-92624/libv8.so(v8::internal::LazyCompileDispatcher::DoBackgroundWork(v8::JobDelegate*)+0x40a) [0x7f571a03a14a]  
/home/uuu/asan/d8_debug_zip/d8-linux-debug-v8-component-92624/libv8_libplatform.so(v8::platform::DefaultJobWorker::Run()+0xd3) [0x7f571ca4c123]  
/home/uuu/asan/d8_debug_zip/d8-linux-debug-v8-component-92624/libv8_libplatform.so(v8::platform::DefaultWorkerThreadsTaskRunner::WorkerThread::Run()+0xcc) [0x7f571ca4e50c]  
/home/uuu/asan/d8_debug_zip/d8-linux-debug-v8-component-92624/libv8_libbase.so(+0x496d8) [0x7f571caa36d8]  
/lib64/libc.so.6(+0x8683c) [0x7f57170e483c]  
/lib64/libc.so.6(+0xf8838) [0x7f5717156838]  
  
  
VERSION  
Chrome Version: [x.x.x.x] + [stable, beta, or dev]  
Operating System: [Please indicate OS, version, and service pack level]  
  
REPRODUCTION CASE  
  
run d8 with   
\--allow-natives-syntax --fuzzing --stress-background-compile --parallel-compile-tasks-for-lazy   
  
FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION  
Type of crash: [tab, browser, etc.]  
Crash State: [see link above: stack trace *with symbols*, registers, exception record]  
Client ID (if relevant): [see link above]  
  
CREDIT INFORMATION  
Externally reported security bugs may appear in Chrome release notes. If this bug is included, how would you like to be credited?  
Reporter credit: [goes here]

1.js 

1.3 KB [ View](<https://issues.chromium.org/action/issues/327740539/attachments/54293366?download=false>)[ Download](<https://issues.chromium.org/action/issues/327740539/attachments/54293366?download=true>)


---

**#2 — wh...@gmail.com — Mar 2, 2024 03:51AM**

PoC  
  
class A {  
valueOf() {  
super.p();  
}  
}


---

**#3 — wh...@gmail.com — Mar 2, 2024 04:03AM**

bisect   
I tested 78686 ([https://www.googleapis.com/download/storage/v1/b/v8-asan/o/linux-debug%2Fd8-linux-debug-v8-component-78686.zip?generation=1642611632001719&alt=media](<https://www.googleapis.com/download/storage/v1/b/v8-asan/o/linux-debug%2Fd8-linux-debug-v8-component-78686.zip?generation=1642611632001719&alt=media>))   
and 78687 ([https://www.googleapis.com/download/storage/v1/b/v8-asan/o/linux-debug%2Fd8-linux-debug-v8-component-78687.zip?generation=1642611759214411&alt=media](<https://www.googleapis.com/download/storage/v1/b/v8-asan/o/linux-debug%2Fd8-linux-debug-v8-component-78687.zip?generation=1642611759214411&alt=media>))   
only 78687 can reproduce  
  
[parser] Fix scope of super properties in heritage position  
  
super.property accesses in heritage positions like `class C extends  
super.property` should resolve super in the current scope, not C's  
class scope.  
  
Bug: chromium:1282096  
Change-Id: I7ef815bc02cfff35a2898ef9f39b133d1114046c  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/3400150](<https://chromium-review.googlesource.com/c/v8/v8/+/3400150>)  
Reviewed-by: Marja Hölttä <[marja@chromium.org](<mailto:marja@chromium.org>)>  
Commit-Queue: Shu-yu Guo <[syg@chromium.org](<mailto:syg@chromium.org>)>  
Cr-Commit-Position: refs/heads/main@{#78687}  
  
active channel: 122/stable, 123/beta, 124/dev


---

**#4 — ti...@chromium.org — Mar 5, 2024 02:19AM**

[Security shepherd] Cannot reproduce locally, but my gn args must be wrong. I need to somehow enable slow asserts in d8.

PoC and bisect look reasonable, so setting severity to high and foundin to 122 provisionally and assigning to v8 shepherd. Please be sure to check whether that is really the case!


---

**#5 — wh...@gmail.com — Mar 5, 2024 02:24AM**

Hi, I don't know why you can't reproduce locally.   
But I can very reliable reproduce every times.   
  
by running   
  
./d8 --allow-natives-syntax --fuzzing --stress-background-compile --parallel-compile-tasks-for-lazy poc.js  
  
also can reproduce with linux-debug_d8-linux-debug-v8-component-92649.zip


---

**#6 — pe...@google.com — Mar 6, 2024 12:38AM**

Setting milestone because of s0/s1 severity.


---

**#7 — pe...@google.com — Mar 6, 2024 12:39AM**

Setting Priority to P1 to match Severity s1. If this is incorrect, please reset the priority. The automation bot account won't make this change again.


---

**#8 — ap...@google.com — Mar 8, 2024 04:33PM**

Project: v8/v8  
Branch: main  
  
commit 8f477f936c9b9e6b4c9f35a8ccc5e65bd4cb7f4e  
Author: Shu-yu Guo <[syg@chromium.org](<mailto:syg@chromium.org>)>  
Date: Thu Mar 07 14:55:28 2024  
  
[parser] Fix home object proxy to work off-thread  
  
Because the home object has special scope lookup rules due to class  
heritage position, VariableProxies of the home object are currently  
directly created on the correct scope during parsing. However, during  
off-thread parsing the main thread is parked, and the correct scope  
may try to dereference a main-thread Handle.  
  
This CL moves the logic into ResolveVariable instead, which happens  
during postprocessing, with the main thread unparked.  
  
Fixed: chromium:327740539  
Change-Id: I3a123d5e37b6764067e58255dd5a67c07e648d02  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5350482](<https://chromium-review.googlesource.com/c/v8/v8/+/5350482>)  
Reviewed-by: Marja Hölttä <[marja@chromium.org](<mailto:marja@chromium.org>)>  
Commit-Queue: Marja Hölttä <[marja@chromium.org](<mailto:marja@chromium.org>)>  
Auto-Submit: Shu-yu Guo <[syg@chromium.org](<mailto:syg@chromium.org>)>  
Cr-Commit-Position: refs/heads/main@{#92722}  
  
M src/ast/ast.h  
M src/ast/scopes.cc  
M src/ast/scopes.h  
M src/parsing/parser-base.h  
M src/parsing/parser.cc  
M src/parsing/parser.h  
M src/parsing/preparser.h  
  
[https://chromium-review.googlesource.com/5350482](<https://chromium-review.googlesource.com/5350482>)


---

**#9 — pe...@google.com — Mar 9, 2024 12:41AM**

This is sufficiently serious that it should be merged to stable. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M122. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately.  
This is sufficiently serious that it should be merged to beta. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M123. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately.  
Thank you for fixing this security bug! We aim to ship security fixes as quickly as possible, to limit their opportunity for exploitation as an "n-day" (that is, a bug where git fixes are developed into attacks before those fixes reach users).  
  
We have determined this fix is necessary on milestone(s): [].  
  
Please answer the following questions so that we can safely process this merge request:  
1\. Which CLs should be backmerged? (Please include Gerrit links.)  
2\. Has this fix been verified on Canary to not pose any stability regressions?  
3\. Does this fix pose any potential non-verifiable stability risks?  
4\. Does this fix pose any known compatibility risks?  
5\. Does it require manual verification by the test team? If so, please describe required testing.


---

**#10 — sy...@chromium.org — Mar 9, 2024 01:06AM**

> 1\. Which CLs should be backmerged? (Please include Gerrit links.)  
  
[https://chromium-review.googlesource.com/c/v8/v8/+/5350482](<https://chromium-review.googlesource.com/c/v8/v8/+/5350482>)  
  
> 2\. Has this fix been verified on Canary to not pose any stability regressions?  
  
Landed on tip of tree, might want to wait for a day to bake in canary.  
  
> 3\. Does this fix pose any potential non-verifiable stability risks?  
  
No...?  
  
> 4\. Does this fix pose any known compatibility risks?  
  
No.  
  
> 5\. Does it require manual verification by the test team? If so, please describe required testing.  
  
No.


---

**#11 — pe...@google.com — Mar 9, 2024 05:28PM**

Merge review required: M123 is already shipping to beta.  
  
Please answer the following questions so that we can safely process your merge request:  
1\. Why does your merge fit within the merge criteria for these milestones?  
\- Chrome Browser: [https://chromiumdash.appspot.com/branches](<https://chromiumdash.appspot.com/branches>)  
\- Chrome OS: [https://goto.google.com/cros-release-branch-merge-guidelines](<https://goto.google.com/cros-release-branch-merge-guidelines>)  
2\. What changes specifically would you like to merge? Please link to Gerrit.  
3\. Have the changes been released and tested on canary?  
4\. Is this a new feature? If yes, is it behind a Finch flag and are experiments active in any release channels?  
5\. [Chrome OS only]: Was the change reviewed and approved by the Eng Prod Representative? [https://goto.google.com/cros-engprodcomponents](<https://goto.google.com/cros-engprodcomponents>)  
6\. If this merge addresses a major issue in the stable channel, does it require manual verification by the test team? If so, please describe required testing.  
  
Please contact the milestone owner if you have questions.  
Owners: govind (Android), govind (iOS), dgagnon (ChromeOS), srinivassista (Desktop)


---

**#12 — pe...@google.com — Mar 9, 2024 05:28PM**

Merge review required: M122 is already shipping to stable.  
  
Please answer the following questions so that we can safely process your merge request:  
1\. Why does your merge fit within the merge criteria for these milestones?  
\- Chrome Browser: [https://chromiumdash.appspot.com/branches](<https://chromiumdash.appspot.com/branches>)  
\- Chrome OS: [https://goto.google.com/cros-release-branch-merge-guidelines](<https://goto.google.com/cros-release-branch-merge-guidelines>)  
2\. What changes specifically would you like to merge? Please link to Gerrit.  
3\. Have the changes been released and tested on canary?  
4\. Is this a new feature? If yes, is it behind a Finch flag and are experiments active in any release channels?  
5\. [Chrome OS only]: Was the change reviewed and approved by the Eng Prod Representative? [https://goto.google.com/cros-engprodcomponents](<https://goto.google.com/cros-engprodcomponents>)  
6\. If this merge addresses a major issue in the stable channel, does it require manual verification by the test team? If so, please describe required testing.  
  
Please contact the milestone owner if you have questions.  
Owners: eakpobaro (Android), eakpobaro (iOS), ceb (ChromeOS), pbommana (Desktop)


---

**#13 — pe...@google.com — Mar 11, 2024 11:46AM**

This high+ V8 security issue with stable impact requires a lightweight post mortem. Please take some time to answer questions asked in this form [1] to help us improve V8 security. [1] [https://docs.google.com/forms/d/e/1FAIpQLSdSMCiEpIFLLFkMbgtulK1sf1B-idQmkFaA4XP2Rz5mN1cqWg/viewform?usp=pp_url&entry.307501673=327740539&entry.364066060=wh0tlif3@gmail.com&entry.958145677=Linux&entry.763880440=Extended&entry.1678852700=High&entry.763402679=Blink](<https://docs.google.com/forms/d/e/1FAIpQLSdSMCiEpIFLLFkMbgtulK1sf1B-idQmkFaA4XP2Rz5mN1cqWg/viewform?usp=pp_url&entry.307501673=327740539&entry.364066060=wh0tlif3@gmail.com&entry.958145677=Linux&entry.763880440=Extended&entry.1678852700=High&entry.763402679=Blink>)>JavaScript&entry.975983575=[syg@chromium.org](<mailto:syg@chromium.org>) Please ensure to copy the full link, as otherwise some issue meta data might not be populated automatically.


---

**#14 — am...@chromium.org — Mar 12, 2024 05:58AM**

I'm basing merge approval on the premise that the V8 team has determined this to be a potentially exploitable security issue; if the understanding is that this is not exploitable than please disregard and do not proceed with merging

merges approved for [https://crrev.com/c/5350482](<https://crrev.com/c/5350482>) please merge this fix to 12.3-lkgr and 12.2-lkgr at your earliest convenience

Stable cut for the M123 Stable is tomorrow at 10am Pacific, if possible please merge before then so this fix can be included If this merge deadline cannot be met, please do NOT merge to 12.2-lkgr at this time.


---

**#15 — ap...@google.com — Mar 12, 2024 07:17AM**

Project: v8/v8  
Branch: refs/branch-heads/12.3  
  
commit 615c099b587db35e68486b531144241df5ec8579  
Author: Shu-yu Guo <[syg@chromium.org](<mailto:syg@chromium.org>)>  
Date: Thu Mar 07 14:55:28 2024  
  
Merged: [parser] Fix home object proxy to work off-thread  
  
Because the home object has special scope lookup rules due to class  
heritage position, VariableProxies of the home object are currently  
directly created on the correct scope during parsing. However, during  
off-thread parsing the main thread is parked, and the correct scope  
may try to dereference a main-thread Handle.  
  
This CL moves the logic into ResolveVariable instead, which happens  
during postprocessing, with the main thread unparked.  
  
Fixed: chromium:327740539  
  
(cherry picked from commit 8f477f936c9b9e6b4c9f35a8ccc5e65bd4cb7f4e)  
  
Change-Id: Ia57c211e5d285f1a801ca1f95db02f7e199ccde9  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5363633](<https://chromium-review.googlesource.com/c/v8/v8/+/5363633>)  
Commit-Queue: Shu-yu Guo <[syg@chromium.org](<mailto:syg@chromium.org>)>  
Reviewed-by: Deepti Gandluri <[gdeepti@chromium.org](<mailto:gdeepti@chromium.org>)>  
Cr-Commit-Position: refs/branch-heads/12.3@{#18}  
Cr-Branched-From: a86e1971579f4165123467fa6ad378e552536b43-refs/heads/12.3.219@{#1}  
Cr-Branched-From: 21869f7f6f3e8f5a58a0b2e61e0f7412480230b1-refs/heads/main@{#92385}  
  
M src/ast/ast.h  
M src/ast/scopes.cc  
M src/ast/scopes.h  
M src/parsing/parser-base.h  
M src/parsing/parser.cc  
M src/parsing/parser.h  
M src/parsing/preparser.h  
  
[https://chromium-review.googlesource.com/5363633](<https://chromium-review.googlesource.com/5363633>)


---

**#16 — ap...@google.com — Mar 12, 2024 07:25AM**

Project: v8/v8  
Branch: refs/branch-heads/12.2  
  
commit 3eb29421eb1f6f913cefa74c9aa1eb0b5f84553f  
Author: Shu-yu Guo <[syg@chromium.org](<mailto:syg@chromium.org>)>  
Date: Thu Mar 07 14:55:28 2024  
  
Merged: [parser] Fix home object proxy to work off-thread  
  
Because the home object has special scope lookup rules due to class  
heritage position, VariableProxies of the home object are currently  
directly created on the correct scope during parsing. However, during  
off-thread parsing the main thread is parked, and the correct scope  
may try to dereference a main-thread Handle.  
  
This CL moves the logic into ResolveVariable instead, which happens  
during postprocessing, with the main thread unparked.  
  
Fixed: chromium:327740539  
  
(cherry picked from commit 8f477f936c9b9e6b4c9f35a8ccc5e65bd4cb7f4e)  
  
Change-Id: I16805ad35f5d70d1acadaf1f5440dfc159dbfa6c  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5363634](<https://chromium-review.googlesource.com/c/v8/v8/+/5363634>)  
Reviewed-by: Deepti Gandluri <[gdeepti@chromium.org](<mailto:gdeepti@chromium.org>)>  
Commit-Queue: Shu-yu Guo <[syg@chromium.org](<mailto:syg@chromium.org>)>  
Cr-Commit-Position: refs/branch-heads/12.2@{#44}  
Cr-Branched-From: 6eb5a9616aa6f8c705217aeb7c7ab8c037a2f676-refs/heads/12.2.281@{#1}  
Cr-Branched-From: 44cf56d850167c6988522f8981730462abc04bcc-refs/heads/main@{#91934}  
  
M src/ast/ast.h  
M src/ast/scopes.cc  
M src/ast/scopes.h  
M src/parsing/parser-base.h  
M src/parsing/parser.cc  
M src/parsing/parser.h  
M src/parsing/preparser.h  
  
[https://chromium-review.googlesource.com/5363634](<https://chromium-review.googlesource.com/5363634>)


---

**#17 — am...@chromium.org — Mar 12, 2024 08:44AM**

This fix here also appears to have resolved [crbug.com/40072287](<https://crbug.com/40072287>) reported in September 2023.


---

**#18 — wh...@gmail.com — Mar 12, 2024 05:17PM**

> [crbug.com/40072287](<http://crbug.com/40072287>) reported in September 2023  
  
Hi, may I still can get a CVE for this report and eligible for reward?


---

**#19 — am...@chromium.org — Mar 13, 2024 02:10AM**

re: c#18 -- we'll have to review at the Chrome VRP Panel but I can't make any guarantees here. There was no deficiency in the original report of [crbug.com/40072287](<https://crbug.com/40072287>) that caused it to not be resolved. There was even a CL in draft to fix that issue, it just seems to have been abandoned by the engineer working on that issue. It's not the fault of the original reporter that their issue went from being worked to overlooked, so it would not be truly fair if we rewarded this issue in full.


---

**#20 — wh...@gmail.com — Mar 14, 2024 12:35PM**

Thank you for your consideration. It's been six months since the original report, and I want to emphasize that any delay in resolution was not due to any oversight on reporter part, but rather a result of the engineer's lapse in attention. Without my report, it's possible that this vulnerability could have persisted even longer without being addressed. Given this, I believe it's only fair to consider both parties' contributions and offer full rewards to both. I'm committed to collaborating further to ensure the issue is fully resolved. Please let me know your thoughts on this proposal.


---

**#21 — am...@chromium.org — Mar 15, 2024 01:24AM**

If both reports are rewarded, it will involve splitting the reward -- not both reports being rewarded the full reward amount, as per our policies. Right now, since the engineer who is the owner of the other report is out of office, we are waiting for them to return so we can determine if these are truly duplicates and get a better understanding of the status of both reports. Thank you for your patience while we work to get this resolved.


---

**#22 — am...@chromium.org — Mar 20, 2024 03:15AM**

It appears that this issue may share a root cause with [crbug.com/40072287](<https://crbug.com/40072287>), these but the two crashes are happening in different locations -- one happens during parsing and another one during bytecode compilation. These bugs will remain separate issues for now while [crbug.com/40072287](<https://crbug.com/40072287>) is being re-opened for re-investigation.


---

**#23 — am...@google.com — Mar 23, 2024 07:42AM**

*** Boilerplate reminders! ***  
Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.  
******************************


---

**#24 — am...@chromium.org — Mar 23, 2024 07:47AM**

Congratulations! The Chrome VRP Panel has decided to award you $7,000 for this report + $1,000 bisect bonus. Thank you for your efforts and reporting this issue to us!


---

**#25 — wh...@gmail.com — Mar 23, 2024 12:45PM**

Hi,  
> V8 security bugs older than M105 may be eligible for a reward higher than specified in the table, based on the age of the bug.  
  
according Chrome VRP, this bug exist older then M105, may I get a higher reward.


---

**#26 — wh...@gmail.com — Mar 23, 2024 12:47PM**

The bug age is from M100 to M122 based bisect.   
  
[https://chromiumdash.appspot.com/commit/2afb952d305000f949c3ab2eb26981d9f40287e0](<https://chromiumdash.appspot.com/commit/2afb952d305000f949c3ab2eb26981d9f40287e0>)


---

**#27 — am...@chromium.org — Mar 28, 2024 01:42AM**

Hello, thank you for pointing this out and congratulations and thank for discovering and reporting a V8 security bug impacting older versions of Chrome! As such, we have updated the reward amount to $15,000 to reflect this.


---

**#28 — wh...@gmail.com — Mar 28, 2024 01:55AM**

Thank you.


---

**#29 — pe...@google.com — Jun 16, 2024 01:02AM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
