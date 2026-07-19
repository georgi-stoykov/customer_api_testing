from typing import Any
from engine.api_models.common import ApiModel


class HealthResponse(ApiModel):
    uptime: str
    approximate_db_size: str
    total_authenticated_requests: int


class EchoResponse(ApiModel):
    auth_token_expiry_time: str
    request_payload: dict[str, Any]
