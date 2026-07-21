"""
infer.py — 타일 추론 → 잉크 확률맵 PNG (첫 시각 산출물).

전체 fragment를 타일로 추론하고 겹침 평균으로 스티칭해 하나의 확률맵 이미지를 만든다.
이 PNG가 Week0의 눈으로 보는 결과물이자 제출 산출물의 씨앗.
"""
from __future__ import annotations

import os

import numpy as np
import torch

from .data import DATA_ROOT, Fragment, iter_tiles, load_surface_volume
from .model import build_model
from .train import CKPT_DIR, STRIDE, TILE, Z_DEPTH


def predict_fragment(frag_id: str = "1", out_png: str | None = None) -> np.ndarray:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    vol = load_surface_volume(Fragment(frag_id=frag_id, root=DATA_ROOT), z_depth=Z_DEPTH)
    _, h, w = vol.shape

    model = build_model(Z_DEPTH).to(device)
    ckpt = os.path.join(CKPT_DIR, f"ink_frag{frag_id}.pt")
    if os.path.exists(ckpt):
        model.load_state_dict(torch.load(ckpt, map_location=device))
    else:
        print(f"⚠️ 체크포인트 없음({ckpt}) — 먼저 src.train 실행. 지금은 랜덤 가중치.")
    model.eval()

    prob = np.zeros((h, w), np.float32)
    cnt = np.zeros((h, w), np.float32)
    with torch.no_grad():
        for y, x, patch in iter_tiles(vol, TILE, STRIDE):
            t = torch.from_numpy(patch)[None].to(device)
            p = torch.sigmoid(model(t))[0, 0].cpu().numpy()
            prob[y : y + TILE, x : x + TILE] += p
            cnt[y : y + TILE, x : x + TILE] += 1.0
    prob /= np.maximum(cnt, 1e-6)

    if out_png:
        import cv2
        os.makedirs(os.path.dirname(out_png), exist_ok=True)
        cv2.imwrite(out_png, (prob * 255).astype(np.uint8))
        print("saved:", out_png)
    return prob


if __name__ == "__main__":
    # 데이터+학습 후: python -m src.infer
    predict_fragment(out_png=r"D:\vesuvius-challenge\submission\ink_pred.png")
