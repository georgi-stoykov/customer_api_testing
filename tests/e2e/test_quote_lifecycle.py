from decimal import Decimal
from http import HTTPStatus
import allure
import pytest
from engine import api_flows as flows
from engine.api_asserters import ConversionAsserter, ErrorAsserter
from engine.api_client import ApiClient
from engine.api_constants.currencies import Currency


@allure.title("Re-accepting a settled quote is rejected and does not convert twice")
def test_reaccepting_settled_quote_does_not_double_convert(
    new_customer: ApiClient,
    conversion_asserter: ConversionAsserter,
    error_asserter: ErrorAsserter,
) -> None:
    amount_in = Decimal("0.1")
    wallets_before = new_customer.wallet.list()
    quote = flows.create_quote(
        new_customer,
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
        amount_in=amount_in,
    )
    new_customer.quote.accept(quote.uuid)
    flows.wait_for_settlement(new_customer, quote.uuid)

    reaccept_response = new_customer.quote.accept(quote.uuid, check=False)

    error_asserter.assert_error(
        reaccept_response,
        expected_status=HTTPStatus.BAD_REQUEST,
        expected_detail="Bad Request",
    )
    settled_quote = flows.wait_for_settlement(new_customer, quote.uuid)
    conversion_asserter.assert_settled_conversion(
        quote=settled_quote,
        wallets_before=wallets_before,
        wallets_after=new_customer.wallet.list(),
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
        amount_in=amount_in,
    )


@allure.title("An immediate second accept is rejected and the quote settles exactly once")
def test_immediate_double_accept_settles_once(
    new_customer: ApiClient,
    conversion_asserter: ConversionAsserter,
    error_asserter: ErrorAsserter,
) -> None:
    amount_in = Decimal("0.1")
    wallets_before = new_customer.wallet.list()
    quote = flows.create_quote(
        new_customer,
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
        amount_in=amount_in,
    )

    new_customer.quote.accept(quote.uuid)
    second_accept_response = new_customer.quote.accept(quote.uuid, check=False)

    error_asserter.assert_error(
        second_accept_response,
        expected_status=HTTPStatus.BAD_REQUEST,
        expected_detail="Bad Request",
    )
    settled_quote = flows.wait_for_settlement(new_customer, quote.uuid)
    conversion_asserter.assert_settled_conversion(
        quote=settled_quote,
        wallets_before=wallets_before,
        wallets_after=new_customer.wallet.list(),
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
        amount_in=amount_in,
    )


@allure.title("Two sequential conversions on one account accumulate correctly")
def test_sequential_conversions_accumulate(
    new_customer: ApiClient,
    conversion_asserter: ConversionAsserter,
) -> None:
    amount_in = Decimal("0.5")
    wallets_start = new_customer.wallet.list()

    first_settled_quote = flows.send_quote(
        new_customer,
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
        amount_in=amount_in,
    )
    wallets_middle = new_customer.wallet.list()
    second_settled_quote = flows.send_quote(
        new_customer,
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
        amount_in=amount_in,
    )
    wallets_end = new_customer.wallet.list()

    conversion_asserter.assert_settled_conversion(
        quote=first_settled_quote,
        wallets_before=wallets_start,
        wallets_after=wallets_middle,
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
        amount_in=amount_in,
    )
    conversion_asserter.assert_settled_conversion(
        quote=second_settled_quote,
        wallets_before=wallets_middle,
        wallets_after=wallets_end,
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
        amount_in=amount_in,
    )


@pytest.mark.xfail(
    reason="Simulator bug: concurrent settlements apply deltas to a stale balance snapshot "
    "and the last write wins — one conversion's wallet impact is lost "
    "(.docs/API_BEHAVIOR.md). Non-strict: the race's determinism is unverified.",
    strict=False,
)
@allure.title("Two concurrently accepted quotes both settle with their combined impact")
def test_concurrent_conversions_apply_combined_impact(
    new_customer: ApiClient,
    conversion_asserter: ConversionAsserter,
) -> None:
    amount_in = Decimal("0.5")
    wallets_before = new_customer.wallet.list()
    first_quote = flows.create_quote(
        new_customer,
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
        amount_in=amount_in,
    )
    second_quote = flows.create_quote(
        new_customer,
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
        amount_in=amount_in,
    )

    new_customer.quote.accept(first_quote.uuid)
    new_customer.quote.accept(second_quote.uuid)
    first_settled_quote = flows.wait_for_settlement(new_customer, first_quote.uuid)
    second_settled_quote = flows.wait_for_settlement(new_customer, second_quote.uuid)

    conversion_asserter.assert_combined_conversion_deltas(
        quotes=[first_settled_quote, second_settled_quote],
        wallets_before=wallets_before,
        wallets_after=new_customer.wallet.list(),
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
    )
