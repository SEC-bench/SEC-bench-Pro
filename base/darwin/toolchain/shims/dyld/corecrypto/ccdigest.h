/* base/darwin/toolchain/shims/dyld/corecrypto/ccdigest.h
 *
 * Stand-in for corecrypto's <corecrypto/ccdigest.h>.  corecrypto headers are
 * not in the public macOS SDK.  common/MachOFile.cpp uses exactly the
 * ccdigest_di_decl/init/update/final/clear quintet to compute a code-directory
 * cdhash; common/MachOLoaded.cpp includes the headers but uses nothing.
 *
 * The _di() accessors are in ccdigest_shim.c, over the CommonCrypto shim,
 * which uses OpenSSL's EVP.
 */
#ifndef _KCB_SHIM_CCDIGEST_H
#define _KCB_SHIM_CCDIGEST_H

#include <stddef.h>
#include <stdint.h>
#include <string.h>

#ifdef __cplusplus
extern "C" {
#endif

struct ccdigest_info {
    size_t output_size;
    size_t ctx_size;
    void (*di_init)(void *ctx);
    void (*di_update)(void *ctx, size_t len, const void *data);
    void (*di_final)(void *ctx, uint8_t *out);
};

#define ccdigest_di_decl(di, name)          uint8_t name[(di)->ctx_size] __attribute__((aligned(16)))
#define ccdigest_init(di, ctx)              (di)->di_init((void *)(ctx))
#define ccdigest_update(di, ctx, len, data) (di)->di_update((void *)(ctx), (len), (data))
#define ccdigest_final(di, ctx, out)        (di)->di_final((void *)(ctx), (out))
#define ccdigest_di_clear(di, ctx)          memset((void *)(ctx), 0, (di)->ctx_size)

#ifdef __cplusplus
}
#endif
#endif /* _KCB_SHIM_CCDIGEST_H */
