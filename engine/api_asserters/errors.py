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
            expected=expected_status,
            context=f"{response.method} {response.path} status code",
        )
        if expected_detail is not None:
            error = response.as_model(ErrorResponse)
            checks.assert_equal(
                actual=error.detail,
                expected=expected_detail,
                context=f"{response.method} {response.path} error detail",
            )

    @allure.step("Response is the generic {expected_status} error")
    def assert_generic_error(
        self,
        response: ApiResponse,
        *,
        expected_status: HTTPStatus,
    ) -> None:
        # The simulator's generic rejections carry the HTTP reason phrase as their detail.
        self.assert_error(
            response,
            expected_status=expected_status,
            expected_detail=expected_status.phrase,
        )
