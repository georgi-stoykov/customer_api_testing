from decimal import Decimal
from http import HTTPStatus
import allure
import pytest
from engine import api_flows as flows
from engine.api_asserters import ConversionAsserter, ErrorAsserter
from engine.api_client import ApiClient
from engine.api_constants.currencies import Currency
from engine.api_constants.general_messages import PENDING_OWNER_RULING


@allure.title("Re-accepting a settled quote is rejected and does not convert twice")
def test_reaccepting_settled_quote_does_not_double_convert(
    customer_api: ApiClient,
    conversion_asserter: ConversionAsserter,
    error_asserter: ErrorAsserter,
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
    customer_api.quote.accept(quote.uuid)
    flows.wait_for_settlement(customer_api, quote.uuid)

    reaccept_response = customer_api.quote.accept(quote.uuid, check=False)

    error_asserter.assert_generic_error(reaccept_response, expected_status=HTTPStatus.BAD_REQUEST)
    settled_quote = customer_api.quote.get(quote.uuid)
    conversion_asserter.assert_settled_conversion(
        quote=settled_quote,
        wallets_before=wallets_before,
        wallets_after=customer_api.wallet.list(),
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
    )


@allure.title("An immediate second accept is rejected and the quote settles exactly once")
def test_immediate_double_accept_settles_once(
    customer_api: ApiClient,
    conversion_asserter: ConversionAsserter,
    error_asserter: ErrorAsserter,
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

    customer_api.quote.accept(quote.uuid)
    second_accept_response = customer_api.quote.accept(quote.uuid, check=False)

    error_asserter.assert_generic_error(
        second_accept_response,
        expected_status=HTTPStatus.BAD_REQUEST,
    )
    settled_quote = flows.wait_for_settlement(customer_api, quote.uuid)
    conversion_asserter.assert_settled_conversion(
        quote=settled_quote,
        wallets_before=wallets_before,
        wallets_after=customer_api.wallet.list(),
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
    )


@allure.title("Two sequential conversions on one customer accumulate correctly")
def test_sequential_conversions_accumulate(
    customer_api: ApiClient,
    conversion_asserter: ConversionAsserter,
) -> None:
    amount_in = Decimal("0.5")
    wallets_start = customer_api.wallet.list()

    first_settled_quote = flows.send_quote(
        customer_api,
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
        amount_in=amount_in,
        wallets=wallets_start,
    )
    wallets_middle = customer_api.wallet.list()
    second_settled_quote = flows.send_quote(
        customer_api,
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
        amount_in=amount_in,
        wallets=wallets_middle,
    )
    wallets_end = customer_api.wallet.list()

    conversion_asserter.assert_settled_conversion(
        quote=first_settled_quote,
        wallets_before=wallets_start,
        wallets_after=wallets_middle,
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
    )
    conversion_asserter.assert_settled_conversion(
        quote=second_settled_quote,
        wallets_before=wallets_middle,
        wallets_after=wallets_end,
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
    )


@pytest.mark.skip(reason=PENDING_OWNER_RULING)
@allure.title("Two concurrently accepted quotes both settle with their combined impact")
def test_concurrent_conversions_apply_combined_impact(
    customer_api: ApiClient,
    conversion_asserter: ConversionAsserter,
) -> None:
    amount_in = Decimal("0.5")
    wallets_before = customer_api.wallet.list()
    first_quote = flows.create_quote(
        customer_api,
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
        amount_in=amount_in,
        wallets=wallets_before,
    )
    second_quote = flows.create_quote(
        customer_api,
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
        amount_in=amount_in,
        wallets=wallets_before,
    )

    customer_api.quote.accept(first_quote.uuid)
    customer_api.quote.accept(second_quote.uuid)
    first_settled_quote = flows.wait_for_settlement(customer_api, first_quote.uuid)
    second_settled_quote = flows.wait_for_settlement(customer_api, second_quote.uuid)

    conversion_asserter.assert_combined_conversion_deltas(
        quotes=[first_settled_quote, second_settled_quote],
        wallets_before=wallets_before,
        wallets_after=customer_api.wallet.list(),
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
    )
