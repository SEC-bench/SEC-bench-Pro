/* base/darwin/toolchain/shims/dyld/TargetConditionals.h
 *
 * Apple's <TargetConditionals.h> for a Linux host build.  dyld's
 * common/Defines.h includes it unconditionally and then tests TARGET_OS_*.
 *
 * The host really is Linux and this header says so.  That matters more for
 * CoreFoundation than for dyld: swift-corelibs-foundation's *public* headers
 * (CFBase.h, CFByteOrder.h, CFLocking.h, ForSwiftFoundationOnly.h) branch on
 * TARGET_OS_MAC/TARGET_OS_LINUX, and the KC builder's translation units must
 * see exactly the same declarations that the CoreFoundation objects in
 * libCoreFoundation.a were compiled against.  Claiming to be macOS here
 * would silently give the two halves different structs.
 *
 * dyld itself is indifferent: BUILDING_CACHE_BUILDER already selects the
 * offline-host-tool paths, and none of the translation units the KC builder
 * compiles tests TARGET_OS_MAC or TARGET_OS_OSX.
 */
#ifndef _KCB_SHIM_TARGETCONDITIONALS_H
#define _KCB_SHIM_TARGETCONDITIONALS_H

#define TARGET_OS_MAC               0
#define TARGET_OS_OSX               0
#define TARGET_OS_IPHONE            0
#define TARGET_OS_IOS               0
#define TARGET_OS_WATCH             0
#define TARGET_OS_TV                0
#define TARGET_OS_VISION            0
#define TARGET_OS_BRIDGE            0
#define TARGET_OS_MACCATALYST       0
#define TARGET_OS_UIKITFORMAC       0
#define TARGET_OS_SIMULATOR         0
#define TARGET_OS_EMBEDDED          0
#define TARGET_OS_DRIVERKIT         0
#define TARGET_OS_EXCLAVEKIT        0
#define TARGET_OS_EXCLAVECORE       0
#define TARGET_OS_WIN32             0
#define TARGET_OS_WINDOWS           0
#define TARGET_OS_UNIX              1
#define TARGET_OS_LINUX             1
#define TARGET_OS_BSD               0
#define TARGET_OS_WASI              0
#define TARGET_IPHONE_SIMULATOR     0

#if defined(__x86_64__)
  #define TARGET_CPU_X86            0
  #define TARGET_CPU_X86_64         1
  #define TARGET_CPU_ARM            0
  #define TARGET_CPU_ARM64          0
#elif defined(__aarch64__)
  #define TARGET_CPU_X86            0
  #define TARGET_CPU_X86_64         0
  #define TARGET_CPU_ARM            0
  #define TARGET_CPU_ARM64          1
#else
  #define TARGET_CPU_X86            0
  #define TARGET_CPU_X86_64         0
  #define TARGET_CPU_ARM            0
  #define TARGET_CPU_ARM64          0
#endif
#define TARGET_CPU_PPC              0
#define TARGET_CPU_PPC64            0
#define TARGET_CPU_MIPS             0
#define TARGET_CPU_SPARC            0
#define TARGET_CPU_ALPHA            0
#define TARGET_RT_MAC_CFM           0
#define TARGET_RT_MAC_MACHO         0
#define TARGET_RT_LITTLE_ENDIAN     1
#define TARGET_RT_BIG_ENDIAN        0
#define TARGET_RT_64_BIT            1

#endif /* _KCB_SHIM_TARGETCONDITIONALS_H */
