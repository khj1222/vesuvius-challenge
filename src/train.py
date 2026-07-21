"""
train.py — 잉크 detection 베이스라인 학습 루프 (Week0 최소 버전).

목표: 작은 fragment로 몇 epoch 돌려 파이프라인이 도는지 확인 + 체크포인트 저장.
metric보다 "눈으로 글자 보이는 예측"이 실질 지표(→ infer.py로 시각확인).

⚠️ 스캐폴드: 데이터 채운 뒤 하이퍼파라미터/검증분할 TODO를 채운다.
"""
from __future__ import annotations

import os

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

from .data import DATA_ROOT, Fragment, iter_tiles, load_labels, load_surface_volume
from .model import build_model

CKPT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "checkpoints")
Z_DEPTH = 16
TILE = 224
STRIDE = 112


class InkTiles(Dataset):
    """한 fragment를 타일로 잘라 (patch, ink_tile) 반환."""

    def __init__(self, frag: Fragment):
        self.vol = load_surface_volume(frag, z_depth=Z_DEPTH)
        self.ink, self.mask = load_labels(frag)
        self.items = [
            (y, x) for y, x, _ in iter_tiles(self.vol, TILE, STRIDE)
            # TODO(week0): mask 안쪽 타일만 남기는 필터 추가(파피루스 밖 배경 제외)
        ]

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        y, x = self.items[i]
        patch = self.vol[:, y : y + TILE, x : x + TILE]
        label = self.ink[y : y + TILE, x : x + TILE][None].astype(np.float32)
        return torch.from_numpy(patch), torch.from_numpy(label)


def train(frag_id: str = "1", epochs: int = 5, bs: int = 8, lr: float = 1e-3):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cpu":
        print("⚠️ CUDA 미검출 — 5090 cu128 torch 설치 확인(requirements.txt)")

    ds = InkTiles(Fragment(frag_id=frag_id, root=DATA_ROOT))
    # TODO(week0): 공간분할 holdout(같은 fragment 내 좌/우 split)로 검증셋 확보 — 누수 주의
    dl = DataLoader(ds, batch_size=bs, shuffle=True, num_workers=0)

    model = build_model(Z_DEPTH).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr)
    loss_fn = nn.BCEWithLogitsLoss()

    model.train()
    for ep in range(epochs):
        tot = 0.0
        for patch, label in dl:
            patch, label = patch.to(device), label.to(device)
            opt.zero_grad()
            loss = loss_fn(model(patch), label)
            loss.backward()
            opt.step()
            tot += loss.item()
        print(f"epoch {ep + 1}/{epochs}  loss={tot / max(len(dl), 1):.4f}")

    os.makedirs(CKPT_DIR, exist_ok=True)
    out = os.path.join(CKPT_DIR, f"ink_frag{frag_id}.pt")
    torch.save(model.state_dict(), out)
    print("saved:", out)


if __name__ == "__main__":
    # 데이터 채운 뒤: python -m src.train
    train()
