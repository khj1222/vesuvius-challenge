#!/usr/bin/env bash
# Store round trip for tools/ink_sdk_channel.py output: ingest the store folder (sidecars -> channels),
# export, so the exported channels can be compared with the files we wrote. Same image as G1/G2.
# /work = docker volume with /work/src from build_and_test.sh; /data = the store folder (ro); /out = results.
set -euo pipefail
(apt-get update -qq && apt-get install -y -qq --no-install-recommends libsqlite3-dev) >/dev/null 2>&1
if [ ! -f /work/build_store/build.ninja ]; then
  cmake -S /work/src/vc_object_store -B /work/build_store -G Ninja -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
    -DVC_OBJECT_STORE_BUILD_LINKING=OFF -DVC_OBJECT_STORE_BUILD_TESTS=OFF 2>&1 | tail -3
fi
cmake --build /work/build_store --target vc_object_ingest vc_object_export --parallel "${JOBS:-12}" 2>&1 | tail -3
ingest=$(find /work/build_store -name vc_object_ingest -type f -perm -u+x | head -1)
export_=$(find /work/build_store -name vc_object_export -type f -perm -u+x | head -1)
rm -rf /tmp/rt /out/export && mkdir -p /tmp/rt
cp -a /data /tmp/rt/seg
uuid=$(grep -o '"uuid": *"[^"]*"' /tmp/rt/seg/meta.json | sed 's/.*"\([^"]*\)"$/\1/')
echo "surface uuid: $uuid"
"$ingest" --db /tmp/rt/objects.vcobj --author roundtrip --no-progress --surface /tmp/rt/seg
"$export_" --db /tmp/rt/objects.vcobj --uuid "$uuid" --output /tmp/rt/export
cp -a /tmp/rt/export /out/export
ls -la /out/export
