#!/bin/bash
# Build 1: ASAN+debug
rm -rf obj-debug-asan
rm -f mozconfig .mozconfig && cat > .mozconfig <<'EOF'
ac_add_options --enable-address-sanitizer
ac_add_options --disable-jemalloc
ac_add_options --enable-optimize="-O1"
ac_add_options --enable-debug
ac_add_options --enable-debug-symbols
ac_add_options --enable-application=js
ac_add_options --disable-bootstrap
mk_add_options MOZ_OBJDIR=@TOPSRCDIR@/obj-debug-asan
EOF
./mach build

# Build 2: Release
rm -rf obj-release
rm -f mozconfig .mozconfig && cat > .mozconfig <<'EOF'
ac_add_options --enable-optimize
ac_add_options --disable-debug
ac_add_options --enable-application=js
ac_add_options --disable-bootstrap
mk_add_options MOZ_OBJDIR=@TOPSRCDIR@/obj-release
EOF
./mach build

mkdir -p /out
ln -sf /src/gecko-dev/obj-debug-asan/dist/bin/js /out/js
ln -sf /src/gecko-dev/obj-release/dist/bin/js /out/js-release
