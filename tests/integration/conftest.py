from decimal import Decimal
import pytest
from engine import api_flows as flows
from engine.api_client import ApiClient
from engine.api_constants.currencies import Currency
from engine.api_models.quotes import Quote


@pytest.fixture
def pending_quote(customer_api: ApiClient) -> Quote:
    # A freshly created, unaccepted quote for tests that need any pending quote and
    # don't assert against the specific request values.
    return flows.create_quote(
        customer_api,
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
        amount_in=Decimal("0.1"),
    )
