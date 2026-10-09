#!/usr/bin/env python3
"""Load third-party checkpoints without executing pickle code, and re-save clean copies.

KLAVIS .pth: torch.load(weights_only=True) only (restricted unpickler); refuse anything else.
Nieuwlaar: safetensors weights + its published training config -> {"model", "config", "step"}.
"""
import hashlib
import json
import sys
from pathlib import Path

import torch
from safetensors.torch import load_file

ROOT = Path(r"E:\vesuvius-challenge\data\ink_9um\models_ext")
OUT = ROOT / "clean"
OUT.mkdir(exist_ok=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


report = {}
for src in sorted((ROOT / "klavis_dense").glob("*.pth")):
    payload = torch.load(src, map_location="cpu", weights_only=True)
    keys = sorted(payload) if isinstance(payload, dict) else type(payload).__name__
    model = payload["model"]
    assert all(isinstance(v, torch.Tensor) for v in model.values()), src
    clean = {"model": model, "config": payload["config"], "step": payload.get("step")}
    dst = OUT / f"klavis_{src.stem}.pth"
    torch.save(clean, dst)
    report[src.name] = {"sha256": sha256(src), "keys": keys, "step": payload.get("step"),
                        "tensors": len(model), "out": dst.name}
    print(src.name, keys, payload.get("step"), len(model), flush=True)

nd = ROOT / "nieuwlaar_dense_native"
weights = load_file(str(nd / "weights" / "dense_native_016000.safetensors"))
config = json.loads((nd / "training" / "configs" / "train_dense_native.json").read_text(encoding="utf-8"))
dst = OUT / "nieuwlaar_dense_native_016000.pth"
torch.save({"model": weights, "config": config, "step": 16000}, dst)
report["dense_native_016000.safetensors"] = {"sha256": sha256(nd / "weights" / "dense_native_016000.safetensors"),
                                            "tensors": len(weights), "step": 16000, "out": dst.name}
print("nieuwlaar", len(weights), flush=True)

# key sets must match a released ink_9um checkpoint's
ref = torch.load(Path(r"E:\vesuvius-challenge\data\ink_9um\models\hybrid_3d2d-seed42\step-010000.pth"),
                 map_location="cpu", weights_only=True)["model"]
for name in sorted(OUT.glob("*.pth")):
    m = torch.load(name, map_location="cpu", weights_only=True)["model"]
    same = set(m) == set(ref) and all(m[k].shape == ref[k].shape for k in ref)
    report.setdefault("key_match", {})[name.name] = same
    print(name.name, "keys/shapes match released ink_9um:", same, flush=True)
(OUT / "convert_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
