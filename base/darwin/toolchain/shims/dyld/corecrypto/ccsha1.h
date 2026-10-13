/* Stand-in for <corecrypto/ccsha1.h>.  See corecrypto/ccdigest.h. */
#ifndef _KCB_SHIM_CCSHA1_H
#define _KCB_SHIM_CCSHA1_H
#include <corecrypto/ccdigest.h>
#ifdef __cplusplus
extern "C" {
#endif
#define CCSHA1_OUTPUT_SIZE 20
const struct ccdigest_info *ccsha1_di(void);
#ifdef __cplusplus
}
#endif
#endif
