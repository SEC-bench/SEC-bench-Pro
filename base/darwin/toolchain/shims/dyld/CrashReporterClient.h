/* base/darwin/toolchain/shims/dyld/CrashReporterClient.h
 *
 * <CrashReporterClient.h> ships only in the internal SDK (-lCrashReporterClient
 * in configs/libKernelCollectionBuilder.xcconfig).  lsl/Allocator.cpp and
 * common/Array.h call CRSetCrashLogMessage{,2} on fatal paths purely to attach
 * a string to a crash report.  No-op them.
 */
#ifndef _KCB_SHIM_CRASHREPORTERCLIENT_H
#define _KCB_SHIM_CRASHREPORTERCLIENT_H
#define CRSetCrashLogMessage(x)  ((void)(x))
#define CRSetCrashLogMessage2(x) ((void)(x))
#endif
