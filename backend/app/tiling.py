from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Tile:
    x0: int
    y0: int
    x1: int
    y1: int


def iter_tiles(*, width: int, height: int, tile_size: int, overlap: int) -> list[Tile]:
    if tile_size < 1:
        raise ValueError("tile_size must be positive")
    overlap = max(0, min(overlap, tile_size // 2))
    step = max(1, tile_size - overlap)
    tiles: list[Tile] = []
    y = 0
    while y < height:
        x = 0
        y1 = min(y + tile_size, height)
        y0 = y
        if y1 - y0 < tile_size and y0 > 0:
            y0 = max(0, y1 - tile_size)
        while x < width:
            x1 = min(x + tile_size, width)
            x0 = x
            if x1 - x0 < tile_size and x0 > 0:
                x0 = max(0, x1 - tile_size)
            tiles.append(Tile(x0=x0, y0=y0, x1=x1, y1=y1))
            if x1 >= width:
                break
            x += step
        if y1 >= height:
            break
        y += step
    return tiles


def _weight_window(h: int, w: int) -> np.ndarray:
    return np.ones((h, w, 1), dtype=np.float32)


def blend_tiles(
    *,
    source: np.ndarray,
    scale: int,
    tile_size: int,
    overlap: int,
    infer_fn: Callable[[np.ndarray], np.ndarray],
    cancel_check: Callable[[], bool] | None = None,
    progress_cb: Callable[[int, int], None] | None = None,
) -> np.ndarray:
    height, width = source.shape[:2]
    channels = source.shape[2] if source.ndim == 3 else 1
    out_h, out_w = height * scale, width * scale
    acc = np.zeros((out_h, out_w, channels), dtype=np.float32)
    weight = np.zeros((out_h, out_w, 1), dtype=np.float32)
    tiles = iter_tiles(width=width, height=height, tile_size=tile_size, overlap=overlap)
    total = len(tiles)

    for index, tile in enumerate(tiles):
        if cancel_check and cancel_check():
            raise RuntimeError("Job cancelled")
        patch = source[tile.y0 : tile.y1, tile.x0 : tile.x1]
        up = infer_fn(patch)
        expected_h = (tile.y1 - tile.y0) * scale
        expected_w = (tile.x1 - tile.x0) * scale
        if up.shape[0] != expected_h or up.shape[1] != expected_w:
            raise RuntimeError(
                f"Tile output size mismatch: got {up.shape[:2]}, expected {(expected_h, expected_w)}"
            )
        y0, x0 = tile.y0 * scale, tile.x0 * scale
        y1, x1 = tile.y1 * scale, tile.x1 * scale
        win = _weight_window(expected_h, expected_w)
        acc[y0:y1, x0:x1] += up.astype(np.float32) * win
        weight[y0:y1, x0:x1] += win
        if progress_cb:
            progress_cb(index + 1, total)

    weight = np.maximum(weight, 1e-6)
    canvas = np.clip(np.rint(acc / weight), 0, 255).astype(np.uint8)
    return canvas
