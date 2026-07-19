from decimal import ROUND_HALF_UP, Decimal
from engine.utils import checks


def round_half_up(
    value: Decimal,
    decimal_places: int,
) -> Decimal:
    return value.quantize(Decimal(10) ** -decimal_places, rounding=ROUND_HALF_UP)


def compute_max_rounding_error(decimal_places: int) -> Decimal:
    # the largest amount rounding to N decimal places can move a value:
    # compute_max_rounding_error(2) == Decimal("0.005"), e.g. 1.995 rounds to 2.00
    smallest_step = Decimal(10) ** -decimal_places
    return smallest_step / 2


def assert_equal(
    *,
    actual: Decimal,
    expected: Decimal,
    context: str,
) -> None:
    checks.assert_equal(actual=actual, expected=expected, context=context)


def assert_equal_with_tolerance(
    *,
    actual: Decimal,
    expected: Decimal,
    tolerance: Decimal,
    context: str,
) -> None:
    # with tolerance=Decimal("0.005"),
    # actual=1.998 vs expected=2.00 passes (off by 0.002), actual=1.99 fails (off by 0.01).
    difference = abs(actual - expected)
    assert difference <= tolerance, (
        f"{context}: expected {expected} within {tolerance}, got {actual} (off by {difference})"
    )
