#!/usr/bin/env bash
# Runs INSIDE WSL (Ubuntu-24.04). Called by tools/render_wsl.sh; do not call from Windows directly.
# Usage: render_wsl_inner.sh <scroll> <url> <mesh_wsl> <name> <out_wsl> <log_wsl> [extra flags...]
set -u
SCROLL="$1"; URL="$2"; MESH_W="$3"; NAME="$4"; OUT_W="$5"; LOG_W="$6"; shift 6
cd /opt/vc3d || exit 3
mkdir -p render cache logs
LOGW="/opt/vc3d/logs/${NAME}.log"
RENDER="/opt/vc3d/render/${NAME}"
rm -rf "$RENDER"
START=$(date +%s)
./squashfs-root/AppRun vc_render_tifxyz -v "/opt/vc3d/cache/${SCROLL}.zarr" --remote-url "$URL" \
  -g 0 --scale 1 -s "$MESH_W" --num-slices 28 --slice-step 1 \
  --zarr-output "$RENDER" --cache-gb 2 "$@" > "$LOGW" 2>&1 &
PID=$!
while kill -0 "$PID" 2>/dev/null; do
  sleep 10
  if tr '\r' '\n' < "$LOGW" | grep -q '(100%)'; then
    AGE=$(( $(date +%s) - $(stat -c %Y "$LOGW") ))
    if [ "$AGE" -ge 90 ] && [ -f "$RENDER/5/.zarray" ]; then
      echo "level 0-5 complete, quiet ${AGE}s -> kill -9" >> "$LOGW"; kill -9 "$PID" 2>/dev/null; break
    fi
  fi
  if [ $(( $(date +%s) - START )) -gt 3600 ]; then echo "timeout 1h" >> "$LOGW"; kill -9 "$PID" 2>/dev/null; exit 2; fi
done
wait "$PID" 2>/dev/null; echo "exit=$? after $(( $(date +%s) - START ))s" >> "$LOGW"
if [ -f "$RENDER/0/.zarray" ] && [ -f "$RENDER/5/.zarray" ] && tr '\r' '\n' < "$LOGW" | grep -q '(100%)'; then
  rm -rf "$OUT_W" && cp -r "$RENDER" "$OUT_W" && cp "$LOGW" "$LOG_W" && rm -rf "$RENDER" && exit 0
fi
cp "$LOGW" "$LOG_W" 2>/dev/null
exit 1
