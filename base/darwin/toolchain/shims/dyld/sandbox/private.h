/* base/darwin/toolchain/shims/dyld/sandbox/private.h
 *
 * <sandbox/private.h> is Apple-private.  common/ClosureFileSystemPhysical.cpp
 * calls sandbox_check() to decide whether the current process may read a path.
 * An offline builder is not sandboxed: report "not blocked" (0).
 */
#ifndef _KCB_SHIM_SANDBOX_PRIVATE_H
#define _KCB_SHIM_SANDBOX_PRIVATE_H
#include <stdint.h>
#include <unistd.h>
#ifdef __cplusplus
extern "C" {
#endif
enum sandbox_filter_type {
    SANDBOX_FILTER_NONE = 0,
    SANDBOX_FILTER_PATH = 1,
    SANDBOX_FILTER_GLOBAL_NAME = 2,
    SANDBOX_FILTER_LOCAL_NAME = 3,
    SANDBOX_FILTER_APPLEEVENT_DESTINATION = 4,
    SANDBOX_FILTER_RIGHT_NAME = 5,
};
#define SANDBOX_CHECK_NO_REPORT (1 << 30)
static inline int sandbox_check(pid_t pid, const char *operation, int type, ...)
{ (void)pid; (void)operation; (void)type; return 0; }
#ifdef __cplusplus
}
#endif
#endif
