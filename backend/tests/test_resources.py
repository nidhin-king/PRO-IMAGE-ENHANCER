from app.resources import ResourceDecision, evaluate_job_resources


def test_small_job_is_allowed():
    decision = evaluate_job_resources(
        width=64,
        height=64,
        scale=2,
        available_ram_bytes=8 * 1024**3,
    )
    assert decision.action == "allow"
    assert decision.expected_width == 128
    assert decision.expected_height == 128


def test_10x_phone_screenshot_warns_or_blocks_on_8gb():
    decision = evaluate_job_resources(
        width=1080,
        height=2340,
        scale=10,
        available_ram_bytes=8 * 1024**3,
    )
    assert decision.action in {"warn", "block"}
    assert decision.expected_width == 10800
    assert decision.expected_height == 23400
    assert decision.output_pixels == 10800 * 23400


def test_confirm_overrides_warn_but_not_block():
    warn = evaluate_job_resources(
        width=2000,
        height=2000,
        scale=8,
        available_ram_bytes=8 * 1024**3,
        confirmed=True,
    )
    assert warn.action in {"allow", "block"}
    if warn.estimated_peak_bytes > 0.70 * 8 * 1024**3:
        assert warn.action == "block"


def test_hard_block_when_output_exceeds_ram_budget():
    decision = evaluate_job_resources(
        width=8000,
        height=8000,
        scale=10,
        available_ram_bytes=8 * 1024**3,
        confirmed=True,
    )
    assert decision.action == "block"
    assert "memory" in decision.message.lower() or "ram" in decision.message.lower()
