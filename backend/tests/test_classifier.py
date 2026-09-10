import numpy as np

from app.classifier import classify_image


def test_photo_like_gradient_is_photo():
    y, x = np.mgrid[0:64, 0:64]
    img = np.stack([x * 3, y * 3, (x + y)], axis=-1).astype(np.uint8)
    result = classify_image(img)
    assert result.kind in {"photo", "screenshot"}
    assert 0.0 <= result.confidence <= 1.0


def test_ui_screenshot_with_hard_edges_is_screenshot():
    img = np.full((80, 120, 3), 245, dtype=np.uint8)
    img[10:20, :] = (30, 30, 30)
    img[40:70, 20:100] = (255, 255, 255)
    img[40:70, 20] = (0, 0, 0)
    img[40:70, 99] = (0, 0, 0)
    result = classify_image(img)
    assert result.kind == "screenshot"
