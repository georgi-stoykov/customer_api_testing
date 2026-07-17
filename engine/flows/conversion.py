import time
from decimal import Decimal

from ..api.models.quotes import PaymentStatus, Quote, QuoteCreateRequest
from ..client import ApiClient
from ..constants import settings
from ..constants.currencies import Currency


def wait_for_settlement(
    api: ApiClient,
    uuid: str,
    *,
    timeout: float = settings.SETTLEMENT_TIMEOUT,
    interval: float = settings.SETTLEMENT_POLL_INTERVAL,
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


def convert(
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
