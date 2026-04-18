import asyncio
import tempfile
import threading
from pathlib import Path
from copy import deepcopy
from typing import Generic, Type, TypeVar

from pydantic import BaseModel, ValidationError

from .file import JsonFile
from .models import MigratableModel

T = TypeVar("T", bound=MigratableModel)

# Known Limitations:
# - Cross process protection: if multiple processes access the same file, this could lead to corruption.
#    Single-process only by design. For multi-process use, use a proper database (PostgreSQL, SQLite, etc).

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
    ) -> None:
        """Initialize database with path and model."""
        # Private attrs to prevent external mutation
        self.private_path = JsonFile(path)
        self.private_database: T = None  # type: ignore[assignment]
        self.private_database_model: Type[T] = database_model
        # Reentrant lock for serializing file I/O operations
        # (read() calls write(), so we need RLock not Lock)
        self.private_lock = threading.RLock()

    def get_path(self) -> Path:
        return self.private_path.absolute()

    def get_database(self) -> T:
        """Get a copy of the database from cache, or read from disk if needed."""
        if self.private_database is None:
            self.read()

        return deepcopy(self.private_database)

    def set_database(self, database: T) -> T:
        """Set and cache the database."""
        self.private_database = deepcopy(database)
        return deepcopy(self.private_database)

    def write(self, database: T) -> T:
        """Write database to file atomically and update cache."""
        with self.private_lock:
            if not self.private_path.parent.exists():
                self.private_path.parent.mkdir(parents=True, exist_ok=True)

            json_content = database.model_dump_json(indent=4, ensure_ascii=False)

            # Write atomically: write to temp file, then rename
            # This prevents partial reads if file is accessed while writing
            with tempfile.NamedTemporaryFile(
                mode="w",
                dir=self.private_path.parent,
                delete=False,
                suffix=".tmp",
                encoding="utf-8",
            ) as tmp_file:
                tmp_file.write(json_content)
                tmp_path = Path(tmp_file.name)

            # On Windows, we need to delete the old file first before renaming
            # to avoid permission errors during concurrent access
            self.private_path.unlink(missing_ok=True)

            # Now rename temp file to target (safe because old file is gone)
            tmp_path.replace(self.private_path)

            self.set_database(database)

            return deepcopy(database)

    def read(self) -> T:
        """Read database from file and cache it."""
        with self.private_lock:
            if not self.private_path.exists():
                return self.write(self.private_database_model())

            raw_database = self.private_path.read_text(
                encoding="utf-8",
                errors="strict",
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

    # Async versions, "just in case" situations

    async def async_update_database(self, updated_database: T) -> T:
        """Async update with thread-pool execution and locking."""
        async with asyncio.Lock():
            return await asyncio.to_thread(self.update_database, updated_database)

    async def async_get_database(self) -> T:
        """Async read with thread-pool execution and locking."""
        async with asyncio.Lock():
            return await asyncio.to_thread(self.get_database)