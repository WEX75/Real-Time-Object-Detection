"""Loads the real models (downloads weights on first run). Skipped in CI.

Run with: python -m pytest -m model -s
"""

import time

import cv2
import numpy as np
import pytest

from app.detector import OpenVocabDetector, YoloDetector

WARMUP_FRAMES = 2
TIMED_FRAMES = 10


def generated_frame() -> bytes:
    """A 640x480 synthetic scene: a table, a cup-like cylinder and a bottle shape."""
    image = np.full((480, 640, 3), 200, dtype=np.uint8)
    cv2.rectangle(image, (60, 300), (580, 460), (60, 90, 130), -1)
    cv2.rectangle(image, (200, 220), (260, 300), (240, 240, 240), -1)
    cv2.ellipse(image, (230, 220), (30, 8), 0, 0, 360, (220, 220, 220), -1)
    cv2.rectangle(image, (380, 160), (420, 300), (40, 140, 40), -1)
    ok, encoded = cv2.imencode(".jpg", image)
    assert ok
    return encoded.tobytes()


@pytest.mark.model
@pytest.mark.parametrize("detector_class", [OpenVocabDetector, YoloDetector], ids=["openvocab", "yolo"])
def test_real_detector_runs_on_generated_image(detector_class: type) -> None:
    detector = detector_class(["person", "cup", "bottle"])
    frame = generated_frame()
    for _ in range(WARMUP_FRAMES):
        detector.detect(frame)

    timings = []
    for _ in range(TIMED_FRAMES):
        start = time.perf_counter()
        detections = detector.detect(frame)
        timings.append((time.perf_counter() - start) * 1000)

    print(
        f"\n{detector.name}: infer_ms mean={np.mean(timings):.1f} "
        f"median={np.median(timings):.1f} min={min(timings):.1f} max={max(timings):.1f} "
        f"over {TIMED_FRAMES} frames; detections={[(d.label, round(d.confidence, 2)) for d in detections]}"
    )
    for detection in detections:
        assert detection.label in {"person", "cup", "bottle"}
        assert 0.0 <= detection.confidence <= 1.0
