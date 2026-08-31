#!/usr/bin/env python
"""Measure how much noise separates the aligned and native renderings of one sheet.

The calibration step of docs/21. For each segment that exists in both representations, this
estimates a per-voxel noise proxy the way the trainer would see it -- after the same
robust-MAD normalisation, on the high-frequency residual, which is dominated by noise rather
than by sheet structure -- and reports the extra noise an aligned patch would need for its
high-frequency energy to match a native one:

    sigma_extra = sqrt(max(0, sigma_native^2 - sigma_aligned^2))

Usage
-----
    python tools/measure_representation_noise.py \\
        --segments pherc0139-w035 pherc0139-w039 pherc0139-w040 pherc0139-w041 \\
        --out runs/ink9um_scorecard/representation_noise.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
ALIGNED = REPO / "data" / "ink_9um" / "surface-volumes" / "aligned9"
NATIVE = REPO / "data" / "ink_9um" / "surface-volumes" / "native9"


def robust_mad_normalise(patch: np.ndarray, lower: float = 1.0, upper: float = 99.0) -> np.ndarray:
    """The trainer's normalisation: clip to robust percentiles, centre, scale by MAD."""
    values = patch.astype(np.float32)
    low, high = np.percentile(values, [lower, upper])
    values = np.clip(values, low, high)
    median = float(np.median(values))
    mad = float(np.median(np.abs(values - median)))
    scale = mad * 1.4826 if mad > 0 else 1.0
    return (values - median) / scale


def high_frequency_sigma(plane: np.ndarray) -> float:
    """Standard deviation of the plane minus a 3x3 Gaussian blur of itself."""
    from scipy.ndimage import gaussian_filter

    residual = plane - gaussian_filter(plane, sigma=1.0)
    return float(residual.std())


def sample_planes(path: Path, samples: int, size: int, rng: np.random.Generator) -> list[np.ndarray]:
    import zarr

    group = zarr.open_group(str(path), mode="r")
    key = "0" if "0" in set(group.array_keys()) else sorted(group.array_keys())[0]
    array = group[key]
    z, height, width = array.shape
    planes = []
    attempts = 0
    while len(planes) < samples and attempts < samples * 20:
        attempts += 1
        y0 = int(rng.integers(0, max(1, height - size)))
        x0 = int(rng.integers(0, max(1, width - size)))
        block = np.asarray(array[z // 2, y0:y0 + size, x0:x0 + size])
        if block.shape != (size, size) or block.std() == 0:
            continue  # empty padding outside the sheet
        planes.append(block)
    return planes


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--segments", nargs="+", required=True)
    parser.add_argument("--samples", type=int, default=24)
    parser.add_argument("--size", type=int, default=128, help="Patch size, matching training.")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    rng = np.random.default_rng(args.seed)
    report: dict[str, object] = {
        "samples_per_segment": args.samples, "patch": args.size, "seed": args.seed,
        "method": "std of (patch - gaussian_blur(patch, sigma=1)) after robust-MAD normalisation",
        "segments": {},
    }
    sigma_extra_all = []
    for segment in args.segments:
        entry: dict[str, object] = {}
        sigmas: dict[str, float] = {}
        for family, root in (("aligned", ALIGNED), ("native", NATIVE)):
            # aligned9 holds <segment>.zarr; native9 holds <short>/<volume>.zarr, where
            # the short name drops the scroll prefix (pherc0139-w035 -> w035).
            path = root / f"{segment}.zarr"
            if not path.exists():
                short = segment.split("-", 1)[1] if "-" in segment else segment
                candidates = []
                for folder in (root / segment, root / short):
                    if folder.is_dir():
                        candidates = sorted(folder.glob("*.zarr"))
                        if candidates:
                            break
                if not candidates:
                    entry[family] = f"missing: {path}"
                    continue
                path = candidates[0]
            planes = sample_planes(path, args.samples, args.size, rng)
            values = [high_frequency_sigma(robust_mad_normalise(p)) for p in planes]
            sigmas[family] = float(np.median(values))
            entry[family] = {
                "path": str(path), "planes": len(planes),
                "sigma_hf_median": round(sigmas[family], 5),
                "sigma_hf_p25": round(float(np.percentile(values, 25)), 5),
                "sigma_hf_p75": round(float(np.percentile(values, 75)), 5),
            }
        if "aligned" in sigmas and "native" in sigmas:
            extra = float(np.sqrt(max(0.0, sigmas["native"] ** 2 - sigmas["aligned"] ** 2)))
            entry["sigma_extra"] = round(extra, 5)
            entry["variance_extra"] = round(extra ** 2, 6)
            entry["native_over_aligned"] = round(sigmas["native"] / sigmas["aligned"], 3)
            sigma_extra_all.append(extra)
        report["segments"][segment] = entry

    if sigma_extra_all:
        median_extra = float(np.median(sigma_extra_all))
        report["sigma_extra_median"] = round(median_extra, 5)
        report["variance_extra_median"] = round(median_extra ** 2, 6)
        report["recipe_variance_range_in_use"] = [0.012403473458920844, 0.027729677693590096]
        report["inside_range_already_used"] = bool(
            0.012403473458920844 <= median_extra ** 2 <= 0.027729677693590096
        )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=1), encoding="utf-8")

    for segment, entry in report["segments"].items():
        if isinstance(entry.get("aligned"), dict) and isinstance(entry.get("native"), dict):
            print(f"  {segment}: aligned sigma {entry['aligned']['sigma_hf_median']:.4f}  "
                  f"native {entry['native']['sigma_hf_median']:.4f}  "
                  f"ratio {entry['native_over_aligned']:.2f}  extra {entry['sigma_extra']:.4f}")
    if sigma_extra_all:
        print(f"\n  median sigma_extra {report['sigma_extra_median']:.4f} "
              f"-> variance {report['variance_extra_median']:.5f}")
        print(f"  recipe already uses variance {report['recipe_variance_range_in_use']}")
        print(f"  inside the range already used: {report['inside_range_already_used']}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
