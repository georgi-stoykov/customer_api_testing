from decimal import Decimal
from http import HTTPStatus
import allure
from engine import api_flows as flows
from engine.api_asserters import ConversionAsserter, ErrorAsserter
from engine.api_client import ApiClient
from engine.api_constants.currencies import Currency

UNKNOWN_QUOTE_UUID = "00000000-0000-0000-0000-000000000000"
UNKNOWN_WALLET_ID = 99999999
NOT_FOUND_DETAIL = "Not Found"


@allure.title("Getting an unknown quote uuid returns 404")
def test_get_unknown_quote_returns_not_found(
    new_customer: ApiClient,
    error_asserter: ErrorAsserter,
) -> None:
    get_response = new_customer.quote.get(UNKNOWN_QUOTE_UUID, check=False)

    error_asserter.assert_error(
        get_response,
        expected_status=HTTPStatus.NOT_FOUND,
        expected_detail=NOT_FOUND_DETAIL,
    )


@allure.title("Accepting an unknown quote uuid returns 404")
def test_accept_unknown_quote_returns_not_found(
    new_customer: ApiClient,
    error_asserter: ErrorAsserter,
) -> None:
    accept_response = new_customer.quote.accept(UNKNOWN_QUOTE_UUID, check=False)

    error_asserter.assert_error(
        accept_response,
        expected_status=HTTPStatus.NOT_FOUND,
        expected_detail=NOT_FOUND_DETAIL,
    )


@allure.title("Getting an unknown wallet id returns 404")
def test_get_unknown_wallet_returns_not_found(
    new_customer: ApiClient,
    error_asserter: ErrorAsserter,
) -> None:
    get_response = new_customer.wallet.get(UNKNOWN_WALLET_ID, check=False)

    error_asserter.assert_error(
        get_response,
        expected_status=HTTPStatus.NOT_FOUND,
        expected_detail=NOT_FOUND_DETAIL,
    )


@allure.title("A quote with an unknown currency code is rejected")
def test_unknown_currency_code_is_rejected(
    new_customer: ApiClient,
    error_asserter: ErrorAsserter,
) -> None:
    source_wallet = new_customer.wallet.list().by_currency(Currency.ETH)

    create_response = flows.create_quote(
        new_customer,
        from_currency="XYZ",
        to_currency=Currency.TRX,
        amount_in=Decimal("0.1"),
        from_wallet_id=source_wallet.id,
        check=False,
    )

    error_asserter.assert_error(
        create_response,
        expected_status=HTTPStatus.BAD_REQUEST,
        expected_detail=(
            f"Request to trade XYZ for {Currency.TRX} "
            f"but source wallet has currency {Currency.ETH}."
        ),
    )


@allure.title("A quote whose from currency mismatches the source wallet is rejected")
def test_currency_wallet_mismatch_is_rejected(
    new_customer: ApiClient,
    error_asserter: ErrorAsserter,
) -> None:
    mismatched_wallet = new_customer.wallet.list().by_currency(Currency.TRX)

    create_response = flows.create_quote(
        new_customer,
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
        amount_in=Decimal("0.1"),
        from_wallet_id=mismatched_wallet.id,
        check=False,
    )

    error_asserter.assert_error(
        create_response,
        expected_status=HTTPStatus.BAD_REQUEST,
        expected_detail=(
            f"Request to trade {Currency.ETH} for {Currency.TRX} "
            f"but source wallet has currency {Currency.TRX}."
        ),
    )


@allure.title("A quote using another account's wallet id is rejected and leaves it untouched")
def test_cross_account_wallet_id_is_rejected(
    new_customer: ApiClient,
    conversion_asserter: ConversionAsserter,
    error_asserter: ErrorAsserter,
) -> None:
    other_customer = flows.new_customer()
    other_wallets_before = other_customer.wallet.list()
    other_source_wallet = other_wallets_before.by_currency(Currency.ETH)

    create_response = flows.create_quote(
        new_customer,
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
        amount_in=Decimal("0.1"),
        from_wallet_id=other_source_wallet.id,
        check=False,
    )

    error_asserter.assert_error(
        create_response,
        expected_status=HTTPStatus.BAD_REQUEST,
        expected_detail=f"Source wallet with ID #{other_source_wallet.id} not found.",
    )
    conversion_asserter.assert_account_unchanged(
        wallets_before=other_wallets_before,
        wallets_after=other_customer.wallet.list(),
    )
