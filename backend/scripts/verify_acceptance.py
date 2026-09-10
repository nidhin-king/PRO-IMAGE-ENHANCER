#!/usr/bin/env python3
"""Live evidence: enhance a 1080x2340-family image and print actual verification."""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.dimensions import expected_output_size  # noqa: E402
from app.enhancer import enhance_image  # noqa: E402
from app.inference import InferenceEngine  # noqa: E402
from app.verification import inspect_output  # noqa: E402


def make_screenshot(path: Path, width: int, height: int) -> None:
    img = Image.new("RGB", (width, height), (248, 250, 252))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, width, 72], fill=(15, 23, 42))
    draw.text((16, 24), "Inbox  128  $42.50  #OK", fill=(255, 255, 255))
    for i in range(8):
        y = 96 + i * 48
        draw.rectangle([12, y, width - 12, y + 36], outline=(15, 23, 42), width=2)
        draw.text((24, y + 8), f"Row {i+1}  invoice-{1000+i}  99%", fill=(15, 23, 42))
    draw.rectangle([0, height - 8, 8, height], fill=(220, 38, 38))
    img.save(path, format="PNG")


def main() -> int:
    out_dir = ROOT / "data" / "jobs" / "acceptance"
    out_dir.mkdir(parents=True, exist_ok=True)
    engine = InferenceEngine(ROOT / "data" / "models", use_stub=False)
    print("engine", engine.health())
    if engine.session is None:
        print("MODEL MISSING", engine.load_error)
        return 1

    print("1080x2340 acceptance table:")
    for scale in (2, 4, 6, 8, 10):
        print(" ", scale, expected_output_size(1080, 2340, scale))

    src = out_dir / "input_108x234.png"
    make_screenshot(src, 108, 234)
    for scale, fmt, name in ((2, "PNG", "out_2x.png"), (4, "PNG", "out_4x.png"), (2, "TIFF", "out_2x.tif")):
        dest = out_dir / name
        enhance_image(
            source_path=src,
            output_path=dest,
            scale=scale,
            output_format=fmt,
            infer_fn=engine.infer_tile,
            model_scale=4,
            tile_size=64,
            overlap=8,
            device=engine.device,
        )
        report = inspect_output(src, dest, requested_scale=scale, requested_format=fmt)
        magic = dest.read_bytes()[:8]
        print("---")
        print(report.summary)
        print("ok", report.ok, "magic", magic)

    src_full = out_dir / "input_1080x234.png"
    make_screenshot(src_full, 1080, 234)
    dest_full = out_dir / "out_1080x234_2x.png"
    enhance_image(
        source_path=src_full,
        output_path=dest_full,
        scale=2,
        output_format="PNG",
        infer_fn=engine.infer_tile,
        model_scale=4,
        tile_size=64,
        overlap=8,
        device=engine.device,
    )
    report = inspect_output(src_full, dest_full, requested_scale=2, requested_format="PNG")
    print("--- full-width phone strip ---")
    print(report.summary)
    print("ok", report.ok, "file_size", dest_full.stat().st_size)
    return 0 if report.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
