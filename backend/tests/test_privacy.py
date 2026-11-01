"""Privacy requirements (CLAUDE.md section 12): no frame reaches the disk, the
database holds only text and numbers, and the server never sends images back."""

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.clock import FakeClock
from app.detector import FakeDetector
from app.main import create_app

from .support import LEFT_TABLE, det, jpeg


def test_full_cycle_writes_only_the_sqlite_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)  # anything written to a relative path lands here
    db_path = tmp_path / "vigilo.sqlite3"
    fake = FakeDetector()
    clock = FakeClock()
    frame = jpeg(320, 240)

    with TestClient(create_app(detector=fake, db_path=db_path, clock=clock)) as client:
        zone = client.post("/api/zones", json={"name": "masa 1", "polygon": LEFT_TABLE}).json()
        client.post(
            "/api/rules",
            json={"zone_id": zone["id"], "type": "left_unattended", "target_labels": ["cup"], "seconds": 2},
        )
        with client.websocket_connect("/ws/detect") as ws:
            for detections in [[det("person"), det("cup", x=0.3)]] * 8 + [[det("cup", x=0.3)]] * 15:
                fake.script(detections)
                clock.advance(0.2)
                ws.send_bytes(frame)
                message = ws.receive()
                assert "text" in message and message.get("bytes") is None  # JSON only, never an image
        assert client.get("/api/events").json(), "the cycle should have produced events"

    files = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*") if p.is_file())
    assert files == ["vigilo.sqlite3"]

    with sqlite3.connect(db_path) as conn:
        tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")]
        for table in tables:
            for row in conn.execute(f"SELECT * FROM {table}"):  # names come from sqlite_master
                assert not any(isinstance(value, bytes) for value in row), f"binary value in {table}"
                assert frame not in repr(row).encode()
