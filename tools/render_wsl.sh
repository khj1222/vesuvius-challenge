#!/usr/bin/env bash
# Render one tifxyz mesh with the Linux VC3D build inside WSL (Ubuntu-24.04), where a renderer
# that hangs at exit can actually be killed (the Windows build leaves an unkillable 4 GB zombie
# per render -- docs/25 section 8). Output is rendered to WSL-local disk and then copied to E:.
# Usage: tools/render_wsl.sh <scroll_dir_on_s3> <volume_zarr> <mesh_dir_E_posix> <out_zarr_E_posix> [extra flags...]
#   paths are given in Git-Bash form (E:/...) and translated to /mnt/e/... here.
set -u
SCROLL="$1"; VOL="$2"; MESH="$3"; OUT="$4"; shift 4
to_wsl() { echo "$1" | sed -E 's#^([A-Za-z]):/#/mnt/\L\1/#'; }
MESH_W=$(to_wsl "$MESH"); OUT_W=$(to_wsl "$OUT")
NAME=$(basename "$OUT")
LOG="${OUT}.render.log"
EXTRA="$*"
URL="https://vesuvius-challenge-open-data.s3.amazonaws.com/${SCROLL}/volumes/${VOL}"
START=$(date +%s)
# run inside WSL: render to /opt/vc3d/render/<name>, kill if it lingers >90 s after 100%, copy out
wsl -d Ubuntu-24.04 -- bash -c "
set -u
cd /opt/vc3d && mkdir -p render cache logs
LOGW=/opt/vc3d/logs/${NAME}.log
rm -rf /opt/vc3d/render/${NAME}
./squashfs-root/AppRun vc_render_tifxyz -v /opt/vc3d/cache/${SCROLL}.zarr --remote-url '${URL}' \
  -g 0 --scale 1 -s '${MESH_W}' --num-slices 28 --slice-step 1 \
  --zarr-output /opt/vc3d/render/${NAME} --cache-gb 2 ${EXTRA} > \"\$LOGW\" 2>&1 &
PID=\$!
while kill -0 \$PID 2>/dev/null; do
  sleep 10
  if tr '\r' '\n' < \"\$LOGW\" | grep -q '(100%)'; then
    AGE=\$(( \$(date +%s) - \$(stat -c %Y \"\$LOGW\") ))
    if [ \"\$AGE\" -ge 90 ] && [ -f /opt/vc3d/render/${NAME}/5/.zarray ]; then
      echo 'level 0-5 complete, quiet 90s -> kill' >> \"\$LOGW\"; kill -9 \$PID 2>/dev/null; break
    fi
  fi
  if [ \$(( \$(date +%s) - $START )) -gt 3600 ]; then echo 'timeout 1h' >> \"\$LOGW\"; kill -9 \$PID 2>/dev/null; exit 2; fi
done
wait \$PID 2>/dev/null; echo \"exit=\$?\" >> \"\$LOGW\"
if [ -f /opt/vc3d/render/${NAME}/0/.zarray ] && [ -f /opt/vc3d/render/${NAME}/5/.zarray ] && tr '\r' '\n' < \"\$LOGW\" | grep -q '(100%)'; then
  rm -rf '${OUT_W}' && cp -r /opt/vc3d/render/${NAME} '${OUT_W}' && cp \"\$LOGW\" '$(to_wsl "$LOG")' && rm -rf /opt/vc3d/render/${NAME} && exit 0
fi
cp \"\$LOGW\" '$(to_wsl "$LOG")' 2>/dev/null; exit 1
"
RC=$?
if [ "$RC" -eq 0 ] && [ -f "$OUT/0/.zarray" ]; then
  echo "$(( $(date +%s) - START ))s (wsl)" > "$OUT/_render_done"; echo "done $OUT in $(( $(date +%s) - START ))s"; exit 0
fi
echo "render failed (rc=$RC): $OUT"; tail -c 400 "$LOG" 2>/dev/null; exit 1
