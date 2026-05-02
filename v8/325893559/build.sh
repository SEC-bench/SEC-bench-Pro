#!/bin/bash

rm -rf out/x64.debug

gn gen out/x64.debug --args='is_debug=true is_asan=false dcheck_always_on=true symbol_level=1 v8_enable_slow_dchecks=false target_cpu="x64" v8_target_cpu="x64" use_sysroot=false v8_enable_sandbox=true v8_enable_pointer_compression=true v8_enable_memory_corruption_api=true is_component_build=false'
ninja -C out/x64.debug d8

mkdir -p /out
ln -sf /src/v8/out/x64.debug/d8 /out/d8
ln -sf /src/v8/out/x64.debug/snapshot_blob.bin /out/snapshot_blob.bin
