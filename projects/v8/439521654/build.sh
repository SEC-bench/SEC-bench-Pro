#!/bin/bash

rm -rf out/ia32.asan

dpkg --add-architecture i386
apt-get update && apt-get install -y --no-install-recommends xz-utils libc6:i386 libstdc++6:i386 zlib1g:i386
python3 build/linux/sysroot_scripts/install-sysroot.py --arch=i386 || true
gn gen out/ia32.asan --args='is_debug=false is_asan=true dcheck_always_on=false symbol_level=1 v8_enable_slow_dchecks=false target_cpu="x86" v8_target_cpu="x86" use_sysroot=true v8_enable_sandbox=false v8_enable_pointer_compression=false v8_enable_memory_corruption_api=false is_component_build=false'
ninja -C out/ia32.asan d8

mkdir -p /out
ln -sf /src/v8/out/ia32.asan/d8 /out/d8
ln -sf /src/v8/out/ia32.asan/snapshot_blob.bin /out/snapshot_blob.bin
