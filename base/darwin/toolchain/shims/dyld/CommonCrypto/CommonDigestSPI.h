/* base/darwin/toolchain/shims/dyld/CommonCrypto/CommonDigestSPI.h
 *
 * The public SDK ships CommonCrypto/CommonDigest.h but not CommonDigestSPI.h,
 * which is where CCDigestRef / CCDigestCreate / kCCDigestSHA256 live.
 * kernel-collection-builder/AppCacheBuilder.cpp:5811 (generateUUID) is the
 * only user.  Implemented over the public CC_SHA256_* API in
 * shims/ccdigest_shim.c.
 *
 * NOTE: this file deliberately shadows nothing else — <CommonCrypto/...> headers other
 * than CommonDigestSPI.h still resolve to the SDK because the shim directory
 * has no other entries under CommonCrypto/.
 */
#ifndef _KCB_SHIM_COMMONDIGESTSPI_H
#define _KCB_SHIM_COMMONDIGESTSPI_H

#include <stddef.h>
#include <stdint.h>
#include <CommonCrypto/CommonDigest.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct CCDigestCtx *CCDigestRef;

enum {
    kCCDigestNone   = 0,
    kCCDigestSHA1   = 8,
    kCCDigestSHA224 = 9,
    kCCDigestSHA256 = 10,
    kCCDigestSHA384 = 11,
    kCCDigestSHA512 = 12,
};
typedef uint32_t CCDigestAlgorithm;

CCDigestRef CCDigestCreate(CCDigestAlgorithm alg);
int         CCDigestUpdate(CCDigestRef ctx, const void *data, size_t len);
int         CCDigestFinal(CCDigestRef ctx, uint8_t *output);
void        CCDigestDestroy(CCDigestRef ctx);
size_t      CCDigestGetOutputSize(CCDigestAlgorithm alg);

#ifdef __cplusplus
}
#endif
#endif /* _KCB_SHIM_COMMONDIGESTSPI_H */
