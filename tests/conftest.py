import pytest
from engine.customer_api import flows
from engine.customer_api.api_client import ApiClient
from engine.customer_api.asserters import ConversionAsserter


@pytest.fixture
def new_customer() -> ApiClient:
    return flows.new_customer()


@pytest.fixture(scope="session")
def conversion_asserter() -> ConversionAsserter:
    return ConversionAsserter()
