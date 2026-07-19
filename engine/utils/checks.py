def assert_equal(
    *,
    actual: object,
    expected: object,
    context: str,
) -> None:
    assert actual == expected, f"{context}: expected {expected}, got {actual}"
