/* base/darwin/toolchain/shims/dyld/mach-o/ranlib.h
 *
 * The static-archive table-of-contents structs.  Not in xnu's
 * EXTERNAL_HEADERS (they are cctools' / the SDK's), but mach_o/Archive.cpp
 * includes the header; it only ever reads `ranlib`/`ran_off`/`ran_name`.
 * Layout matches <mach-o/ranlib.h> from the macOS SDK.
 */
#ifndef _KCB_SHIM_LINUX_RANLIB_H
#define _KCB_SHIM_LINUX_RANLIB_H
#include <stdint.h>
#define SYMDEF          "__.SYMDEF"
#define SYMDEF_SORTED   "__.SYMDEF SORTED"
#define SYMDEF_64       "__.SYMDEF_64"
#define SYMDEF_64_SORTED "__.SYMDEF_64 SORTED"
struct ranlib {
    union { uint32_t ran_strx; } ran_un;
    uint32_t ran_off;
};
struct ranlib_64 {
    union { uint64_t ran_strx; } ran_un;
    uint64_t ran_off;
};
#endif
