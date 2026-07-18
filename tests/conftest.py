import pytest
from engine import api_flows as flows
from engine.api_asserters import ConversionAsserter
from engine.api_client import ApiClient


@pytest.fixture
def new_customer() -> ApiClient:
    return flows.new_customer()


@pytest.fixture(scope="session")
def conversion_asserter() -> ConversionAsserter:
    return ConversionAsserter()
