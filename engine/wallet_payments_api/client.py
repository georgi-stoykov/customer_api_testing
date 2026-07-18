from engine.base_client import BaseClient
from engine.constants import settings
from engine.wallet_payments_api.resources import AccountApi, QuoteApi, WalletApi


class ApiClient:
    def __init__(
        self,
        *,
        token: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self._client = BaseClient(
            base_url or settings.BASE_URL,
            token=token,
            timeout=settings.REQUEST_TIMEOUT,
        )
        self.account = AccountApi(self._client)
        self.wallet = WalletApi(self._client)
        self.quote = QuoteApi(self._client)
