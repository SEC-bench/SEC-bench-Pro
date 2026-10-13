/* base/darwin/toolchain/shims/dyld/_simple.h
 *
 * Stand-in for Apple Libc's private <_simple.h> (SPI, not in the public SDK).
 * dyld uses it for Diagnostics/mach_o::Error message buffers: an append-only,
 * malloc-free string builder that dyld can use before malloc is up.  We do not
 * have that constraint, so this is a plain malloc-backed implementation.
 *
 * `_SIMPLE_STRING` must be `void *`: mach_o/Error.h stores the handle in a
 * `void* _buffer` and passes it straight back to `_simple_sfree`, which only
 * compiles in C++ if the parameter type is `void *`.
 *
 * Implementation: shims/simple_shim.c.  Portable C — nothing Darwin-specific.
 */
#ifndef _KCB_SHIM_SIMPLE_H
#define _KCB_SHIM_SIMPLE_H

#include <stdarg.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef void *_SIMPLE_STRING;

_SIMPLE_STRING _simple_salloc(void);
void           _simple_sfree(_SIMPLE_STRING b);
char          *_simple_string(_SIMPLE_STRING b);
void           _simple_sresize(_SIMPLE_STRING b);
int            _simple_sprintf(_SIMPLE_STRING b, const char *fmt, ...) __attribute__((format(printf, 2, 3)));
int            _simple_vsprintf(_SIMPLE_STRING b, const char *fmt, va_list ap) __attribute__((format(printf, 2, 0)));
int            _simple_sappend(_SIMPLE_STRING b, const char *str);
const char    *_simple_getenv(const char *envp[], const char *var);
int            _simple_vsnprintf(char *buf, size_t len, const char *fmt, va_list ap) __attribute__((format(printf, 3, 0)));
int            _simple_snprintf(char *buf, size_t len, const char *fmt, ...) __attribute__((format(printf, 3, 4)));

#ifdef __cplusplus
}
#endif
#endif /* _KCB_SHIM_SIMPLE_H */
