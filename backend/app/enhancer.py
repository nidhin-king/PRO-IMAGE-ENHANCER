from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from app.classifier import classify_image
from app.dimensions import expected_output_size
from app.tiling import blend_tiles


@dataclass
class EnhanceResult:
    output_width: int
    output_height: int
    output_format: str
    kind: str
    model_scale: int
    device: str


class JobCancelled(RuntimeError):
    pass


def _to_rgb(image: Image.Image) -> tuple[np.ndarray, Image.Image | None]:
    alpha = None
    if image.mode == "RGBA":
        alpha = image.getchannel("A")
        rgb = Image.new("RGB", image.size, (255, 255, 255))
        rgb.paste(image, mask=alpha)
        return np.array(rgb), alpha
    if image.mode != "RGB":
        image = image.convert("RGB")
    return np.array(image), None


def _lanczos_resize(arr: np.ndarray, width: int, height: int) -> np.ndarray:
    img = Image.fromarray(arr, mode="RGB")
    resized = img.resize((width, height), resample=Image.Resampling.LANCZOS)
    return np.array(resized)


def _save_lossless(image: Image.Image, path: Path, output_format: str) -> None:
    output_format = output_format.upper()
    path.parent.mkdir(parents=True, exist_ok=True)
    if output_format == "PNG":
        image.save(path, format="PNG", compress_level=1)
        return
    if output_format == "TIFF":
        image.save(path, format="TIFF", compression="raw")
        return
    raise ValueError(f"Unsupported output format {output_format}")


def enhance_image(
    *,
    source_path: Path,
    output_path: Path,
    scale: int,
    output_format: str,
    infer_fn: Callable[[np.ndarray], np.ndarray],
    model_scale: int = 4,
    tile_size: int = 64,
    overlap: int = 8,
    cancel_event=None,
    progress_cb: Callable[[float, str], None] | None = None,
    device: str = "cpu",
) -> EnhanceResult:
    source_path = Path(source_path)
    output_path = Path(output_path)
    with Image.open(source_path) as src:
        src.load()
        array, alpha = _to_rgb(src)
        original_size = src.size

    kind = classify_image(array).kind
    target_w, target_h = expected_output_size(original_size[0], original_size[1], scale)

    def cancel_check() -> bool:
        return bool(cancel_event and cancel_event.is_set())

    def tile_progress(done: int, total: int) -> None:
        if progress_cb:
            progress_cb(0.1 + 0.8 * (done / max(total, 1)), f"Enhancing tile {done}/{total}")

    def infer_to_model_scale(tile: np.ndarray) -> np.ndarray:
        up = infer_fn(tile)
        expected = (tile.shape[0] * model_scale, tile.shape[1] * model_scale)
        if up.shape[0] != expected[0] or up.shape[1] != expected[1]:
            up = _lanczos_resize(up, expected[1], expected[0])
        return up

    if progress_cb:
        progress_cb(0.05, "Preparing tiles")

    try:
        sr = blend_tiles(
            source=array,
            scale=model_scale,
            tile_size=tile_size,
            overlap=overlap,
            infer_fn=infer_to_model_scale,
            cancel_check=cancel_check,
            progress_cb=tile_progress,
        )
    except RuntimeError as exc:
        if "cancel" in str(exc).lower():
            raise JobCancelled("Job cancelled") from exc
        raise

    if cancel_check():
        raise JobCancelled("Job cancelled")

    if progress_cb:
        progress_cb(0.92, "Matching requested output size")

    if sr.shape[1] != target_w or sr.shape[0] != target_h:
        sr = _lanczos_resize(sr, target_w, target_h)

    out_img = Image.fromarray(sr, mode="RGB")
    if alpha is not None:
        scaled_alpha = alpha.resize((target_w, target_h), resample=Image.Resampling.LANCZOS)
        out_img = out_img.convert("RGBA")
        out_img.putalpha(scaled_alpha)

    _save_lossless(out_img, output_path, output_format)
    if progress_cb:
        progress_cb(0.98, "Saved output")

    return EnhanceResult(
        output_width=target_w,
        output_height=target_h,
        output_format=output_format.upper(),
        kind=kind,
        model_scale=model_scale,
        device=device,
    )
