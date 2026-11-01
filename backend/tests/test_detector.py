from types import SimpleNamespace

import pytest

from app.detector import (
    FakeDetector,
    InvalidFrameError,
    _to_detections,
    create_detector,
    decode_jpeg,
    normalize_words,
)
from app.schemas import Detection

CUP = Detection(label="cup", confidence=0.8, box=(0.1, 0.1, 0.2, 0.2))
PERSON = Detection(label="person", confidence=0.9, box=(0.3, 0.1, 0.6, 0.9))


class _Tensor(list):
    """Stands in for a torch tensor: only `tolist` is used."""

    def tolist(self) -> list:
        return list(self)


def _result(rows: list[tuple[tuple[float, float, float, float], int, float]]) -> SimpleNamespace:
    boxes = SimpleNamespace(
        xyxyn=_Tensor([list(box) for box, _, _ in rows]),
        cls=_Tensor([float(cls) for _, cls, _ in rows]),
        conf=_Tensor([conf for _, _, conf in rows]),
    )
    return SimpleNamespace(boxes=boxes)


def test_decode_jpeg_returns_image(jpeg: bytes) -> None:
    image = decode_jpeg(jpeg)
    assert image.shape == (48, 64, 3)


@pytest.mark.parametrize("data", [b"", b"not a jpeg", b"\xff\xd8\xff" + b"\x00" * 20])
def test_decode_jpeg_rejects_garbage(data: bytes) -> None:
    with pytest.raises(InvalidFrameError):
        decode_jpeg(data)


def test_fake_detector_plays_script_then_repeats_last(jpeg: bytes) -> None:
    detector = FakeDetector([[CUP], [CUP, PERSON]])
    assert detector.detect(jpeg) == [CUP]
    assert detector.detect(jpeg) == [CUP, PERSON]
    assert detector.detect(jpeg) == [CUP, PERSON]
    detector.script([])
    assert detector.detect(jpeg) == []
    assert detector.calls == 4


def test_fake_detector_rejects_corrupt_frame() -> None:
    with pytest.raises(InvalidFrameError):
        FakeDetector([[CUP]]).detect(b"garbage")


def test_fake_detector_reports_unsupported_words() -> None:
    detector = FakeDetector(unsupported=["stapler"])
    assert detector.set_vocabulary(["cup", "stapler"]) == ["stapler"]
    assert detector.vocabulary == ["cup", "stapler"]


def test_results_are_filtered_to_vocabulary_and_clamped() -> None:
    names = {0: "person", 41: "Cup", 39: "bottle"}
    result = _result(
        [
            ((0.1, 0.2, 0.3, 0.4), 0, 0.9),
            ((-0.01, 0.5, 0.2, 1.002), 41, 0.6),
            ((0.5, 0.5, 0.6, 0.6), 39, 0.7),
        ]
    )
    detections = _to_detections(result, names, {"person", "cup"})
    assert [d.label for d in detections] == ["person", "cup"]
    assert detections[1].box == (0.0, 0.5, 0.2, 1.0)


def test_unknown_detector_kind_is_rejected() -> None:
    with pytest.raises(ValueError, match="VIGILO_DETECTOR"):
        create_detector(["person"], kind="magic")



def test_fake_detector_with_supported_list() -> None:
    detector = FakeDetector(supported=["person", "cup"])
    assert detector.set_vocabulary(["person", "stapler"]) == ["stapler"]


def test_normalize_words() -> None:
    assert normalize_words([" Person", "cup", "", "CUP", "  "]) == ["person", "cup"]
