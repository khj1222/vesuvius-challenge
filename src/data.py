"""
data.py — Vesuvius ink detection 데이터 로딩 스캐폴드.

surface volume(표면 깊이방향 TIFF 레이어 스택) + ink/papyrus 마스크를 읽어
2.5D 세그멘테이션 학습용 타일을 만든다.

⚠️ 스캐폴드: 실제 경로/파일명은 데이터 다운로드 후 채운다(TODO week0).
공식 튜토리얼: https://scrollprize.org/tutorial5
"""
from __future__ import annotations

import glob
import os
from dataclasses import dataclass

import numpy as np

# TODO(week0): 다운로드한 fragment 루트로 교체
DATA_ROOT = os.environ.get("VESUVIUS_DATA", r"D:\vesuvius-challenge\data")


@dataclass
class Fragment:
    """한 fragment의 경로 묶음."""
    frag_id: str
    root: str

    @property
    def surface_dir(self) -> str:
        # TODO(week0): 튜토리얼 fragment의 실제 레이어 디렉토리명 확인 (예: 'surface_volume')
        return os.path.join(self.root, self.frag_id, "surface_volume")

    @property
    def ink_label_path(self) -> str:
        # TODO(week0): 실제 잉크 라벨 파일명 확인 (예: 'inklabels.png')
        return os.path.join(self.root, self.frag_id, "inklabels.png")

    @property
    def mask_path(self) -> str:
        return os.path.join(self.root, self.frag_id, "mask.png")


def load_surface_volume(frag: Fragment, z_start: int = 0, z_depth: int = 16) -> np.ndarray:
    """표면 볼륨을 [z_depth, H, W] float32 배열로 로드.

    깊이 방향 TIFF 레이어를 z_start부터 z_depth장 쌓는다. 잉크는 특정 깊이대에
    신호가 몰리므로 z_start/z_depth 선택이 성능을 좌우(튜토리얼 기본값에서 출발).
    """
    import tifffile  # requirements.txt

    layers = sorted(glob.glob(os.path.join(frag.surface_dir, "*.tif")))
    if not layers:
        raise FileNotFoundError(
            f"레이어 없음: {frag.surface_dir} — DATA_ROOT/파일명 TODO를 채웠는지 확인"
        )
    sel = layers[z_start : z_start + z_depth]
    vol = np.stack([tifffile.imread(p).astype(np.float32) for p in sel], axis=0)
    # TODO(week0): 정규화 방식 검토 (16bit → [0,1], per-layer vs global)
    vol /= 65535.0
    return vol


def load_labels(frag: Fragment) -> tuple[np.ndarray, np.ndarray]:
    """(ink_mask, papyrus_mask)를 [H, W] uint8(0/1)로 로드."""
    import cv2  # opencv-python

    ink = cv2.imread(frag.ink_label_path, cv2.IMREAD_GRAYSCALE)
    mask = cv2.imread(frag.mask_path, cv2.IMREAD_GRAYSCALE)
    if ink is None or mask is None:
        raise FileNotFoundError("라벨/마스크 없음 — Fragment 경로 TODO 확인")
    return (ink > 127).astype(np.uint8), (mask > 127).astype(np.uint8)


def iter_tiles(vol: np.ndarray, tile: int = 224, stride: int = 112):
    """볼륨을 (y, x, patch[z,tile,tile]) 타일로 순회. 학습/추론 공통."""
    _, h, w = vol.shape
    for y in range(0, h - tile + 1, stride):
        for x in range(0, w - tile + 1, stride):
            yield y, x, vol[:, y : y + tile, x : x + tile]


if __name__ == "__main__":
    # 스모크 테스트: 데이터 채운 뒤 `python -m src.data`로 shape 확인
    frag = Fragment(frag_id="1", root=DATA_ROOT)
    print("surface_dir:", frag.surface_dir)
    print("데이터 다운로드 후 load_surface_volume/load_labels로 shape 검증할 것.")
