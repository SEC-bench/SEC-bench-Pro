/* base/darwin/toolchain/shims/dyld/libc_private.h
 *
 * Apple Libc private header, not in the public SDK.  common/Diagnostics.cpp,
 * mach_o/Image.cpp and cache_builder/Error.cpp include it for one symbol:
 * abort_report_np(), the "crash with this message" helper.  libSystem exports
 * it on macOS; on Linux commoncrypto_shim.c defines it.
 */
#ifndef _KCB_SHIM_LIBC_PRIVATE_H
#define _KCB_SHIM_LIBC_PRIVATE_H
#ifdef __cplusplus
extern "C" {
#endif
extern void abort_report_np(const char *format, ...) __attribute__((noreturn, format(printf, 1, 2)));
#ifdef __cplusplus
}
#endif
#endif
