"""
model.py — 잉크 detection 베이스라인 세그멘테이션 모델.

입력: surface volume 타일 [B, z_depth, tile, tile] (깊이=채널)
출력: 잉크 확률 [B, 1, tile, tile]

기본은 depth를 채널로 넣는 2.5D UNet. 검증 후 segmentation-models-pytorch(smp)의
사전학습 인코더로 교체하는 게 보통 더 강함(TODO week0/phase2).
"""
from __future__ import annotations

import torch
import torch.nn as nn


class _DoubleConv(nn.Module):
    def __init__(self, cin: int, cout: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(cin, cout, 3, padding=1, bias=False),
            nn.BatchNorm2d(cout),
            nn.ReLU(inplace=True),
            nn.Conv2d(cout, cout, 3, padding=1, bias=False),
            nn.BatchNorm2d(cout),
            nn.ReLU(inplace=True),
        )

    def forward(self, x):
        return self.net(x)


class InkUNet(nn.Module):
    """작은 2.5D UNet 베이스라인. z_depth를 입력 채널로 사용."""

    def __init__(self, z_depth: int = 16, base: int = 32):
        super().__init__()
        self.d1 = _DoubleConv(z_depth, base)
        self.d2 = _DoubleConv(base, base * 2)
        self.d3 = _DoubleConv(base * 2, base * 4)
        self.pool = nn.MaxPool2d(2)
        self.bott = _DoubleConv(base * 4, base * 8)
        self.up3 = nn.ConvTranspose2d(base * 8, base * 4, 2, stride=2)
        self.u3 = _DoubleConv(base * 8, base * 4)
        self.up2 = nn.ConvTranspose2d(base * 4, base * 2, 2, stride=2)
        self.u2 = _DoubleConv(base * 4, base * 2)
        self.up1 = nn.ConvTranspose2d(base * 2, base, 2, stride=2)
        self.u1 = _DoubleConv(base * 2, base)
        self.head = nn.Conv2d(base, 1, 1)

    def forward(self, x):
        c1 = self.d1(x)
        c2 = self.d2(self.pool(c1))
        c3 = self.d3(self.pool(c2))
        b = self.bott(self.pool(c3))
        x = self.u3(torch.cat([self.up3(b), c3], dim=1))
        x = self.u2(torch.cat([self.up2(x), c2], dim=1))
        x = self.u1(torch.cat([self.up1(x), c1], dim=1))
        return self.head(x)  # logits [B,1,H,W]


def build_model(z_depth: int = 16) -> nn.Module:
    # TODO(phase2): smp.Unet(encoder_name="resnet34", in_channels=z_depth) 등으로 교체 비교
    return InkUNet(z_depth=z_depth)


if __name__ == "__main__":
    m = build_model(z_depth=16)
    x = torch.zeros(2, 16, 224, 224)
    print("out:", m(x).shape)  # 기대 [2,1,224,224]
