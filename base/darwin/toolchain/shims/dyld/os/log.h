/* base/darwin/toolchain/shims/dyld/os/log.h -- os_log is a Darwin logging
 * facility with no Linux equivalent and no bearing on the bytes the builder
 * writes.  Everything is a no-op over an opaque handle. */
#ifndef _KCB_SHIM_LINUX_OS_LOG_H
#define _KCB_SHIM_LINUX_OS_LOG_H

#include <stdbool.h>

typedef struct os_log_s *os_log_t;
#define OS_LOG_DEFAULT   ((os_log_t)0)
#define OS_LOG_DISABLED  ((os_log_t)0)

typedef unsigned int os_log_type_t;
#define OS_LOG_TYPE_DEFAULT 0x00
#define OS_LOG_TYPE_INFO    0x01
#define OS_LOG_TYPE_DEBUG   0x02
#define OS_LOG_TYPE_ERROR   0x10
#define OS_LOG_TYPE_FAULT   0x11

static inline os_log_t os_log_create(const char *subsystem, const char *category)
{ (void)subsystem; (void)category; return (os_log_t)0; }
static inline bool os_log_type_enabled(os_log_t log, os_log_type_t type)
{ (void)log; (void)type; return false; }

#define os_log(log, format, ...)        ((void)0)
#define os_log_info(log, format, ...)   ((void)0)
#define os_log_debug(log, format, ...)  ((void)0)
#define os_log_error(log, format, ...)  ((void)0)
#define os_log_fault(log, format, ...)  ((void)0)
#define os_log_with_type(log, type, format, ...) ((void)0)

#endif
