import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import create_app


def _png(width=32, height=48) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), (20, 40, 80)).save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PIE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("PIE_USE_STUB_INFER", "1")
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert "device" in body


def test_upload_and_2x_png(client):
    res = client.post(
        "/api/jobs",
        files={"file": ("shot.png", _png(20, 30), "image/png")},
        data={"scale": "2", "output_format": "PNG"},
    )
    assert res.status_code == 202, res.text
    job_id = res.json()["id"]
    status = client.get(f"/api/jobs/{job_id}")
    assert status.status_code == 200
    body = status.json()
    assert body["status"] in {"queued", "running", "completed"}
    for _ in range(50):
        body = client.get(f"/api/jobs/{job_id}").json()
        if body["status"] in {"completed", "failed"}:
            break
    assert body["status"] == "completed", body
    v = body["verification"]
    assert v["actual_width"] == 40
    assert v["actual_height"] == 60
    assert v["actual_format"] == "PNG"
    download = client.get(f"/api/jobs/{job_id}/result")
    assert download.status_code == 200
    assert download.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_rejects_path_traversal(client):
    res = client.post(
        "/api/jobs",
        files={"file": ("../secret.png", _png(), "image/png")},
        data={"scale": "2", "output_format": "PNG"},
    )
    assert res.status_code == 400


def test_rejects_unsupported_file(client):
    res = client.post(
        "/api/jobs",
        files={"file": ("notes.txt", b"hello", "text/plain")},
        data={"scale": "2", "output_format": "PNG"},
    )
    assert res.status_code == 400


def test_invalid_scale_rejected(client):
    res = client.post(
        "/api/jobs",
        files={"file": ("shot.png", _png(), "image/png")},
        data={"scale": "3", "output_format": "PNG"},
    )
    assert res.status_code == 400
