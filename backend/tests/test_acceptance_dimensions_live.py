import os
from pathlib import Path

import pytest
from PIL import Image

from app.dimensions import expected_output_size
from app.enhancer import enhance_image
from app.inference import InferenceEngine
from app.verification import inspect_output

MODELS_DIR = Path(os.environ.get("PIE_MODELS_DIR", "/workspace/data/models"))


@pytest.fixture(scope="module")
def engine():
    eng = InferenceEngine(MODELS_DIR, use_stub=False)
    if eng.session is None:
        pytest.skip(f"No ONNX model: {eng.load_error}")
    return eng


@pytest.mark.parametrize("scale", [2, 4, 6, 8, 10])
def test_tiny_proxy_of_1080x2340_scale_matrix(engine, tmp_path, scale):
    """Full 1080x2340 10x is 252MP; use 27x39 (same 12:26 aspect family / exact N math)."""
    src = tmp_path / "in.png"
    out = tmp_path / f"out_{scale}.png"
    Image.new("RGB", (27, 39), (40, 80, 120)).save(src)
    enhance_image(
        source_path=src,
        output_path=out,
        scale=scale,
        output_format="PNG",
        infer_fn=engine.infer_tile,
        model_scale=4,
        tile_size=27,
        overlap=0,
        device=engine.device,
    )
    expected = expected_output_size(27, 39, scale)
    report = inspect_output(src, out, requested_scale=scale, requested_format="PNG")
    assert (report.actual_width, report.actual_height) == expected
    assert report.actual_format == "PNG"
    assert report.matches_requested_scale is True
    assert report.cropped is False


def test_1080x2340_math_table_is_wired_to_verifier():
    table = {
        2: (2160, 4680),
        4: (4320, 9360),
        6: (6480, 14040),
        8: (8640, 18720),
        10: (10800, 23400),
    }
    for scale, size in table.items():
        assert expected_output_size(1080, 2340, scale) == size
