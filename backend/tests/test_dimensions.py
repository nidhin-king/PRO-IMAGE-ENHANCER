from app.dimensions import (
    ALLOWED_SCALES,
    expected_output_size,
    scale_factors,
)


def test_allowed_scales_are_exactly_the_user_selectable_set():
    assert ALLOWED_SCALES == (2, 4, 6, 8, 10)


def test_acceptance_1080x2340_every_scale():
    cases = {
        2: (2160, 4680),
        4: (4320, 9360),
        6: (6480, 14040),
        8: (8640, 18720),
        10: (10800, 23400),
    }
    for scale, expected in cases.items():
        assert expected_output_size(1080, 2340, scale) == expected


def test_output_is_input_times_scale_never_hardcoded():
    assert expected_output_size(13, 17, 2) == (26, 34)
    assert expected_output_size(1, 1, 10) == (10, 10)
    assert expected_output_size(640, 480, 6) == (3840, 2880)


def test_scale_factors_use_actual_not_requested():
    factors = scale_factors(1080, 2340, 4320, 9360)
    assert factors == {"scale_x": 4.0, "scale_y": 4.0}


def test_scale_factors_detect_mismatch():
    factors = scale_factors(100, 100, 400, 200)
    assert factors["scale_x"] == 4.0
    assert factors["scale_y"] == 2.0


def test_rejects_disallowed_scale():
    try:
        expected_output_size(10, 10, 3)
    except ValueError as exc:
        assert "scale" in str(exc).lower()
    else:
        raise AssertionError("expected ValueError")
