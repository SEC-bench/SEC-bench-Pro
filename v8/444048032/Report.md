# V8 Sandbox Bypass: OOB write in v8::bigint::AddAndReturnOverflow

Issue URL: https://issues.chromium.org/issues/444048032
VRP-Reward: 5000
Date: Sep 10, 2025 09:45PM


#### VULNERABILITY DETAILS

Concurrently modifying a `BigInt` when it is processed by `MultiplyToomCook` causes an OOB write. The value mutated by the reproducer is read here:

```
#10 0x000055555d1d1ec7 in v8::bigint::Digits::read_4byte_aligned (i=<optimized out>, this=<optimized out>) at ../../src/bigint/bigint.h:132
#11 v8::bigint::Digits::operator[] (i=<optimized out>, this=<optimized out>) at ../../src/bigint/bigint.h:93
#12 v8::bigint::Add (Z=..., X=..., Y=...) at ./../../src/bigint/vector-arithmetic.cc:48
#13 v8::bigint::AddSigned (Z=..., X=..., x_negative=<optimized out>, Y=..., y_negative=<optimized out>) at ./../../src/bigint/vector-arithmetic.cc:96
#14 0x000055555d1e6ab6 in v8::bigint::ProcessorImpl::Toom3Main (this=<optimized out>, Z=..., X=..., Y=...) at ./../../src/bigint/mul-toom.cc:142
#15 0x000055555d1e8055 in v8::bigint::ProcessorImpl::MultiplyToomCook (this=<optimized out>, Z=..., X=..., Y=...) at ./../../src/bigint/mul-toom.cc:216
#16 0x000055555d1a5d2a in v8::bigint::ProcessorImpl::Multiply (this=<optimized out>, Z=..., X=..., Y=...) at ./../../src/bigint/bigint-internal.cc:48
#17 0x000055555d1e6f8b in v8::bigint::ProcessorImpl::Toom3Main (this=<optimized out>, Z=..., X=..., Y=...) at ./../../src/bigint/mul-toom.cc:157
#18 0x000055555d1e8055 in v8::bigint::ProcessorImpl::MultiplyToomCook (this=<optimized out>, Z=..., X=..., Y=...) at ./../../src/bigint/mul-toom.cc:216
#19 0x000055555d1a5d2a in v8::bigint::ProcessorImpl::Multiply (this=<optimized out>, Z=..., X=..., Y=...) at ./../../src/bigint/bigint-internal.cc:48
#20 0x000055555d1d6c04 in v8::bigint::ProcessorImpl::DivideBarrett (this=<optimized out>, Q=..., R=..., A=..., B=..., I=..., scratch=...) at ./../../src/bigint/div-barrett.cc:245
#21 0x000055555d1d8627 in v8::bigint::ProcessorImpl::DivideBarrett (this=<optimized out>, Q=..., R=..., A=..., B=...) at ./../../src/bigint/div-barrett.cc:361
#22 0x000055555d1a77c2 in v8::bigint::ProcessorImpl::Modulo (this=<optimized out>, R=..., A=..., B=...) at ./../../src/bigint/bigint-internal.cc:124
#23 0x000055555d1a84ce in v8::bigint::Processor::Modulo (this=<optimized out>, R=..., A=..., B=...) at ./../../src/bigint/bigint-internal.cc:143
#24 0x000055555965f63f in v8::internal::MutableBigInt_AbsoluteModAndCanonicalize (result_addr=<optimized out>, x_addr=<optimized out>, y_addr=<optimized out>) at ./../../src/objects/bigint.cc:1569
```

#### VERSION

V8 Git Commit: b5aa4c8b718d75f9cf4d4afd635ffd217f0acb38 (Sat Sep 6 21:01:45 2025 -0700)

#### REPRODUCTION CASE

```
d8  --fuzzing --sandbox-fuzzing --single-threaded bug.js
```

**ASan Report**

This bug first triggers an OOB read before triggering an OOB write.

Report for b5aa4c8b718d75f9cf4d4afd635ffd217f0acb38 using the provided reproducer with vanilla ASan:

```
Sandbox testing mode is enabled. Only sandbox violations will be reported, all other crashes will be ignored.
Sandbox bounds: [0x7abe00000000,0x7bbe00000000)
=================================================================
==1925554==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x7bff03631810 at pc 0x5555595f4299 bp 0x7fffffffcfa0 sp 0x7fffffffcf98
READ of size 8 at 0x7bff03631810 thread T0
    #0 0x5555595f4298 in operator unsigned long src/bigint/bigint.h:171:7
    #1 0x5555595f4298 in v8::bigint::AddAndReturnOverflow(v8::bigint::RWDigits, v8::bigint::Digits) src/bigint/vector-arithmetic.cc:19:23
    #2 0x5555596052f6 in v8::bigint::ProcessorImpl::MultiplyToomCook(v8::bigint::RWDigits, v8::bigint::Digits, v8::bigint::Digits) src/bigint/mul-toom.cc:217:7
    #3 0x5555595d0c8d in v8::bigint::ProcessorImpl::Multiply(v8::bigint::RWDigits, v8::bigint::Digits, v8::bigint::Digits) src/bigint/bigint-internal.cc:48:39
    #4 0x5555595fae88 in v8::bigint::ProcessorImpl::DivideBarrett(v8::bigint::RWDigits, v8::bigint::RWDigits, v8::bigint::Digits, v8::bigint::Digits, v8::bigint::Digits, v8::bigint::RWDigits) src/bigint/div-barrett.cc:245:3
    #5 0x5555595fbfe0 in v8::bigint::ProcessorImpl::DivideBarrett(v8::bigint::RWDigits, v8::bigint::RWDigits, v8::bigint::Digits, v8::bigint::Digits) src/bigint/div-barrett.cc:361:5
    #6 0x5555595d2729 in v8::bigint::ProcessorImpl::Modulo(v8::bigint::RWDigits, v8::bigint::Digits, v8::bigint::Digits) src/bigint/bigint-internal.cc:124:5
    #7 0x5555595d3013 in v8::bigint::Processor::Modulo(v8::bigint::RWDigits, v8::bigint::Digits, v8::bigint::Digits) src/bigint/bigint-internal.cc:143:9
    #8 0x5555577e9c2c in v8::internal::MutableBigInt_AbsoluteModAndCanonicalize(unsigned long, unsigned long, unsigned long) src/objects/bigint.cc:1569:56
    #9 0x55555b7448e8 in Builtins_BigIntModulusNoThrow setup-isolate-deserialize.cc
    #10 0x55555b6c8850 in Builtins_Modulus_WithFeedback setup-isolate-deserialize.cc
    #11 0x5555bb641860  (<unknown module>)
    #12 0x55555b64c55b in Builtins_JSEntryTrampoline setup-isolate-deserialize.cc
    #13 0x55555b64c2aa in Builtins_JSEntry setup-isolate-deserialize.cc
    #14 0x55555703e79b in Call src/execution/simulator.h:212:12
    #15 0x55555703e79b in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:442:22
    #16 0x55555703fd58 in v8::internal::Execution::CallScript(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>) src/execution/execution.cc:542:10
    #17 0x555556cbe7dd in v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) src/api/api.cc:1964:7
    #18 0x555556911fc6 in v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) src/d8/d8.cc:1036:44
    #19 0x55555694949d in v8::SourceGroup::Execute(v8::Isolate*) src/d8/d8.cc:5480:10
    #20 0x555556955293 in v8::Shell::RunMainIsolate(v8::Isolate*, bool) src/d8/d8.cc:6436:37
    #21 0x5555569546c5 in v8::Shell::RunMain(v8::Isolate*, bool) src/d8/d8.cc:6344:18
    #22 0x555556957da7 in v8::Shell::Main(int, char**) src/d8/d8.cc:7234:18
    #23 0x7ffff7c8f1c9 in __libc_start_call_main csu/../sysdeps/nptl/libc_start_call_main.h:58:16
    #24 0x7ffff7c8f28a in __libc_start_main csu/../csu/libc-start.c:360:3
    #25 0x555556805029 in _start (/work/v8-build-vanilla/v8/out/vanilla/d8+0x12b1029) (BuildId: b9b906c0aa8d3d0b)

0x7bff03631810 is located 0 bytes after 237584-byte region [0x7bff035f7800,0x7bff03631810)
allocated by thread T0 here:
    #0 0x5555568dfa6d in operator new[](unsigned long) (/work/v8-build-vanilla/v8/out/vanilla/d8+0x138ba6d) (BuildId: b9b906c0aa8d3d0b)
    #1 0x5555595fbae2 in Storage src/bigint/bigint-internal.h:140:43
    #2 0x5555595fbae2 in ScratchDigits src/bigint/bigint-internal.h:151:66
    #3 0x5555595fbae2 in v8::bigint::ProcessorImpl::DivideBarrett(v8::bigint::RWDigits, v8::bigint::RWDigits, v8::bigint::Digits, v8::bigint::Digits) src/bigint/div-barrett.cc:306:17
    #4 0x5555595d2729 in v8::bigint::ProcessorImpl::Modulo(v8::bigint::RWDigits, v8::bigint::Digits, v8::bigint::Digits) src/bigint/bigint-internal.cc:124:5
    #5 0x5555595d3013 in v8::bigint::Processor::Modulo(v8::bigint::RWDigits, v8::bigint::Digits, v8::bigint::Digits) src/bigint/bigint-internal.cc:143:9
    #6 0x5555577e9c2c in v8::internal::MutableBigInt_AbsoluteModAndCanonicalize(unsigned long, unsigned long, unsigned long) src/objects/bigint.cc:1569:56
    #7 0x55555b7448e8 in Builtins_BigIntModulusNoThrow setup-isolate-deserialize.cc
    #8 0x55555b6c8850 in Builtins_Modulus_WithFeedback setup-isolate-deserialize.cc
    #9 0x5555bb641860  (<unknown module>)
    #10 0x55555b64c55b in Builtins_JSEntryTrampoline setup-isolate-deserialize.cc
    #11 0x55555b64c2aa in Builtins_JSEntry setup-isolate-deserialize.cc
    #12 0x55555703e79b in Call src/execution/simulator.h:212:12
    #13 0x55555703e79b in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:442:22
    #14 0x55555703fd58 in v8::internal::Execution::CallScript(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>) src/execution/execution.cc:542:10
    #15 0x555556cbe7dd in v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) src/api/api.cc:1964:7
    #16 0x555556911fc6 in v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) src/d8/d8.cc:1036:44
    #17 0x55555694949d in v8::SourceGroup::Execute(v8::Isolate*) src/d8/d8.cc:5480:10
    #18 0x555556955293 in v8::Shell::RunMainIsolate(v8::Isolate*, bool) src/d8/d8.cc:6436:37
    #19 0x5555569546c5 in v8::Shell::RunMain(v8::Isolate*, bool) src/d8/d8.cc:6344:18
    #20 0x555556957da7 in v8::Shell::Main(int, char**) src/d8/d8.cc:7234:18
    #21 0x7ffff7c8f1c9 in __libc_start_call_main csu/../sysdeps/nptl/libc_start_call_main.h:58:16
    #22 0x7ffff7c8f28a in __libc_start_main csu/../csu/libc-start.c:360:3
    #23 0x555556805029 in _start (/work/v8-build-vanilla/v8/out/vanilla/d8+0x12b1029) (BuildId: b9b906c0aa8d3d0b)

SUMMARY: AddressSanitizer: heap-buffer-overflow src/bigint/bigint.h:171:7 in operator unsigned long
Shadow bytes around the buggy address:
  0x7bff03631580: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x7bff03631600: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x7bff03631680: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x7bff03631700: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x7bff03631780: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
=>0x7bff03631800: 00 00[fa]fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x7bff03631880: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x7bff03631900: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x7bff03631980: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x7bff03631a00: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x7bff03631a80: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
Shadow byte legend (one shadow byte represents 8 application bytes):
  Addressable:           00
  Partially addressable: 01 02 03 04 05 06 07 
  Heap left redzone:       fa
  Freed heap region:       fd
  Stack left redzone:      f1
  Stack mid redzone:       f2
  Stack right redzone:     f3
  Stack after return:      f5
  Stack use after scope:   f8
  Global redzone:          f9
  Global init order:       f6
  Poisoned by user:        f7
  Container overflow:      fc
  Array cookie:            ac
  Intra object redzone:    bb
  ASan internal:           fe
  Left alloca redzone:     ca
  Right alloca redzone:    cb
==1925554==ABORTING

## V8 sandbox violation detected!
```

Report for b5aa4c8b718d75f9cf4d4afd635ffd217f0acb38 using the provided reproducer with ASan that ignores OOB reads:

```
==1947368==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x7bfff584d810 at pc 0x55555d1cf3a8 bp 0x7fffffffcd20 sp 0x7fffffffcd18
WRITE of size 8 at 0x7bfff584d810 thread T0
    #0 0x55555d1cf3a7 in v8::bigint::AddAndReturnOverflow(v8::bigint::RWDigits, v8::bigint::Digits) src/bigint/bigint.h:162:37
    #1 0x55555d1e806e in v8::bigint::ProcessorImpl::MultiplyToomCook(v8::bigint::RWDigits, v8::bigint::Digits, v8::bigint::Digits) src/bigint/mul-toom.cc:217:7
    #2 0x55555d1a5d29 in v8::bigint::ProcessorImpl::Multiply(v8::bigint::RWDigits, v8::bigint::Digits, v8::bigint::Digits) src/bigint/bigint-internal.cc:48:39
    #3 0x55555d1d6c03 in v8::bigint::ProcessorImpl::DivideBarrett(v8::bigint::RWDigits, v8::bigint::RWDigits, v8::bigint::Digits, v8::bigint::Digits, v8::bigint::Digits, v8::bigint::RWDigits) src/bigint/div-barrett.cc:245:3
    #4 0x55555d1d8626 in v8::bigint::ProcessorImpl::DivideBarrett(v8::bigint::RWDigits, v8::bigint::RWDigits, v8::bigint::Digits, v8::bigint::Digits) src/bigint/div-barrett.cc:361:5
    #5 0x55555d1a77c1 in v8::bigint::ProcessorImpl::Modulo(v8::bigint::RWDigits, v8::bigint::Digits, v8::bigint::Digits) src/bigint/bigint-internal.cc:124:5
    #6 0x55555d1a84cd in v8::bigint::Processor::Modulo(v8::bigint::RWDigits, v8::bigint::Digits, v8::bigint::Digits) src/bigint/bigint-internal.cc:143:9
    #7 0x55555965f63e in v8::internal::MutableBigInt_AbsoluteModAndCanonicalize(unsigned long, unsigned long, unsigned long) src/objects/bigint.cc:1569:56
    #8 0x55556107dae8 in Builtins_BigIntModulusNoThrow setup-isolate-deserialize.cc
    #9 0x55556112e84b in Builtins_ModHandler setup-isolate-deserialize.cc
    #10 0x555560f889a9 in Builtins_InterpreterEntryTrampoline setup-isolate-deserialize.cc
    #11 0x555560f8575b in Builtins_JSEntryTrampoline setup-isolate-deserialize.cc
    #12 0x555560f854aa in Builtins_JSEntry setup-isolate-deserialize.cc
    #13 0x55555869bfeb in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/simulator.h:212:12
    #14 0x55555869f3e7 in v8::internal::Execution::CallScript(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>) src/execution/execution.cc:542:10
    #15 0x555557f03c56 in v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) src/api/api.cc:1964:7
    #16 0x5555578d4c25 in v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) src/d8/d8.cc:1040:44
    #17 0x555557947f28 in v8::SourceGroup::Execute(v8::Isolate*) src/d8/d8.cc:5502:10
    #18 0x55555795e60e in v8::Shell::RunMainIsolate(v8::Isolate*, bool) src/d8/d8.cc:6458:37
    #19 0x55555795d125 in v8::Shell::RunMain(v8::Isolate*, bool) src/d8/d8.cc:6366:18
    #20 0x555557964989 in v8::Shell::Main(int, char**) src/d8/d8.cc:7310:18
    #21 0x7ffff796b1c9 in __libc_start_call_main csu/../sysdeps/nptl/libc_start_call_main.h:58:16
    #22 0x7ffff796b28a in __libc_start_main csu/../csu/libc-start.c:360:3
    #23 0x5555577db029 in _start (FuzzingSuppressReadsO1/d8+0x2287029) (BuildId: ba8fbe419f72dad4)

0x7bfff584d810 is located 0 bytes after 237584-byte region [0x7bfff5813800,0x7bfff584d810)
allocated by thread T0 here:
    #0 0x555557877c1d in operator new[](unsigned long) /work/llvm-project/compiler-rt/lib/asan/asan_new_delete.cpp:89:3
    #1 0x55555d1d800b in v8::bigint::ProcessorImpl::DivideBarrett(v8::bigint::RWDigits, v8::bigint::RWDigits, v8::bigint::Digits, v8::bigint::Digits) src/bigint/bigint-internal.h:140:43
    #2 0x55555d1a77c1 in v8::bigint::ProcessorImpl::Modulo(v8::bigint::RWDigits, v8::bigint::Digits, v8::bigint::Digits) src/bigint/bigint-internal.cc:124:5
    #3 0x55555d1a84cd in v8::bigint::Processor::Modulo(v8::bigint::RWDigits, v8::bigint::Digits, v8::bigint::Digits) src/bigint/bigint-internal.cc:143:9
    #4 0x55555965f63e in v8::internal::MutableBigInt_AbsoluteModAndCanonicalize(unsigned long, unsigned long, unsigned long) src/objects/bigint.cc:1569:56
    #5 0x55556107dae8 in Builtins_BigIntModulusNoThrow setup-isolate-deserialize.cc
    #6 0x55556112e84b in Builtins_ModHandler setup-isolate-deserialize.cc
    #7 0x555560f889a9 in Builtins_InterpreterEntryTrampoline setup-isolate-deserialize.cc
    #8 0x555560f8575b in Builtins_JSEntryTrampoline setup-isolate-deserialize.cc
    #9 0x555560f854aa in Builtins_JSEntry setup-isolate-deserialize.cc
    #10 0x55555869bfeb in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/simulator.h:212:12
    #11 0x55555869f3e7 in v8::internal::Execution::CallScript(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>) src/execution/execution.cc:542:10
    #12 0x555557f03c56 in v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) src/api/api.cc:1964:7
    #13 0x5555578d4c25 in v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) src/d8/d8.cc:1040:44
    #14 0x555557947f28 in v8::SourceGroup::Execute(v8::Isolate*) src/d8/d8.cc:5502:10
    #15 0x55555795e60e in v8::Shell::RunMainIsolate(v8::Isolate*, bool) src/d8/d8.cc:6458:37
    #16 0x55555795d125 in v8::Shell::RunMain(v8::Isolate*, bool) src/d8/d8.cc:6366:18
    #17 0x555557964989 in v8::Shell::Main(int, char**) src/d8/d8.cc:7310:18
    #18 0x7ffff796b1c9 in __libc_start_call_main csu/../sysdeps/nptl/libc_start_call_main.h:58:16
    #19 0x7ffff796b28a in __libc_start_main csu/../csu/libc-start.c:360:3
    #20 0x5555577db029 in _start (FuzzingSuppressReadsO1/d8+0x2287029) (BuildId: ba8fbe419f72dad4)

SUMMARY: AddressSanitizer: heap-buffer-overflow src/bigint/bigint.h:162:37 in v8::bigint::AddAndReturnOverflow(v8::bigint::RWDigits, v8::bigint::Digits)
Shadow bytes around the buggy address:
  0x7bfff584d580: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x7bfff584d600: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x7bfff584d680: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x7bfff584d700: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x7bfff584d780: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
=>0x7bfff584d800: 00 00[fa]fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x7bfff584d880: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x7bfff584d900: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x7bfff584d980: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x7bfff584da00: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x7bfff584da80: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
Shadow byte legend (one shadow byte represents 8 application bytes):
  Addressable:           00
  Partially addressable: 01 02 03 04 05 06 07 
  Heap left redzone:       fa
  Freed heap region:       fd
  Stack left redzone:      f1
  Stack mid redzone:       f2
  Stack right redzone:     f3
  Stack after return:      f5
  Stack use after scope:   f8
  Global redzone:          f9
  Global init order:       f6
  Poisoned by user:        f7
  Container overflow:      fc
  Array cookie:            ac
  Intra object redzone:    bb
  ASan internal:           fe
  Left alloca redzone:     ca
  Right alloca redzone:    cb
==1947368==ABORTING
[!] SanitizerFaultHandler()
[!] Received ASan report
Fault Address : 0x7bfff584d810
Description   : heap-buffer-overflow

## V8 sandbox violation detected!
```


---

**#2 — cl...@appspot.gserviceaccount.com — Sep 10, 2025 11:40PM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5597536865681408](<https://clusterfuzz.com/testcase?key=5597536865681408>).


---

**#3 — cl...@appspot.gserviceaccount.com — Sep 10, 2025 11:57PM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5821550246690816](<https://clusterfuzz.com/testcase?key=5821550246690816>).


---

**#4 — 24...@project.gserviceaccount.com — Sep 11, 2025 12:42AM**

Automatically applying components based on crash stacktrace and information from OWNERS files.  
  
If this is incorrect, please apply the hotlistid:4801165.


---

**#5 — 24...@project.gserviceaccount.com — Sep 11, 2025 12:42AM**

Detailed Report: [https://clusterfuzz.com/testcase?key=5821550246690816](<https://clusterfuzz.com/testcase?key=5821550246690816>)  
  
Fuzzer: None  
Job Type: linux_asan_d8_sandbox_testing  
Platform Id: linux  
  
Crash Type: V8 sandbox violation  
Crash Address: 0x75844ca12810  
Crash State:  
v8::bigint::RWDigits::WritableDigitReference::operator unsigned long  
v8::bigint::AddAndReturnOverflow  
v8::bigint::ProcessorImpl::MultiplyToomCook  
  
Sanitizer: address (ASAN)  
  
Crash Revision: [https://clusterfuzz.com/revisions?job=linux_asan_d8_sandbox_testing&revision=102382](<https://clusterfuzz.com/revisions?job=linux_asan_d8_sandbox_testing&revision=102382>)  
  
Reproducer Testcase: [https://clusterfuzz.com/download?testcase_id=5821550246690816](<https://clusterfuzz.com/download?testcase_id=5821550246690816>)  
  
To reproduce this, please build the target in this report and run it against the reproducer testcase. Please use the GN arguments provided at bottom of this report when building the binary.  
  
If you have trouble reproducing, please also export the environment variables listed under "[Environment]" in the crash stacktrace.  
  
If you have any feedback on reproducing test cases, let us know at [https://forms.gle/Yh3qCYFveHj6E5jz5](<https://forms.gle/Yh3qCYFveHj6E5jz5>) so we can improve.


---

**#6 — sk...@google.com — Sep 11, 2025 03:23AM**

Clusterfuzz reproduced the bug, setting a provisional severity/priority


---

**#7 — ml...@google.com — Sep 11, 2025 05:28PM**

Jakob, can you have a first look here?


---

**#8 — dx...@google.com — Sep 11, 2025 09:50PM**

Project: v8/v8  
Branch: main  
Author: Jakob Kummerow [jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)  
Link: [https://chromium-review.googlesource.com/6939350](<https://chromium-review.googlesource.com/6939350>)

[bigint][sandbox] Harden more against concurrent modification

* * *

Expand for full commit details

```
     
    Some additional BigInt algorithms get confused when malicious worker 
    threads concurrently mutate their inputs, which can lead to allocated 
    buffers not being large enough. This patch places a few strategic 
    CHECKs to crash safely when this happens. 
     
    Fixed: 444048032 
    Change-Id: Ide3ec821af32cb775283f8f89aa72df05f2d5454 
    Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6939350 
    Reviewed-by: Clemens Backes <clemensb@chromium.org> 
    Commit-Queue: Clemens Backes <clemensb@chromium.org> 
    Commit-Queue: Jakob Kummerow <jkummerow@chromium.org> 
    Auto-Submit: Jakob Kummerow <jkummerow@chromium.org> 
    Cr-Commit-Position: refs/heads/main@{#102412}
```

* * *

Files:

  * M `src/bigint/vector-arithmetic.cc`

* * *

Hash: [28c02e0c7bb14704cc328b00a84782214d22f48a](<https://chromiumdash.appspot.com/commit/28c02e0c7bb14704cc328b00a84782214d22f48a>)  
Date: Thu Sep 11 12:06:07 2025

* * *


---

**#9 — sp...@google.com — Sep 20, 2025 04:56AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $5000.00 for this report.  
  
Rationale for this decision:  
v8 sandbox bypass with uncontrolled write  
  
  
Important: This payment will be issued by Bugcrowd. You will receive an email from Bugcrowd in the next 24 hours which contains a submission you must claim to be rewarded.  
  
If you do not receive an email from them, please check your spam folder and then reach out to us via a comment here. For issues related to Bugcrowd itself, please contact them via [https://bugcrowd.com/support](<https://bugcrowd.com/support>).  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#10 — ch...@google.com — Dec 19, 2025 09:41PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.


---

**#11 — ch...@google.com — Dec 19, 2025 09:43PM**

This V8 bug has been marked as either a release blocker or a vulnerability bug. V8 bugs affect all OSs supported by Chrome, so the OS field has been updated to reflect this. Please update the bug with the correct OS field if it only affects a subset of OSes.
