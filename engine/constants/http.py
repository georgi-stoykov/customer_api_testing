from enum import StrEnum


class Header(StrEnum):
    AUTHORIZATION = "Authorization"
    ACCEPT = "Accept"


class MediaType(StrEnum):
    JSON = "application/json"


class AuthScheme(StrEnum):
    BEARER = "Bearer"
