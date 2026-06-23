#!/bin/bash

rm -rf out/x64.asan

gn gen out/x64.asan --args='is_debug=false is_asan=true dcheck_always_on=false target_cpu="x64" is_component_build=false v8_enable_sandbox=true v8_enable_memory_corruption_api=true v8_enable_google_benchmark=true v8_enable_test_features=true v8_enable_undefined_double=true v8_no_inline=true'
ninja -C out/x64.asan d8

mkdir -p /out
ln -sf /src/v8/out/x64.asan/d8 /out/d8
ln -sf /src/v8/out/x64.asan/snapshot_blob.bin /out/snapshot_blob.bin
