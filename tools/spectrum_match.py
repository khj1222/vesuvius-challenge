#!/usr/bin/env python3
"""Measure and compare the spatial frequency content of surface volumes.

Cross-scroll transfer fails in a way that per-patch intensity normalisation
cannot explain: the model normalises every patch by a robust median and MAD and
then normalises again with InstanceNorm, so a difference in brightness or
contrast between two scrolls is already gone by the time a convolution sees it.
What those steps do *not* remove is a difference in how much of the signal sits
at each spatial frequency -- the blur and noise spectrum left behind by how the
volume was acquired and rendered.

There is direct evidence that this matters. On the same physical segments, the
``aligned`` representation (a 2.399 um acquisition pooled 4x in z, level-2 in
XY) transfers better than the ``native`` one (a single 9.362 um acquisition) by
+0.03 to +0.07 F1, and the advantage survives training on both families
(``docs/15`` appendix 2). Their pixel sizes are within 3% of each other, so what
differs is the spectrum, not the sampling.

This tool measures that spectrum. ``estimate`` draws windowed patches from a
surface volume, takes each one's radial power profile, and averages them;
``compare`` puts two profiles side by side and reports the filter that would
carry one onto the other.

Profiles are **shape-normalised**: each patch's spectrum is divided by its own
total power with DC excluded. That makes the measurement invariant to exactly
the brightness and contrast differences the model already removes, so what is
left is only the part that could actually matter.

Examples
--------
    python tools/spectrum_match.py estimate \
        data/ink_9um/surface-volumes/aligned9/phercparis4-w00.zarr \
        --out runs/spectra/paris4_aligned.json --patches 256

    python tools/spectrum_match.py compare \
        runs/spectra/aligned.json runs/spectra/native.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np


def open_volume(path: Path):
    """Open a surface volume zarr and return its level-0 array."""
    import zarr

    if not path.exists():
        sys.exit(f"error: missing {path}")
    store = zarr.open(str(path), mode="r")
    if hasattr(store, "array_keys") and "0" in list(store.array_keys()):
        return store["0"]
    return store


def radial_bins(size: int):
    """Map each rank-2 FFT bin to a radial index, and give the bin centres."""
    freq = np.fft.fftfreq(size)
    fy, fx = np.meshgrid(freq, freq, indexing="ij")
    radius = np.sqrt(fy ** 2 + fx ** 2)
    # Bin to the Nyquist limit; the corners beyond it are anisotropic and dropped.
    n_bins = size // 2
    index = np.clip((radius * 2 * n_bins).astype(np.int32), 0, n_bins)
    centres = (np.arange(n_bins + 1) + 0.5) / (2 * n_bins)
    return index, n_bins, centres


def patch_profile(patch: np.ndarray, window: np.ndarray, index, n_bins) -> np.ndarray | None:
    """Shape-normalised radial power profile of one patch, or None if it is flat."""
    field = patch.astype(np.float64)
    field -= field.mean()
    spread = field.std()
    if spread <= 0:
        return None
    field /= spread
    power = np.abs(np.fft.fft2(field * window)) ** 2
    total = np.bincount(index.ravel(), weights=power.ravel(), minlength=n_bins + 1)
    counts = np.bincount(index.ravel(), minlength=n_bins + 1)
    profile = total / np.maximum(counts, 1)
    profile[0] = 0.0  # DC carries the brightness we deliberately ignore
    mass = profile.sum()
    if mass <= 0:
        return None
    return profile / mass


def estimate(args) -> int:
    array = open_volume(args.volume)
    depth, height, width = array.shape[-3:]
    z = args.z if args.z is not None else depth // 2
    if not 0 <= z < depth:
        sys.exit(f"error: --z {z} outside the volume's {depth} slices")
    size = args.patch
    if height < size or width < size:
        sys.exit(f"error: volume is {height}x{width}, smaller than --patch {size}")

    window = np.outer(np.hanning(size), np.hanning(size))
    index, n_bins, centres = radial_bins(size)
    rng = np.random.default_rng(args.seed)

    accumulated = np.zeros(n_bins + 1)
    kept = attempts = 0
    # Sample on the chunk grid: reads stay aligned and no patch straddles chunks.
    max_y, max_x = (height - size) // size, (width - size) // size
    while kept < args.patches and attempts < args.patches * args.max_attempts:
        attempts += 1
        y = int(rng.integers(0, max_y + 1)) * size
        x = int(rng.integers(0, max_x + 1)) * size
        patch = np.asarray(array[z, y:y + size, x:x + size])
        # Off-sheet pixels are exactly zero in a render; skip mostly-blank patches.
        if np.count_nonzero(patch) < args.min_valid * patch.size:
            continue
        profile = patch_profile(patch, window, index, n_bins)
        if profile is None:
            continue
        accumulated += profile
        kept += 1

    if kept == 0:
        sys.exit("error: no usable patch found -- try lowering --min-valid")
    profile = accumulated / kept

    report = {
        "volume": str(args.volume),
        "z": z,
        "patch": size,
        "patches_kept": kept,
        "patches_attempted": attempts,
        "min_valid": args.min_valid,
        "seed": args.seed,
        "frequency": centres.tolist(),
        "power": profile.tolist(),
    }
    print(f"volume        : {args.volume}")
    print(f"shape         : {array.shape}, sampled z={z}")
    print(f"patches       : {kept} kept of {attempts} attempted ({size}x{size})")
    print(f"spectral centroid : {float((centres * profile).sum() / profile.sum()):.4f}"
          f"  (cycles/px; higher = sharper, noisier)")
    for label, lo, hi in (("low  f<0.1", 0.0, 0.1), ("mid  0.1-0.25", 0.1, 0.25),
                          ("high f>0.25", 0.25, 1.0)):
        share = profile[(centres >= lo) & (centres < hi)].sum()
        print(f"  {label:<14} {share:6.1%} of the power")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"profile -> {args.out}")
    return 0


def compare(args) -> int:
    source = json.loads(args.source.read_text(encoding="utf-8"))
    target = json.loads(args.target.read_text(encoding="utf-8"))
    if source["patch"] != target["patch"]:
        sys.exit("error: profiles were measured at different patch sizes")

    freq = np.asarray(source["frequency"])
    s = np.asarray(source["power"])
    t = np.asarray(target["power"])
    floor = args.floor * max(s.max(), t.max())
    gain = np.sqrt(np.maximum(s, floor) / np.maximum(t, floor))
    gain = np.clip(gain, 1 / args.max_gain, args.max_gain)

    centroid_s = float((freq * s).sum() / s.sum())
    centroid_t = float((freq * t).sum() / t.sum())
    print(f"source : {source['volume']}")
    print(f"target : {target['volume']}")
    print(f"\nspectral centroid  source {centroid_s:.4f}  target {centroid_t:.4f}"
          f"  ratio {centroid_t / centroid_s:.3f}")
    divergence = float(np.abs(s - t).sum() / 2)
    print(f"total variation between the profiles: {divergence:.4f}"
          f"   (0 = identical, 1 = disjoint)")

    print(f"\n{'freq':>7} {'source':>10} {'target':>10} {'target/source':>14} {'filter':>8}")
    step = max(1, len(freq) // args.rows)
    for i in range(0, len(freq), step):
        ratio = t[i] / s[i] if s[i] > 0 else float("inf")
        print(f"{freq[i]:>7.3f} {s[i]:>10.3e} {t[i]:>10.3e} {ratio:>14.3f} {gain[i]:>8.3f}")

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps({
            "source": source["volume"], "target": target["volume"],
            "patch": source["patch"], "floor": args.floor, "max_gain": args.max_gain,
            "spectral_centroid": {"source": centroid_s, "target": centroid_t},
            "total_variation": divergence,
            "frequency": freq.tolist(), "gain": gain.tolist(),
        }, indent=2), encoding="utf-8")
        print(f"\nfilter -> {args.out}")
    return 0



def build_kernel(freq: np.ndarray, gain: np.ndarray, *, radius: int, grid: int):
    """Turn a radial gain profile into a small spatial convolution kernel.

    The filter is rotationally symmetric, so it is a convolution. Building the
    kernel once and convolving beats a full-slice FFT: it needs no array the
    size of the volume, and processing a slice in bands with a margin leaves no
    block seams.
    """
    f = np.fft.fftfreq(grid)
    fy, fx = np.meshgrid(f, f, indexing="ij")
    r = np.sqrt(fy ** 2 + fx ** 2)
    response = np.interp(r, freq, gain, left=gain[0], right=gain[-1])
    response[0, 0] = 1.0  # DC: leave overall brightness alone
    kernel = np.fft.fftshift(np.real(np.fft.ifft2(response)))

    centre = grid // 2
    size = 2 * radius + 1
    cut = kernel[centre - radius:centre + radius + 1, centre - radius:centre + radius + 1]
    taper = np.outer(np.hanning(size + 2)[1:-1], np.hanning(size + 2)[1:-1])
    cut = cut * taper
    retained = float(np.abs(cut).sum() / np.abs(kernel).sum())
    cut = cut / cut.sum()  # keep DC gain at exactly 1
    return cut, retained


def apply_filter(args) -> int:
    import zarr
    from scipy.signal import fftconvolve

    spec = json.loads(args.filter.read_text(encoding="utf-8"))
    freq = np.asarray(spec["frequency"], dtype=np.float64)
    gain = np.asarray(spec["gain"], dtype=np.float64)
    kernel, retained = build_kernel(freq, gain, radius=args.radius, grid=args.kernel_grid)
    print(f"filter    : {args.filter}")
    print(f"kernel    : {kernel.shape[0]}x{kernel.shape[1]}, retains {retained:.1%} of the"
          f" kernel's absolute mass")
    print(f"            centre tap {kernel[args.radius, args.radius]:+.4f},"
          f" sum {kernel.sum():.4f}")

    source = open_volume(args.volume)
    if args.out.exists():
        sys.exit(f"error: {args.out} exists; remove it or choose another path")
    root = zarr.open(str(args.out), mode="w")
    destination = root.create_dataset(
        "0", shape=source.shape, chunks=source.chunks, dtype=source.dtype,
        compressor=source.compressor, overwrite=True,
    )
    try:
        root.attrs.update(dict(source.attrs))
    except Exception:
        pass
    root.attrs["spectrum_match"] = {
        "filter": str(args.filter), "kernel_radius": args.radius,
        "kernel_grid": args.kernel_grid, "source_volume": str(args.volume),
    }

    depth, height, width = source.shape[-3:]
    margin = args.radius
    band = max(args.band, 4 * margin)
    clipped_total = written = 0
    for z in range(depth):
        for y0 in range(0, height, band):
            y1 = min(y0 + band, height)
            lo, hi = max(0, y0 - margin), min(height, y1 + margin)
            block = np.asarray(source[z, lo:hi, :]).astype(np.float32)
            valid = block > 0
            if not valid.any():
                continue
            # Fill the off-sheet region with the block median first: convolving
            # across a hard edge to zero would ring back into real pixels.
            filled = np.where(valid, block, np.median(block[valid]))
            out = fftconvolve(filled, kernel, mode="same")
            clipped_total += int(np.count_nonzero((out < 0) | (out > 255)))
            out = np.clip(np.rint(out), 0, 255).astype(source.dtype)
            out[~valid] = 0  # off-sheet stays off-sheet
            destination[z, y0:y1, :] = out[y0 - lo:y0 - lo + (y1 - y0), :]
            written += (y1 - y0) * width
        if (z + 1) % max(1, depth // 6) == 0:
            print(f"  z {z + 1}/{depth}", flush=True)

    print(f"wrote     : {args.out}  ({depth} slices, {written:,} pixels per slice-band pass)")
    print(f"clipped   : {clipped_total:,} samples fell outside [0,255] before rounding")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)

    e = sub.add_parser("estimate", help="measure a volume's mean radial power profile")
    e.add_argument("volume", type=Path, help="surface volume zarr")
    e.add_argument("--out", type=Path, help="write the profile as JSON")
    e.add_argument("--patches", type=int, default=256, help="patches to average. Default: 256")
    e.add_argument("--patch", type=int, default=128, help="patch size in px. Default: 128")
    e.add_argument("--z", type=int, help="slice to sample. Default: the middle one")
    e.add_argument("--min-valid", type=float, default=0.95,
                   help="reject a patch below this share of non-zero px. Default: 0.95")
    e.add_argument("--max-attempts", type=int, default=40,
                   help="attempts per wanted patch before giving up. Default: 40")
    e.add_argument("--seed", type=int, default=0, help="sampling seed. Default: 0")
    e.set_defaults(func=estimate)

    c = sub.add_parser("compare", help="compare two profiles and derive a matching filter")
    c.add_argument("source", type=Path, help="profile to match TO")
    c.add_argument("target", type=Path, help="profile to be corrected")
    c.add_argument("--out", type=Path, help="write the filter as JSON")
    c.add_argument("--max-gain", type=float, default=4.0,
                   help="clamp the filter to [1/g, g]. Default: 4")
    c.add_argument("--floor", type=float, default=1e-4,
                   help="power floor, as a share of the peak, to stop dividing by noise")
    c.add_argument("--rows", type=int, default=16, help="rows to print. Default: 16")
    c.set_defaults(func=compare)

    a = sub.add_parser("apply", help="apply a matching filter to a volume")
    a.add_argument("volume", type=Path, help="surface volume zarr to correct")
    a.add_argument("out", type=Path, help="output zarr (level 0 only; inference reads it)")
    a.add_argument("--filter", type=Path, required=True, help="filter JSON from `compare`")
    a.add_argument("--radius", type=int, default=15,
                   help="kernel half-width in px. Default: 15 (a 31x31 kernel)")
    a.add_argument("--kernel-grid", type=int, default=128,
                   help="grid the kernel is derived on. Default: 128")
    a.add_argument("--band", type=int, default=1024,
                   help="rows processed at a time. Default: 1024")
    a.set_defaults(func=apply_filter)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
