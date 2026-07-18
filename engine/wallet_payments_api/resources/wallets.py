from http import HTTPMethod, HTTPStatus
from engine.base_client import BaseClient, endpoint
from engine.wallet_payments_api.models.wallets import AccountWallets

WALLETS = "/api/wallet"


class WalletApi:
    def __init__(self, client: BaseClient) -> None:
        self._client = client

    @endpoint(model=AccountWallets, expected_status=HTTPStatus.OK)
    def list(self):
        return self._client.send(HTTPMethod.GET, WALLETS)
