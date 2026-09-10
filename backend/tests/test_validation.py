import io

import pytest
from PIL import Image

from app.validation import ValidationError, validate_upload


def _png_bytes(width=32, height=48, color=(12, 80, 160)):
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buf, format="PNG")
    return buf.getvalue()


def test_accepts_valid_png():
    result = validate_upload(
        filename="shot.png",
        content_type="image/png",
        data=_png_bytes(),
    )
    assert result.format == "PNG"
    assert result.width == 32
    assert result.height == 48
    assert result.mode in {"RGB", "RGBA"}


def test_rejects_extension_mismatch():
    with pytest.raises(ValidationError, match="mismatch"):
        validate_upload(
            filename="shot.jpg",
            content_type="image/jpeg",
            data=_png_bytes(),
        )


def test_rejects_path_traversal_filename():
    with pytest.raises(ValidationError, match="path"):
        validate_upload(
            filename="../etc/passwd.png",
            content_type="image/png",
            data=_png_bytes(),
        )


def test_rejects_absolute_path_filename():
    with pytest.raises(ValidationError, match="path"):
        validate_upload(
            filename="/tmp/evil.png",
            content_type="image/png",
            data=_png_bytes(),
        )


def test_rejects_html_polyglot():
    payload = b"<html><body>not an image</body></html>"
    with pytest.raises(ValidationError):
        validate_upload(
            filename="trick.png",
            content_type="image/png",
            data=payload,
        )


def test_rejects_svg():
    svg = b"""<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"></svg>"""
    with pytest.raises(ValidationError):
        validate_upload(
            filename="x.svg",
            content_type="image/svg+xml",
            data=svg,
        )


def test_rejects_oversized_file():
    data = _png_bytes()
    with pytest.raises(ValidationError, match="size"):
        validate_upload(
            filename="big.png",
            content_type="image/png",
            data=data,
            max_bytes=len(data) - 1,
        )


def test_rejects_empty_file():
    with pytest.raises(ValidationError):
        validate_upload(
            filename="empty.png",
            content_type="image/png",
            data=b"",
        )


def test_rejects_unsupported_extension():
    with pytest.raises(ValidationError, match="(?i)unsupported"):
        validate_upload(
            filename="notes.pdf",
            content_type="application/pdf",
            data=b"%PDF-1.4",
        )
