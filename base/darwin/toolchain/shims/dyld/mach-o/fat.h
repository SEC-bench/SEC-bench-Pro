/* base/darwin/toolchain/shims/dyld/mach-o/fat.h
 *
 * xnu's EXTERNAL_HEADERS/mach-o/fat.h (found in place through
 * build-dyld-app-cache-util.sh's -idirafter) is the pre-64-bit-fat version: it has no FAT_MAGIC_64 / struct fat_arch_64.
 * The macOS SDK's does, and mach_o/Architecture.h declares constructors and
 * setters over fat_arch_64.  Pull in xnu's and add the 64-bit half.
 */
#ifndef _KCB_SHIM_LINUX_MACHO_FAT_H
#define _KCB_SHIM_LINUX_MACHO_FAT_H

#include_next <mach-o/fat.h>

#ifndef FAT_MAGIC_64
#define FAT_MAGIC_64 0xcafebabf
#define FAT_CIGAM_64 0xbfbafeca
struct fat_arch_64 {
    cpu_type_t    cputype;
    cpu_subtype_t cpusubtype;
    uint64_t      offset;
    uint64_t      size;
    uint32_t      align;
    uint32_t      reserved;
};
#endif

#endif
