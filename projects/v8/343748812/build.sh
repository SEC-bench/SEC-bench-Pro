#!/bin/bash

rm -rf out/arm64.debug.asan

gn gen out/arm64.debug.asan --args='is_debug=true is_asan=true dcheck_always_on=true v8_enable_slow_dchecks=true target_cpu="x64" v8_target_cpu="arm64" use_sysroot=false v8_enable_sandbox=false v8_enable_pointer_compression=false is_component_build=false'
ninja -C out/arm64.debug.asan d8

mkdir -p /out
ln -sf /src/v8/out/arm64.debug.asan/d8 /out/d8
ln -sf /src/v8/out/arm64.debug.asan/snapshot_blob.bin /out/snapshot_blob.bin
