from __future__ import annotations

from dataclasses import dataclass

from app.dimensions import expected_output_size


@dataclass(frozen=True)
class ResourceDecision:
    action: str
    expected_width: int
    expected_height: int
    output_pixels: int
    estimated_peak_bytes: int
    message: str


def evaluate_job_resources(
    *,
    width: int,
    height: int,
    scale: int,
    available_ram_bytes: int,
    confirmed: bool = False,
    warn_ratio: float = 0.40,
    block_ratio: float = 0.70,
) -> ResourceDecision:
    expected_width, expected_height = expected_output_size(width, height, scale)
    output_pixels = expected_width * expected_height
    # uint8 RGB output + float32 workspace + overlap/tile buffers
    estimated_peak_bytes = int(output_pixels * 3 * 6)
    warn_bytes = int(available_ram_bytes * warn_ratio)
    block_bytes = int(available_ram_bytes * block_ratio)

    if estimated_peak_bytes > block_bytes or output_pixels > 400_000_000:
        return ResourceDecision(
            action="block",
            expected_width=expected_width,
            expected_height=expected_height,
            output_pixels=output_pixels,
            estimated_peak_bytes=estimated_peak_bytes,
            message=(
                "This job exceeds the safe memory budget on this machine. "
                "Reduce the upscale factor or use a smaller image. "
                f"Estimated peak RAM: {estimated_peak_bytes / (1024**3):.1f} GB."
            ),
        )

    if estimated_peak_bytes > warn_bytes and not confirmed:
        return ResourceDecision(
            action="warn",
            expected_width=expected_width,
            expected_height=expected_height,
            output_pixels=output_pixels,
            estimated_peak_bytes=estimated_peak_bytes,
            message=(
                "This job may use a large amount of memory and take a long time on CPU. "
                "Confirm to continue. "
                f"Output will be {expected_width} x {expected_height} px "
                f"(~{estimated_peak_bytes / (1024**3):.1f} GB peak estimate)."
            ),
        )

    return ResourceDecision(
        action="allow",
        expected_width=expected_width,
        expected_height=expected_height,
        output_pixels=output_pixels,
        estimated_peak_bytes=estimated_peak_bytes,
        message="Within the local memory budget.",
    )
