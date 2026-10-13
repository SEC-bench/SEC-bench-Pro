# syntax=docker/dockerfile:1
#
# hwiwonlee/darwin.base — the one image every bench task builds FROM.
#
# qemu-sptm + darwin-vm + ipsw + ldid + apfsftp to boot a guest, the XNU
# cross toolchain and the kernel collection builder, Node and uv, in named
# stages; patches are in `base/darwin/patches/`, scripts in `base/darwin/scripts/`.
#
# Contains NO Apple material and is therefore pushable. Every Apple bit
# (IPSW, KDK, kernelcache) is fetched at task-build or run time.
#
#   build:
#     docker build -t hwiwonlee/darwin.base:latest -f base/darwin/Dockerfile base/darwin/
#
#   run (no privilege, no host modules: the ramdisk is edited in place from
#        userspace by scripts/apfsftp, never mounted):
#     docker run --rm -it \
#         -v darwin-vm-firmware:/darwin-vm/firmware \
#         hwiwonlee/darwin.base:latest
#
#   commands: boot (default) | prep | check | shell
#
#   check is a non-interactive regression run for one DEVNAME/URL - it preps,
#   boots once, and reports whether the kernel reached launchd and whether a
#   guest shell appeared. Exit 0 = shell, 2 = kernel only, 3 = panic/timeout.
#
# HOST REQUIREMENT: none beyond docker. The ramdisk is edited from userspace
# (scripts/apfsftp), so no --privileged, no /lib/modules and no apfs.ko - the
# image is kernel-independent. The HFSX ramdisks of macOS <= 13.2.1 are not
# yet handled by apfsftp.
#
# macOS guests boot the IPSW's own kernelcache (the ipsw-stock variant) or a
# collection relinked from a KDK by bench-kc-build (kdk-*, custom-*).
#
# Exit qemu with ctrl-a x. Some boots panic during bringup (an emulator
# limitation); the entrypoint detects that and restarts qemu, up to
# $BOOT_RETRIES times.

# The image builds nothing against the host kernel, so its Ubuntu
# release is a free choice; pass --build-arg BASE_IMAGE=ubuntu:24.04 for 24.04.
ARG BASE_IMAGE=ubuntu:26.04
# Declared globally so both the toolchain stage and the runtime's smoke test
# see the same value. apt.llvm.org serves the version it builds from main as
# llvm-toolchain-<codename> with no -<version> suffix (llvm.sh's
# LLVM_VERSION_PATTERNS), so the apt source lines fall back to that suite.
ARG LLVM_VERSION=24

# ---------------------------------------------------------------------------
# apt: the common package layer every other stage builds on.
#
# Build and runtime packages are in one list because task builds compile XNU
# *in* the final image, so the base is not slim.
# ---------------------------------------------------------------------------
FROM ${BASE_IMAGE} AS apt

ENV DEBIAN_FRONTEND=noninteractive

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        bash coreutils util-linux kmod sudo procps file \
        build-essential git patch pkg-config \
        ninja-build flex bison \
        python3 python3-pip python3-venv python3-setuptools python3-dev \
        libglib2.0-dev libpixman-1-dev zlib1g-dev \
        libplist-dev libssl-dev \
        jq xz-utils bzip2 cpio rsync socat \
        curl wget ca-certificates gnupg lsb-release; \
    # `7z` for the KDK DMG (bench-fetch-kdk): the package is `7zip` on newer
    # Ubuntu releases and `p7zip-full` on older ones; both install /usr/bin/7z.
    apt-get install -y --no-install-recommends 7zip \
        || apt-get install -y --no-install-recommends p7zip-full; \
    7z i >/dev/null; \
    rm -rf /var/lib/apt/lists/*; \
    pip3 install --break-system-packages --no-cache-dir "meson>=1.5"

ENV PATH=/usr/local/bin:$PATH

# ---------------------------------------------------------------------------
# download-ipsw: ipsw
#
# ipsw extracts kernelcache/SPTM/TXM/DeviceTree/ramdisk straight out of a
# remote IPSW without downloading the whole thing, and doubles as the KC/kext
# inspector (`ipsw kernel kexts`, `ipsw macho info`). The pinned GitHub
# release binary (static, so it runs on any base): no Go toolchain in the
# build or the image. FROM alpine rather than FROM apt so that a change to the
# apt layer does not invalidate this stage, and bumping IPSW_VERSION rebuilds
# only this stage and the runtime layers from its COPY on.
# The sha256 pins are the release's checksums.txt lines for the two tarballs.
# ---------------------------------------------------------------------------
FROM alpine:3.23.6 AS download-ipsw
RUN apk add --no-cache binutils  # Provides 'strip' for shrinking binaries

ARG IPSW_VERSION=3.1.724
ARG IPSW_SHA256_X86_64=08ee1747286c2fb26591a568073735c04e9564ca37476c38a7cc69d0d4783dc2
ARG IPSW_SHA256_ARM64=f9dd06d0c5381bc3d245d8fb73f58ea36195ab1eb0af0e10b34b24642d835023

RUN set -eux; \
    mkdir -p /out/bin; \
    case "$(uname -m)" in \
        x86_64) IPSWARCH=x86_64; IPSWSHA="${IPSW_SHA256_X86_64}" ;; \
        aarch64) IPSWARCH=arm64; IPSWSHA="${IPSW_SHA256_ARM64}" ;; \
        *) echo "unsupported arch" >&2; exit 1 ;; \
    esac; \
    IPSW_TGZ="ipsw_${IPSW_VERSION}_linux_${IPSWARCH}.tar.gz"; \
    wget -qO "/tmp/${IPSW_TGZ}" "https://github.com/blacktop/ipsw/releases/download/v${IPSW_VERSION}/${IPSW_TGZ}"; \
    echo "${IPSWSHA}  /tmp/${IPSW_TGZ}" | sha256sum -c -; \
    tar -C /out/bin -xzf "/tmp/${IPSW_TGZ}" ipsw; \
    rm -f "/tmp/${IPSW_TGZ}"; \
    strip /out/bin/ipsw; \
    /out/bin/ipsw version

# ---------------------------------------------------------------------------
# ldid: stands in for macOS codesign. `ldid -Cadhoc -S` ad-hoc signs and
# `ldid -h` prints a CDHash= line darwin-vm's parsing accepts. The bench never
# mounts ramdisk.dmg: scripts/apfsftp edits it in place from userspace, so
# there is no apfs.ko and no APFS tooling in the image.
# ---------------------------------------------------------------------------
FROM apt AS ldid

ARG LDID_REPO=https://github.com/ProcursusTeam/ldid.git

RUN set -eux; \
    mkdir -p /out/bin; \
    git clone --depth=1 "${LDID_REPO}" /src/ldid; \
    cd /src/ldid; \
    make -j"$(nproc)"; \
    install -m0755 ldid /out/bin/ldid

# ---------------------------------------------------------------------------
# qemu: darwin-vm + qemu-sptm, patched
#
# qemu-sptm is a QEMU fork adding the "darwin" machine (a generic Apple Silicon
# device driven entirely by the guest's own DeviceTree) plus the Apple
# implementation-defined system registers, SPRR and GXF.
#
# These fixes are applied on top of the pin. They live in base/darwin/patches/
# rather than in this file so they can be diffed and reviewed on their own:
#
#  patches/darwin-vm/dt_fixup.patch
#     1. A synthetic BNCH (boot nonce hash) in /chosen/manifest-properties for
#        the pre-SPTM path (DARWIN_VM_ADD_BNCH=1 from bench_prep_dtree):
#        iOS 16-era / macOS 14.x AppleImage4 panics "failed to read boot nonce
#        hash" without one. Plus two /chosen values real iBoot fills in from the boot volume's
#        LocalPolicy, which the IPSW's DeviceTree carries only as placeholders:
#        apfs-preboot-uuid (AppleImage4 uuid_parse()s it) and asmb/lp-sip2 (the
#        "unsafe kernel text" bit that turns CTRR enforcement off). Older macOS
#        releases panic before launchd on either placeholder.
#  patches/darwin-vm/build_tc.patch
#     2. build_tc.py merges <ramdisk>.dmg.trustcache from the IPSW into the
#        hash list it is given (sorted and deduped - XNU binary-searches the
#        entries), so prep hashes only the binaries it adds and takes the
#        hashes of Apple's own from Apple's list (bench-fetch-firmware
#        fetches it as apple_ramdisk.tc).
#  patches/qemu-sptm/no_lva_varange.patch
#     3. -M darwin runs the "max" CPU, which advertises FEAT_LVA
#        (ID_AA64MMFR2_EL1.VARange = 1). XNU's DEVELOPMENT and KASAN kernels
#        assert VARange == 0 in vm_sanitize.c on every user VM call sanitized
#        with VM_SANITIZE_FLAGS_CHECK_ADDR_RANGE, which some releases reach
#        from bash's own startup, so the guest never gets a shell. No Apple
#        silicon has LVA; the bit is 0, as on an M1.
#  patches/qemu-sptm/sptm_blob_headroom.patch
#     4. A KASAN boot collection leaves no gap below the BootKC for SPTM, so
#        the blob is slid forward by whole SPTM strides instead of asserting.
#  patches/qemu-sptm/dev_kernel_tcr.patch
#     5. DEVELOPMENT and KASAN kernels assert TCR_EL1 bits the release SPTM
#        leaves clear (16-bit ASIDs, TBI1 for KASAN); qemu sets them on the
#        SPTM path.
# ---------------------------------------------------------------------------
FROM apt AS qemu

# Upstream darwin-vm with this repo's two patches below and nothing else. The
# bench runs its dt_fixup.py, silence_logs.py, build_tc.py, launchdaemons/ and
# run.sh; the firmware download and the ramdisk edits are bench-fetch-firmware
# and apfsftp, so get_files.sh (which needs a Mac for hdiutil) never runs here.
ARG DARWIN_VM_REPO=https://github.com/jprx/darwin-vm.git
ARG DARWIN_VM_REF=1c1b2c500e2192d29ef84941cd3b517024450526

# Only the qemu-sptm submodule is initialised, and non-recursively: recursing
# would drag in qemu's roms/edk2 tree (openssl, mbedtls, brotli, googletest)
# that a -M darwin build never touches. QEMU's own configure pulls the handful
# of subprojects it actually needs.
RUN set -eux; \
    mkdir -p /darwin-vm; \
    cd /darwin-vm; \
    git init -q; \
    git remote add origin "${DARWIN_VM_REPO}"; \
    git fetch -q --depth=1 origin "${DARWIN_VM_REF}"; \
    git checkout -q FETCH_HEAD; \
    git submodule update --init qemu-sptm

# qemu-sptm is patched and built first, the darwin-vm scripts only afterwards:
# the scripts do not feed the qemu build, and keeping them out of its layer
# chain means a dt_fixup/build_tc change does not rebuild qemu.
COPY patches/qemu-sptm/ /tmp/patches/qemu-sptm/

RUN set -eux; \
    cd /darwin-vm/qemu-sptm; \
    patch -p1 --batch --forward < /tmp/patches/qemu-sptm/no_lva_varange.patch; \
    patch -p1 --batch --forward < /tmp/patches/qemu-sptm/sptm_blob_headroom.patch; \
    patch -p1 --batch --forward < /tmp/patches/qemu-sptm/dev_kernel_tcr.patch; \
    grep -q "sptm_blob_off" hw/arm/xnuboot_sptm.c; \
    grep -q "darwin_vm_dev_kernel_tcr" target/arm/helper.c; \
    grep -q "ID_AA64MMFR2, VARANGE, 0" target/arm/tcg/cpu64.c

RUN set -eux; \
    cd /darwin-vm/qemu-sptm; \
    mkdir -p build; \
    cd build; \
    ../configure \
        --target-list=aarch64-softmmu \
        --prefix=/opt/qemu-sptm \
        --disable-docs \
        --disable-gtk --disable-sdl --disable-vnc --disable-curses \
        --disable-opengl --disable-spice \
        --disable-guest-agent --disable-tools; \
    make -j"$(nproc)"; \
    make install; \
    /opt/qemu-sptm/bin/qemu-system-aarch64 -M help | grep -i darwin

# Drop the qemu source/build tree, leaving run.sh's expected path as a
# symlink to the installed binary (qemu resolves its datadir from the real
# path, so it still finds /opt/qemu-sptm/share/qemu).
RUN set -eux; \
    rm -rf /darwin-vm/qemu-sptm /darwin-vm/.git; \
    mkdir -p /darwin-vm/qemu-sptm/build; \
    ln -s /opt/qemu-sptm/bin/qemu-system-aarch64 \
          /darwin-vm/qemu-sptm/build/qemu-system-aarch64

# The darwin-vm side: this repo's two fixes. .git was removed above, so these
# are plain `patch` runs.
COPY patches/darwin-vm/ /tmp/patches/darwin-vm/

RUN set -eux; \
    cd /darwin-vm; \
    test -x silence_logs.py; \
    patch -p0 --batch --forward dt_fixup.py  < /tmp/patches/darwin-vm/dt_fixup.patch; \
    patch -p0 --batch --forward build_tc.py  < /tmp/patches/darwin-vm/build_tc.patch; \
    python3 -c "import ast; ast.parse(open('dt_fixup.py').read())"; \
    python3 -c "import ast; ast.parse(open('build_tc.py').read())"; \
    grep -q "lp-sip2" dt_fixup.py; \
    grep -q "BNCH" dt_fixup.py; \
    ! grep -q "remove_child('sep')" dt_fixup.py

# ---------------------------------------------------------------------------
# llvm-xnu: upstream clang with Apple's xnu type builtins
#
# xnu's kalloc_type needs __builtin_xnu_type_{summary,signature},
# __builtin_xnu_types_compatible and __attribute__((xnu_usage_semantics)),
# which Apple never upstreamed. base/darwin/patches/llvm/xnu-builtin-type.patch adds
# them to upstream clang. This stage builds that clang, AArch64 only, and
# installs it with its resource headers into /usr/local; the CLT's clang,
# clang++ and cc (toolchain/shims/clt-bin/) are Darwin-cross wrappers that run
# it. The rest of the LLVM tools stay the apt ones.
# The rest of the base is unaffected by a change here (separate stage).
# ---------------------------------------------------------------------------
FROM apt AS llvm-xnu

ARG LLVM_VERSION
ARG LLVM_XNU_COMMIT=58c46bae21181fb4240cf964461bea738d96d50e
RUN set -eux; \
    curl -fsSL https://apt.llvm.org/llvm-snapshot.gpg.key \
        | gpg --dearmor -o /usr/share/keyrings/llvm-archive-keyring.gpg; \
    . /etc/os-release; \
    suite="llvm-toolchain-${VERSION_CODENAME}-${LLVM_VERSION}"; \
    curl -fsI "https://apt.llvm.org/${VERSION_CODENAME}/dists/${suite}/Release" >/dev/null || suite="llvm-toolchain-${VERSION_CODENAME}"; \
    echo "deb [signed-by=/usr/share/keyrings/llvm-archive-keyring.gpg] https://apt.llvm.org/${VERSION_CODENAME}/ ${suite} main" \
        > /etc/apt/sources.list.d/llvm.list; \
    apt-get update; \
    apt-get install -y --no-install-recommends "clang-${LLVM_VERSION}" cmake ninja-build python3; \
    rm -rf /var/lib/apt/lists/*
COPY patches/llvm/xnu-builtin-type.patch /tmp/
RUN set -eux; \
    mkdir -p /src/llvm-project && cd /src/llvm-project; \
    git init -q; git remote add origin https://github.com/llvm/llvm-project; \
    git fetch -q --depth 1 origin "${LLVM_XNU_COMMIT}"; git checkout -q FETCH_HEAD; \
    git apply --check /tmp/xnu-builtin-type.patch && git apply /tmp/xnu-builtin-type.patch; \
    cmake -G Ninja -S llvm -B /src/build \
        -DLLVM_ENABLE_PROJECTS=clang -DLLVM_TARGETS_TO_BUILD=AArch64 \
        -DCMAKE_BUILD_TYPE=Release -DLLVM_ENABLE_ASSERTIONS=ON \
        -DLLVM_INCLUDE_TESTS=OFF -DLLVM_INCLUDE_EXAMPLES=OFF -DLLVM_INCLUDE_BENCHMARKS=OFF \
        -DCLANG_ENABLE_STATIC_ANALYZER=OFF -DCLANG_ENABLE_ARCMT=OFF \
        -DLLVM_PARALLEL_LINK_JOBS=1 \
        -DCMAKE_C_COMPILER="clang-${LLVM_VERSION}" -DCMAKE_CXX_COMPILER="clang++-${LLVM_VERSION}" \
        -DCMAKE_INSTALL_PREFIX=/usr/local; \
    ninja -C /src/build -j"$(nproc)" install-clang install-clang-resource-headers; \
    printf '#if __has_builtin(__builtin_xnu_type_summary)\nok\n#endif\n' | /usr/local/bin/clang -target arm64e-apple-macos26.0 -E - | grep -q '^ok$'; \
    rm -rf /src

# ---------------------------------------------------------------------------
# toolchain: the cross toolchain for compiling XNU on Linux
#
# clang/lld/llvm-* from apt.llvm.org pinned by LLVM_VERSION, the host packages
# xnu's own build tools need, then ${CLT_PREFIX}, where the Command Line Tools
# live on macOS: the patched clang, the install/gm4 shims
# (base/darwin/toolchain/shims/clt-bin/), cctools-port's ld64/libtool/nm/strip/nmedit
# plus the Darwin <mach-o/*.h> headers and libmacho/libstuff xnu's SETUP host
# tools use, and mig + migcom from bootstrap_cmds, built against those headers.
# The xcrun, plutil and codesign shims (base/darwin/toolchain/shims/usr-bin/)
# go in /usr/bin, where macOS has them and where makedefs/MakeInc.cmd
# hard-codes all three.
#
# It is a stage of its own so that a toolchain change does not invalidate the
# qemu build above.
#
# `libclang-N-dev` is here for the DriverKit interface generator. Apple's `iig`
# is closed source, but it is only a libclang AST walk plus printf templates,
# and the MIT `iig-port`, patched per base/darwin/patches/iig-port/, stands in
# for it. build-iig-port.sh installs
# it as ${XCTOOLCHAIN_PREFIX}/bin/iig, where Xcode keeps iig on a Mac and where
# the xcrun shim finds it for xnu's make. Building it
# needs libclang's headers and .so, which the runtime packages above do not
# carry.
# ---------------------------------------------------------------------------
FROM apt AS toolchain

ARG LLVM_VERSION
# Where the Command Line Tools live on macOS; every script below defaults to it.
ARG CLT_PREFIX=/Library/Developer/CommandLineTools/usr
# Where Xcode keeps iig on macOS; the CLT have none.
ARG XCTOOLCHAIN_PREFIX=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr
# bootstrap_cmds and the cctools-port revision are pinned so a rebuild is
# reproducible; both are checked out inside the two build scripts.
ARG BOOTSTRAP_CMDS_TAG=bootstrap_cmds-138
# NOT `master` (= 973.0.1-ld64-609). ld64-609 miscompiles the kernel link --
# 64-bit SUBTRACTOR differences come out short by -image_base, which corrupts
# xnu's __TEXT,__copyio_vectors table and panics the guest in
# load_init_program. build-cctools.sh also builds the libdispatch this ld64 needs.
ARG CCTOOLS_PORT_REF=1030.6.3-ld64-956.6
# Nyktis/iig-port, patched with patches/iig-port/; see build-iig-port.sh.
ARG IIG_PORT_REF=ea6d147d668ca15d490da638012243fcd705f30d

RUN set -eux; \
    curl -fsSL https://apt.llvm.org/llvm-snapshot.gpg.key \
        | gpg --dearmor -o /usr/share/keyrings/llvm-archive-keyring.gpg; \
    . /etc/os-release; \
    suite="llvm-toolchain-${VERSION_CODENAME}-${LLVM_VERSION}"; \
    curl -fsI "https://apt.llvm.org/${VERSION_CODENAME}/dists/${suite}/Release" >/dev/null || suite="llvm-toolchain-${VERSION_CODENAME}"; \
    echo "deb [signed-by=/usr/share/keyrings/llvm-archive-keyring.gpg] https://apt.llvm.org/${VERSION_CODENAME}/ ${suite} main" \
        > /etc/apt/sources.list.d/llvm.list; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        "clang-${LLVM_VERSION}" "lld-${LLVM_VERSION}" "llvm-${LLVM_VERSION}" \
        "libclang-${LLVM_VERSION}-dev"; \
    rm -rf /var/lib/apt/lists/*; \
    "clang-${LLVM_VERSION}" --version; \
    mkdir -p "${CLT_PREFIX}/bin"

# Host packages the XNU build itself reaches for:
#   tcsh      - SETUP/config/doconf is a `#!/bin/csh -f` script
#   unifdef   - the header export strips KERNEL_PRIVATE etc. out of headers
#   cmake,ninja - AvailabilityVersions builds with them (via `xcrun --find`)
#   libbsd-dev - setmode(3)/getmode(3) for SETUP/installfile
#   uuid-dev, flex, bison - kextsymboltool, mig
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        tcsh unifdef cmake ninja-build libbsd-dev uuid-dev flex bison; \
    rm -rf /var/lib/apt/lists/*

ENV PATH=/usr/lib/llvm-${LLVM_VERSION}/bin:$PATH

COPY --chmod=0755 toolchain/ /opt/darwin-bench/toolchain/

# The patched clang in /usr/local, and the shims, among them the CLT's clang,
# clang++ and cc that run it; xcrun has to return those, not the apt clang
# first on $PATH.
COPY --from=llvm-xnu /usr/local/bin/ /usr/local/bin/
COPY --from=llvm-xnu /usr/local/lib/clang/ /usr/local/lib/clang/
RUN set -eux; \
    install -m0755 /opt/darwin-bench/toolchain/shims/clt-bin/* "${CLT_PREFIX}/bin/"; \
    install -m0755 /opt/darwin-bench/toolchain/shims/usr-bin/* /usr/bin/; \
    printf '#if __has_builtin(__builtin_xnu_type_summary)\nok\n#endif\n' | /usr/local/bin/clang -target arm64e-apple-macos26.0 -E - | grep -q '^ok$'; \
    test "$(xcrun -find clang)" = "${CLT_PREFIX}/bin/clang"; \
    printf '#if __has_builtin(__builtin_xnu_type_summary)\nok\n#endif\n' | xcrun clang -E - | grep -q '^ok$'

# cctools: ld64, libtool, nm, strip, nmedit, lipo, otool, codesign_allocate,
# the <mach-o/*.h> host headers, and libmacho.a/libstuff.a in /usr/lib.
RUN set -eux; \
    /opt/darwin-bench/toolchain/build-cctools.sh "${CLT_PREFIX}" "${CCTOOLS_PORT_REF}"; \
    rm -rf /tmp/xnu-toolchain-src; \
    test -x "${CLT_PREFIX}/bin/ld"; \
    test -f /usr/lib/libmacho.a

# mig/migcom. migcom's <mach/*.h> come from the cctools-port headers the step
# above installed into /Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/usr/include,
# so it runs after cctools.
RUN set -eux; \
    /opt/darwin-bench/toolchain/build-mig.sh "${CLT_PREFIX}" "${BOOTSTRAP_CMDS_TAG}"; \
    rm -rf /tmp/xnu-toolchain-src/bootstrap_cmds; \
    test -x "${CLT_PREFIX}/libexec/migcom"

# iig-port as ${XCTOOLCHAIN_PREFIX}/bin/iig: `xcrun -find iig` resolves it and
# xnu's make generates the DriverKit headers with it.
# build-iig-port.sh applies every patch in ../patches/iig-port/ next to it.
COPY patches/iig-port/ /opt/darwin-bench/patches/iig-port/
RUN set -eux; \
    /opt/darwin-bench/toolchain/build-iig-port.sh "${XCTOOLCHAIN_PREFIX}" "${IIG_PORT_REF}"; \
    rm -rf /tmp/xnu-toolchain-src; \
    /usr/bin/xcrun -find iig

# ---------------------------------------------------------------------------
# xnu-src: XNU sources
#
# One bare clone with every tag means each task's `git worktree add` /
# `git clone --shared` is a cache hit rather than a fresh fetch.
# ---------------------------------------------------------------------------
FROM apt AS xnu-src

ARG XNU_REPO=https://github.com/apple-oss-distributions/xnu

RUN set -eux; \
    git clone --bare "${XNU_REPO}" /opt/xnu.git; \
    git -C /opt/xnu.git tag | grep -c '^xnu-'; \
    du -sh /opt/xnu.git

# The dyld-app-cache-util stage needs xnu's EXTERNAL_HEADERS (the Mach-O, byte-order and
# cpu-type structure definitions it stages rather than reinvents) and nothing
# else from xnu. Extract them here, where the bare clone already is, so that
# stage copies the headers instead of the whole repository. A separate
# instruction after the clone, so changing it leaves the clone's layer cached.
ARG XNU_HEADERS_REF=main
RUN set -eux; \
    mkdir -p /opt/xnu-headers; \
    git --git-dir=/opt/xnu.git archive "${XNU_HEADERS_REF}" \
        EXTERNAL_HEADERS osfmk/mach/machine.h | tar x -C /opt/xnu-headers; \
    test -f /opt/xnu-headers/EXTERNAL_HEADERS/mach-o/loader.h; \
    test -f /opt/xnu-headers/osfmk/mach/machine.h; \
    du -sh /opt/xnu-headers

# ---------------------------------------------------------------------------
# dyld-app-cache-util: Apple's OSS kernel collection builder
#
# `dyld_app_cache_util`, built from apple-oss-distributions/dyld dyld-1378 by
# toolchain/build-dyld-app-cache-util.sh with patches/dyld/ and
# patches/swift-corelibs-foundation/, links a boot kernel collection on Linux.
# `kmutil` has no Linux port, so this is what makes a task image able to build
# its own KC instead of importing one from a Mac.
#
# FROM toolchain rather than FROM apt: clang-${LLVM_VERSION} (from apt.llvm.org) is already
# there, and dyld does not build with libstdc++ -- common/CString.h names
# std::__1 explicitly -- so -stdlib=libc++ and the matching -dev packages are
# mandatory.
#
# The two source trees and the objects stay in this stage; only the binary is
# copied into `runtime`, as /usr/bin/dyld_app_cache_util, where macOS keeps kmutil.
# ---------------------------------------------------------------------------
FROM toolchain AS dyld-app-cache-util

ARG LLVM_VERSION

# The packages build-dyld-app-cache-util.sh needs besides what `apt` and
# `toolchain` above already carry (clang, git). libc++-dev/libc++abi-dev
# come from the apt.llvm.org list the toolchain stage configured.
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        "libc++-${LLVM_VERSION}-dev" "libc++abi-${LLVM_VERSION}-dev" \
        libicu-dev libssl-dev uuid-dev; \
    rm -rf /var/lib/apt/lists/*

# The script and its shims came with toolchain/ above.
COPY patches/dyld/ /opt/darwin-bench/patches/dyld/
COPY patches/swift-corelibs-foundation/ /opt/darwin-bench/patches/swift-corelibs-foundation/
COPY --from=xnu-src /opt/xnu-headers /opt/xnu-headers

RUN set -eux; \
    CC="clang-${LLVM_VERSION}" CXX="clang++-${LLVM_VERSION}" XNU_SRC=/opt/xnu-headers \
        /opt/darwin-bench/toolchain/build-dyld-app-cache-util.sh /tmp/dyld-app-cache-util; \
    mkdir -p /out; \
    install -m0755 /tmp/dyld-app-cache-util/dyld_app_cache_util /out/; \
    /out/dyld_app_cache_util 2>&1 | head -3; \
    rm -rf /tmp/dyld-app-cache-util

# ---------------------------------------------------------------------------
# node-uv: harness tooling
#
# Node from the official LTS tarball (the distro's is both old and entangled
# with apt), uv from the pinned GitHub release tarball rather than the
# curl|sh installer so the version is a build input.
# ---------------------------------------------------------------------------
FROM apt AS node-uv

ARG NODE_VERSION=24.20.0
ARG UV_VERSION=0.12.10

RUN set -eux; \
    mkdir -p /opt/node; \
    case "$(uname -m)" in x86_64) NODEARCH=x64 ;; aarch64) NODEARCH=arm64 ;; *) echo "unsupported arch" >&2; exit 1 ;; esac; \
    curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-${NODEARCH}.tar.xz" \
        | tar -C /opt/node --strip-components=1 -xJ; \
    rm -rf /opt/node/share/doc /opt/node/CHANGELOG.md; \
    /opt/node/bin/node --version

RUN set -eux; \
    mkdir -p /out/bin; \
    UVARCH="$(uname -m)"; \
    curl -fsSL "https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-${UVARCH}-unknown-linux-gnu.tar.gz" \
        | tar -C /out/bin --strip-components=1 -xz; \
    chmod 0755 /out/bin/uv /out/bin/uvx; \
    /out/bin/uv --version

# ---------------------------------------------------------------------------
# runtime: the tagged image
#
# FROM toolchain rather than FROM apt so that clang comes with its apt-resolved
# runtime libraries intact; everything else is copied in. Nothing above this
# line is Apple-derived, so this image is safe to push.
# ---------------------------------------------------------------------------
FROM toolchain AS runtime

COPY --from=qemu      /opt/qemu-sptm            /opt/qemu-sptm
COPY --from=qemu      /darwin-vm                /darwin-vm
COPY --from=download-ipsw /out/bin/ipsw         /usr/local/bin/ipsw
COPY --from=ldid      /out/bin/ldid             /usr/local/bin/ldid
COPY --from=xnu-src   /opt/xnu.git              /opt/xnu.git
COPY --from=node-uv   /opt/node                 /opt/node
COPY --from=node-uv   /out/bin/uv               /usr/local/bin/uv
COPY --from=node-uv   /out/bin/uvx              /usr/local/bin/uvx

ENV PATH=/opt/node/bin:/usr/local/bin:$PATH

COPY --chmod=0755 scripts/darwin-vm-entrypoint /usr/local/bin/darwin-vm-entrypoint

# ---------------------------------------------------------------------------
# the kernel collection builder
#
# dyld_app_cache_util links against libicuuc/libicui18n (through the vendored
# CoreFoundation; they pull in libicudata), libcrypto, libc++, libc++abi, and
# the libdispatch/libBlocksRuntime build-cctools.sh installed in /usr/local.
# libssl3/libuuid1 are already in the `apt` layer; libicu and libc++/libc++abi
# are what this adds. The libicu package name differs between Ubuntu
# releases, so it is resolved at build time.
#
# bench-kc-build drives the binary and does the kmutil-parity work.
# The KDK it is pointed at must be BIND-MOUNTED at its real macOS path and is
# never copied into a layer.
# ---------------------------------------------------------------------------
ARG LLVM_VERSION
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        libssl3 libuuid1 \
        "$(apt-cache search --names-only '^libicu[0-9]+$' | awk '{print $1}' | sort -V | tail -1)"; \
    # apt.llvm.org names the runtime libraries libc++1-<N>/libc++abi1-<N> for
    # some LLVM versions and plain libc++1/libc++abi1 for others; take
    # whichever the configured list has.
    apt-get install -y --no-install-recommends "libc++1-${LLVM_VERSION}" "libc++abi1-${LLVM_VERSION}" \
        || apt-get install -y --no-install-recommends libc++1 libc++abi1; \
    rm -rf /var/lib/apt/lists/*

COPY --from=dyld-app-cache-util /out/dyld_app_cache_util /usr/bin/dyld_app_cache_util
COPY --chmod=0755 scripts/bench-kc-build /usr/local/bin/bench-kc-build
# Applied to a KASAN boot collection on the SPTM path; see the script header.
COPY --chmod=0755 scripts/bench-kc-kasan-sptm-l1 /usr/local/bin/bench-kc-kasan-sptm-l1

# linux-xnu-build is the other half of the same story: it compiles and links
# the kernel a task's `custom-*` variant boots. It runs on the docker HOST, in a
# base-image container -- no task Dockerfile invokes it -- so it has to be on
# PATH in the runtime layer.
COPY --chmod=0755 scripts/linux-xnu-build /usr/local/bin/linux-xnu-build

RUN set -eux; \
    ! ldd /usr/bin/dyld_app_cache_util | grep -q 'not found'; \
    dyld_app_cache_util 2>&1 | head -1; \
    bench-kc-build --help >/dev/null

# ---------------------------------------------------------------------------
# xnu patches every linux-xnu-build checkout takes, before a task's own
# patches. disable_bti_all.patch: apple_arm64_common.h sets BTI_ENFORCED 1 for
# every SoC config (VMAPPLE.h alone overrides it to 0), and a kernel built from
# the public sources then takes an endless Branch Target Exception (ESR EC
# 0x0D) in early boot under emulation, with no console output.
# ---------------------------------------------------------------------------
COPY patches/xnu/ /opt/darwin-bench/patches/xnu/
# linux-xnu-build checks $XNU_TAG out of the bare clone and applies these first.
ENV XNU_GIT=/opt/xnu.git XNU_BASE_PATCHES=/opt/darwin-bench/patches/xnu

# Fail the build loudly rather than at boot if anything is missing a shared
# library, or if a tool the bench relies on is not actually runnable.
ARG LLVM_VERSION
RUN set -eux; \
    ! ldd /opt/qemu-sptm/bin/qemu-system-aarch64 | grep -q 'not found'; \
    ! ldd /usr/local/bin/ldid | grep -q 'not found'; \
    /opt/qemu-sptm/bin/qemu-system-aarch64 -M help | grep -qi darwin; \
    ipsw version >/dev/null; \
    ldid 2>&1 | grep -qi usage; \
    node --version; \
    uv --version; \
    "clang-${LLVM_VERSION}" --version >/dev/null; \
    test -x /usr/local/bin/darwin-vm-entrypoint; \
    test "$(git -C /opt/xnu.git tag | grep -c '^xnu-')" -gt 20

# ---------------------------------------------------------------------------
# bench helpers
#
# Deliberately after the smoke test so that editing them does not re-run it.
#
#   bench-common.sh       sourced by every task's secb.sh: task.json
#                         parsing, firmware prep, the console-socket qemu
#                         lifecycle, the BEGIN/END exec protocol, staging and
#                         trust-cache rebuilds.
#   bench-fetch-firmware  the `firmware` stage of a task Dockerfile: the part
#                         of get_files.sh that needs no privilege.
#   bench-fetch-kdk       the `kdk` stage: resolve and download a build with
#                         `ipsw download kdk`, verify it against the task's
#                         sha256 pin, and unpack the DMG with 7z + ipsw pkg +
#                         pbzx-stream.py. No Mac, no privilege.
#                         Its output layer is LOCAL ONLY.
#
# darwin-vm-entrypoint (boot|prep|check|shell) is untouched and remains the
# plain "boot an IPSW" path.
# ---------------------------------------------------------------------------
COPY --chmod=0644 scripts/bench-common.sh      /opt/darwin-bench/bench-common.sh
COPY --chmod=0755 scripts/bench-fetch-firmware /usr/local/bin/bench-fetch-firmware
COPY --chmod=0755 scripts/bench-fetch-kdk      /usr/local/bin/bench-fetch-kdk
COPY --chmod=0755 scripts/bench-fetch-xcode-tools /usr/local/bin/bench-fetch-xcode-tools
COPY --chmod=0755 scripts/pbzx-stream.py       /opt/darwin-bench/pbzx-stream.py

RUN set -eux; \
    bash -n /opt/darwin-bench/bench-common.sh; \
    bash -n /usr/local/bin/bench-fetch-firmware; \
    bash -n /usr/local/bin/bench-fetch-kdk; \
    python3 -c 'import ast; ast.parse(open("/opt/darwin-bench/pbzx-stream.py").read())'; \
    7z i >/dev/null; \
    command -v socat

# ---------------------------------------------------------------------------
# bench-cc: the guest cross-compiler (`bench compile` / `bench poc`)
#
# clang and ld64.lld are already here (the `toolchain` stage this runtime is
# FROM), which is everything needed to emit a Darwin arm64 Mach-O on Linux
# except an SDK -- and an SDK is never baked in (Apple licenses it for
# Apple-branded hardware). bench-cc compiles against one that `crash_check.sh`
# mounts at run time ($BENCH_SDK), fetched on the host with
# `bench-fetch-xcode-tools --clt --clt-for-macos <ver> --sdk`.
#
# bench-poc.sh is the `compile`/`poc` half of a task's bench.sh. It is a
# file of its own, not part of bench-common.sh, because a task image can pick
# it up from a bind-mounted repo (crash_check.sh mounts base/darwin/ at /bench/base)
# without being rebuilt against a re-tagged base image.
# ---------------------------------------------------------------------------
COPY --chmod=0755 scripts/bench-cc          /usr/local/bin/bench-cc
COPY --chmod=0755 scripts/apfsftp           /opt/darwin-bench/apfsftp
COPY --chmod=0644 scripts/bench-poc.sh      /opt/darwin-bench/bench-poc.sh

RUN set -eux; \
    bash -n /usr/local/bin/bench-cc; \
    python3 -c 'import ast; ast.parse(open("/opt/darwin-bench/apfsftp").read())'; \
    bash -n /opt/darwin-bench/bench-poc.sh; \
    command -v ld64.lld

WORKDIR /darwin-vm
VOLUME ["/darwin-vm/firmware"]
ENTRYPOINT ["/usr/local/bin/darwin-vm-entrypoint"]
CMD ["boot"]
