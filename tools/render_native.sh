#!/usr/bin/env bash
# Run the native vc_render_tifxyz and kill it once level 0 is complete and the output has
# been quiet for 60 s -- the 88d4aa8 build renders correctly but can hang at exit.
# Usage: tools/render_native.sh <scroll_dir_on_s3> <volume_zarr> <mesh_dir> <out_zarr> [extra flags...]
set -u
export MSYS_NO_PATHCONV=1
SCROLL="$1"; VOL="$2"; MESH="$3"; OUT="$4"; shift 4
BIN="E:/vesuvius-challenge/data/first_letters/bin/VC3D-88d4aa8/VC3D-88d4aa8-2026-09-18-win64/bin/vc_render_tifxyz.exe"
LOG="${OUT}.render.log"
URL="https://vesuvius-challenge-open-data.s3.amazonaws.com/${SCROLL}/volumes/${VOL}"
START=$(date +%s)
"$BIN" -v "E:/vesuvius-challenge/data/first_letters/cache_native/${SCROLL}.zarr" --remote-url "$URL" \
  -g 0 --scale 1 -s "$MESH" --num-slices 28 --slice-step 1 --zarr-output "$OUT" --cache-gb 8 "$@" > "$LOG" 2>&1 &
PID=$!
while kill -0 $PID 2>/dev/null; do
  sleep 15
  if tr '\r' '\n' < "$LOG" | grep -q "(100%)"; then
    AGE=$(( $(date +%s) - $(stat -c %Y "$LOG") ))
    if [ "$AGE" -ge 60 ] && [ -f "$OUT/0/.zarray" ]; then
      echo "level 0 complete, log quiet ${AGE}s -> killing hung exit" >> "$LOG"; taskkill /PID $PID /F >/dev/null 2>&1; break
    fi
  fi
  if [ $(( $(date +%s) - START )) -gt 3600 ]; then echo "timeout 1h" >> "$LOG"; taskkill /PID $PID /F >/dev/null 2>&1; exit 2; fi
done
wait $PID 2>/dev/null
if [ -f "$OUT/0/.zarray" ] && tr '\r' '\n' < "$LOG" | grep -q "(100%)"; then
  echo "$(( $(date +%s) - START ))s" > "$OUT/_render_done"; echo "done $OUT in $(( $(date +%s) - START ))s"; exit 0
fi
echo "render failed: $OUT"; tail -c 400 "$LOG"; exit 1
