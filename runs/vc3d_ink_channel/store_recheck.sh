#!/usr/bin/env bash
# 2026-11-18: redo every store round trip of docs/37 check 4 with the store tools of villa main 1386f072e
# (schema-22 store, #2546), in main's CI image. The 11-06/11-14 round trips predate #2546.
# /work = docker volume whose /work/src holds villa main 1386f072e (vc_object_store/, vc_reader/), /out = results.
# Inputs (ro): /in/seg = segment_ink v2 store folder, /in/sdk = synthetic bridge channels,
#              /in/real = real ink-sdk mesh-run channels.
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
uuid_of() { grep -o '"uuid": *"[^"]*"' "$1/meta.json" | sed 's/.*"\([^"]*\)"$/\1/'; }

# 1. folder mode: sidecars in the tifxyz folder become channels on ingestion
for name in seg sdk real; do
  echo "=== folder round trip: $name"
  rm -rf /tmp/rt_$name && mkdir -p /tmp/rt_$name
  cp -a /in/$name /tmp/rt_$name/seg
  u=$(uuid_of /tmp/rt_$name/seg); echo "surface uuid: $u"
  "$ingest" --db /tmp/rt_$name/objects.vcobj --author recheck --no-progress --surface /tmp/rt_$name/seg
  "$export_" --db /tmp/rt_$name/objects.vcobj --uuid "$u" --output /tmp/rt_$name/export
  rm -rf /out/$name && mkdir -p /out/$name && cp -a /tmp/rt_$name/export /out/$name/export
  ls /out/$name/export
done

# 2. store mode (segment_ink --target store / G2): surface first, then the channel through --surface-channel
echo "=== store-target round trip"
rm -rf /tmp/rt_target && mkdir -p /tmp/rt_target/surf /out/target/src
cp /in/seg/{x,y,z}.tif /in/seg/meta.json /tmp/rt_target/surf/
cp /in/seg/{x,y,z}.tif /in/seg/ink_reader_v3.tif /out/target/src/
u=$(uuid_of /tmp/rt_target/surf); echo "surface uuid: $u"
"$ingest" --db /tmp/rt_target/objects.vcobj --author recheck --no-progress --surface /tmp/rt_target/surf
"$ingest" --db /tmp/rt_target/objects.vcobj --author recheck --surface-channel "$u" ink_reader_v3 /in/seg/ink_reader_v3.tif
"$export_" --db /tmp/rt_target/objects.vcobj --uuid "$u" --output /tmp/rt_target/export
rm -rf /out/target/export && cp -a /tmp/rt_target/export /out/target/export
ls /out/target/export
