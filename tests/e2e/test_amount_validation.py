from decimal import Decimal
from http import HTTPStatus
import allure
import pytest
from engine import api_flows as flows
from engine.api_asserters import ConversionAsserter, ErrorAsserter
from engine.api_client import ApiClient
from engine.api_constants.currencies import Currency

AMOUNT_NOT_SPECIFIED_DETAIL = "One of 'amountIn' or 'amountOut' must be specified but not both."


@allure.title("Converting the full wallet balance drains the wallet to exactly zero")
def test_full_balance_conversion_drains_wallet(
    new_customer: ApiClient,
    conversion_asserter: ConversionAsserter,
) -> None:
    wallets_before = new_customer.wallet.list()
    amount_in = wallets_before.by_currency(Currency.ETH).balance

    settled_quote = flows.send_quote(
        new_customer,
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
        amount_in=amount_in,
    )

    wallets_after = new_customer.wallet.list()
    conversion_asserter.assert_settled_conversion(
        quote=settled_quote,
        wallets_before=wallets_before,
        wallets_after=wallets_after,
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
        amount_in=amount_in,
    )
    conversion_asserter.assert_wallet_drained(wallets_after.by_currency(Currency.ETH))


@allure.title("A quote for more than the wallet balance is rejected at create")
def test_over_balance_quote_is_rejected(
    new_customer: ApiClient,
    conversion_asserter: ConversionAsserter,
    error_asserter: ErrorAsserter,
) -> None:
    wallets_before = new_customer.wallet.list()
    source_wallet = wallets_before.by_currency(Currency.ETH)

    create_response = flows.create_quote(
        new_customer,
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
        amount_in=source_wallet.balance + Decimal("1"),
        check=False,
    )

    error_asserter.assert_error(
        create_response,
        expected_status=HTTPStatus.PRECONDITION_FAILED,
        expected_detail=f"Insufficient funds available in source wallet #{source_wallet.id}.",
    )
    conversion_asserter.assert_account_unchanged(
        wallets_before=wallets_before,
        wallets_after=new_customer.wallet.list(),
    )


@pytest.mark.xfail(
    reason="Simulator bug: negative amountIn is accepted (201) and settles in reverse, "
    "crediting the source wallet (.docs/API_BEHAVIOR.md).",
    strict=True,
)
@allure.title("A quote with a negative amount is rejected")
def test_negative_amount_is_rejected(
    new_customer: ApiClient,
    error_asserter: ErrorAsserter,
) -> None:
    create_response = flows.create_quote(
        new_customer,
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
        amount_in=Decimal("-1"),
        check=False,
    )

    error_asserter.assert_error(create_response, expected_status=HTTPStatus.BAD_REQUEST)


@allure.title("A quote with a zero amount is rejected")
def test_zero_amount_is_rejected(
    new_customer: ApiClient,
    error_asserter: ErrorAsserter,
) -> None:
    create_response = flows.create_quote(
        new_customer,
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
        amount_in=Decimal("0"),
        check=False,
    )

    # Zero is treated as "amount not specified" (falsy), hence this detail rather than a
    # dedicated must-be-positive validation — documented quirk (.docs/API_BEHAVIOR.md).
    error_asserter.assert_error(
        create_response,
        expected_status=HTTPStatus.BAD_REQUEST,
        expected_detail=AMOUNT_NOT_SPECIFIED_DETAIL,
    )


@allure.title("amountIn finer than the source quantityPrecision is rounded half-up")
def test_excess_precision_amount_is_rounded(
    new_customer: ApiClient,
    conversion_asserter: ConversionAsserter,
) -> None:
    requested_amount_in = Decimal("0.123456789012")

    quote = flows.create_quote(
        new_customer,
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
        amount_in=requested_amount_in,
    )

    conversion_asserter.assert_amount_in_rounding(
        quote=quote,
        requested_amount_in=requested_amount_in,
        source_currency=new_customer.wallet.list().by_currency(Currency.ETH).currency,
    )


@pytest.mark.xfail(
    reason="Simulator bug: for excess-precision input the fee is computed from the unrounded "
    "requested amount, contradicting the quote's own rounded amountIn (.docs/API_BEHAVIOR.md).",
    strict=True,
)
@allure.title("Quote fee is consistent with its own reported amountIn")
def test_excess_precision_fee_matches_reported_amount_in(
    new_customer: ApiClient,
    conversion_asserter: ConversionAsserter,
) -> None:
    quote = flows.create_quote(
        new_customer,
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
        amount_in=Decimal("0.123456789012"),
    )

    wallets = new_customer.wallet.list()
    conversion_asserter.assert_conversion_math(
        quote=quote,
        source_currency=wallets.by_currency(Currency.ETH).currency,
        target_currency=wallets.by_currency(Currency.TRX).currency,
    )
