from decimal import Decimal
from http import HTTPStatus
import allure
from engine import api_flows as flows
from engine.api_asserters import ConversionAsserter, ErrorAsserter, QuoteAsserter
from engine.api_client import ApiClient
from engine.api_constants import quotes
from engine.api_constants.currencies import Currency


@allure.title("An expired quote cannot be accepted and leaves balances untouched")
def test_expired_quote_accept_is_rejected(
    customer_api: ApiClient,
    conversion_asserter: ConversionAsserter,
    quote_asserter: QuoteAsserter,
    error_asserter: ErrorAsserter,
) -> None:
    wallets_before = customer_api.wallet.list()
    quote = flows.create_quote(
        customer_api,
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
        amount_in=Decimal("0.1"),
        wallets=wallets_before,
    )

    expired_quote = flows.wait_for_expiry(customer_api, quote.uuid)
    accept_response = customer_api.quote.accept(quote.uuid, check=False)

    quote_asserter.assert_quote_expired(expired_quote)
    error_asserter.assert_generic_error(
        accept_response,
        expected_status=HTTPStatus.PRECONDITION_FAILED,
    )
    quote_asserter.assert_quote_expired(customer_api.quote.get(quote.uuid))
    conversion_asserter.assert_wallets_unchanged(
        wallets_before=wallets_before,
        wallets_after=customer_api.wallet.list(),
    )


@allure.title("A quote accepted late in its window still settles correctly")
def test_late_window_accept_settles(
    customer_api: ApiClient,
    conversion_asserter: ConversionAsserter,
    quote_asserter: QuoteAsserter,
) -> None:
    amount_in = Decimal("0.1")
    wallets_before = customer_api.wallet.list()
    quote = flows.create_quote(
        customer_api,
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
        amount_in=amount_in,
        wallets=wallets_before,
    )

    held_quote = flows.hold_quote(
        customer_api,
        quote.uuid,
        hold_duration=quotes.ACCEPTANCE_WINDOW - quotes.LATE_ACCEPT_MARGIN,
    )
    quote_asserter.assert_quote_pending(held_quote)
    customer_api.quote.accept(quote.uuid)
    settled_quote = flows.wait_for_settlement(customer_api, quote.uuid)

    conversion_asserter.assert_settled_conversion(
        quote=settled_quote,
        wallets_before=wallets_before,
        wallets_after=customer_api.wallet.list(),
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
    )


@allure.title("Accepting a quote does not move balances before settlement")
def test_accept_does_not_move_balances_before_settlement(
    customer_api: ApiClient,
    conversion_asserter: ConversionAsserter,
    quote_asserter: QuoteAsserter,
) -> None:
    wallets_before = customer_api.wallet.list()
    quote = flows.create_quote(
        customer_api,
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
        amount_in=Decimal("0.1"),
        wallets=wallets_before,
    )

    accepted_quote = customer_api.quote.accept(quote.uuid)

    quote_asserter.assert_quote_accepted(accepted_quote)
    conversion_asserter.assert_wallets_unchanged(
        wallets_before=wallets_before,
        wallets_after=customer_api.wallet.list(),
    )
