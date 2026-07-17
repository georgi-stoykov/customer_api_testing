from http import HTTPMethod, HTTPStatus

from ...base import BaseClient, endpoint
from ..models.account import InitResponse

INIT = "/init"


class AccountApi:
    def __init__(self, client: BaseClient) -> None:
        self._client = client

    @endpoint(model=InitResponse, expected_status=HTTPStatus.OK)
    def init(self):
        return self._client.send(HTTPMethod.GET, INIT)
