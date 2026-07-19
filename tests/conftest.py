import pytest
from engine import api_flows as flows
from engine.api_asserters import ConversionAsserter, ErrorAsserter, QuoteAsserter
from engine.api_client import ApiClient


@pytest.fixture
def customer_api() -> ApiClient:
    return flows.new_customer()


@pytest.fixture(scope="session")
def conversion_asserter() -> ConversionAsserter:
    return ConversionAsserter()


@pytest.fixture(scope="session")
def error_asserter() -> ErrorAsserter:
    return ErrorAsserter()


@pytest.fixture(scope="session")
def quote_asserter() -> QuoteAsserter:
    return QuoteAsserter()
