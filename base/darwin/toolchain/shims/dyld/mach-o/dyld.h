/* base/darwin/toolchain/shims/dyld/mach-o/dyld.h
 *
 * The live-process dyld API.  other-tools/FileUtils.cpp uses exactly one
 * entry point, _NSGetExecutablePath(), to find the tool's own binary; on
 * Linux that is /proc/self/exe.  The image-enumeration calls below are
 * declared for completeness and are not reachable in the KC-builder path.
 */
#ifndef _KCB_SHIM_LINUX_MACHO_DYLD_H
#define _KCB_SHIM_LINUX_MACHO_DYLD_H

#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <unistd.h>

#ifdef __cplusplus
extern "C" {
#endif

static inline int _NSGetExecutablePath(char *buf, uint32_t *bufsize)
{
    char tmp[4096];
    ssize_t n = readlink("/proc/self/exe", tmp, sizeof(tmp) - 1);
    if ( n < 0 )
        return -1;
    tmp[n] = '\0';
    if ( bufsize == NULL )
        return -1;
    if ( (uint32_t)(n + 1) > *bufsize ) { *bufsize = (uint32_t)(n + 1); return -1; }
    memcpy(buf, tmp, (size_t)n + 1);
    return 0;
}

static inline uint32_t _dyld_image_count(void) { return 0; }
static inline const char *_dyld_get_image_name(uint32_t i) { (void)i; return 0; }
static inline intptr_t _dyld_get_image_vmaddr_slide(uint32_t i) { (void)i; return 0; }

#ifdef __cplusplus
}
#endif
#endif
