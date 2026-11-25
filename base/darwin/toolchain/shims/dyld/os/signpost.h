/* base/darwin/toolchain/shims/dyld/os/signpost.h
 *
 * cache_builder/Timer.h emits os_signpost intervals so Instruments can show
 * the shared-cache builder's phases.  There is no Instruments here; the
 * signpost calls become no-ops and the ids are opaque zeros.
 */
#ifndef _KCB_SHIM_LINUX_OS_SIGNPOST_H
#define _KCB_SHIM_LINUX_OS_SIGNPOST_H

#include <stdint.h>
#include <os/log.h>

typedef uint64_t os_signpost_id_t;

#define OS_SIGNPOST_ID_NULL    ((os_signpost_id_t)0)
#define OS_SIGNPOST_ID_INVALID ((os_signpost_id_t)~0ull)

static inline os_signpost_id_t os_signpost_id_generate(os_log_t log) { (void)log; return (os_signpost_id_t)1; }
static inline os_signpost_id_t os_signpost_id_make_with_pointer(os_log_t log, const void *p) { (void)log; (void)p; return (os_signpost_id_t)1; }
static inline bool os_signpost_enabled(os_log_t log) { (void)log; return false; }

#define os_signpost_interval_begin(log, id, name, ...) ((void)0)
#define os_signpost_interval_end(log, id, name, ...)   ((void)0)
#define os_signpost_event_emit(log, id, name, ...)     ((void)0)

#endif
