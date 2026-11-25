#!/bin/bash
# base/darwin/toolchain/build-dyld-app-cache-util.sh
#
# Build Apple's open-source kernel collection builder (`dyld_app_cache_util`
# from apple-oss-distributions/dyld) on **Linux**, with clang, no Xcode and no
# Mac.  base/darwin/scripts/bench-kc-build drives the binary.
#
#   base/darwin/toolchain/build-dyld-app-cache-util.sh [workdir]
#
# workdir defaults to $KCB_WORK or ./out/dyld-app-cache-util (gitignored).  It ends up
# holding two shallow checkouts (dyld, swift-corelibs-foundation), the object
# files, libCoreFoundationMin.a and the binary at <workdir>/dyld_app_cache_util.
# Idempotent: re-running reuses the checkouts and only recompiles.
#
# Requires (Ubuntu, e.g. the hwiwonlee/darwin.base image):
#   clang-${LLVM_VERSION} (default 24; or $CC/$CXX), git, and these packages --
#     libc++-${LLVM_VERSION}-dev libc++abi-${LLVM_VERSION}-dev
#     libicu-dev libssl-dev uuid-dev
#   swift-corelibs-libdispatch with its BlocksRuntime in /usr/local
#   (build-cctools.sh installs it),
#   plus the Darwin Mach-O headers: either the macOS SDK $SDKROOT names (e.g.
#   the CLT's MacOSX<version>.sdk), or an xnu tree $XNU_SRC for its EXTERNAL_HEADERS.
#
# The sources are APSL-2.0 (dyld) and Apache-2.0 (swift-corelibs-foundation);
# both are cloned here and neither is vendored; the shims and patches are ours.
# The binary is ours to keep; a KC it produces embeds Apple's kexts and must
# stay local.
#
# Its inputs besides the two checkouts: the stand-ins in shims/dyld/ and
# shims/swift-corelibs-foundation/ next to this script, and the patches in
# base/darwin/patches/dyld/ and patches/swift-corelibs-foundation/.  The
# translation units it compiles are SOURCES in step 5.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "${HERE}/../../.." && pwd)"
PATCHES="${HERE}/../patches"

DYLD_REPO="${DYLD_REPO:-https://github.com/apple-oss-distributions/dyld.git}"
DYLD_TAG="${DYLD_TAG:-dyld-1378}"
SCF_REPO="${SCF_REPO:-https://github.com/swiftlang/swift-corelibs-foundation.git}"
SCF_TAG="${SCF_TAG:-swift-6.4.0-RELEASE}"

LLVM_VERSION="${LLVM_VERSION:-24}"
CC_BIN="${CC:-clang-${LLVM_VERSION}}"
CXX_BIN="${CXX:-clang++-${LLVM_VERSION}}"
JOBS="${JOBS:-$(nproc)}"

WORK="${KCB_WORK:-${REPO}/out/dyld-app-cache-util}"
case "${1:-}" in ""|--compile-one|--compile-cf) ;; *) WORK="$1" ;; esac

SRC="${WORK}/dyld"
SCF="${WORK}/scf"
CFS="${SCF}/Sources/CoreFoundation"
OBJ="${WORK}/obj"
CFOBJ="${WORK}/cfobj"
CFINC="${WORK}/cf-include"     # CoreFoundation/ -> swift-corelibs' flat include/
DYLD_SHIM="${HERE}/shims/dyld"                  # what dyld's sources lack on Linux
CF_SHIM="${HERE}/shims/swift-corelibs-foundation" # what CoreFoundation lacks without Swift
CFLIB="${WORK}/libCoreFoundationMin.a"

die()  { echo "build-dyld-app-cache-util.sh: error: $*" >&2; exit 1; }
note() { echo "build-dyld-app-cache-util.sh: $*"; }

# ---- the two compile commands, shared with the --compile-* re-entry points ---
# -DBUILDING_CACHE_BUILDER / -DBUILDING_APP_CACHE_UTIL come from
#   configs/libKernelCollectionBuilder.xcconfig.
# -DSUPPORT_ARCH_arm64e / arm64_32 come from Apple's internal AppleFeatures.h.
# -DPAGE_SIZE only sizes an internal Diagnostics buffer (common/Array.h's
#   round_page); 16384 matches the arm64 Mac the reference KCs came from.
# -stdlib=libc++ is not optional: common/CString.h names std::__1 explicitly.
# -Wno-everything is not cosmetic: CoreFoundation's ForSwiftFoundationOnly.h
#   has a narrowing conversion clang reports as an error by default.
# <variant> and <algorithm> stand in for headers the sources get transitively
#   from Apple's internal libc++ module map; kcb-prefix.h is the Linux extra.
dyld_flags() {
    echo -n "-std=c++23 -stdlib=libc++ -fblocks"
    echo -n " -DBUILDING_CACHE_BUILDER=1 -DBUILDING_APP_CACHE_UTIL=1"
    echo -n " -DSUPPORT_ARCH_arm64e=1 -DSUPPORT_ARCH_arm64_32=1 -DPAGE_SIZE=16384"
    # Architecture::current() and the graded-arch tables key on __arm64__ or
    # __x86_64__; clang on arm64 Linux defines only __aarch64__.
    [[ "$(uname -m)" == aarch64 ]] && echo -n " -D__arm64__"
    echo -n " -I${DYLD_SHIM} -I${CFINC} -I${SRC}/dyld -I${SRC}/common"
    echo -n " -I${SRC}/mach_o -I${SRC}/lsl -I${SRC}/include -I${SRC}/include/mach-o"
    echo -n " -I${SRC}/cache_builder -I${SRC}/other-tools"
    # The Mach-O, byte-order and cpu-type definitions (mach-o/{fat,loader,nlist,
    # reloc,stab}.h, mach-o/x86_64/reloc.h, architecture/byte_order.h,
    # mach/machine.h) come straight from the SDK or xnu.  -idirafter puts them
    # behind glibc, the shims and dyld's own include/, so only what none of
    # those has falls through to Darwin's copy.
    if [[ -n "${SDKROOT:-}" ]]; then
        echo -n " -idirafter ${SDKROOT}/usr/include -idirafter ${SDKROOT}/usr/include/mach-o"
    else
        echo -n " -idirafter ${XNU_SRC}/EXTERNAL_HEADERS -idirafter ${XNU_SRC}/EXTERNAL_HEADERS/mach-o"
        echo -n " -idirafter ${XNU_SRC}/osfmk"
    fi
    echo -n " -include ${DYLD_SHIM}/kcb-prefix.h"
    echo -n " -include variant -include algorithm -Wno-everything"
    # libc++ 23 no longer drags <cstdlib> in through the C++ headers; dyld's
    # lsl/Allocator.h (aligned_alloc) relies on that.
    echo -n " -include stdlib.h"
}

# CoreFoundation's own flags, from swift-corelibs-foundation's top-level
# CMakeLists ("_Foundation_common_build_flags") minus the Swift half:
# no -DDEPLOYMENT_RUNTIME_SWIFT (we are not building the Swift overlay).
# CFAvailability.h hard-defines DEPLOYMENT_RUNTIME_SWIFT=1 regardless, so the
# tree still expects a Swift runtime underneath;
# shims/swift-corelibs-foundation/cf_swift_stubs.c
# supplies the symbols that costs.
cf_flags() {
    echo -n "-fblocks -D_GNU_SOURCE -DCF_BUILDING_CF"
    echo -n " -include ${CFS}/internalInclude/CoreFoundation_Prefix.h"
    echo -n " -I${CFS}/include -I${CFS}/internalInclude"
    # CF includes <_foundation_unicode/*.h>, swift-foundation-icu's name for
    # ICU's headers; unicode.yaml maps /vfs/_foundation_unicode onto the
    # system ICU's /usr/include/unicode, whose headers do the same
    # U_ICU_ENTRY_POINT_RENAME dance.
    echo -n " -ivfsoverlay ${CF_SHIM}/unicode.yaml -I/vfs"
}

# ---- re-entry points for the parallel compiles -------------------------------
if [[ "${1:-}" == "--compile-one" ]]; then
    s="$2"
    extra=()
    # dyld_app_cache_util.cpp calls CFStringGetCStringPtr without NULL checks;
    # see shims/dyld/cfstring_compat.h.
    case "${s}" in *dyld_app_cache_util.cpp) extra=(-include "${DYLD_SHIM}/cfstring_compat.h");; esac
    exec "${CXX_BIN}" $(dyld_flags) ${extra[@]+"${extra[@]}"} \
        -c "${SRC}/${s}" -o "${OBJ}/$(echo "${s}" | tr '/' '_').o"
fi
if [[ "${1:-}" == "--compile-cf" ]]; then
    exec "${CC_BIN}" $(cf_flags) \
        -c "${CFS}/$2.c" -o "${CFOBJ}/$2.o"
fi

[[ "$(uname)" == "Linux" ]] || die "this is the Linux build"

mkdir -p "${WORK}" "${OBJ}" "${CFOBJ}"

# ---- 1. sources --------------------------------------------------------------
if [[ ! -d "${SRC}/.git" ]]; then
    note "cloning ${DYLD_REPO} at ${DYLD_TAG} (shallow, ~12 MB)"
    git clone --quiet --depth=1 --branch "${DYLD_TAG}" "${DYLD_REPO}" "${SRC}"
else
    note "reusing dyld checkout at ${SRC}"
fi

if [[ ! -d "${CFS}" ]]; then
    note "cloning ${SCF_REPO} at ${SCF_TAG} (shallow, ~20 MB) for CoreFoundation"
    git clone --quiet --depth=1 --branch "${SCF_TAG}" "${SCF_REPO}" "${SCF}"
else
    note "reusing swift-corelibs-foundation checkout at ${SCF}"
fi

# ---- 2. patches --------------------------------------------------------------
# Each patch says what it fixes in its own header or hunk comments.  Removing
# any one breaks the build or the collection:
#   0001  the CLI's kext dependency graph (arch overrides, x86_64-only kexts,
#         symbol sets): without it kexts fail to bind kernel symbols
#   0002  kmutil's __PRELINK_INFO (-codeless-bundle-id, PlugIns, -kext-variant,
#         bundle paths): bench-kc-build passes options only it adds
#   0003  LP64 integer spellings and Platform::current() on Linux: compile
#   0004  KCB_TEXT_EXEC_ORDER=kernel-first for older xnu (<= 26.3); no effect
#         when unset
# and the swift-corelibs-foundation ones:
#   0001  _CFIsSwift() always false: without it the tool segfaults
#   0002  a .kext's executable is in Contents/MacOS: without it every kext is
#         codeless and the collection holds only the kernel
git -C "${SRC}" checkout --quiet -- .
for p in "${PATCHES}"/dyld/*.patch; do
    note "applying $(basename "${p}")"
    git -C "${SRC}" apply "${p}" || die "patch $(basename "${p}") did not apply to ${DYLD_TAG}"
done

# And the CoreFoundation ones, against the swift-corelibs checkout.
git -C "${SCF}" checkout --quiet -- .
for p in "${PATCHES}"/swift-corelibs-foundation/*.patch; do
    note "applying swift-corelibs-foundation/$(basename "${p}")"
    git -C "${SCF}" apply "${p}" || die "patch swift-corelibs-foundation/$(basename "${p}") did not apply to ${SCF_TAG}"
done

# ---- 3. include tree ---------------------------------------------------------
# Darwin's headers are searched in place (dyld_flags); only check they exist.
# xnu's EXTERNAL_HEADERS is what the SDK installs at usr/include, and
# osfmk/mach/machine.h is its mach/machine.h.
if [[ -n "${SDKROOT:-}" ]]; then
    [[ -f "${SDKROOT}/usr/include/mach-o/loader.h" ]] || die "no mach-o/loader.h under SDKROOT=${SDKROOT}"
elif [[ -n "${XNU_SRC:-}" ]]; then
    [[ -f "${XNU_SRC}/EXTERNAL_HEADERS/mach-o/loader.h" && -f "${XNU_SRC}/osfmk/mach/machine.h" ]] \
        || die "XNU_SRC=${XNU_SRC} lacks EXTERNAL_HEADERS/mach-o/loader.h or osfmk/mach/machine.h"
else
    die "no Darwin headers: set SDKROOT=<macOS SDK> or XNU_SRC=<xnu tree>"
fi

# CoreFoundation headers are flat in swift-corelibs' include/; dyld includes
# them as <CoreFoundation/CFArray.h>, so give them that directory name.
mkdir -p "${CFINC}"
ln -sfn "${CFS}/include" "${CFINC}/CoreFoundation"

# ---- 4. CoreFoundation -------------------------------------------------------
# All of swift-corelibs-foundation's CoreFoundation sources, not only the
# containers and CFPropertyList: CFPropertyListCreateData writes through a CFWriteStream over allocated
# buffers (CFPropertyList.c:2925), which drags in CFStream and, through it,
# CFRunLoop.  None of that ever runs -- the write stream is synchronous and is
# never scheduled on a run loop -- but it has to link.
note "compiling CoreFoundation ($(ls "${CFS}"/*.c | wc -l) sources, -j${JOBS})"
for f in "${CFS}"/*.c; do
    basename "${f}" .c
done | KCB_WORK="${WORK}" xargs -P "${JOBS}" -n1 "${BASH_SOURCE[0]}" --compile-cf \
    || die "one or more CoreFoundation sources failed to compile"
# The Swift-runtime stubs go into the same archive: they are what this
# CoreFoundation needs underneath it, not something dyld uses.  Not with
# cf_flags: CoreFoundation_Prefix.h's Boolean clashes with the file's own.
"${CC_BIN}" -c "${CF_SHIM}/cf_swift_stubs.c" -o "${CFOBJ}/cf_swift_stubs.o"
rm -f "${CFLIB}"
ar rcs "${CFLIB}" "${CFOBJ}"/*.o
note "built ${CFLIB} ($(stat -c %s "${CFLIB}") bytes)"

# ---- 5. the collection builder ----------------------------------------------
# The translation units of apple-oss-distributions/dyld that dyld_app_cache_util
# actually needs, relative to the dyld checkout root.
#
# Derived empirically: everything under kernel-collection-builder/ compiles and
# is required, and the support set is what the linker pulled out of an archive
# built from all of common/ mach_o/ mach_o_writer/ lsl/ cache_builder/.  Nothing from
# mach_o_writer/ or lsl/ survives dead-stripping, and neither does the
# shared-cache half of common/.
SOURCES=(
    # --- the kernel collection builder proper (all of its TUs) ---
    kernel-collection-builder/AppCacheBuilder.cpp
    kernel-collection-builder/KernelAdjustDylibSegments.cpp
    kernel-collection-builder/KernelCacheBuilder.cpp
    kernel-collection-builder/KernelOptimizerBranches.cpp
    kernel-collection-builder/KernelOptimizerLinkedit.cpp
    kernel-collection-builder/MachOAppCache.cpp
    kernel-collection-builder/dyld_app_cache_util.cpp
    kernel-collection-builder/kernel_collection_builder.cpp

    # --- support: Mach-O reading / diagnostics ---
    common/ClosureFileSystemNull.cpp
    common/ClosureFileSystemPhysical.cpp
    common/Diagnostics.cpp
    common/MachOAnalyzer.cpp
    common/MachOFile.cpp
    common/MachOLayout.cpp
    common/MachOLoaded.cpp
    common/MetadataVisitor.cpp
    common/ObjCVisitor.cpp
    common/TargetPolicy.cpp
    common/Utilities.cpp
    mach_o/Architecture.cpp
    mach_o/Archive.cpp
    mach_o/Error.cpp
    mach_o/GradedArchitectures.cpp
    mach_o/LoggingStub.cpp
    mach_o/Platform.cpp
    mach_o/Policy.cpp
    mach_o/Universal.cpp
    mach_o/UnsafeHeader.cpp
    mach_o/Version32.cpp
    mach_o/Version64.cpp
    other-tools/FileUtils.cpp
    cache_builder/ASLRTracker.cpp
)

note "compiling ${#SOURCES[@]} translation units (-j${JOBS})"
printf '%s\n' "${SOURCES[@]}" \
    | KCB_WORK="${WORK}" xargs -P "${JOBS}" -n1 "${BASH_SOURCE[0]}" --compile-one \
    || die "one or more translation units failed to compile"

# The shim implementations: the _simple.h string builder, the corecrypto /
# CCDigest layer, and CommonCrypto over OpenSSL.
note "compiling shims"
"${CC_BIN}" -I"${DYLD_SHIM}" -c "${DYLD_SHIM}/simple_shim.c"       -o "${OBJ}/shim_simple.o"
"${CC_BIN}" -I"${DYLD_SHIM}" -c "${DYLD_SHIM}/ccdigest_shim.c"     -o "${OBJ}/shim_ccdigest.o"
"${CC_BIN}" -I"${DYLD_SHIM}" -c "${DYLD_SHIM}/commoncrypto_shim.c" -o "${OBJ}/shim_commoncrypto.o"

# ---- 6. link -----------------------------------------------------------------
# -L/usr/local/lib first: libdispatch.so needs the libBlocksRuntime.so
# installed next to it, and Ubuntu's libBlocksRuntime.so.0 (libblocksruntime-dev)
# would otherwise load a second blocks runtime into the process.
note "linking"
"${CXX_BIN}" -stdlib=libc++ -o "${WORK}/dyld_app_cache_util" "${OBJ}"/*.o \
    "${CFLIB}" -L/usr/local/lib -ldispatch -lBlocksRuntime -licuuc -licui18n -lcrypto

note "built ${WORK}/dyld_app_cache_util ($(stat -c %s "${WORK}/dyld_app_cache_util") bytes)"
note "next: install it as /usr/bin/dyld_app_cache_util and run base/darwin/scripts/bench-kc-build"
