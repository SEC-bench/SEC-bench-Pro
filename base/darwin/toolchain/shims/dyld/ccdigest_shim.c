/* Implementations for the corecrypto/ and CommonCrypto/CommonDigestSPI.h
 * shims, over the public CommonCrypto digest API. */
#include <corecrypto/ccdigest.h>
#include <corecrypto/ccsha1.h>
#include <corecrypto/ccsha2.h>
#include <CommonCrypto/CommonDigestSPI.h>

#include <stdlib.h>
#include <string.h>

/* ---- corecrypto ccdigest_info over CC_SHA* --------------------------------*/

#define KCB_DI(NAME, CCNAME, CTX, OUT)                                        \
    static void NAME##_init(void *c)   { CCNAME##_Init((CTX *)c); }           \
    static void NAME##_update(void *c, size_t l, const void *d)               \
        { CCNAME##_Update((CTX *)c, d, (CC_LONG)l); }                         \
    static void NAME##_final(void *c, uint8_t *o)                             \
        { CCNAME##_Final(o, (CTX *)c); }                                      \
    static const struct ccdigest_info NAME##_info = {                         \
        OUT, sizeof(CTX), NAME##_init, NAME##_update, NAME##_final };         \
    const struct ccdigest_info *NAME##_di(void) { return &NAME##_info; }

#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wdeprecated-declarations"
KCB_DI(ccsha1,   CC_SHA1,   CC_SHA1_CTX,   20)
KCB_DI(ccsha256, CC_SHA256, CC_SHA256_CTX, 32)
KCB_DI(ccsha384, CC_SHA384, CC_SHA512_CTX, 48)
KCB_DI(ccsha512, CC_SHA512, CC_SHA512_CTX, 64)
#pragma clang diagnostic pop

/* ---- CCDigestRef over the same ------------------------------------------- */

struct CCDigestCtx {
    const struct ccdigest_info *di;
    uint8_t                     ctx[256];
};

static const struct ccdigest_info *di_for(CCDigestAlgorithm alg)
{
    switch ( alg ) {
        case kCCDigestSHA1:   return ccsha1_di();
        case kCCDigestSHA256: return ccsha256_di();
        case kCCDigestSHA384: return ccsha384_di();
        case kCCDigestSHA512: return ccsha512_di();
        default:              return NULL;
    }
}

CCDigestRef CCDigestCreate(CCDigestAlgorithm alg)
{
    const struct ccdigest_info *di = di_for(alg);
    struct CCDigestCtx *c;
    if ( di == NULL || di->ctx_size > sizeof(c->ctx) )
        return NULL;
    c = (struct CCDigestCtx *)calloc(1, sizeof(*c));
    if ( c == NULL )
        return NULL;
    c->di = di;
    di->di_init(c->ctx);
    return c;
}

int CCDigestUpdate(CCDigestRef c, const void *data, size_t len)
{
    if ( c == NULL )
        return -1;
    c->di->di_update(c->ctx, len, data);
    return 0;
}

int CCDigestFinal(CCDigestRef c, uint8_t *out)
{
    if ( c == NULL )
        return -1;
    c->di->di_final(c->ctx, out);
    return 0;
}

void CCDigestDestroy(CCDigestRef c) { free(c); }

size_t CCDigestGetOutputSize(CCDigestAlgorithm alg)
{
    const struct ccdigest_info *di = di_for(alg);
    return (di == NULL) ? 0 : di->output_size;
}
