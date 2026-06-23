#!/bin/bash

rm -rf out/x64.release

mkdir -p out/x64.release /tmp/d8bin
curl -L -o /tmp/d8.zip https://storage.googleapis.com/v8-asan/linux-release/d8-sandbox-testing-linux-release-v8-component-102149.zip
python3 -c "import zipfile; zipfile.ZipFile('/tmp/d8.zip').extractall('/tmp/d8bin')"
cp /tmp/d8bin/d8 out/x64.release/d8
cp /tmp/d8bin/snapshot_blob.bin out/x64.release/snapshot_blob.bin
chmod +x out/x64.release/d8
rm -rf /tmp/d8.zip /tmp/d8bin

mkdir -p /out
ln -sf /src/v8/out/x64.release/d8 /out/d8
ln -sf /src/v8/out/x64.release/snapshot_blob.bin /out/snapshot_blob.bin
