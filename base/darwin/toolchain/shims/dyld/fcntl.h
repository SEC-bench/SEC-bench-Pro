/* base/darwin/toolchain/shims/dyld/fcntl.h
 *
 * Darwin's fcntl(fd, F_GETPATH, buf) fills a MAXPATHLEN buffer with the path
 * an open descriptor refers to.  common/ClosureFileSystemPhysical.cpp uses it
 * twice, to report the real path of a file it opened (symlink resolution).
 * Linux's equivalent is readlink("/proc/self/fd/<n>"), so define F_GETPATH as
 * a private command number and intercept it in a variadic wrapper.
 *
 * The wrapper is defined *before* the macro that redirects fcntl to it, so
 * its own call reaches the real libc fcntl.
 */
#ifndef _KCB_SHIM_LINUX_FCNTL_H
#define _KCB_SHIM_LINUX_FCNTL_H

#include_next <fcntl.h>

#ifndef F_GETPATH

#include <limits.h>
#include <stdarg.h>
#include <stdio.h>
#include <unistd.h>

#define F_GETPATH 0x4b434250   /* 'KCBP' -- private to this shim */
#ifndef MAXPATHLEN
#define MAXPATHLEN PATH_MAX
#endif

#ifdef __cplusplus
extern "C++" {
#endif

static inline int kcb_fcntl(int fd, int cmd, ...)
{
    va_list ap;
    va_start(ap, cmd);
    if ( cmd == F_GETPATH ) {
        char *buf = va_arg(ap, char *);
        va_end(ap);
        char link[64];
        snprintf(link, sizeof(link), "/proc/self/fd/%d", fd);
        ssize_t n = readlink(link, buf, PATH_MAX - 1);
        if ( n < 0 )
            return -1;
        buf[n] = '\0';
        return 0;
    }
    void *arg = va_arg(ap, void *);
    va_end(ap);
    return fcntl(fd, cmd, arg);
}

#ifdef __cplusplus
}
#endif

#define fcntl kcb_fcntl

#endif /* !F_GETPATH */
#endif
