We can use every step in [quickstart-macos.md](quickstart-macos.md) as an oracle to migrate the same pipeline to Ubuntu. This guide will follow the outline of the other one.

# Prepare the environment
1. We will use [Apt](https://wiki.debian.org/Apt) and [Snapcraft](https://snapcraft.io/) instead of [Homebrew](https://brew.sh/) as the package manager.
2. Install [LLVM](https://llvm.org) through its [apt repository](https://apt.llvm.org). This substitutes most of the [Xcode](<https://apps.apple.com/us/app/xcode/id497799835?mt=12 Xcode>).
```bash
export LLVM_VERSION=24
wget https://apt.llvm.org/llvm.sh
chmod +x llvm.sh
sudo ./llvm.sh $LLVM_VERSION all
```
3. Install [ipsw](https://blacktop.github.io/ipsw/docs/getting-started/installation) using `snap`
4. Install [Kernel Debug Kit](https://developer.apple.com/documentation/apple-silicon/debugging-a-custom-kernel-extension)(KDK) from [dortania](https://github.com/dortania)'s [Kernel Debug Kit Mirror](https://github.com/dortania/KdkSupportPkg/releases) using follwing script. Note this step is memory intensive, you should ensure there is at least 20GiB RAM or swap available, otherwise you can copy from macOS. [Apple Developer Downloads](https://developer.apple.com/download/all/) is the official source for KDK.
```bash
sudo apt install -y 7zip
TMP_KDK=$(mktemp -d ~/kdk.XXXXXXXXXX)
(
    cd $TMP_KDK &&
    ipsw download kdk &&
    7z e *.dmg && rm *.dmg &&
    ipsw pkg KernelDebugKit.pkg -p '(Payload|PackageInfo)$' &&
    for pkg in *.pkg/; do
        (
            cd "$pkg" &&
            INSTALL_LOCATION=$(grep -o 'install-location="[^"]*"' PackageInfo | cut -d'"' -f2) &&
            sudo mkdir -p "$INSTALL_LOCATION" &&
            ipsw pbzx Payload &&
            (cd "$INSTALL_LOCATION" && sudo cpio -idm) < Payload.extracted
        )
    done
)
rm -rf $TMP_KDK
```

# Prepare the VM runtime
5. Clone [darwin-vm](https://github.com/jprx/darwin-vm) and run `$ cd darwin-vm`.
6. Define the `DEVNAME` and `MACOS_VERSION` environment variable by running `$ export DEVNAME="Macmini9,1" MACOS_VERSION="26.5"`. We will override the default values and use the Macmini9,1 device and macOS version 26.5 in this example.
7. Get the files `$ export URL=$(ipsw download ipsw -d $DEVNAME -v $MACOS_VERSION -u); eval "$(bash -c 'exec 3>&1; trap "declare -p IPSW_BIN FW_DIR KERNEL_EXT CHIP_NAME >&3" EXIT; source ./get_files.sh >&2')"`. The exported environment variables will be used in the next step. The script is expected to fail at `patch_ramdisk` stage because there is no `hdiutil` on Linux; nevertheless, it will exit successfully with exit code 0.
8. Patch the ramdisk with correct permissions using a ported version of [linux-apfs](https://github.com/linux-apfs) that requires no kernel moudule. The `apfsftp` command line interface is inspired by [sftp](https://man.openbsd.org/sftp.1).
```bash
export APFSFTP="python3 ../base/darwin/scripts/apfsftp" RAMDISK=$FW_DIR/ramdisk.dmg
$APFSFTP mv    $RAMDISK /System/Library/LaunchDaemons /System/Library/LaunchDaemons.old
$APFSFTP mkdir $RAMDISK /System/Library/LaunchDaemons
$APFSFTP put   $RAMDISK launchdaemons/com.jprx.bash.plist /System/Library/LaunchDaemons/com.jprx.bash.plist 644
```
9. Rebuild the trust cache.
```bash
TC_IM4P=$(ipsw extract --remote "$URL" --output "$IPSW_BIN" --flat --pattern "$(basename "$IPSW_BIN"/*/*.dmg).trustcache" -j | jq -r '.[0] // empty')
ipsw img4 im4p extract "$TC_IM4P" -o /dev/stdout | xxd -p -s24 -c22 | cut -c1-40 >> firmware/all_hashes
./build_tc.py firmware/all_hashes firmware/ramdisk.tc
```
10. Build the [`qemu-sptm`](https://github.com/jprx/qemu-sptm).
```bash
sudo sed -i 's/^Types: deb$/Types: deb deb-src/' /etc/apt/sources.list.d/ubuntu.sources
sudo apt update && sudo apt build-dep -y --arch-only qemu
git submodule update --init
cd qemu-sptm
mkdir build
cd build
../configure --target-list=aarch64-softmmu --disable-pvg --disable-werror
make -j
cd ../..
```

# Prepare the PoC programs
11. Install SDK headers.
```bash
sudo apt install -y python3-pip
pip3 install --break-system-packages applecatalog
SDK_PID=$(python3 -m applecatalog macos list | grep "title='Command Line Tools" | tail -1 | grep -oE "[0-9]{3}-[0-9]{5}")
SDK_URL=$(python3 -m applecatalog macos info "$SDK_PID" | grep -o "[^']*/CLTools_macOSNMOS_SDK\.pkg")
TMP_SDK=$(mktemp -d ~/sdk.XXXXXXXXXX)
(
    cd $TMP_SDK &&
    curl -fsSLO "$SDK_URL" &&
    ipsw pkg CLTools_macOSNMOS_SDK.pkg -p 'Payload$' &&
    ipsw pbzx Payload &&
    (cd / && sudo cpio -idm) < Payload.extracted
)
export SDKROOT=$(cpio -it < $TMP_SDK/Payload.extracted | grep -E 'MacOSX[0-9]+\.[0-9]+\.sdk$' | sed 's/^\.//')
rm -rf $TMP_SDK
```
12. Install [ldid](https://github.com/ProcursusTeam/ldid).
```bash
sudo apt update && sudo apt install -y libplist-dev pkg-config
git clone https://github.com/ProcursusTeam/ldid
cd ldid && make -j && sudo make install && cd ..
```
13. We will use the PoC programs from [vschko](https://github.com/vschko) by cloning [CaseStudies](https://github.com/vschko/CaseStudies).
14. Build the PoCs `$ bash -c 'cd CaseStudies/CVE-2026-39868 && clang-$LLVM_VERSION -target arm64-apple-darwin -isysroot "$SDKROOT" -fuse-ld=lld -o ennofs enoffs.c && clang-$LLVM_VERSION -target arm64-apple-darwin -isysroot "$SDKROOT" -fuse-ld=lld -o offs offs.c'`. Since this is a cross build, you cannot run the produced PoC binaries on your host.
15. Copy the PoCs into the ramdisk `$ $APFSFTP put $RAMDISK CaseStudies/CVE-2026-39868/ennofs /bin/ennofs && $APFSFTP put $RAMDISK CaseStudies/CVE-2026-39868/offs /bin/offs`.
16. Add those binaries' Code Directory Hash(CDHash) to the hash list `$ bash -c 'cd CaseStudies/CVE-2026-39868 && ldid -h ennofs offs' | grep -i cdhash= | cut -d= -f2 >> firmware/all_hashes`.
17. Rebuild the trustcache with the updated hash list. `$ ./build_tc.py firmware/all_hashes firmware/ramdisk.tc`
18. Verify the PoCs can be triggered in the VM by starting the VM. Run `$ ./run.sh` then in the VM terminal, run `ennofs` or `offs`, the kernel should panic. Exit QEMU by sending `Ctrl+A` + `x`.

# Build and link the kernel from source
A lot of tools need to be built by ourselves to port the [Command Line Tools](https://developer.apple.com/documentation/xcode/command-line-tools)(CLT).

19. Install `libclang_rt.cc_kext.a` into the same location as if installed by the CLT.
```bash
CLT_URL=$(python3 -m applecatalog macos info "$SDK_PID" | grep -o "[^']*/CLTools_Executables[^']*\.pkg")
TMP_CLT=$(mktemp -d ~/clt.XXXXXXXXXX)
(
    cd $TMP_CLT &&
    curl -fsSLO "$CLT_URL" &&
    ipsw pkg CLTools_Executables*.pkg -p 'Payload$' &&
    ipsw pbzx Payload &&
    (cd / && sudo cpio -idm '*libclang_rt.cc_kext.a') < Payload.extracted
    sudo chown -R "$USER" /Library/Developer/CommandLineTools
)
rm -rf $TMP_CLT
```
20. Replace the `clang`, `lld`, and `llvm-ar` with the source patched version that has `__builtin_xnu_type*` symbols.
```bash
sudo apt install -y cmake
git clone https://github.com/llvm/llvm-project
cd llvm-project
git checkout -q 58c46bae21181fb4240cf964461bea738d96d50e
git apply ../../base/darwin/patches/llvm/xnu-builtin-type.patch
cmake -G Ninja -S llvm -B build -DCMAKE_BUILD_TYPE=Release \
    -DLLVM_ENABLE_PROJECTS="clang;lld" -DLLVM_TARGETS_TO_BUILD="AArch64;host" \
    -DCMAKE_C_COMPILER=clang-$LLVM_VERSION -DCMAKE_CXX_COMPILER=clang++-$LLVM_VERSION
ninja -C build clang lld llvm-ar
sudo ninja -C build install-clang install-clang-resource-headers install-lld install-llvm-ar
cd ..
```
21. Install [libdispatch](https://github.com/apple-oss-distributions/libdispatch) by using its Swift port [swift-corelibs-libdispatch](https://github.com/swiftlang/swift-corelibs-libdispatch), which is required to build [cctools](https://github.com/apple-oss-distributions/cctools).
```bash
git clone https://github.com/swiftlang/swift-corelibs-libdispatch
cd swift-corelibs-libdispatch
cmake -G Ninja -S . -B build \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_C_FLAGS="-Wno-error=unused-but-set-global" \
    -DCMAKE_C_COMPILER=clang-$LLVM_VERSION -DCMAKE_CXX_COMPILER=clang++-$LLVM_VERSION
ninja -C build
sudo ninja -C build install
sudo ldconfig
cd ..
```
22. Install [cctools](https://github.com/apple-oss-distributions/cctools) by using [cctools-port](https://github.com/tpoechtrager/cctools-port). These tools will be installed to the same location as the CLT installs them. Additionally we install cctools' headers, `libmacho.a`, and `libstuff.a`.
```bash
export CLT_PREFIX=/Library/Developer/CommandLineTools/usr
export SDK_PREFIX=/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/usr
git clone https://github.com/tpoechtrager/cctools-port
cd cctools-port/cctools
CC=clang-$LLVM_VERSION CXX=clang++-$LLVM_VERSION ./configure \
    --prefix=$CLT_PREFIX \
    --target=arm64-apple-darwin \
    --program-prefix= \
    --disable-lto-support
make -j PROGRAM_PREFIX=
make install PROGRAM_PREFIX=
mkdir -p $SDK_PREFIX/include
cp -R include/. $SDK_PREFIX/include/
sudo cp libmacho/.libs/libmacho.a libstuff/.libs/libstuff.a /usr/lib/
cd ../..
```
23. Install `mig` and `migcom` from [bootstrap_cmds](https://github.com/apple-oss-distributions/bootstrap_cmds) as if it is provided by CLT.
```bash
git clone https://github.com/apple-oss-distributions/bootstrap_cmds
cd bootstrap_cmds/migcom.tproj
MIG_VERSION=$(git describe --tags)
bison -y -d parser.y
flex -o lexxer.c lexxer.l
mkdir -p $CLT_PREFIX/libexec
clang-$LLVM_VERSION -Ulinux $([ "$(uname -m)" = aarch64 ] && echo -D__arm64__=1) \
    -DMIG_VERSION="\"$MIG_VERSION\"" -idirafter $SDK_PREFIX/include/foreign \
    -o $CLT_PREFIX/libexec/migcom \
    error.c global.c header.c lexxer.c y.tab.c routine.c server.c statement.c string.c type.c user.c utils.c mig.c
install -m0755 mig.sh $CLT_PREFIX/bin/mig
cd ../..
```
24. Install the [IOKit interface generator](https://developer.apple.com/documentation/driverkit/creating-a-driver-using-the-driverkit-sdk)(`iig`) by using [iig-port](https://github.com/Nyktis/iig-port) with patches. It is installed to the same location as Xcode installs `iig`.
```bash
XCTOOLCHAIN_PREFIX=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr
sudo mkdir -p "$XCTOOLCHAIN_PREFIX/bin"
sudo chown -R "$USER" /Applications/Xcode.app
git clone https://github.com/Nyktis/iig-port
cd iig-port
git apply ../../base/darwin/patches/iig-port/default-darwin-target.patch
clang++-$LLVM_VERSION -std=c++17 $(llvm-config-$LLVM_VERSION --cxxflags --ldflags) iig.cpp -lclang \
    -o "$XCTOOLCHAIN_PREFIX/bin/iig"
cd ..
```
25. Install the shims required by XNU's [MakeInc.cmd](https://github.com/apple-oss-distributions/xnu/blob/main/makedefs/MakeInc.cmd). `xcrun`, `plutil`, and `codesign` in `/usr/bin`; `install`, `gm4`, `clang`, `clang++`, and `cc` in `$CLT_PREFIX/bin`.
```bash
sudo install -m0755 ../base/darwin/toolchain/shims/usr-bin/* /usr/bin/
install -m0755 ../base/darwin/toolchain/shims/clt-bin/* $CLT_PREFIX/bin/
```
26. Install CoreFoundation by using its Swift port [swift-corelibs-foundation](https://github.com/swiftlang/swift-corelibs-foundation) with patches, which is required to build (`dyld_app_cache_util`)[https://github.com/apple-oss-distributions/dyld/blob/main/kernel-collection-builder/dyld_app_cache_util.cpp].
```bash
CF_SHIM=$PWD/../base/darwin/toolchain/shims/swift-corelibs-foundation
git clone https://github.com/swiftlang/swift-corelibs-foundation
cd swift-corelibs-foundation
git apply ../../base/darwin/patches/swift-corelibs-foundation/*.patch
cd Sources/CoreFoundation
clang-$LLVM_VERSION -c $CF_SHIM/cf_swift_stubs.c
clang-$LLVM_VERSION -fblocks -D_GNU_SOURCE -DCF_BUILDING_CF -include internalInclude/CoreFoundation_Prefix.h \
    -Iinclude -IinternalInclude -ivfsoverlay $CF_SHIM/unicode.yaml -I/vfs \
    --emit-static-lib -o libCoreFoundation.a *.c cf_swift_stubs.o
sudo install -m0644 libCoreFoundation.a /usr/local/lib/
sudo install -D -m0644 -t /usr/local/include/CoreFoundation include/*.h
cd ../../..
```
27. Install (`dyld_app_cache_util`)[https://github.com/apple-oss-distributions/dyld/blob/main/kernel-collection-builder/dyld_app_cache_util.cpp], the core utility of kernel collection(KC) builder.
```bash
DYLD_SHIM=$PWD/../base/darwin/toolchain/shims/dyld
git clone https://github.com/apple-oss-distributions/dyld
cd dyld
git apply ../../base/darwin/patches/dyld/*.patch
clang-$LLVM_VERSION -I$DYLD_SHIM -c $DYLD_SHIM/{simple_shim,ccdigest_shim,commoncrypto_shim}.c
clang++-$LLVM_VERSION -std=c++23 -stdlib=libc++ -fblocks -Wno-everything \
    $([ "$(uname -m)" = aarch64 ] && echo -D__arm64__) \
    -DBUILDING_CACHE_BUILDER=1 -DBUILDING_APP_CACHE_UTIL=1 \
    -DSUPPORT_ARCH_arm64e=1 -DSUPPORT_ARCH_arm64_32=1 -DPAGE_SIZE=16384 \
    -I$DYLD_SHIM -Idyld -Icommon -Imach_o -Ilsl -Iinclude -Iinclude/mach-o -Icache_builder -Iother-tools \
    -idirafter $SDKROOT/usr/include -idirafter $SDKROOT/usr/include/mach-o \
    -include $DYLD_SHIM/kcb-prefix.h -include $DYLD_SHIM/cfstring_compat.h -include stdlib.h -include variant -include algorithm \
    -o dyld_app_cache_util \
    kernel-collection-builder/*.cpp \
    common/{ClosureFileSystemNull,ClosureFileSystemPhysical,Diagnostics,MachOAnalyzer,MachOFile,MachOLayout,MachOLoaded,MetadataVisitor,ObjCVisitor,TargetPolicy,Utilities}.cpp \
    mach_o/{Architecture,Archive,Error,GradedArchitectures,LoggingStub,Platform,Policy,Universal,UnsafeHeader,Version32,Version64}.cpp \
    other-tools/FileUtils.cpp cache_builder/ASLRTracker.cpp *.o \
    -L/usr/local/lib -lCoreFoundation -ldispatch -lBlocksRuntime -licuuc -licui18n -lcrypto
sudo install -m0755 dyld_app_cache_util /usr/bin/
cd ..
```
28. Clone (XNU)[https://github.com/apple-oss-distributions/xnu] and apply patches.
```bash
cd xnu
git apply - <<'EOF'
diff --git a/pexpert/pexpert/arm64/board_config.h b/pexpert/pexpert/arm64/board_config.h
index 5a6cd3368..6d436b809 100644
--- a/pexpert/pexpert/arm64/board_config.h
+++ b/pexpert/pexpert/arm64/board_config.h
@@ -319,2 +319,4 @@
 #endif  /* ARM64_BOARD_CONFIG_VMAPPLE */
+#undef  BTI_ENFORCED
+#define BTI_ENFORCED 0
 
EOF
git apply - <<'EOF'
diff --git a/osfmk/vm/vm_sanitize.c b/osfmk/vm/vm_sanitize.c
--- a/osfmk/vm/vm_sanitize.c
+++ b/osfmk/vm/vm_sanitize.c
@@ -631,16 +631,6 @@
 		*size = vm_sub_no_ubsan(end_aligned, addr_aligned);
 	}

 	if (flags & VM_SANITIZE_FLAGS_CHECK_ADDR_RANGE) {
-#if defined(__arm64__) && MACH_ASSERT && !__BUILDING_XNU_LIBRARY__
-		/*
-		 * Make sure that this fails noisily if someone adds support for large
-		 * VA extensions. With such extensions, this code will have to check
-		 * ID_AA64MMFR2_EL1 to get the actual max VA size for the system,
-		 * instead of assuming it is 48 bits.
-		 * This is excluded from unit-test build due to being EL1 only instruction
-		 */
-		assert((__builtin_arm_rsr64("ID_AA64MMFR2_EL1") & ID_AA64MMFR2_EL1_VARANGE_MASK) == 0);
-#endif /* defined(__arm64__) && MACH_ASSERT && !__BUILDING_XNU_LIBRARY__ */
 		const uint64_t max_va_bits = 48;
 		const mach_vm_offset_t va_range_upper_bound = (1ULL << max_va_bits);
 		const mach_vm_offset_t va_mask = va_range_upper_bound - 1;
EOF
cd ..
```
29. Build the kernel and the KC with the `--kc` flag. The script is ported from [darwin-xnu-build](https://github.com/blacktop/darwin-xnu-build).
```bash
sudo apt install -y tcsh unifdef libbsd-dev
export KERNEL_CONFIG=DEVELOPMENT
../base/darwin/scripts/linux-xnu-build --kc
```
30. Copy the KC to `firmware/` of `darwin-vm`.
```bash
cp fakeroot/oss-xnu.macOS.$MACOS_VERSION.kc.$CHIP_NAME firmware/bootkc
```
31. Boot by running `$ ./run.sh` then in the VM terminal, run `ennofs` or `offs`, the kernel should panic. Exit QEMU by sending `Ctrl+A` + `x`.
32. Add the patch that fixes CVE-2026-39868 in xnu directory.
```bash
cd xnu
git apply - <<'EOF'
diff --git a/bsd/dev/dtrace/dtrace.c b/bsd/dev/dtrace/dtrace.c
--- a/bsd/dev/dtrace/dtrace.c
+++ b/bsd/dev/dtrace/dtrace.c
@@ -15719,6 +15719,18 @@ dtrace_helper_provider_validate(dof_hdr_t *dof, dof_sec_t *sec)
 		return (-1);
 	}
 
+	if (enoff_sec != NULL) {
+		if (enoff_sec->dofs_entsize != sizeof (uint32_t)) {
+			dtrace_dof_error(dof, "invalid entry size");
+			return (-1);
+		}
+
+		if (enoff_sec->dofs_offset & (sizeof (uint32_t) - 1)) {
+			dtrace_dof_error(dof, "misaligned section offset");
+			return (-1);
+		}
+	}
+
 	if (arg_sec->dofs_entsize != sizeof (uint8_t)) {
 		dtrace_dof_error(dof, "invalid entry size");
 		return (-1);
@@ -15755,10 +15767,9 @@ dtrace_helper_provider_validate(dof_hdr_t *dof, dof_sec_t *sec)
 		 * The offset count must not wrap the index, and the offsets
 		 * must also not overflow the section's data.
 		 */
-		if (probe->dofpr_offidx + probe->dofpr_noffs <
-		    probe->dofpr_offidx ||
-		    (probe->dofpr_offidx + probe->dofpr_noffs) *
-		    off_sec->dofs_entsize > off_sec->dofs_size) {
+		if (((uint64_t)probe->dofpr_offidx +
+		    (uint64_t)probe->dofpr_noffs) *
+		    (uint64_t)off_sec->dofs_entsize > off_sec->dofs_size) {
 			dtrace_dof_error(dof, "invalid probe offset");
 			return (-1);
 		}
@@ -15777,10 +15788,10 @@ dtrace_helper_provider_validate(dof_hdr_t *dof, dof_sec_t *sec)
 					    "offsets with null section");
 					return (-1);
 				}
-			} else if (probe->dofpr_enoffidx +
-			    probe->dofpr_nenoffs < probe->dofpr_enoffidx ||
-			    (probe->dofpr_enoffidx + probe->dofpr_nenoffs) *
-			    enoff_sec->dofs_entsize > enoff_sec->dofs_size) {
+			} else if (((uint64_t)probe->dofpr_enoffidx +
+			    (uint64_t)probe->dofpr_nenoffs) *
+			    (uint64_t)enoff_sec->dofs_entsize >
+			    enoff_sec->dofs_size) {
 				dtrace_dof_error(dof, "invalid is-enabled "
 				    "offset");
 				return (-1);
@@ -15796,10 +15807,9 @@ dtrace_helper_provider_validate(dof_hdr_t *dof, dof_sec_t *sec)
 			return (-1);
 		}
 
-		if (probe->dofpr_argidx + probe->dofpr_xargc <
-		    probe->dofpr_argidx ||
-		    (probe->dofpr_argidx + probe->dofpr_xargc) *
-		    arg_sec->dofs_entsize > arg_sec->dofs_size) {
+		if (((uint64_t)probe->dofpr_argidx +
+		    (uint64_t)probe->dofpr_xargc) *
+		    (uint64_t)arg_sec->dofs_entsize > arg_sec->dofs_size) {
 			dtrace_dof_error(dof, "invalid args");
 			return (-1);
 		}
EOF
```
33. Perform step 29-32, the kernel should not panic this time.