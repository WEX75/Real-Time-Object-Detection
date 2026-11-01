"""Object detectors behind one interface (Strategy).

`OpenVocabDetector` finds any object named in text (YOLO-World), `YoloDetector`
is the COCO fallback and `FakeDetector` serves tests without a model.
Ultralytics is imported inside the real detectors only, so importing this module
stays fast and never downloads weights.
"""

from __future__ import annotations

import logging
import os
import threading
from collections.abc import Iterable, Sequence
from typing import Any, Protocol

import cv2
import numpy as np

from .schemas import Detection, normalize_label

logger = logging.getLogger(__name__)

IMGSZ = 640
DEFAULT_CONF = 0.25
OPENVOCAB_WEIGHTS = "yolov8s-worldv2.pt"
YOLO_WEIGHTS = "yolo11n.pt"
DEFAULT_VOCABULARY = ("person", "cup", "bottle")


class InvalidFrameError(ValueError):
    """The bytes received are not a decodable image."""


class Detector(Protocol):
    name: str

    def set_vocabulary(self, words: list[str]) -> list[str]:
        """Set the words to look for; return the ones this detector cannot find."""
        ...

    def detect(self, jpeg: bytes) -> list[Detection]: ...


def normalize_words(words: Iterable[str]) -> list[str]:
    """Normalized, without blanks or duplicates, in the order given."""
    return list(dict.fromkeys(normalize_label(word) for word in words if word.strip()))


def decode_jpeg(jpeg: bytes) -> np.ndarray:
    """BGR image from encoded bytes. Raises `InvalidFrameError`."""
    if not jpeg:
        raise InvalidFrameError("empty frame")
    image = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise InvalidFrameError("frame is not a valid JPEG image")
    return image


def _clamp(value: float) -> float:
    return min(1.0, max(0.0, float(value)))


def _to_detections(result: Any, names: dict[int, str], vocabulary: set[str]) -> list[Detection]:
    """Convert one Ultralytics result, keeping only labels in the vocabulary."""
    detections: list[Detection] = []
    boxes = result.boxes
    for xyxyn, cls, conf in zip(boxes.xyxyn.tolist(), boxes.cls.tolist(), boxes.conf.tolist()):
        label = normalize_label(names[int(cls)])
        if label not in vocabulary:
            continue
        x1, y1, x2, y2 = (_clamp(v) for v in xyxyn)
        detections.append(Detection(label=label, confidence=_clamp(conf), box=(x1, y1, x2, y2)))
    return detections


class OpenVocabDetector:
    """YOLO-World: the vocabulary becomes the model's classes through CLIP text
    embeddings, so any word works without training."""

    name = "openvocab"

    def __init__(
        self, words: Sequence[str] = DEFAULT_VOCABULARY, conf: float = DEFAULT_CONF, weights: str = OPENVOCAB_WEIGHTS
    ) -> None:
        from ultralytics import YOLOWorld

        self._conf = conf
        self._model = YOLOWorld(weights)
        # set_classes swaps the text embeddings; never in the middle of a predict.
        self._lock = threading.Lock()
        self._vocabulary: list[str] = []
        self.set_vocabulary(list(words))

    def set_vocabulary(self, words: list[str]) -> list[str]:
        with self._lock:
            if words:
                self._model.set_classes(list(words))
            self._vocabulary = list(words)
        return []

    def detect(self, jpeg: bytes) -> list[Detection]:
        image = decode_jpeg(jpeg)
        with self._lock:
            if not self._vocabulary:
                return []
            result = self._model.predict(image, imgsz=IMGSZ, conf=self._conf, device="cpu", verbose=False)[0]
            return _to_detections(result, dict(enumerate(self._vocabulary)), set(self._vocabulary))


class YoloDetector:
    """YOLO11n on the 80 COCO classes; results are filtered to the vocabulary."""

    name = "yolo"

    def __init__(
        self, words: Sequence[str] = DEFAULT_VOCABULARY, conf: float = DEFAULT_CONF, weights: str = YOLO_WEIGHTS
    ) -> None:
        from ultralytics import YOLO

        self._conf = conf
        self._model = YOLO(weights)
        self._names: dict[int, str] = dict(self._model.names)
        self._classes = {normalize_label(name) for name in self._names.values()}
        self._vocabulary: set[str] = set()
        self.set_vocabulary(list(words))

    def set_vocabulary(self, words: list[str]) -> list[str]:
        self._vocabulary = {word for word in words if word in self._classes}
        return [word for word in words if word not in self._classes]

    def detect(self, jpeg: bytes) -> list[Detection]:
        image = decode_jpeg(jpeg)
        result = self._model.predict(image, imgsz=IMGSZ, conf=self._conf, device="cpu", verbose=False)[0]
        return _to_detections(result, self._names, self._vocabulary)


class FakeDetector:
    """Returns detections scripted in advance, one list per frame. After the
    script runs out it keeps returning the last list (or nothing).

    Frames are still decoded, so a corrupt JPEG fails here as it would in a
    real detector.
    """

    name = "fake"

    def __init__(
        self,
        frames: Iterable[Sequence[Detection]] = (),
        supported: Iterable[str] | None = None,
        unsupported: Iterable[str] = (),
    ) -> None:
        """`supported` limits the known words (None: every word); `unsupported`
        names words it never knows."""
        self._frames: list[list[Detection]] = [list(frame) for frame in frames]
        self._last: list[Detection] = []
        self._supported = None if supported is None else {normalize_label(word) for word in supported}
        self._unsupported = {normalize_label(word) for word in unsupported}
        self.vocabulary: list[str] = []
        self.calls = 0

    def script(self, *frames: Sequence[Detection]) -> None:
        """Append frames to the script."""
        self._frames.extend(list(frame) for frame in frames)

    def set_vocabulary(self, words: list[str]) -> list[str]:
        self.vocabulary = list(words)
        return [
            word
            for word in words
            if word in self._unsupported or (self._supported is not None and word not in self._supported)
        ]

    def detect(self, jpeg: bytes) -> list[Detection]:
        decode_jpeg(jpeg)
        self.calls += 1
        if self._frames:
            self._last = self._frames.pop(0)
        return list(self._last)


def create_detector(words: list[str], kind: str | None = None, conf: float | None = None) -> Detector:
    """Build the detector chosen by `VIGILO_DETECTOR` (openvocab|yolo) and load
    the vocabulary. If openvocab cannot load, log why and fall back to yolo."""
    kind = (kind or os.environ.get("VIGILO_DETECTOR", "openvocab")).strip().lower()
    conf = conf if conf is not None else float(os.environ.get("VIGILO_CONF", DEFAULT_CONF))
    if kind not in ("openvocab", "yolo"):
        raise ValueError(f"unknown VIGILO_DETECTOR {kind!r}; expected openvocab or yolo")

    if kind == "openvocab":
        try:
            detector: Detector = OpenVocabDetector(words, conf=conf)
            logger.info("detector: openvocab (%s)", OPENVOCAB_WEIGHTS)
            return detector
        except Exception:
            logger.exception("openvocab detector failed to load; falling back to yolo")

    detector = YoloDetector(words, conf=conf)
    logger.info("detector: yolo (%s)", YOLO_WEIGHTS)
    return detector
