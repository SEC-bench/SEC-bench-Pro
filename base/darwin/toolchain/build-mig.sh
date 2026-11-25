#!/bin/bash
# Build Apple's `mig` (the Mach Interface Generator) and its `migcom` backend
# from apple-oss-distributions/bootstrap_cmds, on Linux, without xcodebuild.
#
#   build-mig.sh [PREFIX] [BOOTSTRAP_CMDS_TAG]
#
# Upstream builds this with an Xcode project whose only real work is:
#   * migcom: a yacc/lex C program in migcom.tproj
#   * mig:    a /bin/sh driver that finds migcom as ../libexec/migcom
# so we drive the same sources with make(1) directly. Apart from ISO C and
# <sys/*.h>, migcom includes a few <mach/*.h> headers for MACH_MSG_TYPE_* and
# boolean_t. Those come from the cctools-port headers build-cctools.sh installs
# into ${CCTOOLS_INCLUDE}, so run this after build-cctools.sh.
set -euo pipefail

PREFIX="${1:-/Library/Developer/CommandLineTools/usr}"
TAG="${2:-${BOOTSTRAP_CMDS_TAG:-bootstrap_cmds-138}}"
SRC="${BUILD_SRC_DIR:-/tmp/xnu-toolchain-src}/bootstrap_cmds"
CCTOOLS_INCLUDE="${CCTOOLS_INCLUDE:-${PREFIX%/usr}/SDKs/MacOSX.sdk/usr/include}"
CC="${HOST_CC_FOR_TOOLS:-clang-${LLVM_VERSION:-24}}"

[ -f "${CCTOOLS_INCLUDE}/foreign/mach/message.h" ] || {
    echo "build-mig.sh: no ${CCTOOLS_INCLUDE}/foreign/mach/message.h; run build-cctools.sh first or set CCTOOLS_INCLUDE" >&2
    exit 1
}

mkdir -p "$(dirname "${SRC}")" "${PREFIX}/bin" "${PREFIX}/libexec"

if [ ! -d "${SRC}" ]; then
    git clone --depth 1 --branch "${TAG}" \
        https://github.com/apple-oss-distributions/bootstrap_cmds.git "${SRC}"
fi

cd "${SRC}/migcom.tproj"

# The Xcode project runs yacc/lex itself; do the same by hand. -y/-d so the
# generated header is y.tab.h, which is the name lexxer.l #includes.
bison -y -d parser.y
flex -o lexxer.c lexxer.l

# handler.c is dead Camelot-era code the Xcode target does not compile: it
# redeclares WriteIncludes and references an undefined IsCamelot and fields
# that no longer exist on struct ipc_type.
SOURCES="error.c global.c header.c lexxer.c y.tab.c routine.c
         server.c statement.c string.c type.c user.c utils.c mig.c"

# migcom.tproj has no config.h; the Xcode project passes MIG_VERSION on the
# command line. The <mach/*.h> includes are satisfied from cctools-port's
# include/foreign, its Linux copy of the SDK headers cctools needs. That
# directory also carries <strings.h>, <stdio.h>, <unistd.h>... lookalikes that
# clash with glibc's, so it goes in with -idirafter: glibc wins every name it
# has, and only mach/, libkern/, sys/_types.h and friends come from foreign.
# type.h includes <linux/types.h>, which has no u_int, under `#ifdef linux`,
# a macro clang predefines on Linux; -Ulinux sends it down the macOS branch,
# <sys/types.h>. Clang knows __private_extern__ on every target.
#
# foreign/mach/machine/*.h pick their arch headers by __x86_64__ or __arm64__.
# Clang on arm64 Linux defines __aarch64__ but not Apple's __arm64__, so name it.
HOST_ARCH_DEFS=()
[[ "$(uname -m)" == aarch64 ]] && HOST_ARCH_DEFS=(-D__arm64__=1)
# shellcheck disable=SC2086 # SOURCES is a deliberate word list
"${CC}" "${HOST_ARCH_DEFS[@]}" -Ulinux \
    -DMIG_VERSION='"'"${TAG}"'"' \
    -idirafter "${CCTOOLS_INCLUDE}/foreign" \
    -o "${PREFIX}/libexec/migcom" ${SOURCES}

# The mig driver locates migcom relative to itself, so it is copied as is.
install -m0755 "${SRC}/migcom.tproj/mig.sh" "${PREFIX}/bin/mig"

"${PREFIX}/libexec/migcom" -version 2>/dev/null || true
echo "mig installed: ${PREFIX}/bin/mig  migcom: ${PREFIX}/libexec/migcom"
