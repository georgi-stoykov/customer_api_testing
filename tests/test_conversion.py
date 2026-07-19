from decimal import Decimal
import pytest
from engine.api_asserters import ConversionAsserter
from engine.api_client import ApiClient
from engine.api_constants.currencies import Currency
from engine.api_flows import send_quote


@pytest.mark.parametrize(
    ("from_currency", "to_currency", "amount_in"),
    [
        pytest.param(Currency.ETH, Currency.TRX, Decimal("1"), id="ETH-to-TRX"),
        pytest.param(Currency.TRX, Currency.USDT, Decimal("420"), id="TRX-to-USDT"),
        pytest.param(Currency.TRX, Currency.ETH, Decimal("987"), id="TRX-to-ETH"),
    ],
)
def test_conversion_settles_with_correct_amounts(
    new_customer: ApiClient,
    conversion_asserter: ConversionAsserter,
    from_currency: Currency,
    to_currency: Currency,
    amount_in: Decimal,
) -> None:
    wallets_before = new_customer.wallet.list()

    settled_quote = send_quote(
        new_customer,
        from_currency=from_currency,
        to_currency=to_currency,
        amount_in=amount_in,
    )

    wallets_after = new_customer.wallet.list()

    conversion_asserter.assert_settled_conversion(
        quote=settled_quote,
        wallets_before=wallets_before,
        wallets_after=wallets_after,
        from_currency=from_currency,
        to_currency=to_currency,
        amount_in=amount_in,
    )
