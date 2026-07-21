from decimal import Decimal
from http import HTTPStatus
import allure
import pytest
from engine import api_flows as flows
from engine.api_asserters import ConversionAsserter, ErrorAsserter, QuoteAsserter
from engine.api_client import ApiClient
from engine.api_constants import error_details
from engine.api_constants.currencies import Currency
from engine.api_constants.general_messages import (
    PENDING_OWNER_RULING,
    UNCONFIRMED_HALF_EVEN_ROUNDING,
)


@allure.title("A quote for more than the wallet balance is rejected at create")
def test_over_balance_quote_is_rejected(
    customer_api: ApiClient,
    conversion_asserter: ConversionAsserter,
    error_asserter: ErrorAsserter,
) -> None:
    wallets_before = customer_api.wallet.list()
    source_wallet = wallets_before.by_currency(Currency.ETH)

    create_response = flows.create_quote(
        customer_api,
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
        amount_in=source_wallet.balance + Decimal("1"),
        wallets=wallets_before,
        check=False,
    )

    error_asserter.assert_error(
        create_response,
        expected_status=HTTPStatus.PRECONDITION_FAILED,
        expected_detail=error_details.insufficient_funds(source_wallet.id),
    )
    conversion_asserter.assert_wallets_unchanged(
        wallets_before=wallets_before,
        wallets_after=customer_api.wallet.list(),
    )


@pytest.mark.skip(reason=PENDING_OWNER_RULING)
@allure.title("A quote with a negative amount is rejected")
def test_negative_amount_is_rejected(
    customer_api: ApiClient,
    error_asserter: ErrorAsserter,
) -> None:
    create_response = flows.create_quote(
        customer_api,
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
        amount_in=Decimal("-1"),
        check=False,
    )

    error_asserter.assert_error(create_response, expected_status=HTTPStatus.BAD_REQUEST)


@allure.title("A quote with a zero amount is rejected")
def test_zero_amount_is_rejected(
    customer_api: ApiClient,
    error_asserter: ErrorAsserter,
) -> None:
    create_response = flows.create_quote(
        customer_api,
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
        amount_in=Decimal("0"),
        check=False,
    )

    # Zero reads as "amount not specified" — known issue #6.
    error_asserter.assert_error(
        create_response,
        expected_status=HTTPStatus.BAD_REQUEST,
        expected_detail=error_details.AMOUNT_NOT_SPECIFIED,
    )


@pytest.mark.parametrize(
    "requested_amount_in",
    [
        pytest.param(Decimal("0.123456789012"), id="rounds-up"),
        pytest.param(Decimal("0.123456781234"), id="rounds-down"),
        # Exact tie — the one input separating HALF_UP from HALF_EVEN; known issue #7.
        pytest.param(
            Decimal("0.123456785"),
            id="tie-rounds-up",
            marks=pytest.mark.skip(reason=UNCONFIRMED_HALF_EVEN_ROUNDING),
        ),
    ],
)
@allure.title("amountIn {requested_amount_in} is rounded half-up to the source quantityPrecision")
def test_excess_precision_amount_is_rounded(
    customer_api: ApiClient,
    quote_asserter: QuoteAsserter,
    requested_amount_in: Decimal,
) -> None:
    wallets = customer_api.wallet.list()

    quote = flows.create_quote(
        customer_api,
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
        amount_in=requested_amount_in,
        wallets=wallets,
    )

    quote_asserter.assert_amount_in_rounding(
        quote=quote,
        requested_amount_in=requested_amount_in,
        source_currency=wallets.by_currency(Currency.ETH).currency,
    )


@pytest.mark.skip(reason=PENDING_OWNER_RULING)
@allure.title("Quote fee is consistent with its own reported amountIn")
def test_excess_precision_fee_matches_reported_amount_in(
    customer_api: ApiClient,
    quote_asserter: QuoteAsserter,
) -> None:
    quote = flows.create_quote(
        customer_api,
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
        amount_in=Decimal("0.123456789012"),
    )

    quote_asserter.assert_fee(quote)
