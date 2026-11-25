/* base/darwin/toolchain/shims/dyld/CommonCrypto/CommonDigest.h
 *
 * The CommonCrypto digest API, implemented over OpenSSL's EVP.  This is the
 * Linux stand-in for the macOS SDK header; the *other* CommonCrypto shim
 * (CommonCrypto/CommonDigestSPI.h)
 * includes this one and builds CCDigestRef on top of it, and
 * ccdigest_shim.c turns both into corecrypto's ccdigest_info.
 *
 * Only the SHA-1/256/384/512 three-call forms are used
 * (common/MachOFile.cpp's cdhash, AppCacheBuilder's generateUUID and
 * KernelOptimizerBranches).  Context sizes matter: ccdigest_shim.c does
 * sizeof(CC_SHA256_CTX), so the contexts hold an EVP_MD_CTX* plus slack.
 *
 * Implementation: shims/commoncrypto_shim.c.
 */
#ifndef _KCB_SHIM_LINUX_COMMONDIGEST_H
#define _KCB_SHIM_LINUX_COMMONDIGEST_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef uint32_t CC_LONG;

#define CC_SHA1_DIGEST_LENGTH   20
#define CC_SHA224_DIGEST_LENGTH 28
#define CC_SHA256_DIGEST_LENGTH 32
#define CC_SHA384_DIGEST_LENGTH 48
#define CC_SHA512_DIGEST_LENGTH 64
#define CC_MD5_DIGEST_LENGTH    16

/* Opaque: an EVP_MD_CTX* behind a fixed-size struct so callers can declare it
   on the stack the way CommonCrypto lets them. */
typedef struct { void *ctx; } CC_SHA1_CTX;
typedef struct { void *ctx; } CC_SHA256_CTX;
typedef struct { void *ctx; } CC_SHA512_CTX;
typedef struct { void *ctx; } CC_MD5_CTX;

int  CC_SHA1_Init(CC_SHA1_CTX *c);
int  CC_SHA1_Update(CC_SHA1_CTX *c, const void *data, CC_LONG len);
int  CC_SHA1_Final(unsigned char *md, CC_SHA1_CTX *c);
unsigned char *CC_SHA1(const void *data, CC_LONG len, unsigned char *md);

int  CC_SHA256_Init(CC_SHA256_CTX *c);
int  CC_SHA256_Update(CC_SHA256_CTX *c, const void *data, CC_LONG len);
int  CC_SHA256_Final(unsigned char *md, CC_SHA256_CTX *c);
unsigned char *CC_SHA256(const void *data, CC_LONG len, unsigned char *md);

int  CC_SHA384_Init(CC_SHA512_CTX *c);
int  CC_SHA384_Update(CC_SHA512_CTX *c, const void *data, CC_LONG len);
int  CC_SHA384_Final(unsigned char *md, CC_SHA512_CTX *c);

int  CC_SHA512_Init(CC_SHA512_CTX *c);
int  CC_SHA512_Update(CC_SHA512_CTX *c, const void *data, CC_LONG len);
int  CC_SHA512_Final(unsigned char *md, CC_SHA512_CTX *c);

#ifdef __cplusplus
}
#endif
#endif
