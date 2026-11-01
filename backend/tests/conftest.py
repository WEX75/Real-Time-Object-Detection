import pytest

from . import support


@pytest.fixture
def jpeg() -> bytes:
    return support.jpeg()
