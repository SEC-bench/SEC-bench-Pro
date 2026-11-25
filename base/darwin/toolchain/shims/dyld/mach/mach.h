/* base/darwin/toolchain/shims/dyld/mach/mach.h
 *
 * The Mach surface the offline KC builder actually uses is tiny -- ten symbols
 * across common/Array.h, common/MachOAnalyzer.cpp, common/MachOLoaded.cpp,
 * common/ClosureFileSystemPhysical.cpp and lsl/Allocator.cpp:
 *
 *   vm_allocate vm_deallocate vm_protect vm_copy
 *   mach_task_self mach_host_self mach_port_deallocate host_info
 *   KERN_SUCCESS VM_PROT_* VM_FLAGS_ANYWHERE VM_MAKE_TAG
 *
 * All of it is "give me some anonymous memory / change its protection", which
 * maps directly onto mmap/munmap/mprotect.  Nothing here talks to a kernel
 * port: mach_task_self() and mach_host_self() return an opaque non-zero
 * token that only ever gets passed back into these same functions.
 */
#ifndef _KCB_SHIM_LINUX_MACH_H
#define _KCB_SHIM_LINUX_MACH_H

#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>

#include <mach/boolean.h>
#include <mach/machine.h>
#include <mach/machine/vm_types.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef int          kern_return_t;
typedef unsigned int mach_port_t;
typedef unsigned int mach_port_name_t;
typedef natural_t    mach_msg_type_number_t;
typedef mach_port_t  vm_map_t;
typedef mach_port_t  task_t;
typedef mach_port_t  host_t;
typedef mach_port_t  host_name_t;
typedef int          vm_prot_t;

#define KERN_SUCCESS             0
#define KERN_INVALID_ADDRESS     1
#define KERN_PROTECTION_FAILURE  2
#define KERN_NO_SPACE            3
#define KERN_INVALID_ARGUMENT    4
#define KERN_FAILURE             5
#define KERN_RESOURCE_SHORTAGE   6

#define VM_PROT_NONE     ((vm_prot_t)0x00)
#define VM_PROT_READ     ((vm_prot_t)0x01)
#define VM_PROT_WRITE    ((vm_prot_t)0x02)
#define VM_PROT_EXECUTE  ((vm_prot_t)0x04)
#define VM_PROT_ALL      (VM_PROT_READ|VM_PROT_WRITE|VM_PROT_EXECUTE)
#define VM_PROT_DEFAULT  (VM_PROT_READ|VM_PROT_WRITE)

#define VM_FLAGS_FIXED       0x0000
#define VM_FLAGS_ANYWHERE    0x0001
#define VM_FLAGS_PURGABLE    0x0002
#define VM_MAKE_TAG(tag)     ((tag) << 24)
#define VM_MEMORY_DYLD       60
#define VM_MEMORY_DYLD_MALLOC 61

#define MACH_PORT_NULL       ((mach_port_t)0)
#define TASK_NULL            ((task_t)0)

/* host_info(HOST_BASIC_INFO) -- only max_mem is read. */
#define HOST_BASIC_INFO      1
struct host_basic_info {
    integer_t  max_cpus;
    integer_t  avail_cpus;
    natural_t  memory_size;
    cpu_type_t cpu_type;
    cpu_subtype_t cpu_subtype;
    cpu_threadtype_t cpu_threadtype;
    integer_t  physical_cpu;
    integer_t  physical_cpu_max;
    integer_t  logical_cpu;
    integer_t  logical_cpu_max;
    uint64_t   max_mem;
};
typedef struct host_basic_info  host_basic_info_data_t;
typedef struct host_basic_info *host_basic_info_t;
typedef integer_t *host_info_t;
#define HOST_BASIC_INFO_COUNT ((mach_msg_type_number_t)(sizeof(host_basic_info_data_t)/sizeof(integer_t)))

/* <mach/vm_param.h>'s page rounding -- common/Array.h rounds its vm_allocate
   sizes with them.  PAGE_SIZE comes from the command line (see
   build-dyld-app-cache-util.sh); it only affects how much slack an internal buffer gets. */
#ifndef round_page
#define round_page(x)  ((((uintptr_t)(x)) + PAGE_SIZE - 1) & ~((uintptr_t)PAGE_SIZE - 1))
#endif
#ifndef trunc_page
#define trunc_page(x)  (((uintptr_t)(x)) & ~((uintptr_t)PAGE_SIZE - 1))
#endif
#ifndef PAGE_MASK
#define PAGE_MASK (PAGE_SIZE - 1)
#endif

static inline task_t mach_task_self(void) { return (task_t)1; }
static inline host_t mach_host_self(void) { return (host_t)2; }
static inline kern_return_t mach_port_deallocate(task_t t, mach_port_t p) { (void)t; (void)p; return KERN_SUCCESS; }

static inline kern_return_t vm_allocate(vm_map_t target, vm_address_t *address,
                                        vm_size_t size, int flags)
{
    void *hint = (flags & VM_FLAGS_ANYWHERE) ? NULL : (void *)*address;
    int   mf   = MAP_PRIVATE | MAP_ANONYMOUS | ((flags & VM_FLAGS_ANYWHERE) ? 0 : MAP_FIXED);
    void *p;
    (void)target;
    if ( size == 0 ) { *address = 0; return KERN_SUCCESS; }
    p = mmap(hint, (size_t)size, PROT_READ | PROT_WRITE, mf, -1, 0);
    if ( p == MAP_FAILED )
        return KERN_NO_SPACE;
    *address = (vm_address_t)p;
    return KERN_SUCCESS;
}

static inline kern_return_t vm_deallocate(vm_map_t target, vm_address_t address, vm_size_t size)
{
    (void)target;
    if ( address == 0 || size == 0 )
        return KERN_SUCCESS;
    return (munmap((void *)address, (size_t)size) == 0) ? KERN_SUCCESS : KERN_INVALID_ADDRESS;
}

static inline kern_return_t vm_protect(vm_map_t target, vm_address_t address, vm_size_t size,
                                       boolean_t setMaximum, vm_prot_t newProtection)
{
    int p = 0;
    (void)target; (void)setMaximum;
    if ( newProtection & VM_PROT_READ )    p |= PROT_READ;
    if ( newProtection & VM_PROT_WRITE )   p |= PROT_WRITE;
    if ( newProtection & VM_PROT_EXECUTE ) p |= PROT_EXEC;
    return (mprotect((void *)address, (size_t)size, p) == 0) ? KERN_SUCCESS : KERN_PROTECTION_FAILURE;
}

static inline kern_return_t vm_copy(vm_map_t target, vm_address_t src, vm_size_t size, vm_address_t dst)
{
    (void)target;
    memmove((void *)dst, (const void *)src, (size_t)size);
    return KERN_SUCCESS;
}

static inline kern_return_t host_info(host_t host, int flavor, host_info_t info,
                                      mach_msg_type_number_t *count)
{
    (void)host;
    if ( flavor != HOST_BASIC_INFO || count == NULL || *count < HOST_BASIC_INFO_COUNT )
        return KERN_INVALID_ARGUMENT;
    host_basic_info_t hi = (host_basic_info_t)info;
    memset(hi, 0, sizeof(*hi));
    long pages = sysconf(_SC_PHYS_PAGES), psz = sysconf(_SC_PAGESIZE), ncpu = sysconf(_SC_NPROCESSORS_ONLN);
    hi->max_cpus = hi->avail_cpus = hi->physical_cpu = hi->logical_cpu = (integer_t)(ncpu > 0 ? ncpu : 1);
    hi->physical_cpu_max = hi->logical_cpu_max = hi->max_cpus;
    hi->max_mem = (pages > 0 && psz > 0) ? (uint64_t)pages * (uint64_t)psz : (uint64_t)4 << 30;
    hi->memory_size = (natural_t)((hi->max_mem > 0xFFFFFFFFull) ? 0xFFFFFFFFull : hi->max_mem);
    *count = HOST_BASIC_INFO_COUNT;
    return KERN_SUCCESS;
}

#ifdef __cplusplus
}
#endif
#endif
