/* base/darwin/toolchain/shims/dyld/commoncrypto_shim.c
 *
 * CommonCrypto (digest + HMAC) over OpenSSL, plus abort_report_np(), which
 * <libc_private.h> declares.  Portable C; the OpenSSL EVP API only.
 */
#include <CommonCrypto/CommonDigest.h>
#include <CommonCrypto/CommonHMAC.h>

#include <openssl/evp.h>
#include <openssl/hmac.h>

#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int cc_init(void **slot, const EVP_MD *md)
{
    EVP_MD_CTX *c = EVP_MD_CTX_new();
    if ( c == NULL )
        return 0;
    if ( EVP_DigestInit_ex(c, md, NULL) != 1 ) { EVP_MD_CTX_free(c); return 0; }
    *slot = c;
    return 1;
}
static int cc_update(void **slot, const void *data, CC_LONG len)
{
    return (*slot != NULL) ? EVP_DigestUpdate((EVP_MD_CTX *)*slot, data, len) : 0;
}
static int cc_final(void **slot, unsigned char *md)
{
    unsigned int n = 0;
    int r;
    if ( *slot == NULL )
        return 0;
    r = EVP_DigestFinal_ex((EVP_MD_CTX *)*slot, md, &n);
    EVP_MD_CTX_free((EVP_MD_CTX *)*slot);
    *slot = NULL;
    return r;
}

int CC_SHA1_Init(CC_SHA1_CTX *c)                                { return cc_init(&c->ctx, EVP_sha1()); }
int CC_SHA1_Update(CC_SHA1_CTX *c, const void *d, CC_LONG l)    { return cc_update(&c->ctx, d, l); }
int CC_SHA1_Final(unsigned char *md, CC_SHA1_CTX *c)            { return cc_final(&c->ctx, md); }

int CC_SHA256_Init(CC_SHA256_CTX *c)                            { return cc_init(&c->ctx, EVP_sha256()); }
int CC_SHA256_Update(CC_SHA256_CTX *c, const void *d, CC_LONG l){ return cc_update(&c->ctx, d, l); }
int CC_SHA256_Final(unsigned char *md, CC_SHA256_CTX *c)        { return cc_final(&c->ctx, md); }

int CC_SHA384_Init(CC_SHA512_CTX *c)                            { return cc_init(&c->ctx, EVP_sha384()); }
int CC_SHA384_Update(CC_SHA512_CTX *c, const void *d, CC_LONG l){ return cc_update(&c->ctx, d, l); }
int CC_SHA384_Final(unsigned char *md, CC_SHA512_CTX *c)        { return cc_final(&c->ctx, md); }

int CC_SHA512_Init(CC_SHA512_CTX *c)                            { return cc_init(&c->ctx, EVP_sha512()); }
int CC_SHA512_Update(CC_SHA512_CTX *c, const void *d, CC_LONG l){ return cc_update(&c->ctx, d, l); }
int CC_SHA512_Final(unsigned char *md, CC_SHA512_CTX *c)        { return cc_final(&c->ctx, md); }

unsigned char *CC_SHA1(const void *data, CC_LONG len, unsigned char *md)
{
    unsigned int n = 0;
    EVP_Digest(data, len, md, &n, EVP_sha1(), NULL);
    return md;
}
unsigned char *CC_SHA256(const void *data, CC_LONG len, unsigned char *md)
{
    unsigned int n = 0;
    EVP_Digest(data, len, md, &n, EVP_sha256(), NULL);
    return md;
}

void CCHmac(CCHmacAlgorithm algorithm, const void *key, size_t keyLength,
            const void *data, size_t dataLength, void *macOut)
{
    const EVP_MD *md;
    unsigned int  n = 0;
    switch ( algorithm ) {
        case kCCHmacAlgSHA1:   md = EVP_sha1();   break;
        case kCCHmacAlgSHA256: md = EVP_sha256(); break;
        case kCCHmacAlgSHA384: md = EVP_sha384(); break;
        case kCCHmacAlgSHA512: md = EVP_sha512(); break;
        default:               return;
    }
    HMAC(md, key, (int)keyLength, (const unsigned char *)data, dataLength,
         (unsigned char *)macOut, &n);
}

/* <libc_private.h> declares this; on Darwin libSystem exports it. */
void abort_report_np(const char *format, ...)
{
    va_list ap;
    va_start(ap, format);
    vfprintf(stderr, format, ap);
    va_end(ap);
    fputc('\n', stderr);
    abort();
}
