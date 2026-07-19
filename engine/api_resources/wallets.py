from http import HTTPMethod, HTTPStatus
from engine.api_models.wallets import AccountWallets
from engine.base_client import ApiResponse, BaseClient, endpoint


class WalletApi:
    def __init__(self, client: BaseClient) -> None:
        self._client = client

    @endpoint(model=AccountWallets, expected_status=HTTPStatus.OK)
    def list(self) -> ApiResponse:
        return self._client.send(HTTPMethod.GET, "/api/wallet")
