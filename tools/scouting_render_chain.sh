#!/usr/bin/env bash
# Render one tifxyz mesh with the :edge container, chaining --timeout/--resume runs until a
# clean exit (docs/16: the old build stalls at random points). Usage:
#   tools/scouting_render_chain.sh <scroll_prefix> <volume_zarr_name> <mesh_dir_under_/work> <out_zarr_under_/work> [max_attempts]
set -u
export MSYS_NO_PATHCONV=1   # Git Bash would rewrite /work/... into C:/Program Files/Git/work/...
SCROLL="$1"; VOL="$2"; MESH="$3"; OUT="$4"; MAX="${5:-10}"
URL="https://vesuvius-challenge-open-data.s3.amazonaws.com/${SCROLL}/volumes/${VOL}"
for i in $(seq 1 "$MAX"); do
  echo "$(date +%H:%M:%S) attempt $i"
  RESUME=""; [ -d "E:/vesuvius-challenge/data/first_letters/${OUT}/0" ] && RESUME="--resume"   # --resume on a missing output crashes at startup
  docker run --rm -e OMP_NUM_THREADS=4 -v E:/vesuvius-challenge/data/first_letters:/work \
    ghcr.io/scrollprize/villa/volume-cartographer:edge \
    vc_render_tifxyz -v "/work/cache/${SCROLL}.zarr" --remote-url "$URL" \
      -g 0 --scale 1 -s "/work/${MESH}" --num-slices 28 --slice-step 1 \
      --zarr-output "/work/${OUT}" --cache-gb 8 $RESUME --timeout 8
  rc=$?
  echo "$(date +%H:%M:%S) attempt $i exit=$rc"
  if [ "$rc" -eq 0 ]; then echo "done after $i attempt(s)"; exit 0; fi
done
echo "gave up after $MAX attempts"; exit 1
