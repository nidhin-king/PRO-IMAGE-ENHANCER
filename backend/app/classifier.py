from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Classification:
    kind: str
    confidence: float
    notes: str


def classify_image(image: np.ndarray) -> Classification:
    if image.ndim != 3 or image.shape[2] < 3:
        return Classification(kind="photo", confidence=0.4, notes="non-rgb")

    rgb = image[:, :, :3].astype(np.float32)
    gray = rgb.mean(axis=2)
    gy = np.abs(np.diff(gray, axis=0)).mean()
    gx = np.abs(np.diff(gray, axis=1)).mean()
    edge = (gx + gy) / 2.0

    quantized = np.round(gray / 16.0)
    unique_ratio = np.unique(quantized).size / 16.0
    std = float(gray.std())

    screenshot_score = 0.0
    if edge > 12:
        screenshot_score += 0.35
    if unique_ratio < 0.85:
        screenshot_score += 0.25
    if std < 70:
        screenshot_score += 0.2
    # large near-white or near-black regions typical of UI
    white_ratio = float((gray > 240).mean())
    black_ratio = float((gray < 20).mean())
    if white_ratio > 0.15 or black_ratio > 0.08:
        screenshot_score += 0.25

    screenshot_score = min(1.0, screenshot_score)
    if screenshot_score >= 0.5:
        return Classification(
            kind="screenshot",
            confidence=screenshot_score,
            notes=f"edge={edge:.1f} unique={unique_ratio:.2f}",
        )
    return Classification(
        kind="photo",
        confidence=1.0 - screenshot_score,
        notes=f"edge={edge:.1f} unique={unique_ratio:.2f}",
    )
