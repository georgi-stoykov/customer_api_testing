from decimal import Decimal
import allure
from engine import api_flows as flows
from engine.api_asserters import QuoteAsserter
from engine.api_client import ApiClient
from engine.api_constants.currencies import Currency
from engine.api_models.quotes import Quote
from engine.utils import checks


@allure.title("Every wallet reads identically via the list and the single-wallet endpoint")
def test_wallet_list_and_single_get_agree(customer_api: ApiClient) -> None:
    wallets = customer_api.wallet.list()

    for listed_wallet in wallets:
        single_wallet = customer_api.wallet.get(listed_wallet.id)
        checks.assert_equal(
            actual=single_wallet,
            expected=listed_wallet,
            context=f"{listed_wallet.label} single get vs list entry",
        )


@allure.title("A quote reads identically via the list and the single-quote endpoint")
def test_quote_list_and_single_get_agree(customer_api: ApiClient, pending_quote: Quote) -> None:
    customer_quotes = customer_api.quote.list()
    fetched_quote = customer_api.quote.get(pending_quote.uuid)

    checks.assert_equal(
        actual=len(customer_quotes),
        expected=1,
        context="quote count for a fresh customer with one quote",
    )
    checks.assert_equal(
        actual=customer_quotes.by_uuid(pending_quote.uuid),
        expected=fetched_quote,
        context="quote list entry vs single get",
    )


@allure.title("The create response and an immediate get return the same quote")
def test_quote_create_response_and_get_agree(
    customer_api: ApiClient,
    pending_quote: Quote,
) -> None:
    fetched_quote = customer_api.quote.get(pending_quote.uuid)

    checks.assert_equal(
        actual=fetched_quote,
        expected=pending_quote,
        context="quote fetched right after create vs create response",
    )


@allure.title("A created quote echoes the requested pair, amount, and wallet ids")
def test_quote_echoes_create_request(
    customer_api: ApiClient,
    quote_asserter: QuoteAsserter,
) -> None:
    amount_in = Decimal("0.1")
    wallets = customer_api.wallet.list()

    quote = flows.create_quote(
        customer_api,
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
        amount_in=amount_in,
        wallets=wallets,
    )

    quote_asserter.assert_quote_echoes_request(
        quote=quote,
        from_currency=Currency.ETH,
        to_currency=Currency.TRX,
        amount_in=amount_in,
        source_wallet_id=wallets.by_currency(Currency.ETH).id,
        target_wallet_id=wallets.by_currency(Currency.TRX).id,
    )
