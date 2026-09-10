import io
import os
from pathlib import Path

import pytest
from PIL import Image

from app.enhancer import enhance_image
from app.inference import InferenceEngine
from app.verification import inspect_output

MODELS_DIR = Path(os.environ.get("PIE_MODELS_DIR", "/workspace/data/models"))


@pytest.fixture(scope="module")
def engine():
    if os.environ.get("PIE_SKIP_ONNX", "0") == "1":
        pytest.skip("ONNX integration skipped")
    eng = InferenceEngine(MODELS_DIR, use_stub=False)
    if eng.session is None:
        pytest.skip(f"No ONNX model: {eng.load_error}")
    return eng


def test_real_onnx_2x_png_actual_dimensions(engine, tmp_path):
    src = tmp_path / "in.png"
    out = tmp_path / "out.png"
    Image.new("RGB", (16, 24), (30, 90, 180)).save(src)
    enhance_image(
        source_path=src,
        output_path=out,
        scale=2,
        output_format="PNG",
        infer_fn=engine.infer_tile,
        model_scale=4,
        tile_size=16,
        overlap=4,
        device=engine.device,
    )
    report = inspect_output(src, out, requested_scale=2, requested_format="PNG")
    assert report.actual_format == "PNG"
    assert report.actual_width == 32
    assert report.actual_height == 48
    assert report.matches_requested_scale is True
    assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_real_onnx_tiff_is_tiff(engine, tmp_path):
    src = tmp_path / "in.png"
    out = tmp_path / "out.tif"
    Image.new("RGB", (12, 12), (12, 40, 90)).save(src)
    enhance_image(
        source_path=src,
        output_path=out,
        scale=2,
        output_format="TIFF",
        infer_fn=engine.infer_tile,
        model_scale=4,
        tile_size=12,
        overlap=0,
        device=engine.device,
    )
    report = inspect_output(src, out, requested_scale=2, requested_format="TIFF")
    assert report.actual_format == "TIFF"
    assert out.read_bytes()[:2] in {b"II", b"MM"}
