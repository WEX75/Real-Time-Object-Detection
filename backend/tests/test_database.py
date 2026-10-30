from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.database import (
    Database,
    EventRepository,
    RuleRepository,
    UnknownZoneError,
    VocabularyRepository,
    ZoneRepository,
)
from app.schemas import EventIn, RuleIn, ZoneIn

TRIANGLE = [(0.1, 0.1), (0.9, 0.1), (0.5, 0.9)]
T0 = datetime(2026, 11, 2, 10, 0, tzinfo=timezone.utc)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "events.sqlite3"


@pytest.fixture
def db(db_path: Path) -> Iterator[Database]:
    database = Database(db_path)
    yield database
    database.close()


def event(zone_id: str = "z1", kind: str = "zone_state_changed", seconds: int = 0) -> EventIn:
    return EventIn(
        created_at=T0 + timedelta(seconds=seconds),
        zone_id=zone_id,
        zone_name="masa 1",
        rule_id=None if kind == "zone_state_changed" else "r1",
        kind=kind,
        detail={"from": "OCCUPIED", "to": "NEEDS_CLEARING"},
    )


# --- zones -----------------------------------------------------------------------


def test_zone_roundtrip_in_insertion_order(db: Database) -> None:
    zones = ZoneRepository(db)
    first = zones.add(ZoneIn(name="masa 1", polygon=TRIANGLE))
    second = zones.add(ZoneIn(name="masa 2", polygon=TRIANGLE))
    assert first.id != second.id
    assert zones.get(first.id) == first
    assert zones.get(first.id).polygon == TRIANGLE
    assert zones.list_all() == [first, second]


def test_get_or_delete_unknown_zone(db: Database) -> None:
    zones = ZoneRepository(db)
    assert zones.get("missing") is None
    assert zones.delete("missing") is False


def test_deleting_a_zone_deletes_its_rules_but_not_its_events(db: Database) -> None:
    zones, rules, events = ZoneRepository(db), RuleRepository(db), EventRepository(db)
    keep = zones.add(ZoneIn(name="masa 1", polygon=TRIANGLE))
    drop = zones.add(ZoneIn(name="masa 2", polygon=TRIANGLE))
    kept_rule = rules.add(RuleIn(zone_id=keep.id, type="presence", target_labels=["cup"]))
    rules.add(RuleIn(zone_id=drop.id, type="presence", target_labels=["cup"]))
    events.add(event(zone_id=drop.id))
    assert zones.delete(drop.id) is True
    assert zones.list_all() == [keep]
    assert rules.list_all() == [kept_rule]
    assert [e.zone_id for e in events.recent()] == [drop.id]


# --- rules -----------------------------------------------------------------------


@pytest.fixture
def zone_id(db: Database) -> str:
    return ZoneRepository(db).add(ZoneIn(name="masa 1", polygon=TRIANGLE)).id


def test_rule_roundtrip(db: Database, zone_id: str) -> None:
    rules = RuleRepository(db)
    created = rules.add(
        RuleIn(zone_id=zone_id, type="count_threshold", target_labels=["person"], seconds=2.5, threshold=3)
    )
    unattended = rules.add(
        RuleIn(zone_id=zone_id, type="left_unattended", target_labels=["cup", "bottle"], seconds=20, enabled=False)
    )
    assert rules.get(created.id) == created
    assert rules.list_all() == [created, unattended]
    assert rules.get(unattended.id).enabled is False


def test_rule_for_unknown_zone_is_rejected(db: Database) -> None:
    with pytest.raises(UnknownZoneError):
        RuleRepository(db).add(RuleIn(zone_id="missing", type="presence", target_labels=["cup"]))
    assert RuleRepository(db).list_all() == []


def test_partial_rule_update(db: Database, zone_id: str) -> None:
    rules = RuleRepository(db)
    rule = rules.add(RuleIn(zone_id=zone_id, type="left_unattended", target_labels=["cup"], seconds=20))
    updated = rules.update(rule.id, {"seconds": 10, "enabled": False})
    assert updated == rule.model_copy(update={"seconds": 10, "enabled": False})
    assert rules.get(rule.id) == updated


def test_rule_update_is_validated(db: Database, zone_id: str) -> None:
    rules = RuleRepository(db)
    rule = rules.add(RuleIn(zone_id=zone_id, type="presence", target_labels=["cup"]))
    with pytest.raises(ValidationError):
        rules.update(rule.id, {"type": "count_threshold"})  # no threshold
    with pytest.raises(UnknownZoneError):
        rules.update(rule.id, {"zone_id": "missing"})
    assert rules.get(rule.id) == rule


def test_rule_update_cannot_change_the_id(db: Database, zone_id: str) -> None:
    rules = RuleRepository(db)
    rule = rules.add(RuleIn(zone_id=zone_id, type="presence", target_labels=["cup"]))
    assert rules.update(rule.id, {"id": "other"}).id == rule.id


def test_update_or_delete_unknown_rule(db: Database) -> None:
    rules = RuleRepository(db)
    assert rules.update("missing", {"seconds": 1}) is None
    assert rules.delete("missing") is False


def test_delete_rule(db: Database, zone_id: str) -> None:
    rules = RuleRepository(db)
    rule = rules.add(RuleIn(zone_id=zone_id, type="presence", target_labels=["cup"]))
    assert rules.delete(rule.id) is True
    assert rules.get(rule.id) is None


# --- vocabulary ------------------------------------------------------------------------


def test_vocabulary_starts_empty_and_keeps_order(db: Database) -> None:
    vocabulary = VocabularyRepository(db)
    assert vocabulary.get() == []
    assert vocabulary.set(["person", "cup", "bottle"]) == ["person", "cup", "bottle"]
    vocabulary.set(["bottle", "backpack"])
    assert vocabulary.get() == ["bottle", "backpack"]


# --- events ------------------------------------------------------------------------------


def test_event_roundtrip(db: Database) -> None:
    events = EventRepository(db)
    stored = events.add(event(kind="rule_triggered"))
    assert stored.id >= 1
    assert events.recent() == [stored]
    loaded = events.recent()[0]
    assert loaded.created_at == T0
    assert loaded.created_at.utcoffset() == timedelta(0)
    assert loaded.detail == {"from": "OCCUPIED", "to": "NEEDS_CLEARING"}
    assert loaded.rule_id == "r1"


def test_recent_events_are_newest_first_and_limited(db: Database) -> None:
    events = EventRepository(db)
    ids = [events.add(event(seconds=i)).id for i in range(5)]
    assert [e.id for e in events.recent(limit=3)] == ids[::-1][:3]
    assert len(events.recent()) == 5


# --- the file on disk ----------------------------------------------------------------------


def test_data_survives_reopening(db_path: Path) -> None:
    first = Database(db_path)
    zone = ZoneRepository(first).add(ZoneIn(name="masa 1", polygon=TRIANGLE))
    VocabularyRepository(first).set(["cup"])
    first.close()

    second = Database(db_path)
    try:
        assert ZoneRepository(second).list_all() == [zone]
        assert VocabularyRepository(second).get() == ["cup"]
    finally:
        second.close()


def test_schema_stores_no_images(db: Database) -> None:
    with db.transaction() as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        column_types = {
            row["type"]
            for table in tables
            for row in conn.execute(f"PRAGMA table_info({table})")  # names come from sqlite_master
        }
    assert tables - {"sqlite_sequence"} == {"zones", "rules", "vocabulary", "events"}
    assert "BLOB" not in column_types
