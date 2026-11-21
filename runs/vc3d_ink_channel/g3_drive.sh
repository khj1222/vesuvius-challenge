#!/usr/bin/env bash
# 2026-11-21: the VC3D panel check through VC3D's agent bridge + xdotool, inside a container started with
# g3_xvfb_start.sh (Xvfb :99). Usage: g3_drive.sh PREFIX  -> /out/screens/PREFIX_*.png
# Same steps as the 2026-11-02 check by hand: open PHerc0841 with the 9.366 um volume, import the
# w00 folder bound at scale 1, activate it, open the Ink Detection dock, open the Detection dropdown.
set -euo pipefail
P=${1:-run}
export DISPLAY=:99
B="python3 /g3_bridge.py"
shot() { xwd -root -silent | convert xwd:- "/out/screens/${P}_$1.png"; }
until ls /root/.vc3d/agent_bridge/ 2>/dev/null | grep -q .; do sleep 2; done
$B ping >/dev/null
$B catalog.list_samples '{}' >/dev/null      # fetches the Open Data manifest the open needs
$B --wait-job catalog.open_sample '{"sampleId":"PHerc0841","resources":{"volumeIds":["20250821151531"]}}' \
  | python3 -c 'import sys,json; d=json.load(sys.stdin); print("open:", d["final"]["result"].get("message"))'
$B volume.select '{"volumeId":"20250821151531"}' >/dev/null
UUID=$($B --wait-job objects.import '{"kind":"surface","path":"/data/20260220213127-w00-local-ink","bind":{"scale":1}}' \
  | python3 -c 'import sys,json; d=json.load(sys.stdin); r=d["final"]["result"]["result"]; print(r["uuids"][0])')
echo "imported: $UUID"
$B segments.activate "{\"segmentId\":\"$UUID\"}" | python3 -c 'import sys,json; d=json.load(sys.stdin); print("active:", d["result"]["segment"]["name"])'
for w in $(xdotool search --onlyvisible --name "Open Data Catalog" 2>/dev/null); do xdotool windowmove $w 1900 1000; done
MAIN=$(xdotool search --onlyvisible --name "Volume Cartographer 3D" | head -1)
xdotool windowsize $MAIN 1920 1080; sleep 3
# Ink Detection dock button. Its x depends on the status-bar text: 420 in the after run; in the before run
# this click opened Transforms, so that run's panel was opened by clicking 420 (close) and then 347.
xdotool mousemove 420 1063 click 1; sleep 3
shot panel
xdotool mousemove 588 577 click 1; sleep 2           # Detection dropdown
shot dropdown
xdotool key Escape
cp /tmp/vc3d.log "/out/vc3d_${P}.log"
