from engine.api_models.common import ApiModel


class InitResponse(ApiModel):
    access_token: str
    token_type: str
    expiry: int
