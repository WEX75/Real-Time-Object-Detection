"""Zone geometry: point-in-polygon and mapping detections onto zones.

All coordinates are normalized to 0..1 of the frame.
"""

from __future__ import annotations

from collections.abc import Sequence

from .schemas import Box, Detection, Point, Zone

_EPSILON = 1e-9


def anchor_point(box: Box) -> Point:
    """Bottom-center of the box: where the object touches the surface."""
    x1, _, x2, y2 = box
    return ((x1 + x2) / 2, y2)


def _on_segment(p: Point, a: Point, b: Point) -> bool:
    (px, py), (ax, ay), (bx, by) = p, a, b
    cross = (bx - ax) * (py - ay) - (by - ay) * (px - ax)
    if abs(cross) > _EPSILON:
        return False
    return (
        min(ax, bx) - _EPSILON <= px <= max(ax, bx) + _EPSILON
        and min(ay, by) - _EPSILON <= py <= max(ay, by) + _EPSILON
    )


def point_in_polygon(point: Point, polygon: Sequence[Point]) -> bool:
    """Ray casting. Points on an edge or vertex count as inside."""
    n = len(polygon)
    if n < 3:
        return False
    x, y = point
    inside = False
    for i in range(n):
        a, b = polygon[i - 1], polygon[i]
        if _on_segment(point, a, b):
            return True
        (ax, ay), (bx, by) = a, b
        # Edge straddles the horizontal line through the point; the half-open
        # comparison counts a vertex exactly on that line only once.
        if (ay > y) != (by > y):
            x_cross = ax + (y - ay) * (bx - ax) / (by - ay)
            if x < x_cross:
                inside = not inside
    return inside


def assign(detections: Sequence[Detection], zones: Sequence[Zone]) -> dict[str, list[Detection]]:
    """Detections per zone id. A detection may belong to several overlapping zones."""
    result: dict[str, list[Detection]] = {zone.id: [] for zone in zones}
    for detection in detections:
        anchor = anchor_point(detection.box)
        for zone in zones:
            if point_in_polygon(anchor, zone.polygon):
                result[zone.id].append(detection)
    return result
