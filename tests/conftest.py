import pytest
from engine import api_flows as flows
from engine.api_client import ApiClient


@pytest.fixture
def customer_api() -> ApiClient:
    return flows.new_customer()
