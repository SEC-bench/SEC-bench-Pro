# Ion only writes 32-bits to 64-bit stack result slot, and baseline reads the full slot

Bug URL: https://bugzilla.mozilla.org/show_bug.cgi?id=1968423
CVE: CVE-2025-8027
Component: JavaScript: WebAssembly
Bounty: (unknown)
Date: 2025-05-25T09:37:10Z
Keywords: csectype-uninitialized, pernosco, reporter-external, sec-high
See Also:
- https://bugzilla.mozilla.org/show_bug.cgi?id=1972292

Created attachment 9490606
poc.js

## Reproduce
1. Clone the Firefox mirror from https://github.com/mozilla/gecko-dev
2. Run build command: `mkdir fuzzbuild_OPT.OBJ && cd fuzzbuild_OPT.OBJ && ../configure --enable-address-sanitizer --disable-jemalloc --enable-debug --enable-optimize --disable-shared-js --enable-application=js --enable-gczeal && make -j64` in the js/src directory of the firefox checkout
3. Run poc: `fuzzbuild_OPT.OBJ/dist/bin/js poc.js`

- my test spidermonkey commit hash
```
commit 2fc84c3d7aba20db92741279f0b4ac9173635b5c (HEAD -> master, origin/master, origin/HEAD)
Author: Ed Lee <edilee@mozilla.com>
Date:   Sat May 24 06:13:48 2025 +0000

    Bug 1965588 - migrate link preview labs users expecting shift-alt and feature enabled for end of labs rollout r=txia,firefox-ai-ml-reviewers
    
    Detect labs enrollment to keep enabled once and keep shift-alt shortcut with legacy prefs. Support prefs like chatbot.
    
    Differential Revision: https://phabricator.services.mozilla.com/D250912
```

## Bisect
Additionally, I ran autobisect:

https://hg.mozilla.org/integration/autoland/pushloghtml?fromchange=46e8f41a1f784a509264e3a1cd8981ee8bb0b06e&tochange=2832dffe91bb84594708723ebdd58c77b247d376

## ASAN Log
```
AddressSanitizer:DEADLYSIGNAL
=================================================================
==481137==ERROR: AddressSanitizer: SEGV on unknown address (pc 0x7f37ad0601fe bp 0x7ffe2717d7f0 sp 0x7ffe2717d748 T0)
==481137==The signal is caused by a READ memory access.
==481137==Hint: this fault was caused by a dereference of a high value address (see register values below).  Disassemble the provided pc to learn which register was used.
/home/sakura/.cache/autobisect/builds/js-m-c-linux-asan-opt-72ee50ceade7/dist/bin/llvm-symbolizer: error: '[anon:js-executable-memory]': No such file or directory
    #0 0x7f37ad0601fe  ([anon:js-executable-memory]+0x11fe)
    #1 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #2 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #3 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #4 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #5 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #6 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #7 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #8 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #9 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #10 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #11 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #12 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #13 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #14 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #15 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #16 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #17 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #18 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #19 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #20 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #21 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #22 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #23 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #24 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #25 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #26 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #27 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #28 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #29 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #30 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #31 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #32 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #33 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #34 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #35 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #36 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #37 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #38 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #39 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #40 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #41 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #42 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #43 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #44 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #45 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #46 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #47 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #48 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #49 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #50 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #51 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #52 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #53 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #54 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #55 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #56 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #57 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #58 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #59 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #60 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #61 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #62 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #63 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #64 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #65 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #66 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #67 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #68 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #69 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #70 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #71 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #72 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #73 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #74 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #75 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #76 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #77 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #78 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #79 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #80 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #81 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #82 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #83 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #84 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #85 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #86 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #87 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #88 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #89 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #90 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #91 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #92 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #93 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #94 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #95 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #96 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #97 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #98 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #99 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #100 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #101 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #102 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #103 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #104 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #105 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #106 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #107 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #108 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #109 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #110 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #111 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #112 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #113 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #114 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #115 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #116 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #117 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #118 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #119 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #120 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #121 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #122 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #123 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #124 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #125 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #126 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #127 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #128 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #129 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #130 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #131 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #132 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #133 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #134 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #135 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #136 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #137 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #138 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #139 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #140 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #141 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #142 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #143 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #144 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #145 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #146 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #147 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #148 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #149 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #150 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #151 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #152 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #153 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #154 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #155 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #156 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #157 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #158 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #159 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #160 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #161 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #162 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #163 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #164 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #165 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #166 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #167 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #168 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #169 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #170 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #171 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #172 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #173 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #174 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #175 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #176 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #177 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #178 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #179 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #180 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #181 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #182 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #183 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #184 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #185 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #186 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #187 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #188 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #189 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #190 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #191 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #192 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #193 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #194 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #195 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #196 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #197 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #198 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #199 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #200 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #201 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #202 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #203 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #204 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #205 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #206 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #207 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #208 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #209 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #210 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #211 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #212 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #213 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #214 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #215 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #216 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #217 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #218 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #219 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #220 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #221 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #222 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #223 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #224 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #225 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #226 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #227 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #228 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #229 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #230 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #231 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #232 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #233 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #234 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #235 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #236 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #237 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #238 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #239 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #240 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #241 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #242 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #243 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #244 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #245 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #246 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #247 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #248 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #249 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #250 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #251 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #252 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #253 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)
    #254 0x7f37ad060219  ([anon:js-executable-memory]+0x1219)

==481137==Register values:
rax = 0x0000516000000000  rbx = 0x000000000000e3c2  rcx = 0x00002eb6fb7ec030  rdx = 0x00002eb6fb7ec058  
rdi = 0x00002eb6fb791178  rsi = 0x00002eb6fb783158  rbp = 0x00007ffe2717d7f0  rsp = 0x00007ffe2717d748  
 r8 = 0x000019b45b600020   r9 = 0x0000000000000000  r10 = 0x00005180d7da7237  r11 = 0x00007ffe2717d718  
r12 = 0x000051b000002380  r13 = 0x00007ffe2729eb20  r14 = 0x0000518000002880  r15 = 0x00007f36a45ab000  
AddressSanitizer can not provide additional info.
SUMMARY: AddressSanitizer: SEGV ([anon:js-executable-memory]+0x11fe) 
==481137==ABORTING
```

---

**Comment 1 — dveditz@mozilla.com — 2025-05-28T21:44:20Z**

The stack looks like it's recursion causing stack exhaustion, which is normally not exploitable. But I haven't looked at what the wasm is actually doing in there.

---

**Comment 2 — eternalsakuraalpha@gmail.com — 2025-06-03T14:12:06Z**

hello, any update?

---

**Comment 3 — bvisness@mozilla.com — 2025-06-03T14:52:06Z**

I do not have a complete answer, but from poking around it is indeed a recursion situation, it seems to only affect baseline, and it doesn't repro for me unless I enable optimizations. It's specifically triggering on an array.get instruction. Pernosco: https://pernos.co/debug/1XJA8O6uRmwFNy58En1OAQ/index.html#f{m[BIA,DHU_,t[AQ,1Fg_,f{e[BHg,Wtij___/

---

**Comment 4 — jpages@mozilla.com — 2025-06-03T15:18:00Z**

I don't have a proper fix yet, but it's indeed a recursion situation. By default, we end up calling a bogus address which is flagged by the address sanitizer.

When forcing the compiler to be either baseline or ion, I can get the error "InternalError: too much recursion", which seems to be the expected behaviour. The bug can reproduce only with the default parameters and lazy tiering enabled.

---

**Comment 5 — continuation@gmail.com — 2025-06-04T21:53:15Z**

Could there be some issue where ASan stack frames are so big that the recursion guards we use don't protect us sufficiently?

---

**Comment 6 — dveditz@mozilla.com — 2025-06-11T22:37:30Z**

Calling this sec-high because of the bounds issue, but if it's an ASAN artifact it would be less severe.

---

**Comment 7 — release-mgmt-account-bot@mozilla.tld — 2025-06-12T12:14:20Z**

The severity field for this bug is set to S3. However, the bug is flagged with the `sec-high` keyword.
:jpages, could you consider increasing the severity of this security bug?

For more information, please visit [BugBot documentation](https://wiki.mozilla.org/BugBot#severity_high_security.py).

---

**Comment 8 — jpages@mozilla.com — 2025-06-16T14:38:50Z**

Created attachment 9494927
testcase.js

---

**Comment 9 — jseward@acm.org — 2025-06-17T11:31:41Z**

Created attachment 9495162
Even smaller testcase

An even smaller testcase.  It seems likely to me that the problem
is an interaction between multivalue returns and reftypes.  If the
multivalue return of function `(;1;)` is removed, the segfault goes away.

Running with JS_GC_PROFILE=0 JS_GC_PROFILE_NURSERY=0 shows that
GC does indeed happen.

---

**Comment 10 — jseward@acm.org — 2025-06-17T13:09:09Z**

Created attachment 9495191
Even more smallerer testcase

Here's an even smaller testcase.  It removes one of the calls to
`func (;1;)`, so there is only one such call, and the recursive call.

The segfault happens on a `movzbl` instruction with scale factor 1,
which I believe is the array access for the `array.get_u 0`.  From
looking at the base and index reg values for that, I'd guess they have
been trashed somehow by the `call 1` two lines above.  

I kinda lost the trail at that point.  One difficulty is that the
`array.new_default 0` before the call turns into a bunch of spaghetti
that mashes the stack around, and it's hard to tell what's going on.

---

**Comment 11 — eternalsakuraalpha@gmail.com — 2025-06-19T14:55:53Z**

hello, any update?

---

**Comment 12 — jpages@mozilla.com — 2025-06-23T21:20:54Z**

Created attachment 9496393
(secure)

---

**Comment 13 — jpages@mozilla.com — 2025-06-23T21:28:03Z**

I have a potential fix but I'm not 100% sure if it's the right one.

This patch adds a zero extension on 64-bits around array accesses in Baseline. I think all of these recursive calls with reftypes may have left some garbage in the high-part of registers, which wasn't cleaned in the following calls.

Eventually, this caused a crash when trying to access the array after a few calls, with a pretty obviously wrong high address.
I think a register containing garbage from a previously returned value was used for computing the array access. This wrong address was picked up by the address sanitizer but the bug is also presents without asan.

---

**Comment 14 — rhunt@eqrion.net — 2025-06-25T21:33:25Z**

*** Bug 1972292 has been marked as a duplicate of this bug. ***

---

**Comment 15 — rhunt@eqrion.net — 2025-06-25T21:34:02Z**

*** Bug 1973326 has been marked as a duplicate of this bug. ***

---

**Comment 16 — rhunt@eqrion.net — 2025-06-25T21:38:07Z**

The core issue here is that for 32-bit function results passed via the stack there is 64-bits of space allocated (on 64-bit platforms) [1]. Ion only stores 32-bits [2], while baseline will read the entire 64-bits [3]. This leads to there being junk in the high 32-bits of the 64-bit register holding a 32-bit value. This breaks our invariant that the high bits of 64-bit registers are either sign-extended or zero-extended (depending on platform) [4], which leads to segfaults like this when we use the GPR holding the value in machine code instructions that don't ignore the high bits.

This shows up usually when using the index as part of a BaseIndex addressing operation.

This bug has probably existed for a while, but I'm guessing us recently enabling lazy tiering for all content has caused the fuzzers to start running more mixed tier wasm code.

[1] https://searchfox.org/mozilla-central/rev/c25dbe453ff9ca10f2c6bdfb873893c515a29826/js/src/wasm/WasmStubs.h#82
[2] https://searchfox.org/mozilla-central/rev/c25dbe453ff9ca10f2c6bdfb873893c515a29826/js/src/jit/CodeGenerator.cpp#10581
[3] https://searchfox.org/mozilla-central/rev/c25dbe453ff9ca10f2c6bdfb873893c515a29826/js/src/wasm/WasmBCFrame.h#833-838
[4] https://searchfox.org/mozilla-central/rev/c25dbe453ff9ca10f2c6bdfb873893c515a29826/js/src/jit/MacroAssembler.h#310

---

**Comment 17 — rhunt@eqrion.net — 2025-06-25T21:44:33Z**

Created attachment 9496865
(secure)


Ion stores stack results that are refs using MWasmStoreRef, and this
is only safe because we manually disable the barriers for the
instruction. Add a dedicated node that is safe for ref stack results
and just does the plain store we need.

---

**Comment 18 — rhunt@eqrion.net — 2025-06-25T21:44:38Z**

Created attachment 9496866
Bug 1968423 - wasm: Add assertion to baseline. r?jseward

---

**Comment 19 — rhunt@eqrion.net — 2025-06-25T21:52:12Z**

As for the severity, I'm assuming that an attacker could somehow figure out how to prime the correct stack offset so that they control the garbage that gets inserted into the high bits of the i32 value. These high bits will then be ignored or not depending on what machine code instruction is used.

So for example, `array.get` in baseline is implemented by an upfront bounds check that does branch32 [1] followed by an index into the array using BaseIndex. The branch32 will ignore the high bits, while the BaseIndex will not. This could lead to a bounds check bypass and a read-write primitive. I'm not sure if there are other exploitable sites in baseline yet, that's just the one the fuzzers found so far.

[1] https://searchfox.org/mozilla-central/rev/c25dbe453ff9ca10f2c6bdfb873893c515a29826/js/src/wasm/WasmBaselineCompile.cpp#7489
[2] https://searchfox.org/mozilla-central/rev/c25dbe453ff9ca10f2c6bdfb873893c515a29826/js/src/wasm/WasmBaselineCompile.cpp#8473

---

**Comment 20 — rhunt@eqrion.net — 2025-06-25T21:52:35Z**

I have a patch that fixes this, but no simple test yet. I will work on that next.

---

**Comment 21 — rhunt@eqrion.net — 2025-06-26T20:47:21Z**

Created attachment 9497127
Bug 1968423 - wasm: Add test. r?jseward

---

**Comment 22 — rhunt@eqrion.net — 2025-06-26T20:59:37Z**

I've written a minimal test that reliably reproduces this. I'm trying to confirm the affected versions, but don't have that yet.

---

**Comment 23 — rhunt@eqrion.net — 2025-07-02T15:51:31Z**

I was able to reproduce this issue on 140, 141, 142. I could not reproduce these test cases on 115, because they rely on wasm-gc to have array access instructions consume these malformed i32 values. However, there could be other vulnerable instructions (table.get seems likely [1]) and so it seems certain to me that 115 is also effected.

[1] https://searchfox.org/mozilla-central/rev/311230215f69ac675d0fb4d5c0f5108228f17388/js/src/wasm/WasmBaselineCompile.cpp#7158

---

**Comment 24 — rhunt@eqrion.net — 2025-07-02T16:07:38Z**

Comment on attachment 9496865
(secure)

### Security Approval Request
* **How easily could an exploit be constructed based on the patch?**: Not easily. A diligent observer could diff the codegen and see that we changed from store32 to storePtr. But there's also noise in the patch that could mislead them to think this is about reference types. Even if they notice the change, they would have to connect it to baseline using loadPtr to consume these values, which is not obvious. Then they would need to figure out that some instructions don't correctly handle i32 values stored in 64-bit registers when the high bits are set.
* **Do comments in the patch, the check-in comment, or tests included in the patch paint a bulls-eye on the security problem?**: No
* **Which branches (beta, release, and/or ESR) are affected by this flaw, and do the release status flags reflect this affected/unaffected state correctly?**: All branches, flags are correct
* **If not all supported branches, which bug introduced the flaw?**: None
* **Do you have backports for the affected branches?**: No
* **If not, how different, hard to create, and risky will they be?**: Patch applies clean to everything but esr115. It looks like the patch doesn't apply to ESR115 because some code has moved around (but hasn't meaningfully changed), it doesn't seem too hard to rebase the patch.
* **How likely is this patch to cause regressions; how much testing does it need?**: Not likely. Multi value code is extremely uncommon on the web, and our test suite is fairly thorough in this area.
* **Is the patch ready to land after security approval is given?**: Yes
* **Is Android affected?**: Yes

---

**Comment 25 — dveditz@mozilla.com — 2025-07-02T18:16:25Z**

Ryan: The initial comment bisected to bug 1965195, but the sec-approval request indicates that wasn't really the underlying bug and instead just let yo

---

**Comment 26 — rhunt@eqrion.net — 2025-07-02T18:30:04Z**

Yes, that bug changed our tiering system so that this bug was much easier to trigger. But there was nothing preventing it from happening before that bug if you split your code to two different modules such that one was Ion compiled because it was small and the other was baseline compiled because it was big and timed it right to run the exploit before the background compilation finished.

---

**Comment 27 — tom@mozilla.com — 2025-07-02T18:46:03Z**

Comment on attachment 9496865
(secure)

Approved to land and request uplift

---

**Comment 28 — pulsebot@bmo.tld — 2025-07-08T16:39:00Z**

Pushed by rhunt@eqrion.net:
https://github.com/mozilla-firefox/firefox/commit/c14351b2b036
https://hg.mozilla.org/integration/autoland/rev/86694580ac1d
wasm: Simplify stack result handling in Ion. r=jseward

---

**Comment 29 — ryanvm@gmail.com — 2025-07-09T03:22:05Z**

https://hg.mozilla.org/mozilla-central/rev/86694580ac1d

---

**Comment 30 — release-mgmt-account-bot@mozilla.tld — 2025-07-09T12:04:51Z**

The patch landed in nightly and beta is affected.
:rhunt, is this bug important enough to require an uplift?
- If yes, please nominate the patch for beta approval.
  - See https://wiki.mozilla.org/Release_Management/Requesting_an_Uplift for documentation on how to request an uplift.
- If no, please set `status-firefox141` to `wontfix`.

For more information, please visit [BugBot documentation](https://wiki.mozilla.org/BugBot#uplift_beta.py).

---

**Comment 31 — rhunt@eqrion.net — 2025-07-09T19:24:12Z**

Created attachment 9499604
(secure)


Ion stores stack results that are refs using MWasmStoreRef, and this
is only safe because we manually disable the barriers for the
instruction. Add a dedicated node that is safe for ref stack results
and just does the plain store we need.

Original Revision: https://phabricator.services.mozilla.com/D255036

---

**Comment 32 — phab-bot@bmo.tld — 2025-07-09T19:28:27Z**

### firefox-beta Uplift Approval Request
- **User impact if declined**: Potentially exploitable bounds check bypass
- **Code covered by automated testing**: no
- **Fix verified in Nightly**: yes
- **Needs manual QE test**: no
- **Steps to reproduce for manual QE testing**: N/A
- **Risk associated with taking this patch**: Low
- **Explanation of risk level**: Multi value code is extremely uncommon on the web, and our test suite is fairly thorough in this area
- **String changes made/needed**: N/A
- **Is Android affected?**: yes

---

**Comment 33 — rhunt@eqrion.net — 2025-07-09T19:28:56Z**

Created attachment 9499607
(secure)


Ion stores stack results that are refs using MWasmStoreRef, and this
is only safe because we manually disable the barriers for the
instruction. Add a dedicated node that is safe for ref stack results
and just does the plain store we need.

Original Revision: https://phabricator.services.mozilla.com/D255036

---

**Comment 34 — phab-bot@bmo.tld — 2025-07-09T19:29:24Z**

### firefox-esr140 Uplift Approval Request
- **User impact if declined**: Potentially exploitable bounds check bypass
- **Code covered by automated testing**: no
- **Fix verified in Nightly**: yes
- **Needs manual QE test**: no
- **Steps to reproduce for manual QE testing**: N/A
- **Risk associated with taking this patch**: Low
- **Explanation of risk level**: Multi value code is extremely uncommon on the web, and our test suite is fairly thorough in this area
- **String changes made/needed**: N/A
- **Is Android affected?**: yes

---

**Comment 35 — rhunt@eqrion.net — 2025-07-09T19:29:44Z**

Created attachment 9499608
(secure)


Ion stores stack results that are refs using MWasmStoreRef, and this
is only safe because we manually disable the barriers for the
instruction. Add a dedicated node that is safe for ref stack results
and just does the plain store we need.

Original Revision: https://phabricator.services.mozilla.com/D255036

---

**Comment 36 — phab-bot@bmo.tld — 2025-07-09T19:36:01Z**

### firefox-esr128 Uplift Approval Request
- **User impact if declined**: Potentially exploitable bounds check bypass
- **Code covered by automated testing**: no
- **Fix verified in Nightly**: yes
- **Needs manual QE test**: no
- **Steps to reproduce for manual QE testing**: N/A
- **Risk associated with taking this patch**: Low
- **Explanation of risk level**: Multi value code is extremely uncommon on the web, and our test suite is fairly thorough in this area
- **String changes made/needed**: N/A
- **Is Android affected?**: yes

---

**Comment 37 — rhunt@eqrion.net — 2025-07-09T19:36:04Z**

Created attachment 9499610
(secure)


Ion stores stack results that are refs using MWasmStoreRef, and this
is only safe because we manually disable the barriers for the
instruction. Add a dedicated node that is safe for ref stack results
and just does the plain store we need.

Original Revision: https://phabricator.services.mozilla.com/D255036

---

**Comment 38 — phab-bot@bmo.tld — 2025-07-09T19:36:12Z**

### firefox-esr115 Uplift Approval Request
- **User impact if declined**: Potentially exploitable bounds check bypass
- **Code covered by automated testing**: no
- **Fix verified in Nightly**: yes
- **Needs manual QE test**: no
- **Steps to reproduce for manual QE testing**: N/A
- **Risk associated with taking this patch**: Low
- **Explanation of risk level**: Multi value code is extremely uncommon on the web, and our test suite is fairly thorough in this area
- **String changes made/needed**: N/A
- **Is Android affected?**: yes

---

**Comment 39 — pulsebot@bmo.tld — 2025-07-10T02:27:15Z**

https://github.com/mozilla-firefox/firefox/commit/24696457aec3
https://hg.mozilla.org/releases/mozilla-beta/rev/cc5a117a37ef

---

**Comment 40 — pulsebot@bmo.tld — 2025-07-10T02:28:04Z**

https://hg.mozilla.org/releases/mozilla-esr140/rev/016e2a9b8a07

---

**Comment 41 — pulsebot@bmo.tld — 2025-07-10T16:26:59Z**

https://hg.mozilla.org/releases/mozilla-esr115/rev/4abe91f6d0fc

---

**Comment 42 — pulsebot@bmo.tld — 2025-07-10T16:29:15Z**

https://hg.mozilla.org/releases/mozilla-esr128/rev/4bdc152586ef

---

**Comment 43 — pascalc@gmail.com — 2025-07-10T16:55:32Z**

Ryan, the ESR115 push has failures: https://treeherder.mozilla.org/jobs?repo=mozilla-esr115&revision=4abe91f6d0fc98716975cd7cfe1122d9955a8e0d

Do you prefer that I back it out from the branch or do you prefer to provide an additional fix? 
Thanks

---

**Comment 44 — rhunt@eqrion.net — 2025-07-10T17:03:33Z**

Created attachment 9499845
(secure)

---

**Comment 45 — rhunt@eqrion.net — 2025-07-10T17:06:16Z**

I uploaded https://phabricator.services.mozilla.com/D256842 as the fix. Sorry, I mentioned in the esr115 patch that I couldn't build it because of a python issue that broke mach entirely for me. Should have made it more obvious it wasn't ready to go.

---

**Comment 46 — pulsebot@bmo.tld — 2025-07-10T20:44:34Z**

https://hg.mozilla.org/releases/mozilla-esr115/rev/802360feac8a

---

**Comment 47 — pascalc@gmail.com — 2025-07-10T21:20:04Z**

Ryan, the failures are still there after the fix up patch landed:
https://treeherder.mozilla.org/jobs?repo=mozilla-esr115&resultStatus=testfailed%2Cbusted%2Cexception%2Cretry%2Cusercancel&revision=802360feac8ab400f5f4f437658e8348db2a3df6&selectedTaskRun=K1VlBCwZQ8WS-tdoKpajoQ.0

(Given that we are in RC week next week, if we can't get it fixed by then, we might have to consider backing out all the uplifts and fix it next cycle.)

---

**Comment 48 — rhunt@eqrion.net — 2025-07-11T15:38:39Z**

The failure is an assertion that should have been removed in the patch, but wasn't in the rebase that I did. [1] [2]. I'll write a quick patch to fix that.

[1] https://hg-edge.mozilla.org/releases/mozilla-esr115/rev/4abe91f6d0fc#l3.17
[2] https://hg-edge.mozilla.org/releases/mozilla-esr140/rev/016e2a9b8a07#l3.17

---

**Comment 49 — rhunt@eqrion.net — 2025-07-11T15:42:07Z**

Created attachment 9500099
(secure)


This was lost in the rebase conflicts.

---

**Comment 50 — rhunt@eqrion.net — 2025-07-11T15:45:15Z**

I'm still trying to figure out how to build esr115 or even do a try run with the busted mach command. The attached patch will definitely fix the issue, as that assertion should just be removed as it is in the other patches. But I would feel better just being able to run it all locally.

---

**Comment 51 — pulsebot@bmo.tld — 2025-07-11T18:42:44Z**

https://hg.mozilla.org/releases/mozilla-esr115/rev/e729400ad674

---

**Comment 52 — sfriedberger@mozilla.com — 2025-07-15T08:46:40Z**

Created attachment 9500517
advisory.txt

---

**Comment 53 — sfriedberger@mozilla.com — 2025-07-15T10:46:25Z**

Created attachment 9500550
advisory.txt

---

**Comment 54 — sfriedberger@mozilla.com — 2025-07-18T09:53:45Z**

Created attachment 9501486
advisory.txt

---

**Comment 55 — release-mgmt-account-bot@mozilla.tld — 2025-09-02T12:01:07Z**

2 months ago, tjr placed a reminder on the bug using the whiteboard tag `[reminder-test 2025-09-02]` .

rhunt, please refer to the original comment to better understand the reason for the reminder.

---

**Comment 56 — pulsebot@bmo.tld — 2026-02-09T21:27:23Z**

Pushed by rhunt@eqrion.net:
https://github.com/mozilla-firefox/firefox/commit/b6a9cb7eaaf5
https://hg.mozilla.org/integration/autoland/rev/dffa69ed6fb7
wasm: Add assertion to baseline. r=jseward
https://github.com/mozilla-firefox/firefox/commit/e9e7eac5eb24
https://hg.mozilla.org/integration/autoland/rev/13a74a4839e1
wasm: Add test. r=jseward

---

**Comment 57 — sstanca@mozilla.com — 2026-02-10T13:09:46Z**

https://hg.mozilla.org/mozilla-central/rev/dffa69ed6fb7
https://hg.mozilla.org/mozilla-central/rev/13a74a4839e1
