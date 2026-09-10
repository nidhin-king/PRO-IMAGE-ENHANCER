ALLOWED_SCALES = (2, 4, 6, 8, 10)


def expected_output_size(width: int, height: int, scale: int) -> tuple[int, int]:
    if scale not in ALLOWED_SCALES:
        raise ValueError(f"Unsupported scale {scale}; allowed: {ALLOWED_SCALES}")
    if width < 1 or height < 1:
        raise ValueError("Width and height must be positive")
    return width * scale, height * scale


def scale_factors(
    original_width: int,
    original_height: int,
    actual_width: int,
    actual_height: int,
) -> dict[str, float]:
    if original_width < 1 or original_height < 1:
        raise ValueError("Original dimensions must be positive")
    return {
        "scale_x": actual_width / original_width,
        "scale_y": actual_height / original_height,
    }
