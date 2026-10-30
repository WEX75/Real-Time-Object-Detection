import pytest

from app.schemas import Detection, Zone
from app.zones import anchor_point, assign, point_in_polygon

SQUARE = [(0.2, 0.2), (0.6, 0.2), (0.6, 0.6), (0.2, 0.6)]
# "U" shape: the notch between the arms (x in 0.4..0.6, y in 0.2..0.6) is outside.
CONCAVE = [(0.2, 0.2), (0.4, 0.2), (0.4, 0.6), (0.6, 0.6), (0.6, 0.2), (0.8, 0.2), (0.8, 0.8), (0.2, 0.8)]
FULL_FRAME = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]


def detection(box: tuple[float, float, float, float], label: str = "cup") -> Detection:
    return Detection(label=label, confidence=0.9, box=box)


def test_point_inside() -> None:
    assert point_in_polygon((0.4, 0.4), SQUARE)


@pytest.mark.parametrize("point", [(0.1, 0.4), (0.7, 0.4), (0.4, 0.1), (0.4, 0.7), (0.9, 0.9)])
def test_point_outside(point: tuple[float, float]) -> None:
    assert not point_in_polygon(point, SQUARE)


@pytest.mark.parametrize("point", [(0.4, 0.2), (0.6, 0.4), (0.4, 0.6), (0.2, 0.4)])
def test_point_on_edge_counts_as_inside(point: tuple[float, float]) -> None:
    assert point_in_polygon(point, SQUARE)


@pytest.mark.parametrize("point", SQUARE)
def test_point_on_vertex_counts_as_inside(point: tuple[float, float]) -> None:
    assert point_in_polygon(point, SQUARE)


def test_point_on_diagonal_edge() -> None:
    triangle = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]
    assert point_in_polygon((0.5, 0.5), triangle)
    assert not point_in_polygon((0.51, 0.51), triangle)


def test_concave_polygon_notch_is_outside() -> None:
    assert not point_in_polygon((0.5, 0.4), CONCAVE)


@pytest.mark.parametrize("point", [(0.3, 0.4), (0.7, 0.4), (0.5, 0.7)])
def test_concave_polygon_arms_and_base_are_inside(point: tuple[float, float]) -> None:
    assert point_in_polygon(point, CONCAVE)


def test_ray_through_vertex_is_counted_once() -> None:
    # The horizontal ray from (0.3, 0.6) passes exactly through the vertices
    # (0.4, 0.6) and (0.6, 0.6) of the notch.
    assert point_in_polygon((0.3, 0.6), CONCAVE)
    assert point_in_polygon((0.7, 0.6), CONCAVE)


@pytest.mark.parametrize("point", [(0.0, 0.0), (1.0, 1.0), (0.5, 1.0), (0.0, 0.5), (1.0, 0.0)])
def test_full_frame_zone_contains_frame_border(point: tuple[float, float]) -> None:
    assert point_in_polygon(point, FULL_FRAME)


def test_degenerate_polygon_contains_nothing() -> None:
    assert not point_in_polygon((0.5, 0.5), [(0.0, 0.0), (1.0, 1.0)])


def test_anchor_is_bottom_center() -> None:
    assert anchor_point((0.2, 0.1, 0.4, 0.5)) == pytest.approx((0.3, 0.5))


def test_assign_uses_bottom_center_of_box() -> None:
    zone = Zone(id="z1", name="masa 1", polygon=[(0.0, 0.5), (1.0, 0.5), (1.0, 1.0), (0.0, 1.0)])
    # Box mostly above the zone but standing in it.
    standing_in = detection((0.4, 0.1, 0.6, 0.55), label="person")
    # Box whose top reaches into the zone but whose bottom is outside.
    hanging_above = detection((0.4, 0.0, 0.6, 0.45))
    result = assign([standing_in, hanging_above], [zone])
    assert result == {"z1": [standing_in]}


def test_assign_box_touching_bottom_of_frame() -> None:
    zone = Zone(id="z1", name="masa 1", polygon=FULL_FRAME)
    det = detection((0.8, 0.7, 1.0, 1.0))
    assert assign([det], [zone]) == {"z1": [det]}


def test_assign_overlapping_zones_and_empty_zone() -> None:
    left = Zone(id="left", name="left", polygon=[(0.0, 0.0), (0.6, 0.0), (0.6, 1.0), (0.0, 1.0)])
    right = Zone(id="right", name="right", polygon=[(0.4, 0.0), (1.0, 0.0), (1.0, 1.0), (0.4, 1.0)])
    far = Zone(id="far", name="far", polygon=[(0.0, 0.0), (0.1, 0.0), (0.1, 0.1)])
    middle = detection((0.45, 0.2, 0.55, 0.5))
    result = assign([middle], [left, right, far])
    assert result == {"left": [middle], "right": [middle], "far": []}


def test_assign_without_zones() -> None:
    assert assign([detection((0.1, 0.1, 0.2, 0.2))], []) == {}
