from http import HTTPStatus
import allure
from engine.api_models.common import ErrorResponse
from engine.base_client import ApiResponse
from engine.utils import checks


class ErrorAsserter:
    @allure.step("Response is {expected_status} with the expected error detail")
    def assert_error(
        self,
        response: ApiResponse,
        *,
        expected_status: HTTPStatus,
        expected_detail: str | None = None,
    ) -> None:
        checks.assert_equal(
            actual=response.status_code,
            expected=int(expected_status),
            context=f"{response.method} {response.path} status code",
        )
        if expected_detail is not None:
            error = ErrorResponse.model_validate(response.json)
            checks.assert_equal(
                actual=error.detail,
                expected=expected_detail,
                context=f"{response.method} {response.path} error detail",
            )
