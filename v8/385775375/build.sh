#!/bin/bash

rm -rf out/x64.asan

gn gen out/x64.asan --args='is_debug=false is_asan=true dcheck_always_on=false v8_enable_slow_dchecks=false target_cpu="x64" v8_target_cpu="x64" use_sysroot=true v8_enable_sandbox=true v8_enable_pointer_compression=true v8_enable_memory_corruption_api=true v8_static_library=true v8_fuzzilli=false is_component_build=false'
ninja -C out/x64.asan d8

mkdir -p /out
ln -sf /src/v8/out/x64.asan/d8 /out/d8
ln -sf /src/v8/out/x64.asan/snapshot_blob.bin /out/snapshot_blob.bin
