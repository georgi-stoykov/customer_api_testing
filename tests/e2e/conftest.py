import pytest
from engine.api_asserters import ConversionAsserter, ErrorAsserter


@pytest.fixture(scope="session")
def conversion_asserter() -> ConversionAsserter:
    return ConversionAsserter()


@pytest.fixture(scope="session")
def error_asserter() -> ErrorAsserter:
    return ErrorAsserter()
