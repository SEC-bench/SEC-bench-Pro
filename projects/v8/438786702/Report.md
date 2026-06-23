# Corrupt Map of Externalized String Cause OOB Read

Issue URL: https://issues.chromium.org/issues/438786702
VRP-Reward: DUP
Date: Aug 15, 2025 01:49PM


#### Description

pi...@gmail.com created issue [ #1](</issues/438786702#comment1>)

Aug 15, 2025 01:49PM

  
VULNERABILITY DETAILS  
Change map of a externalized one byte string to two-byte, result heap-buffer-overflow read when computing UTF-8 length.  
  
VERSION  
V8 Version: 14.0.302  
Operating System: linux  
  
REPRODUCTION CASE  
  
Build args:  
is_debug=false  
is_asan=true  
dcheck_always_on=false  
v8_static_library=true   
v8_enable_verify_heap=true   
v8_enable_i18n_support=true  
is_component_build=false  
target_cpu="x64"  
v8_enable_sandbox=true  
v8_enable_memory_corruption_api=true  
  
Run args: ./d8 --sandbox-fuzzing --expoes-externalize-string poc.js  
  
FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION  
Type of crash: heap-buffer-overflow  
Crash State:   
=================================================================  
==4027794==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x7b7811debd3e at pc 0x563c3750d781 bp 0x7ffcbbbf1cf0 sp 0x7ffcbbbf1ce8  
READ of size 2 at 0x7b7811debd3e thread T0  
#0 0x563c3750d780 in v8::internal::String::Utf8Length(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::String>) src/objects/string-inl.h:1230:19  
#1 0x563c3752a90a in Utf8LengthV2 src/api/api.cc:5701:10  
#2 0x563c3752a90a in v8::String::Utf8Value::Utf8Value(v8::Isolate*, v8::Local<v8::Value>) src/api/api.cc:11129:18  
#3 0x563c370af4e3 in v8::(anonymous namespace)::WriteToFile(char const*, _IO_FILE*, v8::Isolate*, v8::debug::ConsoleCallArguments const&) src/d8/d8-console.cc:32:27  
#4 0x563c375c8e86 in v8::internal::(anonymous namespace)::ConsoleCall(v8::internal::Isolate*, v8::internal::BuiltinArguments const&, void (v8::debug::ConsoleDelegate::*)(v8::debug::ConsoleCallArguments const&, v8::debug::ConsoleContext const&)) src/builtins/builtins-console.cc:170:3  
#5 0x563c375c1495 in Builtin_Impl_ConsoleLog src/builtins/builtins-console.cc:209:1  
#6 0x563c375c1495 in v8::internal::Builtin_ConsoleLog(int, unsigned long*, v8::internal::Isolate*) src/builtins/builtins-console.cc:209:1  
#7 0x563c3cbacf75 in Builtins_CEntry_Return1_ArgvOnStack_BuiltinExit setup-isolate-deserialize.cc  
#8 0x563c3caff934 in Builtins_InterpreterEntryTrampoline setup-isolate-deserialize.cc  
#9 0x563c3cafc55b in Builtins_JSEntryTrampoline setup-isolate-deserialize.cc  
#10 0x563c3cafc2aa in Builtins_JSEntry setup-isolate-deserialize.cc  
#11 0x563c37957e3d in Call src/execution/simulator.h:212:12  
#12 0x563c37957e3d in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:442:22  
#13 0x563c3795a748 in v8::internal::Execution::CallScript(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>) src/execution/execution.cc:542:10  
#14 0x563c374e26e7 in v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) src/api/api.cc:1937:7  
#15 0x563c370ddea0 in v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) src/d8/d8.cc:1033:44  
#16 0x563c3711f237 in v8::SourceGroup::Execute(v8::Isolate*) src/d8/d8.cc:5351:10  
#17 0x563c3712d768 in v8::Shell::RunMainIsolate(v8::Isolate*, bool) src/d8/d8.cc:6307:37  
#18 0x563c3712c98e in v8::Shell::RunMain(v8::Isolate*, bool) src/d8/d8.cc:6215:18  
#19 0x563c371319a9 in v8::Shell::Main(int, char**) src/d8/d8.cc:7100:18  
#20 0x7f5812afbd09 in __libc_start_main (/lib/x86_64-linux-gnu/libc.so.6+0x23d09) (BuildId: a3780b0b8a5bf5876e31d16b0a9d8fc6ba69a1f2)  
  
0x7b7811debd3f is located 0 bytes after 15-byte region [0x7b7811debd30,0x7b7811debd3f)  
allocated by thread T0 here:  
#0 0x563c370a177d in operator new[](unsigned long) (/home/user/v8_build/v8/out/release_asan_debug/d8+0x13c277d) (BuildId: a18194e66e0b05f8)  
#1 0x563c3804d45f in v8::internal::ExternalizeStringExtension::Externalize(v8::FunctionCallbackInfo<v8::Value> const&) src/extensions/externalize-string-extension.cc:126:21  
#2 0x563c3cb01703 in Builtins_CallApiCallbackGeneric setup-isolate-deserialize.cc  
#3 0x563c3caff934 in Builtins_InterpreterEntryTrampoline setup-isolate-deserialize.cc  
#4 0x563c3cafc55b in Builtins_JSEntryTrampoline setup-isolate-deserialize.cc  
#5 0x563c3cafc2aa in Builtins_JSEntry setup-isolate-deserialize.cc  
#6 0x563c37957e3d in Call src/execution/simulator.h:212:12  
#7 0x563c37957e3d in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:442:22  
#8 0x563c3795a748 in v8::internal::Execution::CallScript(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>) src/execution/execution.cc:542:10  
#9 0x563c374e26e7 in v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) src/api/api.cc:1937:7  
#10 0x563c370ddea0 in v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) src/d8/d8.cc:1033:44  
#11 0x563c3711f237 in v8::SourceGroup::Execute(v8::Isolate*) src/d8/d8.cc:5351:10  
#12 0x563c3712d768 in v8::Shell::RunMainIsolate(v8::Isolate*, bool) src/d8/d8.cc:6307:37  
#13 0x563c3712c98e in v8::Shell::RunMain(v8::Isolate*, bool) src/d8/d8.cc:6215:18  
#14 0x563c371319a9 in v8::Shell::Main(int, char**) src/d8/d8.cc:7100:18  
#15 0x7f5812afbd09 in __libc_start_main (/lib/x86_64-linux-gnu/libc.so.6+0x23d09) (BuildId: a3780b0b8a5bf5876e31d16b0a9d8fc6ba69a1f2)  
  
SUMMARY: AddressSanitizer: heap-buffer-overflow src/objects/string-inl.h:1230:19 in v8::internal::String::Utf8Length(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::String>)  
Shadow bytes around the buggy address:  
0x7b7811deba80: fa fa 00 fa fa fa fd fa fa fa fd fd fa fa 00 fa  
0x7b7811debb00: fa fa fd fd fa fa fd fa fa fa fd fd fa fa fd fd  
0x7b7811debb80: fa fa fd fa fa fa fd fa fa fa fd fd fa fa fd fd  
0x7b7811debc00: fa fa fd fd fa fa fd fd fa fa fd fa fa fa fd fa  
0x7b7811debc80: fa fa 00 fa fa fa 00 00 fa fa 00 fa fa fa ac 00  
=>0x7b7811debd00: fa fa fd fa fa fa 00[07]fa fa fa fa fa fa fa fa  
0x7b7811debd80: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa  
0x7b7811debe00: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa  
0x7b7811debe80: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa  
0x7b7811debf00: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa  
0x7b7811debf80: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa  
Shadow byte legend (one shadow byte represents 8 application bytes):  
Addressable: 00  
Partially addressable: 01 02 03 04 05 06 07   
Heap left redzone: fa  
Freed heap region: fd  
Stack left redzone: f1  
Stack mid redzone: f2  
Stack right redzone: f3  
Stack after return: f5  
Stack use after scope: f8  
Global redzone: f9  
Global init order: f6  
Poisoned by user: f7  
Container overflow: fc  
Array cookie: ac  
Intra object redzone: bb  
ASan internal: fe  
Left alloca redzone: ca  
Right alloca redzone: cb  
==4027794==ABORTING  
  
## V8 sandbox violation detected!  
  
  
CREDIT INFORMATION  
Reporter credit: Picasso

poc.js 

361 B [ View](<https://issues.chromium.org/action/issues/438786702/attachments/68475821?download=false>)[ Download](<https://issues.chromium.org/action/issues/438786702/attachments/68475821?download=true>)


---

**#2 — cl...@appspot.gserviceaccount.com — Aug 16, 2025 11:06AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=6490758596984832](<https://clusterfuzz.com/testcase?key=6490758596984832>).


---

**#3 — cl...@appspot.gserviceaccount.com — Aug 16, 2025 11:09AM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5630882522005504](<https://clusterfuzz.com/testcase?key=5630882522005504>).


---

**#4 — am...@chromium.org — Aug 16, 2025 11:24AM**

v8 sandbox bypass:

  * severity= medium / S2
  * is not yet considered a security boundary, so setting SI-None


---

**#5 — am...@chromium.org — Aug 16, 2025 11:25AM**

cc'ing current V8 security shepherd


---

**#6 — 24...@project.gserviceaccount.com — Aug 16, 2025 11:46AM**

Automatically applying components based on crash stacktrace and information from OWNERS files.  
  
If this is incorrect, please apply the hotlistid:4801165.


---

**#7 — 24...@project.gserviceaccount.com — Aug 16, 2025 11:46AM**

Detailed Report: [https://clusterfuzz.com/testcase?key=5630882522005504](<https://clusterfuzz.com/testcase?key=5630882522005504>)  
  
Fuzzer: None  
Job Type: linux_asan_d8_sandbox_testing  
Platform Id: linux  
  
Crash Type: V8 sandbox violation  
Crash Address: 0x7c02d3105f7e  
Crash State:  
v8::internal::String::Utf8Length  
v8::String::Utf8Value::Utf8Value  
v8::WriteToFile  
  
Sanitizer: address (ASAN)  
  
Regressed: [https://clusterfuzz.com/revisions?job=linux_asan_d8_sandbox_testing&range=97070:97071](<https://clusterfuzz.com/revisions?job=linux_asan_d8_sandbox_testing&range=97070:97071>)  
  
Reproducer Testcase: [https://clusterfuzz.com/download?testcase_id=5630882522005504](<https://clusterfuzz.com/download?testcase_id=5630882522005504>)  
  
To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.  
  
If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.  
  
If you have any feedback on reproducing test cases, let us know at [https://forms.gle/Yh3qCYFveHj6E5jz5](<https://forms.gle/Yh3qCYFveHj6E5jz5>) so we can improve.


---

**#8 — is...@chromium.org — Aug 18, 2025 08:25PM**

Thank you for the report!

This is a duplicate of [issue 329781444](<https://issues.chromium.org/issues/329781444>) (V8 sandbox: OOB read when corrupting length of an ExternalString) modulo the way we make this OOB happen (by map corruption instead of length field).


---

**#9 — ch...@google.com — Jan 8, 2026 09:41PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
