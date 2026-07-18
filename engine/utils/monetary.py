from decimal import ROUND_HALF_UP, Decimal


def round_half_up(
    value: Decimal,
    decimal_places: int,
) -> Decimal:
    return value.quantize(Decimal(10) ** -decimal_places, rounding=ROUND_HALF_UP)


def max_rounding_error(decimal_places: int) -> Decimal:
    return Decimal(10) ** -decimal_places / 2


def assert_equal(
    *,
    actual: Decimal,
    expected: Decimal,
    context: str,
) -> None:
    assert actual == expected, f"{context}: expected {expected}, got {actual}"


def assert_equal_within(
    *,
    actual: Decimal,
    expected: Decimal,
    allowed_error: Decimal,
    context: str,
) -> None:
    observed_error = abs(actual - expected)
    assert observed_error <= allowed_error, (
        f"{context}: expected {expected} within {allowed_error}, "
        f"got {actual} (off by {observed_error})"
    )
