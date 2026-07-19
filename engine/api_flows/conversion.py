import time
from decimal import Decimal
import allure
from engine.api_client import ApiClient
from engine.api_constants import quotes, settlement
from engine.api_constants.currencies import Currency
from engine.api_models.quotes import PaymentStatus, Quote, QuoteCreateRequest, QuoteStatus
from engine.base_client import ApiResponse


@allure.step("Create a quote: {amount_in} {from_currency} -> {to_currency}")
def create_quote(
    api: ApiClient,
    *,
    from_currency: str,
    to_currency: str,
    amount_in: Decimal | str,
    from_wallet_id: int | None = None,
    to_wallet_id: int | None = None,
    check: bool = True,
) -> Quote | ApiResponse:
    # from_currency/to_currency are str (not Currency) so negative tests can send invalid
    # codes; a wallet-id override skips resolution for ids the account cannot resolve
    # (mismatched or cross-account wallets).
    wallets = api.wallet.list()
    if from_wallet_id is None:
        from_wallet_id = wallets.by_currency(Currency(from_currency)).id
    if to_wallet_id is None:
        to_wallet_id = wallets.by_currency(Currency(to_currency)).id
    request = QuoteCreateRequest(
        from_=from_currency,
        to=to_currency,
        from_wallet=from_wallet_id,
        to_wallet=to_wallet_id,
        amount_in=str(amount_in),
    )
    return api.quote.create(request, check=check)


@allure.step("Hold quote {uuid} unaccepted for {hold_duration}s")
def hold_quote(
    api: ApiClient,
    uuid: str,
    *,
    hold_duration: float,
    interval: float = settlement.SETTLEMENT_POLL_INTERVAL,
) -> Quote:
    # Polling instead of one long sleep keeps the session's keep-alive socket warm: the
    # simulator silently drops connections idle for ~10s+, and the next request on the
    # stale socket dies with a transport error (.docs/API_BEHAVIOR.md).
    deadline = time.monotonic() + hold_duration
    while True:
        quote = api.quote.get(uuid)
        remaining_hold = deadline - time.monotonic()
        if remaining_hold <= 0:
            return quote
        time.sleep(min(interval, remaining_hold))


@allure.step("Poll quote {uuid} until paymentStatus=SUCCESS")
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


@allure.step("Poll quote {uuid} until quoteStatus=EXPIRED")
def wait_for_expiry(
    api: ApiClient,
    uuid: str,
    *,
    timeout: float = quotes.EXPIRY_TIMEOUT,
    interval: float = settlement.SETTLEMENT_POLL_INTERVAL,
) -> Quote:
    deadline = time.monotonic() + timeout
    while True:
        quote = api.quote.get(uuid)
        if quote.quote_status == QuoteStatus.EXPIRED:
            return quote
        if time.monotonic() >= deadline:
            raise TimeoutError(
                f"Quote {uuid} not expired after {timeout}s (quoteStatus={quote.quote_status})",
            )
        time.sleep(interval)


@allure.step("Create, accept, and settle a quote: {amount_in} {from_currency} -> {to_currency}")
def send_quote(
    api: ApiClient,
    *,
    from_currency: Currency,
    to_currency: Currency,
    amount_in: Decimal,
) -> Quote:
    quote = create_quote(
        api,
        from_currency=from_currency,
        to_currency=to_currency,
        amount_in=amount_in,
    )
    api.quote.accept(quote.uuid)
    return wait_for_settlement(api, quote.uuid)
