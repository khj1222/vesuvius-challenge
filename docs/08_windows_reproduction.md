# Reproducing Vesuvius ink detection on **native Windows** (RTX 5090)

An end‑to‑end walkthrough that takes you from a fresh checkout to legible Greek
letters on a Herculaneum papyrus — running the official
[`ScrollPrize/villa`](https://github.com/ScrollPrize/villa) `koine_machines`
pipeline **on native Windows**, no WSL2 required.

It doubles as a **field guide to the traps** that aren't in the official
tutorial (data size, GPU wheels, a `torch.compile`/Triton crash, PowerShell
noise). Each is called out inline and collected in the
[Gotchas](#gotchas-quick-reference) table at the bottom.

> Verified 2026‑07‑21 on Windows 11 + RTX 5090 (sm_120), `torch 2.10.0+cu128`.

---

## The payoff

The model turns a CT scan that looks like blank papyrus into readable text.

| Raw CT surface (input) | Ink revealed (output) |
| :--: | :--: |
| ![raw CT surface](images/w00_surface.png) | ![ink overlay](images/w00_overlay.png) |
| *A z‑projection of the surface volume — you can see fibres, not letters.* | *Ink probability rendered over the same surface with [`ink_viz`](../tools/ink_viz.py).* |

Segment: `w00_20231016151002` (scroll **PHercParis4**). Everything below produces
these images.

---

## 0. Prerequisites

- **Windows 11**, an NVIDIA GPU with a recent driver. This guide uses an RTX 5090
  (Blackwell, compute capability **sm_120**); any CUDA GPU with enough VRAM works
  (training used ~16 GB).
- [**uv**](https://docs.astral.sh/uv/) on `PATH` (`uv --version`). uv fetches its
  own Python, so you don't need a matching system interpreter.
- The [**Hugging Face CLI**](https://huggingface.co/docs/huggingface_hub/guides/cli)
  (`hf --version`) — the data lives in public HF buckets (anonymous access is fine).
- **git**, and roughly **90 GB free disk** for one segment.

All commands below are **PowerShell**, run from a working root we'll call
`D:\vesuvius-challenge`.

---

## 1. Get the pipeline

```powershell
git clone https://github.com/ScrollPrize/villa external\villa
cd external\villa
git checkout merge-ink-pipelines
```

> ⚠️ **Trap — branch name.** The tutorial references the branch in the singular;
> the real branch is **`merge-ink-pipelines`** (plural "pipelines"). A singular
> name will `error: pathspec ... did not match`.

The ink pipeline lives in `external\villa\ink-detection`. Work from there.

---

## 2. Environment (the RTX 5090 / cu128 override)

`ink-detection/pyproject.toml` pins `torch==2.10.0`. A plain `uv sync` on Windows
can resolve the **CPU** wheel, which then fails at runtime on a modern GPU with
"no kernel image is available for execution on the device" (sm_120 is too new for
older CUDA builds).

Force the CUDA 12.8 index. Add this to `ink-detection/pyproject.toml`:

```toml
[[tool.uv.index]]
name = "pytorch-cu128"
url = "https://download.pytorch.org/whl/cu128"
explicit = true

[tool.uv.sources]
torch = [{ index = "pytorch-cu128" }]
torchvision = [{ index = "pytorch-cu128" }]
```

Then:

```powershell
cd D:\vesuvius-challenge\external\villa\ink-detection
uv sync
```

Verify CUDA actually works before spending an hour training:

```powershell
uv run python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
# -> 2.10.0+cu128 True NVIDIA GeForce RTX 5090
```

> If you prefer not to edit `pyproject.toml`, you can instead override after a
> sync: `uv pip install torch==2.10.0 torchvision==0.25.0 --index-url https://download.pytorch.org/whl/cu128`.

**No WSL2 needed.** The dataloader uses a `spawn` start method, which is
Windows‑safe.

---

## 3. Data

One ink‑labelled segment is enough for a first result.

```powershell
hf buckets sync `
  hf://buckets/scrollprize/datasets/ink/phercparis4/w00_20231016151002 `
  D:\vesuvius-challenge\data\ink-dataset\phercparis4\w00_20231016151002
```

> ⚠️ **Trap — data size.** The tutorial says ~25 GB. The real segment is
> **~86 GB across 147,785 files** (`hf buckets ls -R` reports 85.7 GB — the
> `<seg>.zarr` surface volume alone is ~85 GB). Budget disk and time accordingly.
>
> `hf buckets sync` is **idempotent and resumable** — if it's interrupted (or your
> PC sleeps), just run the same command again and it continues where it left off.

You'll end up with the surface volume `<seg>.zarr`, the label volumes
`<seg>_inklabels.zarr` / `<seg>_supervision_mask.zarr` (+ matching `.tif`s),
`x/y/z.tif`, and `meta.json`.

The surface volume is an **OME‑Zarr multiscale pyramid** — level 0 is
`(z=65, y=32249, x=51380)` uint8; each higher level is 2× smaller in x/y. That
pyramid is what makes the visualisations in step 6 cheap.

---

## 4. Config

`configs/ink_tutorial.json` (2.5D flat model, one ink target):

```jsonc
{
  "out_dir": "runs/ink_tutorial",
  "mode": "flat",
  "model_type": "vesuvius_unet",
  "model_config": { "autoconfigure": true, "z_projection_mode": "max" },
  "targets": { "ink": { "out_channels": 1, "activation": "none", "z_projection_mode": "max" } },
  "patch_size": [64, 256, 256],
  "batch_size": 2,
  "num_iterations": 20000,
  "mixed_precision": "fp16",
  "dataloader_workers": 4,
  "val_every": 500,
  "save_every": 1000,
  "datasets": [
    { "segments_path": "D:/vesuvius-challenge/data/ink-dataset/phercparis4", "volume_scale": "0" }
  ]
}
```

`segments_path` points at the **parent** folder (the one containing the
`w00_...` segment directory).

---

## 5. Train

```powershell
uv run --directory external\villa\ink-detection `
  python -m koine_machines.training.train configs/ink_tutorial.json
```

On an RTX 5090: **20,000 iterations in ~1 h 31 m** (~3.4 it/s), loss falling from
~1.5 toward 0. Checkpoints land in `runs/ink_tutorial/ckpt_0XXXXX.pth` every 1,000
iterations (20 of them, ~1.08 GB each); training previews in
`runs/ink_tutorial/train_previews/`.

**Out of memory?** Drop `batch_size` to `1`, or `patch_size` to `[64, 128, 128]`.

> ℹ️ **Not an error — PowerShell noise.** With output redirected you'll see lines
> like `uv.exe : ... NativeCommandError`. That's just PowerShell wrapping the
> tool's **stderr** (tqdm writes progress there); it does not mean the run failed.

---

## 6. Infer — **and the `--no-compile` trap**

```powershell
uv run --directory external\villa\ink-detection `
  python -m koine_machines.inference.infer `
  D:\vesuvius-challenge\data\ink-dataset\phercparis4\w00_20231016151002\w00_20231016151002.zarr `
  runs/ink_tutorial/ckpt_020000.pth `
  predictions/w00_20231016151002.tif `
  --batch-size 4 --no-compile
```

> ⚠️ **Trap — Triton on Windows.** Inference enables
> `torch.compile(mode="reduce-overhead")` by default. Its Inductor backend needs
> **Triton**, which has **no native‑Windows build**, so the first forward pass
> dies with:
>
> ```
> torch._inductor.exc.TritonMissing: Cannot find a working triton installation.
> ```
>
> **Pass `--no-compile`.** Training is unaffected (it doesn't compile); this only
> bites inference.

On an RTX 5090: **9,425 blocks in ~23 min** (~6.7 block/s). Output is a single
tiled uint8 TIFF at full resolution (`32249 × 51380`, ~700 MB): raw ink
probability for the whole sheet.

---

## 7. Visualise with `ink_viz`

Straight out of the model, the TIFF looks blank in a normal viewer — most of its
range sits near zero. Use [`tools/ink_viz.py`](../tools/ink_viz.py) (in this repo)
to make it readable. It runs in the same `uv` environment:

```powershell
$T = "D:\vesuvius-challenge\tools\ink_viz.py"
$P = "external\villa\ink-detection\predictions\w00_20231016151002.tif"
$Z = "data\ink-dataset\phercparis4\w00_20231016151002\w00_20231016151002.zarr"

# quick QC — is there any signal?
uv run --directory external\villa\ink-detection python $T stats  $P
# grayscale reading preview
uv run --directory external\villa\ink-detection python $T preview $P -o preview.png
# raw CT surface (the "before")
uv run --directory external\villa\ink-detection python $T surface $Z -o surface.png
# ink glowing over the papyrus (the "after")
uv run --directory external\villa\ink-detection python $T overlay $P $Z -o overlay.png
```

`stats` on this run reports non‑zero **82 %**, strong‑ink (`>128`) **11 %**, with a
clean bimodal split (p50=8, p90=143, p99=251) — background low, ink high, exactly
what a good prediction looks like.

> ⚠️ **Trap — `tifffile` + zarr.** Reading the TIFF with
> `tifffile.imread(path, aszarr=True)` raises `ValueError: zarr 2.x < 3 is not
> supported` (the pipeline env pins zarr 2). `ink_viz` reads with a plain
> `tifffile.imread` to avoid that path.

See [`tools/README.md`](../tools/README.md) for all options (`--level`,
`--color`, `--threshold`, `--z-reduce`, …).

---

## Gotchas quick reference

| # | Trap | Symptom | Fix |
|--|------|---------|-----|
| 1 | Branch name | `pathspec ... did not match` | branch is `merge-ink-pipelines` (**plural**) |
| 2 | RTX 5090 = sm_120 | CPU wheel / "no kernel image is available" | install `torch 2.10.0+cu128` (pin the `pytorch-cu128` uv index) |
| 3 | Data size | download blows past the tutorial's "25 GB" | it's really **~86 GB / 147,785 files**; `hf buckets sync` is resumable |
| 4 | **Inference `torch.compile`** | `torch._inductor.exc.TritonMissing` on first forward | **pass `--no-compile`** (Triton has no native‑Windows build; training is fine) |
| 5 | PowerShell stderr | `uv.exe : ... NativeCommandError` | cosmetic — PowerShell wrapping tqdm's stderr, not a failure |
| 6 | Blank‑looking TIFF | opens all‑black in a viewer | values cluster near 0; use `ink_viz preview` / `overlay` (percentile stretch) |
| 7 | `tifffile` aszarr | `ValueError: zarr 2.x < 3 is not supported` | read with plain `tifffile.imread` (what `ink_viz` does) |

## Timings on an RTX 5090

| Stage | Work | Wall‑clock |
|-------|------|-----------|
| Download | 85.7 GB / 147,785 files | network‑bound |
| Train | 20,000 iterations @ ~3.4 it/s | **~1 h 31 m** |
| Infer | 9,425 blocks @ ~6.7 block/s (`--no-compile`) | **~23 min** |
| Visualise | 3 images from the 700 MB TIFF | < 1 min each |

---

*Pipeline © ScrollPrize/villa. This walkthrough and `ink_viz` are MIT‑licensed
(see repo root). Contributions/corrections welcome.*
