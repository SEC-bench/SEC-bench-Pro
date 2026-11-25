/* base/darwin/toolchain/shims/dyld/CommonCrypto/CommonHMAC.h
 *
 * One caller: AppCacheBuilder::fipsSign() seals com.apple.kec.corecrypto's
 * __TEXT,__fips_hmacs with HMAC-SHA256 over its __TEXT,__text.  Over OpenSSL.
 */
#ifndef _KCB_SHIM_LINUX_COMMONHMAC_H
#define _KCB_SHIM_LINUX_COMMONHMAC_H

#include <stddef.h>
#include <CommonCrypto/CommonDigest.h>

#ifdef __cplusplus
extern "C" {
#endif

enum {
    kCCHmacAlgSHA1   = 0,
    kCCHmacAlgMD5    = 1,
    kCCHmacAlgSHA256 = 2,
    kCCHmacAlgSHA384 = 3,
    kCCHmacAlgSHA512 = 4,
    kCCHmacAlgSHA224 = 5,
};
typedef uint32_t CCHmacAlgorithm;

void CCHmac(CCHmacAlgorithm algorithm, const void *key, size_t keyLength,
            const void *data, size_t dataLength, void *macOut);

#ifdef __cplusplus
}
#endif
#endif
