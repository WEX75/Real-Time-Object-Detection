"""Helpers shared by the API, WebSocket and privacy tests."""

import cv2
import numpy as np

from app.schemas import Detection

LEFT_TABLE = [(0.0, 0.5), (0.5, 0.5), (0.5, 1.0), (0.0, 1.0)]


def jpeg(width: int = 64, height: int = 48) -> bytes:
    ok, encoded = cv2.imencode(".jpg", np.full((height, width, 3), 127, dtype=np.uint8))
    assert ok
    return encoded.tobytes()


def det(label: str, x: float = 0.25, y: float = 0.8) -> Detection:
    """Detection whose bottom-center is (x, y). The default point is on LEFT_TABLE."""
    return Detection(label=label, confidence=0.9, box=(x - 0.05, y - 0.2, x + 0.05, y))
