# Invalid stack pointer when delegate is combined with try_table and params

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1884518
Component: JavaScript: WebAssembly
Bounty: (unknown)
Date: 2024-03-09T14:10:16Z
Keywords: csectype-jit, reporter-external, sec-high

Created attachment 9390340
poc_jmp.js

## Reproduce
1. Clone the Firefox mirror from https://github.com/mozilla/gecko-dev
2. Run build command: `mkdir fuzzbuild_OPT.OBJ && cd fuzzbuild_OPT.OBJ && ../configure --enable-address-sanitizer --disable-jemalloc --enable-release --enable-optimize --disable-shared-js --enable-application=js --enable-gczeal && make -j64` in the js/src directory of the firefox checkout
Run poc: `js/src/fuzzbuild_OPT.OBJ/dist/bin/js --wasm-compiler=baseline poc_jmp.js`

## Asan log
```
js/src/fuzzbuild_OPT.OBJ/dist/bin/js --wasm-compiler=baseline poc_jmp.js
AddressSanitizer:DEADLYSIGNAL
=================================================================
==2860019==ERROR: AddressSanitizer: SEGV on unknown address 0x51c000002080 (pc 0x51c000002080 bp 0x2899a84e6079 sp 0x7ffe099c93c8 T0)
==2860019==The signal is caused by a READ memory access.
==2860019==Hint: PC is at a non-executable region. Maybe a wild jump?
    #0 0x51c000002080  (<unknown module>)

AddressSanitizer can not provide additional info.
SUMMARY: AddressSanitizer: SEGV (<unknown module>)
==2860019==ABORTING
```

## Bisect
```
python3 -m autobisect js poc_jmp.js --asan --debug --flags="--wasm-compiler=baseline" --start=2023-12-01
[2024-03-09 21:42:01] Begin bisection...
[2024-03-09 21:42:01] > Start: 81869d55a8d7b3d1d573810ab4e99f63cbe11a8a (20231201095335)
[2024-03-09 21:42:01] > End: efb6c465b7de5cb34b029bb51e5b445952bdd9b2 (20240309090041)
[2024-03-09 21:42:01] Attempting to verify boundaries...
[2024-03-09 21:42:01] Testing build 81869d55a8d7b3d1d573810ab4e99f63cbe11a8a (20231201095335)
[2024-03-09 21:42:03] > Verifying build...
[2024-03-09 21:42:03] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-81869d55a8d7/dist/bin/js --wasm-compiler=baseline -e "quit()"
[2024-03-09 21:42:04] > Launching build with testcase...
[2024-03-09 21:42:04] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-81869d55a8d7/dist/bin/js --wasm-compiler=baseline poc_jmp.js
[2024-03-09 21:42:04] > Failed to reproduce issue!
[2024-03-09 21:42:04] Testing build efb6c465b7de5cb34b029bb51e5b445952bdd9b2 (20240309090041)
[2024-03-09 21:42:06] > Verifying build...
[2024-03-09 21:42:06] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-efb6c465b7de/dist/bin/js --wasm-compiler=baseline -e "quit()"
[2024-03-09 21:42:06] > Launching build with testcase...
[2024-03-09 21:42:06] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-efb6c465b7de/dist/bin/js --wasm-compiler=baseline poc_jmp.js
[2024-03-09 21:42:07] Verified supplied boundaries!
[2024-03-09 21:42:07] Attempting to reduce bisection range using taskcluster binaries
[2024-03-09 21:42:07] Enumerating daily builds: 2023-12-02 09:53:35+00:00 - 2024-03-08 09:00:41+00:00
[2024-03-09 21:42:09] Testing build 5471899cc9d0a7dfda174e9d7cfc986c2820eff8 (20240120093931)
[2024-03-09 21:42:10] > Verifying build...
[2024-03-09 21:42:10] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-5471899cc9d0/dist/bin/js --wasm-compiler=baseline -e "quit()"
[2024-03-09 21:42:11] > Launching build with testcase...
[2024-03-09 21:42:11] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-5471899cc9d0/dist/bin/js --wasm-compiler=baseline poc_jmp.js
[2024-03-09 21:42:11] > Failed to reproduce issue!
[2024-03-09 21:42:13] Testing build 0fff927336814aa029170d9ee5bbc3c342e96061 (20240214045726)
[2024-03-09 21:42:14] > Verifying build...
[2024-03-09 21:42:14] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-0fff92733681/dist/bin/js --wasm-compiler=baseline -e "quit()"
[2024-03-09 21:42:15] > Launching build with testcase...
[2024-03-09 21:42:15] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-0fff92733681/dist/bin/js --wasm-compiler=baseline poc_jmp.js
[2024-03-09 21:42:15] > Failed to reproduce issue!
[2024-03-09 21:42:17] Testing build 689cf8cf7e6b9b9ee5e599a77325de05487a5eed (20240226091922)
[2024-03-09 21:42:18] > Verifying build...
[2024-03-09 21:42:18] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-689cf8cf7e6b/dist/bin/js --wasm-compiler=baseline -e "quit()"
[2024-03-09 21:42:19] > Launching build with testcase...
[2024-03-09 21:42:19] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-689cf8cf7e6b/dist/bin/js --wasm-compiler=baseline poc_jmp.js
[2024-03-09 21:42:19] > Failed to reproduce issue!
[2024-03-09 21:42:21] Testing build c5ddc3b211e53221a5b12ce6c8a5a523bba3641f (20240303091237)
[2024-03-09 21:42:23] > Verifying build...
[2024-03-09 21:42:23] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-c5ddc3b211e5/dist/bin/js --wasm-compiler=baseline -e "quit()"
[2024-03-09 21:42:23] > Launching build with testcase...
[2024-03-09 21:42:23] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-c5ddc3b211e5/dist/bin/js --wasm-compiler=baseline poc_jmp.js
[2024-03-09 21:42:25] Testing build 3facb0e94116fec2e75054e8fef710a08559ce55 (20240229001649)
[2024-03-09 21:42:27] > Verifying build...
[2024-03-09 21:42:27] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-3facb0e94116/dist/bin/js --wasm-compiler=baseline -e "quit()"
[2024-03-09 21:42:27] > Launching build with testcase...
[2024-03-09 21:42:27] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-3facb0e94116/dist/bin/js --wasm-compiler=baseline poc_jmp.js
[2024-03-09 21:42:29] Testing build 06645f775e47ea71f6dfa2daff5411ab31c5a629 (20240228043028)
[2024-03-09 21:42:30] > Downloading: https://firefox-ci-tc.services.mozilla.com/api/queue/v1/task/e8n-2mdoSRWUkPEKyRWmjg/artifacts/public/build/target.jsshell.zip (319.59MiB total)
[2024-03-09 21:43:00] .. still downloading (41.8%, 4.66MB/s)
[2024-03-09 21:43:30] .. still downloading (83.5%, 4.66MB/s)
[2024-03-09 21:43:41] .. downloaded (4.67MB/s)
[2024-03-09 21:43:41] .. extracting
[2024-03-09 21:43:50] Extracted into /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-06645f775e47
[2024-03-09 21:43:53] > Verifying build...
[2024-03-09 21:43:53] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-06645f775e47/dist/bin/js --wasm-compiler=baseline -e "quit()"
[2024-03-09 21:43:53] > Launching build with testcase...
[2024-03-09 21:43:53] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-06645f775e47/dist/bin/js --wasm-compiler=baseline poc_jmp.js
[2024-03-09 21:43:55] Testing build 8ea0c0ea3c7c794cd475d0839f70a26ceb7ff58c (20240227043210)
[2024-03-09 21:43:57] > Verifying build...
[2024-03-09 21:43:57] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-8ea0c0ea3c7c/dist/bin/js --wasm-compiler=baseline -e "quit()"
[2024-03-09 21:43:58] > Launching build with testcase...
[2024-03-09 21:43:58] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-8ea0c0ea3c7c/dist/bin/js --wasm-compiler=baseline poc_jmp.js
[2024-03-09 21:43:58] > Failed to reproduce issue!
[2024-03-09 21:43:58] Enumerating pushdate builds: 2024-02-27 04:32:10+00:00 - 2024-02-28 04:30:28+00:00
[2024-03-09 21:44:06] Testing build 74094dc4022c8437eb87a7e25bf6433fb07a7fbb (20240227095754)
[2024-03-09 21:44:08] > Verifying build...
[2024-03-09 21:44:08] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-74094dc4022c/dist/bin/js --wasm-compiler=baseline -e "quit()"
[2024-03-09 21:44:08] > Launching build with testcase...
[2024-03-09 21:44:08] Running: /home/test/.cache/autobisect/builds/js-m-c-linux-asan-debug-74094dc4022c/dist/bin/js --wasm-compiler=baseline poc_jmp.js
[2024-03-09 21:44:08] > Failed to reproduce issue!
[2024-03-09 21:44:08] Enumerating autoland builds: 2024-02-27 09:57:54+00:00 - 2024-02-28 04:30:28+00:00
[2024-03-09 21:44:10] Unable to find build for a3c8904349c4a01db9f86ce52027c4a8ccca6fc8
[2024-03-09 21:44:11] Unable to find build for 88e37f77f4606d4667745a271994af261983d8a2
[2024-03-09 21:44:12] Unable to find build for d07920bed34c26e732a1b89b88bbebef3f4d14fb
[2024-03-09 21:44:12] Unable to find build for 7f07a1c73ff7cdfe3f7ddf52d26f7fb5238f712b
[2024-03-09 21:44:13] Unable to find build for 972b012d913d3c1fec2bea0f74cf518c55d9ccbf
[2024-03-09 21:44:14] Unable to find build for f5bd3d0df05251960cc541f70b98100727aac03c
[2024-03-09 21:44:15] Unable to find build for b419971e9867e4e69b8b0de8378f3ed34fbef73a
[2024-03-09 21:44:15] Unable to find build for c0ebbc17e074291619adf1be6d94c09a289487db
[2024-03-09 21:44:16] Unable to find build for c5ef10fad9630cd590d110f1e3bf5dac06458cd0
[2024-03-09 21:44:17] Unable to find build for ef1260d1935d9ef7f4d704c6b5a1677ecaed10d7
[2024-03-09 21:44:18] Unable to find build for 3784effbd73f8e123cbe3d5c5dc802a759ba17f6
[2024-03-09 21:44:18] Unable to find build for deb46de7b01c974bed9e0fa675fcabc07c05e34e
[2024-03-09 21:44:19] Unable to find build for 758ad04a330ebb68404446e505caf8482864889a
[2024-03-09 21:44:20] Unable to find build for c4530ae2b9e3c8abfe83047aa665fe2f87a2f095
[2024-03-09 21:44:21] Unable to find build for 56fb245cd38effab4dad4b2a48a8816f8de693cb
[2024-03-09 21:44:21] Unable to find build for ade6db42285df212ddb87f68bd3e2f1014901958
[2024-03-09 21:44:22] Unable to find build for 8d495120e6d2feb0afac4308cac5c336c3493e35
[2024-03-09 21:44:23] Unable to find build for 9f3fe37b77ca75d3e70e9fb3a0bdb2388906cf8d
[2024-03-09 21:44:23] Unable to find build for 3cc96704d17fe1b7b176f77b768e2a447c31e62b
[2024-03-09 21:44:24] Unable to find build for 4c90f0d5fa7a48c9f5d3831bc454119b8c302196
[2024-03-09 21:44:25] Unable to find build for 8fa3d22936fe664d693bb029d61498eb8af25b17
[2024-03-09 21:44:26] Unable to find build for 50ce64203a8582a7d00b263d2aaec1cef6c936b0
[2024-03-09 21:44:26] Unable to find build for 6031aa0ce1d77d8154463a56f2faba01eb41bc55
[2024-03-09 21:44:27] Unable to find build for ac91a84fdc7a12384147e0a41874d255c330c7c9
[2024-03-09 21:44:28] Unable to find build for 74997683643c09494923518de1b3e6ecbbdd9f15
[2024-03-09 21:44:28] Unable to find build for b4a75899570d6e98d4e9e7ad19a6adb35d44608b
[2024-03-09 21:44:29] Unable to find build for c1f6489463b2e22598a4c3891e7bb4d13cdc50d5
[2024-03-09 21:44:30] Unable to find build for b83e6af8db52877953a96b2fa26b4a126fcef02d
[2024-03-09 21:44:31] Unable to find build for ac90a51120e78586b251f6363166425ae26006dc
[2024-03-09 21:44:31] Unable to find build for c3d449c7d19a4aaa5c1ff2cc6ce83fda83c29211
[2024-03-09 21:44:32] Unable to find build for 78a9a7e8e8848472efbd8ce88631a7f57139756f
[2024-03-09 21:44:33] Unable to find build for 27bba8a66bf068e4d0fbbff10bed73b606ff3d85
[2024-03-09 21:44:33] Unable to find build for 4424f8155d05f294e2e66611d74c6b77dac08c5a
[2024-03-09 21:44:34] Unable to find build for 2f8bbb9e7910d24104420dc91aaa0f3ece40aeae
[2024-03-09 21:44:35] Unable to find build for 33a0f61d6e0ce8c5a144b1f273338f446225c98a
[2024-03-09 21:44:36] Unable to find build for 20d4bde96991275737dbf15468d8ea2cf85a08ee
[2024-03-09 21:44:37] Unable to find build for 50f08af6f8f0896075717cff1e0dc5ca14a85282
[2024-03-09 21:44:37] Unable to find build for d7f58dbf5fb5935e47e12b33801ed8da917a4a70
[2024-03-09 21:44:38] Unable to find build for d26fefafb6108706ee4664bac46abfbf5b071911
[2024-03-09 21:44:39] Unable to find build for a10d410cc9dcc2b247a36a9c576303351e984715
[2024-03-09 21:44:40] Unable to find build for 21d7777e589f3e0e5f626f9973ea5e726d190374
[2024-03-09 21:44:40] Unable to find build for 8b56968bb2b19fff679b32bb82eefc7cd38c0140
[2024-03-09 21:44:41] Unable to find build for 7aab4d5877fec7d000decd7b5baccb42942d742d
[2024-03-09 21:44:42] Unable to find build for c445c671382af8464d841e3e88415a8ecf4b5042
[2024-03-09 21:44:42] Unable to find build for 3543911c3c7aa7c424ac0a7d78b3c87d794a1a64
[2024-03-09 21:44:43] Unable to find build for d61967e01fa0feb4fc3cc963d21ac7173d14c185
[2024-03-09 21:44:44] Unable to find build for f2599064d780e4c021db1cf6c386ff54143f153c
[2024-03-09 21:44:45] Unable to find build for 01b5dd543d46f4e75778748141f0680f6f4d498e
[2024-03-09 21:44:46] Unable to find build for 0c1464ffe8d1a3618ecb9702195f63d95bf3e78a
[2024-03-09 21:44:47] Unable to find build for 6833d8b177b6f0bcb28f079d1823464f0b1a5064
[2024-03-09 21:44:47] Unable to find build for 814d00e74eee878b76e6072a18b91cbf4356ce18
[2024-03-09 21:44:48] Unable to find build for dc7f191bb85b4139748abfcfa59956de3a1c1863
[2024-03-09 21:44:49] Unable to find build for ed638085927d4956bc1ac20a6c1b21f6c89adc27
[2024-03-09 21:44:50] Unable to find build for 489bcc624ea3012084d3d3275200cce3449cecc1
[2024-03-09 21:44:51] Unable to find build for 64f678a501fd1e1c4b3d2f8030da3138835ba8f8
[2024-03-09 21:44:52] Unable to find build for aa032608e9e5f55c8c1b3d9ffde63bdaf9669ec9
[2024-03-09 21:44:52] Unable to find build for 1aec740b593e785e034bd90accf1a66b8375b98c
[2024-03-09 21:44:53] Unable to find build for e782f9b9e2afcca8f64cb1c7cad8fd824a514603
[2024-03-09 21:44:54] Unable to find build for a3b821d00017b91d8b560f7207d6253058bc4e89
[2024-03-09 21:44:55] Unable to find build for dcfab5a6e3d5f443fff26f7a5569acc7f9cd6fa1
[2024-03-09 21:44:56] Unable to find build for a4a250dc4c9c53dec1e1a87613cb06c88ce80525
[2024-03-09 21:44:57] Unable to find build for c1a1a9e0953813da907ccfafe46a67112f590e3f
[2024-03-09 21:44:58] Unable to find build for e6b1933e344a2c1db97ac47df1b4d9f2bd7c4581
[2024-03-09 21:44:59] Unable to find build for 8b228797c8ca78f05f9afa47fc8228e8171ff507
[2024-03-09 21:45:00] Unable to find build for b92530fc1436c8bb6a82ed48b16a3218a40474e0
[2024-03-09 21:45:00] Unable to find build for 757841c90c00a0cb591ed750bd775422cbde2f68
[2024-03-09 21:45:01] Unable to find build for ef519b5ac4ea2e3ceed6e8e25c6b43852ca4e6b0
[2024-03-09 21:45:02] Unable to find build for a946d4e144cd3123f84df19e16fe3592fda572e6
[2024-03-09 21:45:03] Unable to find build for b66d5034143359f40d0678651fc1cf25d92abd54
[2024-03-09 21:45:04] Unable to find build for 4f802fe2f1f2c12a54449a666831c8a9f32c134c
[2024-03-09 21:45:05] Unable to find build for 76e5ca0f5b4c6837487a360154c334ad7833032f
[2024-03-09 21:45:05] Unable to find build for abfcfb10cf40f0d8e333d356cd1bcab4b9873c88
[2024-03-09 21:45:06] Unable to find build for 203be33889055a9b82e35c252cfd5a947498769b
[2024-03-09 21:45:07] Unable to find build for 61edd9566aab6e8befbab774259851d31bd94e22
[2024-03-09 21:45:08] Unable to find build for 6a66ebb51163f5f46c03f69cbfc1fb8c39269665
[2024-03-09 21:45:09] Unable to find build for 7980e8851be86f43c76975243d8d458b24475205
[2024-03-09 21:45:10] Unable to find build for 7d50df905d964d8badb5b0b885e44c290b43b5db
[2024-03-09 21:45:10] Unable to find build for b9103d1e43debf7bc6c45471f106bd373762538c
[2024-03-09 21:45:11] Unable to find build for ae670cb0312cacb8d2104266f1a9ae4753014e44
[2024-03-09 21:45:12] Unable to find build for 4fe264344facf2766b698ba5bb9efc7cd857e245
[2024-03-09 21:45:13] Unable to find build for 09d1482a3459163cd060cc35b2d2527f84ad4a6a
[2024-03-09 21:45:14] Unable to find build for 72db1aeecf41be99edb4340c7b48dff10e358a1c
[2024-03-09 21:45:15] Unable to find build for 7abf13deeec13cb7d0b42bdb64bb3df13d5a0f05
[2024-03-09 21:45:16] Unable to find build for 29ee4a77309632936b8f508fabae75bae6ba4755
[2024-03-09 21:45:17] Unable to find build for 2c3d8a9eb42730f6eb5d07414d34170f5046df82
[2024-03-09 21:45:17] Unable to find build for 0d2eaf60c298bd5e0c7217256bc934e2e8a1b817
[2024-03-09 21:45:18] Unable to find build for 36d3e38e9c4120efbd2a71bf1f572ada5f6e7c94
[2024-03-09 21:45:19] Unable to find build for a9839b0cf7f17ec3e738af0a5e8d712dc71c6f63
[2024-03-09 21:45:20] Unable to find build for 854cc78717b8016c4e761b5da882db252d78d9cd
[2024-03-09 21:45:21] Unable to find build for 1bb47efe5cd47aa4a3a4e753cd8f3b770f98e1f6
[2024-03-09 21:45:22] Unable to find build for b74ae2aeca28af97283f838bfef995a3976af81a
[2024-03-09 21:45:23] Unable to find build for 543381939812ac5c1026ade28c5508ebdc0fd1e6
[2024-03-09 21:45:24] Unable to find build for 45070cf9c69e737dc7883ddcc6020ac84918b53a
[2024-03-09 21:45:24] Unable to find build for 68cd9109a9f7cb409b3f660f82b9bc8df17ea0d1
[2024-03-09 21:45:25] Unable to find build for 9f62179225e566f2c04148edbe228a68d9e4e430
[2024-03-09 21:45:27] Unable to find build for f6eb64352980f95a0d5d2da7823650764e9dfecb
[2024-03-09 21:45:28] Unable to find build for cfa733c700c170913bdfa72ca88759e93bfc0b95
[2024-03-09 21:45:28] Unable to find build for 09a1b473f8dab1609e2ca9ae45ead6a8300d9a78
[2024-03-09 21:45:29] Unable to find build for df034e84da57461a16b5d0d4d40036fa17bbac0f
[2024-03-09 21:45:30] Unable to find build for 7c947114da80f5b4248ada3354f8529aa71a2e6c
[2024-03-09 21:45:31] Unable to find build for 9973c75413d6237b9005b9ab908898a153bd2f06
[2024-03-09 21:45:32] Unable to find build for 2e5121a988a84617ccd48d9fc7c3967168d1790c
[2024-03-09 21:45:33] Unable to find build for 9b17ac4800c6e3d2b487f965c68b4af824ed9fd4
[2024-03-09 21:45:33] Unable to find build for e519654e5d8b7e0dc682c316fa0d16318b962765
[2024-03-09 21:45:34] Unable to find build for 1187b18b4da00ba882f1a9e991c72dfe5da154af
[2024-03-09 21:45:35] Unable to find build for 7fcfb99610b1d17addcb7adef26ac4eb09f77b94
[2024-03-09 21:45:36] Unable to find build for 58e140b4ca88ed963502cce4cff849dbaa868e67
[2024-03-09 21:45:37] Unable to find build for 8395cc2be3a019c8d45890e53c5312302cdc9f25
[2024-03-09 21:45:38] Unable to find build for db5b35851cdb09a1ab304acc055023d5ede104fa
[2024-03-09 21:45:39] Unable to find build for 704ac89a7641697b92c72e11c2ce8c1b4a5168a4
[2024-03-09 21:45:40] Unable to find build for 82b351275da7ac8283a64facbb6f5bd745c9ed07
[2024-03-09 21:45:41] Unable to find build for 53f70c6396a672f159b84c41e30e743e3a7dcfe0
[2024-03-09 21:45:42] Unable to find build for ed8e24fca6163cb97275f8e47574407340c8a53a
[2024-03-09 21:45:43] Unable to find build for 2f50d3421a3db7b1c9ab2fd3c5a07e3ae5155462
[2024-03-09 21:45:44] Unable to find build for bf6be80ff787f46f247577eb591d05c71f6a8034
[2024-03-09 21:45:44] Unable to find build for 9a60807265f84ebd2695ba28ecf95de712706ecb
[2024-03-09 21:45:45] Unable to find build for adc60fc41c15aec4ee87f1662b76002c2adc40ec
[2024-03-09 21:45:46] Unable to find build for 7e1b1ec4357bedd2c9bbab9f8c973627c7673539
[2024-03-09 21:45:47] Unable to find build for 17b38d1acb38aec71c39749e58978644dff29d47
[2024-03-09 21:45:48] Unable to find build for 52ef3e132f3c1718217ff3599bf689aca1d58bea
[2024-03-09 21:45:48] Unable to find build for df1c19befcdce39a2afd46cd35336b7fb07e33ce
[2024-03-09 21:45:49] Unable to find build for 64f4316ec95fc5b38316e8d40f1963a15a82b156
[2024-03-09 21:45:50] Unable to find build for d0715e47e1b132b5117a648b5a586f0f471b8dd2
[2024-03-09 21:45:51] Unable to find build for 38ab01fb33c44a7daeb55fbd834c10c11ce7f8d8
[2024-03-09 21:45:52] Unable to find build for 5c60df3c3dfba2c57414dbb4bfda4f915ba444ed
[2024-03-09 21:45:53] Unable to find build for e085e55ced66caf961a85a4a59082bda3f5f48f3
[2024-03-09 21:45:53] Unable to find build for 0002a87b69237448f597c63ad5da0e2acdce7a36
[2024-03-09 21:45:54] Unable to find build for ad4e05d7f18eae3706b1d2d1f04be8b07c0cdc52
[2024-03-09 21:45:55] Unable to find build for 713fb2e74585008e6a52f135514d0be7919de09e
[2024-03-09 21:45:56] Unable to find build for c6d639464cf623ffd5a45d8b8ab62662bd0e838c
[2024-03-09 21:45:57] Unable to find build for 6b6a70588768d169e77f04cda57cac0a886a53ee
[2024-03-09 21:45:58] Unable to find build for a75a96f959cdbfd4fe02e1e78c2f42ac5dd19932
[2024-03-09 21:45:58] Unable to find build for c3732eaa0914e36e179eddb611c7695ac33fe2d0
[2024-03-09 21:45:59] Unable to find build for ba4d1e4ccf73b7cdf970e39babaff4806bc9a99e
[2024-03-09 21:46:00] Unable to find build for 1e26b9d43a576b564dd31b52fee56e03ed50ea9f
[2024-03-09 21:46:01] Unable to find build for 81a095af85a262c9231942885eb1fd95e38d2fb7
[2024-03-09 21:46:02] Unable to find build for 1887aa693fdc4f3fcb08c6c3de69417b986ba4ed
[2024-03-09 21:46:03] Unable to find build for 4eb743d7caf68a0052efaffeecf8cc337386fb0a
[2024-03-09 21:46:04] Unable to find build for a99aa592b4a7dde538ecca1ae2d4cba4be90a180
[2024-03-09 21:46:06] Unable to find build for 667cb325b8cb66ae2778beb8f77f095d76b334de
[2024-03-09 21:46:06] Unable to find build for 27dae926668f5c71e3244493135119ae40ad0578
[2024-03-09 21:46:07] Unable to find build for 0a6b3d90e636ca71c7750b7f27972d9b61857ea8
[2024-03-09 21:46:08] Unable to find build for d29d7e9c38bda1383ac926bb970630529a0b5e5a
[2024-03-09 21:46:09] Unable to find build for 7f46e8820023edcbfd944c1e9a0c4a2ae6ced538
[2024-03-09 21:46:10] Unable to find build for 058d5712354bdaac9e1156710bf1721bd06b2892
[2024-03-09 21:46:11] Unable to find build for 29f139450cccac730676aa8f177134cdcc0204b5
[2024-03-09 21:46:11] Unable to find build for 7571e95ed78c5afc5e5592fd97fc9c537fe713f6
[2024-03-09 21:46:12] Unable to find build for 38614c34e575caaa5d5f6d3cd8c2438ae774f869
[2024-03-09 21:46:13] Unable to find build for a2139db8faa2858adf35796d04acdbb3db2e0ed8
[2024-03-09 21:46:14] Unable to find build for b13b62667d5dc424dee0059815a5ec49682cdf03
[2024-03-09 21:46:15] Unable to find build for 698f532249068fc7d32b8cc80379c7a1b52168f9
[2024-03-09 21:46:16] Unable to find build for 40d985e1af4e88ec0dc4a43ddaf68c272dba32dd
[2024-03-09 21:46:17] Unable to find build for e074bae30fcb342cf3f62ba19c47201807f167bb
[2024-03-09 21:46:17] Unable to find build for dfb5d61dae1b8fdf4fb3df8740ed0b97097dd1c0
[2024-03-09 21:46:18] Unable to find build for eb31f3bf65119a88282fdd03995593242d92b788
[2024-03-09 21:46:19] Unable to find build for 4df9caeb2073fdb1bc558e324a2ecc35152c1d33
[2024-03-09 21:46:20] Unable to find build for 5e2e7bcd99861725338c8e9804ee7bc918bbae9f
[2024-03-09 21:46:21] Unable to find build for 1a5f7a3c39bb837d8ae3a6fea7e5be495f27f549
[2024-03-09 21:46:22] Unable to find build for 6a713f90fba63cd6f585f66d542130a9ae8b03a9
[2024-03-09 21:46:23] Unable to find build for 945aa6c8a8adb41645e19b46374197bff720a0af
[2024-03-09 21:46:23] Unable to find build for 9a7ef455619cb51292013df38a5017291e6ca0f0
[2024-03-09 21:46:24] Unable to find build for 63e88afd6891be94204e214404e0983c827c9fb3
[2024-03-09 21:46:25] Unable to find build for 47d03af2398d6089a5b762c83db3044b34ce4a04
[2024-03-09 21:46:27] Unable to find build for 0e77d9f847ee80d7dfc6afb73d22090e6ed03d3e
[2024-03-09 21:46:27] Unable to find build for c9539953d2b0e0943aeb734c4b4a587ad398c977
[2024-03-09 21:46:28] Unable to find build for 93bce1e1b422914141adece9ff596df498cf130d
[2024-03-09 21:46:29] Unable to find build for 67343475792748f344bacd32290b380fc8bb753d
[2024-03-09 21:46:30] Unable to find build for 8ac74fa64d24ef9abf69f6807b5f630b869a78ac
[2024-03-09 21:46:31] Unable to find build for 4e63443a1754ee9168a23bbff7219dad219db9e6
[2024-03-09 21:46:32] Unable to find build for e2e4557b8d3d2d82d246a1333012340a78e37259
[2024-03-09 21:46:33] Unable to find build for d20d0f5e7849105c0efe2e56743abc414e1c1c94
[2024-03-09 21:46:34] Unable to find build for 8dcd15392aae3caccbe30c85cd21bdec32161396
[2024-03-09 21:46:34] Unable to find build for a463e87b55f0f22244af368bcffcc542125da506
[2024-03-09 21:46:35] Unable to find build for ddda3c5cc90966a4e885c9bac31fad3f46c9936e
[2024-03-09 21:46:37] Unable to find build for f9c17890d242a5b7ea2ca7e566db9c53a5909163
[2024-03-09 21:46:38] Unable to find build for 44a27f2fec8088955bee59ca128bea827b02269e
[2024-03-09 21:46:38] Unable to find build for 21e730d5979d92d75737721b7d46e3b95154ddd5
[2024-03-09 21:46:39] Unable to find build for 7dcc7bdd3296b263b8641aea88ff9950718191de
[2024-03-09 21:46:40] Unable to find build for 6b8582441a76c70ed377ca3f0ee02facdd9eaef1
[2024-03-09 21:46:41] Unable to find build for b0b878dae244416c3b4799f43ee2f5176f3d3fc8
[2024-03-09 21:46:42] Unable to find build for 90f306856d7b0d1f649a504848bf5aa13c7cd20b
[2024-03-09 21:46:43] Unable to find build for 9125a74241251354dc6974a86da3752a8f085e29
[2024-03-09 21:46:43] Unable to find build for 051e5256dd23f438c1b50609711bbe7c77713afe
[2024-03-09 21:46:44] Unable to find build for 21ee2413a28e5542d1007fd78845da74ffddef11
[2024-03-09 21:46:45] Unable to find build for 1590dd97240c64e223f77256256e05a20d5e9f17
[2024-03-09 21:46:46] Unable to find build for ac61888b2c1125ef1fb7a7afc4fd9b6f5f3a0fd5
[2024-03-09 21:46:47] Unable to find build for 3fed5fe0c047f70a537756a267648ed04e94500b
[2024-03-09 21:46:48] Unable to find build for 090ab6540cc56bf36cf1b0603785f6edb573fa8c
[2024-03-09 21:46:49] Unable to find build for 2583e2a361abd308a93dc72eb7a5fd7c425daebc
[2024-03-09 21:46:49] Unable to find build for 0987288cb7d2b1f7907293541f763a78f281ebed
[2024-03-09 21:46:50] Unable to find build for f22be1e1752b2f99afb23dc99aaaea6f00069560
[2024-03-09 21:46:51] Unable to find build for 40a429fa8f4975b3440e1d70ce8d94c900d1d776
[2024-03-09 21:46:52] Unable to find build for 4001ea4b11b043c6c44a9f41e26c70c3ce647a60
[2024-03-09 21:46:53] Unable to find build for 6dd4ac1190657b07628c023cb5129a4cfc5f8a1e
[2024-03-09 21:46:54] Unable to find build for ff2d8eae2a68dfd1db873a06ae7d80d8068519fa
[2024-03-09 21:46:54] Unable to find build for b5f62ac6208752bb2b8065bec1221e96c39fc1b9
[2024-03-09 21:46:55] Unable to find build for 15e93c26055773272fdfcf2c032a26760a09427a
[2024-03-09 21:46:56] Unable to find build for 8c7a686c8691c9bd279edd0e8955a597d720c8b4
[2024-03-09 21:46:57] Unable to find build for ee04f994bad88afccb605c7bc4672e7d3a58460d
[2024-03-09 21:46:59] Unable to find build for 0e28f303a0c1b4e1937502ecbe553e6419d9eb0f
[2024-03-09 21:46:59] Unable to find build for 88e94331994ba660dcd0803ef13d26764c88155e
[2024-03-09 21:47:00] Unable to find build for 10b61df9751188f69496ef6a3396e4e3a4d2ec3a
[2024-03-09 21:47:01] Unable to find build for 4fe7a24c03bf689f4065ca9fc2e667e93651ca73
[2024-03-09 21:47:02] Unable to find build for 5fbea27fb6756e851951b0c9a2af34dcc0444a30
[2024-03-09 21:47:03] Unable to find build for 7f191ca283cd971d4fe05f2061dcf1918045a267
[2024-03-09 21:47:03] Unable to find build for 5d027e405bd8553cbaf51f022a0ce22075bfb092
[2024-03-09 21:47:04] Unable to find build for 63733c638f0bb29f10e810256082d776c8e85e9b
[2024-03-09 21:47:05] Unable to find build for e7850274013002227152edfb4246a8b4dfe022a6
[2024-03-09 21:47:06] Unable to find build for 4c9482a31824ac6dae31c3a4d5145c579d4623fc
[2024-03-09 21:47:07] Unable to find build for 8d9e1646bd6e644166d0da08d8d10bde4876b156
[2024-03-09 21:47:08] Unable to find build for da9aa1960b6316ac90b052abcdaf65643a1743c4
[2024-03-09 21:47:09] Unable to find build for 139a2e4715b7d183c63b04e9fd893b2b23dde432
[2024-03-09 21:47:09] Unable to find build for 5767f4856a8ef3a29064e055e6098f98dcf1b4a0
[2024-03-09 21:47:11] Unable to find build for b0ba248ac06eb82fdb8b50a2447cd8dbdf5a733b
[2024-03-09 21:47:12] Unable to find build for f8c2d8a8b39bc557469364a31cbe575fb042da26
[2024-03-09 21:47:13] Unable to find build for 3c782aff4205a232d793f3ef452d299679ecee7f
[2024-03-09 21:47:13] Unable to find build for 35299f224bb17356c1ab82a098bc2a72c95f2e6a
[2024-03-09 21:47:14] Unable to find build for bc25e9531ce3edaab08e6ef14567c3389c361b17
[2024-03-09 21:47:15] Unable to find build for 5c77ac99c3edf3e9190a428c3734ee9e0694c584
[2024-03-09 21:47:16] Unable to find build for 1f89f18d3af85b731d9dcc7b244bb89e94c31a3d
[2024-03-09 21:47:17] Unable to find build for 42cffffc140b40567782b31b3aa57fa205dc76fb
[2024-03-09 21:47:18] Unable to find build for b9e4cd09297439ee5f10b4adf9c1deed95c6a210
[2024-03-09 21:47:19] Unable to find build for febfcfaa0b38623bd277fc48b396ae7a1c5f2e9c
[2024-03-09 21:47:20] Unable to find build for 461ef0c426d37449827d4b4ec50cf5b4862e18d0
[2024-03-09 21:47:21] Unable to find build for 8ad955cc276516c085cb169381ce3ebef0e4243e
[2024-03-09 21:47:22] Unable to find build for 67fd66802500dfeb8f373485d54e31dc17f48547
[2024-03-09 21:47:23] Unable to find build for c07cc5fbfa5a082e4acf66d95dbf935cccb7fe41
[2024-03-09 21:47:24] Unable to find build for f363f35d8a8d9d72e21e6c023850e065f78ce2b1
[2024-03-09 21:47:24] Unable to find build for 27a282527a8f05467c66266eb242c8fb818226e0
[2024-03-09 21:47:25] Unable to find build for 7ec724ee3aa72e8fecc8902e02f8cabf64a7377f
[2024-03-09 21:47:26] Unable to find build for 5832b428eaea5739c241bb2feb50545e55c99c09
[2024-03-09 21:47:27] Testing build b73f06a9fdb113887db825ebab5b40fcb4ffe1f9 (20240227172311)
[2024-03-09 21:47:29] > Verifying build...
[2024-03-09 21:47:29] Running: /home/test/.cache/autobisect/builds/js-m-a-linux-asan-debug-b73f06a9fdb1/dist/bin/js --wasm-compiler=baseline -e "quit()"
[2024-03-09 21:47:30] > Launching build with testcase...
[2024-03-09 21:47:30] Running: /home/test/.cache/autobisect/builds/js-m-a-linux-asan-debug-b73f06a9fdb1/dist/bin/js --wasm-compiler=baseline poc_jmp.js
[2024-03-09 21:47:30] Testing build edfd64d3c6a087312979ee83fa95b7f56709dc79 (20240227150958)
[2024-03-09 21:47:32] > Verifying build...
[2024-03-09 21:47:32] Running: /home/test/.cache/autobisect/builds/js-m-a-linux-asan-debug-edfd64d3c6a0/dist/bin/js --wasm-compiler=baseline -e "quit()"
[2024-03-09 21:47:32] > Launching build with testcase...
[2024-03-09 21:47:32] Running: /home/test/.cache/autobisect/builds/js-m-a-linux-asan-debug-edfd64d3c6a0/dist/bin/js --wasm-compiler=baseline poc_jmp.js
[2024-03-09 21:47:33] > Failed to reproduce issue!
[2024-03-09 21:47:33] Testing build cbbff9ecf48ea994542d529d599e41a038ad1107 (20240227161314)
[2024-03-09 21:47:34] > Verifying build...
[2024-03-09 21:47:34] Running: /home/test/.cache/autobisect/builds/js-m-a-linux-asan-debug-cbbff9ecf48e/dist/bin/js --wasm-compiler=baseline -e "quit()"
[2024-03-09 21:47:35] > Launching build with testcase...
[2024-03-09 21:47:35] Running: /home/test/.cache/autobisect/builds/js-m-a-linux-asan-debug-cbbff9ecf48e/dist/bin/js --wasm-compiler=baseline poc_jmp.js
[2024-03-09 21:47:35] > Failed to reproduce issue!
[2024-03-09 21:47:35] Reduced build range to:
[2024-03-09 21:47:35] > Start: cbbff9ecf48ea994542d529d599e41a038ad1107 (20240227161314)
[2024-03-09 21:47:35] > End: b73f06a9fdb113887db825ebab5b40fcb4ffe1f9 (20240227172311)
[2024-03-09 21:47:35] > https://hg.mozilla.org/integration/autoland/pushloghtml?fromchange=cbbff9ecf48ea994542d529d599e41a038ad1107&tochange=b73f06a9fdb113887db825ebab5b40fcb4ffe1f9
[2024-03-09 21:47:35] Bisection completed in: 0:05:34
```

---

**Comment 1 — jdemooij@mozilla.com — 2024-03-11T08:52:48Z**

The regression range in comment 0 points to bug 1879179.

---

**Comment 2 — jseward@acm.org — 2024-03-11T10:54:09Z**

Created attachment 9390488
Log leading up to the bad jump

This is the sequence of basic blocks leading up to the bad jump.  Note that
execution happened in the order shown, but the blocks are not contiguous.  The
bad jump is the return at 0x17E59304BF86, which implies the stack is trashed.
0x47AF330 is probably a data area, mostly zero.

---

**Comment 3 — jseward@acm.org — 2024-03-11T11:10:59Z**

This, in the just-about-to-fail code
```
        0x17E59304BEFD:  movl $-84833054,%eax  // 0xfaf18ce2
```
is visible in the IONFLAGS=codegen output
```
  [Codegen] movl       $0xfaf18ce2, %eax
```
and that is in the baseline code for function index 0.  It's a big function
though.  That same function has at least two sequences of `addq $8, %rsp`s,
which is a bit strange.

---

**Comment 4 — jseward@acm.org — 2024-03-11T11:32:52Z**

(In reply to Julian Seward [:jseward] from comment #2)
> which implies the stack is trashed.

Or maybe the stack is not trashed, but the stack pointer is wrong.
Maybe related to the `addq $8, %rsp` sequences in comment 3 ?

---

**Comment 5 — ydelendik@mozilla.com — 2024-03-11T18:45:52Z**

Created attachment 9390599
poc_jmp_reduced1.js

cc'ing ben to confirm a duplicate with array.new

---

**Comment 6 — bvisness@mozilla.com — 2024-03-11T19:38:38Z**

Created attachment 9390612
poc_jmp_reduced2.js

This is unrelated to the array.new. The attached file reproduces the issue without using any GC features. (That said, there is one small issue with error reporting on array bounds; the error is catchable in wasm when it should not be. This makes the array.new effectively act as a wasm `throw` when it should not. This is being addressed in bug 1884767.)

---

**Comment 7 — rhunt@eqrion.net — 2024-03-11T20:50:24Z**

This appears to be an issue with try_table and try-delegate combined.

---

**Comment 8 — rhunt@eqrion.net — 2024-03-12T17:12:55Z**

Triaging this to at least a S2 until I figure out more.

---

**Comment 9 — rhunt@eqrion.net — 2024-03-12T21:14:33Z**

Created attachment 9390871
WIP: Bug 1884518 - wasm: Use correct stack height for try_table.

---

**Comment 10 — rhunt@eqrion.net — 2024-03-12T21:27:20Z**

The attached patch fixes all the test cases. I need to do a little more investigating to make sure there's nothing else lurking here.

If not, the issue appears to be that we were using the wrong stack offset when constructing the exception landing pad for try_table. It included space for params, while we should not have that. I think this could lead to misaligned stack, which appears to be able to lead to loading an incorrect return address.

This requires the `try_table` instruction which is only enabled in nightly and early beta.

---

**Comment 11 — release-mgmt-account-bot@mozilla.tld — 2024-03-13T12:15:31Z**

The bug has a release status flag that shows some version of Firefox is affected, thus it will be considered confirmed.

---

**Comment 12 — rhunt@eqrion.net — 2024-03-22T16:49:53Z**

I think this patch is not sufficient in the case the case there are extra pass-through values on the stack in addition to the try_table params. I'll need to write a more extensive patch.

---

**Comment 13 — rhunt@eqrion.net — 2024-03-29T14:17:06Z**

I am still working on this, trying to find a clean fix.

---

**Comment 14 — rhunt@eqrion.net — 2024-03-29T20:20:33Z**

I had to do some more auditing of our multi-value block params and results code in baseline, and now have a pretty good grasp of this issue.

The issue was not that we were using the wrong framePushed for the landing pad in `try_table`, but that our `delegate` instruction was using the wrong framePushed. It was setting framePushed to Control.stackHeight [1] when jumping to the landing pad. This is correct for the legacy `try` handler, but `try_table` uses a slightly different value (Control.stackHeight + paramSizeOnStack). They're both correct, but delegate needs to know which to use.

As for the severity of this issue, it looks like this bug could result in an incorrect stack pointer which could result in incorrect values loaded or possibly an incorrect return address popped on function return (if I understand what's happening in the POC correctly). sec-high seems right. This bug requires the `exnref` feature, which is enabled in nightly and early beta (not release channels).

This overlaps with a refactoring/optimization I was hoping to do for a while now: bug 1853452. It would change how delegate works so that the unwinder handles `delegate` instead of emitting code in baseline functions to perform manual jumps/rethrows. I just finished implementing it today and verified that it fixes this issue. I plan on fixing this under that public bug as it's a better fix and is good cover. The WIP patch there has no reference to any sorts of issues like this, and is mostly unrelated new code.

[1] https://searchfox.org/mozilla-central/rev/fe951a0a0372de45ebd8c7f5be600253aeda9a92/js/src/wasm/WasmBaselineCompile.cpp#4583-4584

---

**Comment 15 — rhunt@eqrion.net — 2024-04-04T16:09:44Z**

Bug 1853452 landed and fixed this issue.
