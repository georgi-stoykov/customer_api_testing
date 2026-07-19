import pytest
from engine.api_asserters import ConversionAsserter


@pytest.fixture(scope="session")
def conversion_asserter() -> ConversionAsserter:
    return ConversionAsserter()
