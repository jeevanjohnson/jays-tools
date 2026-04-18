from pathlib import Path
from typing import Type, TypeVar

from ..json_database.models import MigratableModel
from .json_collection import JsonCollection as _JsonCollection

T = TypeVar("T", bound=MigratableModel)


def JsonCollection(path: str | Path, model: Type[T]) -> _JsonCollection[T]:
    """Create a JsonCollection instance."""
    return _JsonCollection(
        path=path,
        model=model,
    )