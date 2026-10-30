from collections.abc import Sequence

import pytest

from app.clock import FakeClock
from app.rules import VACATE_SECONDS, DebouncedCondition, EngineResult, RuleEngine
from app.schemas import Detection, EventIn, Rule, Zone, ZoneState

FREE, OCCUPIED, NEEDS_CLEARING = ZoneState.FREE, ZoneState.OCCUPIED, ZoneState.NEEDS_CLEARING
STEP = 0.1  # 10 FPS, the fastest rate the client sends at

TABLE_1 = Zone(id="z1", name="masa 1", polygon=[(0.0, 0.5), (0.5, 0.5), (0.5, 1.0), (0.0, 1.0)])
TABLE_2 = Zone(id="z2", name="masa 2", polygon=[(0.5, 0.5), (1.0, 0.5), (1.0, 1.0), (0.5, 1.0)])


def det(label: str, x: float = 0.25, y: float = 0.8) -> Detection:
    """Detection whose bottom-center is (x, y). The default point is on masa 1."""
    return Detection(label=label, confidence=0.9, box=(x - 0.05, y - 0.2, x + 0.05, y))


PERSON = det("person")
CUP = det("cup", x=0.3)
BOTTLE = det("bottle", x=0.2)


def rule(
    type: str = "left_unattended",
    labels: Sequence[str] = ("cup", "bottle"),
    seconds: float = 20,
    rule_id: str = "r1",
    zone_id: str = "z1",
    **extra: object,
) -> Rule:
    return Rule(id=rule_id, zone_id=zone_id, type=type, target_labels=list(labels), seconds=seconds, **extra)


class Harness:
    """Feeds the same detections to the engine at 10 FPS on a fake clock."""

    def __init__(self, zones: Sequence[Zone] = (TABLE_1,), rules: Sequence[Rule] = ()) -> None:
        self.clock = FakeClock()
        self.engine = RuleEngine(zones, rules)
        self.events: list[EventIn] = []
        self.last: EngineResult | None = None

    def run(self, detections: Sequence[Detection], seconds: float) -> list[EventIn]:
        new_events: list[EventIn] = []
        for _ in range(round(seconds / STEP)):
            self.clock.advance(STEP)
            self.last = self.engine.update(detections, self.clock.now())
            new_events.extend(self.last.events)
        self.events.extend(new_events)
        return new_events

    @property
    def result(self) -> EngineResult:
        assert self.last is not None, "run() was never called"
        return self.last

    def state(self, zone_id: str = "z1") -> ZoneState:
        return next(z.state for z in self.result.zones if z.id == zone_id)

    def kinds(self, events: Sequence[EventIn] | None = None) -> list[str]:
        """Compact event log: 'FREE->OCCUPIED', 'rule_triggered:r1', ..."""
        result = []
        for event in self.events if events is None else events:
            if event.kind == "zone_state_changed":
                result.append(f"{event.detail['from']}->{event.detail['to']}")
            else:
                result.append(f"{event.kind}:{event.rule_id}")
        return result


def occupied_with_cup(h: Harness) -> None:
    h.run([PERSON, CUP], 5)
    assert h.state() == OCCUPIED


def needs_clearing(h: Harness) -> None:
    occupied_with_cup(h)
    h.run([CUP], 20.5)
    assert h.state() == NEEDS_CLEARING


# --- debounce primitive ---------------------------------------------------------


def test_debounced_condition_tracks_held_and_absent_time() -> None:
    c = DebouncedCondition(grace=0.5)
    c.update(False, 0.0)
    assert not c.active
    assert c.absent_for(1.0) == pytest.approx(1.0)
    c.update(True, 1.0)
    c.update(False, 1.3)  # short gap: still active, but the gap is not counted yet
    assert c.active
    assert c.held_for(1.3) == pytest.approx(0.0)
    c.update(True, 1.4)  # seen again: the bridged gap counts
    assert c.held_for(1.4) == pytest.approx(0.4)
    c.update(False, 1.8)
    assert c.active
    c.update(False, 1.9)  # 0.5 s since last seen at 1.4
    assert not c.active
    assert c.held_for(2.0) == 0.0
    assert c.absent_for(2.0) == pytest.approx(0.6)  # measured from the last sighting


# --- zone state machine -----------------------------------------------------------


def test_free_to_occupied_after_one_second_of_person() -> None:
    h = Harness(rules=[rule()])
    h.run([PERSON], 0.8)
    assert h.state() == FREE
    h.run([PERSON], 0.4)
    assert h.state() == OCCUPIED
    assert h.kinds() == ["FREE->OCCUPIED"]


def test_short_visit_does_not_occupy() -> None:
    h = Harness(rules=[rule()])
    h.run([PERSON], 0.7)
    h.run([], 5)
    assert h.state() == FREE
    assert h.events == []


def test_occupied_to_needs_clearing_when_objects_are_left() -> None:
    h = Harness(rules=[rule(seconds=20)])
    occupied_with_cup(h)
    h.run([CUP], 19.7)
    assert h.state() == OCCUPIED
    h.run([CUP], 0.5)
    assert h.state() == NEEDS_CLEARING
    assert h.kinds() == ["FREE->OCCUPIED", "rule_triggered:r1", "OCCUPIED->NEEDS_CLEARING"]
    triggered = h.events[1]
    assert triggered.zone_name == "masa 1"
    assert triggered.detail == {
        "type": "left_unattended",
        "target_labels": ["cup", "bottle"],
        "seconds": 20,
        "counts": {"cup": 1, "bottle": 0},
    }


def test_occupied_to_free_when_nothing_is_left() -> None:
    h = Harness(rules=[rule(seconds=20)])
    occupied_with_cup(h)
    h.run([], 19.7)
    assert h.state() == OCCUPIED
    h.run([], 0.5)
    assert h.state() == FREE
    assert h.kinds() == ["FREE->OCCUPIED", "OCCUPIED->FREE"]


def test_needs_clearing_to_free_after_objects_are_gone_for_two_seconds() -> None:
    h = Harness(rules=[rule()])
    needs_clearing(h)
    h.run([], 1.8)
    assert h.state() == NEEDS_CLEARING
    h.run([], 0.4)
    assert h.state() == FREE
    assert h.kinds()[-2:] == ["rule_cleared:r1", "NEEDS_CLEARING->FREE"]


def test_needs_clearing_to_occupied_when_person_returns() -> None:
    h = Harness(rules=[rule()])
    needs_clearing(h)
    h.run([PERSON, CUP], 0.8)
    assert h.state() == NEEDS_CLEARING
    h.run([PERSON, CUP], 0.4)
    assert h.state() == OCCUPIED
    assert h.kinds()[-2:] == ["rule_cleared:r1", "NEEDS_CLEARING->OCCUPIED"]


def test_waiter_clearing_quickly_does_not_occupy() -> None:
    h = Harness(rules=[rule()])
    needs_clearing(h)
    h.run([PERSON, CUP], 0.4)  # takes the cup in under a second
    h.run([], 3)
    assert h.state() == FREE
    assert "NEEDS_CLEARING->OCCUPIED" not in h.kinds()


def test_without_left_unattended_rule_zone_only_toggles_free_and_occupied() -> None:
    h = Harness(rules=[])
    occupied_with_cup(h)
    h.run([CUP], VACATE_SECONDS + 0.3)
    assert h.state() == FREE
    h.run([CUP], 60)
    assert h.state() == FREE
    assert h.kinds() == ["FREE->OCCUPIED", "OCCUPIED->FREE"]


def test_objects_left_in_free_zone_trigger_rule_but_zone_stays_free() -> None:
    # The state diagram has no FREE -> NEEDS_CLEARING edge; the alert still fires.
    h = Harness(rules=[rule(seconds=20)])
    h.run([CUP], 20.5)
    assert h.state() == FREE
    assert h.kinds() == ["rule_triggered:r1"]


def test_object_noticed_after_person_left_delays_needs_clearing() -> None:
    h = Harness(rules=[rule(seconds=20)])
    h.run([PERSON], 5)
    h.run([], 3)
    h.run([CUP], 18)  # person gone for 21 s, cup seen for 18 s
    assert h.state() == OCCUPIED
    h.run([CUP], 2.3)
    assert h.state() == NEEDS_CLEARING


# --- debounce in the engine ----------------------------------------------------------


def test_person_missed_for_a_few_frames_keeps_zone_occupied() -> None:
    h = Harness(rules=[])
    h.run([PERSON], 2)
    for _ in range(10):
        h.run([], 0.3)
        h.run([PERSON], 0.2)
    assert h.state() == OCCUPIED
    assert h.kinds() == ["FREE->OCCUPIED"]


def test_person_flickering_while_entering_still_counts_as_continuous() -> None:
    h = Harness(rules=[])
    for _ in range(4):
        h.run([PERSON], 0.2)
        h.run([], 0.2)
    assert h.state() == OCCUPIED


def test_object_flicker_does_not_restart_unattended_timer() -> None:
    h = Harness(rules=[rule(seconds=20)])
    occupied_with_cup(h)
    for _ in range(20):
        h.run([CUP], 0.7)
        h.run([], 0.3)
    assert h.state() == OCCUPIED
    h.run([CUP], 0.4)
    assert h.state() == NEEDS_CLEARING
    assert h.kinds().count("rule_triggered:r1") == 1


def test_gap_longer_than_debounce_interrupts_condition() -> None:
    h = Harness(rules=[rule(type="presence", labels=["cup"], seconds=2)])
    h.run([CUP], 2.3)
    assert h.kinds() == ["rule_triggered:r1"]
    assert h.run([], 0.3) == []
    assert h.kinds(h.run([], 0.4)) == ["rule_cleared:r1"]
    assert h.run([CUP], 1.7) == []  # timer restarted from zero
    assert h.kinds(h.run([CUP], 0.5)) == ["rule_triggered:r1"]


# --- event emission --------------------------------------------------------------------


def test_events_are_emitted_once_not_per_frame() -> None:
    h = Harness(rules=[rule()])
    needs_clearing(h)
    assert h.run([CUP], 60) == []
    assert h.result.events == []
    assert h.kinds() == ["FREE->OCCUPIED", "rule_triggered:r1", "OCCUPIED->NEEDS_CLEARING"]


def test_event_timestamps_come_from_the_given_time() -> None:
    h = Harness(rules=[])
    h.run([PERSON], 1.5)
    event = h.events[0]
    assert event.created_at.tzinfo is not None
    assert event.created_at.timestamp() == pytest.approx(h.clock.now() - 0.4, abs=0.11)


# --- rule types --------------------------------------------------------------------------


def test_presence_rule() -> None:
    h = Harness(rules=[rule(type="presence", labels=["person"], seconds=3)])
    h.run([PERSON], 2.8)
    assert "rule_triggered:r1" not in h.kinds()
    triggered = h.run([PERSON], 0.4)
    assert h.kinds(triggered) == ["rule_triggered:r1"]
    assert triggered[0].detail["counts"] == {"person": 1}
    cleared = h.run([], 0.7)
    assert "rule_cleared:r1" in h.kinds(cleared)
    clear_event = next(e for e in cleared if e.kind == "rule_cleared")
    assert clear_event.detail["type"] == "presence"
    assert clear_event.detail["active_seconds"] == pytest.approx(0.5, abs=0.15)


def test_presence_rule_with_zero_seconds_triggers_on_first_frame() -> None:
    h = Harness(rules=[rule(type="presence", labels=["bottle"], seconds=0)])
    assert h.kinds(h.run([BOTTLE], 0.1)) == ["rule_triggered:r1"]


def test_count_threshold_rule_needs_strictly_more_than_threshold() -> None:
    people = [det("person", x=x) for x in (0.1, 0.2, 0.3)]
    h = Harness(rules=[rule(type="count_threshold", labels=["person"], seconds=1, threshold=2)])
    h.run(people[:2], 3)
    assert "rule_triggered:r1" not in h.kinds()
    h.run(people, 0.8)
    assert "rule_triggered:r1" not in h.kinds()
    triggered = h.run(people, 0.4)
    assert h.kinds(triggered) == ["rule_triggered:r1"]
    assert triggered[0].detail["threshold"] == 2
    assert triggered[0].detail["counts"] == {"person": 3}
    assert h.kinds(h.run(people[:2], 0.7)) == ["rule_cleared:r1"]


def test_left_unattended_rule_counts_any_target_label() -> None:
    h = Harness(rules=[rule(seconds=5)])
    h.run([BOTTLE], 5.2)
    assert h.kinds() == ["rule_triggered:r1"]


def test_disabled_rules_are_ignored() -> None:
    rules = [
        rule(enabled=False),
        rule(type="presence", labels=["cup"], seconds=0, rule_id="r2", enabled=False),
    ]
    h = Harness(rules=rules)
    occupied_with_cup(h)
    h.run([CUP], 30)
    assert h.state() == FREE  # behaves as if the zone had no left_unattended rule
    assert h.kinds() == ["FREE->OCCUPIED", "OCCUPIED->FREE"]


def test_labels_are_compared_normalized() -> None:
    h = Harness(rules=[rule(type="presence", labels=["CUP "], seconds=0)])
    h.run([det("  Cup ")], 0.1)
    assert h.kinds() == ["rule_triggered:r1"]
    assert h.result.zones[0].counts == {"cup": 1}


# --- zones and configuration -----------------------------------------------------------


def test_zones_are_independent_and_report_counts() -> None:
    h = Harness(zones=[TABLE_1, TABLE_2], rules=[rule(zone_id="z2")])
    other_person = det("person", x=0.75)
    other_cup = det("cup", x=0.8)
    h.run([other_person, other_cup, other_cup], 2)
    assert h.state("z1") == FREE
    assert h.state("z2") == OCCUPIED
    assert [(z.id, z.name, z.counts) for z in h.result.zones] == [
        ("z1", "masa 1", {}),
        ("z2", "masa 2", {"person": 1, "cup": 2}),
    ]


def test_detections_outside_every_zone_are_ignored() -> None:
    h = Harness(rules=[rule(type="presence", labels=["cup"], seconds=0)])
    h.run([det("person", y=0.3), det("cup", y=0.3)], 3)
    assert h.state() == FREE
    assert h.events == []


def test_rule_for_unknown_zone_is_ignored() -> None:
    h = Harness(rules=[rule(type="presence", labels=["cup"], seconds=0, zone_id="missing")])
    h.run([CUP], 1)
    assert h.events == []


def test_reconfigure_with_same_rules_keeps_timers_and_states() -> None:
    presence = rule(type="presence", labels=["cup"], seconds=2, rule_id="r2")
    h = Harness(rules=[presence])
    h.run([PERSON, CUP], 1.5)
    h.engine.configure([TABLE_1], [presence])
    h.run([PERSON, CUP], 0.7)
    assert h.state() == OCCUPIED
    assert h.kinds() == ["FREE->OCCUPIED", "rule_triggered:r2"]


@pytest.mark.parametrize(
    ("new_rules", "reason"),
    [
        ([rule(type="presence", labels=["cup"], seconds=0, enabled=False)], "rule_disabled"),
        ([], "rule_removed"),
        ([rule(type="presence", labels=["cup", "bottle"], seconds=0)], "rule_changed"),
    ],
)
def test_triggered_rule_is_cleared_when_configuration_changes(new_rules: list[Rule], reason: str) -> None:
    h = Harness(rules=[rule(type="presence", labels=["cup"], seconds=0)])
    h.run([CUP], 1)
    h.engine.configure([TABLE_1], new_rules)
    events = h.run([CUP], 0.1)
    assert events[0].kind == "rule_cleared"
    assert events[0].rule_id == "r1"
    assert events[0].detail["reason"] == reason


def test_disabling_triggered_rule_clears_it_once() -> None:
    r = rule(type="presence", labels=["cup"], seconds=0)
    h = Harness(rules=[r])
    h.run([CUP], 1)
    h.engine.configure([TABLE_1], [r.model_copy(update={"enabled": False})])
    h.run([CUP], 5)
    assert h.kinds() == ["rule_triggered:r1", "rule_cleared:r1"]


def test_removing_a_zone_drops_its_state_without_events() -> None:
    h = Harness(zones=[TABLE_1, TABLE_2], rules=[rule(type="presence", labels=["cup"], seconds=0)])
    h.run([PERSON, CUP], 2)
    h.engine.configure([TABLE_2], [])
    assert h.run([PERSON, CUP], 1) == []
    assert [z.id for z in h.result.zones] == ["z2"]


def test_renaming_a_zone_keeps_its_state() -> None:
    h = Harness(rules=[])
    h.run([PERSON], 2)
    h.engine.configure([TABLE_1.model_copy(update={"name": "bar"})], [])
    h.run([PERSON], 0.1)
    assert h.result.zones[0].name == "bar"
    assert h.state() == OCCUPIED
