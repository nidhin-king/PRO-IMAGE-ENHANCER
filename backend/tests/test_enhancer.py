import io
from pathlib import Path

import numpy as np
from PIL import Image

from app.dimensions import expected_output_size
from app.enhancer import enhance_image
from app.verification import inspect_output


def _save_png(path: Path, width: int, height: int) -> None:
    img = Image.new("RGB", (width, height), (18, 90, 160))
    for x in range(0, width, 8):
        for y in range(height):
            img.putpixel((x, y), (255, 255, 255))
    path.write_bytes(_png_bytes(img))


def _png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _nearest_n(n: int):
    def infer(tile: np.ndarray) -> np.ndarray:
        return np.repeat(np.repeat(tile, n, axis=0), n, axis=1)

    return infer


def test_2x_png_exact_dimensions(tmp_path):
    src = tmp_path / "in.png"
    out = tmp_path / "out.png"
    _save_png(src, 24, 40)
    result = enhance_image(
        source_path=src,
        output_path=out,
        scale=2,
        output_format="PNG",
        infer_fn=_nearest_n(4),
        model_scale=4,
    )
    assert (result.output_width, result.output_height) == expected_output_size(24, 40, 2)
    report = inspect_output(src, out, requested_scale=2, requested_format="PNG")
    assert report.actual_format == "PNG"
    assert report.actual_width == 48
    assert report.actual_height == 80
    assert report.matches_requested_scale is True


def test_every_scale_matches_acceptance_math(tmp_path):
    src = tmp_path / "in.png"
    _save_png(src, 10, 12)
    for scale in (2, 4, 6, 8, 10):
        out = tmp_path / f"out_{scale}.png"
        enhance_image(
            source_path=src,
            output_path=out,
            scale=scale,
            output_format="PNG",
            infer_fn=_nearest_n(4),
            model_scale=4,
        )
        expected_w, expected_h = expected_output_size(10, 12, scale)
        report = inspect_output(src, out, requested_scale=scale, requested_format="PNG")
        assert report.actual_width == expected_w
        assert report.actual_height == expected_h
        assert report.actual_format == "PNG"


def test_tiff_output_is_actually_tiff(tmp_path):
    src = tmp_path / "in.png"
    out = tmp_path / "out.tif"
    _save_png(src, 8, 8)
    enhance_image(
        source_path=src,
        output_path=out,
        scale=2,
        output_format="TIFF",
        infer_fn=_nearest_n(4),
        model_scale=4,
    )
    report = inspect_output(src, out, requested_scale=2, requested_format="TIFF")
    assert report.actual_format == "TIFF"
    assert out.read_bytes()[:2] in {b"II", b"MM"}


def test_original_file_is_never_overwritten(tmp_path):
    src = tmp_path / "in.png"
    _save_png(src, 8, 10)
    before = src.read_bytes()
    enhance_image(
        source_path=src,
        output_path=tmp_path / "out.png",
        scale=2,
        output_format="PNG",
        infer_fn=_nearest_n(4),
        model_scale=4,
    )
    assert src.read_bytes() == before


def test_long_screenshot_keeps_top_and_bottom(tmp_path):
    src = tmp_path / "long.png"
    arr = np.zeros((120, 16, 3), dtype=np.uint8)
    arr[0, 0] = [255, 0, 0]
    arr[-1, -1] = [0, 0, 255]
    Image.fromarray(arr, mode="RGB").save(src)
    out = tmp_path / "out.png"
    enhance_image(
        source_path=src,
        output_path=out,
        scale=2,
        output_format="PNG",
        infer_fn=_nearest_n(4),
        model_scale=4,
        tile_size=32,
        overlap=8,
    )
    result = np.array(Image.open(out))
    assert result.shape[0] == 240
    assert result.shape[1] == 32
    assert result[0, 0, 0] > 200
    assert result[-1, -1, 2] > 200


def test_cancel_stops_between_tiles(tmp_path):
    src = tmp_path / "in.png"
    _save_png(src, 64, 64)
    cancelled = {"n": 0}

    def infer(tile):
        cancelled["n"] += 1
        raise_if = cancelled["n"] > 1
        if raise_if:
            raise RuntimeError("should not be called after cancel")
        return np.repeat(np.repeat(tile, 4, axis=0), 4, axis=1)

    class Flag:
        def is_set(self):
            return cancelled["n"] >= 1

    try:
        enhance_image(
            source_path=src,
            output_path=tmp_path / "out.png",
            scale=4,
            output_format="PNG",
            infer_fn=infer,
            model_scale=4,
            tile_size=16,
            overlap=0,
            cancel_event=Flag(),
        )
    except Exception as exc:
        assert "cancel" in str(exc).lower()
    else:
        raise AssertionError("expected cancellation")
