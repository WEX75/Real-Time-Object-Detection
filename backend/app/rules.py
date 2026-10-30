"""Rule engine: zone state machine, rule timers and debounce.

Pure Python. The engine receives the detections of one frame and a timestamp;
it knows nothing about cameras, OpenCV or models, and never reads the clock.
"""

from __future__ import annotations

import threading
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

from .schemas import Detection, EventIn, EventKind, Rule, RuleType, Zone, ZoneState, ZoneStatus, normalize_label
from .zones import assign

PERSON = "person"
DEBOUNCE_SECONDS = 0.5  # a condition is interrupted only after missing this long
OCCUPY_SECONDS = 1.0  # person present this long -> OCCUPIED
CLEAR_SECONDS = 2.0  # NEEDS_CLEARING -> FREE after target objects are gone this long
VACATE_SECONDS = 2.0  # OCCUPIED -> FREE when the zone has no left_unattended rule


class DebouncedCondition:
    """A condition that starts when first observed and ends only after it has
    not been observed for `grace` seconds in a row.

    Detectors miss objects for a frame or two; without this, states flicker.
    """

    def __init__(self, grace: float = DEBOUNCE_SECONDS) -> None:
        self._grace = grace
        self._since: float | None = None
        self._last_seen: float | None = None
        self._ended_at: float | None = None

    def update(self, observed: bool, now: float) -> None:
        if observed:
            if self._since is None:
                self._since = now
            self._last_seen = now
        elif self._since is not None:
            assert self._last_seen is not None
            if now - self._last_seen >= self._grace:
                self._since = None
                self._ended_at = self._last_seen
        elif self._ended_at is None:
            self._ended_at = now  # never observed: absent from the first update

    @property
    def active(self) -> bool:
        return self._since is not None

    def held_for(self, now: float) -> float:
        """How long the condition has been active, up to its last sighting.

        The grace period after the last sighting does not count, so a
        0.7 s visit never adds up to 1 s; a bridged gap counts once the
        condition is seen again.
        """
        if self._since is None or self._last_seen is None:
            return 0.0
        return self._last_seen - self._since

    def absent_for(self, now: float) -> float:
        """Time since the condition was last observed (0 while active)."""
        if self._since is not None or self._ended_at is None:
            return 0.0
        return now - self._ended_at


def _target_count(rule: Rule, counts: Counter[str]) -> int:
    return sum(counts[label] for label in rule.target_labels)


def _presence(rule: Rule, counts: Counter[str]) -> bool:
    return _target_count(rule, counts) > 0


def _left_unattended(rule: Rule, counts: Counter[str]) -> bool:
    return _target_count(rule, counts) > 0 and counts[PERSON] == 0


def _count_threshold(rule: Rule, counts: Counter[str]) -> bool:
    assert rule.threshold is not None
    return _target_count(rule, counts) > rule.threshold


_PREDICATES: dict[RuleType, Callable[[Rule, Counter[str]], bool]] = {
    "presence": _presence,
    "left_unattended": _left_unattended,
    "count_threshold": _count_threshold,
}


class RuleTracker:
    """Timer and trigger flag of one enabled rule."""

    def __init__(self, rule: Rule) -> None:
        self.rule = rule
        self.condition = DebouncedCondition()
        self.triggered_at: float | None = None

    @property
    def triggered(self) -> bool:
        return self.triggered_at is not None

    def update(self, counts: Counter[str], now: float) -> tuple[EventKind, dict[str, Any]] | None:
        self.condition.update(_PREDICATES[self.rule.type](self.rule, counts), now)
        if not self.triggered and self.condition.active and self.condition.held_for(now) >= self.rule.seconds:
            self.triggered_at = now
            return "rule_triggered", self._trigger_detail(counts)
        if self.triggered and not self.condition.active:
            return "rule_cleared", self.clear(now)
        return None

    def clear(self, now: float) -> dict[str, Any]:
        assert self.triggered_at is not None
        detail = {"type": self.rule.type, "active_seconds": round(now - self.triggered_at, 1)}
        self.triggered_at = None
        return detail

    def _trigger_detail(self, counts: Counter[str]) -> dict[str, Any]:
        detail: dict[str, Any] = {
            "type": self.rule.type,
            "target_labels": list(self.rule.target_labels),
            "seconds": self.rule.seconds,
            "counts": {label: counts[label] for label in self.rule.target_labels},
        }
        if self.rule.threshold is not None:
            detail["threshold"] = self.rule.threshold
        return detail


class ZoneTracker:
    """Context of the zone state machine: current state plus the signals the
    state objects look at."""

    def __init__(self, zone: Zone) -> None:
        self.zone = zone
        self.state = ZoneState.FREE
        self.person = DebouncedCondition()
        self.targets = DebouncedCondition()
        self.unattended: RuleTracker | None = None

    @property
    def vacate_seconds(self) -> float:
        return self.unattended.rule.seconds if self.unattended else VACATE_SECONDS

    def update(
        self, counts: Counter[str], unattended: RuleTracker | None, now: float
    ) -> tuple[ZoneState, ZoneState] | None:
        """Advance the state machine by one frame; return (from, to) on a change."""
        self.unattended = unattended
        labels = unattended.rule.target_labels if unattended else []
        self.person.update(counts[PERSON] > 0, now)
        self.targets.update(any(counts[label] > 0 for label in labels), now)
        new_state = _STATES[self.state].next_state(self, now)
        if new_state is self.state:
            return None
        old_state, self.state = self.state, new_state
        return old_state, new_state


class ZoneStateBehavior(Protocol):
    def next_state(self, zone: ZoneTracker, now: float) -> ZoneState: ...


class FreeState:
    def next_state(self, zone: ZoneTracker, now: float) -> ZoneState:
        if zone.person.held_for(now) >= OCCUPY_SECONDS:
            return ZoneState.OCCUPIED
        return ZoneState.FREE


class OccupiedState:
    def next_state(self, zone: ZoneTracker, now: float) -> ZoneState:
        if zone.person.active:
            return ZoneState.OCCUPIED
        # NEEDS_CLEARING exactly when the left_unattended rule fires, so the
        # zone state and the alert in the log never disagree.
        if zone.unattended is not None and zone.unattended.triggered:
            return ZoneState.NEEDS_CLEARING
        if zone.person.absent_for(now) >= zone.vacate_seconds and not zone.targets.active:
            return ZoneState.FREE
        return ZoneState.OCCUPIED


class NeedsClearingState:
    def next_state(self, zone: ZoneTracker, now: float) -> ZoneState:
        if zone.person.held_for(now) >= OCCUPY_SECONDS:
            return ZoneState.OCCUPIED
        if zone.targets.absent_for(now) >= CLEAR_SECONDS:
            return ZoneState.FREE
        return ZoneState.NEEDS_CLEARING


_STATES: dict[ZoneState, ZoneStateBehavior] = {
    ZoneState.FREE: FreeState(),
    ZoneState.OCCUPIED: OccupiedState(),
    ZoneState.NEEDS_CLEARING: NeedsClearingState(),
}


@dataclass
class EngineResult:
    zones: list[ZoneStatus]
    events: list[EventIn]


class RuleEngine:
    """Evaluates zones and rules frame by frame. Thread-safe: `configure` may be
    called from API handlers while frames are being processed."""

    def __init__(self, zones: Sequence[Zone] = (), rules: Sequence[Rule] = ()) -> None:
        self._lock = threading.Lock()
        self._zones: dict[str, ZoneTracker] = {}
        self._rules: dict[str, RuleTracker] = {}
        self._rules_by_zone: dict[str, list[RuleTracker]] = {}
        # Clears caused by configuration changes; emitted on the next frame,
        # which is the first moment with a timestamp.
        self._pending: list[tuple[RuleTracker, Zone, str]] = []
        self.configure(zones, rules)

    def configure(self, zones: Sequence[Zone], rules: Sequence[Rule]) -> None:
        """Replace the configuration, keeping the state of unchanged zones and rules."""
        with self._lock:
            zone_trackers: dict[str, ZoneTracker] = {}
            for zone in zones:
                tracker = self._zones.get(zone.id) or ZoneTracker(zone)
                tracker.zone = zone
                zone_trackers[zone.id] = tracker

            rule_trackers: dict[str, RuleTracker] = {}
            for rule in rules:
                if rule.enabled and rule.zone_id in zone_trackers:
                    old = self._rules.get(rule.id)
                    rule_trackers[rule.id] = old if old is not None and old.rule == rule else RuleTracker(rule)

            self._queue_dropped_triggers(zone_trackers, rule_trackers, {rule.id: rule for rule in rules})
            self._zones = zone_trackers
            self._rules = rule_trackers
            self._rules_by_zone = {zone_id: [] for zone_id in zone_trackers}
            for tracker in rule_trackers.values():
                self._rules_by_zone[tracker.rule.zone_id].append(tracker)

    def _queue_dropped_triggers(
        self,
        zone_trackers: dict[str, ZoneTracker],
        rule_trackers: dict[str, RuleTracker],
        rules_by_id: dict[str, Rule],
    ) -> None:
        """A triggered rule that is removed, disabled or changed gets a rule_cleared."""
        for rule_id, old in self._rules.items():
            zone_tracker = zone_trackers.get(old.rule.zone_id)
            # A deleted zone takes its history with it: no clear event.
            if not old.triggered or rule_trackers.get(rule_id) is old or zone_tracker is None:
                continue
            new_rule = rules_by_id.get(rule_id)
            if new_rule is None:
                reason = "rule_removed"
            elif not new_rule.enabled:
                reason = "rule_disabled"
            else:
                reason = "rule_changed"
            self._pending.append((old, zone_tracker.zone, reason))

    def update(self, detections: Sequence[Detection], now: float) -> EngineResult:
        with self._lock:
            created_at = datetime.fromtimestamp(now, timezone.utc)
            events: list[EventIn] = []

            def emit(zone: Zone, rule_id: str | None, kind: EventKind, detail: dict[str, Any]) -> None:
                events.append(
                    EventIn(
                        created_at=created_at,
                        zone_id=zone.id,
                        zone_name=zone.name,
                        rule_id=rule_id,
                        kind=kind,
                        detail=detail,
                    )
                )

            for tracker, zone, reason in self._pending:
                emit(zone, tracker.rule.id, "rule_cleared", {**tracker.clear(now), "reason": reason})
            self._pending.clear()

            per_zone = assign(detections, [tracker.zone for tracker in self._zones.values()])
            statuses: list[ZoneStatus] = []
            for zone_id, zone_tracker in self._zones.items():
                zone = zone_tracker.zone
                counts = Counter(normalize_label(d.label) for d in per_zone[zone_id])

                unattended: RuleTracker | None = None
                for rule_tracker in self._rules_by_zone[zone_id]:
                    change = rule_tracker.update(counts, now)
                    if change is not None:
                        emit(zone, rule_tracker.rule.id, *change)
                    if unattended is None and rule_tracker.rule.type == "left_unattended":
                        unattended = rule_tracker

                transition = zone_tracker.update(counts, unattended, now)
                if transition is not None:
                    old_state, new_state = transition
                    emit(zone, None, "zone_state_changed", {"from": old_state.value, "to": new_state.value})

                statuses.append(ZoneStatus(id=zone.id, name=zone.name, state=zone_tracker.state, counts=dict(counts)))
            return EngineResult(zones=statuses, events=events)
