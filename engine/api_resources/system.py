from http import HTTPMethod, HTTPStatus
from typing import Any
from engine.api_models.system import EchoResponse, HealthResponse
from engine.base_client import ApiResponse, BaseClient, endpoint


class SystemApi:
    def __init__(self, client: BaseClient) -> None:
        self._client = client

    @endpoint(model=HealthResponse, expected_status=HTTPStatus.OK)
    def health(self) -> ApiResponse:
        return self._client.send(HTTPMethod.GET, "/health")

    @endpoint(model=EchoResponse, expected_status=HTTPStatus.OK)
    def echo(self, payload: dict[str, Any]) -> ApiResponse:
        return self._client.send(HTTPMethod.POST, "/echo", json=payload)
