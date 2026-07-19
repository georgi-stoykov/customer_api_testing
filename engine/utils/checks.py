from types import TracebackType


def assert_equal(
    *,
    actual: object,
    expected: object,
    context: str,
) -> None:
    assert actual == expected, f"{context}: expected {expected}, got {actual}"


class SoftAssertions:
    """Collects assertion failures instead of stopping at the first one.

    Each `with soft:` block suppresses and records an AssertionError; other
    exception types propagate. `assert_all()` raises one combined failure.
    """

    def __init__(self) -> None:
        self._failures: list[str] = []

    def __enter__(self) -> "SoftAssertions":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        if exc_type is not None and issubclass(exc_type, AssertionError):
            self._failures.append(str(exc))
            return True
        return False

    def assert_all(self) -> None:
        if not self._failures:
            return
        numbered = "\n".join(
            f"{index}) {failure}" for index, failure in enumerate(self._failures, start=1)
        )
        raise AssertionError(f"{len(self._failures)} assertion(s) failed:\n{numbered}")
