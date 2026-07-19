from engine.api_resources import CustomerApi, QuoteApi, SystemApi, WalletApi
from engine.base_client import BaseClient
from engine.constants import settings


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
        self.system = SystemApi(self._client)
        self.customer = CustomerApi(self._client)
        self.wallet = WalletApi(self._client)
        self.quote = QuoteApi(self._client)
