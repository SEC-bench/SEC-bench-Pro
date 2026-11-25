/* base/darwin/toolchain/shims/dyld/mach/machine/thread_status.h
 *
 * <mach-o/loader.h> includes it for the LC_UNIXTHREAD payload types.  The KC
 * builder writes exactly one LC_UNIXTHREAD, for arm64, and reads the kernel's;
 * it does so through mach_o's own structs, so all that is needed here is the
 * generic thread-state vocabulary plus the arm64 state layout.
 */
#ifndef _KCB_SHIM_LINUX_THREAD_STATUS_H
#define _KCB_SHIM_LINUX_THREAD_STATUS_H

#include <stdint.h>
#include <mach/machine/vm_types.h>

typedef int             thread_state_flavor_t;
typedef natural_t      *thread_state_t;
typedef natural_t       thread_state_data_t[614];
#define THREAD_STATE_MAX 614

#define ARM_THREAD_STATE     1
#define ARM_THREAD_STATE64   6
#define ARM_THREAD_STATE32   9
#define x86_THREAD_STATE32   1
#define x86_THREAD_STATE64   4

struct arm_thread_state64 {
    uint64_t x[29];
    uint64_t fp;
    uint64_t lr;
    uint64_t sp;
    uint64_t pc;
    uint32_t cpsr;
    uint32_t flags;
};
typedef struct arm_thread_state64 arm_thread_state64_t;
#define ARM_THREAD_STATE64_COUNT ((mach_msg_type_number_t)(sizeof(arm_thread_state64_t)/sizeof(uint32_t)))

struct arm_thread_state32 {
    uint32_t r[13];
    uint32_t sp;
    uint32_t lr;
    uint32_t pc;
    uint32_t cpsr;
};
typedef struct arm_thread_state32 arm_thread_state32_t;

#endif
