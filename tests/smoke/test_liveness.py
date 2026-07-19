import allure
from engine.api_client import ApiClient
from engine.utils import checks


@allure.title("Liveness: /health reports system metrics")
def test_health_reports_system_metrics(new_customer: ApiClient) -> None:
    health = new_customer.system.health()

    assert health.uptime, f"health uptime: expected a non-empty value, got {health.uptime!r}"
    assert health.total_authenticated_requests >= 1, (
        f"total_authenticated_requests: expected >= 1, got {health.total_authenticated_requests}"
    )


@allure.title("Liveness: /echo round-trips an authenticated payload")
def test_echo_round_trips_authenticated_payload(new_customer: ApiClient) -> None:
    request_payload = {"probe": "ci-liveness"}

    echo = new_customer.system.echo(request_payload)

    checks.assert_equal(
        actual=echo.request_payload,
        expected=request_payload,
        context="echoed payload",
    )
