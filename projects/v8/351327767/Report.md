# WebAssembly OOB memory access due to cached memory index confusion

Issue URL: https://issues.chromium.org/issues/351327767
VRP-Reward: 20000
Date: Jul 6, 2024 06:13PM


### VULNERABILITY DETAILS

#### Summary

WebAssembly OOB memory access due to cached memory index confusion with multi-memory.

#### Details

To speed up WebAssembly memory access, it maintains one cached memory in its instance cache. It heuristically finds the first memory access and caches it.

```
  void StartFunction(FullDecoder* decoder) {
    // ...
    size_t num_memories =
        decoder->module_ == nullptr ? 0 : decoder->module_->memories.size();
    if (num_memories == 1) {
      builder_->set_cached_memory_index(0);
    } else if (num_memories > 1) {
      int first_used_mem_index = FindFirstUsedMemoryIndex(
          base::VectorOf(decoder->start(), decoder->end() - decoder->start()),
          decoder->zone());
      if (first_used_mem_index >= 0) {
        builder_->set_cached_memory_index(first_used_mem_index);
      }
    }
    LoadInstanceCacheIntoSsa(ssa_env);
    // ...
  }

  // Load the instance cache entries into the SSA Environment.
  void LoadInstanceCacheIntoSsa(SsaEnv* ssa_env) {
    builder_->InitInstanceCache(&ssa_env->instance_cache);
  }

void WasmGraphBuilder::InitInstanceCache(
    WasmInstanceCacheNodes* instance_cache) {
  // We handle caching of the instance cache nodes manually, and we may reload
  // them in contexts where load elimination would eliminate the reload.
  // Therefore, we use plain Load nodes which are not subject to load
  // elimination.

  // Only cache memory start and size if there is a memory (the nodes would be
  // dead otherwise, but we can avoid creating them in the first place).
  if (!has_cached_memory()) return;

  instance_cache->mem_start = LoadMemStart(cached_memory_index_);

  // TODO(13957): Clamp the loaded memory size to a safe value.
  instance_cache->mem_size = LoadMemSize(cached_memory_index_);
}
```

On following memory accesses, the compiler re-uses it when the same memory is accessed (with some caveats around reloading on memory growth, irrelevant with this report).

```
Node* WasmGraphBuilder::MemStart(uint32_t mem_index) {
  DCHECK_NOT_NULL(instance_cache_);
  V8_ASSUME(cached_memory_index_ == kNoCachedMemoryIndex ||
            cached_memory_index_ >= 0);
  if (mem_index == static_cast<uint8_t>(cached_memory_index_)) {
    return instance_cache_->mem_start;
  }
  return LoadMemStart(mem_index);
}

Node* WasmGraphBuilder::MemSize(uint32_t mem_index) {
  DCHECK_NOT_NULL(instance_cache_);
  V8_ASSUME(cached_memory_index_ == kNoCachedMemoryIndex ||
            cached_memory_index_ >= 0);
  if (mem_index == static_cast<uint8_t>(cached_memory_index_)) {
    return instance_cache_->mem_size;
  }

  return LoadMemSize(mem_index);
}
```

Note the `static_cast<uint8_t>(cached_memory_index_)` \- this results in truncating the integer memory index into a `uint8_t`, resulting in confusion between different memories. This results in using memory start pointer and length of another memory (and also allows confusion of `kNoCachedMemoryIndex` with `0xff`).

Also, if a memory access is known to be statically in-bounds, the compiler omits runtime bound checks:

```
// Insert code to bounds check a memory access if necessary. Return the
// bounds-checked index, which is guaranteed to have (the equivalent of)
// {uintptr_t} representation.
std::pair<Node*, BoundsCheckResult> WasmGraphBuilder::BoundsCheckMem(
    const wasm::WasmMemory* memory, uint8_t access_size, Node* index,
    uintptr_t offset, wasm::WasmCodePosition position,
    EnforceBoundsCheck enforce_check, AlignmentCheck alignment_check) {
  // ...
  // Convert the index to uintptr.
  Node* converted_index = index;
  if (!memory->is_memory64) {
    converted_index = gasm_->BuildChangeUint32ToUintPtr(index);
  } else if (kSystemPointerSize == kInt32Size) {
    // Only use the low word for the following bounds check.
    converted_index = gasm_->TruncateInt64ToInt32(index);
  }

  UintPtrMatcher constant_index(converted_index);
  // ..
  uintptr_t end_offset = offset + access_size - 1u;

  if (constant_index.HasResolvedValue() &&
      end_offset <= memory->min_memory_size &&
      constant_index.ResolvedValue() < memory->min_memory_size - end_offset) {
    // The input index is a constant and everything is statically within
    // bounds of the smallest possible memory.
    return {converted_index, BoundsCheckResult::kInBounds};
  }
  // ..
}
```

Thus we can create/import memories as below:

  * Index `0`, length larger than `N+8` (`+8` for `i64` access)
  * Index `1 ~ 0xff`, placeholders
  * Index `0x100`, length `N`

And do the following memory accesses:

  * `i64.load {index 0x100, offset 0}, stack [index 0, value X]`
    * This caches memory index 0x100 into instance cache.
  * `i64.load {index 0, offset N}, stack [index 0, value Y]`
    * The access is statically in-bounds in terms of WasmMemory index `0`.
    * This confuses index `0x100` with index `0` and uses the cached pointer, leading to OOB

#### Bisect

This existed since the introduction of multi-memory caching: [https://chromium.googlesource.com/v8/v8.git/+/1137222a33cfce2e6fcc45c7395c98b496a0762f](<https://chromium.googlesource.com/v8/v8.git/+/1137222a33cfce2e6fcc45c7395c98b496a0762f>)

### VERSION

See bisect commit release info in Chromium Dash for more info: [https://chromiumdash.appspot.com/commit/1137222a33cfce2e6fcc45c7395c98b496a0762f](<https://chromiumdash.appspot.com/commit/1137222a33cfce2e6fcc45c7395c98b496a0762f>)

Chrome Version: 118.0.5993.54 stable ~ latest (126.0.6478.127 stable)  
Operating System: All

Note that on environments with wasm OOB trap handling enabled (generally speaking, 64bit platforms), it should prevent exploitation of this vulnerability assuming that its implementation is correct. 32bit chrome is exploitable in the same way as [b/40061453](<https://issuetracker.google.com/issues/40061453>).

### REPRODUCTION CASE

Attached as `wasm-ic-memory-oob.html` which crashes the renderer. Note that DevTools must not be opened as it prevents wasm tier-up. `wasm-module-builder.js` is inlined for easier repro.

### FOR CRASHES, PLEASE INCLUDE THE FOLLOWING ADDITIONAL INFORMATION

Type of crash: Renderer  
Crash State: Crashes on JITed wasm function, explained in depth above in vuln details

### CREDIT INFORMATION

Reporter credit: Seunghyun Lee


---

**#2 — se...@gmail.com — Jul 6, 2024 06:37PM**

Fix would be simply to remove the `static_cast<uint8_t>`. I do not know why the cast was introduced in the first place...?


---

**#3 — se...@gmail.com — Jul 6, 2024 08:46PM**

#### Update:

Even with trap handling, it is possible to access OOB memory outside of the wasm memory guard pages for memory64. **This can be abused to overwrite limited regions of in-sandbox memory, which notably includes the ArrayBuffer PartitionAlloc. This can be exploited to gain in-sandbox exploit primitives as well as fully arbitrary writes** ([b/330563095](<https://issues.chromium.org/issues/330563095>), [b/40238514](<https://issues.chromium.org/issues/40238514>)). Without memory64 and with trap handling enabled in 64bit architecture, I believe exploitation is difficult as each memory regions are fully guarded by 8GB guard region. Exploitation in 32bit architecture is likely to be trivially possible.

Exploitability can be broadly summarized as below.

Memory64 | Trap Handling | Exploitable? | Arch / OS  
---|---|---|---  
O | O | O | (experimental)  
O | X | O | (experimental)  
**X** | **O** | **X** | **x86-64 Linux/ChromeOS/Win/Mac, ARM64 Linux/ChromeOS/Mac ([ src](<https://source.chromium.org/chromium/chromium/src/+/main:content/public/common/content_features.cc;drc=337e49555059ae34498efdf831339e52428a06bd;l=1098>))**  
X | X | O | Other Arch/OSes (32bit, Android, ...)  
  
* * *

~~A question to the Chrome VRP team: Memory64 trap handling is now enabled by default but memory64 itself is still behind`--experimental-wasm-memory64` flag, although it seems that there are [plans to ship it soon](<https://issues.chromium.org/issues/42204673#comment17>). Would writing an exploit that runs on Chrome with memory64 enabled in 64bit architecture land me a Renderer RCE bonus? I can probably also write the exploit on 32bit or by disabling trap handler with `--disable-features=WebAssemblyTrapHandler` (simulating the behavior of Android) if that would conform to the VRP rules.~~ <= not relevant anymore as the exploit is working in Android, see [comment#6](<https://issues.chromium.org/issues/351327767#comment6>)

P.S. Please use `Seunghyun Lee (@0x10n)` for reporter credit, thanks :)


---

**#4 — se...@gmail.com — Jul 7, 2024 12:07AM**

And... crash state & symbolized stack trace just for the record. Symbolized via VS2022 debugger on Windows x86-64, Chrome 126.0.6478.127 Stable.

```
RAX = 0000000000000042 RBX = 000003F700000000 RCX = 00004F539D861000 RDX = 000003F700000000 RSI = 0000534500048311 RDI = 000003EF003C8CA9 R8  = 00000027F4DFC658 R9  = 0000000000000000 R10 = 0000020E563A0000 R11 = 0000000000000246 R12 = 0000000000000000 R13 = 00000CF4007DC080 R14 = 000003EF00000000 R15 = 000003EF00000725 RIP = 00004F539D8618EC RSP = 00000027F4DFCB98 RBP = 00000027F4DFCBA8 EFL = 00010206 

0x000003F700100000 = 0000000000000000 

00004F539D8618C0  push        rbp  
00004F539D8618C1  mov         rbp,rsp  
00004F539D8618C4  push        8  
00004F539D8618C6  push        rsi  
00004F539D8618C7  mov         ebx,dword ptr [rsi+77h]  
00004F539D8618CA  or          rbx,qword ptr [r13+1E0h]  
00004F539D8618D1  mov         rbx,qword ptr [rbx+1007h]  
00004F539D8618D8  mov         edx,dword ptr [rsi+77h]  
00004F539D8618DB  or          rdx,qword ptr [r13+1E0h]  
00004F539D8618E2  mov         rdx,qword ptr [rdx+1007h]  
00004F539D8618E9  mov         qword ptr [rdx],rax  
00004F539D8618EC  mov         qword ptr [rbx+100000h],rax   ; CRASH HERE
00004F539D8618F3  mov         rsp,rbp  
00004F539D8618F6  pop         rbp  
00004F539D8618F7  ret  
```

```
00004f539d8618ec()
00007fffa588e9fd()
00007fffa588eb79()
chrome.dll!Builtins_JSEntryTrampoline()
chrome.dll!Builtins_JSEntry()
chrome.dll!v8::internal::`anonymous namespace'::Invoke(v8::internal::Isolate * isolate, const v8::internal::`anonymous namespace'::InvokeParams & params) Line 437
	at C:\b\s\w\ir\cache\builder\src\v8\src\execution\execution.cc(437)
chrome.dll!v8::internal::Execution::CallScript(v8::internal::Isolate * isolate, v8::internal::Handle<v8::internal::JSFunction> script_function, v8::internal::Handle<v8::internal::Object> receiver, v8::internal::Handle<v8::internal::Object> host_defined_options) Line 516
	at C:\b\s\w\ir\cache\builder\src\v8\src\execution\execution.cc(516)
chrome.dll!v8::Script::Run(v8::Local<v8::Context> context, v8::Local<v8::Data> host_defined_options) Line 2110
	at C:\b\s\w\ir\cache\builder\src\v8\src\api\api.cc(2110)
[Inline Frame] chrome.dll!blink::V8ScriptRunner::RunCompiledScript(v8::Isolate * isolate, v8::Local<v8::Script> script, v8::Local<v8::Data> host_defined_options, blink::ExecutionContext * context) Line 501
	at C:\b\s\w\ir\cache\builder\src\third_party\blink\renderer\bindings\core\v8\v8_script_runner.cc(501)
chrome.dll!blink::V8ScriptRunner::CompileAndRunScript(blink::ScriptState * script_state, blink::ClassicScript * classic_script, blink::ExecuteScriptPolicy policy, blink::V8ScriptRunner::RethrowErrorsOption rethrow_errors) Line 621
	at C:\b\s\w\ir\cache\builder\src\third_party\blink\renderer\bindings\core\v8\v8_script_runner.cc(621)
chrome.dll!blink::ClassicScript::RunScriptOnScriptStateAndReturnValue(blink::ScriptState * script_state, blink::ExecuteScriptPolicy policy, blink::V8ScriptRunner::RethrowErrorsOption rethrow_errors) Line 222
	at C:\b\s\w\ir\cache\builder\src\third_party\blink\renderer\core\script\classic_script.cc(222)
chrome.dll!blink::Script::RunScriptOnScriptState(blink::ScriptState * script_state, blink::ExecuteScriptPolicy execute_script_policy, blink::V8ScriptRunner::RethrowErrorsOption rethrow_errors) Line 35
	at C:\b\s\w\ir\cache\builder\src\third_party\blink\renderer\core\script\script.cc(35)
chrome.dll!blink::Script::RunScript(blink::LocalDOMWindow * window, blink::ExecuteScriptPolicy execute_script_policy, blink::V8ScriptRunner::RethrowErrorsOption rethrow_errors) Line 42
	at C:\b\s\w\ir\cache\builder\src\third_party\blink\renderer\core\script\script.cc(42)
chrome.dll!blink::PendingScript::ExecuteScriptBlockInternal(blink::Script * script, blink::ScriptElementBase * element, bool was_canceled, bool is_external, bool created_during_document_write, base::TimeTicks parser_blocking_load_start_time, bool is_controlled_by_script_runner) Line 297
	at C:\b\s\w\ir\cache\builder\src\third_party\blink\renderer\core\script\pending_script.cc(297)
chrome.dll!blink::PendingScript::ExecuteScriptBlock() Line 193
	at C:\b\s\w\ir\cache\builder\src\third_party\blink\renderer\core\script\pending_script.cc(193)
chrome.dll!blink::ScriptLoader::PrepareScript(blink::ScriptLoader::ParserBlockingInlineOption parser_blocking_inline_option, const WTF::TextPosition & script_start_position) Line 1325
	at C:\b\s\w\ir\cache\builder\src\third_party\blink\renderer\core\script\script_loader.cc(1325)
[Inline Frame] chrome.dll!blink::HTMLParserScriptRunner::ProcessScriptElementInternal(blink::Element * script, const WTF::TextPosition & script_start_position) Line 535
	at C:\b\s\w\ir\cache\builder\src\third_party\blink\renderer\core\script\html_parser_script_runner.cc(535)
chrome.dll!blink::HTMLParserScriptRunner::ProcessScriptElement(blink::Element * script_element, const WTF::TextPosition & script_start_position) Line 298
	at C:\b\s\w\ir\cache\builder\src\third_party\blink\renderer\core\script\html_parser_script_runner.cc(298)
[Inline Frame] chrome.dll!blink::HTMLDocumentParser::RunScriptsForPausedTreeBuilder() Line 681
	at C:\b\s\w\ir\cache\builder\src\third_party\blink\renderer\core\html\parser\html_document_parser.cc(681)
[Inline Frame] chrome.dll!blink::HTMLDocumentParser::CanTakeNextToken(base::TimeDelta & time_executing_script) Line 193
	at C:\b\s\w\ir\cache\builder\src\third_party\blink\renderer\core\html\parser\html_document_parser.h(193)
chrome.dll!blink::HTMLDocumentParser::PumpTokenizer() Line 751
	at C:\b\s\w\ir\cache\builder\src\third_party\blink\renderer\core\html\parser\html_document_parser.cc(751)
chrome.dll!blink::HTMLDocumentParser::PumpTokenizerIfPossible() Line 646
	at C:\b\s\w\ir\cache\builder\src\third_party\blink\renderer\core\html\parser\html_document_parser.cc(646)
chrome.dll!blink::HTMLDocumentParser::DeferredPumpTokenizerIfPossible(bool from_finish_append, base::TimeTicks schedule_time) Line 629
	at C:\b\s\w\ir\cache\builder\src\third_party\blink\renderer\core\html\parser\html_document_parser.cc(629)
[Inline Frame] chrome.dll!base::OnceCallback<void ()>::Run() Line 156
	at C:\b\s\w\ir\cache\builder\src\base\functional\callback.h(156)
[Inline Frame] chrome.dll!base::TaskAnnotator::RunTaskImpl(base::PendingTask & pending_task) Line 203
	at C:\b\s\w\ir\cache\builder\src\base\task\common\task_annotator.cc(203)
[Inline Frame] chrome.dll!base::TaskAnnotator::RunTask(perfetto::StaticString event_name, base::PendingTask & pending_task, base::sequence_manager::internal::ThreadControllerWithMessagePumpImpl::DoWorkImpl::<lambda_4> && args) Line 90
	at C:\b\s\w\ir\cache\builder\src\base\task\common\task_annotator.h(90)
[Inline Frame] chrome.dll!base::sequence_manager::internal::ThreadControllerWithMessagePumpImpl::DoWorkImpl(base::LazyNow * continuation_lazy_now) Line 473
	at C:\b\s\w\ir\cache\builder\src\base\task\sequence_manager\thread_controller_with_message_pump_impl.cc(473)
chrome.dll!base::sequence_manager::internal::ThreadControllerWithMessagePumpImpl::DoWork() Line 338
	at C:\b\s\w\ir\cache\builder\src\base\task\sequence_manager\thread_controller_with_message_pump_impl.cc(338)
chrome.dll!base::MessagePumpDefault::Run(base::MessagePump::Delegate * delegate) Line 41
	at C:\b\s\w\ir\cache\builder\src\base\message_loop\message_pump_default.cc(41)
chrome.dll!base::sequence_manager::internal::ThreadControllerWithMessagePumpImpl::Run(bool application_tasks_allowed, base::TimeDelta timeout) Line 648
	at C:\b\s\w\ir\cache\builder\src\base\task\sequence_manager\thread_controller_with_message_pump_impl.cc(648)
chrome.dll!base::RunLoop::Run(const base::Location & location) Line 136
	at C:\b\s\w\ir\cache\builder\src\base\run_loop.cc(136)
chrome.dll!content::RendererMain(content::MainFunctionParams parameters) Line 376
	at C:\b\s\w\ir\cache\builder\src\content\renderer\renderer_main.cc(376)
chrome.dll!content::RunOtherNamedProcessTypeMain(const std::__Cr::basic_string<char,std::__Cr::char_traits<char>,std::__Cr::allocator<char>> & process_type, content::MainFunctionParams main_function_params, content::ContentMainDelegate * delegate) Line 780
	at C:\b\s\w\ir\cache\builder\src\content\app\content_main_runner_impl.cc(780)
chrome.dll!content::ContentMainRunnerImpl::Run() Line 1158
	at C:\b\s\w\ir\cache\builder\src\content\app\content_main_runner_impl.cc(1158)
[Inline Frame] chrome.dll!content::RunContentProcess(content::ContentMainParams params, content::ContentMainRunner * content_main_runner) Line 332
	at C:\b\s\w\ir\cache\builder\src\content\app\content_main.cc(332)
chrome.dll!content::ContentMain(content::ContentMainParams params) Line 345
	at C:\b\s\w\ir\cache\builder\src\content\app\content_main.cc(345)
chrome.dll!ChromeMain(HINSTANCE__ * instance, sandbox::SandboxInterfaceInfo * sandbox_info, __int64 exe_entry_point_ticks) Line 194
	at C:\b\s\w\ir\cache\builder\src\chrome\app\chrome_main.cc(194)
chrome.exe!MainDllLoader::Launch(HINSTANCE__ * instance, base::TimeTicks exe_entry_point_ticks) Line 181
	at C:\b\s\w\ir\cache\builder\src\chrome\app\main_dll_loader_win.cc(181)
chrome.exe!wWinMain(HINSTANCE__ * instance, HINSTANCE__ * prev, wchar_t *, int) Line 350
	at C:\b\s\w\ir\cache\builder\src\chrome\app\chrome_exe_main_win.cc(350)
[External Code]
```


---

**#5 — se...@gmail.com — Jul 7, 2024 04:08PM**

#### Update:

**This bug also directly leads to v8 sandbox escape** when the two conditions are satisfied:

  1. Memory64 is in use
  2. Either: 
     * Trap handling is disabled
     * The operation is a write operation, and partially OOB writes are not no-ops (non-macos arm64)
     * The operation is `memory.atomic.wait32/64` (results in OOB read)

When `BoundsCheckMem()` decides to use [dynamic bounds check](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/compiler/wasm-compiler.cc;drc=bdb1358afd8fc0dae2a3f8e0348d9841a2d30636;l=3688>), the invariant `end_offset <= min_size <= mem_size` is broken and results in uintptr comparison with overflown `effective_size`. With memory64, this allows indexing of the full 64bit address space.

Attached is a PoC that exploits this behavior to write data outside of the v8 sandbox. Using a d8 binary compiled with gn flags shown in [https://g.co/chrome/vrp/#v8-sandbox-bypass-rewards](<https://g.co/chrome/vrp/#v8-sandbox-bypass-rewards>), run it with `./d8 --experimental-wasm-memory64 --no-wasm-trap-handler --sandbox-testing ./wasm-ic-memory-oob-v8sbx.js` which will demonstrate a v8 sandbox violation.

Note that in the PoC memory corruption API is only used to fetch the base address of the out-of-bounds WASM memory. As we already have relative OOB access to arbitrary offsets, this can be used to leak the base address from which we are OOB read/writing (from ArrayBuffer PartitionAlloc metadata or simply by heap spraying). Thus, under the aformentioned conditions this bug is sufficient on its own to obtain RCE in the current renderer process.

* * *

(Re-updated) Also note that the v8 sandbox escape can be triggered with in-sandbox exploit primtives assuming that memory64 is in use, by racing between imported memory checks at `InstanceBuilder::ProcessImportedMemories()` and then importing a smaller JSArrayBuffer later at `WasmMemoryObject::UseInInstance()`, violating the invariant. However, I currently do not see a way to enable memory64 on non-supported environments (i.e. no `--experimental-wasm-memory64`) with in-sandbox exploit primitives.


---

**#6 — se...@gmail.com — Jul 8, 2024 05:21AM**

#### Update:

Attached is an exploit that obtains RCE within the renderer process on the following environments:

  * **Android ARM64 126.0.6478.122 Stable, tested on Galaxy A34 device**
    * This works without any special flags.
    * Exploit will call `prctl(PR_SET_NAME, "pwn")` which can be checked via `adb shell` -> `ps -AT -o CMD,CMDLINE | grep -v grep | grep pwn`

```
a34x:/ $ ps -AT -o CMD,CMDLINE | grep -v grep | grep pwn
pwn             com.android.chrome:sandboxed_process0:org.chromium.content.app.SandboxedProcessService0:0
```

  * Linux x86-64 126.0.6478.126 Stable, tested on Ubuntu 22.04 without Intel MPK 
    * In this case we assume that trap handler is disabled, so `--disable-features=WebAssemblyTrapHandler` is required.
    * Exploit will call `prctl(PR_SET_NAME, "pwn")` which can be checked via `ps -AT -o comm,command | grep -v grep | grep pwn`

```
$ ps -AT -o comm,command | grep -v grep | grep pwn
pwn             /.../opt/google/chrome/chrome --type=renderer --crashpad-handler-pid=1014629 --enable-crash-reporter=, --origin-trial-disabled-features=ElementCapture --change-stack-guard-on-fork=enable --disable-breakpad --disable-gpu-compositing --lang=en-US --num-raster-threads=4 --enable-main-frame-before-activation --renderer-client-id=7 --time-ticks-at-unix-epoch=-1720220200963958 --launch-time-ticks=162054466135 --shared-files=v8_context_snapshot_data:100 --field-trial-handle=3,i,7838220114294136285,2386602357241543678,262144 --disable-features=WebAssemblyTrapHandler --variations-seed-version=20240704-180140.008000
```

We depend on a specific layout where the gap between ArrayBuffer partition and the v8 cage is over 0x100000000, which allows us to insert `WebAssembly.Memory` between it. In Linux we can simply retry until we have the desired layout, but in Android it seems that [Zygote causes this to be deterministic until reboot](<https://powerofcommunity.net/poc2022/ManYueMo.pdf#page=51>). Thus, if the exploit does not work:

  * In Linux, kill the renderer process & retry
  * In Android, reboot the device (force stop & re-launch does not re-randomize the layout)

Failure detection is also implemented in the exploit, so when the exploit is first visited it tests the OOB and prints out `[!] target not found` if the exploit cannot succeed in the current layout.

Exploit works in the following steps:

  1. We create multiple `WebAssembly.Memory`, shaping the layout such that we can OOB access the ArrayBuffer partition if a gap exists
  2. Using this bug, probe memory out-of-bounds and find the `WebAssembly.Memory` that can OOB access the ArrayBuffer partition 
     * The layout is designed to not crash even on unexploitable cases (on first try, subsequent tries without restarting the renderer process are doomed to eventually crash)
  3. OOB read to leak ArrayBuffer partition address as well as `WebAssembly.Memory` and the v8 sandbox base address
  4. OOB write to overwrite next pointer at ArrayBuffer partition 
     * At this step we already have arbitrary write due to [b/40238514](<https://issues.chromium.org/issues/40238514>). In this exploit however, we use a different v8sbx exploit to reduce version offset hardcoding.
  5. Spray `PACKED_ELEMENTS` arrays with mostly zeros
  6. Reclaim the forged ArrayBuffer pointing into one of the `PACKED_ELEMENTS` arrays
  7. Probe the arrays to find the one overlapping with the reclaim ArrayBuffer 
     * This yields `addrOf()`, `fakeObj()` and almost arbitrary in-sandbox writes.
  8. Use the above primitive to create an ArrayBuffer & DataView ranging the full v8 pointer cage region 
     * Steps 5 ~ 8 is to use already existing v8sbx bypass primitives by creating a DataView equivalent to `new DataView(new Sandbox.MemoryView(0, 0x100000000))`.
  9. Use [b/350292240](<https://issues.chromium.org/issues/350292240>) to cause arbitrary WASM function signature confusion 
     * This leads to v8sbx bypass, as well as leaking JIT address
  10. Use the above primitive to overwrite JIT code to obtain RCE 
     * The exploit calls `prctl(PR_SET_NAME, "pwn")` in both environments and has process continuation.


---

**#7 — sa...@chromium.org — Jul 10, 2024 04:50PM**

Awesome writeup and exploit! I think Clemens may be OOO this week, so CC'ing some more Wasm folks, but Clemens is probably the right person for this as it's related to multi memory.


---

**#8 — jk...@chromium.org — Jul 11, 2024 11:29PM**

Great writeup, great bug. I'll upload a fix.


---

**#9 — se...@gmail.com — Jul 11, 2024 11:43PM**

Update on [comment#5](<https://issues.chromium.org/issues/351327767#comment5>): Seems that we can always satisfy the latter condition with Liftoff-generated atomic read/writes as it forces a (potentially broken) runtime check on atomic memory operations. Thus, having memory64 is enough to trigger the v8 sandbox bypass with in-sandbox exploit primitives. As memory64 is still technically an experimental feature I'm not opening a separate ticket on the v8 sandbox bypass, but feel free to do so if that would be better for tracking issues.

Attached is a PoC that triggers v8 sandbox bypass as explained in the lower section of [comment#5](<https://issues.chromium.org/issues/351327767#comment5>). Run with `--experimental-wasm-memory64 --sandbox-testing`.


---

**#10 — jk...@chromium.org — Jul 12, 2024 12:00AM**

#9: Just to clarify, that race condition is an unrelated problem, right? So it'll need its own fix. I don't care much whether it gets its own issue for tracking or not; but if you want to request two VRP bounties, then having two issues is probably helpful to avoid confusion :-)


---

**#11 — ap...@google.com — Jul 12, 2024 12:21AM**

Project: v8/v8  
Branch: main  
  
commit bc545b15a0ee5dd3bea9f2bfb991b380f5f3659c  
Author: Jakob Kummerow <[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)>  
Date: Thu Jul 11 16:34:00 2024  
  
[wasm][multi-memory] Fix cast of memory index  
  
"uint8_t" must have been a typo.  
  
Fixed: 351327767  
Bug: 42203854  
Change-Id: I196c961ec2f2ed16acfe16bf304d7eae6551aacc  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5695665](<https://chromium-review.googlesource.com/c/v8/v8/+/5695665>)  
Reviewed-by: Matthias Liedtke <[mliedtke@chromium.org](<mailto:mliedtke@chromium.org>)>  
Commit-Queue: Matthias Liedtke <[mliedtke@chromium.org](<mailto:mliedtke@chromium.org>)>  
Auto-Submit: Jakob Kummerow <[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)>  
Commit-Queue: Jakob Kummerow <[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)>  
Cr-Commit-Position: refs/heads/main@{#94981}  
  
M src/compiler/wasm-compiler.cc  
  
[https://chromium-review.googlesource.com/5695665](<https://chromium-review.googlesource.com/5695665>)


---

**#12 — se...@gmail.com — Jul 12, 2024 12:31AM**

Re [comment#10](<https://issues.chromium.org/issues/351327767#comment10>): Yes, the v8sbx bypass with race condition is an unrelated problem, it's just that the same invariant is broken with this bug too. I don't expect a VRP bounty on the v8sbx bypass as memory64 is experimental, but anyways split the issue out to [b/352446085](<https://issues.chromium.org/issues/352446085>) :)


---

**#13 — pe...@google.com — Jul 14, 2024 12:45AM**

Setting milestone because of s0/s1 severity.


---

**#14 — pe...@google.com — Jul 14, 2024 12:46AM**

Setting Priority to P1 to match Severity s1. If this is incorrect, please reset the priority. The automation bot account won't make this change again.


---

**#15 — pe...@google.com — Jul 14, 2024 12:53AM**

This is sufficiently serious that it should be merged to stable. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M126. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately. This is sufficiently serious that it should be merged to beta. But I can't see a Chromium repo commit here,so you will need to investigate what - if anything - needs to be merged to M127. Is there a fix in some other repo which should be merged? Or, perhaps this ticket is a duplicate of some other ticket which has the real fix: please track that down and ensure it is merged appropriately. Merge review required: M126 is already shipping to stable.

Merge review required: M127 is already shipping to beta.

Thank you for fixing this security bug! We aim to ship security fixes as quickly as possible, to limit their opportunity for exploitation as an "n-day" (that is, a bug where git fixes are developed into attacks before those fixes reach users).

We have determined this fix is necessary on milestone(s): [126, 127].

Please answer the following questions so that we can safely process this merge request:

  1. Which CLs should be backmerged? (Please include Gerrit links.)
  2. Has this fix been verified on Canary to not pose any stability regressions?
  3. Does this fix pose any potential non-verifiable stability risks?
  4. Does this fix pose any known compatibility risks?
  5. Does it require manual verification by the test team? If so, please describe required testing.


---

**#16 — jk...@chromium.org — Jul 15, 2024 05:48PM**

#15:

  1. [https://chromium-review.googlesource.com/c/v8/v8/+/5695665](<https://chromium-review.googlesource.com/c/v8/v8/+/5695665>)
  2. Yes, 128.0.6591.0
  3. No
  4. No
  5. No


---

**#17 — am...@chromium.org — Jul 16, 2024 12:19AM**

M126 and M127 merges approved for [https://crrev.com/c/5695665](<https://crrev.com/c/5695665>) please merge this fix to 12.6 at your earliest convenience; please merge this fix to 12.7 as soon as possible, by 10am Pacific Tuesday, 16 July so this fix can be included in the M127 Stable RC being cut tomorrow for release next week


---

**#18 — ap...@google.com — Jul 16, 2024 01:14AM**

Project: v8/v8  
Branch: refs/branch-heads/12.6  
  
commit 01630b99b9f303a224de7fee4deb065e8aff1fab  
Author: Jakob Kummerow <[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)>  
Date: Thu Jul 11 16:34:00 2024  
  
Merged: [wasm][multi-memory] Fix cast of memory index  
  
"uint8_t" must have been a typo.  
  
Fixed: 351327767  
(cherry picked from commit bc545b15a0ee5dd3bea9f2bfb991b380f5f3659c)  
  
Change-Id: Ibd20725045ae41bfcecebcb8f27cf1d0734d1013  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5708568](<https://chromium-review.googlesource.com/c/v8/v8/+/5708568>)  
Reviewed-by: Matthias Liedtke <[mliedtke@chromium.org](<mailto:mliedtke@chromium.org>)>  
Commit-Queue: Matthias Liedtke <[mliedtke@chromium.org](<mailto:mliedtke@chromium.org>)>  
Auto-Submit: Jakob Kummerow <[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)>  
Commit-Queue: Jakob Kummerow <[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)>  
Cr-Commit-Position: refs/branch-heads/12.6@{#52}  
Cr-Branched-From: 3c9fa12db3183a6f4ea53d2675adb66ea1194529-refs/heads/12.6.228@{#2}  
Cr-Branched-From: 981bb15ba4dbf9e2381dfc94ec2c4af0b9c6a0b6-refs/heads/main@{#93835}  
  
M src/compiler/wasm-compiler.cc  
  
[https://chromium-review.googlesource.com/5708568](<https://chromium-review.googlesource.com/5708568>)


---

**#19 — ap...@google.com — Jul 16, 2024 01:14AM**

Project: v8/v8  
Branch: refs/branch-heads/12.7  
  
commit 0f15503a3bd1f4d42079131ef6ccf462823b68a4  
Author: Jakob Kummerow <[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)>  
Date: Thu Jul 11 16:34:00 2024  
  
Merged: [wasm][multi-memory] Fix cast of memory index  
  
"uint8_t" must have been a typo.  
  
Fixed: 351327767  
(cherry picked from commit bc545b15a0ee5dd3bea9f2bfb991b380f5f3659c)  
  
Change-Id: Ib0b7e05052769bd68a3afb04eb1d5fe4a34985c0  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5708509](<https://chromium-review.googlesource.com/c/v8/v8/+/5708509>)  
Reviewed-by: Matthias Liedtke <[mliedtke@chromium.org](<mailto:mliedtke@chromium.org>)>  
Commit-Queue: Matthias Liedtke <[mliedtke@chromium.org](<mailto:mliedtke@chromium.org>)>  
Commit-Queue: Jakob Kummerow <[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)>  
Auto-Submit: Jakob Kummerow <[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)>  
Cr-Commit-Position: refs/branch-heads/12.7@{#30}  
Cr-Branched-From: 35cc908918d3f8083955ed8328506f964e17ae40-refs/heads/12.7.224@{#1}  
Cr-Branched-From: 6d60e6734b32211215c8410db6fe2b84b13abe0e-refs/heads/main@{#94324}  
  
M src/compiler/wasm-compiler.cc  
  
[https://chromium-review.googlesource.com/5708509](<https://chromium-review.googlesource.com/5708509>)


---

**#20 — sp...@google.com — Jul 26, 2024 07:55AM**

** NOTE: This is an automatically generated email **  
  
Hello,  
  
Congratulations! The Chrome Vulnerability Rewards Program (VRP) Panel has decided to award you $20000.00 for this report.  
  
Rationale for this decision:  
$20,000 for high-quality report + exploit of V8 security bug impacting Stable and older versions of Chrome  
  
  
Important: If you aren't already registered with Google as a supplier, [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>) will reach out to you. If you have registered in the past, no need to repeat the process – you can sit back and relax, and we will process the payment soon.  
  
If you have any payment related requests, please direct them to [p2p-vrp@google.com](<mailto:p2p-vrp@google.com>). Please remember to include the subject of this email and the email address that the report was sent from.  
  
  
Thank you for your efforts and helping us make Chrome more secure for all users!  
  
Cheers,  
Chrome VRP Panel Bot  
  
  
P.S. One other thing we'd like to mention:  
  
* Please do NOT publicly disclose details until a fix has been released to all our users. Early public disclosure may cancel the provisional reward. Also, please be considerate about disclosure when the bug affects a core library that may be used by other products. Please do NOT share this information with third parties who are not directly involved in fixing the bug. Doing so may cancel the provisional reward. Please be honest if you have already disclosed anything publicly or to third parties. Lastly, we understand that some of you are not interested in money. We offer the option to donate your reward to an eligible charity. If you prefer this option, let us know and we will also match your donation - subject to our discretion. Any rewards that are unclaimed after 12 months will be donated to a charity of our choosing.  
Please contact [security-vrp@chromium.org](<mailto:security-vrp@chromium.org>) with any questions.


---

**#21 — am...@chromium.org — Jul 26, 2024 07:59AM**

Congratulations Seunghyun! Great work on this incredibly thorough and detailed report + exploit. Thank you for your efforts in discovering, analyzing, and reporting this issue to us!


---

**#22 — pe...@google.com — Sep 5, 2024 01:29AM**

This issue requires additional review before it can be merged to the LTS channel. Please answer the following questions to help us evaluate this merge:

  1. Number of CLs needed for this fix and links to them.
  2. Level of complexity (High, Medium, Low - Explain)
  3. Has this been merged to a stable release? beta release?
  4. Overall Recommendation (Yes, No)


---

**#23 — rz...@google.com — Sep 5, 2024 01:32AM**

1. [https://crrev.com/c/5832698](<https://crrev.com/c/5832698>)
  2. Low, no conflicts
  3. 126, 127
  4. Yes


---

**#24 — ap...@google.com — Sep 17, 2024 02:50AM**

Project: v8/v8  
Branch: refs/branch-heads/12.0  
  
commit ff462a28908ccecf2129f33cc197ec4946336d4d  
Author: Jakob Kummerow <[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)>  
Date: Thu Jul 11 16:34:00 2024  
  
[M120-LTS][wasm][multi-memory] Fix cast of memory index  
  
"uint8_t" must have been a typo.  
  
(cherry picked from commit bc545b15a0ee5dd3bea9f2bfb991b380f5f3659c)  
  
Fixed: [b/351327767](<https://issues.chromium.org/issues/351327767>)  
Bug: [b/42203854](<https://issues.chromium.org/issues/42203854>)  
No-Try: true  
No-Presubmit: true  
No-Tree-Checks: true  
Change-Id: I196c961ec2f2ed16acfe16bf304d7eae6551aacc  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5695665](<https://chromium-review.googlesource.com/c/v8/v8/+/5695665>)  
Commit-Queue: Matthias Liedtke <[mliedtke@chromium.org](<mailto:mliedtke@chromium.org>)>  
Auto-Submit: Jakob Kummerow <[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)>  
Commit-Queue: Jakob Kummerow <[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)>  
Cr-Original-Commit-Position: refs/heads/main@{#94981}  
Reviewed-on: [https://chromium-review.googlesource.com/c/v8/v8/+/5832698](<https://chromium-review.googlesource.com/c/v8/v8/+/5832698>)  
Reviewed-by: Jakob Kummerow <[jkummerow@chromium.org](<mailto:jkummerow@chromium.org>)>  
Commit-Queue: Roger Felipe Zanoni da Silva (xWF) <[rzanoni@google.com](<mailto:rzanoni@google.com>)>  
Reviewed-by: Clemens Backes <[clemensb@chromium.org](<mailto:clemensb@chromium.org>)>  
Auto-Submit: Roger Felipe Zanoni da Silva (xWF) <[rzanoni@google.com](<mailto:rzanoni@google.com>)>  
Cr-Commit-Position: refs/branch-heads/12.0@{#70}  
Cr-Branched-From: ed7b4caf1fb8184ad9e24346c84424055d4d430a-refs/heads/12.0.267@{#1}  
Cr-Branched-From: 210e75b19db4352c9b78dce0bae11c2dc3077df4-refs/heads/main@{#90651}  
  
M src/compiler/wasm-compiler.cc  
  
[https://chromium-review.googlesource.com/5832698](<https://chromium-review.googlesource.com/5832698>)


---

**#25 — pe...@google.com — Oct 19, 2024 03:37AM**

This bug has been closed for more than 14 weeks. Removing issue access restrictions.
