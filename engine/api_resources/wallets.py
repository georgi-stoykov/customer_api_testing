from http import HTTPMethod, HTTPStatus
from engine.api_models.wallets import CustomerWallets, Wallet
from engine.base_client import ApiResponse, BaseClient, endpoint


class WalletApi:
    def __init__(self, client: BaseClient) -> None:
        self._client = client

    @endpoint(model=CustomerWallets, expected_status=HTTPStatus.OK)
    def list(self) -> ApiResponse:
        return self._client.send(HTTPMethod.GET, "/api/wallet")

    @endpoint(model=Wallet, expected_status=HTTPStatus.OK)
    def get(self, wallet_id: int) -> ApiResponse:
        return self._client.send(HTTPMethod.GET, f"/api/wallet/{wallet_id}")
