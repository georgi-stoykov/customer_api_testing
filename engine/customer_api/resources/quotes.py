from http import HTTPMethod, HTTPStatus
from engine.base_client import ApiResponse, BaseClient, endpoint
from engine.customer_api.models.quotes import Quote, QuoteCreateRequest

QUOTES = "/api/v1/quote"
QUOTE = "/api/v1/quote/{uuid}"
QUOTE_ACCEPT = "/api/v1/quote/accept/{uuid}"


class QuoteApi:
    def __init__(self, client: BaseClient) -> None:
        self._client = client

    @endpoint(model=Quote, expected_status=HTTPStatus.CREATED)
    def create(self, request: QuoteCreateRequest) -> ApiResponse:
        return self._client.send(
            HTTPMethod.POST,
            QUOTES,
            json=request.model_dump(by_alias=True),
        )

    @endpoint(model=Quote, expected_status=HTTPStatus.OK)
    def get(self, uuid: str) -> ApiResponse:
        return self._client.send(HTTPMethod.GET, QUOTE.format(uuid=uuid))

    @endpoint(model=Quote, expected_status=HTTPStatus.OK)
    def accept(self, uuid: str) -> ApiResponse:
        return self._client.send(HTTPMethod.PUT, QUOTE_ACCEPT.format(uuid=uuid))
