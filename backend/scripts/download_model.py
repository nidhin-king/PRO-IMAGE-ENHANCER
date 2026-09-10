#!/usr/bin/env python3
"""Download a real x4 super-resolution ONNX model."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.inference import InferenceEngine  # noqa: E402


def main() -> int:
    models = ROOT / "data" / "models"
    engine = InferenceEngine(models, use_stub=False)
    print(engine.health())
    return 0 if engine.session is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
