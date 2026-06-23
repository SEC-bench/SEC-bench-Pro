# Exported global with literal initializers and subtyping can change the type of the global after creation

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1884887
Component: JavaScript: WebAssembly
Bounty: (unknown)
Date: 2024-03-12T09:51:41Z
Keywords: assertion, crash, csectype-uaf, regression, sec-high, testcase

The attached testcase crashes on mozilla-central revision 343e945a502e+ (debug fuzzing build, run with --no-threads --wasm-compiler=baseline). 

Backtrace:

```
    ==911308==ERROR: AddressSanitizer: heap-use-after-free on address 0x51900002d080 at pc 0x55c6dea1334a bp 0x7ffc31ad3630 sp 0x7ffc31ad3628
    READ of size 8 at 0x51900002d080 thread T0
        #0 0x55c6dea13349 in std::__atomic_base<unsigned long>::load(std::memory_order) const /usr/lib/gcc/x86_64-linux-gnu/9/../../../../include/c++/9/bits/atomic_base.h:419:9
        #1 0x55c6dea13349 in mozilla::detail::IntrinsicMemoryOps<unsigned long, (mozilla::MemoryOrdering)2>::load(std::atomic<unsigned long> const&) js/src/debug64fuzzing/dist/include/mozilla/Atomics.h:194:17
        #2 0x55c6dea13349 in mozilla::detail::AtomicBaseIncDec<unsigned long, (mozilla::MemoryOrdering)2>::operator unsigned long() const js/src/debug64fuzzing/dist/include/mozilla/Atomics.h:339:31
        #3 0x55c6dea13349 in js::AtomicRefCounted<js::wasm::RecGroup>::hasOneRef() const js/src/debug64fuzzing/dist/include/js/RefCounted.h:87:12
        #4 0x55c6dea13349 in TypeIdSet::purge() js/src/wasm/WasmTypeDef.cpp:531:23
        #5 0x55c6dea12d17 in js::wasm::PurgeCanonicalTypes() js/src/wasm/WasmTypeDef.cpp:558:11
        #6 0x55c6de99ecc4 in js::wasm::ShutDown() js/src/wasm/WasmProcess.cpp:471:3
        #7 0x55c6dc41778c in ShutdownImpl(JS::detail::FrontendOnly) js/src/vm/Initialization.cpp:281:3
        #8 0x55c6dc41778c in JS_ShutDown() js/src/vm/Initialization.cpp:310:3
        [...]
    
    0x51900002d080 is located 0 bytes inside of 1056-byte region [0x51900002d080,0x51900002d4a0)
    freed by thread T0 here:
        #0 0x55c6dbe390c6 in free /builds/worker/fetches/llvm-project/compiler-rt/lib/asan/asan_malloc_linux.cpp:52:3
        #1 0x55c6dd3bf88f in unsigned long js::gc::Arena::finalize<js::Shape>(JS::GCContext*, js::gc::AllocKind, unsigned long) js/src/gc/Sweeping.cpp:133:10
        #2 0x55c6dd37ee1c in bool FinalizeTypedArenas<js::Shape>(JS::GCContext*, js::gc::ArenaList&, js::gc::SortedArenaList&, js::gc::AllocKind, js::SliceBudget&) js/src/gc/Sweeping.cpp:200:29
        #3 0x55c6dd37ee1c in FinalizeArenas(JS::GCContext*, js::gc::ArenaList&, js::gc::SortedArenaList&, js::gc::AllocKind, js::SliceBudget&) js/src/gc/Sweeping.cpp:231:5
        #4 0x55c6dd37be1a in js::gc::GCRuntime::backgroundFinalize(JS::GCContext*, JS::Zone*, js::gc::AllocKind, js::gc::Arena**) js/src/gc/Sweeping.cpp:270:3
        #5 0x55c6dd381c22 in js::gc::GCRuntime::sweepBackgroundThings(js::gc::ZoneList&) js/src/gc/Sweeping.cpp:348:9
        #6 0x55c6dd382448 in js::gc::GCRuntime::sweepFromBackgroundThread(js::AutoLockHelperThreadState&) js/src/gc/Sweeping.cpp:425:5
        #7 0x55c6dd2fdfdb in js::GCParallelTask::runTask(JS::GCContext*, js::AutoLockHelperThreadState&) js/src/gc/GCParallelTask.cpp:201:3
        #8 0x55c6dd2fd120 in js::GCParallelTask::runFromMainThread(js::AutoLockHelperThreadState&) js/src/gc/GCParallelTask.cpp:152:3
        #9 0x55c6dd2fd120 in js::GCParallelTask::runFromMainThread() js/src/gc/GCParallelTask.cpp:158:3
        #10 0x55c6dd38211e in js::gc::GCRuntime::queueZonesAndStartBackgroundSweep(js::gc::ZoneList&&) js/src/gc/Sweeping.cpp:408:15
        #11 0x55c6dd391271 in js::gc::GCRuntime::endSweepingSweepGroup(JS::GCContext*, js::SliceBudget&) js/src/gc/Sweeping.cpp:1696:3
        #12 0x55c6dd3d2e9f in sweepaction::SweepActionSequence::run(js::gc::SweepAction::Args&) js/src/gc/Sweeping.cpp:2172:23
        #13 0x55c6dd3c8e79 in sweepaction::SweepActionForEach<js::gc::SweepGroupsIter, JSRuntime*>::run(js::gc::SweepAction::Args&) js/src/gc/Sweeping.cpp:2207:19
        #14 0x55c6dd3987b9 in js::gc::GCRuntime::performSweepActions(js::SliceBudget&) js/src/gc/Sweeping.cpp:2355:53
        #15 0x55c6dd2c14d9 in js::gc::GCRuntime::incrementalSlice(js::SliceBudget&, JS::GCReason, bool) js/src/gc/GC.cpp:3796:11
        #16 0x55c6dd2c668b in js::gc::GCRuntime::gcCycle(bool, js::SliceBudget const&, JS::GCReason) js/src/gc/GC.cpp:4307:3
        #17 0x55c6dd2c8563 in js::gc::GCRuntime::collect(bool, js::SliceBudget const&, JS::GCReason) js/src/gc/GC.cpp:4498:9
        #18 0x55c6dd281be0 in js::gc::GCRuntime::gc(JS::GCOptions, JS::GCReason) js/src/gc/GC.cpp:4575:3
        #19 0x55c6dc73b986 in JSRuntime::destroyRuntime() js/src/vm/Runtime.cpp:258:8
        #20 0x55c6dc47ea2c in js::DestroyContext(JSContext*) js/src/vm/JSContext.cpp:223:7
        [...]
    
    previously allocated by thread T0 here:
        #0 0x55c6dbe3936e in malloc /builds/worker/fetches/llvm-project/compiler-rt/lib/asan/asan_malloc_linux.cpp:69:3
        #1 0x55c6de6c8eb0 in js_arena_malloc(unsigned long, unsigned long) js/src/debug64fuzzing/dist/include/js/Utility.h:370:10
        #2 0x55c6de6c8eb0 in js_malloc(unsigned long) js/src/debug64fuzzing/dist/include/js/Utility.h:374:10
        #3 0x55c6de6c8eb0 in js::wasm::RecGroup::allocate(unsigned int) js/src/wasm/WasmTypeDef.h:937:37
        #4 0x55c6de6c77d4 in js::wasm::TypeContext::startRecGroup(unsigned int) js/src/wasm/WasmTypeDef.h:1139:32
        #5 0x55c6dea2f433 in DecodeTypeSection(js::wasm::Decoder&, js::wasm::ModuleEnvironment*) js/src/wasm/WasmValidate.cpp:1719:44
        #6 0x55c6dea2f433 in js::wasm::DecodeModuleEnvironment(js::wasm::Decoder&, js::wasm::ModuleEnvironment*) js/src/wasm/WasmValidate.cpp:2893:8
        #7 0x55c6de77201a in js::wasm::CompileBuffer(js::wasm::CompileArgs const&, js::wasm::ShareableBytes const&, mozilla::UniquePtr<char [], JS::FreePolicy>*, mozilla::Vector<mozilla::UniquePtr<char [], JS::FreePolicy>, 0ul, js::SystemAllocPolicy>*, JS::OptimizedEncodingListener*) js/src/wasm/WasmCompile.cpp:796:29
        #8 0x55c6de840598 in js::WasmModuleObject::construct(JSContext*, unsigned int, JS::Value*) js/src/wasm/WasmJS.cpp:1497:7
        #9 0x55c6dc08f70c in CallJSNative(JSContext*, bool (*)(JSContext*, unsigned int, JS::Value*), js::CallReason, JS::CallArgs const&) js/src/vm/Interpreter.cpp:479:13
        [...]
    
    SUMMARY: AddressSanitizer: heap-use-after-free /usr/lib/gcc/x86_64-linux-gnu/9/../../../../include/c++/9/bits/atomic_base.h:419:9 in std::__atomic_base<unsigned long>::load(std::memory_order) const
    Shadow bytes around the buggy address:
      0x51900002d000: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
    =>0x51900002d080:[fd]fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd
      0x51900002d100: fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd
    Shadow byte legend (one shadow byte represents 8 application bytes):
      Addressable:           00
      Partially addressable: 01 02 03 04 05 06 07 
      Heap left redzone:       fa
      Freed heap region:       fd
```


It looks like this is triggered at shutdown of the JS shell, with the JS context being destroyed and GCing memory vs. `js::wasm::ShutDown()` being called. This made it somewhat tricky to reproduce this in the fuzzing runs so it would be good to be able to simulate the `js::wasm::ShutDown()` part somehow if that is what can also occur in the browser.

I found this with the wasm-smith upgrade from bug 1884777 but not sure if that contributed here.

---

**Comment 1 — choller@mozilla.com — 2024-03-12T09:51:44Z**

Created attachment 9390717
Detailed Crash Information

---

**Comment 2 — choller@mozilla.com — 2024-03-12T09:51:46Z**

Created attachment 9390718
Testcase

---

**Comment 3 — choller@mozilla.com — 2024-03-12T12:27:58Z**

This is an automated crash issue comment:

Summary: AddressSanitizer: heap-use-after-free [@ js::wasm::TypeDef::recGroup] with READ of size 4
Build version: mozilla-central revision 343e945a502e+
Build type: debug fuzzing build
Runtime options: --no-threads --wasm-compiler=baseline --setpref=wasm_memory_control=true

Testcase:

    modBuf = new Uint8Array([
      0,97,115,109,1,0,0,0,1,5,1,96,1,125,0,2,1,0,3,2,1,0,4,8,1,
      99,0,1,0,167,233,16,5,11,1,5,227,1,224,252,245,235,215,
      175,31,13,9,4,0,0,0,0,0,0,0,0,6,30,4,125,1,67,125,125,125,
      125,11,125,1,67,125,125,125,125,11,125,1,67,125,125,125,
      125,11,112,0,208,0,11,7,67,7,1,0,3,3,2,0,98,3,3,0,3,3,1,
      51,3,3,1,52,3,3,3,93,47,2,3,1,37,77,77,77,77,77,77,77,77,
      77,77,77,77,77,77,77,77,77,77,77,77,77,77,77,77,77,77,77,
      77,77,77,77,77,77,77,77,77,126,2,0,9,5,1,7,99,0,0,12,1,1,
      10,4,1,2,0,11,11,6,1,0,66,0,11,0
    ]);
    module = new WebAssembly.Module(modBuf); 
    instance = new WebAssembly.Instance(module, {});

Backtrace:

    ==913580==ERROR: AddressSanitizer: heap-use-after-free on address 0x51300000abd8 at pc 0x5597d7d41e4f bp 0x7ffcbea656f0 sp 0x7ffcbea656e8
    READ of size 4 at 0x51300000abd8 thread T0
        #0 0x5597d7d41e4e in js::wasm::TypeDef::recGroup() const js/src/wasm/WasmTypeDef.h:702:44
        #1 0x5597d7d41e4e in js::wasm::RefType::Release() const js/src/wasm/WasmTypeDef.h:1344:14
        #2 0x5597d7d41e4e in js::wasm::PackedType<js::wasm::ValTypeTraits>::Release() const js/src/wasm/WasmTypeDef.h:1331:13
        #3 0x5597d7d41e4e in js::WasmGlobalObject::finalize(JS::GCContext*, JSObject*) js/src/wasm/WasmJS.cpp:3232:20
        #4 0x5597d68aa888 in JSClass::doFinalize(JS::GCContext*, JSObject*) const js/src/debug64fuzzing/dist/include/js/Class.h:649:5
        #5 0x5597d68aa888 in JSObject::finalize(JS::GCContext*) js/src/vm/JSObject-inl.h:99:12
        #6 0x5597d68aa888 in unsigned long js::gc::Arena::finalize<JSObject>(JS::GCContext*, js::gc::AllocKind, unsigned long) js/src/gc/Sweeping.cpp:133:10
        #7 0x5597d689f670 in bool FinalizeTypedArenas<JSObject>(JS::GCContext*, js::gc::ArenaList&, js::gc::SortedArenaList&, js::gc::AllocKind, js::SliceBudget&) js/src/gc/Sweeping.cpp:200:29
        #8 0x5597d6867e1a in js::gc::GCRuntime::backgroundFinalize(JS::GCContext*, JS::Zone*, js::gc::AllocKind, js::gc::Arena**) js/src/gc/Sweeping.cpp:270:3
        #9 0x5597d686dbb2 in js::gc::GCRuntime::sweepBackgroundThings(js::gc::ZoneList&) js/src/gc/Sweeping.cpp:348:9
        #10 0x5597d686e448 in js::gc::GCRuntime::sweepFromBackgroundThread(js::AutoLockHelperThreadState&) js/src/gc/Sweeping.cpp:425:5
        #11 0x5597d67e9fdb in js::GCParallelTask::runTask(JS::GCContext*, js::AutoLockHelperThreadState&) js/src/gc/GCParallelTask.cpp:201:3
        #12 0x5597d67e9120 in js::GCParallelTask::runFromMainThread(js::AutoLockHelperThreadState&) js/src/gc/GCParallelTask.cpp:152:3
        #13 0x5597d67e9120 in js::GCParallelTask::runFromMainThread() js/src/gc/GCParallelTask.cpp:158:3
        #14 0x5597d686e11e in js::gc::GCRuntime::queueZonesAndStartBackgroundSweep(js::gc::ZoneList&&) js/src/gc/Sweeping.cpp:408:15
        #15 0x5597d687d271 in js::gc::GCRuntime::endSweepingSweepGroup(JS::GCContext*, js::SliceBudget&) js/src/gc/Sweeping.cpp:1696:3
        #16 0x5597d68bee9f in sweepaction::SweepActionSequence::run(js::gc::SweepAction::Args&) js/src/gc/Sweeping.cpp:2172:23
        #17 0x5597d68b4e79 in sweepaction::SweepActionForEach<js::gc::SweepGroupsIter, JSRuntime*>::run(js::gc::SweepAction::Args&) js/src/gc/Sweeping.cpp:2207:19
        #18 0x5597d68847b9 in js::gc::GCRuntime::performSweepActions(js::SliceBudget&) js/src/gc/Sweeping.cpp:2355:53
        #19 0x5597d67ad4d9 in js::gc::GCRuntime::incrementalSlice(js::SliceBudget&, JS::GCReason, bool) js/src/gc/GC.cpp:3796:11
        #20 0x5597d67b268b in js::gc::GCRuntime::gcCycle(bool, js::SliceBudget const&, JS::GCReason) js/src/gc/GC.cpp:4307:3
        #21 0x5597d67b4563 in js::gc::GCRuntime::collect(bool, js::SliceBudget const&, JS::GCReason) js/src/gc/GC.cpp:4498:9
        #22 0x5597d676dbe0 in js::gc::GCRuntime::gc(JS::GCOptions, JS::GCReason) js/src/gc/GC.cpp:4575:3
        #23 0x5597d5c27986 in JSRuntime::destroyRuntime() js/src/vm/Runtime.cpp:258:8
        #24 0x5597d596aa2c in js::DestroyContext(JSContext*) js/src/vm/JSContext.cpp:223:7
        #25 0x5597d5379a91 in main::$_2::operator()() const js/src/shell/js.cpp:11674:41
        #26 0x5597d5379a91 in mozilla::ScopeExit<main::$_2>::~ScopeExit() js/src/debug64fuzzing/dist/include/mozilla/ScopeExit.h:106:7
        #27 0x5597d5379a91 in main js/src/shell/js.cpp:11767:1
    
    0x51300000abd8 is located 24 bytes inside of 368-byte region [0x51300000abc0,0x51300000ad30)
    freed by thread T0 here:
        #0 0x5597d53250c6 in free /builds/worker/fetches/llvm-project/compiler-rt/lib/asan/asan_malloc_linux.cpp:52:3
        #1 0x5597d7f416c3 in js_free(void*) js/src/debug64fuzzing/dist/include/js/Utility.h:418:3
        #2 0x5597d7f416c3 in void js_delete<js::wasm::RecGroup>(js::wasm::RecGroup const*) js/src/debug64fuzzing/dist/include/js/Utility.h:566:5
        #3 0x5597d7f416c3 in js::AtomicRefCounted<js::wasm::RecGroup>::Release() const js/src/debug64fuzzing/dist/include/js/RefCounted.h:81:7
        #4 0x5597d7f416c3 in mozilla::RefPtrTraits<js::wasm::RecGroup>::Release(js::wasm::RecGroup*) js/src/debug64fuzzing/dist/include/mozilla/RefPtr.h:49:40
        #5 0x5597d7f416c3 in RefPtr<js::wasm::RecGroup const>::ConstRemovingRefPtrTraits<js::wasm::RecGroup const>::Release(js::wasm::RecGroup const*) js/src/debug64fuzzing/dist/include/mozilla/RefPtr.h:417:7
        #6 0x5597d7f416c3 in RefPtr<js::wasm::RecGroup const>::~RefPtr() js/src/debug64fuzzing/dist/include/mozilla/RefPtr.h:80:7
        #7 0x5597d7f416c3 in mozilla::detail::HashTableEntry<RefPtr<js::wasm::RecGroup const> const>::destroyStoredT() js/src/debug64fuzzing/dist/include/mozilla/HashTable.h:1081:11
        #8 0x5597d7f416c3 in mozilla::detail::EntrySlot<RefPtr<js::wasm::RecGroup const> const>::clearLive() js/src/debug64fuzzing/dist/include/mozilla/HashTable.h:1165:13
        #9 0x5597d7f416c3 in mozilla::detail::HashTable<RefPtr<js::wasm::RecGroup const> const, mozilla::HashSet<RefPtr<js::wasm::RecGroup const>, RecGroupHashPolicy, js::SystemAllocPolicy>::SetHashPolicy, js::SystemAllocPolicy>::remove(mozilla::detail::EntrySlot<RefPtr<js::wasm::RecGroup const> const>&) js/src/debug64fuzzing/dist/include/mozilla/HashTable.h:1927:13
        #10 0x5597d7f011b0 in mozilla::detail::HashTable<RefPtr<js::wasm::RecGroup const> const, mozilla::HashSet<RefPtr<js::wasm::RecGroup const>, RecGroupHashPolicy, js::SystemAllocPolicy>::SetHashPolicy, js::SystemAllocPolicy>::remove(mozilla::detail::HashTable<RefPtr<js::wasm::RecGroup const> const, mozilla::HashSet<RefPtr<js::wasm::RecGroup const>, RecGroupHashPolicy, js::SystemAllocPolicy>::SetHashPolicy, js::SystemAllocPolicy>::Ptr) js/src/debug64fuzzing/dist/include/mozilla/HashTable.h:2253:5
        #11 0x5597d7f011b0 in mozilla::HashSet<RefPtr<js::wasm::RecGroup const>, RecGroupHashPolicy, js::SystemAllocPolicy>::remove(mozilla::detail::HashTable<RefPtr<js::wasm::RecGroup const> const, mozilla::HashSet<RefPtr<js::wasm::RecGroup const>, RecGroupHashPolicy, js::SystemAllocPolicy>::SetHashPolicy, js::SystemAllocPolicy>::Ptr) js/src/debug64fuzzing/dist/include/mozilla/HashTable.h:644:33
        #12 0x5597d7f011b0 in TypeIdSet::clearRecGroup(RefPtr<js::wasm::RecGroup const>*) js/src/wasm/WasmTypeDef.cpp:546:14
        #13 0x5597d7f00531 in js::wasm::TypeContext::~TypeContext() js/src/wasm/WasmTypeDef.cpp:581:13
        #14 0x5597d7b8672a in void js_delete<js::wasm::TypeContext>(js::wasm::TypeContext const*) js/src/debug64fuzzing/dist/include/js/Utility.h:565:9
        #15 0x5597d7b8672a in js::AtomicRefCounted<js::wasm::TypeContext>::Release() const js/src/debug64fuzzing/dist/include/js/RefCounted.h:81:7
        #16 0x5597d7b8672a in mozilla::RefPtrTraits<js::wasm::TypeContext>::Release(js::wasm::TypeContext*) js/src/debug64fuzzing/dist/include/mozilla/RefPtr.h:49:40
        #17 0x5597d7b8672a in RefPtr<js::wasm::TypeContext const>::ConstRemovingRefPtrTraits<js::wasm::TypeContext const>::Release(js::wasm::TypeContext const*) js/src/debug64fuzzing/dist/include/mozilla/RefPtr.h:417:7
        #18 0x5597d7b8672a in RefPtr<js::wasm::TypeContext const>::~RefPtr() js/src/debug64fuzzing/dist/include/mozilla/RefPtr.h:80:7
        #19 0x5597d7b8672a in js::wasm::Metadata::~Metadata() js/src/wasm/WasmCode.h:420:31
        #20 0x5597d7e48715 in void js_delete<js::wasm::Metadata>(js::wasm::Metadata const*) js/src/debug64fuzzing/dist/include/js/Utility.h:565:9
        #21 0x5597d7e48715 in js::AtomicRefCounted<js::wasm::Metadata>::Release() const js/src/debug64fuzzing/dist/include/js/RefCounted.h:81:7
        #22 0x5597d7e48715 in mozilla::RefPtrTraits<js::wasm::Metadata>::Release(js::wasm::Metadata*) js/src/debug64fuzzing/dist/include/mozilla/RefPtr.h:49:40
        #23 0x5597d7e48715 in RefPtr<js::wasm::Metadata const>::ConstRemovingRefPtrTraits<js::wasm::Metadata const>::Release(js::wasm::Metadata const*) js/src/debug64fuzzing/dist/include/mozilla/RefPtr.h:417:7
        #24 0x5597d7e48715 in RefPtr<js::wasm::Metadata const>::~RefPtr() js/src/debug64fuzzing/dist/include/mozilla/RefPtr.h:80:7
        #25 0x5597d7e48715 in js::wasm::Code::~Code() js/src/wasm/WasmCode.h:775:7
        #26 0x5597d7d020e0 in void js_delete<js::wasm::Code>(js::wasm::Code const*) js/src/debug64fuzzing/dist/include/js/Utility.h:565:9
        #27 0x5597d7d020e0 in js::AtomicRefCounted<js::wasm::Code>::Release() const js/src/debug64fuzzing/dist/include/js/RefCounted.h:81:7
        #28 0x5597d7d020e0 in mozilla::RefPtrTraits<js::wasm::Code>::Release(js::wasm::Code*) js/src/debug64fuzzing/dist/include/mozilla/RefPtr.h:49:40
        #29 0x5597d7d020e0 in RefPtr<js::wasm::Code const>::ConstRemovingRefPtrTraits<js::wasm::Code const>::Release(js::wasm::Code const*) js/src/debug64fuzzing/dist/include/mozilla/RefPtr.h:417:7
        #30 0x5597d7d020e0 in RefPtr<js::wasm::Code const>::~RefPtr() js/src/debug64fuzzing/dist/include/mozilla/RefPtr.h:80:7
        #31 0x5597d7d020e0 in js::wasm::Instance::~Instance() js/src/wasm/WasmInstance.cpp:2608:1
        #32 0x5597d7d2ecb5 in js::wasm::Instance::destroy(js::wasm::Instance*) js/src/wasm/WasmInstance.cpp:2267:13
        #33 0x5597d7d2ecb5 in js::WasmInstanceObject::finalize(JS::GCContext*, JSObject*) js/src/wasm/WasmJS.cpp:1634:5
        #34 0x5597d68aa888 in JSClass::doFinalize(JS::GCContext*, JSObject*) const js/src/debug64fuzzing/dist/include/js/Class.h:649:5
        #35 0x5597d68aa888 in JSObject::finalize(JS::GCContext*) js/src/vm/JSObject-inl.h:99:12
        #36 0x5597d68aa888 in unsigned long js::gc::Arena::finalize<JSObject>(JS::GCContext*, js::gc::AllocKind, unsigned long) js/src/gc/Sweeping.cpp:133:10
        #37 0x5597d689f670 in bool FinalizeTypedArenas<JSObject>(JS::GCContext*, js::gc::ArenaList&, js::gc::SortedArenaList&, js::gc::AllocKind, js::SliceBudget&) js/src/gc/Sweeping.cpp:200:29
        #38 0x5597d687f78d in js::gc::GCRuntime::foregroundFinalize(JS::GCContext*, JS::Zone*, js::gc::AllocKind, js::SliceBudget&, js::gc::SortedArenaList&) js/src/gc/Sweeping.cpp:1761:8
        #39 0x5597d687f78d in js::gc::GCRuntime::finalizeAllocKind(JS::GCContext*, js::SliceBudget&) js/src/gc/Sweeping.cpp:1964:8
        #40 0x5597d68b5f24 in sweepaction::SweepActionForEach<ContainerIter<mozilla::EnumSet<js::gc::AllocKind, unsigned long>>, mozilla::EnumSet<js::gc::AllocKind, unsigned long>>::run(js::gc::SweepAction::Args&) js/src/gc/Sweeping.cpp:2207:19
        #41 0x5597d68bee9f in sweepaction::SweepActionSequence::run(js::gc::SweepAction::Args&) js/src/gc/Sweeping.cpp:2172:23
        #42 0x5597d68b5786 in sweepaction::SweepActionForEach<js::gc::SweepGroupZonesIter, JSRuntime*>::run(js::gc::SweepAction::Args&) js/src/gc/Sweeping.cpp:2207:19
        #43 0x5597d68bee9f in sweepaction::SweepActionSequence::run(js::gc::SweepAction::Args&) js/src/gc/Sweeping.cpp:2172:23
        #44 0x5597d68b4e79 in sweepaction::SweepActionForEach<js::gc::SweepGroupsIter, JSRuntime*>::run(js::gc::SweepAction::Args&) js/src/gc/Sweeping.cpp:2207:19
        #45 0x5597d68847b9 in js::gc::GCRuntime::performSweepActions(js::SliceBudget&) js/src/gc/Sweeping.cpp:2355:53
        #46 0x5597d67ad4d9 in js::gc::GCRuntime::incrementalSlice(js::SliceBudget&, JS::GCReason, bool) js/src/gc/GC.cpp:3796:11
        #47 0x5597d67b268b in js::gc::GCRuntime::gcCycle(bool, js::SliceBudget const&, JS::GCReason) js/src/gc/GC.cpp:4307:3
        #48 0x5597d67b4563 in js::gc::GCRuntime::collect(bool, js::SliceBudget const&, JS::GCReason) js/src/gc/GC.cpp:4498:9
        #49 0x5597d676dbe0 in js::gc::GCRuntime::gc(JS::GCOptions, JS::GCReason) js/src/gc/GC.cpp:4575:3
        #50 0x5597d5c27986 in JSRuntime::destroyRuntime() js/src/vm/Runtime.cpp:258:8
        #51 0x5597d596aa2c in js::DestroyContext(JSContext*) js/src/vm/JSContext.cpp:223:7
        #52 0x5597d5379a91 in main::$_2::operator()() const js/src/shell/js.cpp:11674:41
        #53 0x5597d5379a91 in mozilla::ScopeExit<main::$_2>::~ScopeExit() js/src/debug64fuzzing/dist/include/mozilla/ScopeExit.h:106:7
        #54 0x5597d5379a91 in main js/src/shell/js.cpp:11767:1
    
    previously allocated by thread T0 here:
        #0 0x5597d532536e in malloc /builds/worker/fetches/llvm-project/compiler-rt/lib/asan/asan_malloc_linux.cpp:69:3
        #1 0x5597d7bb4eb0 in js_arena_malloc(unsigned long, unsigned long) js/src/debug64fuzzing/dist/include/js/Utility.h:370:10
        #2 0x5597d7bb4eb0 in js_malloc(unsigned long) js/src/debug64fuzzing/dist/include/js/Utility.h:374:10
        #3 0x5597d7bb4eb0 in js::wasm::RecGroup::allocate(unsigned int) js/src/wasm/WasmTypeDef.h:937:37
        #4 0x5597d7bb37d4 in js::wasm::TypeContext::startRecGroup(unsigned int) js/src/wasm/WasmTypeDef.h:1139:32
        #5 0x5597d7f1b433 in DecodeTypeSection(js::wasm::Decoder&, js::wasm::ModuleEnvironment*) js/src/wasm/WasmValidate.cpp:1719:44
        #6 0x5597d7f1b433 in js::wasm::DecodeModuleEnvironment(js::wasm::Decoder&, js::wasm::ModuleEnvironment*) js/src/wasm/WasmValidate.cpp:2893:8
        #7 0x5597d7c5e01a in js::wasm::CompileBuffer(js::wasm::CompileArgs const&, js::wasm::ShareableBytes const&, mozilla::UniquePtr<char [], JS::FreePolicy>*, mozilla::Vector<mozilla::UniquePtr<char [], JS::FreePolicy>, 0ul, js::SystemAllocPolicy>*, JS::OptimizedEncodingListener*) js/src/wasm/WasmCompile.cpp:796:29
        #8 0x5597d7d2c598 in js::WasmModuleObject::construct(JSContext*, unsigned int, JS::Value*) js/src/wasm/WasmJS.cpp:1497:7
        [...]
    
    SUMMARY: AddressSanitizer: heap-use-after-free js/src/wasm/WasmTypeDef.h:702:44 in js::wasm::TypeDef::recGroup() const
    Shadow bytes around the buggy address:
      0x51300000ab00: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
    =>0x51300000ab80: fa fa fa fa fa fa fa fa fd fd fd[fd]fd fd fd fd
      0x51300000ac00: fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd
    Shadow byte legend (one shadow byte represents 8 application bytes):
      Addressable:           00
      Partially addressable: 01 02 03 04 05 06 07 
      Heap left redzone:       fa
      Freed heap region:       fd


Another instance but only involving `DestroyContext`.

---

**Comment 4 — ydelendik@mozilla.com — 2024-03-12T12:32:58Z**

Text variant of test case:

```
modBuf = wasmTextToBinary(`(module
  (type $t0 (sub (func)))
  (rec
    (type $t1 (array i8))
    (type $t2 (sub (struct)))
    (type $t3 (sub $t0 (func)))
  )
  (global $g0 (ref null $t0) ref.null $t3)
  (export "" (global $g0))
)`);
module = new WebAssembly.Module(modBuf);
new WebAssembly.Instance(module, {});
```

---

**Comment 5 — rhunt@eqrion.net — 2024-03-12T16:12:29Z**

Exported globals are designed to take a strong reference to any type definition associated with it, and the free it when finalized. However, when the initializer for the global is a simple 'literal' such as null, we're accidentally mutating the type information on the global object to the precise type of the initializer. So in this example, the global gets created with type $t0 and takes a ref to it, then when initializing the value to `ref.null` the type gets accidentally changed to `$t3` without taking a strong reference to it, nor releasing `$t0`.

The right fix here is to prevent the type on the global from ever changing after creation.

---

**Comment 6 — rhunt@eqrion.net — 2024-03-12T16:18:21Z**

This can lead to a global object pointing at a type that is freed. If that memory gets reallocated to a different type or something that looks like a type, it's possible for this global to then get imported by another module as an incorrect type, leading to type confusion.

I'm guessing this is a sec-high.

---

**Comment 7 — rhunt@eqrion.net — 2024-03-12T16:18:41Z**

Created attachment 9390799
Bug 1884887 - wasm: Cleanup global initialization logic. r?yury

---

**Comment 8 — rhunt@eqrion.net — 2024-03-12T16:18:53Z**

Created attachment 9390800
Bug 1884887 - wasm: Add test. r?yury



Depends on D204378

---

**Comment 9 — rhunt@eqrion.net — 2024-03-12T20:42:38Z**

This was introduced by the addition of subtyping in the GC proposal which shipped in 120.

---

**Comment 10 — rhunt@eqrion.net — 2024-03-12T20:44:11Z**

Comment on attachment 9390799
Bug 1884887 - wasm: Cleanup global initialization logic. r?yury

### Security Approval Request
* **How easily could an exploit be constructed based on the patch?**: Not easily. The patch slightly refactors the global initialization logic so the exact code paths that are changing are obscured.
* **Do comments in the patch, the check-in comment, or tests included in the patch paint a bulls-eye on the security problem?**: No
* **Which branches (beta, release, and/or ESR) are affected by this flaw, and do the release status flags reflect this affected/unaffected state correctly?**: Beta and release
* **If not all supported branches, which bug introduced the flaw?**: Bug 1845373
* **Do you have backports for the affected branches?**: Yes
* **If not, how different, hard to create, and risky will they be?**: 
* **How likely is this patch to cause regressions; how much testing does it need?**: The change is pretty minor, easy to understand, and in well tested code.
* **Is the patch ready to land after security approval is given?**: Yes
* **Is Android affected?**: Yes

---

**Comment 11 — rhunt@eqrion.net — 2024-03-12T20:50:57Z**

Created attachment 9390868
Bug 1884887 - wasm: Cleanup global initialization logic. r?yury



Original Revision: https://phabricator.services.mozilla.com/D204378

---

**Comment 12 — rhunt@eqrion.net — 2024-03-12T20:52:47Z**

I created a beta revision for uplifting, but then realized it probably is too late for 124. If this lands after 125 goes to beta, I will re-create the revision.

---

**Comment 13 — tom@mozilla.com — 2024-03-21T15:43:16Z**

Comment on attachment 9390799
Bug 1884887 - wasm: Cleanup global initialization logic. r?yury

sec-approvals were paused for a few days after merge, thanks for the patience.  approved to land and uplift

---

**Comment 14 — rhunt@eqrion.net — 2024-03-22T19:11:42Z**

Created attachment 9392828
Bug 1884887 - wasm: Cleanup global initialization logic. r?yury



Original Revision: https://phabricator.services.mozilla.com/D204378

---

**Comment 15 — phab-bot@bmo.tld — 2024-03-22T19:13:39Z**

# Uplift Approval Request
- **Is Android affected?**: yes
- **Code covered by automated testing**: yes
- **User impact if declined**: Potentially exploitable security issue
- **Explanation of risk level**: The change is pretty minor, easy to understand, and in well tested code.
- **Steps to reproduce for manual QE testing**: N/A
- **Risk associated with taking this patch**: Low
- **Fix verified in Nightly**: yes
- **String changes made/needed**: N/A
- **Needs manual QE test**: no

---

**Comment 16 — pulsebot@bmo.tld — 2024-03-23T01:27:08Z**

Pushed by rhunt@eqrion.net:
https://hg.mozilla.org/integration/autoland/rev/13089f2b4abd
wasm: Cleanup global initialization logic. r=yury

---

**Comment 17 — aryx.bugmail@gmx-topmail.de — 2024-03-23T10:29:05Z**

https://hg.mozilla.org/mozilla-central/rev/13089f2b4abd

---

**Comment 18 — pulsebot@bmo.tld — 2024-03-23T17:24:03Z**

https://hg.mozilla.org/releases/mozilla-beta/rev/6d0cf21b6832

---

**Comment 19 — release-mgmt-account-bot@mozilla.tld — 2024-05-28T12:01:00Z**

2 months ago, tjr placed a reminder on the bug using the whiteboard tag `[reminder-test 2024-05-28]` .

rhunt, please refer to the original comment to better understand the reason for the reminder.

---

**Comment 20 — bugmon@mozilla.com — 2024-09-19T08:22:39Z**

Verified bug as fixed on rev mozilla-central 20240323092917-341c752f9f93.
Removing bugmon keyword as no further action possible.  Please review the bug and re-add the keyword for further analysis.

---

**Comment 21 — pulsebot@bmo.tld — 2025-09-10T21:20:30Z**

Pushed by rhunt@eqrion.net:
https://github.com/mozilla-firefox/firefox/commit/e4bc6682f2c0
https://hg.mozilla.org/integration/autoland/rev/5cbe86b1cb90
wasm: Add test. r=yury

---

**Comment 22 — nbeleuzu@mozilla.com — 2025-09-11T04:09:34Z**

https://hg.mozilla.org/mozilla-central/rev/5cbe86b1cb90
