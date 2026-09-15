"""Run the patched model-card quick start against the real weights, offline, from the local files.

The only difference from the card: AutoModel.from_pretrained is replaced by importing the
repo's own modeling file and loading model.safetensors, so nothing is downloaded here."""
import json, os, sys
os.environ["HF_HUB_OFFLINE"] = "1"; os.environ["TRANSFORMERS_OFFLINE"] = "1"
import torch
from safetensors.torch import load_file
sys.path.insert(0, "E:/vesuvius-challenge/planning/october_failures")
from hf_source.configuration_inkdetection import InkDetectionConfig      # unchanged upstream file
from hf_source.modeling_inkdetection import InkDetectionModel            # unchanged upstream file (weights/compute)

torch.cuda.set_per_process_memory_fraction(0.20)
cfg = InkDetectionConfig(**json.load(open("E:/vesuvius-challenge/planning/october_failures/hf_source/config.json")))
model = InkDetectionModel(cfg)
print("strict load:", model.load_state_dict(load_file("E:/vesuvius-challenge/data/october_failures/model.safetensors"), strict=True))
model = model.eval().cuda()

# --- the patched quick start, verbatim from here ---
# Input: float32, shape (B, 1, D=62, H=256, W=256).
# Explicitly reproduce clipping followed by Albumentations'
# Normalize(mean=0, std=1, max_pixel_value=255): clip(raw, 0, 200) / 255.
# This is intensity scaling, not per-tile z-score normalization.
# This synthetic tensor demonstrates the call shape only, not ink quality.
torch.manual_seed(0)
raw = torch.randint(0, 256, (1, 1, 62, 256, 256), device="cuda")
x = raw.float().clamp(0, 200) / 255.0

with torch.no_grad():
    out = model(x)

print(out.logits.shape)                        # torch.Size([1, 1, 64, 64])
prob = torch.sigmoid(out.logits)               # ink probability per pixel
# --- end of quick start ---
print(f"input range after scaling: [{x.min().item():.4f}, {x.max().item():.4f}]   (raw uint8 clipped to 200 -> max 200/255 = {200/255:.4f})")
print(f"prob range on this synthetic tensor: [{prob.min().item():.3f}, {prob.max().item():.3f}]   (shape check only; noise input says nothing about ink)")
