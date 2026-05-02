#!/bin/bash

rm -rf out/x64.release

mkdir -p out/x64.release
curl -L -o out/x64.release/d8 'https://issues.chromium.org/action/issues/334120897/attachments/55482930?download=true'
curl -L -o out/x64.release/snapshot_blob.bin 'https://issues.chromium.org/action/issues/334120897/attachments/55482932?download=true'
chmod +x out/x64.release/d8

mkdir -p /out
ln -sf /src/v8/out/x64.release/d8 /out/d8
ln -sf /src/v8/out/x64.release/snapshot_blob.bin /out/snapshot_blob.bin
