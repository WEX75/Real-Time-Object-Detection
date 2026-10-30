import logging

import pytest

from app.events import EVENTS_TOPIC, InProcessEventBus


def test_subscriber_receives_messages_of_its_topic_only() -> None:
    bus = InProcessEventBus()
    received: list[object] = []
    other: list[object] = []
    bus.subscribe(EVENTS_TOPIC, received.append)
    bus.subscribe("vigilo/other", other.append)
    bus.publish(EVENTS_TOPIC, {"kind": "rule_triggered"})
    assert received == [{"kind": "rule_triggered"}]
    assert other == []


def test_subscribers_are_called_in_subscription_order() -> None:
    bus = InProcessEventBus()
    calls: list[str] = []
    bus.subscribe(EVENTS_TOPIC, lambda m: calls.append(f"first:{m}"))
    bus.subscribe(EVENTS_TOPIC, lambda m: calls.append(f"second:{m}"))
    bus.publish(EVENTS_TOPIC, 1)
    bus.publish(EVENTS_TOPIC, 2)
    assert calls == ["first:1", "second:1", "first:2", "second:2"]


def test_unsubscribe_stops_delivery_and_is_idempotent() -> None:
    bus = InProcessEventBus()
    received: list[object] = []
    unsubscribe = bus.subscribe(EVENTS_TOPIC, received.append)
    bus.publish(EVENTS_TOPIC, "a")
    unsubscribe()
    unsubscribe()
    bus.publish(EVENTS_TOPIC, "b")
    assert received == ["a"]


def test_failing_handler_does_not_block_others(caplog: pytest.LogCaptureFixture) -> None:
    bus = InProcessEventBus()
    received: list[object] = []

    def broken(_: object) -> None:
        raise RuntimeError("boom")

    bus.subscribe(EVENTS_TOPIC, broken)
    bus.subscribe(EVENTS_TOPIC, received.append)
    with caplog.at_level(logging.ERROR, logger="app.events"):
        bus.publish(EVENTS_TOPIC, "event")
    assert received == ["event"]
    assert "event handler failed" in caplog.text


def test_publish_without_subscribers_is_a_no_op() -> None:
    InProcessEventBus().publish(EVENTS_TOPIC, "nobody listens")


def test_handler_subscribed_during_publish_gets_only_later_messages() -> None:
    bus = InProcessEventBus()
    late: list[object] = []
    bus.subscribe(EVENTS_TOPIC, lambda _: bus.subscribe(EVENTS_TOPIC, late.append))
    bus.publish(EVENTS_TOPIC, 1)
    assert late == []
    bus.publish(EVENTS_TOPIC, 2)
    assert late == [2]
