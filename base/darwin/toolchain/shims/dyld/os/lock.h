/* base/darwin/toolchain/shims/dyld/os/lock.h
 *
 * os_unfair_lock over pthread_mutex.  lsl/Allocator.{h,cpp} takes one around
 * its pool; MachOAppCache/MachOAnalyzer pull it in transitively.  The lock is
 * real: dispatch_apply runs on libdispatch's worker threads.
 */
#ifndef _KCB_SHIM_LINUX_OS_LOCK_H
#define _KCB_SHIM_LINUX_OS_LOCK_H

#include <pthread.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct os_unfair_lock_s { pthread_mutex_t m; } os_unfair_lock, *os_unfair_lock_t;

#define OS_UNFAIR_LOCK_INIT ((os_unfair_lock){ PTHREAD_MUTEX_INITIALIZER })

static inline void os_unfair_lock_lock(os_unfair_lock_t l)   { pthread_mutex_lock(&l->m); }
static inline void os_unfair_lock_unlock(os_unfair_lock_t l) { pthread_mutex_unlock(&l->m); }
static inline bool os_unfair_lock_trylock(os_unfair_lock_t l){ return pthread_mutex_trylock(&l->m) == 0; }
static inline void os_unfair_lock_assert_owner(os_unfair_lock_t l) { (void)l; }
static inline void os_unfair_lock_assert_not_owner(os_unfair_lock_t l) { (void)l; }

#ifdef __cplusplus
}
#endif
#endif
