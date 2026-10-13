/* base/darwin/toolchain/shims/dyld/cfstring_compat.h
 *
 * Force-included (-include) into kernel-collection-builder/dyld_app_cache_util.cpp
 * ONLY.  It is not a missing-header shim: it works around a real latent bug in
 * Apple's open-source CLI driver.
 *
 * dyld_app_cache_util.cpp calls CFStringGetCStringPtr(s, kCFStringEncodingASCII)
 * in seven places and uses the result without a NULL check --
 * CFBundleGetIdentifier(), CFURLCopyFileSystemPath() for the executable, the
 * bundle URL and the PlugIns URL, and the OSBundleLibraries dependency keys.
 * CFStringGetCStringPtr is documented to return NULL whenever the string is not
 * *already* stored in the requested encoding, which is exactly what happens for
 * the CFStrings CFURLCopyFileSystemPath hands back on macOS 26: the tool
 * segfaults in std::string::operator=(const char*) at
 * dyld_app_cache_util.cpp:1188 (`bundleData.executablePath = bundleExecutablePath`)
 * on the first kext in a KDK's System/Library/Extensions.
 *
 * Rather than patch Apple's source, redirect the call through a wrapper that
 * falls back to CFStringGetCString into a heap buffer.  Callers treat the
 * result as a borrowed interior pointer and never free it, so the fallback
 * buffer is intentionally leaked; the tool is a one-shot process and the total
 * stays small.
 */
#ifndef _KCB_SHIM_CFSTRING_COMPAT_H
#define _KCB_SHIM_CFSTRING_COMPAT_H

/* CFString.h, not the CoreFoundation.h umbrella: the umbrella pulls in
 * ForSwiftFoundationOnly.h, whose __has_include(<malloc/malloc.h>) would find
 * the SDK's copy through -idirafter and drag Darwin's libc types in. */
#include <CoreFoundation/CFString.h>
#include <stdlib.h>

static inline const char *kcb_CFStringGetCStringPtr(CFStringRef s, CFStringEncoding encoding)
{
    if ( s == NULL )
        return NULL;
    const char *p = CFStringGetCStringPtr(s, encoding);
    if ( p != NULL )
        return p;
    CFIndex len = CFStringGetLength(s);
    CFIndex max = CFStringGetMaximumSizeForEncoding(len, kCFStringEncodingUTF8) + 1;
    char *buf = (char *)malloc((size_t)max);
    if ( buf == NULL )
        return NULL;
    if ( !CFStringGetCString(s, buf, max, kCFStringEncodingUTF8) ) {
        free(buf);
        return NULL;
    }
    return buf;   /* deliberately leaked; see comment above */
}

#define CFStringGetCStringPtr kcb_CFStringGetCStringPtr

#endif /* _KCB_SHIM_CFSTRING_COMPAT_H */
