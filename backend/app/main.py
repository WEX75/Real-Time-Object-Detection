"""FastAPI application: REST configuration API, the /ws/detect frame loop and
the wiring between detector, rule engine, event bus and SQLite.

`create_app` takes every dependency, so tests run it with a FakeDetector, a
temporary database and a FakeClock. Nothing is opened or loaded at import: the
real detector and the database are created when the app starts.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request, Response, WebSocket, WebSocketDisconnect, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, ValidationError

from .clock import Clock, SystemClock
from .database import (
    Database,
    EventRepository,
    RuleRepository,
    UnknownZoneError,
    VocabularyRepository,
    ZoneRepository,
)
from .detector import DEFAULT_VOCABULARY, Detector, InvalidFrameError, create_detector, normalize_words
from .events import EVENTS_TOPIC, EventBus, InProcessEventBus
from .rules import RuleEngine
from .schemas import Detection, Event, Rule, RuleIn, RuleType, Zone, ZoneIn, ZoneStatus

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = "events.sqlite3"


class VocabularyIn(BaseModel):
    words: list[str]


class RulePatch(BaseModel):
    """Partial update of a rule: only the fields sent are changed."""

    zone_id: str | None = None
    type: RuleType | None = None
    target_labels: list[str] | None = None
    seconds: float | None = None
    threshold: int | None = None
    enabled: bool | None = None


@dataclass
class FrameResult:
    detections: list[Detection]
    zones: list[ZoneStatus]
    infer_ms: float


@dataclass
class Services:
    detector: Detector
    db: Database
    zones: ZoneRepository
    rules: RuleRepository
    vocabulary: VocabularyRepository
    events: EventRepository
    engine: RuleEngine
    bus: EventBus
    clock: Clock
    unsupported: list[str] = field(default_factory=list)

    def reload_engine(self) -> None:
        self.engine.configure(self.zones.list_all(), self.rules.list_all())

    def set_vocabulary(self, words: list[str]) -> list[str]:
        words = normalize_words(words)
        self.unsupported = self.detector.set_vocabulary(words)
        self.vocabulary.set(words)
        return words

    def process_frame(self, jpeg: bytes) -> FrameResult:
        """Detect, evaluate rules, persist and publish events. Runs off the event loop."""
        start = time.perf_counter()
        detections = self.detector.detect(jpeg)
        infer_ms = (time.perf_counter() - start) * 1000
        result = self.engine.update(detections, self.clock.now())
        for event_in in result.events:
            # Persist first, so observers receive the event with its id.
            self.bus.publish(EVENTS_TOPIC, self.events.add(event_in))
        return FrameResult(detections=detections, zones=result.zones, infer_ms=round(infer_ms, 1))


def _services(request: Request) -> Services:
    return request.app.state.services


def create_app(
    detector: Detector | None = None,
    db_path: str | Path | None = None,
    clock: Clock | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        db = Database(db_path or os.environ.get("DATABASE_PATH", DEFAULT_DB_PATH))
        zones, rules = ZoneRepository(db), RuleRepository(db)
        vocabulary = VocabularyRepository(db)
        words = vocabulary.get() or list(DEFAULT_VOCABULARY)
        active = detector or await run_in_threadpool(create_detector, words)
        services = Services(
            detector=active,
            db=db,
            zones=zones,
            rules=rules,
            vocabulary=vocabulary,
            events=EventRepository(db),
            engine=RuleEngine(zones.list_all(), rules.list_all()),
            bus=InProcessEventBus(),
            clock=clock or SystemClock(),
        )
        await run_in_threadpool(services.set_vocabulary, words)
        logger.info("Vigilo started with detector %s", active.name)
        app.state.services = services
        app.state.frame_lock = asyncio.Lock()
        try:
            yield
        finally:
            db.close()

    app = FastAPI(title="Vigilo", lifespan=lifespan)

    @app.get("/api/health")
    def health(request: Request) -> dict[str, Any]:
        services = _services(request)
        return {"status": "ok", "detector": services.detector.name, "unsupported": services.unsupported}

    @app.get("/api/vocabulary")
    def get_vocabulary(request: Request) -> dict[str, list[str]]:
        return {"words": _services(request).vocabulary.get()}

    @app.put("/api/vocabulary")
    def put_vocabulary(body: VocabularyIn, request: Request) -> dict[str, list[str]]:
        services = _services(request)
        words = services.set_vocabulary(body.words)
        return {"words": words, "unsupported": services.unsupported}

    @app.get("/api/zones")
    def list_zones(request: Request) -> list[Zone]:
        return _services(request).zones.list_all()

    @app.post("/api/zones", status_code=status.HTTP_201_CREATED)
    def create_zone(body: ZoneIn, request: Request) -> Zone:
        services = _services(request)
        zone = services.zones.add(body)
        services.reload_engine()
        return zone

    @app.delete("/api/zones/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_zone(zone_id: str, request: Request) -> Response:
        services = _services(request)
        if not services.zones.delete(zone_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"zone {zone_id} not found")
        services.reload_engine()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.get("/api/rules")
    def list_rules(request: Request) -> list[Rule]:
        return _services(request).rules.list_all()

    @app.post("/api/rules", status_code=status.HTTP_201_CREATED)
    def create_rule(body: RuleIn, request: Request) -> Rule:
        services = _services(request)
        try:
            rule = services.rules.add(body)
        except UnknownZoneError:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"zone {body.zone_id} does not exist") from None
        services.reload_engine()
        return rule

    @app.patch("/api/rules/{rule_id}")
    def update_rule(rule_id: str, body: RulePatch, request: Request) -> Rule:
        services = _services(request)
        try:
            rule = services.rules.update(rule_id, body.model_dump(exclude_unset=True))
        except UnknownZoneError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"zone {exc} does not exist") from None
        except ValidationError as exc:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, exc.errors(include_url=False, include_context=False)
            ) from None
        if rule is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"rule {rule_id} not found")
        services.reload_engine()
        return rule

    @app.delete("/api/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_rule(rule_id: str, request: Request) -> Response:
        services = _services(request)
        if not services.rules.delete(rule_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"rule {rule_id} not found")
        services.reload_engine()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.get("/api/events")
    def recent_events(request: Request, limit: int = Query(default=50, ge=1, le=500)) -> list[Event]:
        return _services(request).events.recent(limit)

    @app.websocket("/ws/detect")
    async def detect(websocket: WebSocket) -> None:
        """One telemetry message per binary JPEG received. Errors are reported
        and the connection stays open."""
        services: Services = websocket.app.state.services
        frame_lock: asyncio.Lock = websocket.app.state.frame_lock
        await websocket.accept()
        pending: list[Event] = []
        unsubscribe = services.bus.subscribe(EVENTS_TOPIC, pending.append)
        frame_id = 0
        try:
            while True:
                message = await websocket.receive()
                if message["type"] == "websocket.disconnect":
                    break
                jpeg = message.get("bytes")
                if jpeg is None:
                    await websocket.send_json({"type": "error", "message": "expected a binary JPEG frame"})
                    continue
                try:
                    # One frame at a time across connections: the engine has one timeline.
                    async with frame_lock:
                        frame = await run_in_threadpool(services.process_frame, jpeg)
                except InvalidFrameError as exc:
                    await websocket.send_json({"type": "error", "message": str(exc)})
                    continue
                except Exception:
                    logger.exception("frame processing failed")
                    await websocket.send_json({"type": "error", "message": "frame processing failed"})
                    continue
                frame_id += 1
                events, pending[:] = list(pending), []
                await websocket.send_json(
                    {
                        "type": "telemetry",
                        "frame_id": frame_id,
                        "infer_ms": frame.infer_ms,
                        "detector": services.detector.name,
                        "detections": [d.model_dump(mode="json") for d in frame.detections],
                        "zones": [z.model_dump(mode="json") for z in frame.zones],
                        "events": [e.model_dump(mode="json") for e in events],
                    }
                )
        except WebSocketDisconnect:
            pass
        finally:
            unsubscribe()

    return app


app = create_app()
