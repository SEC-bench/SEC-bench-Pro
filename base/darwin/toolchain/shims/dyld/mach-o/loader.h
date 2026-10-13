/* base/darwin/toolchain/shims/dyld/mach-o/loader.h
 *
 * xnu's EXTERNAL_HEADERS/mach-o/loader.h (found in place through
 * build-dyld-app-cache-util.sh's -idirafter) trails the macOS SDK's by a few constants that dyld-1378 uses.  Pull it in
 * and top it up; every value below is the macOS SDK header's.
 */
#ifndef _KCB_SHIM_LINUX_MACHO_LOADER_H
#define _KCB_SHIM_LINUX_MACHO_LOADER_H

#include_next <mach-o/loader.h>

/* build_tool_version.tool */
#ifndef TOOL_CLANG
#define TOOL_CLANG  1
#endif
#ifndef TOOL_SWIFT
#define TOOL_SWIFT  2
#endif
#ifndef TOOL_LD
#define TOOL_LD     3
#endif
#ifndef TOOL_LLD
#define TOOL_LLD    4
#endif

/* build_version_command.platform */
#ifndef PLATFORM_MACOS
#define PLATFORM_MACOS               1
#endif
#ifndef PLATFORM_IOS
#define PLATFORM_IOS                 2
#endif
#ifndef PLATFORM_TVOS
#define PLATFORM_TVOS                3
#endif
#ifndef PLATFORM_WATCHOS
#define PLATFORM_WATCHOS             4
#endif
#ifndef PLATFORM_BRIDGEOS
#define PLATFORM_BRIDGEOS            5
#endif
#ifndef PLATFORM_MACCATALYST
#define PLATFORM_MACCATALYST         6
#endif
#ifndef PLATFORM_IOSSIMULATOR
#define PLATFORM_IOSSIMULATOR        7
#endif
#ifndef PLATFORM_TVOSSIMULATOR
#define PLATFORM_TVOSSIMULATOR       8
#endif
#ifndef PLATFORM_WATCHOSSIMULATOR
#define PLATFORM_WATCHOSSIMULATOR    9
#endif
#ifndef PLATFORM_DRIVERKIT
#define PLATFORM_DRIVERKIT          10
#endif
#ifndef PLATFORM_VISIONOS
#define PLATFORM_VISIONOS           11
#endif
#ifndef PLATFORM_VISIONOSSIMULATOR
#define PLATFORM_VISIONOSSIMULATOR  12
#endif
#ifndef PLATFORM_FIRMWARE
#define PLATFORM_FIRMWARE           13
#endif
#ifndef PLATFORM_SEPOS
#define PLATFORM_SEPOS              14
#endif

#endif
