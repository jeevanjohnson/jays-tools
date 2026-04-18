import asyncio
from pathlib import Path
from typing import Generic, Type, TypeVar

from ..json_database import JsonDatabase, MigratableModel
from ..json_database.database import JsonDatabase as _JsonDatabase

T = TypeVar("T", bound=MigratableModel)


class JsonCollection(Generic[T]):
    """Collection of entities stored as individual JSON files, keyed by filename."""

    def __init__(
        self,
        path: str | Path,
        model: Type[T],
    ) -> None:
        self.private_path = Path(path)
        self.private_model = model
        self._lock = asyncio.Lock()

    def create(self, key: str, database: T) -> T:
        """Create a new entity. Raises ValueError if key already exists."""
        if self.exists(key):
            raise ValueError(f"Key '{key}' already exists in the collection.")

        return self.update(key, database)

    def get(self, key: str) -> _JsonDatabase[T]:
        """Get an entity by key, creating directory if needed."""
        if not key or not key.strip():
            raise ValueError("Key cannot be empty or whitespace-only")

        if not self.private_path.exists():
            self.private_path.mkdir(parents=True, exist_ok=True)

        return JsonDatabase(
            path=self.private_path / f"{key}.json",
            database_model=self.private_model,
        )

    def list_keys(self) -> list[str]:
        if not self.private_path.exists():
            return []

        return [
            file.stem
            for file in self.private_path.glob("*.json")
            if file.is_file()
        ]

    def delete(self, key: str) -> None:
        """Delete an entity by key."""
        if not key or not key.strip():
            raise ValueError("Key cannot be empty or whitespace-only")

        file_path = self.private_path / f"{key}.json"
        if file_path.exists():
            file_path.unlink()

    def exists(self, key: str) -> bool:
        """Check if an entity exists."""
        if not key or not key.strip():
            raise ValueError("Key cannot be empty or whitespace-only")

        file_path = self.private_path / f"{key}.json"
        return file_path.exists()

    def clear(self) -> None:
        if not self.private_path.exists():
            return

        for file in self.private_path.glob("*.json"):
            if file.is_file():
                file.unlink()

    def update(self, key: str, updated_database: T) -> T:
        db = self.get(key)
        db.write(updated_database)
        return db.get_database()

    def get_all(self) -> dict[str, T]:
        all_data = {}
        for key in self.list_keys():
            db = self.get(key)
            all_data[key] = db.get_database()
        return all_data

    def update_all(self, updated_databases: dict[str, T]) -> dict[str, T]:
        for key, updated_database in updated_databases.items():
            self.update(key, updated_database)
        return self.get_all()

    # Async versions, "just in case" situations

    async def async_update(self, key: str, updated_database: T) -> T:
        """Async update with thread-pool execution and locking."""
        async with self._lock:
            return await asyncio.to_thread(self.update, key, updated_database)

    async def async_get_all(self) -> dict[str, T]:
        """Async get all with thread-pool execution and locking."""
        async with self._lock:
            return await asyncio.to_thread(self.get_all)

    async def async_update_all(
        self, updated_databases: dict[str, T]
    ) -> dict[str, T]:
        """Async update all with thread-pool execution and locking."""
        async with self._lock:
            return await asyncio.to_thread(self.update_all, updated_databases)

    async def async_delete(self, key: str) -> None:
        """Async delete with thread-pool execution and locking."""
        async with self._lock:
            await asyncio.to_thread(self.delete, key)

    async def async_exists(self, key: str) -> bool:
        """Async exists with thread-pool execution and locking."""
        async with self._lock:
            return await asyncio.to_thread(self.exists, key)

    async def async_clear(self) -> None:
        """Async clear with thread-pool execution and locking."""
        async with self._lock:
            await asyncio.to_thread(self.clear)

    async def async_list_keys(self) -> list[str]:
        """Async list keys with thread-pool execution and locking."""
        async with self._lock:
            return await asyncio.to_thread(self.list_keys)

    async def async_get(self, key: str) -> _JsonDatabase[T]:
        """Async get with thread-pool execution and locking."""
        async with self._lock:
            return await asyncio.to_thread(self.get, key)