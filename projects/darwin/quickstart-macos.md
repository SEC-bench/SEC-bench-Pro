# Prepare the environment
1. Install [Xcode](<https://apps.apple.com/us/app/xcode/id497799835?mt=12 Xcode>) from Mac App Store using your Apple Account. Alternatively you can acquire a copy from [Apple Developer Downloads](https://developer.apple.com/download/all/?q=Xcode).
2. Install [Command Line Tools](https://developer.apple.com/documentation/xcode/command-line-tools)(CLT) using `$ xcode-select --install`. You can also get it from [Apple Developer Downloads](https://developer.apple.com/download/all/?q=command%20line%20tools).
3. Install [Homebrew](https://brew.sh/) by following the instruction from its website. It depends on the CLT.
4. Install [ipsw](https://blacktop.github.io/ipsw/docs/getting-started/installation) using `brew`.
5. Install [Kernel Debug Kit](https://developer.apple.com/documentation/apple-silicon/debugging-a-custom-kernel-extension)(KDK) from [dortania](https://github.com/dortania)'s [Kernel Debug Kit Mirror](https://github.com/dortania/KdkSupportPkg/releases) using `$ ipsw download kdk --install`. [Apple Developer Downloads](https://developer.apple.com/download/all/) is the official source for KDK.

# Prepare the VM runtime
6. Clone [darwin-vm](https://github.com/jprx/darwin-vm) and run `$ cd darwin-vm`.
7. Define the `DEVNAME` and `MACOS_VERSION` environment variable by running `$ export DEVNAME="Macmini9,1" MACOS_VERSION="26.5"`. We will override the default values and use the Macmini9,1 device and macOS version 26.5 in this example.
8. Apply the following patch in the `darwin-vm` project root to fix stdout redirection of `hdiutil detach` command in `get_files.sh`.
```zsh
git apply - <<'EOF'
diff --git a/get_files.sh b/get_files.sh
--- a/get_files.sh
+++ b/get_files.sh
@@ -171,3 +171,3 @@
     echo "mounted ${ramdisk} on ${livemount}"
-    trap 'hdiutil detach ${livemount}; rmdir ${livemount}' EXIT
+    trap 'hdiutil detach "${livemount}" >&2 2>&1; rmdir "${livemount}"' EXIT
 
EOF
```
9. Get the files `$ export URL=$(ipsw download ipsw -d $DEVNAME -v $MACOS_VERSION -u); eval "$(bash -c 'source ./get_files.sh >&2; declare -p KERNEL_EXT CHIP_NAME')"`. The exported environment variables will be used in the next step.
10. Fix the permissions of the files `$ ./fix_perms.sh firmware/ramdisk.dmg`.
11. Build the [`qemu-sptm`](https://github.com/jprx/qemu-sptm). If you are using system Python 3.9, you will need to patch the quotes in `dumpregs.py`, like below.
```zsh
brew update && brew install $(brew deps --include-build qemu)
pip3 install tomli
git submodule update --init
cd qemu-sptm
git apply - <<'EOF'
diff --git a/scripts/darwin/dumpregs.py b/scripts/darwin/dumpregs.py
--- a/scripts/darwin/dumpregs.py
+++ b/scripts/darwin/dumpregs.py
@@ -226,5 +226,5 @@ def dump_struct(r, is_cpustate=False, is_banked=False):
             if "_GL" in r:
-                s += f"        .fieldoffset = offsetof(CPUARMState, {(r.split("_GL")[0]+"_gl").lower()}[{el}]),\n"
+                s += f"        .fieldoffset = offsetof(CPUARMState, {(r.split('_GL')[0]+'_gl').lower()}[{el}]),\n"
             elif "_EL" in r:
-                s += f"        .fieldoffset = offsetof(CPUARMState, {(r.split("_EL")[0]+"_el").lower()}[{el}]),\n"
+                s += f"        .fieldoffset = offsetof(CPUARMState, {(r.split('_EL')[0]+'_el').lower()}[{el}]),\n"
             else:
EOF
mkdir build
cd build
../configure --target-list=aarch64-softmmu --disable-pvg --disable-werror
make -j
cd ../..
```

# Prepare the PoC programs
12. We will use the PoC programs from [vschko](https://github.com/vschko) by cloning [CaseStudies](https://github.com/vschko/CaseStudies).
13. Build the PoCs `$ bash -c 'cd CaseStudies/CVE-2026-39868 && ./build.sh'`. Do NOT run the produced PoC binaries on your host.
14. Copy the PoCs into the ramdisk.
```zsh
mkdir mnt
hdiutil attach -owners on -mountpoint mnt firmware/ramdisk.dmg
sudo cp CaseStudies/CVE-2026-39868/{ennofs,offs} mnt/bin/
hdiutil detach mnt
rmdir mnt
```
15. Add those binaries' Code Directory Hash(CDHash) to the hash list `$ bash -c 'cd CaseStudies/CVE-2026-39868 && codesign -d -vvv ennofs offs 2>&1' | grep -i cdhash= | cut -d= -f2- >> firmware/all_hashes`.
16. Rebuild the trustcache with the updated hash list. `$ ./build_tc.py firmware/all_hashes firmware/ramdisk.tc`
17. Verify the PoCs can be triggered in the VM by starting the VM. Run `$ ./run.sh` then in the VM terminal, run `ennofs` or `offs`, the kernel should panic. Exit QEMU by sending `Ctrl+A` + `x`.

# Build and link the kernel from source
18. Clone [darwin-xnu-build](https://github.com/blacktop/darwin-xnu-build) and run `$ cd darwin-xnu-build`.
19. Define the `MACHINE_CONFIG` environment variable by running `$ export MACHINE_CONFIG=$CHIP_NAME`.
20. Extend the existing patch `patches/26.0/disable_bti_vmapple.patch` to disable Branch Target Identification(BTI) for every SoC. Run this in the `darwin-xnu-build` project root:
```zsh
cat > patches/26.0/disable_bti_all.patch <<'EOF'
diff --git a/pexpert/pexpert/arm64/board_config.h b/pexpert/pexpert/arm64/board_config.h
index 5a6cd3368..6d436b809 100644
--- a/pexpert/pexpert/arm64/board_config.h
+++ b/pexpert/pexpert/arm64/board_config.h
@@ -319,2 +319,4 @@
 #endif  /* ARM64_BOARD_CONFIG_VMAPPLE */
+#undef  BTI_ENFORCED
+#define BTI_ENFORCED 0
 
EOF
```
21. Dsiable the Virtual Address Range(VARange) assertion.
```zsh
cat > patches/26.0/disable_varange_check.patch <<'EOF'
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
```
22. Build the kernel by running `$ export KERNEL_CONFIG=development; eval "$(bash -c 'source ./build.sh >&2; declare -p BUILD_DIR DSTROOT KC_VARIANT KERNEL_TYPE KDKROOT')"` in the project root. The exported environment variables will be used in the next step. We will NOT use the `--kc` flag because it failed to bind '_image4_v2_set_nonce_digest' in 'com.apple.security.Image4' due to missing symbol.
23. Instead, build the kernel collection(KC) using the following commands:
```zsh
KC_FILTER='com.apple.driver.SEPHibernation'
kmutil create -v -V $KC_VARIANT -a arm64e -n boot -s none \
    --kdk "$KDKROOT" \
    -B "${DSTROOT}/oss-xnu.macOS.${MACOS_VERSION}.kc.$(echo "$MACHINE_CONFIG" | tr '[:upper:]' '[:lower:]')" \
    -k "${BUILD_DIR}/xnu.obj/kernel.${KERNEL_TYPE}" \
    -x $(plutil -convert json "$KDKROOT/System/Library/KernelCollections/kernelcache.release.$KERNEL_EXT.manifest.plist" -o - | jq -r '.requiredIdentifiers[]' | grep -vE "$KC_FILTER" | awk '{print " -b "$1; }')
```
24. Copy the KC to `firmware/` of `darwin-vm`. `kmutil` appends `.${KC_VARIANT}` to the `-B` path for every variant except `release`.
```zsh
KC_SUFFIX=$([ "$KC_VARIANT" = release ] || echo ".$KC_VARIANT")
cp "${DSTROOT}/oss-xnu.macOS.${MACOS_VERSION}.kc.$(echo "$MACHINE_CONFIG" | tr '[:upper:]' '[:lower:]')${KC_SUFFIX}" ../firmware/bootkc
```
25. Boot the VM from the `darwin-vm` project root by running `$ cd .. && ./run.sh` then in the VM terminal, run `ennofs` or `offs`, the kernel should panic. Exit QEMU by sending `Ctrl+A` + `x`.
26. Add the patch that fixes CVE-2026-39868 in darwin-xnu-build directory.
```zsh
cat > patches/26.0/CVE-2026-39868.patch <<'EOF'
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
27. `build.sh` skips compiling when `build/xnu.obj/kernel.${KERNEL_TYPE}` already exists, so before performing an incremental build after a patch change, run `$ rm -rf build/xnu.obj/kernel.${KERNEL_TYPE}`.
28. Perform step 23-25, the kernel should not panic this time.
