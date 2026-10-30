"""Pydantic models shared by the REST API, the WebSocket and the rule engine."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Point = tuple[float, float]
Box = tuple[float, float, float, float]
RuleType = Literal["presence", "left_unattended", "count_threshold"]
EventKind = Literal["zone_state_changed", "rule_triggered", "rule_cleared"]


def normalize_label(label: str) -> str:
    """Labels are compared lower-case and without surrounding whitespace."""
    return label.strip().lower()


def _check_unit(value: float) -> float:
    if not 0.0 <= value <= 1.0:
        raise ValueError("coordinates must be normalized to [0, 1]")
    return value


class ZoneState(str, Enum):
    FREE = "FREE"
    OCCUPIED = "OCCUPIED"
    NEEDS_CLEARING = "NEEDS_CLEARING"


class Detection(BaseModel):
    label: str
    confidence: float = Field(ge=0.0, le=1.0)
    box: Box  # x1, y1, x2, y2 normalized to 0..1

    @field_validator("box")
    @classmethod
    def _box_in_frame(cls, box: Box) -> Box:
        x1, y1, x2, y2 = (_check_unit(v) for v in box)
        if x1 > x2 or y1 > y2:
            raise ValueError("box must be (x1, y1, x2, y2) with x1 <= x2 and y1 <= y2")
        return box


class ZoneIn(BaseModel):
    name: str
    polygon: list[Point]

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, name: str) -> str:
        name = name.strip()
        if not name:
            raise ValueError("zone name must not be empty")
        return name

    @field_validator("polygon")
    @classmethod
    def _valid_polygon(cls, polygon: list[Point]) -> list[Point]:
        if len(polygon) < 3:
            raise ValueError("polygon needs at least 3 points")
        for x, y in polygon:
            _check_unit(x)
            _check_unit(y)
        return polygon


class Zone(ZoneIn):
    id: str


class RuleIn(BaseModel):
    zone_id: str
    type: RuleType
    target_labels: list[str]
    seconds: float = Field(default=0, ge=0)
    threshold: int | None = Field(default=None, ge=0)
    enabled: bool = True

    @field_validator("target_labels")
    @classmethod
    def _normalize_labels(cls, labels: list[str]) -> list[str]:
        normalized = list(dict.fromkeys(normalize_label(label) for label in labels if label.strip()))
        if not normalized:
            raise ValueError("at least one target label is required")
        return normalized

    @model_validator(mode="after")
    def _threshold_for_count(self) -> RuleIn:
        if self.type == "count_threshold" and self.threshold is None:
            raise ValueError("threshold is required for count_threshold rules")
        return self


class Rule(RuleIn):
    id: str


class EventIn(BaseModel):
    created_at: datetime  # UTC
    zone_id: str
    zone_name: str
    rule_id: str | None
    kind: EventKind
    detail: dict[str, Any]


class Event(EventIn):
    id: int


class ZoneStatus(BaseModel):
    """Per-zone entry of the telemetry message."""

    id: str
    name: str
    state: ZoneState
    counts: dict[str, int]
