import pytest

from engine.client import ApiClient
from engine.flows import new_account


@pytest.fixture
def api() -> ApiClient:
    return new_account()
