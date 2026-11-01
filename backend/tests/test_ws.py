from collections.abc import Sequence
from typing import Any

from fastapi.testclient import TestClient
from starlette.testclient import WebSocketTestSession

from app.clock import FakeClock
from app.detector import FakeDetector
from app.schemas import Detection

from .support import LEFT_TABLE, det, jpeg

STEP = 0.2  # 5 FPS, a realistic CPU detection rate


def send_frames(
    ws: WebSocketTestSession,
    fake: FakeDetector,
    clock: FakeClock,
    detections: Sequence[Detection],
    seconds: float,
) -> list[dict[str, Any]]:
    """Send one JPEG per STEP for `seconds`, the detector returning `detections`."""
    replies = []
    for _ in range(round(seconds / STEP)):
        fake.script(detections)
        clock.advance(STEP)
        ws.send_bytes(jpeg())
        replies.append(ws.receive_json())
    return replies


def setup_table(client: TestClient, seconds: float = 20) -> tuple[dict[str, Any], dict[str, Any]]:
    zone = client.post("/api/zones", json={"name": "masa 1", "polygon": LEFT_TABLE}).json()
    rule = client.post(
        "/api/rules",
        json={"zone_id": zone["id"], "type": "left_unattended", "target_labels": ["cup", "bottle"], "seconds": seconds},
    ).json()
    return zone, rule


def test_each_frame_gets_one_telemetry_message(client: TestClient, fake: FakeDetector, clock: FakeClock) -> None:
    zone, _ = setup_table(client)
    with client.websocket_connect("/ws/detect") as ws:
        replies = send_frames(ws, fake, clock, [det("cup")], 0.4)
    first, second = replies
    assert first["type"] == "telemetry"
    assert [first["frame_id"], second["frame_id"]] == [1, 2]
    assert first["detector"] == "fake"
    assert first["infer_ms"] >= 0
    assert first["detections"] == [det("cup").model_dump(mode="json")]
    assert first["zones"] == [{"id": zone["id"], "name": "masa 1", "state": "FREE", "counts": {"cup": 1}}]
    assert first["events"] == []
    assert fake.calls == 2


def test_corrupt_jpeg_reports_error_and_keeps_the_connection(
    client: TestClient, fake: FakeDetector, clock: FakeClock
) -> None:
    with client.websocket_connect("/ws/detect") as ws:
        ws.send_bytes(b"definitely not a jpeg")
        error = ws.receive_json()
        ws.send_text("hello")
        text_error = ws.receive_json()
        replies = send_frames(ws, fake, clock, [], 0.2)
    assert error["type"] == "error"
    assert "JPEG" in error["message"]
    assert text_error == {"type": "error", "message": "expected a binary JPEG frame"}
    assert replies[0]["type"] == "telemetry"
    assert replies[0]["frame_id"] == 1


def test_demo_scenario_reaches_needs_clearing_and_logs_events(
    client: TestClient, fake: FakeDetector, clock: FakeClock
) -> None:
    zone, rule = setup_table(client, seconds=20)
    person, cup = det("person"), det("cup", x=0.3)
    with client.websocket_connect("/ws/detect") as ws:
        sitting = send_frames(ws, fake, clock, [person, cup], 3)
        left = send_frames(ws, fake, clock, [cup], 21)

    assert sitting[-1]["zones"][0]["state"] == "OCCUPIED"
    assert left[-1]["zones"][0]["state"] == "NEEDS_CLEARING"
    streamed = [event for reply in sitting + left for event in reply["events"]]
    assert [(e["kind"], e["detail"].get("to")) for e in streamed] == [
        ("zone_state_changed", "OCCUPIED"),
        ("rule_triggered", None),
        ("zone_state_changed", "NEEDS_CLEARING"),
    ]
    assert streamed[1]["rule_id"] == rule["id"]
    assert all(e["zone_id"] == zone["id"] and e["zone_name"] == "masa 1" for e in streamed)

    logged = client.get("/api/events").json()
    assert [e["id"] for e in logged] == [e["id"] for e in reversed(streamed)]


def test_vocabulary_change_applies_to_the_next_frame(client: TestClient, fake: FakeDetector) -> None:
    client.put("/api/vocabulary", json={"words": ["backpack"]})
    assert fake.vocabulary == ["backpack"]


def test_rules_added_while_streaming_take_effect(client: TestClient, fake: FakeDetector, clock: FakeClock) -> None:
    with client.websocket_connect("/ws/detect") as ws:
        assert send_frames(ws, fake, clock, [det("cup")], 0.2)[0]["zones"] == []
        zone = client.post("/api/zones", json={"name": "masa 1", "polygon": LEFT_TABLE}).json()
        client.post("/api/rules", json={"zone_id": zone["id"], "type": "presence", "target_labels": ["cup"]})
        replies = send_frames(ws, fake, clock, [det("cup")], 0.2)
    assert [e["kind"] for e in replies[0]["events"]] == ["rule_triggered"]
