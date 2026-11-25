/* base/darwin/toolchain/shims/dyld/libkern/OSByteOrder.h
 *
 * Byte swapping, used through <architecture/byte_order.h> (staged verbatim
 * from xnu) by mach_o/Error.cpp and the fat-header readers.  Over the
 * compiler builtins so it is endian-correct on any host.
 */
#ifndef _KCB_SHIM_LINUX_OSBYTEORDER_H
#define _KCB_SHIM_LINUX_OSBYTEORDER_H

#include <stdint.h>

#define OSSwapConstInt16(x) __builtin_bswap16((uint16_t)(x))
#define OSSwapConstInt32(x) __builtin_bswap32((uint32_t)(x))
#define OSSwapConstInt64(x) __builtin_bswap64((uint64_t)(x))

static inline uint16_t OSSwapInt16(uint16_t x) { return __builtin_bswap16(x); }
static inline uint32_t OSSwapInt32(uint32_t x) { return __builtin_bswap32(x); }
static inline uint64_t OSSwapInt64(uint64_t x) { return __builtin_bswap64(x); }

#if defined(__BYTE_ORDER__) && __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
  #define OSSwapBigToHostInt16(x)    ((uint16_t)(x))
  #define OSSwapBigToHostInt32(x)    ((uint32_t)(x))
  #define OSSwapBigToHostInt64(x)    ((uint64_t)(x))
  #define OSSwapHostToBigInt16(x)    ((uint16_t)(x))
  #define OSSwapHostToBigInt32(x)    ((uint32_t)(x))
  #define OSSwapHostToBigInt64(x)    ((uint64_t)(x))
  #define OSSwapLittleToHostInt16(x) OSSwapInt16(x)
  #define OSSwapLittleToHostInt32(x) OSSwapInt32(x)
  #define OSSwapLittleToHostInt64(x) OSSwapInt64(x)
  #define OSSwapHostToLittleInt16(x) OSSwapInt16(x)
  #define OSSwapHostToLittleInt32(x) OSSwapInt32(x)
  #define OSSwapHostToLittleInt64(x) OSSwapInt64(x)
#else
  #define OSSwapBigToHostInt16(x)    OSSwapInt16(x)
  #define OSSwapBigToHostInt32(x)    OSSwapInt32(x)
  #define OSSwapBigToHostInt64(x)    OSSwapInt64(x)
  #define OSSwapHostToBigInt16(x)    OSSwapInt16(x)
  #define OSSwapHostToBigInt32(x)    OSSwapInt32(x)
  #define OSSwapHostToBigInt64(x)    OSSwapInt64(x)
  #define OSSwapLittleToHostInt16(x) ((uint16_t)(x))
  #define OSSwapLittleToHostInt32(x) ((uint32_t)(x))
  #define OSSwapLittleToHostInt64(x) ((uint64_t)(x))
  #define OSSwapHostToLittleInt16(x) ((uint16_t)(x))
  #define OSSwapHostToLittleInt32(x) ((uint32_t)(x))
  #define OSSwapHostToLittleInt64(x) ((uint64_t)(x))
#endif

/* Unaligned load/store with an explicit byte order -- common/FileAbstraction.hpp
   reads and writes Mach-O fields through these. */
static inline uint16_t _kcb_ldu16(const volatile void *p) { uint16_t v; __builtin_memcpy(&v, (const void *)p, 2); return v; }
static inline uint32_t _kcb_ldu32(const volatile void *p) { uint32_t v; __builtin_memcpy(&v, (const void *)p, 4); return v; }
static inline uint64_t _kcb_ldu64(const volatile void *p) { uint64_t v; __builtin_memcpy(&v, (const void *)p, 8); return v; }
static inline void _kcb_stu16(volatile void *p, uint16_t v) { __builtin_memcpy((void *)p, &v, 2); }
static inline void _kcb_stu32(volatile void *p, uint32_t v) { __builtin_memcpy((void *)p, &v, 4); }
static inline void _kcb_stu64(volatile void *p, uint64_t v) { __builtin_memcpy((void *)p, &v, 8); }

static inline uint16_t OSReadBigInt16(const volatile void *p, uintptr_t o)     { return OSSwapBigToHostInt16(_kcb_ldu16((const char *)p + o)); }
static inline uint32_t OSReadBigInt32(const volatile void *p, uintptr_t o)     { return OSSwapBigToHostInt32(_kcb_ldu32((const char *)p + o)); }
static inline uint64_t OSReadBigInt64(const volatile void *p, uintptr_t o)     { return OSSwapBigToHostInt64(_kcb_ldu64((const char *)p + o)); }
static inline uint16_t OSReadLittleInt16(const volatile void *p, uintptr_t o)  { return OSSwapLittleToHostInt16(_kcb_ldu16((const char *)p + o)); }
static inline uint32_t OSReadLittleInt32(const volatile void *p, uintptr_t o)  { return OSSwapLittleToHostInt32(_kcb_ldu32((const char *)p + o)); }
static inline uint64_t OSReadLittleInt64(const volatile void *p, uintptr_t o)  { return OSSwapLittleToHostInt64(_kcb_ldu64((const char *)p + o)); }
static inline void OSWriteBigInt16(volatile void *p, uintptr_t o, uint16_t v)    { _kcb_stu16((char *)p + o, OSSwapHostToBigInt16(v)); }
static inline void OSWriteBigInt32(volatile void *p, uintptr_t o, uint32_t v)    { _kcb_stu32((char *)p + o, OSSwapHostToBigInt32(v)); }
static inline void OSWriteBigInt64(volatile void *p, uintptr_t o, uint64_t v)    { _kcb_stu64((char *)p + o, OSSwapHostToBigInt64(v)); }
static inline void OSWriteLittleInt16(volatile void *p, uintptr_t o, uint16_t v) { _kcb_stu16((char *)p + o, OSSwapHostToLittleInt16(v)); }
static inline void OSWriteLittleInt32(volatile void *p, uintptr_t o, uint32_t v) { _kcb_stu32((char *)p + o, OSSwapHostToLittleInt32(v)); }
static inline void OSWriteLittleInt64(volatile void *p, uintptr_t o, uint64_t v) { _kcb_stu64((char *)p + o, OSSwapHostToLittleInt64(v)); }

#endif
