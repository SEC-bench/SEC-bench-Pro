#!/bin/bash
# Build iig-port, the MIT reimplementation of Apple's closed DriverKit
# interface generator `iig` (github.com/Nyktis/iig-port), and install it where
# Xcode keeps iig on a Mac (the Command Line Tools have none), so `xcrun -find
# iig` finds it and xnu's make runs it on a tag's .iig files.
#
#   build-iig-port.sh [PREFIX] [IIG_PORT_REF]
#
# PREFIX/bin/iig is the binary, built with base/darwin/patches/iig-port/'s
# patch, which defaults libclang to a Darwin target, as Apple's iig gets for
# free by running on a Mac, and finds libclang's builtin headers.
# iig-port links apt.llvm.org's libclang, found through llvm-config-$LLVM_VERSION
# (installed by `llvm.sh $LLVM_VERSION all`).
set -euo pipefail

PREFIX="${1:-/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr}"
REF="${2:-${IIG_PORT_REF:-ea6d147d668ca15d490da638012243fcd705f30d}}"
SRC="${BUILD_SRC_DIR:-/tmp/xnu-toolchain-src}/iig-port"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATCH_DIR="${IIG_PORT_PATCH_DIR:-${HERE}/../patches/iig-port}"
LLVM_CONFIG="${LLVM_CONFIG:-$(command -v "llvm-config-${LLVM_VERSION:-24}" || command -v llvm-config || true)}"

[ -x "${LLVM_CONFIG}" ] || { echo "build-iig-port.sh: no llvm-config; set LLVM_CONFIG" >&2; exit 1; }
compgen -G "${PATCH_DIR}/*.patch" >/dev/null || { echo "build-iig-port.sh: no patches in ${PATCH_DIR}; set IIG_PORT_PATCH_DIR" >&2; exit 1; }
LLVM_BINDIR="$("${LLVM_CONFIG}" --bindir)"
CXX="${CXX:-${LLVM_BINDIR}/clang++}"

mkdir -p "$(dirname "${SRC}")" "${PREFIX}/bin"
if [ ! -d "${SRC}/.git" ]; then
    git init -q "${SRC}"
    git -C "${SRC}" remote add origin https://github.com/Nyktis/iig-port
fi
git -C "${SRC}" fetch -q --depth 1 origin "${REF}"
git -C "${SRC}" checkout -q --force FETCH_HEAD
for p in "${PATCH_DIR}"/*.patch; do
    patch -d "${SRC}" -p1 --batch --forward < "${p}" >/dev/null
done

# Upstream's README build line, with our compiler and output path. No rpath:
# libclang-N.so.N is installed in the multiarch libdir the loader searches.
# shellcheck disable=SC2046 # llvm-config's flags are meant to word-split
"${CXX}" -std=c++17 $("${LLVM_CONFIG}" --cxxflags --ldflags) "${SRC}/iig.cpp" -lclang -o "${PREFIX}/bin/iig"
echo "iig-port ${REF} -> ${PREFIX}/bin/iig"
