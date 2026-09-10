from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image

from app.dimensions import scale_factors


@dataclass
class VerificationReport:
    ok: bool
    actual_format: str | None
    actual_width: int | None
    actual_height: int | None
    original_width: int
    original_height: int
    scale_x: float | None
    scale_y: float | None
    matches_requested_scale: bool
    format_matches_request: bool
    cropped: bool
    orientation: str
    summary: str
    message: str
    requested_scale: int
    requested_format: str

    def to_dict(self) -> dict:
        return asdict(self)


def _format_from_magic(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"
    if data[:2] in {b"II", b"MM"} and (data[2:4] in {b"\x2a\x00", b"\x00\x2a"}):
        return "TIFF"
    if data[:2] == b"\xff\xd8":
        return "JPEG"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "WEBP"
    return None


def inspect_output(
    original_path: Path,
    output_path: Path,
    requested_scale: int,
    requested_format: str,
) -> VerificationReport:
    original_path = Path(original_path)
    output_path = Path(output_path)

    with Image.open(original_path) as original:
        original_width, original_height = original.size

    if not output_path.exists():
        return VerificationReport(
            ok=False,
            actual_format=None,
            actual_width=None,
            actual_height=None,
            original_width=original_width,
            original_height=original_height,
            scale_x=None,
            scale_y=None,
            matches_requested_scale=False,
            format_matches_request=False,
            cropped=False,
            orientation="unknown",
            summary="Output file does not exist",
            message="Output file does not exist",
            requested_scale=requested_scale,
            requested_format=requested_format,
        )

    data = output_path.read_bytes()
    magic_format = _format_from_magic(data)
    try:
        with Image.open(output_path) as image:
            image.load()
            actual_width, actual_height = image.size
            decoded_format = (image.format or magic_format or "UNKNOWN").upper()
            if decoded_format == "JPG":
                decoded_format = "JPEG"
    except Exception as exc:
        return VerificationReport(
            ok=False,
            actual_format=magic_format,
            actual_width=None,
            actual_height=None,
            original_width=original_width,
            original_height=original_height,
            scale_x=None,
            scale_y=None,
            matches_requested_scale=False,
            format_matches_request=False,
            cropped=False,
            orientation="unknown",
            summary="Output file could not be opened",
            message=f"Output file could not be opened: {exc}",
            requested_scale=requested_scale,
            requested_format=requested_format,
        )

    actual_format = magic_format or decoded_format
    factors = scale_factors(original_width, original_height, actual_width, actual_height)
    scale_x = factors["scale_x"]
    scale_y = factors["scale_y"]
    matches = (
        abs(scale_x - requested_scale) < 1e-6
        and abs(scale_y - requested_scale) < 1e-6
    )
    cropped = abs(scale_x - scale_y) > 1e-6
    orientation = "landscape" if actual_width > actual_height else "portrait" if actual_height > actual_width else "square"
    format_matches = actual_format == requested_format.upper()
    ok = matches and format_matches and not cropped

    summary = (
        f"Image format: {actual_format}\n"
        f"Resolution: {actual_width} x {actual_height} px\n"
        f"Upscale: {original_width} x {original_height} -> {actual_width} x {actual_height} = {scale_x:g}x / {scale_y:g}x\n"
        f"Original resolution: {original_width} x {original_height} px\n"
        f"Requested: {requested_scale}x {requested_format}"
    )
    return VerificationReport(
        ok=ok,
        actual_format=actual_format,
        actual_width=actual_width,
        actual_height=actual_height,
        original_width=original_width,
        original_height=original_height,
        scale_x=scale_x,
        scale_y=scale_y,
        matches_requested_scale=matches,
        format_matches_request=format_matches,
        cropped=cropped,
        orientation=orientation,
        summary=summary,
        message="Verified from output file" if ok else "Actual output differs from request",
        requested_scale=requested_scale,
        requested_format=requested_format,
    )
