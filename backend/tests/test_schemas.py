import pytest
from pydantic import ValidationError

from app.schemas import Detection, RuleIn, ZoneIn, normalize_label

TRIANGLE = [(0.1, 0.1), (0.9, 0.1), (0.5, 0.9)]


def test_normalize_label() -> None:
    assert normalize_label("  Cup ") == "cup"


def test_zone_accepts_valid_polygon_and_strips_name() -> None:
    zone = ZoneIn(name="  masa 1 ", polygon=TRIANGLE)
    assert zone.name == "masa 1"
    assert zone.polygon == TRIANGLE


@pytest.mark.parametrize(
    "polygon",
    [
        [(0.1, 0.1), (0.9, 0.1)],
        [(0.1, 0.1), (1.2, 0.1), (0.5, 0.9)],
        [(-0.1, 0.1), (0.9, 0.1), (0.5, 0.9)],
    ],
)
def test_zone_rejects_invalid_polygon(polygon: list[tuple[float, float]]) -> None:
    with pytest.raises(ValidationError):
        ZoneIn(name="masa", polygon=polygon)


def test_zone_rejects_blank_name() -> None:
    with pytest.raises(ValidationError):
        ZoneIn(name="   ", polygon=TRIANGLE)


def test_rule_normalizes_and_deduplicates_labels() -> None:
    rule = RuleIn(zone_id="z1", type="presence", target_labels=[" Cup", "cup", "BOTTLE", " "])
    assert rule.target_labels == ["cup", "bottle"]
    assert rule.seconds == 0
    assert rule.enabled is True


def test_rule_requires_a_label() -> None:
    with pytest.raises(ValidationError):
        RuleIn(zone_id="z1", type="presence", target_labels=["  "])


def test_count_threshold_requires_threshold() -> None:
    with pytest.raises(ValidationError, match="threshold is required"):
        RuleIn(zone_id="z1", type="count_threshold", target_labels=["person"])
    rule = RuleIn(zone_id="z1", type="count_threshold", target_labels=["person"], threshold=3)
    assert rule.threshold == 3


def test_rule_rejects_negative_seconds_and_unknown_type() -> None:
    with pytest.raises(ValidationError):
        RuleIn(zone_id="z1", type="presence", target_labels=["cup"], seconds=-1)
    with pytest.raises(ValidationError):
        RuleIn(zone_id="z1", type="zone_empty", target_labels=["cup"])


@pytest.mark.parametrize(
    "box",
    [(0.5, 0.1, 0.4, 0.2), (0.1, 0.5, 0.2, 0.4), (0.1, 0.1, 1.1, 0.2)],
)
def test_detection_rejects_invalid_box(box: tuple[float, float, float, float]) -> None:
    with pytest.raises(ValidationError):
        Detection(label="cup", confidence=0.5, box=box)


def test_detection_rejects_confidence_out_of_range() -> None:
    with pytest.raises(ValidationError):
        Detection(label="cup", confidence=1.5, box=(0.1, 0.1, 0.2, 0.2))
