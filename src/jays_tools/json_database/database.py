import asyncio
from pathlib import Path
from copy import deepcopy
from typing import Generic, Type, TypeVar

from pydantic import BaseModel, ValidationError

from .file import JsonFile
from .models import MigratableModel

T = TypeVar("T", bound=MigratableModel)

# Known Bugs/Features to Implement:
# - Atomic writes to prevent data loss. See: https://stackoverflow.com/a/2333872/11761617
# - Cross process protection: if multiple processes access the same file, this could lead to corruption.
#    To fix, we would need to do OS level file locking.

def model_has_defaults(model: Type[BaseModel]) -> bool:
    try:
        model()
        return True
    except ValidationError:
        return False

class JsonDatabase(Generic[T]):
    def __new__(cls, *args, **kwargs) -> "JsonDatabase[T]":
        database_model = kwargs.get("database_model")

        if database_model is None:
            raise ValueError("database_model is required to create a JsonDatabase instance.")

        if not model_has_defaults(database_model):
            raise ValueError(
                f"JsonDatabase requires all fields to have defaults, but "
                f"{database_model.__name__} has required fields."
            )

        return super().__new__(cls)

    def __init__(
        self,
        path: str | Path,
        database_model: Type[T],
    ):
        # Private attrs to prevent external mutation
        self.private_path = JsonFile(path)
        self.private_database: T = None # type: ignore[assignment]
        self.private_database_model: Type[T] = database_model

    def get_path(self) -> Path:
        return self.private_path.absolute()

    def get_database(self) -> T:
        if self.private_database is None:
            self.read()

        return deepcopy(self.private_database)
    
    def set_database(self, database: T) -> T:
        self.private_database = deepcopy(database)
        return deepcopy(self.private_database)

    def write(self, database: T) -> T:
        """Write database to file and update cache."""
        if not self.private_path.parent.exists():
            self.private_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.private_path.write_text(
            database.model_dump_json(indent=4, ensure_ascii=False),
            encoding="utf-8",
            errors="strict",
        )
        
        self.set_database(database)

        return deepcopy(database)

    def read(self) -> T:
        """Read database from file and cache it."""
        if not self.private_path.exists():
            return self.write(self.private_database_model())
        
        raw_database = self.private_path.read_text(
            encoding="utf-8", 
            errors="strict"
        )

        if not raw_database:
            return self.write(self.private_database_model())

        try:
            self.set_database(
                self.private_database_model.model_validate_json(raw_database)
            )
        except ValidationError as error:
            error_message = (
                f"Failed to read database file {self.private_path} due to validation error:\n{error}\n"
                "If this is for production use, consider implementing a migration strategy.\n"
            )
            raise ValueError(error_message)

        return deepcopy(self.private_database)

    def update_database(self, updated_database: T) -> T:
        """Update database with new data, write to file, and return a copy."""
        self.write(updated_database)
        return deepcopy(self.private_database)

    # async versions, "just in case" situations

    async def async_update_database(self, updated_database: T) -> T:
        async with asyncio.Lock():
            return await asyncio.to_thread(self.update_database, updated_database)

    async def async_get_database(self) -> T:
        async with asyncio.Lock():
            return await asyncio.to_thread(self.get_database)