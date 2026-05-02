#!/bin/bash

rm -rf out/x64.release

gn gen out/x64.release --args='is_debug=false is_asan=false dcheck_always_on=false target_cpu="x64" v8_target_cpu="x64" use_sysroot=false v8_enable_sandbox=true v8_enable_backtrace=true v8_enable_disassembler=true v8_enable_object_print=true v8_enable_verify_heap=true is_component_build=false'
ninja -C out/x64.release d8

mkdir -p /out
ln -sf /src/v8/out/x64.release/d8 /out/d8
ln -sf /src/v8/out/x64.release/snapshot_blob.bin /out/snapshot_blob.bin
