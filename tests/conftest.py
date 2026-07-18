import pytest
from engine.wallet_payments_api.client import ApiClient
from engine.wallet_payments_api.flows import new_account


@pytest.fixture
def api() -> ApiClient:
    return new_account()
