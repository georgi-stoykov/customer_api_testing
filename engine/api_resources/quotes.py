from http import HTTPMethod, HTTPStatus
from engine.api_models.quotes import AccountQuotes, Quote, QuoteCreateRequest
from engine.base_client import ApiResponse, BaseClient, endpoint


class QuoteApi:
    def __init__(self, client: BaseClient) -> None:
        self._client = client

    @endpoint(model=AccountQuotes, expected_status=HTTPStatus.OK)
    def list(self) -> ApiResponse:
        return self._client.send(HTTPMethod.GET, "/api/v1/quote")

    @endpoint(model=Quote, expected_status=HTTPStatus.CREATED)
    def create(self, request: QuoteCreateRequest) -> ApiResponse:
        return self._client.send(
            HTTPMethod.POST,
            "/api/v1/quote",
            json=request.model_dump(by_alias=True),
        )

    @endpoint(model=Quote, expected_status=HTTPStatus.OK)
    def get(self, uuid: str) -> ApiResponse:
        return self._client.send(HTTPMethod.GET, f"/api/v1/quote/{uuid}")

    @endpoint(model=Quote, expected_status=HTTPStatus.OK)
    def accept(self, uuid: str) -> ApiResponse:
        return self._client.send(HTTPMethod.PUT, f"/api/v1/quote/accept/{uuid}")
