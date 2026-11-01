from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.clock import FakeClock
from app.detector import FakeDetector
from app.main import create_app

from . import support

SUPPORTED = ["person", "cup", "bottle", "backpack"]


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def fake() -> FakeDetector:
    return FakeDetector(supported=SUPPORTED)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "vigilo.sqlite3"


@pytest.fixture
def client(fake: FakeDetector, db_path: Path, clock: FakeClock) -> Iterator[TestClient]:
    with TestClient(create_app(detector=fake, db_path=db_path, clock=clock)) as test_client:
        yield test_client


@pytest.fixture
def jpeg() -> bytes:
    return support.jpeg()
