/* Stand-in for <corecrypto/ccsha2.h>.  See corecrypto/ccdigest.h. */
#ifndef _KCB_SHIM_CCSHA2_H
#define _KCB_SHIM_CCSHA2_H
#include <corecrypto/ccdigest.h>
#ifdef __cplusplus
extern "C" {
#endif
#define CCSHA256_OUTPUT_SIZE 32
#define CCSHA384_OUTPUT_SIZE 48
#define CCSHA512_OUTPUT_SIZE 64
const struct ccdigest_info *ccsha256_di(void);
const struct ccdigest_info *ccsha384_di(void);
const struct ccdigest_info *ccsha512_di(void);
#ifdef __cplusplus
}
#endif
#endif
