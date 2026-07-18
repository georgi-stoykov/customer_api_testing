import time
from decimal import Decimal
from engine.api_client import ApiClient
from engine.api_constants import settlement
from engine.api_constants.currencies import Currency
from engine.api_models.quotes import PaymentStatus, Quote, QuoteCreateRequest


def wait_for_settlement(
    api: ApiClient,
    uuid: str,
    *,
    timeout: float = settlement.SETTLEMENT_TIMEOUT,
    interval: float = settlement.SETTLEMENT_POLL_INTERVAL,
) -> Quote:
    deadline = time.monotonic() + timeout
    while True:
        quote = api.quote.get(uuid)
        if quote.payment_status == PaymentStatus.SUCCESS:
            return quote
        if time.monotonic() >= deadline:
            raise TimeoutError(
                f"Quote {uuid} not settled after {timeout}s (paymentStatus={quote.payment_status})",
            )
        time.sleep(interval)


def send_quote(
    api: ApiClient,
    *,
    from_currency: Currency,
    to_currency: Currency,
    amount_in: str | Decimal,
) -> Quote:
    wallets = api.wallet.list()
    source = wallets.by_currency(from_currency)
    target = wallets.by_currency(to_currency)
    request = QuoteCreateRequest(
        from_=from_currency,
        to=to_currency,
        from_wallet=source.id,
        to_wallet=target.id,
        amount_in=str(amount_in),
    )
    quote = api.quote.create(request)
    api.quote.accept(quote.uuid)
    return wait_for_settlement(api, quote.uuid)
