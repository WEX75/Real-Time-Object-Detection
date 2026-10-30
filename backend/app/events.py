"""Publish/subscribe between the rule engine and its consumers.

`InProcessEventBus` stands in for an MQTT broker: same topics and the same
`subscribe`/`publish` interface, so swapping it later does not touch callers.
"""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from collections.abc import Callable
from typing import Any, Protocol

logger = logging.getLogger(__name__)

EVENTS_TOPIC = "vigilo/events"

Handler = Callable[[Any], None]
Unsubscribe = Callable[[], None]


class EventBus(Protocol):
    def subscribe(self, topic: str, handler: Handler) -> Unsubscribe: ...

    def publish(self, topic: str, message: Any) -> None: ...


class InProcessEventBus:
    """Synchronous delivery, in subscription order. A failing handler is logged
    and does not stop delivery to the others."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._handlers: defaultdict[str, list[Handler]] = defaultdict(list)

    def subscribe(self, topic: str, handler: Handler) -> Unsubscribe:
        with self._lock:
            self._handlers[topic].append(handler)

        def unsubscribe() -> None:
            with self._lock:
                if handler in self._handlers[topic]:
                    self._handlers[topic].remove(handler)

        return unsubscribe

    def publish(self, topic: str, message: Any) -> None:
        with self._lock:
            handlers = list(self._handlers.get(topic, ()))
        for handler in handlers:
            try:
                handler(message)
            except Exception:
                logger.exception("event handler failed on topic %s", topic)
