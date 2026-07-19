import time
from collections.abc import Callable
from decimal import Decimal
import allure
from engine.api_client import ApiClient
from engine.api_constants import quotes, settlement
from engine.api_constants.currencies import Currency
from engine.api_models.quotes import PaymentStatus, Quote, QuoteCreateRequest, QuoteStatus
from engine.api_models.wallets import CustomerWallets
from engine.base_client import ApiResponse


@allure.step("Create a quote: {amount_in} {from_currency} -> {to_currency}")
def create_quote(
    api: ApiClient,
    *,
    from_currency: Currency | str,
    to_currency: Currency | str,
    amount_in: Decimal,
    wallets: CustomerWallets | None = None,
    from_wallet_id: int | None = None,
    check: bool = True,
) -> Quote | ApiResponse:
    # Currencies admit plain str so negative tests can send invalid codes; a wallet-id
    # override skips resolution for ids the customer cannot resolve (mismatched or
    # cross-customer wallets). Callers that already hold a wallets snapshot pass it to
    # save the resolution fetch.
    if wallets is None:
        wallets = api.wallet.list()
    if from_wallet_id is None:
        from_wallet_id = wallets.by_currency(Currency(from_currency)).id
    request = QuoteCreateRequest(
        from_=from_currency,
        to=to_currency,
        from_wallet=from_wallet_id,
        to_wallet=wallets.by_currency(Currency(to_currency)).id,
        amount_in=str(amount_in),
    )
    return api.quote.create(request, check=check)


def _poll_quote(
    api: ApiClient,
    uuid: str,
    *,
    until: Callable[[Quote], bool],
    timeout: float,
    interval: float,
) -> Quote:
    # Polling instead of one long sleep keeps the session's keep-alive socket warm: the
    # simulator silently drops connections idle for ~10s+, and the next request on the
    # stale socket dies with a transport error (.docs/API_BEHAVIOR.md). Returns the last
    # fetched quote whether or not the condition was met — callers decide how to fail.
    deadline = time.monotonic() + timeout
    while True:
        quote = api.quote.get(uuid)
        remaining_wait = deadline - time.monotonic()
        if until(quote) or remaining_wait <= 0:
            return quote
        time.sleep(min(interval, remaining_wait))


def _is_settled(quote: Quote) -> bool:
    return quote.payment_status == PaymentStatus.SUCCESS


def _is_expired(quote: Quote) -> bool:
    return quote.quote_status == QuoteStatus.EXPIRED


@allure.step("Hold quote {uuid} unaccepted for {hold_duration}s")
def hold_quote(
    api: ApiClient,
    uuid: str,
    *,
    hold_duration: float,
    interval: float = settlement.SETTLEMENT_POLL_INTERVAL,
) -> Quote:
    return _poll_quote(
        api,
        uuid,
        until=lambda quote: False,
        timeout=hold_duration,
        interval=interval,
    )


@allure.step("Poll quote {uuid} until paymentStatus=SUCCESS")
def wait_for_settlement(
    api: ApiClient,
    uuid: str,
    *,
    timeout: float = settlement.SETTLEMENT_TIMEOUT,
    interval: float = settlement.SETTLEMENT_POLL_INTERVAL,
) -> Quote:
    quote = _poll_quote(api, uuid, until=_is_settled, timeout=timeout, interval=interval)
    if not _is_settled(quote):
        raise TimeoutError(
            f"Quote {uuid} not settled after {timeout}s (paymentStatus={quote.payment_status})",
        )
    return quote


@allure.step("Poll quote {uuid} until quoteStatus=EXPIRED")
def wait_for_expiry(
    api: ApiClient,
    uuid: str,
    *,
    timeout: float = quotes.EXPIRY_TIMEOUT,
    interval: float = settlement.SETTLEMENT_POLL_INTERVAL,
) -> Quote:
    quote = _poll_quote(api, uuid, until=_is_expired, timeout=timeout, interval=interval)
    if not _is_expired(quote):
        raise TimeoutError(
            f"Quote {uuid} not expired after {timeout}s (quoteStatus={quote.quote_status})",
        )
    return quote


@allure.step("Create, accept, and settle a quote: {amount_in} {from_currency} -> {to_currency}")
def send_quote(
    api: ApiClient,
    *,
    from_currency: Currency,
    to_currency: Currency,
    amount_in: Decimal,
    wallets: CustomerWallets | None = None,
) -> Quote:
    quote = create_quote(
        api,
        from_currency=from_currency,
        to_currency=to_currency,
        amount_in=amount_in,
        wallets=wallets,
    )
    api.quote.accept(quote.uuid)
    return wait_for_settlement(api, quote.uuid)
