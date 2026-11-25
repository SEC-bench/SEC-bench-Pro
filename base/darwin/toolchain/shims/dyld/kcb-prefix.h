/* base/darwin/toolchain/shims/dyld/kcb-prefix.h
 *
 * Force-included (-include) into every translation unit of the Linux build.
 * It carries the scraps of Darwin vocabulary that are neither a header of
 * their own nor worth shadowing a system header for:
 *
 *  - <sys/cdefs.h> printf-attribute macros.  Apple's sys/cdefs.h defines
 *    __printflike/__scanflike; glibc's does not, and MachOAnalyzer.cpp:149
 *    puts __printflike on a *block* declaration, which does not even parse
 *    without it.
 *  - htonl/ntohl (common/MachOFile.cpp's code-signature blob byte order);
 *    Darwin gets them transitively, glibc wants <arpa/inet.h>.
 *  - fsobj_id_t, used by one unread field of DyldSharedCache.h's file info.
 *  - <fcntl.h> and <dispatch/dispatch.h>, which AppCacheBuilder.cpp and
 *    dyld_app_cache_util.cpp use (dispatch_apply, ::open/O_RDONLY) without
 *    including: on Darwin they arrive transitively through the SDK's module
 *    map, which we have no equivalent of.  Both resolve to shims here.
 *
 * Nothing here changes behaviour; it only makes the Darwin sources parse.
 */
#ifndef _KCB_LINUX_PREFIX_H
#define _KCB_LINUX_PREFIX_H

#include <arpa/inet.h>
#include <stdint.h>
#include <fcntl.h>
#include <dispatch/dispatch.h>

#ifndef __printflike
  #define __printflike(fmtarg, firstvararg) __attribute__((format(printf, fmtarg, firstvararg)))
#endif
#ifndef __printf0like
  #define __printf0like(fmtarg, firstvararg) __attribute__((format(printf, fmtarg, firstvararg)))
#endif
#ifndef __scanflike
  #define __scanflike(fmtarg, firstvararg) __attribute__((format(scanf, fmtarg, firstvararg)))
#endif
#ifndef __unused
  #define __unused __attribute__((unused))
#endif
#ifndef __dead2
  #define __dead2 __attribute__((noreturn))
#endif
#ifndef __pure2
  #define __pure2 __attribute__((const))
#endif
#ifndef __DARWIN_ONLY_64_BIT_INO_T
  #define __DARWIN_ONLY_64_BIT_INO_T 1
#endif

#ifndef _FSOBJ_ID_T
#define _FSOBJ_ID_T
typedef struct fsobj_id { uint32_t fid_objno; uint32_t fid_generation; } fsobj_id_t;
#endif

#endif
