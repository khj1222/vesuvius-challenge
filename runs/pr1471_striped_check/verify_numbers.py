"""Re-derive every figure quoted in submission/pr1471_reply_jaideepsaipadhi.md.

Run from the repository root. Recomputes each number from the raw artifacts in
this directory and asserts that the string it produces appears in the draft, so
a number cannot drift from its evidence without this failing.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DRAFT = HERE.parent.parent / "submission" / "pr1471_reply_jaideepsaipadhi.md"

checks: list[tuple[str, str, bool]] = []


def check(name: str, value: str, present: bool | None = None) -> None:
    text = DRAFT.read_text(encoding="utf-8")
    ok = (value in text) if present is None else present
    checks.append((name, value, ok))


def verdict(detail: dict | None) -> str:
    if detail is None:
        return "n/a"
    if detail.get("byte_identical"):
        return "equal"
    numeric = detail.get("numeric")
    if numeric is None:
        return "unknown"
    if any(entry.get("reason") for entry in numeric):
        return "SHAPE"
    return "equal" if sum(int(e.get("mismatched_voxels", 0)) for e in numeric) == 0 else "DIFFER"


# ---------------------------------------------------------------- matrix
rows = json.loads((HERE / "results_matrix.json").read_text(encoding="utf-8"))
both = [r for r in rows if r.get("head_ok") and r.get("base_ok")]
crashed = [r for r in rows if not r.get("head_ok")]
levels = sum(len(r["regression_detail"].get("numeric") or []) for r in both if r.get("regression_detail"))
voxels = sum(
    sum(int(e["voxels"]) for e in (r["regression_detail"].get("numeric") or []))
    for r in both if r.get("regression_detail")
)
mismatched = sum(
    sum(int(e.get("mismatched_voxels", 0)) for e in (r["regression_detail"].get("numeric") or []))
    for r in both if r.get("regression_detail")
)
check("matrix variants", str(len(rows)))
check("matrix compared on both trees", str(len(both)))
check("matrix head-only crashes", str(len(crashed)))
check("matrix level comparisons", str(levels))
check("matrix voxels compared", f"{voxels:,}")
check("matrix regression mismatches == 0", "zero mismatches", mismatched == 0)
assert all(verdict(r.get("regression_detail")) == "equal" for r in both), "a regression comparison is not equal"
assert all(r.get("base_ok") for r in crashed), "a head crash also failed on the parent"
assert all(len(r["regression_detail"].get("numeric") or []) == 6 for r in both), "a comparison did not cover six levels"
jpeg = next(r for r in rows if r["codec"] == "jpeg")
assert jpeg["head_streamed"] == "false" and jpeg["base_streamed"] == "false", "jpeg did not fall through on both trees"
assert verdict(jpeg.get("regression_detail")) == "equal", "jpeg fallback output differs between trees"

# ---------------------------------------------------------------- one-row-strip
fix_rows = json.loads((HERE / "results_onerow_fix.json").read_text(encoding="utf-8"))
head_crash = [r for r in fix_rows if not r["head_ok"]]
fix_crash = [r for r in fix_rows if not r["headfix_ok"]]
comparable = [r for r in fix_rows if r["fix_vs_base"] != "n/a"]
check("fix-run variants", str(len(fix_rows)))
check("fix-run head crashes", str(len(head_crash)))
check("fix-run headfix crashes", str(len(fix_crash)))
check("fix-run comparable outputs", str(len(comparable)))
assert all(r["fix_vs_base"] == "equal" for r in comparable), "a fixed output is not equal to base"
# the two non-rowsperstrip-1 triggers quoted in the draft
for case, layout in (("mod1_256", "strip256"), ("mod1_16", "strip16")):
    row = next(r for r in fix_rows if r["case"] == case and r["layout"] == layout)
    assert not row["head_ok"], f"{case}/{layout} was expected to crash on head"
    tiled = next(r for r in fix_rows if r["case"] == case and r["layout"] == "tiled256")
    assert tiled["head_ok"], f"{case}/tiled256 was expected to convert"
check("trigger 513x1027 @256", "513×1027 at `rowsperstrip=256`")
check("trigger 2049x1027 @16", "2049×1027 at `rowsperstrip=16`")

# ---------------------------------------------------------------- decode shapes
probe = [json.loads(line) for line in (HERE / "probe_decode_shapes.jsonl").read_text(encoding="utf-8").splitlines() if line.startswith("{")]
by_case = {p["case"]: p for p in probe}
first = by_case["odd_odd/strip1024"]["strips"][0]
last = by_case["odd_odd/strip1024"]["strips"][1]
seven = by_case["odd_odd/strip7"]["strips"][1]
check("decode full strip", "(1, %d, %d, 1)" % (first["decoded_shape"][1], first["decoded_shape"][2]))
check("decode one-row strip", "(1, %d, %d, 1)" % (last["decoded_shape"][1], last["decoded_shape"][2]))
check("decode 5-row remainder", "(1, %d, %d, 1)" % (seven["decoded_shape"][1], seven["decoded_shape"][2]))
assert isinstance(last["normalize_to_2d"], str) and "ValueError" in last["normalize_to_2d"]
assert seven["normalize_to_2d"] == [5, 2051]

# ---------------------------------------------------------------- real file
inputs = json.loads((HERE / "real_inputs.json").read_text(encoding="utf-8"))
height, width = inputs["shape"]
check("real height x width", f"{height}×{width}")
check("real tiles", f"{inputs['layouts']['tiled256']['n_blocks']:,}")
check("real strips", str(inputs["layouts"]["strip1024"]["n_blocks"]))
check("real tiled file MB", f"{inputs['layouts']['tiled256']['file_mb']:.2f} MB")
check("real striped file MB", f"{inputs['layouts']['strip1024']['file_mb']:.2f} MB")

timings = {}
for line in (HERE / "real_timings.jsonl").read_text(encoding="utf-8").splitlines():
    if line.startswith("{"):
        record = json.loads(line)
        timings[record["label"]] = record
for label, key in (
    ("head/tiled256", "tiled"),
    ("head/strip1024", "striped"),
    ("head+fullwidth-blocks/strip1024", "fullwidth"),
    ("merge-ink-pipelines(#1234)/strip1024", "merged"),
):
    record = timings[label]
    check(f"{key} seconds", f"{record['seconds']:.2f} s")
    check(f"{key} peak rss", f"{record['peak_rss_gib']:.3f} GiB")

equality = [json.loads(line) for line in (HERE / "real_equality.jsonl").read_text(encoding="utf-8").splitlines() if line.startswith("{")]
for report in equality:
    assert report["equal"], f"real comparison not equal: {report['label']}"
    assert all(e["mismatched_pixels"] == 0 for e in report["levels"])
nonzero = [e["nonzero_pixels_left"] for e in equality[0]["levels"]]
check("real nonzero per level", " / ".join(f"{n:,}" for n in nonzero))

# ---------------------------------------------------------------- derived ratios
tiled_s = timings["head/tiled256"]["seconds"]
striped_s = timings["head/strip1024"]["seconds"]
full_s = timings["head+fullwidth-blocks/strip1024"]["seconds"]
merged_s = timings["merge-ink-pipelines(#1234)/strip1024"]["seconds"]
merged_rss = timings["merge-ink-pipelines(#1234)/strip1024"]["peak_rss_gib"]
striped_rss = timings["head/strip1024"]["peak_rss_gib"]
check("striped slower than tiled by", f"{round((striped_s - tiled_s) / tiled_s * 100)}%")
check("wall ratio vs merged", f"{striped_s / merged_s:.1f}x")
check("rss ratio vs merged", f"{merged_rss / striped_rss:.1f}x")
check("fullwidth ratio vs merged", f"{full_s / merged_s:.1f}x")
check("gap closed", f"{round((striped_s - full_s) / (striped_s - merged_s) * 100)}%")
horizontal_blocks = math.ceil(width / 1024)
check("horizontal blocks", f"{horizontal_blocks} times")
check("32249 mod 1024", f"{height} mod 1024 = {height % 1024}")
check("32249 mod 7", f"{height} mod 7 = {height % 7}")
check("32249 mod 8", f"{height} mod 8 = {height % 8}")

# ---------------------------------------------------------------- report
failed = [c for c in checks if not c[2]]
width_name = max(len(c[0]) for c in checks)
for name, value, ok in checks:
    print(f"{'ok ' if ok else 'MISS'} {name:{width_name}s}  {value}")
print()
print(f"{len(checks) - len(failed)}/{len(checks)} figures verified against artifacts")
if failed:
    print("MISSING FROM DRAFT:")
    for name, value, _ in failed:
        print(f"  {name}: {value!r}")
    sys.exit(1)
