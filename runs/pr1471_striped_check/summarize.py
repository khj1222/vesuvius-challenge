"""Summarise results.json on the numeric verdict, not the chunk-byte hashes.

The zarr chunk payloads are not reproducible byte-for-byte across processes
(blosc splits work by thread), so equality has to be read off the decoded
arrays. Every comparison in results.json carries a full per-level numeric
report whenever the hashes differed, which is every time.
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "work" / "results.json"


def verdict(detail: dict | None) -> tuple[str, int]:
    if detail is None:
        return "n/a", 0
    if detail.get("byte_identical"):
        return "equal", 0
    numeric = detail.get("numeric")
    if numeric is None:
        return "unknown", 0
    mismatched = sum(int(entry.get("mismatched_voxels", 0)) for entry in numeric)
    shape_bad = any(entry.get("reason") for entry in numeric)
    if shape_bad:
        return "SHAPE", mismatched
    return ("equal" if mismatched == 0 else "DIFFER"), mismatched


def main() -> None:
    rows = json.loads(RESULTS.read_text(encoding="utf-8"))
    header = (
        f"{'case':17s} {'variant':17s} {'tiff blocks':>11s} {'streamed h/b':12s} "
        f"{'regression':>10s} {'layout':>10s} {'preexist':>9s} {'h_s':>6s} {'b_s':>6s}"
    )
    print(header)
    print("-" * len(header))
    counts = {"regression": {}, "layout": {}, "preexisting": {}}
    failures = []
    for row in rows:
        if not row.get("head_ok") or not row.get("base_ok"):
            failures.append(row)
            print(
                f"{row['case']:17s} {row['variant']:17s} "
                f"{'':>11s} head_ok={row.get('head_ok')} base_ok={row.get('base_ok')}  "
                f"head_error={row.get('head_error')}"
            )
            continue
        reg, reg_n = verdict(row.get("regression_detail"))
        lay, lay_n = verdict(row.get("layout_detail"))
        pre, pre_n = verdict(row.get("preexisting_detail"))
        for name, value in (("regression", reg), ("layout", lay), ("preexisting", pre)):
            counts[name][value] = counts[name].get(value, 0) + 1
        print(
            f"{row['case']:17s} {row['variant']:17s} {str(row['tiff_blocks']):>11s} "
            f"{str(row['head_streamed'])[:4]}/{str(row['base_streamed'])[:5]:5s} "
            f"{reg:>10s} {lay:>10s} {pre:>9s} "
            f"{row['head_seconds']:6.2f} {row['base_seconds']:6.2f}"
        )
    print()
    for name, tally in counts.items():
        print(f"{name:12s}: {tally}")
    if failures:
        print(f"\nfailed variants: {len(failures)}")
        for row in failures:
            print(f"  {row['case']}/{row['variant']}")
            print(f"    head: ok={row.get('head_ok')} err={row.get('head_error')}")
            print(f"    base: ok={row.get('base_ok')} err={row.get('base_error')}")


if __name__ == "__main__":
    main()
