from pathlib import Path
from typing import Type, TypeVar

from .database import JsonDatabase as _JsonDatabase
from .models import MigratableModel

# Dev Notes:
# factory = a function or class whose sole purpose is to create instances of a class, in this case, `_JsonDatabase` parametrized with the provided Pydantic model.

T = TypeVar("T", bound=MigratableModel)

def JsonDatabase(
    path: str | Path,
    models: Type[T],
) -> _JsonDatabase[T]:
    return _JsonDatabase(
        path=path,
        database_model=models,
    )