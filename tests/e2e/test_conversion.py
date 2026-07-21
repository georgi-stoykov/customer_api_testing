from decimal import Decimal
import allure
import pytest
from engine.api_asserters import ConversionAsserter, QuoteAsserter
from engine.api_client import ApiClient
from engine.api_constants.currencies import Currency
from engine.api_flows import send_quote
from engine.utils import checks


@pytest.mark.parametrize(
    ("from_currency", "to_currency", "amount_in"),
    [
        pytest.param(Currency.ETH, Currency.TRX, Decimal("1"), id="ETH-to-TRX"),
        pytest.param(Currency.TRX, Currency.USDT, Decimal("420"), id="TRX-to-USDT"),
        pytest.param(Currency.TRX, Currency.ETH, Decimal("987"), id="TRX-to-ETH"),
        # Exactly at ETH's 8-dp quantityPrecision — runs the full-precision fee end to end.
        pytest.param(
            Currency.ETH,
            Currency.TRX,
            Decimal("0.12345678"),
            id="ETH-to-TRX-max-precision",
        ),
        pytest.param(Currency.TRX, Currency.USDT, Decimal("420.5"), id="TRX-to-USDT-fractional"),
    ],
)
@allure.title(
    "Conversion {amount_in} {from_currency} -> {to_currency} settles with correct amounts"
)
def test_conversion_settles_with_correct_amounts(
    customer_api: ApiClient,
    conversion_asserter: ConversionAsserter,
    quote_asserter: QuoteAsserter,
    from_currency: Currency,
    to_currency: Currency,
    amount_in: Decimal,
) -> None:
    wallets_before = customer_api.wallet.list()

    settled_quote = send_quote(
        customer_api,
        from_currency=from_currency,
        to_currency=to_currency,
        amount_in=amount_in,
    )

    wallets_after = customer_api.wallet.list()

    quote_asserter.assert_settled_quote(
        quote=settled_quote,
        source_currency=wallets_after.by_currency(from_currency).currency,
        target_currency=wallets_after.by_currency(to_currency).currency,
    )
    conversion_asserter.assert_settled_conversion(
        quote=settled_quote,
        wallets_before=wallets_before,
        wallets_after=wallets_after,
        from_currency=from_currency,
        to_currency=to_currency,
    )
    # Make sure changes are persisted.
    for settled_wallet in (
        wallets_after.by_currency(from_currency),
        wallets_after.by_currency(to_currency),
    ):
        checks.assert_equal(
            actual=customer_api.wallet.get(settled_wallet.id),
            expected=settled_wallet,
            context=f"{settled_wallet.label} single get vs list entry after settlement",
        )


@allure.title("Converting the full wallet balance drains the wallet to exactly zero")
def test_full_balance_conversion_drains_wallet(
    customer_api: ApiClient,
    conversion_asserter: ConversionAsserter,
) -> None:
    wallets_before = customer_api.wallet.list()
    amount_in = wallets_before.by_currency(Currency.ETH).balance

    settled_quote = send_quote(
        customer_api,
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
        amount_in=amount_in,
        wallets=wallets_before,
    )

    wallets_after = customer_api.wallet.list()
    conversion_asserter.assert_settled_conversion(
        quote=settled_quote,
        wallets_before=wallets_before,
        wallets_after=wallets_after,
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
    )
    conversion_asserter.assert_wallet_drained(wallets_after.by_currency(Currency.ETH))
