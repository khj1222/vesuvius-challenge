#!/usr/bin/env python3
"""Audit a segment's held-out mask for patch-scale adjacency to training pixels.

A held-out split only measures generalisation if the held-out pixels are far
enough from the training pixels that the model cannot have learned them.  At a
128 px training patch, held-out pixels a few tens of pixels from supervised ones
sit inside patches the model saw: it trained on one half of a stroke and is
scored on the other, and on the image context immediately around it.  That is
the failure `make_validation_mask.py` was written to avoid, and this tool checks
whether a mask that already exists avoids it too.

Geometry mode (default) needs only the labels.  It reports the segment's region
structure, how many annotated regions contain both held-out and training pixels,
and the distribution of distances from held-out pixels to the nearest supervised
pixel.  A mask that takes whole regions shows large distances and no shared
regions; a mask cut through regions shows the opposite.

Scoring mode (``--prediction`` / ``--control``) measures whether the adjacency
actually pays.  It splits the held-out pixels into distance strata and scores a
prediction in each.  Raw scores per stratum are not comparable -- strata differ
in ink density and difficulty -- so pass ``--control`` as well: a prediction from
a model that never trained on this segment.  Its scores measure each stratum's
intrinsic difficulty, and the quantity that means something is how much the
trained model's advantage over it grows as held-out pixels get closer to
training ones.

Examples
--------
    python tools/audit_holdout_masks.py data/ink_9um/labels/aligned-.../pherc0139-w016

    python tools/audit_holdout_masks.py <segment_dir> \
        --prediction preds/pherc0139-w016_s42_020000.tif \
        --control    preds/pherc0139-w016_loso0139_42_020000.tif
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

DEFAULT_EDGES = [0, 64, 128, 256]


def centre_slice(path: Path) -> np.ndarray:
    """The annotated z-slice of a label pyramid, as bool.

    Label pyramids in this corpus carry the annotation on one z-slice of a
    shallow stack, and the trainer reads ``shape[0] // 2`` -- same index.
    """
    import zarr

    if not path.exists():
        sys.exit(f"error: missing {path}")
    array = zarr.open(str(path), mode="r")["0"]
    return np.asarray(array[array.shape[0] // 2]) > 0


def best_f1(prediction: np.ndarray, ink: np.ndarray) -> dict:
    """Best F1 over every uint8 threshold, from cumulative histograms."""
    pos = np.bincount(prediction[ink], minlength=256).astype(np.int64)
    neg = np.bincount(prediction[~ink], minlength=256).astype(np.int64)
    tp = pos.sum() - np.concatenate(([0], np.cumsum(pos)[:-1]))
    fp = neg.sum() - np.concatenate(([0], np.cumsum(neg)[:-1]))
    fn = pos.sum() - tp
    denominator = 2 * tp + fp + fn
    f1 = np.where(denominator > 0, 2 * tp / np.maximum(denominator, 1), 0.0)
    best = int(np.argmax(f1))
    return {"f1": float(f1[best]), "threshold": best,
            "precision": float(tp[best] / max(1, tp[best] + fp[best])),
            "recall": float(tp[best] / max(1, tp[best] + fn[best]))}


def strata_masks(held_out, distance, edges):
    """Held-out pixels split by distance to the nearest supervised pixel."""
    bounds = list(edges) + [np.inf]
    out = []
    for low, high in zip(bounds[:-1], bounds[1:]):
        name = f"<{high:g}" if low == 0 else (f">={low:g}" if high == np.inf else f"{low:g}-{high:g}")
        out.append((name, held_out & (distance >= low) & (distance < high)))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("segment_dir", type=Path, help="Segment folder holding the label pyramids")
    ap.add_argument("--patch", type=int, default=128, help="Training patch width in px. Default: 128")
    ap.add_argument("--edges", type=float, nargs="+", default=DEFAULT_EDGES,
                    help="Distance stratum edges in px. Default: 0 64 128 256")
    ap.add_argument("--prediction", type=Path, help="Prediction TIFF from a model trained on this segment")
    ap.add_argument("--control", type=Path,
                    help="Prediction TIFF from a model that never trained on this segment")
    ap.add_argument("--json", type=Path, help="Write the report as JSON")
    args = ap.parse_args(argv)

    from scipy import ndimage

    seg = args.segment_dir.resolve()
    name = seg.name
    supervision = centre_slice(seg / f"{name}_supervision_mask.zarr")
    held_out = centre_slice(seg / f"{name}_validation_mask.zarr")
    ink = centre_slice(seg / f"{name}_inklabels.zarr")

    # The corpus ships held-out as a set disjoint from supervision, so the two
    # together are the segment's whole annotation.
    annotation = supervision | held_out
    labels, region_count = ndimage.label(annotation)
    shared = sum(
        1 for region in range(1, region_count + 1)
        if np.any((labels == region) & held_out) and np.any((labels == region) & supervision)
    )
    distance = ndimage.distance_transform_edt(~supervision)
    d_held = distance[held_out]

    report = {
        "segment": name,
        "annotated_px": int(annotation.sum()),
        "supervised_px": int(supervision.sum()),
        "held_out_px": int(held_out.sum()),
        "held_out_share": float(held_out.sum() / max(1, annotation.sum())),
        "annotated_regions": int(region_count),
        "regions_mixing_held_out_and_training": int(shared),
        "distance_to_training": {
            "min": float(d_held.min()), "p25": float(np.percentile(d_held, 25)),
            "median": float(np.median(d_held)), "p75": float(np.percentile(d_held, 75)),
            "max": float(d_held.max()),
            "within_patch": float(np.count_nonzero(d_held < args.patch) / d_held.size),
            "within_two_patches": float(np.count_nonzero(d_held < 2 * args.patch) / d_held.size),
        },
    }

    print(f"segment            : {name}")
    print(f"annotation         : {report['annotated_px']:,} px in {region_count} regions")
    print(f"  supervised       : {report['supervised_px']:,}")
    print(f"  held out         : {report['held_out_px']:,} ({report['held_out_share']:.1%})")
    print(f"regions holding both held-out and training pixels: {shared}/{region_count}"
          + ("   <- the split cuts through annotated regions" if shared else "   <- whole regions"))
    d = report["distance_to_training"]
    print(f"distance from held-out pixels to the nearest training pixel:")
    print(f"  min {d['min']:.0f} | p25 {d['p25']:.0f} | median {d['median']:.0f}"
          f" | p75 {d['p75']:.0f} | max {d['max']:.0f}")
    print(f"  within one patch ({args.patch} px) : {d['within_patch']:.1%}")
    print(f"  within two patches               : {d['within_two_patches']:.1%}")

    if args.prediction:
        import tifffile

        prediction = tifffile.imread(str(args.prediction))
        if prediction.shape != supervision.shape:
            sys.exit(f"error: prediction is {prediction.shape}, labels are {supervision.shape}")
        control = None
        if args.control:
            control = tifffile.imread(str(args.control))
            if control.shape != supervision.shape:
                sys.exit(f"error: control is {control.shape}, labels are {supervision.shape}")

        rows = []
        print(f"\n{'stratum':>10} {'px':>9} {'ink':>7} {'model':>8}"
              + (f" {'control':>8} {'gain':>8}" if control is not None else ""))
        for stratum, mask in strata_masks(held_out, distance, args.edges):
            count = int(mask.sum())
            if count == 0:
                continue
            density = float(ink[mask].mean())
            if density == 0:
                print(f"{stratum:>10} {count:>9,} {density:>7.4f}   no ink -- F1 undefined here")
                rows.append({"stratum": stratum, "px": count, "ink_density": density, "scorable": False})
                continue
            scored = best_f1(prediction[mask], ink[mask])
            row = {"stratum": stratum, "px": count, "ink_density": density,
                   "scorable": True, "model": scored}
            line = f"{stratum:>10} {count:>9,} {density:>7.4f} {scored['f1']:>8.4f}"
            if control is not None:
                control_scored = best_f1(control[mask], ink[mask])
                row["control"] = control_scored
                row["gain"] = scored["f1"] - control_scored["f1"]
                line += f" {control_scored['f1']:>8.4f} {row['gain']:>+8.4f}"
            rows.append(row)
            print(line)
        report["strata"] = rows

        scorable = [r for r in rows if r.get("scorable") and "gain" in r]
        if len(scorable) >= 2:
            near, far = scorable[0], scorable[-1]
            excess = near["gain"] - far["gain"]
            report["excess_gain_nearest_over_farthest"] = excess
            print(f"\nexcess gain of {near['stratum']} over {far['stratum']}: {excess:+.4f} F1")
            print("  (the advantage of having trained on this segment, in excess of what the same"
                  "\n   advantage is worth on the farthest held-out pixels -- adjacency, not skill)")

    if args.json:
        args.json.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nreport -> {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
