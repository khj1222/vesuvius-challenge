#!/usr/bin/env bash
# 2026-11-21 VC3D panel check driven by the AI assistant at the owner's request.
# Runs inside main's CI image: a virtual X display (Xvfb :99), VC3D on it with the agent bridge on,
# so the catalog open / import / surface selection go through VC3D's own bridge RPCs and only the
# Ink Detection panel dropdown is clicked with xdotool. Screenshots: bridge screenshot.capture or xwd.
set -euo pipefail
(apt-get update -qq && apt-get install -y -qq --no-install-recommends \
   libsqlite3-0 xvfb xdotool x11-apps imagemagick python3 >/dev/null) >/dev/null 2>&1 || true
Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp >/tmp/xvfb.log 2>&1 &
sleep 2
export DISPLAY=:99 QT_QPA_PLATFORM=xcb LANG=C.UTF-8 LIBGL_ALWAYS_SOFTWARE=1
/work/build_app/bin/VC3D --agent-bridge-name g3bridge >/tmp/vc3d.log 2>&1 &
echo "VC3D pid $!"
wait
