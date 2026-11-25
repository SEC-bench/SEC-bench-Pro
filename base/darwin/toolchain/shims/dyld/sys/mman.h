/* base/darwin/toolchain/shims/dyld/sys/mman.h
 *
 * MAP_RESILIENT_CODESIGN asks the Darwin VM to return zero-filled pages
 * instead of killing the process when a page of a code-signed mapping fails
 * validation.  common/ClosureFileSystemPhysical.cpp maps every input file
 * with it.  Linux has no such flag and no such failure mode, so it is 0.
 */
#ifndef _KCB_SHIM_LINUX_SYS_MMAN_H
#define _KCB_SHIM_LINUX_SYS_MMAN_H
#include_next <sys/mman.h>
#ifndef MAP_RESILIENT_CODESIGN
#define MAP_RESILIENT_CODESIGN 0
#endif
#ifndef MAP_RESILIENT_MEDIA
#define MAP_RESILIENT_MEDIA 0
#endif
#endif
