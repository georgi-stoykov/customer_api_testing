import pytest
from engine.constants.currencies import Currency
from engine.customer_api.api_client import ApiClient
from engine.customer_api.asserters import ConversionAsserter
from engine.customer_api.flows import send_quote


@pytest.mark.parametrize(
    ("from_currency", "to_currency", "amount_in"),
    [
        pytest.param(Currency.ETH, Currency.TRX, "1", id="1-ETH-to-TRX"),
        pytest.param(Currency.TRX, Currency.USDT, "420", id="420-TRX-to-USDT"),
        pytest.param(Currency.TRX, Currency.ETH, "987", id="987-TRX-to-ETH"),
    ],
)
def test_conversion_settles_with_correct_amounts(
    new_customer: ApiClient,
    conversion_asserter: ConversionAsserter,
    from_currency: Currency,
    to_currency: Currency,
    amount_in: str,
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
