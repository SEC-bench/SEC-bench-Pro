# V8 Sandbox Bypass: OOB write in JsonStringifier::SerializeString

Issue URL: https://issues.chromium.org/issues/388437270
VRP-Reward: 5000
Date: Jan 8, 2025 11:33PM


#### VULNERABILITY DETAILS

Changing a string value that has been embedded into a `FixedArray` causes an out-of-bounds write during JSON serialization.

#### VERSION

V8 commit: 4715559d4fe2ce6e2c0f6de3c966347b6da6a489

#### REPRODUCTION CASE

Build args:

```
is_debug=false
is_asan=true
v8_enable_sandbox=true
v8_enable_memory_corruption_api=true
dcheck_always_on=false
v8_static_library=true
v8_fuzzilli=false
target_cpu="x64"
```

Shell args: `d8 --single-threaded --sandbox-fuzzing --allow-natives-syntax --expose-gc bug.js`

##### ASAN Report:

```
==1363666==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x521000049900 at pc 0x555556dbcbdc bp 0x7fffffffb9c0 sp 0x7fffffffb9b8
WRITE of size 2 at 0x521000049900 thread T0
    #0 0x555556dbcbdb in std::__Cr::pair<unsigned char const*, unsigned short*> std::__Cr::__copy_impl::operator()<unsigned char const*, unsigned char const*, unsigned short*>(unsigned char const*, unsigned char const*, unsigned short*) const third_party/libc++/src/include/__algorithm/copy.h:40:17
    #1 0x555556dbcbdb in std::__Cr::pair<unsigned char const*, unsigned short*> std::__Cr::__copy_move_unwrap_iters<std::__Cr::__copy_impl, unsigned char const*, unsigned char const*, unsigned short*, 0>(unsigned char const*, unsigned char const*, unsigned short*) third_party/libc++/src/include/__algorithm/copy_move_common.h:94:19
    #2 0x555556dbcbdb in std::__Cr::pair<unsigned char const*, unsigned short*> std::__Cr::__copy<unsigned char const*, unsigned char const*, unsigned short*>(unsigned char const*, unsigned char const*, unsigned short*) third_party/libc++/src/include/__algorithm/copy.h:109:10
    #3 0x555556dbcbdb in unsigned short* std::__Cr::copy<unsigned char const*, unsigned short*>(unsigned char const*, unsigned char const*, unsigned short*) third_party/libc++/src/include/__algorithm/copy.h:115:10
    #4 0x555556dbcbdb in unsigned short* std::__Cr::copy_n<unsigned char const*, unsigned long, unsigned short*, 0>(unsigned char const*, unsigned long, unsigned short*) third_party/libc++/src/include/__algorithm/copy_n.h:55:10
    #5 0x555556dbcbdb in void v8::internal::CopyChars<unsigned char, unsigned short>(unsigned short*, unsigned char const*, unsigned long) src/utils/memcopy.h:398:7
    #6 0x555557dc14b0 in void v8::internal::JsonStringifier::AppendSubstringByCopy<unsigned char>(unsigned char const*, int) src/json/json-stringifier.cc:212:7
    #7 0x555557d96674 in bool v8::internal::JsonStringifier::SerializeString_<unsigned char, unsigned short, false>(v8::internal::Tagged<v8::internal::String>, v8::internal::PerThreadAssertScopeEmpty<false, (v8::internal::PerThreadAssertType)1, (v8::internal::PerThreadAssertType)2> const&) src/json/json-stringifier.cc:1588:5
    #8 0x555557d96674 in bool v8::internal::JsonStringifier::SerializeString<false>(v8::internal::Handle<v8::internal::String>) src/json/json-stringifier.cc:1694:12
    #9 0x555557da9d5d in v8::internal::JsonStringifier::Result v8::internal::JsonStringifier::Serialize_<false>(v8::internal::Handle<v8::internal::Union<v8::internal::Smi, v8::internal::HeapNumber, v8::internal::BigInt, v8::internal::String, v8::internal::Symbol, v8::internal::Boolean, v8::internal::Null, v8::internal::Undefined, v8::internal::JSReceiver>>, bool, v8::internal::Handle<v8::internal::Object>) src/json/json-stringifier.cc:1006:9
    #10 0x555557dae7e5 in v8::internal::JsonStringifier::SerializeElement(v8::internal::Isolate*, v8::internal::Handle<v8::internal::Union<v8::internal::Smi, v8::internal::HeapNumber, v8::internal::BigInt, v8::internal::String, v8::internal::Symbol, v8::internal::Boolean, v8::internal::Null, v8::internal::Undefined, v8::internal::JSReceiver>>, int) src/json/json-stringifier.cc:66:12
    #11 0x555557dae7e5 in v8::internal::JsonStringifier::Result v8::internal::JsonStringifier::SerializeFixedArrayWithPossibleTransitions<(v8::internal::ElementsKind)2>(v8::internal::DirectHandle<v8::internal::JSArray>, unsigned int, unsigned int*) src/json/json-stringifier.cc:1212:23
    #12 0x555557dae7e5 in v8::internal::JsonStringifier::SerializeJSArray(v8::internal::Handle<v8::internal::JSArray>, v8::internal::Handle<v8::internal::Object>) src/json/json-stringifier.cc:1115:7
    #13 0x555557dae7e5 in v8::internal::JsonStringifier::Result v8::internal::JsonStringifier::Serialize_<false>(v8::internal::Handle<v8::internal::Union<v8::internal::Smi, v8::internal::HeapNumber, v8::internal::BigInt, v8::internal::String, v8::internal::Symbol, v8::internal::Boolean, v8::internal::Null, v8::internal::Undefined, v8::internal::JSReceiver>>, bool, v8::internal::Handle<v8::internal::Object>) src/json/json-stringifier.cc:961:14
    #14 0x555557d826e1 in v8::internal::JsonStringifier::SerializeObject(v8::internal::Handle<v8::internal::Union<v8::internal::Smi, v8::internal::HeapNumber, v8::internal::BigInt, v8::internal::String, v8::internal::Symbol, v8::internal::Boolean, v8::internal::Null, v8::internal::Undefined, v8::internal::JSReceiver>>) src/json/json-stringifier.cc:59:12
    #15 0x555557d826e1 in v8::internal::JsonStringifier::Stringify(v8::internal::Handle<v8::internal::Union<v8::internal::Smi, v8::internal::HeapNumber, v8::internal::BigInt, v8::internal::String, v8::internal::Symbol, v8::internal::Boolean, v8::internal::Null, v8::internal::Undefined, v8::internal::JSReceiver>>, v8::internal::Handle<v8::internal::Union<v8::internal::Smi, v8::internal::HeapNumber, v8::internal::BigInt, v8::internal::String, v8::internal::Symbol, v8::internal::Boolean, v8::internal::Null, v8::internal::Undefined, v8::internal::JSReceiver>>, v8::internal::Handle<v8::internal::Object>) src/json/json-stringifier.cc:558:19
    #16 0x555557da4a42 in v8::internal::JsonStringify(v8::internal::Isolate*, v8::internal::Handle<v8::internal::Union<v8::internal::Smi, v8::internal::HeapNumber, v8::internal::BigInt, v8::internal::String, v8::internal::Symbol, v8::internal::Boolean, v8::internal::Null, v8::internal::Undefined, v8::internal::JSReceiver>>, v8::internal::Handle<v8::internal::Union<v8::internal::Smi, v8::internal::HeapNumber, v8::internal::BigInt, v8::internal::String, v8::internal::Symbol, v8::internal::Boolean, v8::internal::Null, v8::internal::Undefined, v8::internal::JSReceiver>>, v8::internal::Handle<v8::internal::Object>) src/json/json-stringifier.cc:2798:24
    #17 0x555556d7ba48 in v8::internal::Builtin_Impl_JsonStringify(v8::internal::BuiltinArguments, v8::internal::Isolate*) src/builtins/builtins-json.cc:37:3
    #18 0x55555e3dc475 in Builtins_CEntry_Return1_ArgvOnStack_BuiltinExit setup-isolate-deserialize.cc
    #19 0x55555e330c40 in Builtins_InterpreterEntryTrampoline setup-isolate-deserialize.cc
    #20 0x55555e32e85b in Builtins_JSEntryTrampoline setup-isolate-deserialize.cc
    #21 0x55555e32e5aa in Builtins_JSEntry setup-isolate-deserialize.cc
    #22 0x5555572dc132 in v8::internal::GeneratedCode<unsigned long, unsigned long, unsigned long, unsigned long, unsigned long, long, unsigned long**>::Call(unsigned long, unsigned long, unsigned long, unsigned long, long, unsigned long**) src/execution/simulator.h:191:12
    #23 0x5555572dc132 in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:436:22
    #24 0x5555572df229 in v8::internal::Execution::CallScript(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>) src/execution/execution.cc:536:10
    #25 0x555556bac947 in v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) src/api/api.cc:2155:7
    #26 0x555556801cba in v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) src/d8/d8.cc:1017:44
    #27 0x555556850679 in v8::SourceGroup::Execute(v8::Isolate*) src/d8/d8.cc:4962:10
    #28 0x555556864382 in v8::Shell::RunMainIsolate(v8::Isolate*, bool) src/d8/d8.cc:5906:37
    #29 0x5555568632e3 in v8::Shell::RunMain(v8::Isolate*, bool) src/d8/d8.cc:5815:18
    #30 0x5555568691fd in v8::Shell::Main(int, char**) src/d8/d8.cc:6700:18
    #31 0x7fffbf91f1c9 in __libc_start_call_main csu/../sysdeps/nptl/libc_start_call_main.h:58:16
    #32 0x7fffbf91f28a in __libc_start_main csu/../csu/libc-start.c:360:3
    #33 0x555556687029 in _start (/work/v8-build/v8/out/FuzzingSuppressReadsO1/d8+0x1133029) (BuildId: b464b5e14fdd1c7f)

0x521000049900 is located 0 bytes after 4096-byte region [0x521000048900,0x521000049900)
allocated by thread T0 here:
    #0 0x5555567b3068 in operator new[](unsigned long) /work/llvm-project/compiler-rt/lib/asan/asan_new_delete.cpp:89:3
    #1 0x555557d86425 in v8::internal::JsonStringifier::ChangeEncoding() src/json/json-stringifier.cc:1727:19
    #2 0x555557d93a25 in bool v8::internal::JsonStringifier::SerializeString<false>(v8::internal::Handle<v8::internal::String>) src/json/json-stringifier.cc:1689:7
    #3 0x555557da9d5d in v8::internal::JsonStringifier::Result v8::internal::JsonStringifier::Serialize_<false>(v8::internal::Handle<v8::internal::Union<v8::internal::Smi, v8::internal::HeapNumber, v8::internal::BigInt, v8::internal::String, v8::internal::Symbol, v8::internal::Boolean, v8::internal::Null, v8::internal::Undefined, v8::internal::JSReceiver>>, bool, v8::internal::Handle<v8::internal::Object>) src/json/json-stringifier.cc:1006:9
    #4 0x555557dae7e5 in v8::internal::JsonStringifier::SerializeElement(v8::internal::Isolate*, v8::internal::Handle<v8::internal::Union<v8::internal::Smi, v8::internal::HeapNumber, v8::internal::BigInt, v8::internal::String, v8::internal::Symbol, v8::internal::Boolean, v8::internal::Null, v8::internal::Undefined, v8::internal::JSReceiver>>, int) src/json/json-stringifier.cc:66:12
    #5 0x555557dae7e5 in v8::internal::JsonStringifier::Result v8::internal::JsonStringifier::SerializeFixedArrayWithPossibleTransitions<(v8::internal::ElementsKind)2>(v8::internal::DirectHandle<v8::internal::JSArray>, unsigned int, unsigned int*) src/json/json-stringifier.cc:1212:23
    #6 0x555557dae7e5 in v8::internal::JsonStringifier::SerializeJSArray(v8::internal::Handle<v8::internal::JSArray>, v8::internal::Handle<v8::internal::Object>) src/json/json-stringifier.cc:1115:7
    #7 0x555557dae7e5 in v8::internal::JsonStringifier::Result v8::internal::JsonStringifier::Serialize_<false>(v8::internal::Handle<v8::internal::Union<v8::internal::Smi, v8::internal::HeapNumber, v8::internal::BigInt, v8::internal::String, v8::internal::Symbol, v8::internal::Boolean, v8::internal::Null, v8::internal::Undefined, v8::internal::JSReceiver>>, bool, v8::internal::Handle<v8::internal::Object>) src/json/json-stringifier.cc:961:14
    #8 0x555557d826e1 in v8::internal::JsonStringifier::SerializeObject(v8::internal::Handle<v8::internal::Union<v8::internal::Smi, v8::internal::HeapNumber, v8::internal::BigInt, v8::internal::String, v8::internal::Symbol, v8::internal::Boolean, v8::internal::Null, v8::internal::Undefined, v8::internal::JSReceiver>>) src/json/json-stringifier.cc:59:12
    #9 0x555557d826e1 in v8::internal::JsonStringifier::Stringify(v8::internal::Handle<v8::internal::Union<v8::internal::Smi, v8::internal::HeapNumber, v8::internal::BigInt, v8::internal::String, v8::internal::Symbol, v8::internal::Boolean, v8::internal::Null, v8::internal::Undefined, v8::internal::JSReceiver>>, v8::internal::Handle<v8::internal::Union<v8::internal::Smi, v8::internal::HeapNumber, v8::internal::BigInt, v8::internal::String, v8::internal::Symbol, v8::internal::Boolean, v8::internal::Null, v8::internal::Undefined, v8::internal::JSReceiver>>, v8::internal::Handle<v8::internal::Object>) src/json/json-stringifier.cc:558:19
    #10 0x555557da4a42 in v8::internal::JsonStringify(v8::internal::Isolate*, v8::internal::Handle<v8::internal::Union<v8::internal::Smi, v8::internal::HeapNumber, v8::internal::BigInt, v8::internal::String, v8::internal::Symbol, v8::internal::Boolean, v8::internal::Null, v8::internal::Undefined, v8::internal::JSReceiver>>, v8::internal::Handle<v8::internal::Union<v8::internal::Smi, v8::internal::HeapNumber, v8::internal::BigInt, v8::internal::String, v8::internal::Symbol, v8::internal::Boolean, v8::internal::Null, v8::internal::Undefined, v8::internal::JSReceiver>>, v8::internal::Handle<v8::internal::Object>) src/json/json-stringifier.cc:2798:24
    #11 0x555556d7ba48 in v8::internal::Builtin_Impl_JsonStringify(v8::internal::BuiltinArguments, v8::internal::Isolate*) src/builtins/builtins-json.cc:37:3
    #12 0x55555e3dc475 in Builtins_CEntry_Return1_ArgvOnStack_BuiltinExit setup-isolate-deserialize.cc
    #13 0x55555e330c40 in Builtins_InterpreterEntryTrampoline setup-isolate-deserialize.cc
    #14 0x55555e32e85b in Builtins_JSEntryTrampoline setup-isolate-deserialize.cc
    #15 0x55555e32e5aa in Builtins_JSEntry setup-isolate-deserialize.cc
    #16 0x5555572dc132 in v8::internal::GeneratedCode<unsigned long, unsigned long, unsigned long, unsigned long, unsigned long, long, unsigned long**>::Call(unsigned long, unsigned long, unsigned long, unsigned long, long, unsigned long**) src/execution/simulator.h:191:12
    #17 0x5555572dc132 in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:436:22
    #18 0x5555572df229 in v8::internal::Execution::CallScript(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>) src/execution/execution.cc:536:10
    #19 0x555556bac947 in v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) src/api/api.cc:2155:7
    #20 0x555556801cba in v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) src/d8/d8.cc:1017:44
    #21 0x555556850679 in v8::SourceGroup::Execute(v8::Isolate*) src/d8/d8.cc:4962:10
    #22 0x555556864382 in v8::Shell::RunMainIsolate(v8::Isolate*, bool) src/d8/d8.cc:5906:37
    #23 0x5555568632e3 in v8::Shell::RunMain(v8::Isolate*, bool) src/d8/d8.cc:5815:18
    #24 0x5555568691fd in v8::Shell::Main(int, char**) src/d8/d8.cc:6700:18
    #25 0x7fffbf91f1c9 in __libc_start_call_main csu/../sysdeps/nptl/libc_start_call_main.h:58:16
    #26 0x7fffbf91f28a in __libc_start_main csu/../csu/libc-start.c:360:3
    #27 0x555556687029 in _start (/work/v8-build/v8/out/FuzzingSuppressReadsO1/d8+0x1133029) (BuildId: b464b5e14fdd1c7f)

SUMMARY: AddressSanitizer: heap-buffer-overflow third_party/libc++/src/include/__algorithm/copy.h:40:17 in std::__Cr::pair<unsigned char const*, unsigned short*> std::__Cr::__copy_impl::operator()<unsigned char const*, unsigned char const*, unsigned short*>(unsigned char const*, unsigned char const*, unsigned short*) const
Shadow bytes around the buggy address:
  0x521000049680: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x521000049700: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x521000049780: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x521000049800: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x521000049880: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
=>0x521000049900:[fa]fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x521000049980: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x521000049a00: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x521000049a80: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x521000049b00: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x521000049b80: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
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
==1363666==ABORTING

## V8 sandbox violation detected!
```

#### CREDIT INFORMATION

Reporter credit: v8sbxfuzz


---

**#2 — v8...@gmail.com — Jan 9, 2025 12:02AM**

I just noticed this does not reproduce on a vanilla build, but I don't know why. I will update this if I get the reproducer running.


---

**#3 — cl...@appspot.gserviceaccount.com — Jan 9, 2025 07:26PM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=6583838679433216](<https://clusterfuzz.com/testcase?key=6583838679433216>).


---

**#4 — cl...@appspot.gserviceaccount.com — Jan 9, 2025 07:27PM**

ClusterFuzz is analyzing your testcase. Developers can follow the progress at [https://clusterfuzz.com/testcase?key=5601148954148864](<https://clusterfuzz.com/testcase?key=5601148954148864>).


---

**#5 — sa...@google.com — Jan 9, 2025 07:38PM**

I'm so far not able to reproduce this issue, unfortunately. I've tried it on Clusterfuzz, but also locally with the exact same gn args and on the specified revision. The output I get is always

```
Sandbox testing mode is enabled. Only sandbox violations will be reported, all other crashes will be ignored.
o_addr: 4a440
found: 0x4a438
Caught harmless memory access violation (inside sandbox address space). Exiting process...
```

And the (harmless) crash happens here:

```
#0  0x000055555734812d in __cxx_atomic_load<short> () at ../../third_party/libc++/src/include/__atomic/support/c11.h:75
#1  load () at ../../third_party/libc++/src/include/__atomic/atomic.h:63
#2  atomic_load_explicit<short> () at ../../third_party/libc++/src/include/__atomic/atomic.h:524
#3  Relaxed_Load () at ../../src/base/atomicops.h:240
#4  instance_type () at ../../src/objects/map.h:1118
#5  Serialize_<false> () at ../../src/json/json-stringifier.cc:907
#6  0x000055555734dbd0 in SerializeElement () at ../../src/json/json-stringifier.cc:66
#7  SerializeFixedArrayWithPossibleTransitions<(v8::internal::ElementsKind)2> () at ../../src/json/json-stringifier.cc:1212
#8  SerializeJSArray () at ../../src/json/json-stringifier.cc:1115
#9  Serialize_<false> () at ../../src/json/json-stringifier.cc:961
#10 0x0000555557332437 in SerializeObject () at ../../src/json/json-stringifier.cc:59
#11 Stringify () at ../../src/json/json-stringifier.cc:558
#12 0x0000555557345d66 in JsonStringify () at ../../src/json/json-stringifier.cc:2798
#13 0x0000555556a26299 in Builtin_Impl_JsonStringify () at ../../src/builtins/builtins-json.cc:37
#14 0x000055555ae412b6 in Builtins_CEntry_Return1_ArgvOnStack_BuiltinExit ()
#15 0x000055555ad95a81 in Builtins_InterpreterEntryTrampoline ()
```

Probably indicating that it's accessing a corrupted HeapObject pointer during serialization.

I'm testing this on a Linux machine with lots of cores and memory, but I don't think these should matter? Do you have a better understanding of what the testcase is trying to corrupt? The testcase seems to search backwards from the array that will be serialized, so I'm guessing it is looking for the FixedArray that backs the JSArray in memory (potentially you could confirm this by using `%DebugPrint()` in you testcase to print the addresses of various objects)? In my case, it finds the magic value quickly, at offset 8, so I'm assuming it corrupts a pointer (to one of the elements of the array?) and makes it point somewhere else in memory, making the testcase very dependent on heap memory layout.


---

**#6 — v8...@gmail.com — Jan 9, 2025 08:16PM**

Thanks for the hints! I restarted the fuzzer yesterday and found the bug in `5e6710454cac62520d9ffcc0a843af9d5c90644f` (revision from yesterday) as well. [Here](<https://pernos.co/debug/Gjj5Fi1DWAlEmBw3ohCtxQ/index.html#f%7Bm%5BIRw,DrdF_,t%5BAQ,O9u/_,f%7Be%5BIRw,L7U_,s%7BaVVVVVUAA,bBQ,uAhNfoA,oAhqtqQ___/>) you can find a rr trace of the bug. I tried to create a reproducer for several hours but failed to do so since the object that gets mutated is initialized by the `Builtins_ArraySingleArgumentConstructor_HoleySmi_DisableAllocationSites` builtin that I am unable to debug. Thus, I cannot determine how to get a stable reference to the target object. However, I can provide some details: The bug is triggered by mutating a "pointer" that is read here:

```
    #0 0x55555677f96e in __sanitizer_print_stack_trace /work/llvm-project/compiler-rt/lib/asan/asan_stack.cpp:87:3
    #1 0x7fffbfd1d14a in __fuzzer_before_heap_sandbox_load /work/fuzzer/runtime/src/mem_hooks.rs:158:30
    #2 0x555557d9bb31 in v8::internal::TaggedField<v8::internal::FixedArrayBase, 8, v8::internal::V8HeapCompressionSchemeImpl<v8::internal::MainCage>>::load(v8::internal::PtrComprCageBase, v8::internal::Tagged<v8::internal::HeapObject>, int) src/objects/tagged-field-inl.h:224:20
    #3 0x555557d9bb31 in v8::internal::JSObject::elements(v8::internal::PtrComprCageBase) const src/objects/js-objects-inl.h:62:10
    #4 0x555557d9bb31 in v8::internal::JSObject::elements() const src/objects/js-objects-inl.h:61:1
    #5 0x555557d9bb31 in v8::internal::JsonStringifier::Result v8::internal::JsonStringifier::SerializeFixedArrayWithPossibleTransitions<(v8::internal::ElementsKind)3>(v8::internal::DirectHandle<v8::internal::JSArray>, unsigned int, unsigned int*) src/json/json-stringifier.cc:1199:33
    #6 0x555557d9bb31 in v8::internal::JsonStringifier::SerializeJSArray(v8::internal::Handle<v8::internal::JSArray>, v8::internal::Handle<v8::internal::Object>) src/json/json-stringifier.cc:1116:7
    #7 0x555557d9bb31 in v8::internal::JsonStringifier::Result v8::internal::JsonStringifier::Serialize_<false>(v8::internal::Handle<v8::internal::Union<v8::internal::Smi, v8::internal::HeapNumber, v8::internal::BigInt, v8::internal::String, v8::internal::Symbol, v8::internal::Boolean, v8::internal::Null, v8::internal::Undefined, v8::internal::JSReceiver>>, bool, v8::internal::Handle<v8::internal::Object>) src/json/json-stringifier.cc:961:14
    #8 0x555557d9a6a5 in v8::internal::JsonStringifier::SerializeElement(v8::internal::Isolate*, v8::internal::Handle<v8::internal::Union<v8::internal::Smi, v8::internal::HeapNumber, v8::internal::BigInt, v8::internal::String, v8::internal::Symbol, v8::internal::Boolean, v8::internal::Null, v8::internal::Undefined, v8::internal::JSReceiver>>, int) src/json/json-stringifier.cc:66:12
    #9 0x555557d9a6a5 in v8::internal::JsonStringifier::Result v8::internal::JsonStringifier::SerializeFixedArrayWithPossibleTransitions<(v8::internal::ElementsKind)2>(v8::internal::DirectHandle<v8::internal::JSArray>, unsigned int, unsigned int*) src/json/json-stringifier.cc:1212:23
    #10 0x555557d9a6a5 in v8::internal::JsonStringifier::SerializeJSArray(v8::internal::Handle<v8::internal::JSArray>, v8::internal::Handle<v8::internal::Object>) src/json/json-stringifier.cc:1115:7
    #11 0x555557d9a6a5 in v8::internal::JsonStringifier::Result v8::internal::JsonStringifier::Serialize_<false>(v8::internal::Handle<v8::internal::Union<v8::internal::Smi, v8::internal::HeapNumber, v8::internal::BigInt, v8::internal::String, v8::internal::Symbol, v8::internal::Boolean, v8::internal::Null, v8::internal::Undefined, v8::internal::JSReceiver>>, bool, v8::internal::Handle<v8::internal::Object>) src/json/json-stringifier.cc:961:14
    #12 0x555557d6efa1 in v8::internal::JsonStringifier::SerializeObject(v8::internal::Handle<v8::internal::Union<v8::internal::Smi, v8::internal::HeapNumber, v8::internal::BigInt, v8::internal::String, v8::internal::Symbol, v8::internal::Boolean, v8::internal::Null, v8::internal::Undefined, v8::internal::JSReceiver>>) src/json/json-stringifier.cc:59:12
    #13 0x555557d6efa1 in v8::internal::JsonStringifier::Stringify(v8::internal::Handle<v8::internal::Union<v8::internal::Smi, v8::internal::HeapNumber, v8::internal::BigInt, v8::internal::String, v8::internal::Symbol, v8::internal::Boolean, v8::internal::Null, v8::internal::Undefined, v8::internal::JSReceiver>>, v8::internal::Handle<v8::internal::Union<v8::internal::Smi, v8::internal::HeapNumber, v8::internal::BigInt, v8::internal::String, v8::internal::Symbol, v8::internal::Boolean, v8::internal::Null, v8::internal::Undefined, v8::internal::JSReceiver>>, v8::internal::Handle<v8::internal::Object>) src/json/json-stringifier.cc:558:19
    #14 0x555557d90a62 in v8::internal::JsonStringify(v8::internal::Isolate*, v8::internal::Handle<v8::internal::Union<v8::internal::Smi, v8::internal::HeapNumber, v8::internal::BigInt, v8::internal::String, v8::internal::Symbol, v8::internal::Boolean, v8::internal::Null, v8::internal::Undefined, v8::internal::JSReceiver>>, v8::internal::Handle<v8::internal::Union<v8::internal::Smi, v8::internal::HeapNumber, v8::internal::BigInt, v8::internal::String, v8::internal::Symbol, v8::internal::Boolean, v8::internal::Null, v8::internal::Undefined, v8::internal::JSReceiver>>, v8::internal::Handle<v8::internal::Object>) src/json/json-stringifier.cc:2798:24
    #15 0x555556d739d8 in v8::internal::Builtin_Impl_JsonStringify(v8::internal::BuiltinArguments, v8::internal::Isolate*) src/builtins/builtins-json.cc:37:3
```

After the mutation has been applied, the pointer points to a UTF8 string (the content of the actual JS file). Which somehow confuses the serialization routine later.

This is the test case executed. The `FuzzerInjectionPoint` marker can also be found in the output of the rr trace.

```
//FuzzerInjectionPoint(1);
//FuzzerInjectionPoint(4);
const v3 = Array(4096);
//FuzzerInjectionPoint(5);
v3[1588] = Int32Array;
//FuzzerInjectionPoint(6);
JSON.stringify(["囧","æ","æ",v3]);
//FuzzerInjectionPoint(7);
```

Are there any tricks to get useable debug output for builtins such as `Builtins_ArraySingleArgumentConstructor_HoleySmi_DisableAllocationSites`?


---

**#7 — sa...@google.com — Jan 9, 2025 09:24PM**

Since the issue doesn't appear to require a race, maybe it'd be enough to know how the FixedArray looks like just prior to serialization. Do you get any useful output in a successful run if you add some `%DebugPrint(o)` and `%DebugPrint(o[X])` before the serialization? You mentioned that the pointer points to a UTF8 string, does that mean to a V8 `String` object that uses UTF8 encoding or directly into raw character data?


---

**#8 — v8...@gmail.com — Jan 9, 2025 09:43PM**

The problem with debugging is that adding any additional code (such as calling `%DebugPrint(o)`) causes the addresses to shift and the bug to no longer trigger. Also, the fuzzer works by intercepting reads and introducing additional reads (e.g., by `%DebugPrint`) causes the mutation to get async and to mutate wrong values. I probably need to work on that first. FYI: It seems like the Pernosco session is broken, so there is no use in that.

The mutated value returned by `internal::JSObject::elements()` points to raw UTF16 bytes (but misaligned). By the way, is there any native syntax instruction that sets a breakpoint?

Edit: Some additional information (primarily just notes for myself, maybe helpful for others)

  * The map of the mutated heap object is created by `Builtins_ArraySingleArgumentConstructor_HoleySmi_DisableAllocationSites`
  * Next, the map value is changed by `Builtins_KeyedStoreIC_Megamorphic`, which I guess means its type was changed.
  * These are the first four words of the object (first is the map address): `0x7e9f00049b80: 0x0018da7d 0x00000745 0x00049b91 0x00002000`
  * The value we are mutating is `0x00049b91` (the third word). That value initially points to an object that was deserialized from the snapshot:

```
#1  v8::internal::Deserializer<v8::internal::Isolate>::ReadObject (this=this@entry=0x7fffbda04960, space=<optimized out>)
    at ../../src/snapshot/deserializer.cc:796
#2  0x00005555591fe667 in v8::internal::Deserializer<v8::internal::Isolate>::ReadNewObject<v8::internal::SlotAccessorForHeapObject> (this=this@entry=0x7fffbda04960, data=<optimized out>, slot_accessor=...) at ../../src/snapshot/deserializer.cc:1091
#3  0x00005555591dc46d in v8::internal::Deserializer<v8::internal::Isolate>::ReadSingleBytecodeData<v8::internal::SlotAccessorForHeapObject> (this=<optimized out>, data=<optimized out>, slot_accessor=...) at ../../src/snapshot/deserializer.cc:984
```

  * The mutation causes it to point to `0x7e9f00048b91: u"䘀愀甀氀琀䤀` (first word as bytes `0x61004600`), which is the content of the JS file, as we can see if we align the address (subtract one): `0x7e9f00048b90: u"eFaultInjection();`
  * I guess since the JSON serialized array only contains strings (`["囧","æ","æ",v3]`), this somehow confuses the serialization routine?


---

**#9 — v8...@gmail.com — Jan 10, 2025 01:15AM**

The bug seems to be located here (`SerializeFixedArrayWithPossibleTransitions`, `src/json/json-stringifier.cc:1184`). While iterating the array of size 4096, the fuzzer mutates the value returned by `array->elements()` after some iterations. This causes the other object to be serialized, which seems to be unexpected. However, I don't know what implicit assumption this breaks right now.

```
template <ElementsKind kind>
JsonStringifier::Result
JsonStringifier::SerializeFixedArrayWithPossibleTransitions(
    DirectHandle<JSArray> array, uint32_t length, uint32_t* slow_path_index) {
  static_assert(IsObjectElementsKind(kind));

  HandleScope handle_scope(isolate_);
  DirectHandle<Object> old_length(array->length(), isolate_);
  constexpr bool is_holey = IsHoleyElementsKind(kind);
  bool should_check_treat_hole_as_undefined = true;
  for (uint32_t i = 0; i < length; i++) {
    if (array->length() != *old_length || kind != array->GetElementsKind()) {
      // Array was modified during SerializeElement.
      *slow_path_index = i;
      return UNCHANGED;
    }
    Tagged<Object> current_element =
        Cast<FixedArray>(array->elements())->get(I); // <----------------------- The value returned by array->elements() is mutated after some iterations.
    if (is_holey && IsTheHole(current_element)) {
      if (should_check_treat_hole_as_undefined) {
        if (!CanFastSerializeJSArray(isolate_, *array)) {
          *slow_path_index = i;
          return UNCHANGED;
        }
        should_check_treat_hole_as_undefined = false;
      }
      Separator(i == 0);
      AppendCStringLiteral("null");
    } else {
      Separator(i == 0);
      Result result = SerializeElement(
          isolate_, handle(Cast<JSAny>(current_element), isolate_), i);
      if (result == UNCHANGED) {
        AppendCStringLiteral("null");
      } else if (result != SUCCESS) {
        return result;
      }
      if constexpr (is_holey) {
        should_check_treat_hole_as_undefined = true;
      }
    }
  }
  return SUCCESS;
}
```

This seems to be the reason for the OOB write:

```
#0  v8::internal::JsonStringifier::AppendSubstringByCopy<unsigned char> (this=0x7fffffffcb30, src=0x7e9f00290040 "", count=-1) at ../../src/json/json-stringifier.cc:201
201	in ../../src/json/json-stringifier.cc
(rr) print count
$4 = -1
(rr) print (u32)count
$5 = 4294967295
```


---

**#10 — sa...@google.com — Jan 10, 2025 11:11PM**

Thanks! Hm interesting, if we corrupt the pointer in the FixedArray to point to a UTF16 string (0x7e9f00048b90 in your example), and then go down this path:

```
    #2 0x555557d93a25 in bool v8::internal::JsonStringifier::SerializeString<false>(v8::internal::Handle<v8::internal::String>) src/json/json-stringifier.cc:1689:7
    #3 0x555557da9d5d in v8::internal::JsonStringifier::Result v8::internal::JsonStringifier::Serialize_<false>(v8::internal::Handle<v8::internal::Union<v8::internal::Smi, v8::internal::HeapNumber, v8::internal::BigInt, v8::internal::String, v8::internal::Symbol, v8::internal::Boolean, v8::internal::Null, v8::internal::Undefined, v8::internal::JSReceiver>>, bool, v8::internal::Handle<v8::internal::Object>) src/json/json-stringifier.cc:1006:9
    #4 0x555557dae7e5 in v8::internal::JsonStringifier::SerializeElement
```

I think it would mean that the UTF16 data happens to start with a 4-byte value that is a valid compressed pointer, and if that memory is being treated as a Map, its instance type is one of the string instance types. Quite a coincidence but not super unrealistic. That would also explain why the crash is hard to reproduce with that testcase.

Just from reading some of the code, I'm wondering if the problem here is some integer overflow or signdness issue in the JSON encoder. In particular, the logic in [`AppendSubstring`](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/json/json-stringifier.cc;l=220;drc=44a9b8bbbd2a5bd505c337808f774dcad56ce85c>) looks sketchy, taking size_t input sizes and casting them to uint32_t (possible truncation issue), then adding one to it (possible integer overflow). For example, the following testcase already seems to trigger some kind of memory corruption:

```
function assertEquals(a, b) {
  if (a != b) throw "Assertion failed";
}

const kSeqStringType = Sandbox.getInstanceTypeIdFor("SEQ_TWO_BYTE_STRING_TYPE");
const kStringLengthOffset = Sandbox.getFieldOffset(kSeqStringType, "length");

let memory = new DataView(new Sandbox.MemoryView(0, 0x100000000));

let s = "foo" + "💥";
assertEquals(Sandbox.getInstanceTypeIdOf(s), kSeqStringType);

let string_address = Sandbox.getAddressOf(s);
let orig_length = memory.getUint32(string_address + kStringLengthOffset, true);
assertEquals(orig_length, s.length);
let corrupted_length = -1;
memory.setUint32(string_address + kStringLengthOffset, corrupted_length, true);

JSON.stringify(s);
// Should now crash with something like "malloc(): invalid size (unsorted)" or "double free or corruption (out)" now, indicating heap corruption
```

I think this causes an integer overflow in AppendSubstring when trying to determine whether to reserve more space.

In ASan-instrumented builds this will unfortunately run into a `ERROR: AddressSanitizer: negative-size-param: (size=-2)` which we then [ignore](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/sandbox/testing.cc;l=710;drc=10716def74506bb718a8955c7496cc79fe603c7e>) because we cannot determine if the write happens into the sandbox or not. This is probably because we use [`int count` in `AppendSubstringByCopy`](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/json/json-stringifier.cc;l=201;drc=44a9b8bbbd2a5bd505c337808f774dcad56ce85c>) which is probably also wrong, we should be using either uint32_t or size_t (i.e. an unsigned value).

Does this help with the analysis? Maybe you could check if your testcase triggers any of these same symptoms (e.g. integer overflow in AppendSubstring etc.). I'm going to be OOO starting next week until mid April, so I'll reassign this to Stephen (next week's Shepherd) now.


---

**#11 — sa...@google.com — Jan 10, 2025 11:38PM**

FWIW my current theory here is that something like this happens when a corrupted String is serialized:

  * Somewhere we fetch the string's length and store it as int
  * Then we convert that int to size_t when creating a base::Vector that represents the bytes in memory. The size_t will be 0xffffffffffffffff
  * Then in AppendSubstring, we truncate that size_t back to uint32_t (0xffffffff) and add 1 to it which triggers the integer overflow to 0
  * Therefore we don't grow the backing buffer but still copy 0xffffffff bytes into it (or whatever happens with a negative size param to memcpy)


---

**#12 — sr...@google.com — Jan 14, 2025 07:40PM**

From the stack trace, I think what's going on here is what saelo@ mentioned above.

```
    uint32_t count = static_cast<uint32_t>(to - from);
    while (!CurrentPartCanFit(count + 1)) Extend();
```

`to` in this case is just the length of the input vector, which is created from the in-sandbox string (i.e. `String::GetFlatContent` reads a uint32_t length [here](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/objects/string-inl.h;l=867;drc=a378a42c1a419c060aeff740773cf384af7771f7>). If the length is 0xffffffff, then the call turns into `CurrentPartCanFit(0)`, which will always pass and then write out of bounds below.

We should use checked arithmetic here everywhere. E.g. when serializing a json object, we also take a uint32 + 1 for the size check: [https://source.chromium.org/chromium/chromium/src/+/main:v8/src/json/json-stringifier.cc;l=192;drc=a378a42c1a419c060aeff740773cf384af7771f7](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/json/json-stringifier.cc;l=192;drc=a378a42c1a419c060aeff740773cf384af7771f7>)


---

**#13 — v8...@gmail.com — Jan 14, 2025 11:53PM**

Thanks for the input. I finally managed to build a reproducer. To cause memory corruption, instead of triggering the `AddressSanitizer: negative-size-param` error, `ChangeEncoding()` must be called before the string is serialized.

Args: `d8 --fuzzing --sandbox-fuzzing --allow-natives-syntax --expose-gc --single-threaded bug.js`

ASAN Report:

```
==4153322==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x7e0fbedf6501 at pc 0x555556a4d7a9 bp 0x7fffffffbd50 sp 0x7fffffffbd48
WRITE of size 16 at 0x7e0fbedf6501 thread T0
    #0 0x555556a4d7a8 in operator()<const unsigned char *, const unsigned char *, unsigned short *> third_party/libc++/src/include/__algorithm/copy.h:40:17
    #1 0x555556a4d7a8 in __copy_move_unwrap_iters<std::__Cr::__copy_impl, const unsigned char *, const unsigned char *, unsigned short *, 0> third_party/libc++/src/include/__algorithm/copy_move_common.h:94:19
    #2 0x555556a4d7a8 in __copy<const unsigned char *, const unsigned char *, unsigned short *> third_party/libc++/src/include/__algorithm/copy.h:109:10
    #3 0x555556a4d7a8 in copy<const unsigned char *, unsigned short *> third_party/libc++/src/include/__algorithm/copy.h:115:10
    #4 0x555556a4d7a8 in copy_n<const unsigned char *, unsigned long, unsigned short *, 0> third_party/libc++/src/include/__algorithm/copy_n.h:55:10
    #5 0x555556a4d7a8 in void v8::internal::CopyChars<unsigned char, unsigned short>(unsigned short*, unsigned char const*, unsigned long) src/utils/memcopy.h:398:7
    #6 0x55555734fb78 in void v8::internal::JsonStringifier::AppendSubstringByCopy<unsigned char>(unsigned char const*, int) src/json/json-stringifier.cc:212:7
    #7 0x55555733af8f in SerializeString_<unsigned char, unsigned short, false> src/json/json-stringifier.cc:1588:5
    #8 0x55555733af8f in bool v8::internal::JsonStringifier::SerializeString<false>(v8::internal::Handle<v8::internal::String>) src/json/json-stringifier.cc:1694:12
    #9 0x555557342db0 in v8::internal::JsonStringifier::Result v8::internal::JsonStringifier::Serialize_<false>(v8::internal::Handle<v8::internal::Union<v8::internal::Smi, v8::internal::HeapNumber, v8::internal::BigInt, v8::internal::String, v8::internal::Symbol, v8::internal::Boolean, v8::internal::Null, v8::internal::Undefined, v8::internal::JSReceiver>>, bool, v8::internal::Handle<v8::internal::Object>) src/json/json-stringifier.cc:1006:9
    #10 0x55555732c966 in SerializeObject src/json/json-stringifier.cc:59:12
    #11 0x55555732c966 in v8::internal::JsonStringifier::Stringify(v8::internal::Handle<v8::internal::Union<v8::internal::Smi, v8::internal::HeapNumber, v8::internal::BigInt, v8::internal::String, v8::internal::Symbol, v8::internal::Boolean, v8::internal::Null, v8::internal::Undefined, v8::internal::JSReceiver>>, v8::internal::Handle<v8::internal::Union<v8::internal::Smi, v8::internal::HeapNumber, v8::internal::BigInt, v8::internal::String, v8::internal::Symbol, v8::internal::Boolean, v8::internal::Null, v8::internal::Undefined, v8::internal::JSReceiver>>, v8::internal::Handle<v8::internal::Object>) src/json/json-stringifier.cc:558:19
    #12 0x555557340075 in v8::internal::JsonStringify(v8::internal::Isolate*, v8::internal::Handle<v8::internal::Union<v8::internal::Smi, v8::internal::HeapNumber, v8::internal::BigInt, v8::internal::String, v8::internal::Symbol, v8::internal::Boolean, v8::internal::Null, v8::internal::Undefined, v8::internal::JSReceiver>>, v8::internal::Handle<v8::internal::Union<v8::internal::Smi, v8::internal::HeapNumber, v8::internal::BigInt, v8::internal::String, v8::internal::Symbol, v8::internal::Boolean, v8::internal::Null, v8::internal::Undefined, v8::internal::JSReceiver>>, v8::internal::Handle<v8::internal::Object>) src/json/json-stringifier.cc:2798:24
    #13 0x555556a23988 in v8::internal::Builtin_Impl_JsonStringify(v8::internal::BuiltinArguments, v8::internal::Isolate*) src/builtins/builtins-json.cc:37:3
    #14 0x55555ae295b5 in Builtins_CEntry_Return1_ArgvOnStack_BuiltinExit setup-isolate-deserialize.cc
    #15 0x55555ad82c00 in Builtins_InterpreterEntryTrampoline setup-isolate-deserialize.cc
    #16 0x55555ad8075b in Builtins_JSEntryTrampoline setup-isolate-deserialize.cc
    #17 0x55555ad804aa in Builtins_JSEntry setup-isolate-deserialize.cc
    #18 0x555556d28f14 in Call src/execution/simulator.h:191:12
    #19 0x555556d28f14 in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:436:22
    #20 0x555556d2a4b8 in v8::internal::Execution::CallScript(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>) src/execution/execution.cc:536:10
    #21 0x55555690518a in v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) src/api/api.cc:2155:7
    #22 0x555556728233 in v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) src/d8/d8.cc:1013:44
    #23 0x555556754353 in v8::SourceGroup::Execute(v8::Isolate*) src/d8/d8.cc:4942:10
    #24 0x55555675edee in v8::Shell::RunMainIsolate(v8::Isolate*, bool) src/d8/d8.cc:5886:37
    #25 0x55555675e4e6 in v8::Shell::RunMain(v8::Isolate*, bool) src/d8/d8.cc:5795:18
    #26 0x555556761508 in v8::Shell::Main(int, char**) src/d8/d8.cc:6649:18
    #27 0x7fffbfb911c9 in __libc_start_call_main csu/../sysdeps/nptl/libc_start_call_main.h:58:16
    #28 0x7fffbfb9128a in __libc_start_main csu/../csu/libc-start.c:360:3
    #29 0x555556621029 in _start (/work/v8-build/v8/out/Reproduction/d8+0x10cd029) (BuildId: f23b0ee3ab9b33af)

0x7e0fbedf6501 is located 1 bytes after 4096-byte region [0x7e0fbedf5500,0x7e0fbedf6500)
allocated by thread T0 here:
    #0 0x5555566fa50d in operator new[](unsigned long) /b/s/w/ir/cache/builder/src/third_party/llvm/compiler-rt/lib/asan/asan_new_delete.cpp:89:3
    #1 0x55555732ee70 in v8::internal::JsonStringifier::ChangeEncoding() src/json/json-stringifier.cc:1727:19
    #2 0x55555732e68b in v8::internal::JsonStringifier::InitializeGap(v8::internal::Handle<v8::internal::Object>) src/json/json-stringifier.cc:657:11
    #3 0x55555732c934 in v8::internal::JsonStringifier::Stringify(v8::internal::Handle<v8::internal::Union<v8::internal::Smi, v8::internal::HeapNumber, v8::internal::BigInt, v8::internal::String, v8::internal::Symbol, v8::internal::Boolean, v8::internal::Null, v8::internal::Undefined, v8::internal::JSReceiver>>, v8::internal::Handle<v8::internal::Union<v8::internal::Smi, v8::internal::HeapNumber, v8::internal::BigInt, v8::internal::String, v8::internal::Symbol, v8::internal::Boolean, v8::internal::Null, v8::internal::Undefined, v8::internal::JSReceiver>>, v8::internal::Handle<v8::internal::Object>) src/json/json-stringifier.cc:554:40
    #4 0x555557340075 in v8::internal::JsonStringify(v8::internal::Isolate*, v8::internal::Handle<v8::internal::Union<v8::internal::Smi, v8::internal::HeapNumber, v8::internal::BigInt, v8::internal::String, v8::internal::Symbol, v8::internal::Boolean, v8::internal::Null, v8::internal::Undefined, v8::internal::JSReceiver>>, v8::internal::Handle<v8::internal::Union<v8::internal::Smi, v8::internal::HeapNumber, v8::internal::BigInt, v8::internal::String, v8::internal::Symbol, v8::internal::Boolean, v8::internal::Null, v8::internal::Undefined, v8::internal::JSReceiver>>, v8::internal::Handle<v8::internal::Object>) src/json/json-stringifier.cc:2798:24
    #5 0x555556a23988 in v8::internal::Builtin_Impl_JsonStringify(v8::internal::BuiltinArguments, v8::internal::Isolate*) src/builtins/builtins-json.cc:37:3
    #6 0x55555ae295b5 in Builtins_CEntry_Return1_ArgvOnStack_BuiltinExit setup-isolate-deserialize.cc
    #7 0x55555ad82c00 in Builtins_InterpreterEntryTrampoline setup-isolate-deserialize.cc
    #8 0x55555ad8075b in Builtins_JSEntryTrampoline setup-isolate-deserialize.cc
    #9 0x55555ad804aa in Builtins_JSEntry setup-isolate-deserialize.cc
    #10 0x555556d28f14 in Call src/execution/simulator.h:191:12
    #11 0x555556d28f14 in v8::internal::(anonymous namespace)::Invoke(v8::internal::Isolate*, v8::internal::(anonymous namespace)::InvokeParams const&) src/execution/execution.cc:436:22
    #12 0x555556d2a4b8 in v8::internal::Execution::CallScript(v8::internal::Isolate*, v8::internal::DirectHandle<v8::internal::JSFunction>, v8::internal::DirectHandle<v8::internal::Object>, v8::internal::DirectHandle<v8::internal::Object>) src/execution/execution.cc:536:10
    #13 0x55555690518a in v8::Script::Run(v8::Local<v8::Context>, v8::Local<v8::Data>) src/api/api.cc:2155:7
    #14 0x555556728233 in v8::Shell::ExecuteString(v8::Isolate*, v8::Local<v8::String>, v8::Local<v8::String>, v8::Shell::ReportExceptions, v8::Global<v8::Value>*) src/d8/d8.cc:1013:44
    #15 0x555556754353 in v8::SourceGroup::Execute(v8::Isolate*) src/d8/d8.cc:4942:10
    #16 0x55555675edee in v8::Shell::RunMainIsolate(v8::Isolate*, bool) src/d8/d8.cc:5886:37
    #17 0x55555675e4e6 in v8::Shell::RunMain(v8::Isolate*, bool) src/d8/d8.cc:5795:18
    #18 0x555556761508 in v8::Shell::Main(int, char**) src/d8/d8.cc:6649:18
    #19 0x7fffbfb911c9 in __libc_start_call_main csu/../sysdeps/nptl/libc_start_call_main.h:58:16
    #20 0x7fffbfb9128a in __libc_start_main csu/../csu/libc-start.c:360:3
    #21 0x555556621029 in _start (/work/v8-build/v8/out/Reproduction/d8+0x10cd029) (BuildId: f23b0ee3ab9b33af)

SUMMARY: AddressSanitizer: heap-buffer-overflow third_party/libc++/src/include/__algorithm/copy.h:40:17 in operator()<const unsigned char *, const unsigned char *, unsigned short *>
Shadow bytes around the buggy address:
  0x7e0fbedf6280: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x7e0fbedf6300: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x7e0fbedf6380: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x7e0fbedf6400: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x7e0fbedf6480: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
=>0x7e0fbedf6500:[fa]fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x7e0fbedf6580: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x7e0fbedf6600: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x7e0fbedf6680: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x7e0fbedf6700: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x7e0fbedf6780: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
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
==4153322==ABORTING

## V8 sandbox violation detected!
```


---

**#14 — ap...@google.com — Jan 15, 2025 08:29PM**

Project: v8/v8  
Branch: main  
Author: pthier <[pthier@chromium.org](<mailto:pthier@chromium.org>)>  
Link: [https://chromium-review.googlesource.com/6172045](<https://chromium-review.googlesource.com/6172045>)

[json] Stringify: Avoid int overflows with negative string length

* * *

Expand for full commit details

```
[json] Stringify: Avoid int overflows with negative string length 
 
Fixed: 388437270 
Change-Id: I8d35eea7272fec8296332242097b3b83eb642d25 
Reviewed-on: https://chromium-review.googlesource.com/c/v8/v8/+/6172045 
Reviewed-by: Igor Sheludko <ishell@chromium.org> 
Commit-Queue: Patrick Thier <pthier@chromium.org> 
Cr-Commit-Position: refs/heads/main@{#98123}
```

* * *

Files:

  * M `src/json/json-stringifier.cc`

* * *

Hash: f62b0d60d5bd4a13e1ac077bf51d71941dad75b6  
Date: Wed Jan 15 11:51:59 2025

* * *


---

**#15 — sp...@google.com — Jan 24, 2025 02:57AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $5000.00 for this report.  
  
Rationale for this decision:  
V8 sandbox bypass reward demonstrating memory corruption outside the sandbox   
  
  
Important: This payment will be issued by Bugcrowd. You will receive an email from Bugcrowd in the next 24 hours which contains a submission you must claim to be rewarded.  
  
If you do not receive an email from them, please check your spam folder and then reach out to us via a comment here. For issues related to Bugcrowd itself, please contact them via [https://bugcrowd.com/support](<https://bugcrowd.com/support>).  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#16 — am...@chromium.org — Jan 24, 2025 02:59AM**

Congratulations on another one! Thank you for your efforts fuzzing the V8 heap sandbox -- great work!


---

**#17 — ch...@google.com — Apr 24, 2025 09:38PM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
