#!/usr/bin/env bash
# Render one tifxyz mesh with the Linux VC3D build inside WSL (Ubuntu-24.04), where a renderer
# that hangs at exit can actually be killed (the Windows build leaves an unkillable 4 GB zombie
# per render -- docs/25 section 8). The work happens in tools/render_wsl_inner.sh, run from
# /mnt/e so no script text crosses the wsl.exe argument boundary (it mangles quotes).
# Usage: tools/render_wsl.sh <scroll_dir_on_s3> <volume_zarr> <mesh_dir_E_posix> <out_zarr_E_posix> [extra flags...]
set -u
SCROLL="$1"; VOL="$2"; MESH="$3"; OUT="$4"; shift 4
to_wsl() { echo "$1" | sed -E 's#^([A-Za-z]):/#/mnt/\L\1/#'; }
MESH_W=$(to_wsl "$MESH"); OUT_W=$(to_wsl "$OUT")
NAME=$(basename "$OUT")
LOG="${OUT}.render.log"; LOG_W=$(to_wsl "$LOG")
URL="https://vesuvius-challenge-open-data.s3.amazonaws.com/${SCROLL}/volumes/${VOL}"
START=$(date +%s)
wsl -d Ubuntu-24.04 -- bash /mnt/e/vesuvius-challenge/tools/render_wsl_inner.sh "$SCROLL" "$URL" "$MESH_W" "$NAME" "$OUT_W" "$LOG_W" "$@"
RC=$?
if [ "$RC" -eq 0 ] && [ -f "$OUT/0/.zarray" ]; then
  echo "$(( $(date +%s) - START ))s (wsl)" > "$OUT/_render_done"; echo "done $OUT in $(( $(date +%s) - START ))s"; exit 0
fi
echo "render failed (rc=$RC): $OUT"; tail -c 400 "$LOG" 2>/dev/null; exit 1
