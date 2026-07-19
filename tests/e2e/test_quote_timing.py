from decimal import Decimal
from http import HTTPStatus
import allure
from engine import api_flows as flows
from engine.api_asserters import ConversionAsserter, ErrorAsserter
from engine.api_client import ApiClient
from engine.api_constants import quotes
from engine.api_constants.currencies import Currency
from engine.api_models.quotes import PaymentStatus, QuoteStatus
from engine.utils import checks


@allure.title("An expired quote cannot be accepted and leaves balances untouched")
def test_expired_quote_accept_is_rejected(
    new_customer: ApiClient,
    conversion_asserter: ConversionAsserter,
    error_asserter: ErrorAsserter,
) -> None:
    wallets_before = new_customer.wallet.list()
    quote = flows.create_quote(
        new_customer,
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
        amount_in=Decimal("0.1"),
    )

    expired_quote = flows.wait_for_expiry(new_customer, quote.uuid)
    accept_response = new_customer.quote.accept(quote.uuid, check=False)

    checks.assert_equal(
        actual=expired_quote.payment_status,
        expected=PaymentStatus.EXPIRED,
        context="paymentStatus of an expired quote",
    )
    error_asserter.assert_error(
        accept_response,
        expected_status=HTTPStatus.PRECONDITION_FAILED,
        expected_detail="Precondition Failed",
    )
    checks.assert_equal(
        actual=new_customer.quote.get(quote.uuid).quote_status,
        expected=QuoteStatus.EXPIRED,
        context="quoteStatus after the rejected accept",
    )
    conversion_asserter.assert_account_unchanged(
        wallets_before=wallets_before,
        wallets_after=new_customer.wallet.list(),
    )


@allure.title("A quote accepted late in its window still settles correctly")
def test_late_window_accept_settles(
    new_customer: ApiClient,
    conversion_asserter: ConversionAsserter,
) -> None:
    amount_in = Decimal("0.1")
    wallets_before = new_customer.wallet.list()
    quote = flows.create_quote(
        new_customer,
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
        amount_in=amount_in,
    )

    held_quote = flows.hold_quote(
        new_customer,
        quote.uuid,
        hold_duration=quotes.ACCEPTANCE_WINDOW - quotes.LATE_ACCEPT_MARGIN,
    )
    checks.assert_equal(
        actual=held_quote.quote_status,
        expected=QuoteStatus.PENDING,
        context="quoteStatus late in the acceptance window",
    )
    new_customer.quote.accept(quote.uuid)
    settled_quote = flows.wait_for_settlement(new_customer, quote.uuid)

    conversion_asserter.assert_settled_conversion(
        quote=settled_quote,
        wallets_before=wallets_before,
        wallets_after=new_customer.wallet.list(),
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
        amount_in=amount_in,
    )


@allure.title("Accepting a quote does not move balances before settlement")
def test_accept_does_not_move_balances_before_settlement(
    new_customer: ApiClient,
    conversion_asserter: ConversionAsserter,
) -> None:
    wallets_before = new_customer.wallet.list()
    quote = flows.create_quote(
        new_customer,
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
        amount_in=Decimal("0.1"),
    )

    accepted_quote = new_customer.quote.accept(quote.uuid)

    checks.assert_equal(
        actual=accepted_quote.quote_status,
        expected=QuoteStatus.ACCEPTED,
        context="quoteStatus right after accept",
    )
    checks.assert_equal(
        actual=accepted_quote.payment_status,
        expected=PaymentStatus.PROCESSING,
        context="paymentStatus right after accept",
    )
    conversion_asserter.assert_account_unchanged(
        wallets_before=wallets_before,
        wallets_after=new_customer.wallet.list(),
    )
