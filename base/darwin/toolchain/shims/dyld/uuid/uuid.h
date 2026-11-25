/* base/darwin/toolchain/shims/dyld/uuid/uuid.h
 *
 * util-linux's libuuid (uuid-dev) already provides uuid_t, uuid_generate,
 * uuid_unparse and friends with Apple-compatible signatures -- uuid_t is
 * unsigned char[16] in both.  The one thing it lacks is Apple's
 * uuid_string_t, the char[37] buffer type mach_o/UnsafeHeader.cpp declares
 * for uuid_unparse_upper().  Add it, and pass everything else through.
 */
#ifndef _KCB_SHIM_LINUX_UUID_H
#define _KCB_SHIM_LINUX_UUID_H
#include_next <uuid/uuid.h>
#ifndef _UUID_STRING_T
#define _UUID_STRING_T
typedef char uuid_string_t[37];
#endif
#endif
