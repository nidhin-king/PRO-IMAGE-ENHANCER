import io
from pathlib import Path

from PIL import Image

from app.verification import inspect_output


def _write(path: Path, size, fmt, **save_kwargs):
    Image.new("RGB", size, (40, 80, 120)).save(path, format=fmt, **save_kwargs)


def test_png_verification_reports_actual_size_and_format(tmp_path):
    original = tmp_path / "original.png"
    output = tmp_path / "output.png"
    _write(original, (108, 234), "PNG")
    _write(output, (432, 936), "PNG")
    report = inspect_output(original_path=original, output_path=output, requested_scale=4, requested_format="PNG")
    assert report.actual_format == "PNG"
    assert report.actual_width == 432
    assert report.actual_height == 936
    assert report.scale_x == 4.0
    assert report.scale_y == 4.0
    assert report.matches_requested_scale is True
    assert report.cropped is False
    assert report.format_matches_request is True


def test_never_reports_requested_values_when_actual_differs(tmp_path):
    original = tmp_path / "original.png"
    output = tmp_path / "output.png"
    _write(original, (100, 100), "PNG")
    _write(output, (200, 200), "PNG")
    report = inspect_output(original_path=original, output_path=output, requested_scale=8, requested_format="TIFF")
    assert report.actual_format == "PNG"
    assert report.actual_width == 200
    assert report.scale_x == 2.0
    assert report.matches_requested_scale is False
    assert report.format_matches_request is False
    assert "8" not in report.summary or "2" in report.summary


def test_tiff_magic_is_not_confused_with_png(tmp_path):
    original = tmp_path / "original.png"
    output = tmp_path / "output.tif"
    _write(original, (16, 16), "PNG")
    _write(output, (32, 32), "TIFF", compression="raw")
    report = inspect_output(original_path=original, output_path=output, requested_scale=2, requested_format="TIFF")
    assert report.actual_format == "TIFF"
    assert report.format_matches_request is True


def test_missing_output_is_a_failure(tmp_path):
    original = tmp_path / "original.png"
    _write(original, (8, 8), "PNG")
    report = inspect_output(
        original_path=original,
        output_path=tmp_path / "missing.png",
        requested_scale=2,
        requested_format="PNG",
    )
    assert report.ok is False
    assert "exist" in report.message.lower() or "missing" in report.message.lower()


def test_crop_detected_when_aspect_changes(tmp_path):
    original = tmp_path / "original.png"
    output = tmp_path / "output.png"
    _write(original, (100, 200), "PNG")
    _write(output, (400, 400), "PNG")
    report = inspect_output(original_path=original, output_path=output, requested_scale=4, requested_format="PNG")
    assert report.cropped is True
    assert report.matches_requested_scale is False
