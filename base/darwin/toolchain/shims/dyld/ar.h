/* base/darwin/toolchain/shims/dyld/ar.h
 *
 * mach_o/Archive.cpp tests AR_EFMT1, the "#1/<len>" long-name extension BSD
 * (and therefore Darwin) archives use.  glibc's <ar.h> has the struct but not
 * the constant.
 */
#ifndef _KCB_SHIM_LINUX_AR_H
#define _KCB_SHIM_LINUX_AR_H
#include_next <ar.h>
#ifndef AR_EFMT1
#define AR_EFMT1 "#1/"
#endif
#endif
