import asyncio
import time
from pathlib import Path
from types import TracebackType
from typing import Generic, Type, TypeVar

from pydantic import BaseModel, ValidationError

from .file import JsonFile

T = TypeVar("T", bound=BaseModel)

ASYNCIO_LOCKS_AVAILABLE: dict[str, asyncio.Lock] = {}

# Known Bugs/Features to Implement:
# - Atomic writes to prevent data loss. See: https://stackoverflow.com/a/2333872/11761617
# - Sync/async race, handle the case where a user uses both sync and async, which could lead to corruption.
# - Cross process protection, if multiple processes are accessing the same file, this could lead to corruption.
#    To fix, we would need to do OS level file locking.

# Dev Notes:
# - asyncio.to_thread is used to run the synchronous method in a separate thread,
#    this allows the event loop to remain working while the potentially blocking file I/O operation is performed.

class _JsonDatabase(Generic[T]):
    def __init__(
        self,
        path: str | Path,
        database_model: Type[T],
        backup_on_validation_error: bool,
    ):

        try:
            database_model()
        except ValidationError as error:
            raise ValueError(
                f"JsonDatabase requires all fields to have defaults, but "
                f"{database_model.__name__} has required fields:\n{error}"
            )

        self.path = JsonFile(path)

        self.backup_on_validation_error = backup_on_validation_error
        self.database_model = database_model
        self.database: T = self.database_model()
        
        self.lock_key = str(self.path.absolute())

    def get_lock(self) -> asyncio.Lock:
        lock = ASYNCIO_LOCKS_AVAILABLE.get(self.lock_key)

        if lock is None:
            lock = ASYNCIO_LOCKS_AVAILABLE[self.lock_key] = asyncio.Lock()

        return lock

    async def read_async(self) -> T:
        return await asyncio.to_thread(self.read)

    async def write_async(self, data: T) -> None:
        await asyncio.to_thread(self.write, data)
    
    def set(self, data: T) -> None:
        if not isinstance(data, self.database_model):
            raise TypeError(
                f"set() expected {self.database_model.__name__}, got {type(data).__name__}"
            )

        # Prevents Reference issues when a user does something to data after calling set.
        self.database = data.model_copy(deep=True)

    async def __aenter__(self) -> T:
        lock = self.get_lock()
        await lock.acquire()

        self.database = await self.read_async()
        return self.database.model_copy(deep=True)

    async def __aexit__(
        self,
        exc_type: Type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        try:
            await self.write_async(self.database)
        finally:
            lock = self.get_lock()
            lock.release()

    def write(self, data: T) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

        self.path.write_text(
            data.model_dump_json(indent=4)
        )

    def backup(self) -> None:
        current_epoch_time = int(time.time())

        backup_path = self.path.with_name(f"{self.path.stem}_backup_{current_epoch_time}.json")
        
        backup_path.write_text(
            self.path.read_text()
        )

    def read(self) -> T:
        if not self.path.exists():
            # new_instance prevents cases where the file is empty, but self.database isn't
            # or file exists but self.database != the content in the file
            # basically ensures that the file's data and self.database are always in sync at any point in time.
            new_instance = self.database_model()
            self.write(new_instance)
            return new_instance
        
        data = self.path.read_text()

        if data:
            try:
                return self.database_model.model_validate_json(data)
            except ValidationError as error:
                error_message = (
                    f"Failed to read database file {self.path} due to validation error:\n{error}\n"
                    "If this is for production use, consider implementing a migration strategy.\n"
                )

                if self.backup_on_validation_error:
                    self.backup()
                    error_message += (
                        "\nA backup of the invalid data has been created with a timestamp in the filename. "
                    )

                raise ValueError(error_message)
        else:
            new_instance = self.database_model()
            self.write(new_instance)
            return new_instance

    def __enter__(self) -> T:
        self.database = self.read()
        return self.database.model_copy(deep=True)

    def __exit__(
        self,
        exc_type: Type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.write(self.database)