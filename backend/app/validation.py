from __future__ import annotations

import imghdr
import io
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError

ALLOWED_EXTENSIONS = {
    ".png": "PNG",
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".webp": "WEBP",
    ".bmp": "BMP",
    ".tif": "TIFF",
    ".tiff": "TIFF",
}

ALLOWED_MIME = {
    "image/png": "PNG",
    "image/jpeg": "JPEG",
    "image/jpg": "JPEG",
    "image/webp": "WEBP",
    "image/bmp": "BMP",
    "image/x-ms-bmp": "BMP",
    "image/tiff": "TIFF",
    "image/tif": "TIFF",
}

MAX_UPLOAD_BYTES = 40 * 1024 * 1024
MAX_INPUT_PIXELS = 40_000_000


class ValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ValidatedImage:
    format: str
    width: int
    height: int
    mode: str
    filename: str


def _safe_filename(filename: str) -> str:
    if not filename or not filename.strip():
        raise ValidationError("Missing filename")
    name = filename.replace("\\", "/")
    if name.startswith("/") or name.startswith("..") or "/.." in f"/{name}":
        raise ValidationError("Unsafe path in filename")
    if "/" in name:
        raise ValidationError("Unsafe path in filename")
    return Path(name).name


def _detect_format(data: bytes, claimed: str | None) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"
    if data[:2] in {b"II", b"MM"} and (data[2:4] == b"\x2a\x00" or data[2:4] == b"\x00\x2a"):
        return "TIFF"
    if data[:2] == b"\xff\xd8":
        return "JPEG"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "WEBP"
    if data[:2] == b"BM":
        return "BMP"
    sniffed = imghdr.what(None, h=data)
    mapping = {"png": "PNG", "jpeg": "JPEG", "bmp": "BMP", "tiff": "TIFF", "webp": "WEBP"}
    if sniffed in mapping:
        return mapping[sniffed]
    return claimed


def validate_upload(
    *,
    filename: str,
    content_type: str,
    data: bytes,
    max_bytes: int = MAX_UPLOAD_BYTES,
    max_pixels: int = MAX_INPUT_PIXELS,
) -> ValidatedImage:
    if data is None or len(data) == 0:
        raise ValidationError("Empty file")
    if len(data) > max_bytes:
        raise ValidationError(f"File size exceeds limit of {max_bytes} bytes")

    safe_name = _safe_filename(filename)
    ext = Path(safe_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(f"Unsupported file extension: {ext or '(none)'}")

    mime = (content_type or "").split(";")[0].strip().lower()
    if mime and mime not in ALLOWED_MIME:
        raise ValidationError(f"Unsupported MIME type: {mime}")

    ext_format = ALLOWED_EXTENSIONS[ext]
    mime_format = ALLOWED_MIME.get(mime, ext_format)
    if mime and mime_format != ext_format:
        raise ValidationError("MIME type and extension mismatch")

    magic_format = _detect_format(data, None)
    if magic_format and magic_format != ext_format:
        raise ValidationError("File content and extension mismatch")

    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
        with Image.open(io.BytesIO(data)) as image:
            image.load()
            width, height = image.size
            decoded_format = (image.format or ext_format).upper()
            mode = image.mode
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValidationError("Corrupted or unreadable image") from exc

    if decoded_format == "JPG":
        decoded_format = "JPEG"
    if decoded_format not in set(ALLOWED_EXTENSIONS.values()):
        raise ValidationError(f"Unsupported decoded format: {decoded_format}")
    if decoded_format != ext_format:
        raise ValidationError("File content and extension mismatch")
    if width < 1 or height < 1:
        raise ValidationError("Invalid image dimensions")
    if width * height > max_pixels:
        raise ValidationError(f"Image exceeds maximum pixel count ({max_pixels})")

    return ValidatedImage(
        format=decoded_format,
        width=width,
        height=height,
        mode=mode,
        filename=safe_name,
    )
