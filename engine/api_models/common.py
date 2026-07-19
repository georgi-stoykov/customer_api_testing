from collections.abc import Callable, Iterator
from typing import TypeVar
from pydantic import BaseModel, ConfigDict, RootModel

ItemT = TypeVar("ItemT")


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class ErrorResponse(ApiModel):
    detail: str


class RootList(RootModel[list[ItemT]]):
    """Base for list-response models: iteration, len, and loud single-item selection
    (zero matches -> KeyError, multiple -> ValueError; never a silent first-match).
    """

    def _single(
        self,
        predicate: Callable[[ItemT], bool],
        *,
        description: str,
    ) -> ItemT:
        matching_items = [item for item in self.root if predicate(item)]
        if not matching_items:
            raise KeyError(f"No {description}")
        if len(matching_items) > 1:
            raise ValueError(f"{len(matching_items)} matches for {description}, expected one")
        return matching_items[0]

    def __iter__(self) -> Iterator[ItemT]:
        return iter(self.root)

    def __len__(self) -> int:
        return len(self.root)
