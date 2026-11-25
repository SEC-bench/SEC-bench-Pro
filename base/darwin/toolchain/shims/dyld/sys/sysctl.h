/* base/darwin/toolchain/shims/dyld/sys/sysctl.h
 *
 * Linux has no sysctlbyname.  mach_o/Architecture.cpp:453 asks the *running*
 * kernel to grade a list of cputypes ("kern.grade_cputype") when picking the
 * best slice for the host; a Linux host has no opinion about arm64e, and the
 * KC builder always passes an explicit -arch anyway.  Fail the call so the
 * caller falls back to its static grading table.
 */
#ifndef _KCB_SHIM_LINUX_SYSCTL_H
#define _KCB_SHIM_LINUX_SYSCTL_H
#include <stddef.h>
#include <errno.h>
#ifdef __cplusplus
extern "C" {
#endif
static inline int sysctlbyname(const char *name, void *oldp, size_t *oldlenp,
                               void *newp, size_t newlen)
{ (void)name; (void)oldp; (void)oldlenp; (void)newp; (void)newlen; errno = ENOENT; return -1; }
static inline int sysctl(int *name, unsigned namelen, void *oldp, size_t *oldlenp,
                         void *newp, size_t newlen)
{ (void)name; (void)namelen; (void)oldp; (void)oldlenp; (void)newp; (void)newlen; errno = ENOENT; return -1; }
#ifdef __cplusplus
}
#endif
#endif
