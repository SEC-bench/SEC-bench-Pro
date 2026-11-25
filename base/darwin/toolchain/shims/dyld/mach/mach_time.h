/* base/darwin/toolchain/shims/dyld/mach/mach_time.h
 *
 * AppCacheBuilder.cpp times its phases with mach_absolute_time().  On Linux,
 * CLOCK_MONOTONIC nanoseconds, with a 1:1 timebase so the sources' usual
 * "multiply by numer / denom" turns nanoseconds into nanoseconds.
 */
#ifndef _KCB_SHIM_LINUX_MACH_TIME_H
#define _KCB_SHIM_LINUX_MACH_TIME_H

#include <stdint.h>
#include <time.h>

#ifdef __cplusplus
extern "C" {
#endif

struct mach_timebase_info { uint32_t numer; uint32_t denom; };
typedef struct mach_timebase_info *mach_timebase_info_t;
typedef struct mach_timebase_info  mach_timebase_info_data_t;

static inline uint64_t mach_absolute_time(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ull + (uint64_t)ts.tv_nsec;
}
static inline uint64_t mach_continuous_time(void) { return mach_absolute_time(); }
static inline int mach_timebase_info(mach_timebase_info_t info)
{
    if ( info != 0 ) { info->numer = 1; info->denom = 1; }
    return 0;
}

#ifdef __cplusplus
}
#endif
#endif
