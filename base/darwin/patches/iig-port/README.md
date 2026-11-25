# `iig-port` patches

[`Nyktis/iig-port`](https://github.com/Nyktis/iig-port) (MIT) is a
cross-platform reimplementation of Apple's closed-source DriverKit generator
`iig`, targeting the same `DriverKit-440` this project builds against. It is a
single `iig.cpp` doing a libclang AST walk plus printf templates, the same
shape as Apple's tool. The kernel build runs it in place of Apple's `iig`.

One patch, `default-darwin-target.patch`, against `ea6d147`: on a non-Apple
host it parses for a Darwin target and finds libclang's builtin headers,
below.

Its outputs differ from Apple's `iig` only for
`iokit/Tests/TestServices/TestDextRematch.iig`, the one input outside the
DriverKit framework directory: its `.iig.cpp` lacks the include preamble
Apple's iig writes without `--framework-name`, and its `.h` lacks an
`@iig implementation` block in a documentation comment. Neither matters to
the build: the implementation block itself includes
`TestDextRematchKernel.h`, which brings in the declarations.

`base/darwin/toolchain/build-iig-port.sh` fetches the pinned commit, applies
the patch and builds it against libclang (found through
`llvm-config`):

```
base/darwin/toolchain/build-iig-port.sh   # -> /Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/iig
```

It installs the binary as `iig`, Xcode's path and the name `xcrun -find iig`
resolves. xnu's Makefiles pass iig no target, because Apple's iig only runs on
a Mac, where libclang's default triple is the host's `arm64-apple-macosx`. On
Linux the default is the Linux host's triple, where xnu's `mach/machine/*.h`
stop with `architecture not supported`. So `default-darwin-target.patch`, on a
non-Apple host only and unless the caller passes `--target=` itself, hands
libclang `--target=arm64-apple-darwin`. (`-target X` and `-arch` are both
rejected by iig's argument handling; only `--target=X` reaches libclang.) Any
Darwin triple gives the same output.

The same patch hands libclang `-resource-dir`, the directory of clang's
builtin headers (`stdint.h` for `EXTERNAL_HEADERS/stdint.h`'s `#include_next`,
`stddef.h`...), unless the caller passes one. libclang 24 builds its driver
from an empty path, so the directory comes out as the relative
`lib/clang/N`, which resolves only from some working directories; make runs
iig from the object tree, where it does not. libclang's C API has no call that
returns the directory, so iig derives it at run time from the library file
`dladdr()` names and `clang_getClangVersion()`'s major version, taking the
first of `<prefix>/lib/clang/N` (an upstream install, libclang in
`<prefix>/lib`) and `/usr/lib/clang/N` (Debian and apt.llvm.org, libclang in
`/usr/lib/<triple>`, where `libclang-common-N-dev` links it) whose
`include/stdint.h` exists. No build flag is needed.

The upstream repository has a single author and no reviewers, and it
generates kernel IPC ABI; its clean-room claim ("based on observing the …
output for different inputs, not on reverse engineering") is unreviewed.
