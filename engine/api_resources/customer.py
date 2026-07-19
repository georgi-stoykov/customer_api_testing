from http import HTTPMethod, HTTPStatus
from engine.api_models.customer import InitResponse
from engine.base_client import ApiResponse, BaseClient, endpoint


class CustomerApi:
    def __init__(self, client: BaseClient) -> None:
        self._client = client

    @endpoint(model=InitResponse, expected_status=HTTPStatus.OK)
    def init(self) -> ApiResponse:
        return self._client.send(HTTPMethod.GET, "/init")
