/* base/darwin/toolchain/shims/swift-corelibs-foundation/cf_swift_stubs.c
 *
 * swift-corelibs-foundation's CoreFoundation hard-defines
 * DEPLOYMENT_RUNTIME_SWIFT=1 in two headers it always includes
 * (include/CFAvailability.h:11 and internalInclude/CoreFoundation_Prefix.h:11).
 * There is no "plain C CoreFoundation" build: the tree assumes a
 * Swift runtime and a Swift Foundation sit underneath it.
 *
 * What that actually costs a pure-C client is small and enumerable -- eight
 * symbols, all of which exist so CF can hand an object back to Swift:
 *
 *   _CF_CONSTANT_STRING_SWIFT_CLASS   the isa every CFSTR() literal carries.
 *                                     CF compares against its ADDRESS and
 *                                     treats a match as "a native constant
 *                                     string, not a Swift object"
 *                                     (CFRuntime.c:1816), so a dummy object
 *                                     of the right name is exactly right.
 *   NSNumber / __NSCFBoolean classes  the same trick for the constant
 *                                     CFNumbers and kCFBoolean{True,False}.
 *   _CFIsSwift / __CFSwiftBridge      the "is this object really a Swift
 *                                     one, and if so call through this vtable"
 *                                     pair.  No object here is ever a Swift
 *                                     one: _CFIsSwift returns false and the
 *                                     bridge is never dereferenced.
 *   swift_retain / swift_release      reference counting for those objects.
 *
 * libdispatch_init and the _dispatch_*_4CF hooks CF also calls come from
 * swift-corelibs-libdispatch itself.
 *
 * If any of these were ever really reached it would mean a genuinely Swift
 * object had entered CF, which cannot happen in a C-only process.
 */
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

/* The class objects.  Only their addresses are ever used, as isa values.
   Sized generously so nothing that walks a class header runs off the end. */
#define KCB_CLASS_STUB(sym) void *sym[32] = { 0 }

KCB_CLASS_STUB($s10Foundation19_NSCFConstantStringCN);
KCB_CLASS_STUB($s10Foundation8NSNumberCN);
KCB_CLASS_STUB($s10Foundation13__NSCFBooleanCN);
KCB_CLASS_STUB($s10Foundation10__NSCFTypeCN);
KCB_CLASS_STUB($s10Foundation6NSNullCN);
KCB_CLASS_STUB($s10Foundation13NSMutableDataCN);

/* Swift's heap allocator.  CFRuntime.c routes _CFRuntimeCreateInstance
   through it in DEPLOYMENT_RUNTIME_SWIFT mode.  A Swift HeapObject is a
   metadata pointer followed by the refcount words, and CF then writes its own
   CFRuntimeBase over exactly that; so calloc + store the metadata pointer is
   a faithful stand-in.  Reference counting is a no-op and the process leaks
   -- it is a one-shot builder, and the alternative (implementing Swift's
   side-table refcounts) would buy nothing. */
void *swift_allocObject(void *metadata, size_t requiredSize, size_t requiredAlignmentMask)
{
    size_t align = requiredAlignmentMask + 1;
    void  *p     = NULL;
    if ( align < sizeof(void *) )
        align = sizeof(void *);
    if ( requiredSize % align )
        requiredSize += align - (requiredSize % align);
    if ( posix_memalign(&p, align, requiredSize) != 0 || p == NULL )
        return NULL;
    memset(p, 0, requiredSize);
    *(void **)p = metadata;
    return p;
}
void  swift_retain(void *obj)  { (void)obj; }
void  swift_release(void *obj) { (void)obj; }
void  swift_deallocClassInstance(void *obj, size_t size, size_t mask) { (void)obj; (void)size; (void)mask; }
void  swift_unknownObjectRetain(void *obj)  { (void)obj; }
void  swift_unknownObjectRelease(void *obj) { (void)obj; }

/* Hooks Swift Foundation installs into CF at startup.  They do not exist
   here; __CFInitialize calls them unconditionally. */
void  __CFInitializeSwift(void) { }
void *__CFSwiftGetBaseClass(void) { return NULL; }

/* CFURL.c's _CFURLCreateCurrentDirectoryURL calls it.  Swift Foundation
   defines it (Foundation/FileManager.swift, @_cdecl), so a C-only CF has none. */
typedef unsigned char Boolean;
Boolean _CFGetCurrentDirectory(char *path, int maxlen) { return getcwd(path, maxlen) != NULL; }
