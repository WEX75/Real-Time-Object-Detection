"""SQLite persistence for zones, rules, vocabulary and events.

Only text and numbers are stored; never images or frames.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from .schemas import Event, EventIn, Rule, RuleIn, Zone, ZoneIn

_SCHEMA = """
CREATE TABLE IF NOT EXISTS zones (
    id      TEXT PRIMARY KEY,
    name    TEXT NOT NULL,
    polygon TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS rules (
    id            TEXT PRIMARY KEY,
    zone_id       TEXT NOT NULL REFERENCES zones(id) ON DELETE CASCADE,
    type          TEXT NOT NULL,
    target_labels TEXT NOT NULL,
    seconds       REAL NOT NULL,
    threshold     INTEGER,
    enabled       INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS vocabulary (
    position INTEGER PRIMARY KEY,
    word     TEXT NOT NULL
);
-- No foreign key: the history of a deleted zone is kept.
CREATE TABLE IF NOT EXISTS events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    zone_id    TEXT NOT NULL,
    zone_name  TEXT NOT NULL,
    rule_id    TEXT,
    kind       TEXT NOT NULL,
    detail     TEXT NOT NULL
);
"""


_INSERT_RULE = """
INSERT INTO rules (id, zone_id, type, target_labels, seconds, threshold, enabled)
VALUES (:id, :zone_id, :type, :target_labels, :seconds, :threshold, :enabled)
"""
_UPDATE_RULE = """
UPDATE rules SET zone_id = :zone_id, type = :type, target_labels = :target_labels,
    seconds = :seconds, threshold = :threshold, enabled = :enabled
WHERE id = :id
"""


class UnknownZoneError(LookupError):
    """A rule refers to a zone that does not exist."""


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


class Database:
    """One shared connection, serialized by a lock: API handlers and the frame
    loop run on different threads."""

    def __init__(self, path: str | Path) -> None:
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        with self.transaction() as conn:
            conn.executescript(_SCHEMA)

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Commit on success, roll back on error."""
        with self._lock, self._conn:
            yield self._conn

    def close(self) -> None:
        with self._lock:
            self._conn.close()


class ZoneRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def add(self, zone: ZoneIn) -> Zone:
        created = Zone(id=_new_id(), **zone.model_dump())
        with self._db.transaction() as conn:
            conn.execute(
                "INSERT INTO zones (id, name, polygon) VALUES (?, ?, ?)",
                (created.id, created.name, json.dumps(created.polygon)),
            )
        return created

    def get(self, zone_id: str) -> Zone | None:
        with self._db.transaction() as conn:
            row = conn.execute("SELECT * FROM zones WHERE id = ?", (zone_id,)).fetchone()
        return self._to_zone(row) if row else None

    def list_all(self) -> list[Zone]:
        with self._db.transaction() as conn:
            rows = conn.execute("SELECT * FROM zones ORDER BY rowid").fetchall()
        return [self._to_zone(row) for row in rows]

    def delete(self, zone_id: str) -> bool:
        """Delete the zone and its rules. False if it did not exist."""
        with self._db.transaction() as conn:
            return conn.execute("DELETE FROM zones WHERE id = ?", (zone_id,)).rowcount > 0

    @staticmethod
    def _to_zone(row: sqlite3.Row) -> Zone:
        return Zone(id=row["id"], name=row["name"], polygon=json.loads(row["polygon"]))


class RuleRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def add(self, rule: RuleIn) -> Rule:
        created = Rule(id=_new_id(), **rule.model_dump())
        with self._db.transaction() as conn:
            self._write(conn, _INSERT_RULE, created)
        return created

    def get(self, rule_id: str) -> Rule | None:
        with self._db.transaction() as conn:
            row = conn.execute("SELECT * FROM rules WHERE id = ?", (rule_id,)).fetchone()
        return self._to_rule(row) if row else None

    def list_all(self) -> list[Rule]:
        with self._db.transaction() as conn:
            rows = conn.execute("SELECT * FROM rules ORDER BY rowid").fetchall()
        return [self._to_rule(row) for row in rows]

    def update(self, rule_id: str, changes: Mapping[str, Any]) -> Rule | None:
        """Apply a partial update, re-validating the whole rule. None if not found.

        Raises `pydantic.ValidationError` if the result is not a valid rule.
        """
        with self._db.transaction() as conn:
            row = conn.execute("SELECT * FROM rules WHERE id = ?", (rule_id,)).fetchone()
            if row is None:
                return None
            merged = {**self._to_rule(row).model_dump(), **changes, "id": rule_id}
            updated = Rule.model_validate(merged)
            self._write(conn, _UPDATE_RULE, updated)
        return updated

    def delete(self, rule_id: str) -> bool:
        with self._db.transaction() as conn:
            return conn.execute("DELETE FROM rules WHERE id = ?", (rule_id,)).rowcount > 0

    @staticmethod
    def _write(conn: sqlite3.Connection, sql: str, rule: Rule) -> None:
        params = {
            **rule.model_dump(),
            "target_labels": json.dumps(rule.target_labels),
            "enabled": int(rule.enabled),
        }
        try:
            conn.execute(sql, params)
        except sqlite3.IntegrityError as exc:
            if "FOREIGN KEY" not in str(exc):
                raise
            raise UnknownZoneError(rule.zone_id) from exc

    @staticmethod
    def _to_rule(row: sqlite3.Row) -> Rule:
        return Rule(
            id=row["id"],
            zone_id=row["zone_id"],
            type=row["type"],
            target_labels=json.loads(row["target_labels"]),
            seconds=row["seconds"],
            threshold=row["threshold"],
            enabled=bool(row["enabled"]),
        )


class VocabularyRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def get(self) -> list[str]:
        with self._db.transaction() as conn:
            rows = conn.execute("SELECT word FROM vocabulary ORDER BY position").fetchall()
        return [row["word"] for row in rows]

    def set(self, words: list[str]) -> list[str]:
        with self._db.transaction() as conn:
            conn.execute("DELETE FROM vocabulary")
            conn.executemany("INSERT INTO vocabulary (position, word) VALUES (?, ?)", enumerate(words))
        return list(words)


class EventRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def add(self, event: EventIn) -> Event:
        with self._db.transaction() as conn:
            cursor = conn.execute(
                "INSERT INTO events (created_at, zone_id, zone_name, rule_id, kind, detail) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    event.created_at.isoformat(),
                    event.zone_id,
                    event.zone_name,
                    event.rule_id,
                    event.kind,
                    json.dumps(event.detail),
                ),
            )
            assert cursor.lastrowid is not None
            return Event(id=cursor.lastrowid, **event.model_dump())

    def recent(self, limit: int = 50) -> list[Event]:
        """The newest events first."""
        with self._db.transaction() as conn:
            rows = conn.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [
            Event(
                id=row["id"],
                created_at=datetime.fromisoformat(row["created_at"]),
                zone_id=row["zone_id"],
                zone_name=row["zone_name"],
                rule_id=row["rule_id"],
                kind=row["kind"],
                detail=json.loads(row["detail"]),
            )
            for row in rows
        ]
