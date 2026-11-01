from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.clock import FakeClock
from app.detector import FakeDetector
from app.main import create_app

from .support import LEFT_TABLE


def make_zone(client: TestClient, name: str = "masa 1") -> dict[str, Any]:
    response = client.post("/api/zones", json={"name": name, "polygon": LEFT_TABLE})
    assert response.status_code == 201, response.text
    return response.json()


def make_rule(client: TestClient, zone_id: str, **fields: Any) -> dict[str, Any]:
    body = {"zone_id": zone_id, "type": "left_unattended", "target_labels": ["cup", "bottle"], "seconds": 20}
    response = client.post("/api/rules", json={**body, **fields})
    assert response.status_code == 201, response.text
    return response.json()


def test_health_reports_active_detector(client: TestClient) -> None:
    assert client.get("/api/health").json() == {"status": "ok", "detector": "fake", "unsupported": []}


def test_vocabulary_starts_with_defaults_and_reaches_the_detector(client: TestClient, fake: FakeDetector) -> None:
    assert client.get("/api/vocabulary").json() == {"words": ["person", "cup", "bottle"]}
    assert fake.vocabulary == ["person", "cup", "bottle"]


def test_put_vocabulary_normalizes_and_reports_unsupported_words(client: TestClient, fake: FakeDetector) -> None:
    response = client.put("/api/vocabulary", json={"words": [" Person", "cup", "Stapler", "cup"]})
    assert response.status_code == 200
    assert response.json() == {"words": ["person", "cup", "stapler"], "unsupported": ["stapler"]}
    assert fake.vocabulary == ["person", "cup", "stapler"]
    assert client.get("/api/vocabulary").json() == {"words": ["person", "cup", "stapler"]}
    assert client.get("/api/health").json()["unsupported"] == ["stapler"]


def test_configuration_survives_a_restart(client: TestClient, db_path: Path) -> None:
    client.put("/api/vocabulary", json={"words": ["backpack"]})
    zone = make_zone(client)
    rule = make_rule(client, zone["id"])
    fresh = FakeDetector()
    with TestClient(create_app(detector=fresh, db_path=db_path, clock=FakeClock())) as restarted:
        assert restarted.get("/api/vocabulary").json() == {"words": ["backpack"]}
        assert restarted.get("/api/zones").json() == [zone]
        assert restarted.get("/api/rules").json() == [rule]
    assert fresh.vocabulary == ["backpack"]


def test_zone_create_list_delete(client: TestClient) -> None:
    zone = make_zone(client)
    assert zone["name"] == "masa 1"
    assert [tuple(p) for p in zone["polygon"]] == LEFT_TABLE
    assert client.get("/api/zones").json() == [zone]
    assert client.delete(f"/api/zones/{zone['id']}").status_code == 204
    assert client.get("/api/zones").json() == []
    assert client.delete(f"/api/zones/{zone['id']}").status_code == 404


@pytest.mark.parametrize(
    "body",
    [
        {"name": "masa 1", "polygon": [(0.1, 0.1), (0.2, 0.2)]},
        {"name": "masa 1", "polygon": [(0.1, 0.1), (1.5, 0.2), (0.3, 0.9)]},
        {"name": "masa 1", "polygon": [(0.1, 0.1), (0.2, -0.1), (0.3, 0.9)]},
        {"name": "   ", "polygon": LEFT_TABLE},
        {"polygon": LEFT_TABLE},
    ],
    ids=["two-points", "x-above-1", "y-below-0", "blank-name", "no-name"],
)
def test_invalid_zone_is_rejected(client: TestClient, body: dict[str, Any]) -> None:
    assert client.post("/api/zones", json=body).status_code == 422
    assert client.get("/api/zones").json() == []


def test_rule_create_and_list(client: TestClient) -> None:
    zone = make_zone(client)
    rule = make_rule(client, zone["id"], target_labels=[" Cup ", "BOTTLE"])
    assert rule["target_labels"] == ["cup", "bottle"]
    assert rule["enabled"] is True
    assert client.get("/api/rules").json() == [rule]


def test_count_threshold_requires_threshold(client: TestClient) -> None:
    zone = make_zone(client)
    body = {"zone_id": zone["id"], "type": "count_threshold", "target_labels": ["person"], "seconds": 5}
    assert client.post("/api/rules", json=body).status_code == 422
    assert client.post("/api/rules", json={**body, "threshold": 3}).status_code == 201


def test_rule_on_missing_zone_is_rejected(client: TestClient) -> None:
    body = {"zone_id": "nope", "type": "presence", "target_labels": ["person"]}
    response = client.post("/api/rules", json=body)
    assert response.status_code == 422
    assert "nope" in response.json()["detail"]


@pytest.mark.parametrize(
    "fields",
    [{"seconds": -1}, {"type": "unknown"}, {"target_labels": ["  "]}, {"threshold": -1, "type": "count_threshold"}],
    ids=["negative-seconds", "unknown-type", "blank-labels", "negative-threshold"],
)
def test_invalid_rule_fields_are_rejected(client: TestClient, fields: dict[str, Any]) -> None:
    zone = make_zone(client)
    body = {"zone_id": zone["id"], "type": "presence", "target_labels": ["person"], **fields}
    assert client.post("/api/rules", json=body).status_code == 422


def test_patch_changes_only_the_fields_sent(client: TestClient) -> None:
    zone = make_zone(client)
    rule = make_rule(client, zone["id"])
    response = client.patch(f"/api/rules/{rule['id']}", json={"seconds": 5, "enabled": False})
    assert response.status_code == 200
    assert response.json() == {**rule, "seconds": 5, "enabled": False}
    assert client.get("/api/rules").json() == [response.json()]


def test_patch_revalidates_the_whole_rule(client: TestClient) -> None:
    zone = make_zone(client)
    rule = make_rule(client, zone["id"])
    assert client.patch(f"/api/rules/{rule['id']}", json={"type": "count_threshold"}).status_code == 422
    assert client.patch(f"/api/rules/{rule['id']}", json={"zone_id": "nope"}).status_code == 422
    assert client.get("/api/rules").json() == [rule]


def test_patch_and_delete_of_missing_rule_return_404(client: TestClient) -> None:
    assert client.patch("/api/rules/nope", json={"seconds": 1}).status_code == 404
    assert client.delete("/api/rules/nope").status_code == 404


def test_delete_rule(client: TestClient) -> None:
    zone = make_zone(client)
    rule = make_rule(client, zone["id"])
    assert client.delete(f"/api/rules/{rule['id']}").status_code == 204
    assert client.get("/api/rules").json() == []


def test_deleting_a_zone_deletes_its_rules(client: TestClient) -> None:
    kept = make_zone(client, "masa 2")
    zone = make_zone(client)
    make_rule(client, zone["id"])
    other = make_rule(client, kept["id"])
    client.delete(f"/api/zones/{zone['id']}")
    assert client.get("/api/rules").json() == [other]


def test_events_start_empty_and_limit_is_validated(client: TestClient) -> None:
    assert client.get("/api/events").json() == []
    assert client.get("/api/events?limit=0").status_code == 422
    assert client.get("/api/events?limit=501").status_code == 422
