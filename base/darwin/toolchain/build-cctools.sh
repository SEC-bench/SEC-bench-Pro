#!/bin/bash
# Build Apple's cctools (ld64, libtool, otool, nm, strip, nmedit, lipo,
# codesign_allocate...) as a Linux->Darwin cross toolchain, from
# tpoechtrager/cctools-port.
#
#   build-cctools.sh [PREFIX] [CCTOOLS_PORT_REF]
#
# Two things the LLVM tools cannot give us and this can:
#   * `ld` that understands -kernel, -add_split_seg_info, -segprot, -sectcreate
#     into a kernel Mach-O -- ld64.lld rejects -kernel outright.
#   * the Darwin <mach-o/*.h> and <mach/*.h> headers and the libmacho
#     functions that xnu's own SETUP host tools (kextsymboltool, setsegname)
#     use.
#
# libtapi is not built: it only adds .tbd (text-based stub dylib) support, and a
# kernel link resolves everything from .o files and static archives.
#
# ld64 from the 1009 branch on needs libdispatch and its blocks runtime, which
# Ubuntu does not package; it is built from swift-corelibs-libdispatch into
# /usr/local below, where cctools' configure looks on its own.
set -euo pipefail

PREFIX="${1:-/Library/Developer/CommandLineTools/usr}"
REF="${2:-${CCTOOLS_PORT_REF:-1030.6.3-ld64-956.6}}"
SRC="${BUILD_SRC_DIR:-/tmp/xnu-toolchain-src}/cctools-port"
TARGET_TRIPLE="${CCTOOLS_TARGET:-arm64-apple-darwin}"
# The headers go into the include dir of the unversioned MacOSX.sdk next to
# PREFIX, which on macOS is the CLT's symlink to the current SDK. Here it is a
# real directory, so a versioned SDK installed beside it (MacOSX<version>.sdk,
# what -isysroot names) is never written to.
CCTOOLS_INCLUDE="${CCTOOLS_INCLUDE:-${PREFIX%/usr}/SDKs/MacOSX.sdk/usr/include}"
JOBS="${JOBS:-$(nproc)}"
# libdispatch (-fblocks) and cctools' configure both require clang. Exported so
# cmake and configure pick it up too.
export CC="${HOST_CC_FOR_TOOLS:-clang-${LLVM_VERSION:-24}}"
export CXX="clang++-${LLVM_VERSION:-24}"

mkdir -p "$(dirname "${SRC}")" "${PREFIX}/bin"

if [ ! -d "${SRC}" ]; then
    git clone --depth 1 --branch "${REF}" \
        https://github.com/tpoechtrager/cctools-port.git "${SRC}"
fi

# libdispatch, with the BlocksRuntime it bundles, into /usr/local.
LIBDISPATCH_REF="${LIBDISPATCH_REF:-swift-6.4.0-RELEASE}"
if [ ! -e /usr/local/lib/libdispatch.so ]; then
    DISPATCH_SRC="$(dirname "${SRC}")/swift-corelibs-libdispatch"
    [ -d "${DISPATCH_SRC}" ] || git clone --depth 1 --branch "${LIBDISPATCH_REF}" \
        https://github.com/swiftlang/swift-corelibs-libdispatch.git "${DISPATCH_SRC}"
    cmake -G Ninja -S "${DISPATCH_SRC}" -B "${DISPATCH_SRC}/build" \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_C_FLAGS="-Wno-error=unused-but-set-global"
    ninja -C "${DISPATCH_SRC}/build" -j"${JOBS}"
    ninja -C "${DISPATCH_SRC}/build" install
    # The loader only finds /usr/local/lib through ld.so.cache.
    ldconfig
fi

cd "${SRC}/cctools"
if [ ! -f Makefile ]; then
    # --disable-lto-support: the kernel link uses no LTO, and with llvm-N-dev
    # installed (`llvm.sh N all`) configure would find libLTO and build
    # libstuff/lto.c, whose bundled llvm-c/lto.h needs LLVM headers
    # (llvm-c/Visibility.h, llvm/Config/llvm-config.h) cctools-port does not
    # ship. Without llvm-N-dev, LTO is off anyway.
    #
    # --target sets the default -arch (EMULATED_HOST_CPU_TYPE) and would also
    # prefix every installed name with the triple. xnu's makedefs ask xcrun for
    # the plain names, so --program-prefix= installs them as ld, lipo, otool...
    # and PROGRAM_PREFIX= below makes the tools that run each other (strip ->
    # ld, otool -> llvm-objdump) look for those plain names too.
    ./configure \
        --prefix="${PREFIX}" \
        --target="${TARGET_TRIPLE}" \
        --program-prefix= \
        --disable-lto-support
fi
make -j"${JOBS}" PROGRAM_PREFIX=
make install PROGRAM_PREFIX=

# xnu's own SETUP host tools (kextsymboltool.c, setsegname.c) include <libc.h>,
# <mach-o/arch.h>, <mach-o/swap.h> and <mach/mach_init.h>, none of which exist
# on Linux. cctools-port carries usable copies (include/foreign among them);
# stage them where the HOST_CC wrapper linux-xnu-build generates can -idirafter
# them (after glibc, so its <stdio.h>/<fcntl.h> lookalikes never shadow the
# real ones).
mkdir -p "${CCTOOLS_INCLUDE}"
cp -R "${SRC}/cctools/include/." "${CCTOOLS_INCLUDE}/"

# xnu's SETUP host tools also call what Apple's libmacho provides: the arch
# table (NXGetLocalArchInfo, NXGetArchInfoFromName) and the Mach-O byte
# swappers (swap_mach_header_64 and friends). cctools-port builds both into
# archives it links its own tools with but does not install: libmacho (the arch
# table) and libstuff (the swappers, plus libstuff/port.c's Linux stand-ins for
# the host_info() call NXGetLocalArchInfo makes). They go in /usr/lib, where
# macOS keeps libmacho as part of libSystem and the host linker finds them
# without -L.
cp "${SRC}/cctools/libmacho/.libs/libmacho.a" \
   "${SRC}/cctools/libstuff/.libs/libstuff.a" /usr/lib/

echo "cctools installed in ${PREFIX}/bin"
"${PREFIX}/bin/ld" -v 2>&1 | head -3 || true
