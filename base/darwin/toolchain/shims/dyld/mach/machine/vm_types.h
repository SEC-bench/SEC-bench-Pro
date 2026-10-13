/* base/darwin/toolchain/shims/dyld/mach/machine/vm_types.h -- standalone base
 * Mach scalar types.  Kept separate from mach/mach.h so that xnu's
 * osfmk/mach/machine.h (found in place through build-dyld-app-cache-util.sh's
 * -idirafter) can include it without a cycle. */
#ifndef _KCB_SHIM_LINUX_MACH_VM_TYPES_H
#define _KCB_SHIM_LINUX_MACH_VM_TYPES_H
#include <stdint.h>
#include <stddef.h>
typedef unsigned int  natural_t;
typedef int           integer_t;
typedef uintptr_t     vm_offset_t;
typedef uintptr_t     vm_size_t;
typedef uintptr_t     vm_address_t;
typedef uint64_t      mach_vm_address_t;
typedef uint64_t      mach_vm_offset_t;
typedef uint64_t      mach_vm_size_t;
typedef uint64_t      vm_map_offset_t;
typedef uint64_t      vm_map_address_t;
typedef uint64_t      vm_map_size_t;
#endif
