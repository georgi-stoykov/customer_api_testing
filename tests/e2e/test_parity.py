from decimal import Decimal
import allure
from engine import api_flows as flows
from engine.api_client import ApiClient
from engine.api_constants.currencies import Currency
from engine.utils import checks


@allure.title("Every wallet reads identically via the list and the single-wallet endpoint")
def test_wallet_list_and_single_get_agree(new_customer: ApiClient) -> None:
    wallets = new_customer.wallet.list()

    for listed_wallet in wallets:
        single_wallet = new_customer.wallet.get(listed_wallet.id)
        checks.assert_equal(
            actual=single_wallet,
            expected=listed_wallet,
            context=f"{listed_wallet.label} single get vs list entry",
        )


@allure.title("A quote reads identically via the list and the single-quote endpoint")
def test_quote_list_and_single_get_agree(new_customer: ApiClient) -> None:
    quote = flows.create_quote(
        new_customer,
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
        amount_in=Decimal("0.1"),
    )

    account_quotes = new_customer.quote.list()
    fetched_quote = new_customer.quote.get(quote.uuid)

    checks.assert_equal(
        actual=len(account_quotes),
        expected=1,
        context="quote count for a fresh account with one quote",
    )
    checks.assert_equal(
        actual=account_quotes.by_uuid(quote.uuid),
        expected=fetched_quote,
        context="quote list entry vs single get",
    )


@allure.title("The create response and an immediate get return the same quote")
def test_quote_create_response_and_get_agree(new_customer: ApiClient) -> None:
    created_quote = flows.create_quote(
        new_customer,
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
        amount_in=Decimal("0.1"),
    )

    fetched_quote = new_customer.quote.get(created_quote.uuid)

    checks.assert_equal(
        actual=fetched_quote,
        expected=created_quote,
        context="quote fetched right after create vs create response",
    )
