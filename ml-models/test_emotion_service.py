import os
import io
import base64
import asyncio
from typing import List

import numpy as np
import cv2
import pytest
from fastapi.testclient import TestClient

from main import app
from emotion_model import EmotionModel
from utils import b64_encode_image, b64_decode_image, validate_image, preprocess_image


@pytest.fixture(scope="session", autouse=True)
def enable_mock_mode():
    os.environ["EMOTION_MOCK"] = "true"
    yield
    os.environ.pop("EMOTION_MOCK", None)


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


def create_dummy_face_image(width: int = 256, height: int = 256) -> bytes:
    # Create a simple synthetic face-like pattern
    img = np.zeros((height, width, 3), dtype=np.uint8)
    cv2.circle(img, (width // 2, height // 2), min(width, height) // 3, (255, 255, 255), -1)
    cv2.circle(img, (width // 2 - 30, height // 2 - 20), 10, (0, 0, 0), -1)
    cv2.circle(img, (width // 2 + 30, height // 2 - 20), 10, (0, 0, 0), -1)
    cv2.ellipse(img, (width // 2, height // 2 + 30), (40, 20), 0, 0, 180, (0, 0, 0), 3)
    _, buf = cv2.imencode('.jpg', img)
    return buf.tobytes()


def test_validate_and_preprocess_image():
    img_bytes = create_dummy_face_image()
    assert validate_image(img_bytes)
    processed = preprocess_image(img_bytes)
    assert processed is not None
    assert processed.ndim == 3


def test_b64_roundtrip():
    img_bytes = create_dummy_face_image()
    b64 = b64_encode_image(img_bytes)
    decoded = b64_decode_image(b64)
    assert decoded is not None
    assert decoded[:16] == img_bytes[:16]


def test_health_endpoint(client: TestClient):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data


def test_single_predict_endpoint(client: TestClient):
    img_bytes = create_dummy_face_image()
    files = {"file": ("test.jpg", img_bytes, "image/jpeg")}
    res = client.post("/predict/emotion", files=files)
    assert res.status_code == 200
    body = res.json()
    assert "success" in body
    assert body["success"] in [True, False]
    if body["success"]:
        assert "prediction" in body


def test_batch_predict_endpoint(client: TestClient):
    img1 = create_dummy_face_image()
    img2 = create_dummy_face_image()
    files = [
        ("files", ("a.jpg", img1, "image/jpeg")),
        ("files", ("b.jpg", img2, "image/jpeg")),
    ]
    res = client.post("/predict/batch", files=files)
    assert res.status_code == 200
    body = res.json()
    assert "predictions" in body


def test_invalid_file_type(client: TestClient):
    res = client.post(
        "/predict/emotion",
        files={"file": ("bad.txt", b"not an image", "text/plain")},
    )
    assert res.status_code == 400
    body = res.json()
    assert body.get("detail", {}).get("error")


def test_missing_file_returns_json_error(client: TestClient):
    res = client.post("/predict/emotion")
    # FastAPI would usually raise validation error, but our handler should produce JSON detail
    assert res.status_code == 400 or res.status_code == 422
    body = res.json()
    # Accept either our custom shape or validation default, but prefer our error key
    if res.status_code == 400:
        assert body.get("detail", {}).get("error") == "No file uploaded"

