import functools
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any

import requests
from pydantic import BaseModel

from .constants.http import AuthScheme, Header, MediaType

logger = logging.getLogger(__name__)


class ApiError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response: "ApiResponse | None" = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response = response


@dataclass
class ApiResponse:
    status_code: int
    json: Any
    method: str
    path: str

    def raise_for_status(self, expected: int) -> "ApiResponse":
        if self.status_code != expected:
            raise ApiError(
                f"{self.method} {self.path} expected {expected}, got {self.status_code}: {self.json!r}",
                status_code=self.status_code,
                response=self,
            )
        return self

    def as_model(self, model: type[BaseModel]) -> BaseModel:
        return model.model_validate(self.json)


def endpoint(
    *,
    model: type[BaseModel] | None = None,
    expected_status: int = HTTPStatus.OK,
) -> Callable:
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, check: bool = True, **kwargs):
            response: ApiResponse = func(*args, **kwargs)
            if not check:
                return response
            response.raise_for_status(expected_status)
            if model is not None:
                return response.as_model(model)
            return response

        return wrapper

    return decorator


class BaseClient:
    def __init__(
        self,
        base_url: str,
        *,
        token: str | None = None,
        timeout: float,
    ) -> None:
        self._base_url = base_url
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers[Header.ACCEPT] = MediaType.JSON
        if token:
            self._session.headers[Header.AUTHORIZATION] = f"{AuthScheme.BEARER} {token}"

    def send(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: Any = None,
    ) -> ApiResponse:
        url = self._base_url + path
        start = time.perf_counter()
        response = self._session.request(
            method,
            url,
            json=json,
            params=params,
            timeout=self._timeout,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info("%s %s -> %s (%.0fms)", method, path, response.status_code, elapsed_ms)
        try:
            body = response.json()
        except ValueError:
            body = None
        return ApiResponse(status_code=response.status_code, json=body, method=method, path=path)
